from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT.parent / "casey-git-clone" / "src"))

from casey_git_clone.cli import main as casey_main  # noqa: E402
from casey_git_clone.export import export_casey_facts  # noqa: E402
from selector_dsl.casey_adapter import evaluate_casey_export  # noqa: E402


def test_casey_advisory_is_deterministic_for_same_export() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "casey_runtime.sqlite"
        casey_main(["init", "--db", str(db_path), "--workspace", "alice"])
        casey_main(["workspace", "create", "--db", str(db_path), "--workspace", "bob"])
        casey_main(
            [
                "publish",
                "--db",
                str(db_path),
                "--workspace",
                "alice",
                "--path",
                "src/main.c",
                "--content",
                "base",
            ]
        )
        casey_main(["sync", "--db", str(db_path), "--workspace", "bob"])
        casey_main(
            [
                "publish",
                "--db",
                str(db_path),
                "--workspace",
                "alice",
                "--path",
                "src/main.c",
                "--content",
                "alice-edit",
            ]
        )
        casey_main(
            [
                "publish",
                "--db",
                str(db_path),
                "--workspace",
                "bob",
                "--path",
                "src/main.c",
                "--content",
                "bob-edit",
            ]
        )

        casey_export = export_casey_facts(db_path=db_path, workspace_id="alice")

    advisory_a = evaluate_casey_export(casey_export, evaluated_at="2026-03-19T12:00:00Z")
    advisory_b = evaluate_casey_export(casey_export, evaluated_at="2026-03-19T12:00:00Z")

    assert advisory_a == advisory_b
    assert advisory_a["fuzzymodo_result_version"] == "fuzzymodo.casey.advisory.v1"
    assert advisory_a["workspace_id"] == "alice"
    assert len(advisory_a["path_results"]) == 1

    result = advisory_a["path_results"][0]
    assert result["path"] == "src/main.c"
    assert result["gap"]["gap_kind"] == "candidate_divergence"
    assert result["gap"]["severity"] == "medium"
    assert len(result["candidate_rankings"]) == 2
    assert result["recommended_fv_id"] == result["candidate_rankings"][0]["fv_id"]
    assert "evaluation_digest" in advisory_a
    assert advisory_a["evaluation_digest"]


def test_casey_export_and_advisory_roundtrip_via_cli_json(capsys) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "casey_runtime.sqlite"
        casey_main(["init", "--db", str(db_path), "--workspace", "alice"])
        casey_main(
            [
                "publish",
                "--db",
                str(db_path),
                "--workspace",
                "alice",
                "--path",
                "README.md",
                "--content",
                "hello",
            ]
        )

        capsys.readouterr()
        casey_main(["--json", "export", "--db", str(db_path), "--workspace", "alice"])
        export_payload = json.loads(capsys.readouterr().out)

    advisory = evaluate_casey_export(export_payload, evaluated_at="2026-03-19T12:30:00Z")

    assert export_payload["kind"] == "export"
    assert export_payload["casey_export_version"] == "casey.facts.v1"
    assert advisory["path_results"][0]["gap"]["gap_kind"] == "none"
