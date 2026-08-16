"""fixture 를 http:// 로 띄우는 임시 서버.

file:// 에서는 브라우저 컨텍스트별 localStorage 격리가 실제 사이트와 다르게 동작한다.
쿠키 기반 타이머를 제대로 재현하려면 http origin 이 필요하다.
"""

from __future__ import annotations

import contextlib
import functools
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args, **kwargs):  # 스캔 로그를 요청 로그로 덮지 않는다.
        pass


@contextlib.contextmanager
def serve(directory: Path):
    handler = functools.partial(_QuietHandler, directory=str(directory))
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_address[1]}"
    finally:
        httpd.shutdown()
        httpd.server_close()
