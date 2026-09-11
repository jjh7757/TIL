"""파이프라인 검증용 최소 앱. 배포된 커밋 SHA를 보여준다."""
import datetime
import http.server
import os
import socketserver

PORT = 3000


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = (
            "deploy-test OK\n"
            f"host={os.uname().nodename}\n"
            f"sha={os.environ.get('GIT_SHA', '-')}\n"
            f"time={datetime.datetime.now().isoformat()}\n"
        )
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, *args):
        pass


with socketserver.TCPServer(("", PORT), Handler) as httpd:
    httpd.serve_forever()
