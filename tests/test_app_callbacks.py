import app


def test_default_operator_state_has_correct_structure() -> None:
    state = app._default_operator_state()

    assert state["provider_state"] == "idle"
    assert state["checkpoint"] == "pending"
    assert state["export"] == "pending"
    assert "message" in state
    assert "No operator action" in state["message"]


def test_zero_gpu_entrypoint_returns_fn_unchanged_when_spaces_none() -> None:
    original_spaces = app.spaces
    app.spaces = None

    def my_fn(x: int) -> int:
        return x * 2

    wrapped = app._zero_gpu_entrypoint(my_fn)
    assert wrapped is my_fn
    assert wrapped(5) == 10

    app.spaces = original_spaces


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


def test_approve_checkpoint_blocks_when_run_is_none() -> None:
    blocked = app.approve_checkpoint(None, False, None, "Forge", None)

    assert blocked[13]["provider_state"] == "blocked"
    assert "No run exists yet" in blocked[13]["message"]


def test_approve_checkpoint_sets_checkpointed_when_export_gate_not_clear() -> None:
    result = app.run_weave(
        "gothic patent leather platform boots",
        "Strict",
        "Wan2.2 I2V",
        False,
        None,
        "Forge",
    )
    run = result[13]
    dirty_scan = {"status": "review", "export_gate": "blocked", "findings": ["extension mismatch"]}
    operator_state = result[15]

    approved = app.approve_checkpoint(run, False, dirty_scan, "Forge", operator_state)

    assert approved[13]["checkpoint"] == "approved"
    assert approved[13]["provider_state"] == "checkpointed"
    assert "ST3GG review" in approved[13]["message"]


def test_export_blocks_when_run_is_none() -> None:
    clean_scan = {"status": "pass", "export_gate": "clear"}

    blocked = app.export_packet(None, False, clean_scan, "Forge", None)

    assert blocked[13]["provider_state"] == "blocked"
    assert blocked[13]["export"] == "blocked"
    assert "no active run packet" in blocked[13]["message"]


def test_export_blocks_when_scan_gate_not_clear() -> None:
    result = app.run_weave(
        "gothic patent leather platform boots",
        "Strict",
        "Wan2.2 I2V",
        False,
        None,
        "Forge",
    )
    run = result[13]
    operator_state = result[15]

    # First approve the checkpoint
    clean_scan = {"status": "pass", "export_gate": "clear"}
    approved = app.approve_checkpoint(run, False, clean_scan, "Forge", operator_state)

    # Then try to export with a blocked scan
    dirty_scan = {"status": "review", "export_gate": "blocked"}
    blocked_export = app.export_packet(run, False, dirty_scan, "Forge", approved[13])

    assert blocked_export[13]["provider_state"] == "blocked"
    assert "ST3GG gate is not clear" in blocked_export[13]["message"]


def test_stop_provider_job_always_sets_stopped() -> None:
    for initial_state in [None, {"provider_state": "exported"}, {"provider_state": "checkpointed"}]:
        result = app.stop_provider_job(None, False, None, "Forge", initial_state)
        assert result[13]["provider_state"] == "stopped"
        assert "stopped" in result[13]["message"].lower()


def test_reset_demo_returns_17_tuple_with_idle_state() -> None:
    result = app.reset_demo(False, "Forge")

    assert len(result) == 17
    # result[13] is None (active_run_state reset)
    assert result[13] is None
    # result[15] is the operator_state, which should be idle
    assert result[15]["provider_state"] == "idle"
    assert result[15]["checkpoint"] == "pending"
    # result[16] is gr.update(interactive=False)
    assert result[16]["interactive"] is False


def test_reset_demo_clears_run_json_to_empty_dict() -> None:
    result = app.reset_demo(False, "Forge")

    # result[10] is run_json
    assert result[10] == {}


def test_toggle_adult_visibility_returns_10_tuple() -> None:
    result = app.toggle_adult_visibility(False, "Forge", None)

    assert len(result) == 10
    # Last element should be operator_state with adult mode message
    assert isinstance(result[9], dict)
    assert "Adult catalog visibility changed" in result[9]["message"]
    # Gates should remain active
    assert "ST3GG" in result[9]["message"]


def test_toggle_adult_visibility_adult_mode_on() -> None:
    result_off = app.toggle_adult_visibility(False, "Security", None)
    result_on = app.toggle_adult_visibility(True, "Security", None)

    # Both should return a valid 10-tuple
    assert len(result_off) == 10
    assert len(result_on) == 10
    # The topbar HTML (index 0) should differ between modes
    assert result_off[0] != result_on[0]


def test_render_stateful_stop_btn_interactive_false_for_idle_state() -> None:
    """_render_stateful should return gr.update(interactive=False) when no run exists."""
    result = app._render_stateful(
        None,
        False,
        None,
        "Forge",
        {"provider_state": "idle", "checkpoint": "pending", "export": "pending", "message": "test"},
    )

    # result[14] is the stop_btn update
    assert result[14]["interactive"] is False


def test_render_stateful_stop_btn_interactive_true_when_run_active() -> None:
    """_render_stateful returns interactive=True for stop_btn when run exists in active state."""
    from nexus_visual_weaver.planner import build_command_center_run

    run = build_command_center_run("gothic patent leather")
    operator_state = {
        "provider_state": "checkpointed",
        "checkpoint": "pending_review",
        "export": "pending",
        "message": "Run active.",
    }

    result = app._render_stateful(run, False, None, "Forge", operator_state)

    # result[14] is the stop_btn update
    assert result[14]["interactive"] is True


def test_scan_reference_updates_export_gate_in_operator_state() -> None:
    result = app.scan_reference(None, False, None, "Forge", None)

    # result[-1] is scan (the extra return value)
    assert isinstance(result[-1], dict)
    # The operator_state (result[13]) reflects the scanned export gate
    assert result[13]["export"] in {"clear", "pending", "blocked"}
