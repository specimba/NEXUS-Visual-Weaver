import json
from pathlib import Path

from nexus_visual_weaver.exporter import write_export_packet
from nexus_visual_weaver.planner import build_command_center_run


def test_write_export_packet_records_evidence_without_secrets(monkeypatch) -> None:
    export_dir = Path("outputs/test-exports")
    monkeypatch.setenv("NEXUS_EXPORT_DIR", str(export_dir))
    run = build_command_center_run("gothic couture archivist, platform boots")
    scan = {"status": "pass", "export_gate": "clear", "findings": [], "purification_actions": []}
    state = {
        "provider_state": "export_ready",
        "checkpoint": "approved",
        "message": "approved",
        "generation": {"status": "success", "output_path": "/data/artifact.png", "hf_token_present": True},
        "minicpm_judge": {"status": "success", "repo_id": "openbmb/MiniCPM-V-4.6"},
        "nemotron_evidence": {"status": "missing_secret", "repo_id": "nvidia/NVIDIA-Nemotron-Parse-v1.2"},
    }

    result = write_export_packet(run=run, scan=scan, operator_state=state, adult_mode=False)
    payload = json.loads(Path(result["path"]).read_text(encoding="utf-8"))

    assert payload["run_id"] == run.checkpoint.checkpoint_id
    assert payload["hackathon_claims"]["openbmb_lane"] is True
    assert payload["hackathon_claims"]["nvidia_nemotron_lane"] is False
    assert payload["parameter_budget"]["status"] == "pass"
    assert "token" not in json.dumps(payload).lower()
