import app


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
    result = app.run_weave(
        "gothic patent leather platform boots, crimson hardware",
        "Strict",
        "Wan2.2 I2V",
        False,
        None,
        "Forge",
    )
    run = result[13]
    operator_state = result[15]
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
