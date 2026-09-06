"""Record an RTSP stream as HLS segments with FFmpeg.

Before running this script, replace ``RTSP_URL`` with a valid camera stream
URL and make sure ``DOWNLOAD_PATH`` exists and is writable. The script starts
FFmpeg in a separate process, writes MPEG-TS segments and an HLS playlist to
that directory, and starts a second process that monitors the FFmpeg process(for testing purposes).

Run it with:

    python3 iot-lab/ffmpeg/rtsp_streaming.py

Requirements: FFmpeg installed on ``PATH`` and the Python packages
``psutil``.
"""

import multiprocessing
import subprocess
import time
import psutil

RTSP_URL = "<rtsp_url>"
DOWNLOAD_PATH = "/var/www/html/temp_videos"

# FFmpeg connects over TCP, copies the source video without re-encoding, and
# creates ten-minute HLS recordings split into ten-second MPEG-TS segments.
COMMAND = ['ffmpeg', '-n', '-loglevel', 'info', '-report', '-rtsp_flags', 'prefer_tcp', '-rtsp_transport', 'tcp', '-i', RTSP_URL, '-an', '-c', 'copy', '-r',
           '2', '-t', '1200', '-f', 'hls', '-g', '2', '-strftime', '1', '-hls_time', '10', '-hls_list_size', '0', '-hls_segment_type', 'mpegts', '-hls_segment_filename', 'record_segment_%Y-%m-%d_%H-%M-%S.ts', 'record_segment']


def create_subprocess(command, download_path):
    """Run FFmpeg in ``download_path`` and capture its output."""
    try:
        print("Starting subprocess !!!")
        result = subprocess.run(
            command,
            cwd=download_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=1260
        )
        print(result)
    except Exception as e:
        print(f"Failed create_subprocess : {e}")
    return


def subprocess_status_check(process):
    """Monitor FFmpeg's child process and stop it after ten checks."""
    try:
        count = 0
        while True:
            count += 1
            parent = psutil.Process(process.pid)
            for child in parent.children(recursive=True):
                print(child)
                if count == 10:
                    print("Killing")
                    status = child.kill()
                    print(status)
                    break
                
            time.sleep(2)
        print("Stopped")
    except Exception as e:
        print(f"Failed subprocess_status_check : {e}")


def run():
    """Start the recorder and its process monitor."""
    # Keep FFmpeg isolated from the parent process so it can be monitored and
    # terminated independently of the main Python process.
    process = multiprocessing.Process(
        target=create_subprocess,
        args=(
            COMMAND,
            DOWNLOAD_PATH,
        ),
        daemon=True,
    )
    process.start()
    print("Main process started !!!")

    # The monitor checks the FFmpeg process every two seconds and kills its
    # child after the configured number of checks in subprocess_status_check.
    status_process = multiprocessing.Process(
        target=subprocess_status_check,
        args=(
            process,
        ),
        daemon=True,
    )
    status_process.start()
    print("Status process started !!!")
    
    print("Success")
    process.join()


if __name__ == '__main__':
    run()
