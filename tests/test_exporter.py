import json
from pathlib import Path

from nexus_visual_weaver.exporter import export_root, write_export_packet
from nexus_visual_weaver.planner import build_command_center_run


def _make_base_state(**overrides):
    state = {
        "provider_state": "export_ready",
        "checkpoint": "approved",
        "message": "approved",
        "generation": {"status": "success", "output_path": "/data/artifact.png", "hf_token_present": True},
        "locateanything_grounding": {"status": "pass", "repo_id": "nvidia/LocateAnything-3B", "targets": [{"slot_name": "footwear"}]},
        "offellia_judge": {"status": "deferred_local", "repo_id": "Brunobkr/OFFELLIA_Q4_0_gemma-4-12B-it.gguf"},
        "minicpm_judge": {"status": "success", "repo_id": "openbmb/MiniCPM-V-4.6"},
        "nemotron_evidence": {"status": "missing_secret", "repo_id": "nvidia/NVIDIA-Nemotron-Parse-v1.2"},
        "modal_video_repair": {"status": "deferred", "repo_id": "netflix/void-model", "provider": "modal"},
        "audio_lore_tts": {"status": "optional", "repo_id": "hexgrad/Kokoro-82M"},
        "tiny_titan_sidecar": {"status": "available", "repo_id": "black-forest-labs/FLUX.2-klein-4B"},
    }
    state.update(overrides)
    return state


def test_write_export_packet_records_evidence_without_secrets(monkeypatch) -> None:
    export_dir = Path("outputs/test-exports")
    monkeypatch.setenv("NEXUS_EXPORT_DIR", str(export_dir))
    run = build_command_center_run("gothic couture archivist, platform boots")
    scan = {"status": "pass", "export_gate": "clear", "findings": [], "purification_actions": []}
    state = _make_base_state()

    result = write_export_packet(run=run, scan=scan, operator_state=state, adult_mode=False)
    payload = json.loads(Path(result["path"]).read_text(encoding="utf-8"))

    assert payload["run_id"] == run.checkpoint.checkpoint_id
    assert payload["hackathon_claims"]["openbmb_lane"] is True
    assert payload["hackathon_claims"]["nvidia_nemotron_lane"] is False
    assert payload["parameter_budget"]["status"] == "pass"
    assert payload["active_preset"] == "Raven Quality Stack"
    assert payload["modal_video_repair"]["repo_id"] == "netflix/void-model"
    assert payload["offellia_judge"]["repo_id"] == "Brunobkr/OFFELLIA_Q4_0_gemma-4-12B-it.gguf"
    assert payload["audio_lore_tts"]["repo_id"] == "hexgrad/Kokoro-82M"
    assert payload["tiny_titan_sidecar"]["repo_id"] == "black-forest-labs/FLUX.2-klein-4B"
    assert payload["hackathon_claims"]["raven_quality_stack"] is True
    assert payload["hackathon_claims"]["locateanything_grounding"] is True
    assert payload["hackathon_claims"]["offellia_quality_lane"] is False
    assert "token" not in json.dumps(payload).lower()
    assert payload["artifact"] == "artifact.png"
    assert payload["generation"]["output_path"] == "artifact.png"
    assert "/data/" not in json.dumps(payload)


def test_export_packet_has_correct_schema_version(monkeypatch) -> None:
    monkeypatch.setenv("NEXUS_EXPORT_DIR", "outputs/test-exports")
    run = build_command_center_run("dark couture brief")
    scan = {"status": "pass", "export_gate": "clear"}
    state = _make_base_state()

    result = write_export_packet(run=run, scan=scan, operator_state=state, adult_mode=False)
    payload = json.loads(Path(result["path"]).read_text(encoding="utf-8"))

    assert payload["schema"] == "nexus_visual_weaver.export_packet.v1"


def test_export_packet_stores_adult_mode_flag(monkeypatch) -> None:
    monkeypatch.setenv("NEXUS_EXPORT_DIR", "outputs/test-exports")
    run_public = build_command_center_run("dark couture brief", adult_mode=False)
    run_private = build_command_center_run("dark couture brief", adult_mode=True)
    scan = {"status": "pass", "export_gate": "clear"}

    result_public = write_export_packet(run=run_public, scan=scan, operator_state=_make_base_state(), adult_mode=True)
    result_private = write_export_packet(run=run_private, scan=scan, operator_state=_make_base_state(), adult_mode=False)

    public_payload = json.loads(Path(result_public["path"]).read_text(encoding="utf-8"))
    private_payload = json.loads(Path(result_private["path"]).read_text(encoding="utf-8"))

    assert public_payload["adult_mode"] is False
    assert private_payload["adult_mode"] is True
    assert public_payload["model_stack"][0]["repo_id"] == run_public.model_stack[0].repo_id
    assert private_payload["model_stack"][0]["repo_id"] == run_private.model_stack[0].repo_id


def test_export_packet_removes_hf_token_from_generation(monkeypatch) -> None:
    monkeypatch.setenv("NEXUS_EXPORT_DIR", "outputs/test-exports")
    run = build_command_center_run("gothic platform boots brief")
    scan = {"status": "pass", "export_gate": "clear"}
    state = _make_base_state(
        generation={"status": "success", "output_path": "/data/artifact.png", "hf_token_present": True},
    )

    result = write_export_packet(run=run, scan=scan, operator_state=state, adult_mode=False)
    payload = json.loads(Path(result["path"]).read_text(encoding="utf-8"))

    assert "hf_token_present" not in payload["generation"]
    assert "token" not in json.dumps(payload).lower()


def test_export_packet_hackathon_claims_both_success(monkeypatch) -> None:
    monkeypatch.setenv("NEXUS_EXPORT_DIR", "outputs/test-exports")
    run = build_command_center_run("couture archivist brief")
    scan = {"status": "pass", "export_gate": "clear"}
    state = _make_base_state(
        minicpm_judge={"status": "success"},
        nemotron_evidence={"status": "success"},
    )

    result = write_export_packet(run=run, scan=scan, operator_state=state, adult_mode=False)
    payload = json.loads(Path(result["path"]).read_text(encoding="utf-8"))

    assert payload["hackathon_claims"]["openbmb_lane"] is True
    assert payload["hackathon_claims"]["nvidia_nemotron_lane"] is True
    assert payload["hackathon_claims"]["gradio_space"] is True
    assert payload["hackathon_claims"]["off_brand_custom_ui"] is True


def test_export_packet_hackathon_claims_st3gg_export_gate(monkeypatch) -> None:
    monkeypatch.setenv("NEXUS_EXPORT_DIR", "outputs/test-exports")
    run_clear = build_command_center_run("scan gate test brief clear")
    run_blocked = build_command_center_run("scan gate test brief blocked")
    scan_clear = {"status": "pass", "export_gate": "clear"}
    scan_blocked = {"status": "review", "export_gate": "blocked"}

    result_clear = write_export_packet(run=run_clear, scan=scan_clear, operator_state=_make_base_state(), adult_mode=False)
    result_blocked = write_export_packet(run=run_blocked, scan=scan_blocked, operator_state=_make_base_state(), adult_mode=False)

    payload_clear = json.loads(Path(result_clear["path"]).read_text(encoding="utf-8"))
    payload_blocked = json.loads(Path(result_blocked["path"]).read_text(encoding="utf-8"))

    assert payload_clear["hackathon_claims"]["st3gg_export_gate"] == "clear"
    assert payload_blocked["hackathon_claims"]["st3gg_export_gate"] == "blocked"


def test_export_packet_includes_model_stack_and_prompts(monkeypatch) -> None:
    monkeypatch.setenv("NEXUS_EXPORT_DIR", "outputs/test-exports")
    run = build_command_center_run("raven archivist couture brief")
    scan = {"status": "pass", "export_gate": "clear"}

    result = write_export_packet(run=run, scan=scan, operator_state=_make_base_state(), adult_mode=False)
    payload = json.loads(Path(result["path"]).read_text(encoding="utf-8"))

    assert isinstance(payload["model_stack"], list)
    assert len(payload["model_stack"]) > 0
    assert all("repo_id" in entry and "params_b" in entry for entry in payload["model_stack"])
    assert isinstance(payload["prompt"], str)
    assert isinstance(payload["refined_prompt"], str)
    assert isinstance(payload["created_at_epoch"], int)


def test_export_root_uses_nexus_export_dir_env(monkeypatch) -> None:
    custom_dir = Path("outputs/test-exports/custom_export")
    monkeypatch.setenv("NEXUS_EXPORT_DIR", str(custom_dir))

    root = export_root()

    assert root == custom_dir.resolve()
    assert root.is_dir()


def test_export_root_rejects_src_export_dir(monkeypatch) -> None:
    unsafe_dir = Path("src/nexus_visual_weaver/export-leak")
    monkeypatch.setenv("NEXUS_EXPORT_DIR", str(unsafe_dir))

    root = export_root()

    src_root = (Path.cwd() / "src").resolve()
    assert root != src_root
    assert src_root not in root.parents
    assert not unsafe_dir.exists()


def test_export_root_falls_back_to_outputs_when_no_env(monkeypatch) -> None:
    monkeypatch.delenv("NEXUS_EXPORT_DIR", raising=False)
    # Patch /data so it is not seen as existing
    import nexus_visual_weaver.exporter as exporter_mod
    original_exists = Path.exists

    def patched_exists(self):
        if str(self) == "/data":
            return False
        return original_exists(self)

    monkeypatch.setattr(Path, "exists", patched_exists)

    root = export_root()
    assert "outputs" in str(root) or "exports" in str(root)


def test_export_packet_returns_both_path_and_packet(monkeypatch) -> None:
    monkeypatch.setenv("NEXUS_EXPORT_DIR", "outputs/test-exports")
    run = build_command_center_run("return structure brief")
    scan = {"status": "pass", "export_gate": "clear"}

    result = write_export_packet(run=run, scan=scan, operator_state=_make_base_state(), adult_mode=False)

    assert "path" in result
    assert "packet" in result
    assert isinstance(result["packet"], dict)
    assert result["packet"]["schema"] == "nexus_visual_weaver.export_packet.v1"
