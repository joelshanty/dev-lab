"""Check an RTSP stream with ffprobe and report process memory usage.

Configure ``RTSP_URL`` with a reachable camera or stream URL, then run:

    python3 iot-lab/ffmpeg/ffprobe_resource_monitor.py

Requirements:
    - FFmpeg's ``ffprobe`` command must be installed and available on PATH.
    - The Python package ``psutil`` must be installed.

The script starts ffprobe asynchronously, waits briefly for it to initialize,
reports its resident memory usage, and returns ``True`` when ffprobe exits
successfully. A timeout or process error returns ``False``.
"""

import asyncio
import time
import psutil


RTSP_URL = "RTSP URL here"


class FFProbeStatusChecker:
    """Run ffprobe and inspect the resources used by its process."""

    async def memory_check(self, proc=None):
        """Print and return the ffprobe process resident memory in megabytes."""
        if proc and proc.pid is not None:
            try:
                memory_bytes = psutil.Process(proc.pid).memory_info().rss
                memory_mb = memory_bytes / (1024 * 1024)
                print(f"Memory used by ffprobe process {proc.pid}: {memory_mb:.2f} MB")
                return memory_mb
            except (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied):
                print(f"ffprobe process {proc.pid} is not available for memory check")

        print("ffprobe process is not running, cannot check memory usage")

    async def get_status(self) -> bool:
        """Return whether the configured RTSP stream can be probed successfully."""
        status = False
        rtsp_url = None
        proc = None
        try:
            # Start ffprobe separately so its PID and memory usage can be measured.
            proc = await self.__create_ffprobe_process()
            print(f"created ffprobe process pid={proc.pid}")
            await asyncio.sleep(3)  # Allow some time for the process to start and consume memory
            await self.memory_check(proc)

            # Collect ffprobe output and stop waiting if the stream is unresponsive.
            _stdout, _stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=10
            )
            if proc.returncode == 0:
                status = True
            stderr_text = _stderr.decode().strip()
            print(f"ffprobe output: {stderr_text}")
            # await self.memory_check(proc)

        except asyncio.TimeoutError:
            print(f"ffprobe timed out: {RTSP_URL}")
        except Exception as e:
            print(f"ffprobe failed: {RTSP_URL} : {e}")
        finally:
            # Ensure a timed-out or failed ffprobe process does not remain running.
            if proc and proc.returncode is None:
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
                await proc.communicate()
        return status

    async def __create_ffprobe_process(self):
        """Start ffprobe with low-latency RTSP and video-stream options."""
        proc = None
        try:            
            if not RTSP_URL:
                raise ValueError(
                    "mainStream or subStream is required in rtsp connection object for FFPROBE status check"
                )

            # Probe only the first video stream and emit diagnostic output as JSON.
            cmd = [
                "ffprobe",
                "-v",
                "error",
                "-rtsp_transport",
                "tcp",
                "-analyzeduration", "0",
                "-probesize",
                "32768",
                "-max_probe_packets",
                "1",
                "-select_streams", "v:0",
                "-show_entries", "stream=codec_type",
                "-show_streams",
                "-fflags", "nobuffer",
                "-of",
                "json",
                RTSP_URL,
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except Exception as e:
            raise Exception(f"failed to create ffprobe process: {e}")
        return proc


if __name__ == "__main__":
    # Measure the complete check duration for quick performance diagnostics.
    status_checker = FFProbeStatusChecker()
    start_time = time.perf_counter()
    status = asyncio.run(status_checker.get_status())
    end_time = time.perf_counter()

    # Calculate elapsed time
    elapsed_time = end_time - start_time

    print(f"Status : {status} ---------------- Time taken: {elapsed_time:.6f} seconds")
    print(status)
