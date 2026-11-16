"""Unit tests for MireloTool (all HTTP mocked)."""

import os
from unittest.mock import MagicMock, patch

import pytest

from praisonai_tools.tools import mirelo_tool
from praisonai_tools.tools.mirelo_tool import BASE_URL, MireloTool, mirelo_video_to_sfx

VIDEO_URL = "https://example.com/chase.mp4"
# Captured before the autouse fixture swaps in a fake key.
_REAL_KEY = os.getenv("MIRELO_API_KEY")


def _resp(status=200, json_data=None, headers=None, content=b"RIFF"):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = json_data if json_data is not None else {}
    r.headers = headers or {}
    r.text = "boom"
    r.content = content
    return r


def _job(status="succeeded", variants=(), job_id="job_1"):
    return {
        "id": job_id,
        "status": status,
        "credits": 100,
        "errors": [],
        "urls": {"self": f"/v3/video-to-sfx/generations/{job_id}"},
        "result": {"outputs": [{"variants": [
            {"status": s, "files": {"audio": {"url": f"https://cdn.mirelo.ai/{i}.wav"}} if s == "succeeded" else None}
            for i, s in enumerate(variants)
        ]}]} if variants else None,
    }


@pytest.fixture
def requests_mock():
    with patch("requests.post") as post, patch("requests.get") as get, patch.object(mirelo_tool.time, "sleep"):
        get.return_value = _resp()
        yield post, get


@pytest.fixture(autouse=True)
def api_key(monkeypatch):
    monkeypatch.setenv("MIRELO_API_KEY", "sk-test")


def test_import_and_catalogue():
    from praisonai_tools import MireloTool as PkgTool, mirelo_video_to_sfx as fn
    from praisonai_tools.catalogue import list_tools

    assert PkgTool is MireloTool and fn is mirelo_video_to_sfx
    assert next(e for e in list_tools() if e.name == "MireloTool").extras == ("mirelo",)
    assert MireloTool().get_schema()["function"]["name"] == "mirelo"


def test_url_body_and_download(requests_mock, tmp_path):
    post, _ = requests_mock
    post.return_value = _resp(200, _job(variants=["succeeded"]))

    result = mirelo_video_to_sfx(VIDEO_URL, negative_prompt="music", duration_seconds=12, output_dir=str(tmp_path))

    assert post.call_args.args[0] == f"{BASE_URL}/v3/video-to-sfx/generations"
    body = post.call_args.kwargs["json"]
    assert body["model"] == "sfx-2.0"
    assert body["duration_ms"] == 12000
    assert body["input"] == {"video": {"type": "url", "url": VIDEO_URL}, "negative_prompt": "music"}
    assert body["controls"] == {"preserve_speech": True}
    assert result["status"] == "succeeded"
    assert result["files"] == [os.path.join(str(tmp_path), "job_1_0.wav")]
    assert os.path.exists(result["files"][0])


def test_rejects_non_url_and_missing_key(requests_mock, monkeypatch):
    post, _ = requests_mock
    assert "error" in mirelo_video_to_sfx("/local/clip.mp4")
    monkeypatch.delenv("MIRELO_API_KEY")
    assert "MIRELO_API_KEY" in mirelo_video_to_sfx(VIDEO_URL)["error"]
    post.assert_not_called()


def test_poll_until_succeeded(requests_mock, tmp_path):
    post, get = requests_mock
    post.return_value = _resp(202, _job(status="queued"), headers={"Retry-After": "120"})
    get.side_effect = [_resp(200, _job(status="running")), _resp(200, _job(variants=["succeeded"])), _resp()]

    result = mirelo_video_to_sfx(VIDEO_URL, output_dir=str(tmp_path))

    assert result["status"] == "succeeded"
    assert get.call_args_list[0].args[0] == f"{BASE_URL}/v3/video-to-sfx/generations/job_1"
    assert mirelo_tool.time.sleep.call_args_list[0].args[0] == 30  # Retry-After capped
    assert len(result["files"]) == 1


def test_poll_respects_timeout(requests_mock):
    post, get = requests_mock
    post.return_value = _resp(202, _job(status="queued"), headers={"Retry-After": "30"})

    result = MireloTool(timeout=1).video_to_sfx(VIDEO_URL)

    assert "Timed out" in result["error"] and result["job_id"] == "job_1"
    mirelo_tool.time.sleep.assert_not_called()
    get.assert_not_called()


def test_download_failure_keeps_results(requests_mock, tmp_path):
    post, get = requests_mock
    post.return_value = _resp(200, _job(variants=["succeeded", "succeeded"]))
    get.side_effect = [_resp(), RuntimeError("boom")]

    result = mirelo_video_to_sfx(VIDEO_URL, output_dir=str(tmp_path))

    assert "boom" in result["error"]
    assert len(result["files"]) == 1 and len(result["urls"]) == 2 and result["job_id"] == "job_1"


def test_partially_succeeded(requests_mock, tmp_path):
    post, _ = requests_mock
    post.return_value = _resp(200, _job(status="partially_succeeded", variants=["succeeded", "failed"]))

    result = mirelo_video_to_sfx(VIDEO_URL, output_dir=str(tmp_path))

    assert result["status"] == "partially_succeeded" and len(result["files"]) == 1


def test_failed_job_and_api_error(requests_mock):
    post, _ = requests_mock
    job = _job(status="failed")
    job["errors"] = [{"message": "invalid_video"}]
    post.return_value = _resp(200, job)
    assert "invalid_video" in mirelo_video_to_sfx(VIDEO_URL)["error"]

    post.return_value = _resp(402)
    assert "402" in mirelo_video_to_sfx(VIDEO_URL)["error"]


@pytest.mark.skipif(not _REAL_KEY, reason="MIRELO_API_KEY not set")
def test_real_agentic(tmp_path, monkeypatch):
    """Real agentic test: an Agent scores a public sample clip (costs ~100 credits)."""
    from praisonaiagents import Agent

    monkeypatch.setenv("MIRELO_API_KEY", _REAL_KEY)
    monkeypatch.chdir(tmp_path)
    agent = Agent(
        name="sound-designer",
        instructions="Add sound design to the video URL the user gives you.",
        tools=[mirelo_video_to_sfx],
    )
    print(agent.start("Add sound to https://di3otfzjg1gxa.cloudfront.net/chase.mp4, no music"))
    assert list((tmp_path / "mirelo_outputs").glob("*"))
