"""Run Guizang's dependency-free local visual interface."""

from __future__ import annotations

import argparse
import atexit
import json
import mimetypes
import os
import signal
import subprocess
import sys
import time
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "web"
PID_FILE = ROOT / ".guizang.pid"


def load_local_environment():
    """Load only supported local settings without overriding process settings."""
    config = ROOT / ".env"
    if config.is_file():
        for line in config.read_text(encoding="utf-8").splitlines():
            name, separator, value = line.partition("=")
            if separator and name.strip() in {"DASHSCOPE_API_KEY", "GUIZANG_BAILIAN_BASE_URL"}:
                os.environ.setdefault(name.strip(), value.strip())


def stop_previous_instance() -> None:
    """Stop only the previous process recorded by this project."""
    if not PID_FILE.is_file():
        return
    try:
        previous_pid = int(PID_FILE.read_text(encoding="ascii").strip())
    except (OSError, ValueError):
        PID_FILE.unlink(missing_ok=True)
        return
    if previous_pid == os.getpid():
        return
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(previous_pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        else:
            os.kill(previous_pid, signal.SIGTERM)
        for _ in range(20):
            time.sleep(0.05)
            try:
                os.kill(previous_pid, 0)
            except (OSError, SystemError):
                break
    except ProcessLookupError:
        pass
    except PermissionError as exc:
        raise RuntimeError(f"无法停止上一次归藏服务进程：{previous_pid}") from exc
    finally:
        PID_FILE.unlink(missing_ok=True)


def write_pid_file() -> None:
    PID_FILE.write_text(str(os.getpid()), encoding="ascii", newline="\n")

    def cleanup() -> None:
        try:
            if PID_FILE.read_text(encoding="ascii").strip() == str(os.getpid()):
                PID_FILE.unlink(missing_ok=True)
        except OSError:
            pass

    atexit.register(cleanup)

sys.path.insert(0, str(ROOT / "scripts"))

from web_service import delete_document, list_recent, read_document, save_idea, save_link, search_knowledge  # noqa: E402
from ai_summary import summarize


class GuizangHandler(BaseHTTPRequestHandler):
    server_version = "Guizang/0.1"

    def log_message(self, format_string: str, *args: object) -> None:
        print(f"[归藏] {self.address_string()} - {format_string % args}")


class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True

    def _send_json(self, payload: object, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, object]:
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("请求长度无效") from exc
        if content_length <= 0 or content_length > 1024 * 1024:
            raise ValueError("请求内容为空或超过 1 MB")
        try:
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("请求不是有效的 JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError("请求内容必须是 JSON 对象")
        return payload

    def _serve_static(self, request_path: str) -> None:
        relative = "index.html" if request_path in {"", "/"} else unquote(request_path.lstrip("/"))
        requested = (WEB_ROOT / relative).resolve()
        try:
            requested.relative_to(WEB_ROOT.resolve())
        except ValueError:
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        if not requested.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        body = requested.read_bytes()
        mime_type, _ = mimetypes.guess_type(requested.name)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{mime_type or 'application/octet-stream'}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/state":
                recent = list_recent(ROOT)
                self._send_json({"recent": recent, "count": len(list_recent(ROOT, limit=100000))})
                return
            if parsed.path == "/api/document":
                path = parse_qs(parsed.query).get("path", [""])[0]
                self._send_json(read_document(ROOT, path))
                return
            self._serve_static(parsed.path)
        except ValueError as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except OSError as exc:
            self._send_json({"error": f"读取失败：{exc}"}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_POST(self) -> None:  # noqa: N802
        try:
            payload = self._read_json()
            content = str(payload.get("content", ""))
            endpoint = urlparse(self.path).path.rstrip("/") or "/"
            if endpoint == "/api/idea":
                result = save_idea(ROOT, content)
            elif endpoint == "/api/link":
                title = payload.get("title", "")
                body = payload.get("body")
                if not isinstance(title, str) or (body is not None and not isinstance(body, str)):
                    raise ValueError("文章标题和正文必须是文本")
                result = save_link(ROOT, content, supplied_title=title, supplied_body=body)
            elif endpoint == "/api/summarize":
                result = summarize(ROOT, str(payload.get("path", "")), payload.get("model", "qwen-plus"))
            elif endpoint == "/api/delete":
                result = delete_document(ROOT, str(payload.get("path", "")))
            elif endpoint == "/api/search":
                results = search_knowledge(ROOT, content)
                result = {
                    "message": f"找到 {len(results)} 条相关内容。" if results else "没有找到相关内容。",
                    "results": results,
                }
            else:
                self._send_json({"error": "接口不存在"}, HTTPStatus.NOT_FOUND)
                return
            self._send_json(result)
        except ValueError as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except OSError as exc:
            self._send_json({"error": f"处理失败：{exc}"}, HTTPStatus.INTERNAL_SERVER_ERROR)


def main() -> int:
    load_local_environment()
    stop_previous_instance()
    parser = argparse.ArgumentParser(description="启动归藏本地可视化入口")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址，默认仅本机")
    parser.add_argument("--port", type=int, default=8765, help="监听端口")
    parser.add_argument("--no-browser", action="store_true", help="启动后不自动打开浏览器")
    args = parser.parse_args()

    server = ReusableThreadingHTTPServer((args.host, args.port), GuizangHandler)
    write_pid_file()
    url = f"http://{args.host}:{args.port}"
    print(f"归藏已启动：{url}")
    print("按 Ctrl+C 停止。")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n归藏已停止。")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

