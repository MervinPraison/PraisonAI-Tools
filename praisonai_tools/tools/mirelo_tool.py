"""Mirelo Tool for PraisonAI Agents.

Sound design for video (SFX, foley, ambience) and text-to-SFX using Mirelo SFX 2.0.

Usage:
    from praisonai_tools import mirelo_video_to_sfx

    result = mirelo_video_to_sfx("https://example.com/clip.mp4", negative_prompt="music")

Environment Variables:
    MIRELO_API_KEY: Mirelo API key
"""

import json
import logging
import mimetypes
import os
import shutil
import subprocess
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)

BASE_URL = "https://api.mirelo.ai"
MODEL = "sfx-2.0"
DEFAULT_DURATION_SECONDS = 10
_FINAL_STATUSES = {"succeeded", "partially_succeeded", "failed", "canceled", "expired"}
_MAX_POLL_INTERVAL = 30


class MireloTool(BaseTool):
    """Tool for Mirelo SFX 2.0 video-to-sound and text-to-sound generation."""

    name = "mirelo"
    description = "Generate synced sound effects, foley and ambience for a video, or SFX from text, using Mirelo SFX 2.0."

    def __init__(self, api_key: Optional[str] = None, timeout: int = 900):
        self.api_key = api_key or os.getenv("MIRELO_API_KEY")
        self.timeout = timeout
        super().__init__()

    def run(self, action: str = "video_to_sfx", **kwargs) -> Dict[str, Any]:
        if action == "video_to_sfx":
            return self.video_to_sfx(**kwargs)
        if action == "text_to_sfx":
            return self.text_to_sfx(**kwargs)
        return {"error": f"Unknown action: {action}"}

    def _get_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def video_to_sfx(
        self,
        video: str,
        prompt: Optional[str] = None,
        negative_prompt: Optional[str] = None,
        preserve_speech: bool = True,
        duration_seconds: Optional[float] = None,
        num_variants: int = 1,
        output_format: str = "wav",
        return_video: bool = False,
        output_dir: Optional[str] = None,
        estimate_only: bool = False,
    ) -> Dict[str, Any]:
        """Generate sound design for a video (https URL or local file path)."""
        if not video:
            return {"error": "video is required"}
        if not self.api_key:
            return {"error": "MIRELO_API_KEY required"}
        is_url = video.startswith("https://")
        if not is_url and not os.path.isfile(video):
            return {"error": f"Video file not found: {video}"}

        try:
            import requests  # noqa: F401
        except ImportError:
            return {"error": "requests not installed. Install with: pip install praisonai-tools[mirelo]"}

        note = None
        if duration_seconds is None:
            duration_seconds = None if is_url else _probe_duration(video)
            if duration_seconds is None:
                duration_seconds = DEFAULT_DURATION_SECONDS
                note = (
                    f"Video duration unknown; generated the first {DEFAULT_DURATION_SECONDS}s only. "
                    "Pass duration_seconds to cover the whole clip."
                )

        try:
            if is_url:
                video_ref = {"type": "url", "url": video}
            else:
                asset_id = self._upload(video)
                if isinstance(asset_id, dict):
                    return asset_id
                video_ref = {"type": "asset", "id": asset_id}

            input_block: Dict[str, Any] = {"video": video_ref}
            if prompt:
                input_block["prompt"] = prompt
            if negative_prompt:
                input_block["negative_prompt"] = negative_prompt
            body = {
                "model": MODEL,
                "duration_ms": int(duration_seconds * 1000),
                "num_variants": num_variants,
                "input": input_block,
                "controls": {"preserve_speech": preserve_speech},
                "output": {"media": "video"} if return_video else {"format": output_format},
            }
            return self._generate("video-to-sfx", body, output_dir, estimate_only, note)
        except Exception as e:
            logger.error(f"Mirelo video_to_sfx error: {e}")
            return {"error": str(e)}

    def text_to_sfx(
        self,
        prompt: str,
        duration_seconds: float = DEFAULT_DURATION_SECONDS,
        negative_prompt: Optional[str] = None,
        num_variants: int = 1,
        output_format: str = "wav",
        output_dir: Optional[str] = None,
        estimate_only: bool = False,
    ) -> Dict[str, Any]:
        """Generate a sound effect from a text description."""
        if not prompt:
            return {"error": "prompt is required"}
        if not self.api_key:
            return {"error": "MIRELO_API_KEY required"}

        try:
            import requests  # noqa: F401
        except ImportError:
            return {"error": "requests not installed. Install with: pip install praisonai-tools[mirelo]"}

        input_block = {"prompt": prompt}
        if negative_prompt:
            input_block["negative_prompt"] = negative_prompt
        body = {
            "model": MODEL,
            "duration_ms": int(duration_seconds * 1000),
            "num_variants": num_variants,
            "input": input_block,
            "output": {"format": output_format},
        }
        try:
            return self._generate("text-to-sfx", body, output_dir, estimate_only)
        except Exception as e:
            logger.error(f"Mirelo text_to_sfx error: {e}")
            return {"error": str(e)}

    def _upload(self, path: str):
        """Upload a local file via /v3/assets. Returns the asset id or an error dict."""
        import requests

        content_type = mimetypes.guess_type(path)[0] or "video/mp4"
        resp = requests.post(
            f"{BASE_URL}/v3/assets",
            headers=self._get_headers(),
            json={"content_type": content_type},
            timeout=30,
        )
        if resp.status_code >= 400:
            return {"error": _error_message(resp)}
        ticket = resp.json()
        if os.path.getsize(path) > ticket.get("max_bytes", float("inf")):
            return {"error": f"File exceeds Mirelo upload limit of {ticket['max_bytes']} bytes; pass an https URL instead"}
        with open(path, "rb") as f:
            # Presigned upload: fields first, file last, and no Authorization header.
            up = requests.post(
                ticket["upload_url"],
                data=ticket.get("fields", {}),
                files={"file": (os.path.basename(path), f, content_type)},
                timeout=self.timeout,
            )
        if up.status_code >= 400:
            return {"error": f"Upload failed ({up.status_code})"}
        return ticket["id"]

    def _generate(
        self,
        family: str,
        body: Dict[str, Any],
        output_dir: Optional[str],
        estimate_only: bool,
        note: Optional[str] = None,
    ) -> Dict[str, Any]:
        import requests

        url = f"{BASE_URL}/v3/{family}/generations"
        if estimate_only:
            resp = requests.post(f"{url}/preflight", headers=self._get_headers(), json=body, timeout=60)
            if resp.status_code >= 400:
                return {"error": _error_message(resp)}
            quote = resp.json()
            result = {"estimate_only": True, "credits": quote.get("credits"), "estimated_ms": quote.get("estimated_ms")}
            if note:
                result["note"] = note
            return result

        headers = {**self._get_headers(), "Prefer": "wait=25"}
        resp = requests.post(url, headers=headers, json=body, timeout=60)
        if resp.status_code >= 400:
            return {"error": _error_message(resp)}
        job = resp.json()

        deadline = time.monotonic() + self.timeout
        while job.get("status") not in _FINAL_STATUSES:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return {"error": f"Timed out waiting for Mirelo job {job.get('id')}", "job_id": job.get("id")}
            time.sleep(min(_retry_after(resp), remaining))
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return {"error": f"Timed out waiting for Mirelo job {job.get('id')}", "job_id": job.get("id")}
            resp = requests.get(
                urljoin(BASE_URL, job["urls"]["self"]), headers=self._get_headers(), timeout=min(60, remaining)
            )
            if resp.status_code >= 400:
                return {"error": _error_message(resp), "job_id": job.get("id")}
            job = resp.json()

        status = job["status"]
        if status not in ("succeeded", "partially_succeeded"):
            messages = "; ".join(e.get("message", "") for e in job.get("errors") or [])
            return {"error": f"Mirelo job {status}: {messages}".rstrip(": "), "job_id": job.get("id")}

        urls = _collect_urls(job.get("result"))
        out_dir = output_dir or os.path.join(os.getcwd(), "mirelo_outputs")
        os.makedirs(out_dir, exist_ok=True)
        files = []
        try:
            for i, file_url in enumerate(urls):
                ext = os.path.splitext(file_url.split("?", 1)[0])[1] or ".bin"
                path = os.path.join(out_dir, f"{job['id']}_{i}{ext}")
                with requests.get(file_url, stream=True, timeout=120) as dl:
                    dl.raise_for_status()
                    with open(path, "wb") as f:
                        for chunk in dl.iter_content(chunk_size=1 << 16):
                            f.write(chunk)
                files.append(path)
        except Exception as e:
            # The job is paid for; return what we have so the caller can re-download from the URLs.
            return {"error": f"Download failed: {e}", "files": files, "urls": urls, "status": status, "job_id": job.get("id")}

        result = {
            "files": files,
            "urls": urls,
            "status": status,
            "credits": job.get("credits"),
            "seed": job.get("seed"),
            "job_id": job.get("id"),
        }
        if status == "partially_succeeded":
            result["warning"] = "Some variants failed; returning the ones that succeeded."
        if note:
            result["note"] = note
        return result


def _collect_urls(result: Optional[Dict[str, Any]]) -> List[str]:
    """Extract download URLs from a job result (``output`` or ``outputs``)."""
    if not result:
        return []
    outputs = result.get("outputs") or ([result["output"]] if result.get("output") else [])
    urls = []
    for output in outputs:
        for variant in output.get("variants") or []:
            files = variant.get("files") or {}
            media = files.get("video") or files.get("audio")
            if variant.get("status") == "succeeded" and media and media.get("url"):
                urls.append(media["url"])
    return urls


def _retry_after(resp) -> float:
    try:
        return min(max(float(resp.headers.get("Retry-After", 2)), 1), _MAX_POLL_INTERVAL)
    except (TypeError, ValueError):
        return 2


def _error_message(resp) -> str:
    try:
        err = resp.json().get("error")
        message = err.get("message") if isinstance(err, dict) else err
    except (ValueError, AttributeError):
        message = None
    return f"Mirelo API error {resp.status_code}: {message or resp.text[:200]}"


def _probe_duration(path: str) -> Optional[float]:
    """Return the video duration in seconds using ffprobe, if available."""
    if not shutil.which("ffprobe"):
        return None
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", path],
            capture_output=True, text=True, timeout=30, check=True,
        )
        return float(json.loads(out.stdout)["format"]["duration"])
    except Exception:
        return None


def mirelo_video_to_sfx(
    video: str,
    prompt: Optional[str] = None,
    negative_prompt: Optional[str] = None,
    preserve_speech: bool = True,
    duration_seconds: Optional[float] = None,
    num_variants: int = 1,
    output_format: str = "wav",
    return_video: bool = False,
    output_dir: Optional[str] = None,
    estimate_only: bool = False,
) -> Dict[str, Any]:
    """Add synced sound effects, foley and ambience to a video with Mirelo SFX 2.0.

    Args:
        video: https URL or local video file path.
        prompt: Optional description of the sound to steer generation.
        negative_prompt: Sounds to avoid, e.g. "music, crowd noise".
        preserve_speech: Keep dialogue already in the clip.
        duration_seconds: Seconds of video to score (probed for local files; 10 if unknown).
        num_variants: Number of alternatives to generate (1-4); each one costs credits.
        output_format: wav, flac, mp3_128..mp3_320 or m4a_128..m4a_256.
        return_video: Return an MP4 with the new soundtrack instead of audio.
        output_dir: Directory to save results (default ./mirelo_outputs).
        estimate_only: Only return the credit cost quote; generate nothing.

    Returns:
        Dict with local "files", "urls", "status", "credits", "seed" and "job_id", or "error".
    """
    return MireloTool().video_to_sfx(
        video=video,
        prompt=prompt,
        negative_prompt=negative_prompt,
        preserve_speech=preserve_speech,
        duration_seconds=duration_seconds,
        num_variants=num_variants,
        output_format=output_format,
        return_video=return_video,
        output_dir=output_dir,
        estimate_only=estimate_only,
    )


def mirelo_text_to_sfx(
    prompt: str,
    duration_seconds: float = DEFAULT_DURATION_SECONDS,
    negative_prompt: Optional[str] = None,
    num_variants: int = 1,
    output_format: str = "wav",
    output_dir: Optional[str] = None,
    estimate_only: bool = False,
) -> Dict[str, Any]:
    """Generate a sound effect from a text description with Mirelo SFX 2.0.

    Args:
        prompt: Description of the sound, e.g. "gravel footsteps".
        duration_seconds: Length of the sound in seconds.
        negative_prompt: Sounds to avoid.
        num_variants: Number of alternatives to generate (1-4); each one costs credits.
        output_format: wav, flac, mp3_128..mp3_320 or m4a_128..m4a_256.
        output_dir: Directory to save results (default ./mirelo_outputs).
        estimate_only: Only return the credit cost quote; generate nothing.

    Returns:
        Dict with local "files", "urls", "status", "credits", "seed" and "job_id", or "error".
    """
    return MireloTool().text_to_sfx(
        prompt=prompt,
        duration_seconds=duration_seconds,
        negative_prompt=negative_prompt,
        num_variants=num_variants,
        output_format=output_format,
        output_dir=output_dir,
        estimate_only=estimate_only,
    )
