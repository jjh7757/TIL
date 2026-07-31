"""Static server for local playtesting, plus a POST /shot endpoint that saves a
canvas dataURL to disk so screenshots can be inspected without a visible
browser pane. Development only -- nothing here ships to GitHub Pages."""
import base64
import http.server
import os
import socketserver

PORT = int(os.environ.get("PORT", 8777))
SHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".shots")


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/shot":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", 0))
        payload = self.rfile.read(length).decode("utf-8", "replace")
        name, _, data_url = payload.partition("\n")
        b64 = data_url.split(",", 1)[-1]
        os.makedirs(SHOT_DIR, exist_ok=True)
        safe = "".join(ch for ch in name if ch.isalnum() or ch in "-_") or "shot"
        path = os.path.join(SHOT_DIR, safe + ".png")
        with open(path, "wb") as fh:
            fh.write(base64.b64decode(b64))
        body = path.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *args):
        pass


class Server(socketserver.ThreadingTCPServer):
    # a single-threaded server deadlocks as soon as the page holds a connection
    # open while POSTing a screenshot from the same tab
    allow_reuse_address = True
    daemon_threads = True


with Server(("127.0.0.1", PORT), Handler) as httpd:
    print(f"serving on http://127.0.0.1:{PORT}  (shots -> {SHOT_DIR})")
    httpd.serve_forever()
