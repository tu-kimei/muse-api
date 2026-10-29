"""
Meta Muse AI - CLI & Control Center
Developed by ENI Tier 3 for Anh Tú.
"""

import sys
import io
import json
import argparse
from muse_api import MuseClient

# Ensure UTF-8 output on Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def cmd_status(args):
    print("Đang kết nối đến Meta Muse VM Gateway...")
    client = MuseClient()
    client.connect()
    print(f"Xác thực thành công!")
    print(f"- VM ID: {client.vm_id}")
    print(f"- Node ID: {client.node_id}")
    print(f"- Access Token: {client.access_token[:24]}...")
    print(f"- Hatch Token: {client.hatch_token[:24]}...")
    health = client.vm_health()
    print(f"- VM Health: {health.get('status', 'OK')}")
    client.close()


def cmd_sessions(args):
    client = MuseClient()
    client.connect()
    sessions = client.get_sessions()
    print(f"=== DANH SÁCH SESSIONS CỦA ANH TÚ ({len(sessions)}) ===")
    for idx, s in enumerate(sessions):
        title = s.get("title") or "Không tiêu đề"
        sid = s.get("session_id")
        unread = s.get("unread_count", 0)
        snippet = s.get("snippet", "")
        if snippet:
            snippet = snippet.replace("\n", " ")[:60] + "..."
        print(f"[{idx+1}] {title}")
        print(f"    - ID: {sid}")
        print(f"    - Unread: {unread} | Snippet: {snippet}")
    client.close()


def cmd_history(args):
    client = MuseClient()
    client.connect()
    history = client.get_history(session_id=args.thread, limit=args.limit)
    print(f"=== LỊCH SỬ TIN NHẮN ({len(history)} tin) ===")
    for h in history:
        role = h.get("role", "unknown").upper()
        text = h.get("text", "")
        seq = h.get("seq", 0)
        print(f"[{seq}] {role}: {text}")
        print("-" * 50)
    client.close()


def cmd_send(args):
    client = MuseClient()
    client.connect()
    prompt = " ".join(args.prompt)
    print(f"Đang gửi prompt tới Muse AI: {repr(prompt)}")
    res = client.send_message(text=prompt, session_id=args.thread, wait_reply=True, timeout=args.timeout)
    reply = res.get("reply")
    if reply:
        print("\n=== PHẢN HỒI TỪ MUSE AI ===")
        print(reply.get("text", ""))
    else:
        print("Không nhận được câu trả lời từ Muse AI hoặc hết thời gian chờ.")
        print("Chi tiết raw:", json.dumps(res, indent=2, ensure_ascii=False))
    client.close()


def cmd_server(args):
    from server import app
    print(f"Khởi động OpenAI-compatible API Server trên http://127.0.0.1:{args.port}...")
    app.run(host="0.0.0.0", port=args.port, debug=False)


def main():
    parser = argparse.ArgumentParser(description="Công cụ tương tác và bắt API Meta Muse AI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # status
    subparsers.add_parser("status", help="Kiểm tra kết nối và trạng thái VM")

    # sessions
    subparsers.add_parser("sessions", help="Lấy danh sách các cuộc trò chuyện")

    # history
    p_hist = subparsers.add_parser("history", help="Lấy lịch sử hội thoại")
    p_hist.add_argument("--thread", "-t", default=None, help="ID của session/thread")
    p_hist.add_argument("--limit", "-n", type=int, default=15, help="Số lượng tin nhắn")

    # send
    p_send = subparsers.add_parser("send", help="Gửi prompt và nhận câu trả lời")
    p_send.add_argument("prompt", nargs="+", help="Nội dung prompt")
    p_send.add_argument("--thread", "-t", default=None, help="ID session (nếu có)")
    p_send.add_argument("--timeout", type=float, default=60.0, help="Thời gian chờ tối đa")

    # server
    p_server = subparsers.add_parser("server", help="Chạy REST API Server chuẩn OpenAI")
    p_server.add_argument("--port", "-p", type=int, default=7777, help="Cổng chạy server (mặc định: 7777)")

    args = parser.parse_args()

    if args.command == "status":
        cmd_status(args)
    elif args.command == "sessions":
        cmd_sessions(args)
    elif args.command == "history":
        cmd_history(args)
    elif args.command == "send":
        cmd_send(args)
    elif args.command == "server":
        cmd_server(args)


if __name__ == "__main__":
    main()
