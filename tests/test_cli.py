from __future__ import annotations

import json


def test_check_command_generates_valid_data_without_running_server(tmp_path, capsys):
    from dealerwatch.__main__ import main
    assert main(["--data", str(tmp_path / "data"), "--runtime", str(tmp_path / "runtime"), "--check"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["valid"] and result["label_counts"]["UNLINKED_PATTERN"] >= 3
    assert not (tmp_path / "runtime" / "dealerwatch.db").exists()


def test_check_command_preserves_existing_files(tmp_path, capsys):
    from dealerwatch.__main__ import main
    data = tmp_path / "data"
    args = ["--data", str(data), "--runtime", str(tmp_path / "runtime"), "--check"]
    assert main(args) == 0
    before = (data / "calls" / "C-001.json").read_bytes()
    assert main(args) == 0
    assert (data / "calls" / "C-001.json").read_bytes() == before
