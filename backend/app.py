from __future__ import annotations

import argparse
import json
import mimetypes
import time
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse


ROOT_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = ROOT_DIR / "frontend"


def build_feedback(text: str, scenario: str) -> dict:
    started = time.perf_counter()
    utterance = " ".join(text.strip().split())

    replacements = [
        ("I am agree", "I agree"),
        ("he go", "he goes"),
        ("she go", "she goes"),
        ("very much people", "many people"),
        ("discuss about", "discuss"),
        ("more better", "better"),
        ("I very like", "I really like"),
        ("it help", "it helps"),
    ]

    corrected = utterance or "I would like to practice a short conversation."
    feedback = []
    lowered = corrected.lower()
    for wrong, right in replacements:
        if wrong.lower() in lowered:
            corrected = corrected.replace(wrong, right)
            feedback.append(
                {
                    "type": "grammar",
                    "original": wrong,
                    "suggestion": right,
                    "reason": "Use the natural collocation or verb form in spoken English.",
                }
            )

    word_count = len(corrected.split())
    fluency_score = min(96, 58 + word_count * 3 - len(feedback) * 8)
    fluency_score = max(45, fluency_score)
    cefr = "B1" if fluency_score < 76 else "B2"
    if word_count > 22 and not feedback:
        cefr = "C1"

    scenario_prompt = {
        "interview": "Let's continue with a follow-up interview question.",
        "travel": "Let's continue with a travel problem-solving scene.",
        "campus": "Let's continue with a campus conversation.",
        "daily": "Let's continue with a daily small-talk exchange.",
    }.get(scenario, "Let's continue the conversation.")

    if not feedback:
        feedback.append(
            {
                "type": "expression",
                "original": corrected,
                "suggestion": "Add one concrete detail to make the answer more natural.",
                "reason": "Specific details make spoken answers easier to follow.",
            }
        )

    elapsed_ms = round((time.perf_counter() - started) * 1000 + 120)
    return {
        "id": str(uuid.uuid4()),
        "input": utterance,
        "corrected": corrected,
        "reply": f"{scenario_prompt} A stronger version is: \"{corrected}\"",
        "feedback": feedback,
        "metrics": {
            "mockLatencyMs": elapsed_ms,
            "fluencyScore": fluency_score,
            "cefrEstimate": cefr,
            "wordCount": word_count,
        },
        "nextPrompt": "Could you answer again with one reason and one example?",
    }


class AppHandler(BaseHTTPRequestHandler):
    server_version = "SpeakFlowCoach/0.1"

    def log_message(self, format: str, *args) -> None:
        print(f"[{self.log_date_time_string()}] {self.address_string()} {format % args}")

    def _set_common_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._set_common_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_static(self, file_path: Path) -> None:
        try:
            resolved = file_path.resolve()
            resolved.relative_to(FRONTEND_DIR.resolve())
        except ValueError:
            self._send_json({"error": "invalid static path"}, HTTPStatus.FORBIDDEN)
            return

        if not resolved.exists() or not resolved.is_file():
            self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
            return

        content_type = mimetypes.guess_type(resolved.name)[0] or "application/octet-stream"
        data = resolved.read_bytes()
        self.send_response(HTTPStatus.OK)
        self._set_common_headers()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self._set_common_headers()
        self.end_headers()

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/health":
            self._send_json(
                {
                    "status": "ok",
                    "service": "speakflow-coach",
                    "mode": "local-mock",
                }
            )
            return

        if path == "/api/session":
            self._send_json(
                {
                    "sessionId": str(uuid.uuid4()),
                    "audio": {
                        "sampleRate": 16000,
                        "chunkMs": 30,
                        "transport": "mock-http-now-webrtc-later",
                    },
                    "pipeline": ["vad", "streaming-stt", "llm-feedback", "tts", "barge-in"],
                }
            )
            return

        static_path = unquote(path.lstrip("/"))
        if path in ("", "/"):
            self._send_static(FRONTEND_DIR / "index.html")
            return
        self._send_static(FRONTEND_DIR / static_path)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path != "/api/conversation/mock":
            self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_length).decode("utf-8")
            payload = json.loads(raw_body or "{}")
        except json.JSONDecodeError:
            self._send_json({"error": "invalid json"}, HTTPStatus.BAD_REQUEST)
            return

        text = str(payload.get("text", ""))
        scenario = str(payload.get("scenario", "daily"))
        self._send_json(build_feedback(text, scenario))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the SpeakFlow Coach local mock server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), AppHandler)
    print(f"SpeakFlow Coach running at http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
