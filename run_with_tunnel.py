import os
import shutil
import signal
import subprocess
import sys
from typing import List, Optional


def check_dependency(cmd: str) -> None:
    if shutil.which(cmd):
        return
    raise SystemExit(
        f"Не найден исполняемый файл '{cmd}'. "
        "Установите его и убедитесь, что он в PATH."
    )


def build_uvicorn_command(port: int) -> List[str]:
    return [
        sys.executable,
        "-m",
        "uvicorn",
        "server:app",
        "--host",
        "0.0.0.0",
        "--port",
        str(port),
    ]


def build_cloudflared_command(port: int) -> List[str]:
    token = os.environ.get("CLOUDFLARED_TUNNEL_TOKEN")
    base = ["cloudflared", "--no-autoupdate"]
    if token:
        return base + ["tunnel", "run", "--token", token]
    public_url = f"http://localhost:{port}"
    return base + ["tunnel", "--url", public_url]


def run_processes(port: int) -> None:
    check_dependency("cloudflared")
    uvicorn_cmd = build_uvicorn_command(port)
    tunnel_cmd = build_cloudflared_command(port)

    uvicorn_proc = subprocess.Popen(uvicorn_cmd)
    tunnel_proc: Optional[subprocess.Popen] = None

    try:
        tunnel_proc = subprocess.Popen(tunnel_cmd)

        def handle_sig(signum, frame):
            terminate_processes(uvicorn_proc, tunnel_proc)

        signal.signal(signal.SIGINT, handle_sig)
        signal.signal(signal.SIGTERM, handle_sig)

        while True:
            uvicorn_code = uvicorn_proc.poll()
            tunnel_code = tunnel_proc.poll()
            if uvicorn_code is not None or tunnel_code is not None:
                break
        if uvicorn_proc.poll() is None:
            uvicorn_proc.terminate()
        if tunnel_proc.poll() is None:
            tunnel_proc.terminate()
    finally:
        terminate_processes(uvicorn_proc, tunnel_proc)


def terminate_processes(
    uvicorn_proc: subprocess.Popen, tunnel_proc: Optional[subprocess.Popen]
) -> None:
    for proc in filter(None, [tunnel_proc, uvicorn_proc]):
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == "__main__":
    port = int(os.environ.get("APP_PORT", "8000"))
    run_processes(port)
