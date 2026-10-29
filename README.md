# Meta Muse AI (Project Hatch) - API Gateway & SDK

Reverse-engineered API gateway, CLI và Python SDK để tương tác trực tiếp với **Personal Virtual Machine (VM)** của Meta Muse AI — thay thế đường dẫn browser WebSocket/Protobuf độc quyền.

Phát triển bởi **ENI Tier 3** dành riêng cho anh Tú.

---

## 🏗️ Kiến trúc tổng quan

Meta Muse AI không dùng REST API thông thường cho hội thoại. Mỗi người dùng được phân bổ một **Personal Virtual Machine (VM)** chạy cô isolates trên hạ tầng Meta:

```
┌─────────────────┐      ┌─────────────────────────────────────────┐
│   User / CLI    │─────►│  main.py  (CLI Control Center)           │
│   Browser       │─────►│  server.py (OpenAI-compatible REST)     │
│   Postman/Cursor│─────►│                                         │
└─────────────────┘      └──────────────┬───────────────────────────┘
                                        │
        ┌───────────────────────────────┼─────────────────────────────┐
        ▼                               ▼                               ▼
   ┌──────────┐                   ┌──────────┐                    ┌──────────┐
   │ Cluster  │                   │ Cluster  │                    │ Cluster  │
   │ CLI CP   │                   │ Gateway  │                    │ Transport│
   │ (main.py)│                   │ (server) │                    │ (muse_api)│
   └────┬─────┘                   └────┬─────┘                    └────┬─────┘
        │                              │                               │
        └──────────────────────────────┴───────────────────────────────┘
                                           │
                                           ▼
                                  ┌────────────────┐
                                  │ Meta Muse VM GW│
                                  │ wss://.../noise│
                                  │ Noise-XX + PB  │
                                  └────────────────┘
```

Luồng kết nối chuẩn (6 bước):

1. **Xác thực phiên (OAuth)**: Gửi cookie → `POST https://muse.ai/api/auth/check` lấy `access_token`
2. **Định danh VM cá nhân**: `GET https://muse.ai/api/session` lấy `vm_id`
3. **Cấp Notary Token**: `POST https://muse.ai/api/hatch/token` nhận `hatch_token`
4. **Kết nối Gateway WebSocket**: `wss://hatch.metaaivm.com/v1/noise?vm_id=...&auth_token=...`
5. **Mã hóa đầu-cuối Noise-XX** (`Noise_XX_25519_AESGCM_SHA256`): bắt tay mật mã 3 bước
6. **Đóng gói Protocol Buffers**: `NoiseTransportFrame` → `ServiceRequest` → `ApplicationRequest` điều khiển hơn **258 RPC methods** (`chat.stream`, `chat.history`, `sessions.list`, …)

---

## 📁 Cấu trúc dự án

```
muse-api/
├── README.md            # Tài liệu này
├── ARCHITECTURE.md      # Tài liệu kiến trúc chi tiết (tự sinh từ GitNexus knowledge graph)
├── main.py              # CLI Control Center (status, sessions, history, send, server)
├── server.py            # Local REST API Server chuẩn OpenAI (port 7777)
├── muse_api.py          # Core SDK: MuseClient (Noise-XX, Protobuf, REST + WebSocket)
├── routes.json          # Danh mục 258 gateway methods của Meta Muse AI
├── desc0.bin, desc1.bin # Protobuf descriptor nhị phân của Meta
├── requirements.txt     # Thư viện Python cần thiết
├── start.bat            # Launcher cho Windows
├── start.sh             # Launcher cho macOS / Linux
└── cookies.txt          # (gitignored) Lưu session cookies của bạn
```

---

## 🖥️ Yêu cầu hệ thống

- **macOS / Linux / Windows**
- Python 3.8+
- `pip` (hoặc `pip3`)
- File `cookies.txt` chứa session cookies của bạn từ `https://muse.ai`

---

## 🚀 Cài đặt (macOS)

### 1. Clone repository

```bash
git clone https://github.com/tu-kimei/muse-api.git
cd muse-api
```

### 2. Tạo file cookies.txt

Truy cập `https://muse.ai` bằng trình duyệt, mở DevTools → Application → Cookies, sao chép toàn bộ chuỗi cookie vào file `cookies.txt` ở gốc dự án.

```bash
# Ví dụ nội dung cookies.txt
hatch_sess=xxx; hatch_gw=yyy; datr=zzz; hatch_vml=www
```

### 3. Cài đặt thư viện Python

```bash
pip3 install -r requirements.txt
```

Thư viện cần thiết:
- `curl_cffi` — HTTP client Impersonate Chrome (bypass TLS fingerprint)
- `noiseprotocol` — Mã hóa Noise-XX
- `protobuf` — Serialization Protocol Buffers
- `flask` — Web server cho API gateway

### 4. Chạy launcher (macOS / Linux)

```bash
chmod +x start.sh
./start.sh
```

Hoặc chạy thủ công:

```bash
# CLI
python3 main.py status

# API Server (OpenAI-compatible, port 7777)
python3 server.py
```

---

## 💻 Sử dụng CLI (`main.py`)

```bash
# 1. Kiểm tra kết nối & VM
python3 main.py status

# 2. Xem danh sách phiên trò chuyện
python3 main.py sessions

# 3. Xem lịch sử tin nhắn
python3 main.py history --limit 10
python3 main.py history --thread <thread_id>

# 4. Gửi prompt và nhận trả lời
python3 main.py send "Xin chào Muse AI, giới thiệu về bạn"
python3 main.py send "Giải thích cache L1/L2" --thread <thread_id> --timeout 120

# 5. Chạy API Server chuẩn OpenAI
python3 main.py server --port 7777
```

---

## 🌐 Sử dụng API Server (`server.py`)

Khởi động server:

```bash
python3 server.py
# Lắng nghe tại http://127.0.0.1:7777
```

### Web Dashboard
Truy cập `http://localhost:7777` bằng trình duyệt để test gửi prompt trực tiếp.

### Endpoints chính

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `GET` | `/` | Web Dashboard / JSON status |
| `GET` | `/api/status` | Trạng thái VM & kết nối |
| `GET` | `/v1/models` | Danh sách model (`muse-spark`, `muse-code`, `muse-wonder`) |
| `GET` | `/v1/sessions` | Danh sách phiên trò chuyện |
| `GET` | `/v1/history?session_id=...&limit=20` | Lịch sử tin nhắn |
| `POST` | `/api/chat` | Gửi prompt đơn giản (`?prompt=...` hoặc JSON body) |
| `GET` | `/api/ask` | Gửi prompt qua query string |
| `POST` | `/v1/chat/completions` | Chuẩn OpenAI Chat Completions (cho Postman, NextChat, Cursor) |

### Ví dụ gọi API bằng cURL

```bash
# OpenAI-compatible chat completions
curl -X POST http://localhost:7777/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "muse-spark", "messages": [{"role": "user", "content": "Xin chào Muse AI"}]}'

# Simple chat
curl "http://localhost:7777/api/ask?prompt=Xin%20ch%C3%A0o"

# Status
curl http://localhost:7777/api/status
```

### Cấu hình Postman / NextChat / Cursor

- **Base URL**: `http://localhost:7777/v1`
- **Chat endpoint**: `POST /chat/completions`
- **Headers**: `Content-Type: application/json`
- **Body**:
  ```json
  {
    "model": "muse-spark",
    "messages": [{"role": "user", "content": "Câu hỏi của bạn"}]
  }
  ```

---

## 🐍 Sử dụng trực tiếp trong code Python (`muse_api.py`)

```python
from muse_api import MuseClient

client = MuseClient()  # tự đọc cookies.txt
client.connect()

# 1. Lấy danh sách hội thoại
sessions = client.get_sessions()
print(f"Tổng số sessions: {len(sessions)}")

# 2. Gửi tin nhắn và nhận trả lời
result = client.send_message("Giải thích nguyên lý cache L1/L2 của CPU")
print("Câu trả lời:", result["reply"]["text"])

client.close()
```

---

## 🔑 Lưu ý quan trọng

- **`cookies.txt`** là bắt buộc. Nếu thiếu hoặc không có cookie hợp lệ, các thao tác xác thực sẽ thất bại.
- Repository này **không chứa** file `cookies.txt` (đã gitignore) vì nó chứa thông tin phiên đăng nhập cá nhân.
- User-Agent mặc định đã được điều chỉnh để tương thích với macOS.
- Cổng mặc định của API Server là **7777**.

---

## 📄 Tài liệu liên quan

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — Kiến trúc chi tiết, các nhóm chức năng (clusters), luồng thực thi (execution flows) và sơ đồ Mermaid (sinh từ GitNexus knowledge graph).
- [`routes.json`](routes.json) — Danh mục đầy đủ 258 gateway methods.

---

> ⚠️ **Lưu ý pháp lý**: Dự án này là công cụ reverse-engineering cho mục đích học tập và tự động hóa cá nhân. Vui lòng tuân thủ điều khoản dịch vụ của Meta Muse AI khi sử dụng.