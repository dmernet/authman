#!/usr/bin/env python3
"""AuthMan 本地运行控制器：无需 Docker，自动准备虚拟环境并启动 FastAPI 服务。

子命令：
  prepare  只准备虚拟环境和依赖，打印运行方式
  serve    前台运行服务（agent 请用后台任务方式调用；用户可直接在终端运行）
  status   查询服务是否可访问及监听进程
  stop     按端口停止服务

结构化结果写 stdout，进度信息写 stderr，便于 agent 解析。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_MIRROR = "https://mirrors.aliyun.com/pypi/simple/"


def emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def note(message: str) -> None:
    print(message, file=sys.stderr)


def find_repo_root(explicit: str | None = None) -> Path:
    """从 skill 目录向上查找含 main.py / requirements.txt / app 的项目根目录。"""
    candidates: list[Path] = []
    for value in (explicit, os.getenv("AUTHMAN_PROJECT_DIR")):
        if value:
            candidates.append(Path(value).expanduser())
    here = Path(__file__).resolve()
    candidates.extend([here, *here.parents])
    for base in candidates:
        base = base.resolve()
        if (base / "main.py").is_file() and (base / "requirements.txt").is_file() and (base / "app").is_dir():
            return base
    raise SystemExit("无法定位 AuthMan 项目根目录，请用 --repo 或 AUTHMAN_PROJECT_DIR 指定。")


def venv_python(venv_dir: Path) -> Path:
    return venv_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def python_candidates(explicit: str | None) -> list[list[str]]:
    result: list[list[str]] = []
    for value in (explicit, os.getenv("AUTHMAN_PYTHON")):
        if value:
            result.append([value])
    result.append([sys.executable])
    if os.name == "nt":
        result += [["py", f"-3.{minor}"] for minor in (12, 11, 10, 13)]
    else:
        result += [[name] for name in ("python3.12", "python3.11", "python3.10", "python3")]
    return result


def ensure_venv(venv_dir: Path, explicit_python: str | None) -> Path:
    target = venv_python(venv_dir)
    if target.is_file():
        return target
    venv_dir.parent.mkdir(parents=True, exist_ok=True)
    note(f"未发现虚拟环境，正在创建: {venv_dir}")
    last_error: Exception | None = None
    for cmd in python_candidates(explicit_python):
        try:
            subprocess.run([*cmd, "-m", "venv", str(venv_dir)], check=True, capture_output=True)
            if target.is_file():
                note(f"虚拟环境就绪: {' '.join(cmd)}")
                return target
        except (OSError, subprocess.CalledProcessError) as exc:
            last_error = exc
    raise SystemExit(f"创建虚拟环境失败: {last_error or '未找到可用 Python（建议 3.10+）'}")


def ensure_deps(py: Path, repo: Path, runtime: Path, mirror: str | None, skip: bool) -> None:
    if skip:
        note("跳过依赖安装 (--no-install)")
        return
    req = repo / "requirements.txt"
    try:
        version = subprocess.run(
            [str(py), "-c", "import platform;print(platform.python_version())"],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        version = platform.python_version()
    digest = hashlib.sha256(
        (req.read_text(encoding="utf-8") + version + (mirror or "")).encode("utf-8")
    ).hexdigest()[:16]
    marker = runtime / f"deps-{digest}.ok"
    if marker.is_file():
        note("依赖已安装，跳过 pip")
        return

    cmd = [str(py), "-m", "pip", "install", "--disable-pip-version-check"]
    if mirror:
        cmd += ["-i", mirror]
    cmd += ["-r", str(req)]
    note("首次运行，正在安装依赖（可能需要 1-2 分钟）...")
    result = subprocess.run(cmd, cwd=str(repo))
    if result.returncode != 0 and mirror and "pypi.org" not in mirror:
        note("镜像源安装失败，回退到 PyPI 官方源重试...")
        result = subprocess.run(
            [str(py), "-m", "pip", "install", "--disable-pip-version-check", "-r", str(req)],
            cwd=str(repo),
        )
    if result.returncode != 0:
        raise SystemExit(f"依赖安装失败（退出码 {result.returncode}）。可换源：--mirror <url> 或离线时加 --no-install")
    marker.touch()
    note("依赖安装完成")


def prepare(repo: Path, args: argparse.Namespace) -> tuple[Path, Path, dict[str, str]]:
    runtime = repo / ".runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    venv_dir = Path(args.venv).expanduser().resolve() if args.venv else repo / ".venv"
    py = ensure_venv(venv_dir, args.python)
    ensure_deps(py, repo, runtime, args.mirror, args.no_install)
    db_path = Path(os.getenv("DB_PATH", str(repo / "data" / "tokens.db"))).expanduser().resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["DB_PATH"] = str(db_path)
    env["PYTHONPATH"] = str(repo) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    env.setdefault("PYTHONUNBUFFERED", "1")
    return py, db_path, env


def port_is_free(port: int, host: str) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("0.0.0.0" if host in ("0.0.0.0", "::") else host, port))
            return True
        except OSError:
            return False


def pick_port(host: str, requested: int) -> int:
    if requested == 0:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("", 0))
            return int(sock.getsockname()[1])
    for port in range(requested, requested + 50):
        if port_is_free(port, host):
            return port
    raise SystemExit(f"端口 {requested}-{requested + 49} 都被占用，请用 --port 指定其它端口。")


def http_ok(url: str, timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return 200 <= resp.status < 300
    except (urllib.error.URLError, OSError, ValueError):
        return False


def listening_pids(port: int) -> list[int]:
    """返回监听指定 TCP 端口的进程号（尽力而为）。"""
    pids: set[int] = set()
    if os.name == "nt":
        try:
            out = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, timeout=10).stdout
            text = out.decode("utf-8", errors="replace")
            for line in text.splitlines():
                if "LISTENING" not in line:
                    continue
                parts = line.split()
                if len(parts) > 1 and parts[1].endswith(f":{port}") and parts[-1].isdigit():
                    pids.add(int(parts[-1]))
        except (OSError, subprocess.SubprocessError):
            pass
    else:
        for cmd in (["lsof", "-ti", f"tcp:{port}"], ["fuser", "-n", "tcp", str(port)]):
            try:
                out = subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout or ""
                pids.update(int(tok) for tok in re.findall(r"\d+", out))
            except (OSError, subprocess.SubprocessError, ValueError):
                continue
            if pids:
                break
    return sorted(pids)


def kill_pids(pids: list[int]) -> None:
    for pid in pids:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
        else:
            try:
                os.kill(pid, 15)
            except OSError:
                pass


def read_state(runtime: Path) -> dict[str, Any]:
    path = runtime / "serve.json"
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def write_state(runtime: Path, state: dict[str, Any]) -> None:
    runtime.mkdir(parents=True, exist_ok=True)
    (runtime / "serve.json").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def display_host(host: str) -> str:
    return "127.0.0.1" if host in ("0.0.0.0", "::") else host


def cmd_prepare(args: argparse.Namespace) -> None:
    repo = find_repo_root(args.repo)
    py, db_path, _ = prepare(repo, args)
    script = Path(__file__).resolve()
    emit({
        "ok": True,
        "repo": str(repo),
        "venv_python": str(py),
        "db_path": str(db_path),
        "run_command": f'"{sys.executable}" "{script}" serve --repo "{repo}" --port {args.port}',
        "note": "agent 调用 serve 时请使用后台任务方式；用户可直接在终端运行。",
    })


def cmd_serve(args: argparse.Namespace) -> None:
    repo = find_repo_root(args.repo)
    py, db_path, env = prepare(repo, args)
    host, port = args.host, pick_port(args.host, args.port)
    url = f"http://{display_host(host)}:{port}"
    write_state(repo / ".runtime", {
        "url": url, "port": port, "host": host, "db_path": str(db_path),
        "venv_python": str(py), "repo": str(repo),
    })
    note(f"AuthMan 启动中: {url}  数据库: {db_path}")
    cmd = [str(py), "-m", "uvicorn", "main:app", "--host", host, "--port", str(port)]
    try:
        raise SystemExit(subprocess.run(cmd, cwd=str(repo), env=env).returncode)
    finally:
        state = read_state(repo / ".runtime")
        if state.get("port") == port:
            state["status"] = "stopped"
            write_state(repo / ".runtime", state)


def cmd_status(args: argparse.Namespace) -> None:
    repo = find_repo_root(args.repo)
    state = read_state(repo / ".runtime")
    port = args.port if args.port is not None else int(state.get("port") or 8000)
    host = args.host or str(state.get("host") or "0.0.0.0")
    url = f"http://{display_host(host)}:{port}"
    healthy = http_ok(url + "/openapi.json")
    emit({
        "ok": healthy,
        "status": "running" if healthy else "stopped",
        "url": url,
        "docs_url": url + "/docs",
        "admin_url": url + "/admin",
        "port": port,
        "pids": listening_pids(port),
        "db_path": state.get("db_path"),
    })


def cmd_stop(args: argparse.Namespace) -> None:
    repo = find_repo_root(args.repo)
    state = read_state(repo / ".runtime")
    port = args.port if args.port is not None else int(state.get("port") or 8000)
    pids = listening_pids(port)
    kill_pids(pids)
    time.sleep(0.5)
    state["status"] = "stopped"
    write_state(repo / ".runtime", state)
    emit({"ok": True, "port": port, "killed_pids": pids, "remaining": listening_pids(port)})


def add_common(sub: argparse.ArgumentParser, with_port: bool = True) -> None:
    sub.add_argument("--repo", help="AuthMan 项目根目录，默认自动定位")
    if with_port:
        sub.add_argument("--port", type=int, default=None, help="端口，默认 8000；被占用时自动顺延（serve）")
    sub.add_argument("--host", default=None, help="监听地址，默认 0.0.0.0")
    sub.add_argument("--venv", help="虚拟环境目录，默认 <repo>/.venv")
    sub.add_argument("--python", help="用于创建虚拟环境的 Python 解释器")
    sub.add_argument("--mirror", default=os.getenv("PIP_INDEX_URL", DEFAULT_MIRROR), help="pip 源，传空字符串使用默认源")
    sub.add_argument("--no-install", action="store_true", help="跳过依赖安装")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AuthMan 本地运行控制器（无需 Docker）")
    subs = parser.add_subparsers(dest="command", required=True)

    p_prepare = subs.add_parser("prepare", help="准备虚拟环境与依赖")
    add_common(p_prepare)
    p_prepare.set_defaults(func=cmd_prepare)

    p_serve = subs.add_parser("serve", help="运行服务（前台，由 agent/终端托管）")
    add_common(p_serve)
    p_serve.set_defaults(func=cmd_serve)

    p_status = subs.add_parser("status", help="查询服务状态")
    add_common(p_status)
    p_status.set_defaults(func=cmd_status)

    p_stop = subs.add_parser("stop", help="按端口停止服务")
    add_common(p_stop)
    p_stop.set_defaults(func=cmd_stop)
    return parser


if __name__ == "__main__":
    parsed = build_parser().parse_args()
    if parsed.command in ("serve", "prepare") and getattr(parsed, "port", None) is None:
        parsed.port = int(os.getenv("AUTHMAN_PORT", "8000"))
    if getattr(parsed, "host", None) is None:
        parsed.host = os.getenv("AUTHMAN_HOST", "0.0.0.0")
    parsed.func(parsed)
