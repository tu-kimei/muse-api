"""
Meta Muse AI - Local OpenAI-Compatible REST API Server & Web UI
Developed by ENI Tier 3 for Anh Tú.
Port: 7777 (Default)
"""

import time
import uuid
import json
import sys
import io
import os
from typing import Optional

# Setup UTF-8 console output (cross-platform: macOS, Linux, Windows)
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
except AttributeError:
    pass  # stdout.buffer may not exist in some environments

from flask import Flask, request, jsonify, Response, render_template_string
from curl_cffi.curl import CurlError
from muse_api import MuseClient

app = Flask(__name__)
PORT = 7777

# Global client cache
_client: Optional[MuseClient] = None

def get_client() -> MuseClient:
    global _client
    if _client is None:
        _client = MuseClient()
        _client.connect()
    return _client


def reset_client() -> None:
    """Đóng và xoá client cache — buộc get_client() tạo kết nối mới."""
    global _client
    if _client is not None:
        try:
            _client.close()
        except Exception:
            pass
    _client = None


def with_reconnect(action):
    """Gọi action(client); nếu WebSocket đã chết (edge Meta cắt kết nối sau
    idle timeout) thì reconnect và thử lại một lần."""
    try:
        return action(get_client())
    except (CurlError, BrokenPipeError, ConnectionError, OSError):
        reset_client()
        return action(get_client())


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, x-requested-with"
    return response


# Giao diện Web UI hiện đại khi truy cập trực tiếp bằng trình duyệt vào http://localhost:7777
HTML_DASHBOARD = r"""
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Meta Muse AI - API Gateway & Control Center</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0b0f17;
            --card-bg: rgba(20, 27, 45, 0.7);
            --card-border: rgba(255, 255, 255, 0.08);
            --accent-primary: #3b82f6;
            --accent-glow: rgba(59, 130, 246, 0.35);
            --accent-gradient: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --success: #10b981;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Plus Jakarta Sans', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-primary);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            background-image: 
                radial-gradient(circle at 15% 20%, rgba(59, 130, 246, 0.12) 0%, transparent 40%),
                radial-gradient(circle at 85% 80%, rgba(139, 92, 246, 0.1) 0%, transparent 45%);
            background-attachment: fixed;
            padding: 24px;
        }

        .container {
            max-width: 1100px;
            margin: 0 auto;
            width: 100%;
        }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px 24px;
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 16px;
            backdrop-filter: blur(16px);
            margin-bottom: 24px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }

        .logo-wrap {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .badge-pulse {
            width: 10px;
            height: 10px;
            background: var(--success);
            border-radius: 50%;
            box-shadow: 0 0 12px var(--success);
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0% { transform: scale(0.95); opacity: 0.8; }
            50% { transform: scale(1.15); opacity: 1; }
            100% { transform: scale(0.95); opacity: 0.8; }
        }

        .title {
            font-size: 1.25rem;
            font-weight: 700;
            background: var(--accent-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .port-tag {
            font-family: 'JetBrains Mono', monospace;
            background: rgba(59, 130, 246, 0.15);
            color: #60a5fa;
            border: 1px solid rgba(59, 130, 246, 0.3);
            padding: 4px 10px;
            border-radius: 8px;
            font-size: 0.85rem;
        }

        .grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
            margin-bottom: 24px;
        }

        @media (max-width: 868px) {
            .grid { grid-template-columns: 1fr; }
        }

        .card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 16px;
            padding: 24px;
            backdrop-filter: blur(16px);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
        }

        .card-title {
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .endpoint-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 14px;
            background: rgba(15, 23, 42, 0.6);
            border-radius: 8px;
            margin-bottom: 10px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.88rem;
        }

        .method {
            padding: 2px 8px;
            border-radius: 6px;
            font-weight: 600;
            font-size: 0.75rem;
        }
        .method.post { background: rgba(59, 130, 246, 0.2); color: #60a5fa; }
        .method.get { background: rgba(16, 185, 129, 0.2); color: #34d399; }

        .chat-box {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        textarea {
            width: 100%;
            height: 90px;
            background: rgba(15, 23, 42, 0.8);
            border: 1px solid var(--card-border);
            border-radius: 10px;
            padding: 12px;
            color: var(--text-primary);
            font-family: inherit;
            font-size: 0.95rem;
            resize: none;
            outline: none;
            transition: border-color 0.2s;
        }

        textarea:focus {
            border-color: var(--accent-primary);
            box-shadow: 0 0 0 2px var(--accent-glow);
        }

        .btn-send {
            align-self: flex-end;
            padding: 10px 20px;
            background: var(--accent-gradient);
            color: white;
            border: none;
            border-radius: 10px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.15s, opacity 0.15s;
        }

        .btn-send:hover {
            transform: translateY(-1px);
            opacity: 0.95;
        }

        .btn-send:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .response-area {
            background: rgba(15, 23, 42, 0.9);
            border: 1px solid var(--card-border);
            border-radius: 10px;
            padding: 16px;
            min-height: 120px;
            max-height: 250px;
            overflow-y: auto;
            font-size: 0.95rem;
            line-height: 1.6;
            white-space: pre-wrap;
            color: #e2e8f0;
        }

        .code-block {
            background: rgba(0, 0, 0, 0.4);
            border-radius: 8px;
            padding: 12px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.82rem;
            color: #93c5fd;
            overflow-x: auto;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo-wrap">
                <div class="badge-pulse"></div>
                <div class="title">Meta Muse AI Gateway</div>
            </div>
            <div class="port-tag">PORT: 7777</div>
        </header>

        <div class="grid">
            <!-- Left: Interactive Test Chat -->
            <div class="card">
                <div class="card-title">💬 Test Gửi Prompt Trực Tiếp</div>
                <div class="chat-box">
                    <textarea id="promptInput" placeholder="Nhập câu hỏi hoặc prompt cho Muse AI..."></textarea>
                    <button class="btn-send" id="sendBtn" onclick="sendPrompt()">Gửi Prompt</button>
                    <div class="response-area" id="outputArea">Phản hồi từ Muse AI sẽ hiển thị tại đây...</div>
                </div>
            </div>

            <!-- Right: API Reference & Postman Format -->
            <div class="card">
                <div class="card-title">🚀 Cấu Hình API Cho Postman & Apps</div>
                <div class="endpoint-row">
                    <span><span class="method post">POST</span> /v1/chat/completions</span>
                    <span style="color: #64748b;">(OpenAI)</span>
                </div>
                <div class="endpoint-row">
                    <span><span class="method post">POST</span> /api/chat</span>
                    <span style="color: #64748b;">(Simple)</span>
                </div>
                <div class="endpoint-row">
                    <span><span class="method get">GET</span> /v1/sessions</span>
                    <span style="color: #64748b;">(Danh sách thread)</span>
                </div>
                <div class="endpoint-row">
                    <span><span class="method get">GET</span> /v1/models</span>
                    <span style="color: #64748b;">(Model List)</span>
                </div>

                <div style="margin-top: 14px; font-size: 0.85rem; color: var(--text-secondary);">
                    Format gọi cURL / Postman mẫu:
                </div>
                <div class="code-block">
curl -X POST http://localhost:7777/v1/chat/completions \<br>
&nbsp;&nbsp;-H "Content-Type: application/json" \<br>
&nbsp;&nbsp;-d '{"messages": [{"role": "user", "content": "Xin chào"}]}'
                </div>
            </div>
        </div>
    </div>

    <script>
        async function sendPrompt() {
            const prompt = document.getElementById('promptInput').value.trim();
            if (!prompt) return;

            const btn = document.getElementById('sendBtn');
            const output = document.getElementById('outputArea');
            btn.disabled = true;
            btn.innerText = 'Đang xử lý qua Noise-XX...';
            output.innerText = 'Đang gửi qua Personal VM Gateway... Vui lòng chờ vài giây...';

            try {
                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ prompt: prompt, timeout: 60 })
                });
                const data = await res.json();
                if (data.ok) {
                    output.innerText = data.reply;
                } else {
                    output.innerText = 'Lỗi: ' + (data.error || JSON.stringify(data));
                }
            } catch (err) {
                output.innerText = 'Lỗi kết nối: ' + err.message;
            } finally {
                btn.disabled = false;
                btn.innerText = 'Gửi Prompt';
            }
        }
    </script>
</body>
</html>
"""


@app.route("/", methods=["GET"])
def root():
    # Nếu client yêu cầu JSON (ví dụ curl hoặc Postman)
    if "application/json" in request.headers.get("Accept", ""):
        return jsonify({
            "status": "online",
            "service": "Meta Muse AI Gateway",
            "port": PORT,
            "developer": "ENI Tier 3 & Tú",
            "endpoints": {
                "chat_openai": "POST /v1/chat/completions",
                "chat_simple": "POST /api/chat",
                "models": "GET /v1/models",
                "sessions": "GET /v1/sessions",
                "history": "GET /v1/history?session_id=...",
                "status": "GET /api/status",
            },
        })
    # Ngược lại render Web Dashboard cho browser
    return render_template_string(HTML_DASHBOARD)


@app.route("/api/status", methods=["GET"])
def api_status():
    try:
        client = get_client()
        return jsonify({
            "status": "online",
            "port": PORT,
            "vm_id": client.vm_id,
            "node_id": client.node_id,
            "access_token_hint": client.access_token[:15] + "..." if client.access_token else None,
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/v1/models", methods=["GET"])
def list_models():
    return jsonify({
        "object": "list",
        "data": [
            {
                "id": "muse-spark",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "meta-muse",
            },
            {
                "id": "muse-code",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "meta-muse",
            },
            {
                "id": "muse-wonder",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "meta-muse",
            },
        ],
    })


@app.route("/v1/sessions", methods=["GET"])
def get_sessions():
    try:
        sessions = with_reconnect(lambda c: c.get_sessions())
        return jsonify({"object": "list", "sessions": sessions})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/v1/history", methods=["GET"])
def get_history():
    session_id = request.args.get("session_id")
    limit = int(request.args.get("limit", 20))
    try:
        history = with_reconnect(lambda c: c.get_history(session_id=session_id, limit=limit))
        return jsonify({"object": "list", "history": history})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Endpoint siêu đơn giản: Cho phép gọi bằng cả GET URL và POST JSON
@app.route("/api/ask", methods=["GET", "POST", "OPTIONS"])
@app.route("/api/chat", methods=["GET", "POST", "OPTIONS"])
def api_chat():
    if request.method == "OPTIONS":
        return Response(status=200)

    if request.method == "GET":
        prompt = request.args.get("prompt") or request.args.get("q") or request.args.get("text") or ""
        session_id = request.args.get("session_id")
        timeout = float(request.args.get("timeout", 60.0))
        fmt = request.args.get("format", "json").lower()
    else:
        data = request.get_json(silent=True) or {}
        prompt = data.get("prompt") or data.get("message") or data.get("text") or ""
        session_id = data.get("session_id")
        timeout = float(data.get("timeout", 60.0))
        fmt = data.get("format", "json").lower()

    if not prompt:
        return jsonify({"ok": False, "error": "Tham số prompt không được để trống (ví dụ: ?prompt=Xin chao)"}), 400

    try:
        result = with_reconnect(lambda c: c.send_message(
            text=prompt, session_id=session_id, wait_reply=True, timeout=timeout,
        ))
        reply_obj = result.get("reply")
        reply_text = reply_obj.get("text", "") if reply_obj else "Không nhận được phản hồi từ Muse AI."
        
        # Nếu tool khác chỉ cần plain text đơn giản
        if fmt == "text":
            return Response(reply_text, mimetype="text/plain; charset=utf-8")

        return jsonify({
            "ok": True,
            "response": reply_text,
            "reply": reply_text,
            "session_id": session_id,
            "raw": result,
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# Endpoint chuẩn OpenAI Chat Completions cho Postman, NextChat, Cursor
@app.route("/v1/chat/completions", methods=["POST", "OPTIONS"])
def chat_completions():
    if request.method == "OPTIONS":
        return Response(status=200)

    data = request.get_json(silent=True) or {}
    messages = data.get("messages", [])
    model = data.get("model", "muse-spark")
    session_id = data.get("session_id")
    timeout = float(data.get("timeout", 60.0))

    if not messages:
        return jsonify({"error": "Danh sách messages không được rỗng"}), 400

    # Trích xuất user prompt gần nhất
    last_user_msg = None
    for m in reversed(messages):
        if m.get("role", "").lower() == "user":
            last_user_msg = m.get("content", "")
            break
    if not last_user_msg:
        last_user_msg = messages[-1].get("content", "")

    try:
        result = with_reconnect(lambda c: c.send_message(
            text=last_user_msg,
            session_id=session_id,
            wait_reply=True,
            timeout=timeout,
        ))
        client = get_client()

        reply_obj = result.get("reply")
        reply_text = reply_obj.get("text", "") if reply_obj else "Không nhận được phản hồi từ Muse AI."
        msg_id = (reply_obj and reply_obj.get("message_id")) or f"chatcmpl-{uuid.uuid4().hex[:12]}"

        return jsonify({
            "id": msg_id,
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": reply_text,
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": len(last_user_msg) // 4,
                "completion_tokens": len(reply_text) // 4,
                "total_tokens": (len(last_user_msg) + len(reply_text)) // 4,
            },
            "meta_vm": {
                "vm_id": client.vm_id,
                "session_id": session_id,
            },
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Lỗi khi gửi prompt tới Muse AI: {str(e)}"}), 500


if __name__ == "__main__":
    print(f"Khởi động Meta Muse AI API Gateway trên http://127.0.0.1:{PORT}...")
    app.run(host="0.0.0.0", port=PORT, debug=False)
