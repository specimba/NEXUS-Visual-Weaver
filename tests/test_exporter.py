import json
from pathlib import Path

from nexus_visual_weaver.exporter import export_root, write_export_packet
from nexus_visual_weaver.planner import build_command_center_run


def _make_base_state(**overrides):
    """
    Create a test operator state payload with optional field overrides.
    
    Parameters:
    	**overrides: Fields to override in the base state dictionary.
    
    Returns:
    	dict: A dictionary containing operator state data for export packet testing.
    """
    state = {
        "provider_state": "export_ready",
        "checkpoint": "approved",
        "message": "approved",
        "generation": {
            "status": "success",
            "provider_state": "generated",
            "output_path": "/data/artifact.png",
            "hf_token_present": True,
            "lora_status": "loaded",
            "lora_repo_id": "DeverStyle/Flux.2-Klein-Loras",
            "lora_message": "Adapter loaded and applied for this generation.",
        },
        "creator_controls": {
            "reasoning_mode": "Strict",
            "wardrobe": {"outerwear": "black patent leather long coat", "footwear": "platform boots"},
        },
        "reference_metadata": [
            {
                "source": "upload",
                "basename": "C:/Users/speci.000/Downloads/reference.png",
                "sha256": "a" * 64,
                "size_bytes": 128,
                "st3gg_status": "pass",
                "export_gate": "clear",
            }
        ],
        "minicpm_judge": {"status": "success", "repo_id": "openbmb/MiniCPM-V-4.6"},
        "nemotron_evidence": {"status": "missing_secret", "repo_id": "nvidia/NVIDIA-Nemotron-Parse-v1.2"},
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
    assert "token" not in json.dumps(payload).lower()
    assert payload["artifact"] == "artifact.png"
    assert payload["image_basename"] == "artifact.png"
    assert payload["generation"]["output_path"] == "artifact.png"
    assert payload["lora_status"]["status"] == "loaded"
    assert payload["creator_controls"]["wardrobe"]["footwear"] == "platform boots"
    assert payload["reference_metadata"][0]["basename"] == "reference.png"
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
        """
        Custom exists check that treats "/data" as non-existent.
        
        Returns:
        	False if the path is "/data", otherwise the original exists check result.
        """
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


def test_export_packet_redacts_raw_payload_paths_and_secret_like_values(monkeypatch) -> None:
    monkeypatch.setenv("NEXUS_EXPORT_DIR", "outputs/test-exports")
    run = build_command_center_run(
        "redaction brief",
        creator_controls={"wardrobe": {"footwear": "platform boots"}},
        reference_metadata=[{"source": "url", "domain": "shop.example.test", "url_hash": "b" * 64}],
    )
    scan = {
        "status": "review",
        "export_gate": "blocked",
        "payload_excerpt": "hf_" + "abcdefghijklmnopqrstuvwxyz123456",
        "findings": ["raw hidden bytes at C:/Users/speci.000/Downloads/thing.png"],
        "purification_actions": ["base64 payload removed from /data/nexus_visual_weaver/artifact.png"],
    }
    state = _make_base_state(
        generation={
            "status": "success",
            "provider_state": "generated",
            "output_path": "/data/nexus_visual_weaver/artifact.png",
            "hf_token_present": True,
            "lora_status": "failed",
            "lora_repo_id": "example/lora",
            "lora_message": "RuntimeError: failed without token value",
        },
        minicpm_judge={
            "status": "failed",
            "provider_state": "failed",
            "provider": "OpenBMB",
            "repo_id": "openbmb/MiniCPM-V-4.6",
            "model": "MiniCPM-V-4.6",
            "message": "Set MINICPM_API_KEY in Space secrets.",
            "evidence": {"raw_summary": "Bearer " + "secret-value", "configured": True},
        },
        reference_metadata=[
            {
                "source": "upload",
                "basename": "C:/Users/speci.000/Downloads/reference.png",
                "sha256": "c" * 64,
                "size_bytes": 2048,
                "st3gg_status": "review",
                "export_gate": "blocked",
            }
        ],
    )

    result = write_export_packet(run=run, scan=scan, operator_state=state, adult_mode=False)
    payload = json.loads(Path(result["path"]).read_text(encoding="utf-8"))
    serialized = json.dumps(payload)

    assert "payload_excerpt" not in serialized
    assert "raw_summary" not in serialized
    assert "Bearer " + "secret-value" not in serialized
    assert "MINICPM_API_KEY" not in serialized
    assert "/data/" not in serialized
    assert "C:/Users/speci.000/Downloads" not in serialized
    assert payload["st3gg_verdict"] == {"status": "review", "export_gate": "blocked"}
    assert payload["provider_states"]["minicpm"] == "failed"


def test_export_packet_redacts_windows_backslash_paths_on_linux(monkeypatch) -> None:
    monkeypatch.setenv("NEXUS_EXPORT_DIR", "outputs/test-exports")
    run = build_command_center_run("redaction brief")
    scan = {
        "status": "review",
        "export_gate": "blocked",
        "findings": [r"raw hidden bytes at C:\Users\speci.000\Downloads\thing.png"],
        "purification_actions": [],
    }
    state = _make_base_state()

    result = write_export_packet(run=run, scan=scan, operator_state=state, adult_mode=False)
    payload = json.loads(Path(result["path"]).read_text(encoding="utf-8"))
    serialized = json.dumps(payload)

    assert r"C:\Users\speci.000\Downloads" not in serialized
    assert "[local_path]/thing.png" in serialized


def test_export_packet_records_st3gg_override_reason(monkeypatch) -> None:
    monkeypatch.setenv("NEXUS_EXPORT_DIR", "outputs/test-exports")
    run = build_command_center_run("gothic patent leather platform boots")
    scan = {"status": "review", "export_gate": "blocked", "findings": ["metadata review"], "purification_actions": ["strip metadata"]}
    state = _make_base_state(
        st3gg_override_reason="Operator reviewed the ST3GG findings and is writing an audit packet only.",
        export="override",
    )

    result = write_export_packet(run=run, scan=scan, operator_state=state, adult_mode=False)
    payload = json.loads(Path(result["path"]).read_text(encoding="utf-8"))

    assert payload["st3gg_verdict"] == {"status": "review", "export_gate": "blocked"}
    assert payload["st3gg_override"] == {
        "used": True,
        "reason": "Operator reviewed the ST3GG findings and is writing an audit packet only.",
    }
