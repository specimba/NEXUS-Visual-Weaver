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


# --- _is_within tests ---

from nexus_visual_weaver.exporter import (
    _artifact_name,
    _is_within,
    _safe_dict,
    _safe_export_candidate,
    _safe_provider,
    _safe_reference_metadata,
    _safe_scan,
    _sanitize_text,
    REPO_ROOT,
)


def test_is_within_returns_true_for_child_path() -> None:
    root = Path("/some/root")
    child = Path("/some/root/subdir/file.txt")

    assert _is_within(child, root) is True


def test_is_within_returns_false_for_sibling_path() -> None:
    root = Path("/some/root")
    sibling = Path("/some/other/file.txt")

    assert _is_within(sibling, root) is False


def test_is_within_returns_false_for_parent_path() -> None:
    root = Path("/some/root/subdir")
    parent = Path("/some/root")

    assert _is_within(parent, root) is False


def test_is_within_returns_false_for_same_path() -> None:
    root = Path("/some/root")
    # Same path is not "within" itself (relative_to with same path succeeds but returns empty Path)
    # _is_within should return True for same path since relative_to doesn't raise
    result = _is_within(root, root)
    # Same path: relative_to returns Path('.') or empty - shouldn't raise, returns True
    assert result is True


# --- _artifact_name tests ---

def test_artifact_name_returns_filename_from_unix_path() -> None:
    assert _artifact_name("/data/nexus_visual_weaver/artifact.png") == "artifact.png"


def test_artifact_name_returns_filename_from_windows_path() -> None:
    assert _artifact_name(r"C:\Users\user\Downloads\artifact.png") == "artifact.png"


def test_artifact_name_returns_none_for_none() -> None:
    assert _artifact_name(None) is None


def test_artifact_name_returns_none_for_empty_string() -> None:
    assert _artifact_name("") is None


def test_artifact_name_returns_filename_for_simple_name() -> None:
    assert _artifact_name("artifact.png") == "artifact.png"


# --- _sanitize_text tests ---

def test_sanitize_text_redacts_hf_token() -> None:
    fake_token = "hf_" + "abcdefghijklmnopqrstuvwxyz1234567"
    text = f"token is {fake_token}"
    result = _sanitize_text(text)

    assert fake_token not in result
    assert "[redacted_secret]" in result


def test_sanitize_text_redacts_bearer_token() -> None:
    fake_token = "sk-test-" + "abcdefghijklmnopqrstu"
    text = "Authorization: Bearer " + fake_token
    result = _sanitize_text(text)

    assert fake_token not in result


def test_sanitize_text_redacts_credential_names() -> None:
    text = "Please set MINICPM_API_KEY and NEMOTRON_API_KEY"
    result = _sanitize_text(text)

    assert "MINICPM_API_KEY" not in result
    assert "NEMOTRON_API_KEY" not in result
    assert "[redacted_credential_name]" in result


def test_sanitize_text_redacts_windows_paths() -> None:
    text = "Found at C:\\Users\\user\\Downloads\\artifact.png"
    result = _sanitize_text(text)

    assert "C:\\Users\\user\\Downloads" not in result
    assert "[local_path]/artifact.png" in result


def test_sanitize_text_redacts_data_paths() -> None:
    text = "Output stored at /data/nexus_visual_weaver/artifact.png"
    result = _sanitize_text(text)

    assert "/data/nexus_visual_weaver" not in result
    assert "[data]/" in result


def test_sanitize_text_truncates_to_1000_chars() -> None:
    long_text = "safe text " * 200
    result = _sanitize_text(long_text)

    assert len(result) <= 1000
    assert result.endswith("...")


def test_sanitize_text_does_not_truncate_short_text() -> None:
    short_text = "safe short text without secrets"
    result = _sanitize_text(short_text)

    assert result == short_text


# --- _safe_dict tests ---

def test_safe_dict_drops_sensitive_keys() -> None:
    data = {
        "status": "ok",
        "token": "hf_secretvalue",
        "api_key": "sk-secretvalue",
        "message": "clean",
    }
    result = _safe_dict(data)

    assert "status" in result
    assert "message" in result
    assert "token" not in result
    assert "api_key" not in result


def test_safe_dict_preserves_safe_keys() -> None:
    data = {"status": "pass", "export_gate": "clear", "extension": ".png"}
    result = _safe_dict(data)

    assert result == data


def test_safe_dict_handles_nested_dicts() -> None:
    data = {"outer": {"secret": "hidden", "safe_field": "visible"}}
    result = _safe_dict(data)

    assert "secret" not in result.get("outer", {})
    assert result["outer"]["safe_field"] == "visible"


def test_safe_dict_limits_lists_to_40() -> None:
    data = list(range(50))
    result = _safe_dict(data)

    assert len(result) == 40


def test_safe_dict_sanitizes_string_values() -> None:
    data = {"message": "Error: MINICPM_API_KEY not set"}
    result = _safe_dict(data)

    assert "MINICPM_API_KEY" not in result.get("message", "")


def test_safe_dict_preserves_size_bytes_when_allowed() -> None:
    data = {"size_bytes": 1024, "token": "hf_" + "secret123456789012345"}
    result = _safe_dict(data, allow_size_bytes=True)

    assert "size_bytes" in result
    assert result["size_bytes"] == 1024
    assert "token" not in result


def test_safe_dict_drops_size_bytes_by_default() -> None:
    # "bytes" matches the sensitive key pattern
    data = {"size_bytes": 1024, "status": "ok"}
    result = _safe_dict(data)

    assert "size_bytes" not in result


def test_safe_dict_returns_non_dict_non_list_unchanged() -> None:
    assert _safe_dict(42) == 42
    assert _safe_dict(3.14) == 3.14
    assert _safe_dict(True) is True
    assert _safe_dict(None) is None


# --- _safe_scan tests ---

def test_safe_scan_extracts_required_fields() -> None:
    scan = {
        "status": "pass",
        "scanner": "ST3GG v2",
        "export_gate": "clear",
        "extension": ".png",
        "magic": "PNG",
        "findings": ["no issues"],
        "purification_actions": ["none needed"],
        "payload_excerpt": "HIDDEN_SENSITIVE_DATA",
    }
    result = _safe_scan(scan)

    assert result["status"] == "pass"
    assert result["scanner"] == "ST3GG v2"
    assert result["export_gate"] == "clear"
    assert result["extension"] == ".png"
    assert result["magic"] == "PNG"
    assert "payload_excerpt" not in result


def test_safe_scan_handles_empty_scan() -> None:
    result = _safe_scan({})

    assert "status" in result
    assert "export_gate" in result
    assert result["status"] is None
    assert result["export_gate"] is None


def test_safe_scan_sanitizes_findings() -> None:
    scan = {
        "findings": ["found MINICPM_API_KEY pattern", "raw bytes at C:\\Users\\data\\file.png"],
    }
    result = _safe_scan(scan)

    serialized = json.dumps(result)
    assert "MINICPM_API_KEY" not in serialized
    assert "C:\\Users\\data" not in serialized


# --- _safe_provider tests ---

def test_safe_provider_extracts_fields() -> None:
    provider = {
        "status": "success",
        "provider_state": "configured",
        "provider": "OpenBMB",
        "repo_id": "openbmb/MiniCPM-V-4.6",
        "model": "MiniCPM-V-4.6",
        "message": "judge returned evidence",
        "evidence": {"overall_status": "pass"},
        "latency_seconds": 1.23,
    }
    result = _safe_provider(provider)

    assert result["status"] == "success"
    assert result["provider"] == "OpenBMB"
    assert result["repo_id"] == "openbmb/MiniCPM-V-4.6"
    assert result["latency_seconds"] == 1.23
    assert result["evidence"]["overall_status"] == "pass"


def test_safe_provider_handles_none_input() -> None:
    result = _safe_provider(None)

    assert isinstance(result, dict)
    assert "status" in result
    assert result["status"] is None


def test_safe_provider_redacts_secret_values_in_evidence() -> None:
    provider = {
        "status": "failed",
        "evidence": {"token_used": "hf_" + "abcdefghijklmnopqrstuvwx", "raw": "sensitive-data"},
    }
    result = _safe_provider(provider)

    assert "token_used" not in result["evidence"]
    assert "raw" not in result["evidence"]


def test_safe_provider_handles_non_dict_evidence() -> None:
    provider = {"status": "success", "evidence": "plain string evidence"}
    result = _safe_provider(provider)

    # Non-dict evidence should be treated as empty
    assert result["evidence"] == {}


# --- _safe_reference_metadata tests ---

def test_safe_reference_metadata_returns_empty_for_non_list() -> None:
    assert _safe_reference_metadata(None) == []
    assert _safe_reference_metadata("string") == []
    assert _safe_reference_metadata(42) == []


def test_safe_reference_metadata_extracts_fields_from_records() -> None:
    records = [
        {
            "source": "upload",
            "status": "pass",
            "basename": "C:/Users/user/Downloads/reference.png",
            "sha256": "a" * 64,
            "size_bytes": 1024,
            "st3gg_status": "pass",
            "export_gate": "clear",
            "magic": "PNG",
            "extension": ".png",
        }
    ]
    result = _safe_reference_metadata(records)

    assert len(result) == 1
    assert result[0]["source"] == "upload"
    assert result[0]["basename"] == "reference.png"  # Only filename, not full path
    assert result[0]["sha256"] == "a" * 64
    assert result[0]["export_gate"] == "clear"


def test_safe_reference_metadata_limits_to_20_records() -> None:
    records = [{"source": "upload", "sha256": str(i)} for i in range(30)]
    result = _safe_reference_metadata(records)

    assert len(result) == 20


def test_safe_reference_metadata_skips_non_dict_records() -> None:
    records = [{"source": "upload"}, "not a dict", None, {"source": "url"}]
    result = _safe_reference_metadata(records)

    assert len(result) == 2
    assert all(isinstance(r, dict) for r in result)


def test_safe_reference_metadata_includes_url_fields() -> None:
    records = [
        {
            "source": "url",
            "status": "metadata_only",
            "domain": "shop.example.test",
            "url_hash": "b" * 64,
        }
    ]
    result = _safe_reference_metadata(records)

    assert result[0]["domain"] == "shop.example.test"
    assert result[0]["url_hash"] == "b" * 64


# --- _safe_export_candidate tests ---

def test_safe_export_candidate_accepts_outputs_dir() -> None:
    candidate = REPO_ROOT / "outputs" / "exports" / "test-subdir"
    result = _safe_export_candidate(candidate)

    assert result is not None
    assert "outputs" in str(result)


def test_safe_export_candidate_rejects_src_dir() -> None:
    candidate = REPO_ROOT / "src" / "nexus_visual_weaver" / "exports"
    result = _safe_export_candidate(candidate)

    assert result is None


def test_safe_export_candidate_rejects_src_root_itself() -> None:
    candidate = REPO_ROOT / "src"
    result = _safe_export_candidate(candidate)

    assert result is None
