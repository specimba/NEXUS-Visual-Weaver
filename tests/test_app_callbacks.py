import app
from nexus_visual_weaver.planner import build_command_center_run


# --- _checkpoint_seed tests ---

def test_checkpoint_seed_parses_valid_hex_suffix() -> None:
    # "nw-" prefix + "abcdef12" -> int("abcdef12", 16) % 1_000_000
    checkpoint_id = "nw-abcdef12"
    result = app._checkpoint_seed(checkpoint_id)
    assert result == int("abcdef12", 16) % 1_000_000


def test_checkpoint_seed_handles_empty_suffix() -> None:
    assert app._checkpoint_seed("") == 0
    assert app._checkpoint_seed("nw-") == 0


def test_checkpoint_seed_handles_non_hex_suffix() -> None:
    # No hex chars -> return 0
    result = app._checkpoint_seed("nw-zzzzzzzz")
    assert result == 0


def test_checkpoint_seed_ignores_non_hex_chars_in_last_8() -> None:
    # Strips non-hex: "abc-xyz" -> only "abcef" are hex in the last 8 chars ("-xyz" strips to "abc")
    # "0000000g" -> only "0000000" are valid hex
    result = app._checkpoint_seed("0000000g")
    assert result == int("0000000", 16) % 1_000_000
    assert result == 0


def test_checkpoint_seed_returns_value_within_range() -> None:
    checkpoint_id = "nw-deadbeef"
    result = app._checkpoint_seed(checkpoint_id)
    assert 0 <= result < 1_000_000


def test_checkpoint_seed_uses_only_last_8_chars() -> None:
    # Long checkpoint id: only last 8 chars considered
    # "nw-aabbccddee11223344" -> last 8 is "11223344"
    result = app._checkpoint_seed("nw-aabbccddee11223344")
    assert result == int("11223344", 16) % 1_000_000


# --- _wardrobe_summary tests ---

def test_wardrobe_summary_returns_string_with_slot_fields() -> None:
    run = build_command_center_run("gothic patent leather platform boots, crimson hardware")
    summary = app._wardrobe_summary(run)

    # Summary is a semicolon-delimited string of slot info
    assert isinstance(summary, str)
    assert len(summary) > 0
    # Should contain material= and palette= from slot info
    assert "material=" in summary
    assert "palette=" in summary
    assert "locked=" in summary


def test_wardrobe_summary_handles_run_with_no_outfit() -> None:
    class FakeRun:
        outfit = None

    summary = app._wardrobe_summary(FakeRun())
    assert summary == ""


def test_wardrobe_summary_handles_none_run() -> None:
    # Pass something with no outfit attribute
    class Empty:
        pass

    summary = app._wardrobe_summary(Empty())
    assert summary == ""


def test_wardrobe_summary_includes_slot_names() -> None:
    run = build_command_center_run("dark couture archivist, patent leather, platform boots")
    summary = app._wardrobe_summary(run)

    # Slot names like footwear, outerwear, upper_body should appear
    assert any(slot_name in summary for slot_name in ["footwear", "outerwear", "upper_body", "jewelry"])


def test_run_weave_returns_stateful_dashboard_packet() -> None:
    result = app.run_weave(
        "gothic patent leather platform boots, crimson hardware",
        "Strict",
        "Wan2.2 I2V",
        False,
        None,
        "Forge",
    )

    assert len(result) == 17
    assert result[13].checkpoint.checkpoint_id.startswith("nw-")
    assert result[15]["provider_state"] == "checkpointed"
    assert result[16]["interactive"] is True
    assert result[15]["creator_controls"]["wardrobe"]["footwear"] == "platform boots"
    assert result[15]["generation"]["lora_status"] == "disabled"


def test_run_weave_persists_additive_creator_controls_and_reference_url_metadata() -> None:
    result = app.run_weave(
        "gothic patent leather platform boots, crimson hardware",
        "Frontier",
        "LTX-2.3",
        False,
        None,
        "Wardrobe",
        "layered tactical silhouette",
        "faux fur collar coat",
        "black mesh layer",
        "patent leather heels",
        "obsidian, pearl, crimson",
        "silver occult buckles",
        "https://shop.example.test/item/123",
    )

    state = result[15]
    run = result[13]

    assert state["creator_controls"]["reasoning_mode"] == "Frontier"
    assert state["creator_controls"]["wardrobe"]["footwear"] == "patent leather heels"
    assert state["reference_metadata"][0]["source"] == "url"
    assert state["reference_metadata"][0]["domain"] == "shop.example.test"
    assert "url_hash" in state["reference_metadata"][0]
    assert run.request.creator_controls["wardrobe"]["outerwear"] == "faux fur collar coat"


def test_operator_actions_transition_checkpoint_export_and_stop() -> None:
    from pathlib import Path

    result = app.run_weave(
        "gothic patent leather platform boots, crimson hardware",
        "Strict",
        "Wan2.2 I2V",
        False,
        None,
        "Forge",
    )
    run = result[13]
    artifact_path = Path("outputs/test-generated-artifact.png")
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    operator_state = {**result[15], "generation": {**result[15]["generation"], "output_path": str(artifact_path)}}
    clean_scan = {"status": "pass", "export_gate": "clear", "findings": [], "purification_actions": []}

    approved = app.approve_checkpoint(run, False, clean_scan, "Forge", operator_state)
    assert approved[13]["checkpoint"] == "approved"
    assert approved[13]["provider_state"] == "export_ready"

    exported = app.export_packet(run, False, clean_scan, "Forge", approved[13])
    assert exported[13]["provider_state"] == "exported"
    assert exported[13]["export"] == "clear"

    stopped = app.stop_provider_job(run, False, clean_scan, "Forge", operator_state)
    assert stopped[13]["provider_state"] == "stopped"


def test_clear_export_ignores_stale_override_reason(monkeypatch) -> None:
    monkeypatch.setenv("NEXUS_EXPORT_DIR", "outputs/test-exports")
    result = app.run_weave(
        "gothic patent leather platform boots, crimson hardware",
        "Strict",
        "Wan2.2 I2V",
        False,
        None,
        "Forge",
    )
    run = result[13]
    artifact_path = app.ROOT / "outputs" / "test-clear-override-artifact.png"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIEND\xaeB`\x82")
    operator_state = {
        **result[15],
        "generation": {**result[15]["generation"], "output_path": str(artifact_path)},
    }
    clean_scan = {"status": "pass", "export_gate": "clear", "findings": [], "purification_actions": []}

    approved = app.approve_checkpoint(run, False, clean_scan, "Forge", operator_state)
    exported = app.export_packet(run, False, clean_scan, "Forge", approved[13], "stale text from prior blocked run")

    assert exported[13]["provider_state"] == "exported"
    assert exported[13]["export"] == "clear"
    assert "st3gg_override_reason" not in exported[13]


def test_export_blocks_without_checkpoint() -> None:
    result = app.run_weave(
        "gothic patent leather platform boots, crimson hardware",
        "Strict",
        "Wan2.2 I2V",
        False,
        None,
        "Forge",
    )
    clean_scan = {"status": "pass", "export_gate": "clear", "findings": [], "purification_actions": []}

    blocked = app.export_packet(result[13], False, clean_scan, "Forge", result[15])

    assert blocked[13]["provider_state"] == "blocked"
    assert "checkpoint" in blocked[13]["message"].lower()


def test_reference_scan_cannot_clear_blocked_generated_artifact() -> None:
    base = app.ROOT / "outputs" / "test-app-callbacks"
    base.mkdir(parents=True, exist_ok=True)
    blocked_artifact = base / "blocked-generated.png"
    blocked_artifact.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIEND\xaeB`\x82"
        b"NEXUS_TRAILING_PAYLOAD"
    )
    clean_reference = base / "clean-reference.png"
    clean_reference.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIEND\xaeB`\x82")
    run = build_command_center_run("gothic patent leather platform boots")
    state = {
        "provider_state": "checkpointed",
        "checkpoint": "pending_review",
        "export": "blocked",
        "generation": {"status": "success", "output_path": str(blocked_artifact)},
        "generated_scan": app.scan_file(str(blocked_artifact)),
    }

    scanned = app.scan_reference(run, False, str(clean_reference), "Forge", state)
    assert scanned[13]["reference_scan"]["export_gate"] == "clear"
    assert scanned[13]["export"] == "blocked"
    assert scanned[15]["export_gate"] == "blocked"

    approved = app.approve_checkpoint(run, False, scanned[15], "Forge", scanned[13])
    assert approved[13]["provider_state"] == "checkpointed"
    assert approved[13]["export"] == "blocked"


def test_blocked_reference_scan_does_not_block_clear_generated_artifact() -> None:
    base = app.ROOT / "outputs" / "test-app-callbacks"
    base.mkdir(parents=True, exist_ok=True)
    generated = base / "clear-generated.png"
    generated.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIEND\xaeB`\x82")
    blocked_reference = base / "blocked-reference.png"
    blocked_reference.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIEND\xaeB`\x82"
        b"NEXUS_TRAILING_PAYLOAD"
    )
    run = build_command_center_run("gothic patent leather platform boots")
    state = {
        "provider_state": "checkpointed",
        "checkpoint": "pending_review",
        "export": "clear",
        "generation": {"status": "success", "output_path": str(generated)},
        "generated_scan": app.scan_file(str(generated)),
    }

    scanned = app.scan_reference(run, False, str(blocked_reference), "Forge", state)
    assert scanned[13]["reference_scan"]["export_gate"] == "blocked"
    assert scanned[13]["export"] == "clear"
    assert scanned[15]["export_gate"] == "clear"

    approved = app.approve_checkpoint(run, False, scanned[15], "Forge", scanned[13])
    assert approved[13]["provider_state"] == "export_ready"
    assert approved[13]["export"] == "clear"


def test_checkpoint_blocks_without_generated_artifact() -> None:
    result = app.run_weave(
        "gothic patent leather platform boots, crimson hardware",
        "Strict",
        "Wan2.2 I2V",
        False,
        None,
        "Forge",
    )
    clean_scan = {"status": "pass", "export_gate": "clear", "findings": [], "purification_actions": []}

    blocked = app.approve_checkpoint(result[13], False, clean_scan, "Forge", result[15])

    assert blocked[13]["provider_state"] == "blocked"
    assert "no generated artifact" in blocked[13]["message"].lower()


# --- _safe_file_hash tests ---

def test_safe_file_hash_returns_sha256_and_size_for_valid_file() -> None:
    import hashlib
    from pathlib import Path

    path = app.ROOT / "outputs" / "test-hash-target.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    path.write_bytes(data)

    file_hash, size = app._safe_file_hash(str(path))

    assert file_hash == hashlib.sha256(data).hexdigest()
    assert size == len(data)


def test_safe_file_hash_returns_none_for_none_path() -> None:
    assert app._safe_file_hash(None) == (None, None)


def test_safe_file_hash_returns_none_for_empty_string() -> None:
    assert app._safe_file_hash("") == (None, None)


def test_safe_file_hash_returns_none_for_missing_file() -> None:
    result = app._safe_file_hash("/nonexistent/path/no-such-file.png")
    assert result == (None, None)


def test_safe_file_hash_hash_is_64_hex_chars() -> None:
    from pathlib import Path

    path = app.ROOT / "outputs" / "test-hash-hex.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x01" * 8)

    file_hash, _ = app._safe_file_hash(str(path))

    assert file_hash is not None
    assert len(file_hash) == 64
    assert all(c in "0123456789abcdef" for c in file_hash)


# --- _safe_reference_url_metadata tests ---

def test_safe_reference_url_metadata_returns_none_for_falsy() -> None:
    assert app._safe_reference_url_metadata(None) is None
    assert app._safe_reference_url_metadata("") is None


def test_safe_reference_url_metadata_returns_metadata_for_valid_https_url() -> None:
    result = app._safe_reference_url_metadata("https://shop.example.test/item/123")

    assert result is not None
    assert result["status"] == "metadata_only"
    assert result["domain"] == "shop.example.test"
    assert "url_hash" in result
    assert len(result["url_hash"]) == 64


def test_safe_reference_url_metadata_returns_metadata_for_valid_http_url() -> None:
    result = app._safe_reference_url_metadata("http://example.test/path?q=1")

    assert result is not None
    assert result["status"] == "metadata_only"
    assert result["domain"] == "example.test"


def test_safe_reference_url_metadata_rejects_file_scheme() -> None:
    result = app._safe_reference_url_metadata("file:///etc/passwd")

    assert result is not None
    assert result["status"] == "invalid_url"


def test_safe_reference_url_metadata_rejects_ftp_scheme() -> None:
    result = app._safe_reference_url_metadata("ftp://ftp.example.test/file.txt")

    assert result is not None
    assert result["status"] == "invalid_url"


def test_safe_reference_url_metadata_rejects_missing_host() -> None:
    result = app._safe_reference_url_metadata("http:///no-host")

    assert result is not None
    assert result["status"] == "invalid_url"


def test_safe_reference_url_metadata_domain_is_lowercase() -> None:
    result = app._safe_reference_url_metadata("https://SHOP.EXAMPLE.TEST/Item/123")

    assert result is not None
    assert result["domain"] == "shop.example.test"


def test_safe_reference_url_metadata_url_hash_is_stable() -> None:
    url = "https://shop.example.test/stable-hash-test"
    first = app._safe_reference_url_metadata(url)
    second = app._safe_reference_url_metadata(url)

    assert first is not None and second is not None
    assert first["url_hash"] == second["url_hash"]


def test_safe_reference_url_metadata_different_urls_produce_different_hashes() -> None:
    url_a = "https://shop.example.test/item/1"
    url_b = "https://shop.example.test/item/2"

    result_a = app._safe_reference_url_metadata(url_a)
    result_b = app._safe_reference_url_metadata(url_b)

    assert result_a is not None and result_b is not None
    assert result_a["url_hash"] != result_b["url_hash"]


# --- _reference_metadata tests ---

def test_reference_metadata_returns_empty_for_no_inputs() -> None:
    scan = {"status": "pass", "export_gate": "clear"}
    result = app._reference_metadata(None, None, scan)

    assert result == []


def test_reference_metadata_includes_file_record_when_uploaded() -> None:
    from pathlib import Path

    path = app.ROOT / "outputs" / "test-ref-meta.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 16)
    scan = {"status": "pass", "export_gate": "clear", "magic": "PNG", "extension": ".png"}

    result = app._reference_metadata(str(path), None, scan)

    assert len(result) == 1
    assert result[0]["source"] == "upload"
    assert result[0]["basename"] == "test-ref-meta.png"
    assert result[0]["sha256"] is not None
    assert result[0]["st3gg_status"] == "pass"
    assert result[0]["export_gate"] == "clear"
    assert result[0]["magic"] == "PNG"
    assert result[0]["extension"] == ".png"


def test_reference_metadata_includes_url_record_when_url_given() -> None:
    scan = {}
    result = app._reference_metadata(None, "https://shop.example.test/item/99", scan)

    assert len(result) == 1
    assert result[0]["source"] == "url"
    assert result[0]["domain"] == "shop.example.test"


def test_reference_metadata_includes_both_file_and_url() -> None:
    from pathlib import Path

    path = app.ROOT / "outputs" / "test-ref-both.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIEND\xaeB`\x82")
    scan = {"status": "pass", "export_gate": "clear"}

    result = app._reference_metadata(str(path), "https://shop.example.test/item/77", scan)

    assert len(result) == 2
    sources = {r["source"] for r in result}
    assert sources == {"upload", "url"}


def test_reference_metadata_size_bytes_is_integer() -> None:
    from pathlib import Path

    data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 24
    path = app.ROOT / "outputs" / "test-ref-size.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    scan = {}

    result = app._reference_metadata(str(path), None, scan)

    assert result[0]["size_bytes"] == len(data)


# --- _creator_controls tests ---

def test_creator_controls_returns_dict_with_wardrobe_and_generation() -> None:
    result = app._creator_controls("Strict", "Wan2.2 I2V")

    assert "wardrobe" in result
    assert "generation" in result
    assert result["reasoning_mode"] == "Strict"
    assert result["video_preset"] == "Wan2.2 I2V"


def test_creator_controls_default_wardrobe_values() -> None:
    result = app._creator_controls("Strict", "Wan2.2 I2V")
    wardrobe = result["wardrobe"]

    assert wardrobe["footwear"] == "platform boots"
    assert wardrobe["outerwear"] == "black patent leather long coat"
    assert wardrobe["palette"] == "black, crimson, cyan neon"


def test_creator_controls_overrides_wardrobe_slots() -> None:
    result = app._creator_controls(
        "Frontier",
        "LTX-2.3",
        footwear="patent leather heels",
        outerwear="faux fur collar coat",
        palette="obsidian, pearl, crimson",
    )
    wardrobe = result["wardrobe"]

    assert wardrobe["footwear"] == "patent leather heels"
    assert wardrobe["outerwear"] == "faux fur collar coat"
    assert wardrobe["palette"] == "obsidian, pearl, crimson"


def test_creator_controls_locked_slots_present() -> None:
    result = app._creator_controls("Strict", "Wan2.2 I2V")
    wardrobe = result["wardrobe"]

    assert "locked_slots" in wardrobe
    assert isinstance(wardrobe["locked_slots"], list)
    assert "outerwear" in wardrobe["locked_slots"]


def test_creator_controls_generation_specifies_flux_primary() -> None:
    result = app._creator_controls("Strict", "Wan2.2 I2V")
    generation = result["generation"]

    assert "black-forest-labs/FLUX.2-klein-9B" in generation["flux_primary"]
    assert "black-forest-labs/FLUX.2-klein-4B" in generation["flux_sidecar"]


# --- _prompt_with_controls tests ---

def test_prompt_with_controls_appends_wardrobe_suffix() -> None:
    controls = app._creator_controls("Strict", "Wan2.2 I2V", footwear="platform boots")
    result = app._prompt_with_controls("gothic couture portrait", controls)

    assert result.startswith("gothic couture portrait")
    assert "Wardrobe controls:" in result
    assert "platform boots" in result


def test_prompt_with_controls_returns_prompt_unchanged_when_no_wardrobe() -> None:
    # A controls dict with no wardrobe key
    result = app._prompt_with_controls("gothic couture portrait", {})

    assert result == "gothic couture portrait"


def test_prompt_with_controls_includes_all_wardrobe_fields() -> None:
    controls = app._creator_controls(
        "Strict",
        "Wan2.2 I2V",
        silhouette="structured long coat",
        outerwear="black patent leather long coat",
        upper_body="Chantilly lace neckline",
        footwear="platform boots",
        palette="black, crimson, cyan neon",
        hardware="crimson hardware",
    )
    result = app._prompt_with_controls("brief", controls)

    assert "structured long coat" in result
    assert "black patent leather long coat" in result
    assert "Chantilly lace neckline" in result
    assert "platform boots" in result
    assert "crimson hardware" in result


def test_prompt_with_controls_does_not_duplicate_prompt() -> None:
    controls = app._creator_controls("Strict", "Wan2.2 I2V")
    prompt = "gothic couture brief"
    result = app._prompt_with_controls(prompt, controls)

    assert result.count(prompt) == 1


# --- _generated_output_path tests ---

def test_generated_output_path_returns_none_when_no_state() -> None:
    assert app._generated_output_path(None) is None


def test_generated_output_path_returns_none_when_no_generation_key() -> None:
    assert app._generated_output_path({"provider_state": "idle"}) is None


def test_generated_output_path_returns_none_when_no_output_path() -> None:
    state = {"generation": {"status": "disabled"}}
    assert app._generated_output_path(state) is None


def test_generated_output_path_returns_string_when_present() -> None:
    state = {"generation": {"output_path": "/data/artifact.png"}}
    result = app._generated_output_path(state)

    assert result == "/data/artifact.png"


def test_generated_output_path_returns_none_for_empty_path() -> None:
    state = {"generation": {"output_path": ""}}
    assert app._generated_output_path(state) is None


# --- _authoritative_generated_scan tests ---

def test_authoritative_generated_scan_returns_default_for_no_state() -> None:
    result = app._authoritative_generated_scan(None)

    assert isinstance(result, dict)
    assert "status" in result


def test_authoritative_generated_scan_scans_output_path_when_present() -> None:
    from pathlib import Path

    path = app.ROOT / "outputs" / "test-auth-scan.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIEND\xaeB`\x82")
    state = {"generation": {"output_path": str(path)}}

    result = app._authoritative_generated_scan(state)

    assert result["status"] in {"pass", "review"}
    assert "export_gate" in result


def test_authoritative_generated_scan_falls_back_to_stored_scan() -> None:
    stored_scan = {"status": "review", "export_gate": "blocked", "findings": ["trailing data"]}
    state = {"generated_scan": stored_scan}

    result = app._authoritative_generated_scan(state)

    assert result == stored_scan


def test_authoritative_generated_scan_uses_output_path_over_stored_scan() -> None:
    from pathlib import Path

    path = app.ROOT / "outputs" / "test-auth-scan-prefer.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIEND\xaeB`\x82")
    stale_scan = {"status": "review", "export_gate": "blocked"}
    state = {
        "generation": {"output_path": str(path)},
        "generated_scan": stale_scan,
    }

    result = app._authoritative_generated_scan(state)

    # Should re-scan from file, not use stored scan
    assert result["status"] == "pass"
    assert result["export_gate"] == "clear"


def test_export_packet_allows_blocked_st3gg_with_explicit_override(monkeypatch) -> None:
    monkeypatch.setenv("NEXUS_EXPORT_DIR", "outputs/test-exports")
    run = build_command_center_run("gothic patent leather platform boots")
    blocked_scan = {
        "status": "review",
        "export_gate": "blocked",
        "findings": ["metadata review"],
        "purification_actions": ["strip metadata"],
    }
    state = {
        **app._default_operator_state(),
        "checkpoint": "approved",
        "provider_state": "generated",
        "generated_scan": blocked_scan,
        "generation": {
            "status": "success",
            "provider_state": "generated",
            "output_path": "outputs/runtime/nexus_flux_test.png",
            "lora_status": "skipped_incompatible",
        },
    }

    blocked = app.export_packet(run, False, blocked_scan, "Forge", state, "")
    assert blocked[13]["provider_state"] == "blocked"
    assert "override reason" in blocked[13]["message"].lower()

    exported = app.export_packet(run, False, blocked_scan, "Forge", state, "Operator reviewed ST3GG and wrote audit evidence only.")
    assert exported[13]["provider_state"] == "exported"
    assert exported[13]["export"] == "override"
    assert "export_packet" in exported[13]
