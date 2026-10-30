"""Durable case publication and reviewer/audit transactions over real SQLite files."""
from __future__ import annotations

import json
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from toolkit import asr
from toolkit.ledger import Ledger

from dealerwatch import config, pipeline
from dealerwatch.decisions import apply_decision
from dealerwatch.models import CaseStatus, Recommendation
from dealerwatch.store import Store
from test_api import PHONE, build_fixture
from test_core_decisions import _case


@pytest.fixture
def investigation(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DW_LLM", "mock")
    monkeypatch.setenv("DW_ASR", "replay")
    monkeypatch.setenv("DW_LLM_CACHE_ON", "0")
    data, runtime = tmp_path / "data", tmp_path / "runtime"
    build_fixture(data)
    pipeline.run(str(data), str(runtime))
    store = Store(runtime / config.DB_FILE)
    ledger = Ledger(str(runtime / config.LEDGER_FILE))
    yield data, runtime, store, ledger
    ledger.close()


def _state(store: Store, ledger: Ledger):
    return store.list_cases(), store.get_stats(), ledger.entries()


def test_rerun_preserves_reviewed_case_and_appends_ledger(investigation):
    data, runtime, store, ledger = investigation
    original = store.list_cases()[0]
    decided = apply_decision(store, ledger, original.case_id, "approve_escalation", "Asha", "complete")
    prefix = ledger.entries()

    pipeline.run(str(data), str(runtime))

    assert store.get_case(original.case_id) == decided
    assert len(store.list_cases()) == 2
    assert ledger.entries()[:len(prefix)] == prefix
    assert ledger.count() > len(prefix)
    assert ledger.verify()["ok"]


def test_analysis_failure_leaves_previous_publication_untouched(investigation, monkeypatch):
    data, runtime, store, ledger = investigation
    before = _state(store, ledger)
    make_case = pipeline.make_case
    calls = 0

    def fail_second_case(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("analysis interrupted")
        return make_case(*args, **kwargs)

    monkeypatch.setattr(pipeline, "make_case", fail_second_case)
    with pytest.raises(RuntimeError, match="analysis interrupted"):
        pipeline.run(str(data), str(runtime))
    assert calls == 2
    assert _state(store, ledger) == before


@pytest.mark.parametrize("reset", [False, True])
def test_publication_failure_rolls_back_cases_stats_and_audit(investigation, reset):
    data, runtime, store, ledger = investigation
    before = _state(store, ledger)
    trades_path = data / "trades.json"
    trades = json.loads(trades_path.read_text())
    trades[0]["price"] += 1
    trades_path.write_text(json.dumps(trades))
    with sqlite3.connect(store.path) as db:
        db.execute("CREATE TRIGGER fail_case BEFORE INSERT ON cases "
                   "WHEN json_extract(NEW.body, '$.account.account_id') = 'A-050' "
                   "BEGIN SELECT RAISE(ABORT, 'publication interrupted'); END")

    with pytest.raises(sqlite3.IntegrityError, match="publication interrupted"):
        pipeline.run(str(data), str(runtime), reset=reset)
    assert _state(store, ledger) == before


def test_modified_evidence_cannot_reuse_old_decision_even_with_same_dataset_id(investigation):
    data, runtime, store, ledger = investigation
    pipeline.run(str(data), str(runtime), reset=True, dataset_id="import-1")
    old = next(c for c in store.list_cases() if c.account.account_id == "A-011")
    decided = apply_decision(store, ledger, old.case_id, "dismiss", "Asha", "reviewed old evidence")
    trades_path = data / "trades.json"
    trades = json.loads(trades_path.read_text())
    trades[0]["price"] = 1490.0
    trades_path.write_text(json.dumps(trades))

    pipeline.run(str(data), str(runtime), dataset_id="import-1")

    assert store.get_case(old.case_id) == decided
    revised = [c for c in store.list_cases() if c.account.account_id == "A-011" and c.case_id != old.case_id]
    assert len(revised) == 1
    assert revised[0].status == CaseStatus.NEW and revised[0].decisions == []
    assert revised[0].evidence_snapshot["trades"][0]["price"] == 1490.0
    assert old.evidence_snapshot["trades"][0]["price"] == 1500.0
    assert len(store.list_cases()) == 4
    assert ledger.verify()["ok"]


def test_legacy_case_ids_are_retained_on_first_durable_run(investigation):
    data, runtime, store, ledger = investigation
    legacy = _case("CASE-0001")
    store.save_case(legacy)
    decided = apply_decision(store, ledger, legacy.case_id, "dismiss", "Asha")
    pipeline.run(str(data), str(runtime))
    assert store.get_case(legacy.case_id) == decided


def test_revision_prevents_stale_decision_and_idempotency_returns_original_response(investigation):
    _, _, store, ledger = investigation
    case = store.list_cases()[0]
    first = apply_decision(store, ledger, case.case_id, "start_review", "Asha", "checking",
                           expected_revision=case.revision, idempotency_key="review-1")
    assert first.revision == case.revision + 1
    count = ledger.count()
    with pytest.raises(ValueError, match="revision"):
        apply_decision(store, ledger, case.case_id, "dismiss", "Asha", expected_revision=case.revision)
    second = apply_decision(store, ledger, case.case_id, "request_info", "Asha", "need KYC",
                            expected_revision=first.revision, idempotency_key="review-2")
    replay = apply_decision(Store(store.path), ledger, case.case_id, "start_review", "Asha", "checking",
                            expected_revision=case.revision, idempotency_key="review-1")
    assert replay == first
    assert store.get_case(case.case_id) == second
    assert ledger.count() == count + 1
    with pytest.raises(ValueError, match="idempotency"):
        apply_decision(store, ledger, case.case_id, "dismiss", "Asha", idempotency_key="review-1")
    other = next(c for c in store.list_cases() if c.case_id != case.case_id)
    with pytest.raises(ValueError, match="idempotency"):
        apply_decision(store, ledger, other.case_id, "start_review", "Asha", "checking",
                       expected_revision=case.revision, idempotency_key="review-1")
    assert ledger.count() == count + 1


def test_idempotent_terminal_retry_succeeds_without_another_audit_event(investigation):
    _, _, store, ledger = investigation
    case = store.list_cases()[0]
    result = apply_decision(store, ledger, case.case_id, "dismiss", "Asha",
                            expected_revision=case.revision, idempotency_key="close-1")
    count = ledger.count()
    assert apply_decision(store, ledger, case.case_id, "dismiss", "Asha",
                          expected_revision=case.revision, idempotency_key="close-1") == result
    with pytest.raises(ValueError, match="CLOSED"):
        apply_decision(store, ledger, case.case_id, "dismiss", "Asha", idempotency_key="close-2")
    assert ledger.count() == count


def test_concurrent_terminal_decisions_across_store_instances_have_one_winner(investigation):
    _, runtime, store, ledger = investigation
    case = store.list_cases()[0]
    before = ledger.count()
    barrier = threading.Barrier(8)

    def decide(index):
        independent_store = Store(store.path)
        independent_ledger = Ledger(str(runtime / config.LEDGER_FILE))
        try:
            barrier.wait(timeout=10)
            try:
                return apply_decision(independent_store, independent_ledger, case.case_id,
                                      "dismiss" if index % 2 else "approve_escalation", f"Reviewer {index}")
            except ValueError:
                return None
        finally:
            independent_ledger.close()

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(decide, range(8)))
    winners = [result for result in results if result is not None]
    assert len(winners) == 1
    assert len(store.get_case(case.case_id).decisions) == 1
    assert ledger.count() == before + 1
    assert ledger.verify()["ok"]


def test_audit_insert_failure_rolls_back_decision_and_allows_retry(investigation):
    _, _, store, ledger = investigation
    case = store.list_cases()[0]
    before = _state(store, ledger)
    with sqlite3.connect(ledger.path) as db:
        db.execute("CREATE TRIGGER fail_audit BEFORE INSERT ON ledger "
                   "BEGIN SELECT RAISE(ABORT, 'audit unavailable'); END")
    with pytest.raises(sqlite3.IntegrityError, match="audit unavailable"):
        apply_decision(store, ledger, case.case_id, "dismiss", "Asha",
                       expected_revision=case.revision, idempotency_key="retry-after-failure")
    assert _state(store, ledger) == before
    with sqlite3.connect(ledger.path) as db:
        db.execute("DROP TRIGGER fail_audit")
    result = apply_decision(store, ledger, case.case_id, "dismiss", "Asha",
                            expected_revision=case.revision, idempotency_key="retry-after-failure")
    assert result.status == CaseStatus.CLOSED and len(result.decisions) == 1
    assert ledger.count() == len(before[2]) + 1


def test_snapshot_contains_transcribed_calls_raw_evidence_and_bounded_prices(investigation, monkeypatch):
    data, runtime, store, _ = investigation
    transcript = [{"id": "C-001-u01", "speaker": "D1", "start_ms": 0, "end_ms": 5000,
                   "text": "Buy INFY, big order coming"}]
    monkeypatch.setattr(asr, "transcribe", lambda *args, **kwargs: (transcript, "test-asr"))
    pipeline.run(str(data), str(runtime), reset=True)
    case = next(c for c in store.list_cases() if c.account.account_id == "A-011")
    snap = case.evidence_snapshot
    assert [t["trade_id"] for t in snap["trades"]] == ["T-000001", "T-000002", "T-000003"]
    assert snap["call_details"][0]["utterances"] == transcript
    assert snap["call_details"][0]["audio_file"] == "audio/C-001.wav"
    assert snap["call_details"][0]["has_audio"] is True
    assert {c["clause_id"] for c in snap["clauses"]} == {"PFUTP-4-2-q", "SEBI-AMC-FR-MECH"}
    assert snap["prices"][0]["time"] == "2026-09-14T11:41:00"
    assert snap["prices"][-1]["time"] == "2026-09-14T15:29:00"
    assert snap["node_labels"]["P-001"] == "Vikram Shah (brother-in-law of D1)"
    assert snap["node_labels"][PHONE] == "Vikram Shah (P-001)"
    assert Path(snap["data_dir"]) == data.resolve()


def test_progress_run_metadata_and_explicit_reset(investigation):
    data, runtime, store, ledger = investigation
    case = store.list_cases()[0]
    apply_decision(store, ledger, case.case_id, "dismiss", "Asha")
    calls = []
    stats = pipeline.run(str(data), str(runtime), reset=True, run_id="run-demo",
                         dataset_id="demo-data", progress=lambda *args: calls.append(args))
    assert stats.run_id == "run-demo" and stats.dataset_id == "demo-data"
    assert all(c.run_id == "run-demo" and c.dataset_id == "demo-data" for c in store.list_cases())
    assert all(c.status == CaseStatus.NEW and not c.decisions for c in store.list_cases())
    assert calls and all(isinstance(stage, str) and 0 <= completed <= total
                         for stage, completed, total in calls)
    assert any(completed == total == 2 for _, completed, total in calls)
    assert not any(e["action"].startswith("decision.") for e in ledger.entries())
    assert ledger.verify()["ok"]


def test_store_filters_and_pages_without_losing_total_count(investigation):
    _, _, store, _ = investigation
    assert store.count_cases() == 2
    rows, total = store.query_cases(scrip="INFY", dealer_id="D1", limit=1, offset=1)
    assert len(rows) == 1 and total == 2
    rows, total = store.query_cases(q="neha", recommendation="ESCALATE", status="NEW")
    assert total == 1 and rows[0].account.account_id == "A-011"
    assert store.query_cases(q="%_") == ([], 0)
    assert store.query_cases(scrip="TCS") == ([], 0)


def test_existing_sqlite_schema_and_case_json_migrate_without_erasing_history(tmp_path):
    path = tmp_path / "old.db"
    case = _case()
    body = case.model_dump(mode="json", exclude={"revision", "dataset_id", "run_id", "evidence_snapshot"})
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE cases (case_id TEXT PRIMARY KEY, status TEXT NOT NULL, "
                   "recommendation TEXT NOT NULL, score REAL NOT NULL, body TEXT NOT NULL)")
        db.execute("INSERT INTO cases VALUES (?, ?, ?, ?, ?)",
                   (case.case_id, case.status.value, case.recommendation.value, case.candidate.score,
                    json.dumps(body)))
    store = Store(path)
    rows, count = store.query_cases(q="Sunil", scrip="INFY", dealer_id="D1")
    assert count == 1 and rows[0].case_id == case.case_id
    assert rows[0].revision == 0 and rows[0].evidence_snapshot == {}


def test_review_committed_during_analysis_survives_publication(investigation, monkeypatch):
    data, runtime, store, ledger = investigation
    target = store.list_cases()[0]
    decided = []
    make_case = pipeline.make_case

    def review_while_analysing(*args, **kwargs):
        case = make_case(*args, **kwargs)
        if not decided:
            decided.append(apply_decision(Store(store.path), ledger, target.case_id,
                                          "approve_escalation", "Asha", "review completed during run"))
        return case

    monkeypatch.setattr(pipeline, "make_case", review_while_analysing)
    pipeline.run(str(data), str(runtime))
    assert store.get_case(target.case_id) == decided[0]
    assert ledger.verify()["ok"]
    assert sum(e["action"] == "decision.approve_escalation" for e in ledger.entries()) == 1


def test_late_audit_failure_rolls_back_entire_publication(investigation):
    data, runtime, store, ledger = investigation
    before = _state(store, ledger)
    with sqlite3.connect(ledger.path) as db:
        db.execute("CREATE TRIGGER fail_run_end BEFORE INSERT ON ledger WHEN NEW.action = 'run.end' "
                   "BEGIN SELECT RAISE(ABORT, 'late audit failure'); END")
    with pytest.raises(sqlite3.IntegrityError, match="late audit failure"):
        pipeline.run(str(data), str(runtime), reset=True)
    assert _state(store, ledger) == before


def test_parallel_toolkit_appends_and_decisions_share_one_valid_chain(investigation):
    _, runtime, store, ledger = investigation
    target = store.list_cases()[0]
    count = ledger.count()
    barrier = threading.Barrier(6)

    def write(index):
        local_store = Store(store.path)
        local_ledger = Ledger(str(runtime / config.LEDGER_FILE))
        try:
            barrier.wait(timeout=10)
            for n in range(10):
                if index % 2:
                    local_ledger.append("integration", "concurrent.event", {"writer": index, "n": n})
                else:
                    apply_decision(local_store, local_ledger, target.case_id, "request_info", "Asha",
                                   f"item {index}-{n}", idempotency_key=f"parallel-{index}-{n}")
        finally:
            local_ledger.close()

    with ThreadPoolExecutor(max_workers=6) as executor:
        list(executor.map(write, range(6)))
    assert len(store.get_case(target.case_id).decisions) == 30
    assert store.get_case(target.case_id).revision == target.revision + 30
    assert ledger.count() == count + 60
    assert ledger.verify()["ok"]


@pytest.mark.parametrize("field", ["expected_revision", "idempotency_key"])
def test_invalid_concurrency_controls_do_not_mutate_cases(investigation, field):
    _, _, store, ledger = investigation
    case = store.list_cases()[0]
    before = _state(store, ledger)
    values = [-1, True, "0"] if field == "expected_revision" else ["", " ", "x" * 201]
    for value in values:
        with pytest.raises(ValueError):
            apply_decision(store, ledger, case.case_id, "dismiss", "Asha", **{field: value})
    assert _state(store, ledger) == before


def test_price_or_transcript_changes_create_new_evidence_without_overwriting_case(investigation, monkeypatch):
    data, runtime, store, ledger = investigation
    target = next(c for c in store.list_cases() if c.account.account_id == "A-011")
    decided = apply_decision(store, ledger, target.case_id, "dismiss", "Asha")
    raw_calls = json.loads((data / "calls" / "C-001.json").read_text())
    transcribed = raw_calls["utterances"]
    transcribed[0]["text"] += " Additional transcribed sentence."
    monkeypatch.setattr(asr, "transcribe", lambda *args, **kwargs: (transcribed, "test-asr"))
    pipeline.run(str(data), str(runtime))
    assert store.get_case(target.case_id) == decided
    revisions = [c for c in store.list_cases() if c.account.account_id == "A-011"]
    assert len(revisions) == 2
    assert len({c.dataset_id for c in revisions}) == 1
    assert len({c.case_id for c in revisions}) == 2


def test_empty_dataset_run_preserves_history_but_updates_latest_stats(investigation):
    data, runtime, store, ledger = investigation
    before = store.list_cases()
    (data / "trades.json").write_text("[]")
    stats = pipeline.run(str(data), str(runtime))
    assert stats.cases == stats.candidates == 0
    assert store.list_cases() == before
    assert store.get_stats() == stats
    assert ledger.verify()["ok"]


def test_queue_ranks_recommendation_then_score_but_list_keeps_stable_identity_order(tmp_path):
    store = Store(tmp_path / "cases.db")
    for identity, recommendation, score in (
            ("CASE-A", Recommendation.DISMISS, 0.99),
            ("CASE-B", Recommendation.REVIEW, 0.99),
            ("CASE-C", Recommendation.ESCALATE, 0.50),
            ("CASE-D", Recommendation.ESCALATE, 0.90)):
        case = _case(identity)
        store.save_case(case.model_copy(update={"recommendation": recommendation,
                                               "candidate": case.candidate.model_copy(update={"score": score})}))
    assert [case.case_id for case in store.query_cases(limit=3)[0]] == ["CASE-D", "CASE-C", "CASE-B"]
    assert [case.case_id for case in store.list_cases()] == ["CASE-A", "CASE-B", "CASE-C", "CASE-D"]


def test_archived_audio_survives_source_replacement_and_used_for_asr(investigation, monkeypatch):
    data, runtime, store, _ = investigation
    case = next(c for c in store.list_cases() if c.account.account_id == "A-011")
    call = case.evidence_snapshot["call_details"][0]
    archived = Path(case.evidence_snapshot["audio_dir"]) / call["snapshot_audio_file"]
    original = archived.read_bytes()
    original_source = data / call["audio_file"]
    assert original == original_source.read_bytes()
    new_audio = original + b"new recording bytes"
    original_source.write_bytes(new_audio)
    assert archived.read_bytes() == original
    seen = []

    def check_archived_asr(transcription_call, transcription_dir):
        audio = Path(transcription_dir) / transcription_call["audio_file"]
        seen.append(audio.read_bytes())
        assert audio.is_relative_to(runtime.resolve())
        return transcription_call["utterances"], "replay"

    monkeypatch.setattr(asr, "transcribe", check_archived_asr)
    pipeline.run(str(data), str(runtime))
    assert seen == [new_audio]
    assert store.get_case(case.case_id).evidence_snapshot == case.evidence_snapshot
    newer = next(c for c in store.list_cases() if c.account.account_id == "A-011" and c.case_id != case.case_id)
    newer_call = newer.evidence_snapshot["call_details"][0]
    newer_archive = Path(newer.evidence_snapshot["audio_dir"]) / newer_call["snapshot_audio_file"]
    assert newer_archive.read_bytes() == new_audio and newer_archive != archived


@pytest.mark.parametrize("idempotent", [False, True])
def test_parallel_revision_checks_or_identical_retries_commit_only_once(investigation, idempotent):
    _, runtime, store, ledger = investigation
    target = store.list_cases()[0]
    before = ledger.count()
    barrier = threading.Barrier(4)

    def review(_):
        local_store = Store(store.path)
        local_ledger = Ledger(str(runtime / config.LEDGER_FILE))
        try:
            barrier.wait(timeout=10)
            try:
                return apply_decision(local_store, local_ledger, target.case_id, "start_review", "Asha",
                                      expected_revision=target.revision,
                                      idempotency_key="same-request" if idempotent else None)
            except ValueError:
                return None
        finally:
            local_ledger.close()

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(review, range(4)))
    completed = [result for result in results if result is not None]
    assert len(completed) == (4 if idempotent else 1)
    assert all(result == completed[0] for result in completed)
    assert store.get_case(target.case_id).revision == target.revision + 1
    assert ledger.count() == before + 1
    assert ledger.verify()["ok"]


def test_wal_configuration_rejects_audited_change_without_partial_write(investigation):
    _, _, store, ledger = investigation
    target = store.list_cases()[0]
    before = _state(store, ledger)
    with sqlite3.connect(store.path) as db:
        assert db.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
    with pytest.raises(ValueError, match="rollback journal"):
        apply_decision(store, ledger, target.case_id, "dismiss", "Asha")
    assert _state(store, ledger) == before
