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
