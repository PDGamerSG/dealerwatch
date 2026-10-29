"""Validate imported evidence before it can enter an investigation."""
from __future__ import annotations

import copy

import pytest
from test_api import build_fixture


@pytest.fixture
def bundle(tmp_path):
    from dealerwatch.datasets import read_bundle
    build_fixture(tmp_path / "source")
    return read_bundle(tmp_path / "source")


def test_valid_bundle_round_trip_is_content_addressed(bundle, tmp_path):
    from dealerwatch.datasets import DatasetRegistry, read_bundle, validate_bundle
    report = validate_bundle(bundle)
    assert report["valid"], report["issues"]
    registry = DatasetRegistry(tmp_path / "runtime", tmp_path / "original")
    path, imported = registry.import_bundle(bundle)
    assert imported["fingerprint"] == report["fingerprint"]
    assert registry.active_dir == path
    assert DatasetRegistry(tmp_path / "runtime", tmp_path / "original").active_dir == path
    assert validate_bundle(read_bundle(path))["fingerprint"] == report["fingerprint"]
    assert registry.import_bundle(bundle)[0] == path


@pytest.mark.parametrize("mutation", [
    lambda x: x["trades"][0].update(price=float("nan")),
    lambda x: x["trades"][0].update(price=-1),
    lambda x: x["trades"][0].update(price=1e308),
    lambda x: x["trades"][0].update(qty=True),
    lambda x: x["trades"][0].update(qty=10**400),
    lambda x: x["trades"][0].update(qty=0),
    lambda x: x["trades"][0].update(qty=1.5),
    lambda x: x["trades"][0].update(account_id="UNKNOWN"),
    lambda x: x["trades"].append(copy.deepcopy(x["trades"][0])),
    lambda x: x["orders"][0].update(order_time="not-a-date"),
    lambda x: x["orders"][0].update(exec_end="2026-09-13T09:00:00"),
    lambda x: x["orders"][0].update(order_time="2026-09-14T13:41:00+05:30"),
    lambda x: x["calls"][0].update(audio_file="../../secret.wav"),
    lambda x: x["calls"][0].update(call_id="../../escape"),
    lambda x: x["calls"][0]["utterances"][0].update(end_ms=-1),
    lambda x: x["calls"][0]["utterances"][0].update(end_ms=99999999),
    lambda x: x["links"][0].update(dst="UNKNOWN"),
    lambda x: x["truth"]["cases"][0].update(order_id="UNKNOWN"),
    lambda x: x["prices"][0].update(close="NaN"),
])
def test_bad_evidence_rejected_without_switching_active_dataset(bundle, tmp_path, mutation):
    from dealerwatch.datasets import (
        DatasetRegistry,
        DatasetValidationError,
        validate_bundle,
    )
    registry = DatasetRegistry(tmp_path / "runtime", tmp_path / "original")
    old, _ = registry.import_bundle(bundle)
    mutation(bundle)
    report = validate_bundle(bundle)
    assert report["valid"] is False
    assert any(x["severity"] == "error" for x in report["issues"])
    with pytest.raises(DatasetValidationError):
        registry.import_bundle(bundle)
    assert registry.active_dir == old


def test_missing_required_files_do_not_appear_as_valid_empty_data(tmp_path):
    from dealerwatch.datasets import validate_directory
    tmp_path.joinpath("orders.json").write_text("[]")
    report = validate_directory(tmp_path)
    assert report["valid"] is False
    assert any("trades" in x["location"] for x in report["issues"])


def test_fingerprint_detects_changed_transcript_and_price(bundle):
    from dealerwatch.datasets import validate_bundle
    before = validate_bundle(bundle)["fingerprint"]
    bundle["calls"][0]["utterances"][0]["text"] = "Changed evidence"
    assert validate_bundle(bundle)["fingerprint"] != before


def test_optional_labels_and_prices_are_not_required(bundle):
    from dealerwatch.datasets import validate_bundle
    bundle.pop("truth")
    bundle.pop("prices")
    report = validate_bundle(bundle)
    assert report["valid"] and report["label_counts"] == {}


def test_invalid_json_is_a_report_not_an_unhandled_error(tmp_path):
    from dealerwatch.datasets import validate_directory
    tmp_path.joinpath("orders.json").write_text("{broken")
    assert validate_directory(tmp_path)["valid"] is False


def test_reversed_call_order_round_trips_and_reimports(bundle, tmp_path):
    from dealerwatch.datasets import DatasetRegistry, validate_directory
    second = copy.deepcopy(bundle["calls"][0])
    second["call_id"] = "C-002"
    second["utterances"] = []
    bundle["calls"] = [second, bundle["calls"][0]]
    registry = DatasetRegistry(tmp_path / "runtime", tmp_path / "original")
    directory, report = registry.import_bundle(bundle)
    assert validate_directory(directory)["fingerprint"] == report["fingerprint"]
    assert registry.import_bundle(bundle)[0] == directory
