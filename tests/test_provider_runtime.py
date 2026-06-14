from PIL import Image

from nexus_visual_weaver.provider_runtime import judge_with_minicpm, judge_with_nemotron


def test_minicpm_reports_missing_secret(monkeypatch) -> None:
    monkeypatch.delenv("MINICPM_BASE_URL", raising=False)
    monkeypatch.delenv("MINICPM_API_KEY", raising=False)
    monkeypatch.delenv("OPENBMB_API_KEY", raising=False)

    result = judge_with_minicpm(
        prompt="gothic couture",
        image_path=None,
        scan={"export_gate": "pending"},
        wardrobe_summary="boots and lace",
    )

    assert result.status == "missing_secret"
    assert result.provider_state == "missing secret"
    assert result.repo_id == "openbmb/MiniCPM-V-4.6"


def test_minicpm_blocks_when_artifact_missing(monkeypatch) -> None:
    monkeypatch.setenv("MINICPM_BASE_URL", "http://127.0.0.1:9")
    monkeypatch.setenv("MINICPM_API_KEY", "test-token")

    result = judge_with_minicpm(
        prompt="gothic couture",
        image_path="missing.png",
        scan={"export_gate": "clear"},
        wardrobe_summary="boots and lace",
    )

    assert result.status == "no_artifact"
    assert result.provider_state == "blocked"


def test_minicpm_success_with_mocked_post(monkeypatch) -> None:
    image = "outputs/test-provider-artifact.png"
    Image.new("RGB", (8, 8), color=(12, 16, 20)).save(image)
    monkeypatch.setenv("MINICPM_BASE_URL", "http://example.test")
    monkeypatch.setenv("MINICPM_API_KEY", "test-token")

    def fake_post(url, token, payload, timeout):
        assert url == "http://example.test/v1/chat/completions"
        assert token == "test-token"
        assert payload["messages"][0]["content"][1]["image_url"]["url"].startswith("data:image/png;base64,")
        return {"choices": [{"message": {"content": '{"overall_status":"pass","footwear_check":"visible"}'}}]}

    monkeypatch.setattr("nexus_visual_weaver.provider_runtime._post_json", fake_post)

    result = judge_with_minicpm(
        prompt="gothic couture",
        image_path=image,
        scan={"export_gate": "clear"},
        wardrobe_summary="boots and lace",
    )

    assert result.status == "success"
    assert result.evidence["overall_status"] == "pass"


def test_nemotron_reports_missing_secret(monkeypatch) -> None:
    monkeypatch.delenv("NEMOTRON_BASE_URL", raising=False)
    monkeypatch.delenv("NEMOTRON_API_KEY", raising=False)
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)

    result = judge_with_nemotron(prompt="brief", run_packet={"id": "nw-test"})

    assert result.status == "missing_secret"
    assert result.provider == "NVIDIA"
    assert "Nemotron" in result.message
