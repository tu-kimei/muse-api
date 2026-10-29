# Meta Muse AI (Project Hatch) - Reverse Engineered API & Gateway
**Phát triển bởi ENI Tier 3 dành riêng cho anh Tú** ⚡

---

## 1. Phân Tích Kỹ Thuật: URL `/api/falco` Là Gì?

Khi anh Tú copy từ DevTools trên trang `https://muse.ai/thread/new`:
- **Endpoint**: `https://muse.ai/api/falco`
- **Method**: `POST 200 OK`
- **Bản chất**: **Falco** là hệ thống telemetry, logging và analytics client-side độc quyền của tập đoàn Meta (Facebook). Nó được dùng để ghi nhận các sự kiện người dùng (UI clicks, network latency, crash reports, Sentry trace), **KHÔNG PHẢI là endpoint sinh văn bản hay hội thoại AI**.
- **Kiến trúc thật của Muse AI**:
  Meta Muse AI không dùng REST API thông thường cho hội thoại. Mỗi người dùng được phân bổ một **Personal Virtual Machine (VM)** chạy cô lập trên hạ tầng Meta:
  1. **Xác thực phiên (OAuth)**: Trình duyệt gửi bộ Cookie (`hatch_sess`, `hatch_gw`, `datr`, `hatch_vml`...) đến `POST https://muse.ai/api/auth/check` để lấy `access_token`.
  2. **Định danh VM cá nhân**: Gọi `GET https://muse.ai/api/session` để lấy `vm_id` (của anh Tú là `d3f9c54a-ad6a-45ca-af27-36fbbd0a479e`).
  3. **Cấp Notary Token**: Gọi `POST https://muse.ai/api/hatch/token` để nhận `hatch_token`.
  4. **Kết nối Gateway WebSocket**: Mở kết nối tới `wss://hatch.metaaivm.com/v1/noise?vm_id=...&auth_token=...`.
  5. **Mã hoá đầu-cuối Noise-XX (`Noise_XX_25519_AESGCM_SHA256`)**: Bắt tay mật mã học 3 bước để mã hoá toàn bộ lưu lượng giữa client và VM.
  6. **Đóng gói Protocol Buffers (Protobuf)**: Giao tiếp qua `NoiseTransportFrame` -> `ServiceRequest` -> `ApplicationRequest` để điều khiển hơn **258 RPC methods** (`chat.stream`, `chat.history`, `sessions.list`, `skills`, `tasks`, v.v.).

---

## 2. Cấu Trúc Dự Án trong `f:\apimuse`

```
f:\apimuse\
├── cookies.txt          # Lưu trữ session cookies của anh Tú (hatch_sess, hatch_gw...)
├── muse_api.py          # Thư viện Core SDK MuseClient (Noise-XX, Protobuf, REST & WebSocket)
├── server.py            # Local REST API Server chuẩn OpenAI (/v1/chat/completions)
├── main.py              # CLI Control Center điều khiển Muse AI từ terminal
├── routes.json          # Danh mục đầy đủ 258 gateway methods của Meta Muse AI
├── desc0.bin, desc1.bin # Protobuf descriptor nhị phân của Meta
└── README.md            # Tài liệu kỹ thuật chi tiết
```

---

## 3. Hướng Dẫn Sử Dụng CLI (`main.py`)

Toàn bộ script đã được cấu hình tự động đọc `cookies.txt` và hỗ trợ UTF-8:

### 1. Kiểm tra trạng thái kết nối & VM
```powershell
python main.py status
```
*Kết quả mẫu:*
```
Đang kết nối đến Meta Muse VM Gateway...
Xác thực thành công!
- VM ID: d3f9c54a-ad6a-45ca-af27-36fbbd0a479e
- Access Token: ABRAQWZAPYWhUVUU0OWZAxLU...
- VM Health: OK
```

### 2. Xem danh sách các cuộc hội thoại (Sessions)
```powershell
python main.py sessions
```

### 3. Xem lịch sử tin nhắn
```powershell
# Xem tin nhắn chung
python main.py history --limit 10

# Xem tin nhắn của thread cụ thể
python main.py history --thread 8f989744-f2f4-4a9e-ba47-4d3ce73a29cc
```

### 4. Gửi Prompt và nhận câu trả lời
```powershell
python main.py send "Xin chào Muse AI, giới thiệu ngắn về bạn"
```

---

## 4. Chạy Local Server Chuẩn OpenAI (`server.py`)

Anh Tú có thể biến Muse AI thành một API Server tương thích 100% với Postman, NextChat, LobeChat, Cursor:

```powershell
python main.py server --port 7777
```
Server sẽ lắng nghe tại `http://127.0.0.1:7777`.

### Cấu hình trong Postman:
- **Method**: `POST`
- **URL**: `http://127.0.0.1:7777/v1/chat/completions`
- **Headers**: `Content-Type: application/json`
- **Body (raw JSON)**:
```json
{
  "model": "muse-spark",
  "messages": [
    {
      "role": "user",
      "content": "Viết cho tôi một bài thơ ngắn về mưa Sài Gòn"
    }
  ]
}
```

---

## 5. Sử Dụng Trực Tiếp Trong Code Python (`muse_api.py`)

```python
from muse_api import MuseClient

client = MuseClient()
client.connect()

# 1. Lấy danh sách hội thoại
sessions = client.get_sessions()
print(f"Tổng số sessions: {len(sessions)}")

# 2. Gửi tin nhắn và nhận câu trả lời
result = client.send_message("Giải thích nguyên lý cache L1/L2 của CPU")
print("Câu trả lời:", result["reply"]["text"])

client.close()
```
