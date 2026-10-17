"""Unit tests for MireloTool (all HTTP mocked)."""

import os
from unittest.mock import MagicMock, patch

import pytest

from praisonai_tools.tools import mirelo_tool
from praisonai_tools.tools.mirelo_tool import (
    BASE_URL,
    MireloTool,
    mirelo_text_to_sfx,
    mirelo_video_to_sfx,
)

VIDEO_URL = "https://example.com/chase.mp4"
# Captured before the autouse fixture swaps in a fake key.
_REAL_KEY = os.getenv("MIRELO_API_KEY")


def _resp(status=200, json_data=None, headers=None):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = json_data if json_data is not None else {}
    r.headers = headers or {}
    r.text = ""
    return r


def _job(status="succeeded", outputs=None, job_id="job_1"):
    return {
        "id": job_id,
        "status": status,
        "seed": 42,
        "credits": 100,
        "errors": [],
        "urls": {"self": f"/v3/video-to-sfx/generations/{job_id}"},
        "result": {"outputs": outputs} if outputs is not None else None,
    }


def _output(*variants):
    return {
        "index": 0,
        "type": "mix",
        "variants": [
            {"index": i, "status": s, "files": {"audio": {"url": f"https://cdn.mirelo.ai/{i}.wav"}} if s == "succeeded" else None}
            for i, s in enumerate(variants)
        ],
    }


def _download():
    dl = MagicMock()
    dl.__enter__.return_value = dl
    dl.iter_content.return_value = [b"RIFF"]
    return dl


@pytest.fixture
def requests_mock():
    with patch("requests.post") as post, patch("requests.get") as get, patch.object(mirelo_tool.time, "sleep"):
        get.return_value = _download()
        yield post, get


@pytest.fixture(autouse=True)
def api_key(monkeypatch):
    monkeypatch.setenv("MIRELO_API_KEY", "sk-test")


class TestImportAndSchema:
    def test_import_via_package(self):
        from praisonai_tools import MireloTool as PkgTool, mirelo_text_to_sfx as t, mirelo_video_to_sfx as v

        assert PkgTool is MireloTool and t is mirelo_text_to_sfx and v is mirelo_video_to_sfx

    def test_catalogue_extra(self):
        from praisonai_tools.catalogue import list_tools

        entry = next(e for e in list_tools() if e.name == "MireloTool")
        assert entry.extras == ("mirelo",)

    def test_schema(self):
        schema = MireloTool().get_schema()
        assert schema["function"]["name"] == "mirelo"


class TestVideoToSfx:
    def test_url_body(self, requests_mock, tmp_path):
        post, _ = requests_mock
        post.return_value = _resp(200, _job(outputs=[_output("succeeded")]))

        result = mirelo_video_to_sfx(VIDEO_URL, duration_seconds=12, output_dir=str(tmp_path))

        url = post.call_args.args[0]
        body = post.call_args.kwargs["json"]
        assert url == f"{BASE_URL}/v3/video-to-sfx/generations"
        assert body["model"] == "sfx-2.0"
        assert body["duration_ms"] == 12000
        assert body["num_variants"] == 1
        assert body["controls"] == {"preserve_speech": True}
        assert body["input"]["video"] == {"type": "url", "url": VIDEO_URL}
        assert body["output"] == {"format": "wav"}
        assert result["status"] == "succeeded"
        assert result["files"] == [os.path.join(str(tmp_path), "job_1_0.wav")]
        assert os.path.exists(result["files"][0])

    def test_url_without_duration_defaults_with_note(self, requests_mock, tmp_path):
        post, _ = requests_mock
        post.return_value = _resp(200, _job(outputs=[_output("succeeded")]))

        result = mirelo_video_to_sfx(VIDEO_URL, output_dir=str(tmp_path))

        assert post.call_args.kwargs["json"]["duration_ms"] == 10000
        assert "note" in result

    def test_local_file_upload(self, requests_mock, tmp_path):
        post, _ = requests_mock
        video = tmp_path / "clip.mp4"
        video.write_bytes(b"\x00" * 10)
        ticket = {"id": "asset_1", "upload_url": "https://upload.example.com/", "fields": {"key": "k", "policy": "p"}, "max_bytes": 1000}
        post.side_effect = [
            _resp(200, ticket),
            _resp(204),
            _resp(200, _job(outputs=[_output("succeeded")])),
        ]

        with patch.object(mirelo_tool, "_probe_duration", return_value=7.5):
            result = mirelo_video_to_sfx(str(video), output_dir=str(tmp_path))

        assets_call, upload_call, gen_call = post.call_args_list
        assert assets_call.args[0] == f"{BASE_URL}/v3/assets"
        assert assets_call.kwargs["json"] == {"content_type": "video/mp4"}
        assert upload_call.args[0] == "https://upload.example.com/"
        assert "headers" not in upload_call.kwargs
        assert upload_call.kwargs["data"] == ticket["fields"]
        assert list(upload_call.kwargs["files"]) == ["file"]
        body = gen_call.kwargs["json"]
        assert body["input"]["video"] == {"type": "asset", "id": "asset_1"}
        assert body["duration_ms"] == 7500
        assert "error" not in result

    def test_local_file_too_large(self, requests_mock, tmp_path):
        post, _ = requests_mock
        video = tmp_path / "clip.mp4"
        video.write_bytes(b"\x00" * 10)
        post.return_value = _resp(200, {"id": "a", "upload_url": "https://u/", "fields": {}, "max_bytes": 5})

        result = mirelo_video_to_sfx(str(video), duration_seconds=5)

        assert "error" in result
        assert post.call_count == 1

    def test_missing_local_file(self, requests_mock):
        post, _ = requests_mock
        result = mirelo_video_to_sfx("/nope/clip.mp4")
        assert "error" in result
        post.assert_not_called()

    def test_poll_until_succeeded(self, requests_mock, tmp_path):
        post, get = requests_mock
        post.return_value = _resp(202, _job(status="queued"), headers={"Retry-After": "120"})
        get.side_effect = [
            _resp(200, _job(status="running")),
            _resp(200, _job(status="some_new_status")),
            _resp(200, _job(outputs=[_output("succeeded")])),
            _download(),
        ]

        result = mirelo_video_to_sfx(VIDEO_URL, duration_seconds=5, output_dir=str(tmp_path))

        assert result["status"] == "succeeded"
        assert get.call_args_list[0].args[0] == f"{BASE_URL}/v3/video-to-sfx/generations/job_1"
        assert mirelo_tool.time.sleep.call_args_list[0].args[0] == 30  # Retry-After capped
        assert len(result["files"]) == 1

    def test_upload_uses_file_content_type(self, requests_mock, tmp_path):
        post, _ = requests_mock
        video = tmp_path / "clip.webm"
        video.write_bytes(b"\x00" * 10)
        ticket = {"id": "asset_1", "upload_url": "https://u/", "fields": {}, "max_bytes": 1000}
        post.side_effect = [_resp(200, ticket), _resp(204), _resp(200, _job(outputs=[_output("succeeded")]))]

        mirelo_video_to_sfx(str(video), duration_seconds=5, output_dir=str(tmp_path))

        assets_call, upload_call, _ = post.call_args_list
        assert assets_call.kwargs["json"] == {"content_type": "video/webm"}
        assert upload_call.kwargs["files"]["file"][2] == "video/webm"

    def test_poll_respects_timeout(self, requests_mock):
        post, get = requests_mock
        post.return_value = _resp(202, _job(status="queued"), headers={"Retry-After": "30"})
        get.return_value = _resp(200, _job(status="running"))

        with patch.object(mirelo_tool.time, "monotonic", side_effect=[0, 0, 1]):
            result = MireloTool(timeout=1).video_to_sfx(VIDEO_URL, duration_seconds=5)

        assert mirelo_tool.time.sleep.call_args.args[0] == 1  # capped at remaining time
        assert "Timed out" in result["error"]
        get.assert_not_called()

    def test_download_failure_keeps_results(self, requests_mock, tmp_path):
        post, get = requests_mock
        post.return_value = _resp(200, _job(outputs=[_output("succeeded", "succeeded")]))
        get.side_effect = [_download(), RuntimeError("boom")]

        result = mirelo_video_to_sfx(VIDEO_URL, duration_seconds=5, num_variants=2, output_dir=str(tmp_path))

        assert "boom" in result["error"]
        assert len(result["files"]) == 1
        assert len(result["urls"]) == 2
        assert result["job_id"] == "job_1"

    def test_partially_succeeded(self, requests_mock, tmp_path):
        post, _ = requests_mock
        post.return_value = _resp(200, _job(status="partially_succeeded", outputs=[_output("succeeded", "failed")]))

        result = mirelo_video_to_sfx(VIDEO_URL, duration_seconds=5, num_variants=2, output_dir=str(tmp_path))

        assert len(result["files"]) == 1
        assert "warning" in result

    def test_failed_job(self, requests_mock):
        post, _ = requests_mock
        job = _job(status="failed")
        job["errors"] = [{"message": "invalid_video"}]
        post.return_value = _resp(200, job)

        result = mirelo_video_to_sfx(VIDEO_URL, duration_seconds=5)

        assert "invalid_video" in result["error"]

    def test_insufficient_credits(self, requests_mock):
        post, _ = requests_mock
        post.return_value = _resp(402, {"error": {"message": "Not enough credits"}})

        result = mirelo_video_to_sfx(VIDEO_URL, duration_seconds=5)

        assert "402" in result["error"] and "Not enough credits" in result["error"]

    def test_return_video(self, requests_mock, tmp_path):
        post, _ = requests_mock
        out = {"index": 0, "type": "mix", "variants": [{"index": 0, "status": "succeeded", "files": {"video": {"url": "https://cdn.mirelo.ai/v.mp4?sig=x"}}}]}
        post.return_value = _resp(200, _job(outputs=[out]))

        result = mirelo_video_to_sfx(VIDEO_URL, duration_seconds=5, return_video=True, output_dir=str(tmp_path))

        assert post.call_args.kwargs["json"]["output"] == {"media": "video"}
        assert result["files"][0].endswith(".mp4")

    def test_estimate_only(self, requests_mock):
        post, _ = requests_mock
        post.return_value = _resp(200, {"credits": 100, "estimated_ms": 20000})

        result = mirelo_video_to_sfx(VIDEO_URL, duration_seconds=10, estimate_only=True)

        assert post.call_count == 1
        assert post.call_args.args[0].endswith("/generations/preflight")
        assert result == {"estimate_only": True, "credits": 100, "estimated_ms": 20000}

    def test_missing_api_key(self, requests_mock, monkeypatch):
        post, get = requests_mock
        monkeypatch.delenv("MIRELO_API_KEY")

        assert "error" in mirelo_video_to_sfx(VIDEO_URL)
        assert "error" in mirelo_text_to_sfx("thunder")
        post.assert_not_called()
        get.assert_not_called()


class TestTextToSfx:
    def test_body_and_result(self, requests_mock, tmp_path):
        post, _ = requests_mock
        job = _job()
        job["result"] = {"output": _output("succeeded")}
        post.return_value = _resp(200, job)

        result = mirelo_text_to_sfx("gravel footsteps", duration_seconds=3, output_dir=str(tmp_path))

        assert post.call_args.args[0] == f"{BASE_URL}/v3/text-to-sfx/generations"
        body = post.call_args.kwargs["json"]
        assert body["model"] == "sfx-2.0"
        assert body["duration_ms"] == 3000
        assert body["input"] == {"prompt": "gravel footsteps"}
        assert len(result["files"]) == 1


@pytest.mark.skipif(not _REAL_KEY, reason="MIRELO_API_KEY not set")
def test_real_agentic(tmp_path, monkeypatch):
    """Real agentic test: an Agent scores a public sample clip (costs ~100 credits)."""
    from praisonaiagents import Agent

    monkeypatch.setenv("MIRELO_API_KEY", _REAL_KEY)
    monkeypatch.chdir(tmp_path)
    agent = Agent(
        name="sound-designer",
        instructions="Add sound design to the video the user gives you. Use 10 seconds and 1 variant.",
        tools=[mirelo_video_to_sfx],
    )
    output = agent.start("Add sound to https://di3otfzjg1gxa.cloudfront.net/chase.mp4, no music")
    print(output)
    files = list((tmp_path / "mirelo_outputs").glob("*"))
    print(files)
    assert files
