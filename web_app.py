import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from main import ask_ai


HOST = "127.0.0.1"
PORT = 8000
PAGE = Path(__file__).with_name("index.html")


class ChatHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        if self.path not in ("/", "/index.html"):
            self.send_error(404)
            return

        page = PAGE.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(page)))
        self.end_headers()
        self.wfile.write(page)

    def do_POST(self):
        if self.path != "/api/chat":
            self.send_error(404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length))
            messages = payload.get("messages")
            if not isinstance(messages, list) or not messages:
                raise ValueError("A non-empty messages list is required.")
            if any(
                not isinstance(message, dict)
                or message.get("role") not in ("user", "assistant", "system")
                or not isinstance(message.get("content"), str)
                for message in messages
            ):
                raise ValueError("Messages must have a role and text content.")
        except (ValueError, json.JSONDecodeError) as error:
            self._send_json(400, {"error": str(error)})
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache, no-transform")
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True

        answer = ask_ai(messages, on_event=self._send_event)
        if answer is None:
            self._send_event({
                "type": "error",
                "message": "Both providers failed. Check the server output and API key settings."
            })
        else:
            self._send_event({"type": "done"})

    def _send_event(self, event):
        data = json.dumps(event).encode("utf-8")
        self.wfile.write(b"data: " + data + b"\n\n")
        self.wfile.flush()

    def _send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format_string, *args):
        print("%s - %s" % (self.address_string(), format_string % args))


def main():
    server = ThreadingHTTPServer((HOST, PORT), ChatHandler)
    print(f"Multi-model chatbot UI running at http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping chatbot UI.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()