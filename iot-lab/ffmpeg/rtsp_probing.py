"""
RTSP stream probe utility.

This script checks whether an RTSP URL is reachable and valid by running
ffprobe against the stream. It inspects stream metadata, reports common
connection/authentication issues, and prints a readable summary.

Configuration:
    Replace RTSP_URL with the actual camera stream URL before running.

Usage:
    python rtsp_probing.py

Requirements:
    - ffprobe must be installed and available in PATH.
    - The RTSP source must be reachable from this machine.
"""

import subprocess
import json
from typing import Dict, Any, Tuple

# Camera stream URL to test.
RTSP_URL = "<Give the RTSP URL of the camera>"

# ---------------------------------------------------------------------------
# Error classification helpers
# ---------------------------------------------------------------------------
def classify_error(stderr: str) -> Tuple[str, str]:
    """
    Return (code, human_message) based on common ffprobe/RTSP failures.
    code is a short machine-friendly tag.
    """
    s = stderr.lower()
    if "401" in s or "unauthorized" in s or "authentication" in s:
        return "auth_failed", "Authentication failed — check username/password."
    if "timed out" in s or "connection timed out" in s:
        return "timeout", "Connection timed out — check network/firewall or server availability."
    if "connection refused" in s or "no route to host" in s:
        return "connection_refused", "Connection refused — server not reachable or port blocked."
    if "could not find" in s or "not found" in s or "invalid data found" in s:
        return "invalid_stream", "Stream not found / not an RTSP stream / invalid data."
    if "unsupported" in s or "protocol" in s:
        return "protocol_error", "Protocol error — maybe transport mismatch (tcp/udp) or server uses different protocol."
    # fallback
    print(s)
    return "unknown", stderr.strip() or "Unknown ffprobe error."

# ---------------------------------------------------------------------------
# Core probe function
# ---------------------------------------------------------------------------
def probe_rtsp(rtsp_url: str,
               timeout: int = 10,
               rtsp_transport: str = "tcp",
               extra_ffprobe_args: list | None = None) -> Dict[str, Any]:
    """
    Probe an RTSP URL using ffprobe and return parsed JSON info on success.
    Raises Exception on failure with a helpful message.
    - rtsp_url: full RTSP URL (can include username:password@host)
    - timeout: process timeout in seconds
    - rtsp_transport: 'tcp' or 'udp' (ffmpeg/ffprobe option)
    - extra_ffprobe_args: additional ffprobe args as list of strings
    """
    if extra_ffprobe_args is None:
        extra_ffprobe_args = []

    # Build ffprobe command
    # -v quiet suppresses verbose; -print_format json -> JSON output; -show_streams/-show_format provide details
    cmd = [
        "ffprobe",
        "-v", "error",
        "-rtsp_transport", rtsp_transport,
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        rtsp_url,
        *extra_ffprobe_args
    ]

    try:
        proc = subprocess.run(cmd,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              text=True,
                              timeout=timeout)
    except subprocess.TimeoutExpired:
        raise Exception("timeout: ffprobe did not finish within {}s".format(timeout))

    if proc.returncode != 0:
        stderr_output = proc.stderr.lower()
        print(stderr_output)
        errcode, msg = classify_error(proc.stderr)
        raise Exception(f"{errcode}: {msg}\nffprobe stderr: {proc.stderr.strip()}")

    # parse stdout JSON
    if not proc.stdout:
        raise Exception("no_output: ffprobe returned no output; check URL/transport.")

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise Exception(f"json_error: cannot parse ffprobe output: {e}\nraw output: {proc.stdout[:1000]}")

    # Basic normalization: return dict with streams and format, plus raw stdout/stderr
    result = {
        "streams": data.get("streams", []),
        "format": data.get("format", {}),
        "raw": data,
        "ffprobe_stderr": proc.stderr.strip()
    }
    return result

if __name__ == "__main__":
    try:
        info = probe_rtsp(RTSP_URL, timeout=8, rtsp_transport="tcp")
        print("Probe succeeded.")
        print("Stream count:", len(info["streams"]))
        # print codec and resolution for each stream
        for i, s in enumerate(info["streams"]):
            print(f"Stream {i}: codec={s.get('codec_name')} type={s.get('codec_type')} "
                  f"resolution={s.get('width')}x{s.get('height')} fps={s.get('r_frame_rate')}")
    except Exception as e:
        print("Probe failed:", e)
