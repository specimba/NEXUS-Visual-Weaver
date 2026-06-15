from PIL import Image
from pathlib import Path

from nexus_visual_weaver.provider_runtime import (
    NEMOTRON_NANO_REPO_ID,
    NEMOTRON_PARSE_REPO_ID,
    OPENBMB_REPO_ID,
    ProviderJudgeResult,
    _extract_content,
    _image_data_url,
    _post_json,
    _safe_json_from_text,
    _safe_provider_payload,
    _short_error,
    judge_with_minicpm,
    judge_with_nemotron,
)


RUNTIME_FIXTURE_DIR = Path("tests/fixtures/runtime")


def _runtime_fixture_path(name: str) -> Path:
    RUNTIME_FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    return RUNTIME_FIXTURE_DIR / name


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
    image = _runtime_fixture_path("test-provider-artifact.png")
    Image.new("RGB", (8, 8), color=(12, 16, 20)).save(image)
    monkeypatch.setenv("MINICPM_BASE_URL", "http://example.test")
    monkeypatch.setenv("MINICPM_API_KEY", "test-token")

    def fake_post(url, token, payload, timeout):
        assert url == "http://example.test/v1/chat/completions"
        assert token == "test-token"
        assert payload["messages"][0]["content"][1]["image_url"]["url"].startswith("data:image/png;base64,")
        return {"choices": [{"message": {"content": '{"overall_status":"pass","footwear_check":"visible"}'}}]}

    monkeypatch.setattr("nexus_visual_weaver.provider_runtime._post_json", fake_post)

    try:
        result = judge_with_minicpm(
            prompt="gothic couture",
            image_path=str(image),
            scan={"export_gate": "clear"},
            wardrobe_summary="boots and lace",
        )
    finally:
        image.unlink(missing_ok=True)

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


# --- _short_error tests ---

def test_short_error_prefixes_class_name() -> None:
    exc = ValueError("something went wrong")
    result = _short_error(exc)
    assert result.startswith("ValueError:")
    assert "something went wrong" in result


def test_short_error_truncates_long_messages() -> None:
    long_message = "x" * 500
    exc = RuntimeError(long_message)
    result = _short_error(exc)
    assert len(result) <= len("RuntimeError: ") + 360
    assert result.endswith("...")


def test_short_error_collapses_newlines() -> None:
    exc = OSError("line one\nline two\nline three")
    result = _short_error(exc)
    assert "\n" not in result
    assert "line one" in result


# --- _image_data_url tests ---

def test_image_data_url_returns_none_for_none_path() -> None:
    assert _image_data_url(None) is None


def test_image_data_url_returns_none_for_missing_file() -> None:
    assert _image_data_url("/nonexistent/path/to/image.png") is None


def test_image_data_url_encodes_png_as_base64() -> None:
    image_path = _runtime_fixture_path("test-img-data-url.png")
    Image.new("RGB", (4, 4), color=(0, 0, 0)).save(image_path)

    try:
        result = _image_data_url(str(image_path))
    finally:
        image_path.unlink(missing_ok=True)

    assert result is not None
    assert result.startswith("data:image/png;base64,")


def test_image_data_url_uses_jpeg_mime_for_jpg() -> None:
    image_path = _runtime_fixture_path("test-img-data-url.jpg")
    Image.new("RGB", (4, 4), color=(0, 0, 0)).save(image_path)

    try:
        result = _image_data_url(str(image_path))
    finally:
        image_path.unlink(missing_ok=True)

    assert result is not None
    assert result.startswith("data:image/jpeg;base64,")


def test_image_data_url_rejects_unknown_suffix() -> None:
    image_path = _runtime_fixture_path("not-an-image.txt")
    image_path.write_text("not an image", encoding="utf-8")

    try:
        assert _image_data_url(str(image_path)) is None
    finally:
        image_path.unlink(missing_ok=True)


def test_image_data_url_rejects_oversized_file(monkeypatch) -> None:
    image_path = _runtime_fixture_path("large.png")
    image_path.write_bytes(b"not actually decoded because size fails")
    monkeypatch.setattr("nexus_visual_weaver.provider_runtime.MAX_PROVIDER_IMAGE_BYTES", 4)

    try:
        assert _image_data_url(str(image_path)) is None
    finally:
        image_path.unlink(missing_ok=True)


# --- _extract_content tests ---

def test_extract_content_returns_string_from_choices() -> None:
    response = {"choices": [{"message": {"content": "hello world"}}]}
    assert _extract_content(response) == "hello world"


def test_extract_content_returns_empty_for_no_choices() -> None:
    assert _extract_content({"choices": []}) == ""
    assert _extract_content({}) == ""


def test_extract_content_serializes_non_string_content() -> None:
    response = {"choices": [{"message": {"content": {"key": "value"}}}]}
    result = _extract_content(response)
    assert "key" in result
    assert "value" in result


# --- _safe_json_from_text tests ---

def test_safe_json_from_text_parses_valid_json() -> None:
    text = '{"status": "pass", "score": 0.9}'
    result = _safe_json_from_text(text)
    assert result == {"status": "pass", "score": 0.9}


def test_safe_json_from_text_returns_empty_dict_for_empty_string() -> None:
    assert _safe_json_from_text("") == {}
    assert _safe_json_from_text("   ") == {}


def test_safe_json_from_text_falls_back_on_invalid_json() -> None:
    text = "this is not valid json"
    result = _safe_json_from_text(text)
    assert "raw_summary" in result
    assert "this is not valid json" in result["raw_summary"]


def test_safe_json_from_text_extracts_embedded_json() -> None:
    text = 'Some prefix text {"result": "ok"} trailing text'
    result = _safe_json_from_text(text)
    assert result == {"result": "ok"}


def test_safe_json_from_text_truncates_fallback_to_1200_chars() -> None:
    long_text = "not json " + "x" * 2000
    result = _safe_json_from_text(long_text)
    assert "raw_summary" in result
    assert len(result["raw_summary"]) <= 1200


# --- ProviderJudgeResult.to_dict tests ---

def test_provider_judge_result_to_dict_contains_all_fields() -> None:
    result = ProviderJudgeResult(
        status="success",
        provider_state="configured",
        provider="OpenBMB",
        repo_id=OPENBMB_REPO_ID,
        model="MiniCPM-V-4.6",
        message="judge returned evidence",
        evidence={"overall_status": "pass"},
        latency_seconds=1.23,
    )
    d = result.to_dict()

    assert d["status"] == "success"
    assert d["provider_state"] == "configured"
    assert d["provider"] == "OpenBMB"
    assert d["repo_id"] == OPENBMB_REPO_ID
    assert d["model"] == "MiniCPM-V-4.6"
    assert d["latency_seconds"] == 1.23
    assert d["evidence"]["overall_status"] == "pass"


# --- nemotron success/failure tests ---

def test_nemotron_success_with_mocked_post(monkeypatch) -> None:
    monkeypatch.setenv("NEMOTRON_BASE_URL", "http://nemotron.test")
    monkeypatch.setenv("NEMOTRON_API_KEY", "nvidia-token")

    def fake_post(url, token, payload, timeout):
        assert "Nemotron" in payload["model"] or "nemotron" in payload["model"]
        return {"choices": [{"message": {"content": '{"final_claim_status":"pass","structured_parse":"ok"}'}}]}

    monkeypatch.setattr("nexus_visual_weaver.provider_runtime._post_json", fake_post)

    result = judge_with_nemotron(
        prompt="gothic couture brief",
        run_packet={"checkpoint": {"checkpoint_id": "nw-test-123"}},
        minicpm_result={"status": "success"},
    )

    assert result.status == "success"
    assert result.provider == "NVIDIA"
    assert result.evidence["final_claim_status"] == "pass"
    assert result.latency_seconds is not None


def test_nemotron_failed_api_call_returns_failed_status(monkeypatch) -> None:
    import urllib.error

    monkeypatch.setenv("NEMOTRON_BASE_URL", "http://nemotron.test")
    monkeypatch.setenv("NEMOTRON_API_KEY", "nvidia-token")

    def fake_post(url, token, payload, timeout):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr("nexus_visual_weaver.provider_runtime._post_json", fake_post)

    result = judge_with_nemotron(
        prompt="brief",
        run_packet={"id": "nw-fail"},
    )

    assert result.status == "failed"
    assert result.provider_state == "failed"
    assert "URLError" in result.message or "connection" in result.message.lower()
    assert result.evidence.get("configured") is True


def test_minicpm_failed_api_call_returns_failed_status(monkeypatch) -> None:
    import urllib.error

    image_path = _runtime_fixture_path("test-minicpm-fail.png")
    Image.new("RGB", (4, 4), color=(0, 0, 0)).save(image_path)
    monkeypatch.setenv("MINICPM_BASE_URL", "http://minicpm.test")
    monkeypatch.setenv("MINICPM_API_KEY", "test-token")

    def fake_post(url, token, payload, timeout):
        raise urllib.error.URLError("network unreachable")

    monkeypatch.setattr("nexus_visual_weaver.provider_runtime._post_json", fake_post)

    try:
        result = judge_with_minicpm(
            prompt="gothic couture",
            image_path=str(image_path),
            scan={"export_gate": "clear"},
            wardrobe_summary="platform boots",
        )
    finally:
        image_path.unlink(missing_ok=True)

    assert result.status == "failed"
    assert result.provider_state == "failed"
    assert result.provider == "OpenBMB"
    assert result.evidence.get("configured") is True


def test_nemotron_uses_parse_repo_id_for_parse_model(monkeypatch) -> None:
    monkeypatch.setenv("NEMOTRON_BASE_URL", "http://nemotron.test")
    monkeypatch.setenv("NEMOTRON_API_KEY", "nvidia-token")
    monkeypatch.setenv("NEMOTRON_MODEL", "nvidia/NVIDIA-Nemotron-Parse-v1.2")

    def fake_post(url, token, payload, timeout):
        return {"choices": [{"message": {"content": "{}"}}]}

    monkeypatch.setattr("nexus_visual_weaver.provider_runtime._post_json", fake_post)

    result = judge_with_nemotron(prompt="brief", run_packet={})

    assert result.repo_id == NEMOTRON_PARSE_REPO_ID


def test_nemotron_uses_nano_repo_id_for_non_parse_model(monkeypatch) -> None:
    monkeypatch.setenv("NEMOTRON_BASE_URL", "http://nemotron.test")
    monkeypatch.setenv("NEMOTRON_API_KEY", "nvidia-token")
    monkeypatch.setenv("NEMOTRON_MODEL", "nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF")

    def fake_post(url, token, payload, timeout):
        return {"choices": [{"message": {"content": "{}"}}]}

    monkeypatch.setattr("nexus_visual_weaver.provider_runtime._post_json", fake_post)

    result = judge_with_nemotron(prompt="brief", run_packet={})

    assert result.repo_id == NEMOTRON_NANO_REPO_ID


def test_minicpm_uses_openbmb_api_key_as_fallback(monkeypatch) -> None:
    monkeypatch.setenv("MINICPM_BASE_URL", "http://minicpm.test")
    monkeypatch.delenv("MINICPM_API_KEY", raising=False)
    monkeypatch.setenv("OPENBMB_API_KEY", "openbmb-fallback-token")

    image_path = _runtime_fixture_path("test-openbmb-key.png")
    Image.new("RGB", (4, 4), color=(0, 0, 0)).save(image_path)

    captured = {}

    def fake_post(url, token, payload, timeout):
        captured["token"] = token
        return {"choices": [{"message": {"content": '{"status": "ok"}'}}]}

    monkeypatch.setattr("nexus_visual_weaver.provider_runtime._post_json", fake_post)

    try:
        result = judge_with_minicpm(
            prompt="test",
            image_path=str(image_path),
            scan={},
            wardrobe_summary="",
        )
    finally:
        image_path.unlink(missing_ok=True)

    assert result.status == "success"
    assert captured["token"] == "openbmb-fallback-token"


def test_nemotron_uses_nvidia_api_key_as_fallback(monkeypatch) -> None:
    monkeypatch.setenv("NEMOTRON_BASE_URL", "http://nemotron.test")
    monkeypatch.delenv("NEMOTRON_API_KEY", raising=False)
    monkeypatch.setenv("NVIDIA_API_KEY", "nvidia-fallback-token")

    captured = {}

    def fake_post(url, token, payload, timeout):
        captured["token"] = token
        return {"choices": [{"message": {"content": "{}"}}]}

    monkeypatch.setattr("nexus_visual_weaver.provider_runtime._post_json", fake_post)

    result = judge_with_nemotron(prompt="brief", run_packet={})

    assert result.status == "success"
    assert captured["token"] == "nvidia-fallback-token"


def test_safe_provider_payload_redacts_sensitive_nested_keys() -> None:
    result = _safe_provider_payload(
        {
            "checkpoint": "ok",
            "HF_TOKEN": "should-not-leak",
            "nested": {"raw_payload": "hidden", "items": [{"base64_image": "hidden"}, {"safe": "visible"}]},
        }
    )

    assert result["checkpoint"] == "ok"
    assert result["HF_TOKEN"] == "[redacted]"
    assert result["nested"]["raw_payload"] == "[redacted]"
    assert result["nested"]["items"][0]["base64_image"] == "[redacted]"
    assert result["nested"]["items"][1]["safe"] == "visible"


def test_nemotron_redacts_run_packet_before_provider_call(monkeypatch) -> None:
    monkeypatch.setenv("NEMOTRON_BASE_URL", "http://localhost:8001")
    monkeypatch.setenv("NEMOTRON_API_KEY", "nvidia-token")
    captured = {}

    def fake_post(url, token, payload, timeout):
        captured["content"] = payload["messages"][0]["content"]
        return {"choices": [{"message": {"content": '{"final_claim_status":"pass"}'}}]}

    monkeypatch.setattr("nexus_visual_weaver.provider_runtime._post_json", fake_post)

    result = judge_with_nemotron(
        prompt="brief",
        run_packet={"safe": "visible", "api_key": "hidden-key", "nested": {"payload_bytes": "hidden-bytes"}},
        minicpm_result={"status": "success", "authorization": "hidden-auth"},
    )

    assert result.status == "success"
    assert "visible" in captured["content"]
    assert "hidden-key" not in captured["content"]
    assert "hidden-bytes" not in captured["content"]
    assert "hidden-auth" not in captured["content"]
    assert "[redacted]" in captured["content"]


def test_post_json_rejects_unsupported_url_schemes_before_urlopen(monkeypatch) -> None:
    called = False

    def fake_urlopen(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("urlopen should not be called for invalid schemes")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    for url in ["file:///tmp/payload.json", "ftp://example.test/api", "http:///missing-host"]:
        try:
            _post_json(url, "token", {"ok": True}, 1.0)
        except ValueError as exc:
            assert "Invalid URL" in str(exc)
        else:
            raise AssertionError(f"{url} should have been rejected")

    assert called is False


def test_post_json_rejects_plain_http_non_loopback_before_urlopen(monkeypatch) -> None:
    called = False

    def fake_urlopen(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("urlopen should not be called for plaintext remote provider URLs")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    try:
        _post_json("http://example.test/v1/chat/completions", "token", {"ok": True}, 1.0)
    except ValueError as exc:
        assert "HTTPS" in str(exc)
        assert "loopback" in str(exc)
    else:
        raise AssertionError("remote http provider URL should have been rejected")

    assert called is False


def test_post_json_allows_loopback_http_for_local_tests(monkeypatch) -> None:
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"ok": true}'

    def fake_urlopen(request, timeout):
        assert request.full_url == "http://127.0.0.1:8000/v1/chat/completions"
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    assert _post_json("http://127.0.0.1:8000/v1/chat/completions", "token", {"ok": True}, 1.0) == {"ok": True}
