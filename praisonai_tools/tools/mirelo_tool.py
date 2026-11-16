"""Mirelo SFX 2.0 video-to-sound tool (URL input). Requires MIRELO_API_KEY."""

import os
import time
from typing import Any, Dict, Optional
from urllib.parse import urljoin

from praisonai_tools.tools.base import BaseTool

BASE_URL = "https://api.mirelo.ai"
_FINAL = {"succeeded", "partially_succeeded", "failed", "canceled", "expired"}


class MireloTool(BaseTool):
    name = "mirelo"
    description = "Generate synced sound effects, foley and ambience for a video URL using Mirelo SFX 2.0."

    def __init__(self, api_key: Optional[str] = None, timeout: int = 900):
        self.api_key = api_key or os.getenv("MIRELO_API_KEY")
        self.timeout = timeout
        super().__init__()

    def run(self, **kwargs) -> Dict[str, Any]:
        return self.video_to_sfx(**kwargs)

    def video_to_sfx(self, video_url: str, prompt: Optional[str] = None, negative_prompt: Optional[str] = None,
                     duration_seconds: float = 10, output_dir: Optional[str] = None) -> Dict[str, Any]:
        if not video_url or not video_url.startswith("https://"):
            return {"error": "video_url must be an https URL"}
        if not self.api_key:
            return {"error": "MIRELO_API_KEY required"}
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed. Install with: pip install praisonai-tools[mirelo]"}

        headers = {"Authorization": f"Bearer {self.api_key}"}
        inp = {"video": {"type": "url", "url": video_url}, "prompt": prompt, "negative_prompt": negative_prompt}
        body = {"model": "sfx-2.0", "duration_ms": int(duration_seconds * 1000), "num_variants": 1,
                "input": {k: v for k, v in inp.items() if v}, "controls": {"preserve_speech": True}, "output": {"format": "wav"}}
        try:
            resp = requests.post(f"{BASE_URL}/v3/video-to-sfx/generations", json=body, timeout=60,
                                 headers={**headers, "Prefer": "wait=25"})
            deadline = time.monotonic() + self.timeout
            while resp.status_code < 400 and resp.json().get("status") not in _FINAL:
                job = resp.json()
                wait = min(float(resp.headers.get("Retry-After", 2)), 30)
                if time.monotonic() + wait >= deadline:
                    return {"error": f"Timed out waiting for Mirelo job {job.get('id')}", "job_id": job.get("id")}
                time.sleep(wait)
                resp = requests.get(urljoin(BASE_URL, job["urls"]["self"]), headers=headers, timeout=60)
            if resp.status_code >= 400:
                return {"error": f"Mirelo API error {resp.status_code}: {resp.text[:200]}"}
            job = resp.json()
            if job["status"] not in ("succeeded", "partially_succeeded"):
                msg = "; ".join(e.get("message", "") for e in job.get("errors") or [])
                return {"error": f"Mirelo job {job['status']}: {msg}".rstrip(": "), "job_id": job.get("id")}
            urls = [v["files"]["audio"]["url"] for o in (job.get("result") or {}).get("outputs") or []
                    for v in o.get("variants") or [] if v.get("status") == "succeeded"]
            result = {"files": [], "urls": urls, "status": job["status"], "credits": job.get("credits"),
                      "job_id": job.get("id")}
            out_dir = output_dir or os.path.join(os.getcwd(), "mirelo_outputs")
            os.makedirs(out_dir, exist_ok=True)
            for i, url in enumerate(urls):
                path = os.path.join(out_dir, f"{job['id']}_{i}.wav")
                try:
                    dl = requests.get(url, timeout=120)
                    dl.raise_for_status()
                except Exception as e:  # job is paid for: keep urls so the caller can retry the download
                    return {**result, "error": f"Download failed: {e}"}
                with open(path, "wb") as f:
                    f.write(dl.content)
                result["files"].append(path)
            return result
        except Exception as e:
            return {"error": str(e)}


def mirelo_video_to_sfx(video_url: str, prompt: Optional[str] = None, negative_prompt: Optional[str] = None,
                        duration_seconds: float = 10, output_dir: Optional[str] = None) -> Dict[str, Any]:
    """Add synced sound effects, foley and ambience to a video with Mirelo SFX 2.0 (speech is preserved).

    Args:
        video_url: https URL of the video.
        prompt: Optional description of the sound to steer generation.
        negative_prompt: Sounds to avoid, e.g. "music, crowd noise".
        duration_seconds: Seconds of video to score (default 10).
        output_dir: Directory to save WAV results (default ./mirelo_outputs).

    Returns:
        Dict with local "files", "urls", "status", "credits" and "job_id", or "error".
    """
    return MireloTool().video_to_sfx(video_url, prompt, negative_prompt, duration_seconds, output_dir)
