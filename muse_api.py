"""
Meta Muse AI (Project Hatch) SDK & API Engine
Developed by ENI Tier 3 for Anh Tú.
Provides direct interaction with Meta Muse AI personal VM via WebSocket Noise-XX encryption.
"""

import json
import os
import struct
import time
import urllib.parse
import uuid
import secrets
from typing import Optional, Dict, Any, List, Generator

from curl_cffi import requests as rq
from curl_cffi.requests import WebSocket
from noise.connection import NoiseConnection, Keypair
from google.protobuf import descriptor_pb2, descriptor_pool, message_factory

GATEWAY_HOST = "hatch.metaaivm.com"
DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36"
)

# Protobuf message setup
_pool = descriptor_pool.DescriptorPool()
_DIR = os.path.dirname(os.path.abspath(__file__))

for _i in (0, 1):
    _desc_path = os.path.join(_DIR, f"desc{_i}.bin")
    if os.path.exists(_desc_path):
        _fd = descriptor_pb2.FileDescriptorProto()
        with open(_desc_path, "rb") as _fh:
            _fd.ParseFromString(_fh.read())
        _pool.Add(_fd)

def _get_msg(name: str):
    return message_factory.GetMessageClass(_pool.FindMessageTypeByName(name))

NoiseTransportFrame = _get_msg("ingress_rev_proxy.NoiseTransportFrame")
ServiceRequest = _get_msg("hatch.noise.ServiceRequest")
ServiceResponse = _get_msg("hatch.noise.ServiceResponse")
ServiceFrame = _get_msg("hatch.noise.ServiceFrame")
ApplicationRequest = _get_msg("hatch.noise.ApplicationRequest")

# Load routes
ROUTES_PATH = os.path.join(_DIR, "routes.json")
if os.path.exists(ROUTES_PATH):
    with open(ROUTES_PATH, "r", encoding="utf-8") as _rf:
        ROUTES = {e["method"]: e for e in json.load(_rf)}
else:
    ROUTES = {}

SERVICE_IDS = {"daemon": 0, "sentinel": 1, "vault": 2, "authd": 3}


class MuseAuthError(Exception):
    pass


class MuseGatewayError(Exception):
    def __init__(self, status: int, payload: Any):
        super().__init__(f"Gateway Error (status={status}): {payload!r}")
        self.status = status
        self.payload = payload


class MuseClient:
    """Client kết nối trực tiếp đến Personal VM của Meta Muse AI."""

    def __init__(self, cookies_str: Optional[str] = None, cookies_path: str = "cookies.txt"):
        if cookies_str:
            self.cookies = cookies_str.strip()
        elif os.path.exists(cookies_path):
            with open(cookies_path, "r", encoding="utf-8") as f:
                self.cookies = f.read().strip()
        else:
            raise MuseAuthError(f"Không tìm thấy cookies tại {cookies_path} và không có cookies_str")

        self.node_id = secrets.token_hex(8)
        self.access_token: Optional[str] = None
        self.vm_id: Optional[str] = None
        self.hatch_token: Optional[str] = None
        self.ws: Optional[WebSocket] = None
        self.noise: Optional[NoiseConnection] = None
        self.stream_id = 1

    def _headers(self, with_auth: bool = True) -> Dict[str, str]:
        h = {
            "User-Agent": DEFAULT_UA,
            "Referer": "https://muse.ai/",
            "Origin": "https://muse.ai",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": self.cookies,
        }
        if with_auth and self.access_token:
            h["Authorization"] = f"Bearer {self.access_token}"
        return h

    def authenticate(self) -> None:
        """Lấy Access Token và khám phá VM ID được phân bổ."""
        # 1. Auth check
        resp = rq.post(
            "https://muse.ai/api/auth/check",
            headers=self._headers(with_auth=False),
            data=b"",
            impersonate="chrome",
            timeout=20,
        )
        if resp.status_code != 200:
            raise MuseAuthError(f"api/auth/check thất bại ({resp.status_code}): {resp.text[:200]}")
        data = resp.json()
        self.access_token = data.get("access_token")
        if not self.access_token:
            raise MuseAuthError("Không tìm thấy access_token trong phản hồi auth/check")

        # 2. Session info
        resp_sess = rq.get(
            "https://muse.ai/api/session",
            headers=self._headers(with_auth=True),
            impersonate="chrome",
            timeout=20,
        )
        if resp_sess.status_code != 200:
            raise MuseAuthError(f"api/session thất bại ({resp_sess.status_code}): {resp_sess.text[:200]}")
        sess_data = resp_sess.json()
        self.vm_id = sess_data.get("vm_id")
        if not self.vm_id:
            raise MuseGatewayError(-1, f"Không tìm thấy vm_id: {sess_data}")

        # 3. Hatch token
        resp_token = rq.post(
            "https://muse.ai/api/hatch/token",
            headers=self._headers(with_auth=True),
            json={"vmAddress": f"wss://{self.vm_id}.metaaivm.com/", "vmName": self.vm_id},
            impersonate="chrome",
            timeout=20,
        )
        if resp_token.status_code != 200:
            raise MuseAuthError(f"api/hatch/token thất bại ({resp_token.status_code}): {resp_token.text[:200]}")
        self.hatch_token = resp_token.json().get("token")

    def connect(self) -> None:
        """Thiết lập kết nối WebSocket và bắt tay mật mã Noise-XX."""
        if not self.access_token or not self.vm_id or not self.hatch_token:
            self.authenticate()

        url = (
            f"wss://{GATEWAY_HOST}/v1/noise?vm_id={self.vm_id}"
            f"&auth_token={urllib.parse.quote(self.hatch_token, safe='')}"
        )
        self.ws = WebSocket()
        self.ws.connect(url, impersonate="chrome", timeout=25, verify=True)

        noise = NoiseConnection.from_name(b"Noise_XX_25519_AESGCM_SHA256")
        noise.set_as_initiator()
        noise.set_keypair_from_private_bytes(Keypair.STATIC, os.urandom(32))
        noise.start_handshake()

        # Step 1: Client sends e
        self.ws.send_bytes(bytes(noise.write_message(b"")))
        # Step 2: Server responds e, ee, s, es
        m2, _ = self.ws.recv()
        noise.read_message(bytes(m2))
        # Step 3: Client sends s, se
        self.ws.send_bytes(bytes(noise.write_message(b"")))

        if not noise.handshake_finished:
            raise RuntimeError("Noise-XX handshake không hoàn tất thành công")

        self.noise = noise
        self.stream_id = 1

    def close(self) -> None:
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
            self.ws = None

    def _send_envelope(self, service_id: int, frame_bytes: bytes) -> None:
        outer = ServiceRequest(service=service_id, payload=frame_bytes)
        chunk_id = struct.unpack("<q", os.urandom(8))[0]
        fr = NoiseTransportFrame(
            chunk_id=chunk_id, chunk_index=0, total_chunks=1, payload=outer.SerializeToString()
        )
        self.ws.send_bytes(bytes(self.noise.encrypt(fr.SerializeToString())))

    def _open_stream(self, method: str, body: Any = None, query: Optional[Dict] = None, path_params: Optional[Dict] = None) -> int:
        if method not in ROUTES:
            raise ValueError(f"Method '{method}' không tồn tại trong routes.json")
        route = ROUTES[method]
        path = route["path"]
        if path_params:
            for k, v in path_params.items():
                path = path.replace("{" + k + "}", urllib.parse.quote(str(v), safe=""))
        if query:
            qs = urllib.parse.urlencode({k: v for k, v in query.items() if v is not None})
            if qs:
                path = path + ("&" if "?" in path else "?") + qs

        raw = b"" if body is None else (body if isinstance(body, bytes) else json.dumps(body).encode())
        req = ApplicationRequest(verb=route.get("http", "GET"), path=path, body=raw, end_body=True)
        h = req.headers.add()
        h.key = "x-request-id"
        h.value = str(uuid.uuid4())
        if raw:
            h2 = req.headers.add()
            h2.key = "content-type"
            h2.value = "application/json"

        frame = ServiceFrame(stream_id=self.stream_id)
        frame.request.CopyFrom(req)
        sid = self.stream_id
        self.stream_id += 1

        service_name = route.get("service", "daemon")
        self._send_envelope(SERVICE_IDS.get(service_name, 0), frame.SerializeToString())
        return sid

    def request(self, method: str, body: Any = None, query: Optional[Dict] = None, path_params: Optional[Dict] = None, timeout: float = 40.0) -> Dict[str, Any]:
        """Gọi đồng bộ một RPC method và nhận response JSON đầy đủ."""
        if not self.ws or not self.noise:
            self.connect()

        sid = self._open_stream(method, body=body, query=query, path_params=path_params)
        chunks = []
        status = None
        deadline = time.time() + timeout

        while time.time() < deadline:
            data, _ = self.ws.recv()
            pt = bytes(self.noise.decrypt(bytes(data)))
            ntf = NoiseTransportFrame()
            ntf.ParseFromString(pt)
            sr = ServiceResponse()
            sr.ParseFromString(ntf.payload)
            sf = ServiceFrame()
            sf.ParseFromString(sr.payload)

            if sf.stream_id != sid:
                continue

            kind = sf.WhichOneof("kind")
            if kind == "response":
                status = sf.response.status
                if sf.response.body:
                    chunks.append(bytes(sf.response.body))
                if sf.response.end_body:
                    break
            elif kind == "body_chunk":
                chunks.append(bytes(sf.body_chunk.data))
                if sf.body_chunk.end_body:
                    break
            elif kind == "reset":
                raise MuseGatewayError(-1, f"Stream reset code {sf.reset.code}: {sf.reset.reason}")

        if status is None:
            raise TimeoutError(f"Hết thời gian chờ phản hồi ({timeout}s) cho method {method}")

        raw_bytes = b"".join(chunks)
        if not raw_bytes:
            return {"status": status, "data": None}
        try:
            return json.loads(raw_bytes.decode("utf-8"))
        except Exception:
            return {"status": status, "raw": raw_bytes.decode("utf-8", errors="replace")}

    # -- High-level convenience methods --

    def get_sessions(self) -> List[Dict[str, Any]]:
        """Lấy danh sách các session / thread trò chuyện."""
        res = self.request("sessions.list")
        if isinstance(res, dict) and "result" in res:
            return res["result"].get("sessions", [])
        return res.get("sessions", [])

    def get_history(self, session_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """Lấy lịch sử tin nhắn của một thread hoặc toàn bộ."""
        params = {"limit": limit}
        if session_id:
            params["session_id"] = session_id
        res = self.request("chat.history", body=params)
        events = res.get("result", {}).get("chat_events", []) if "result" in res else res.get("chat_events", [])
        
        parsed = []
        for e in events:
            p = e.get("payload", {}) if isinstance(e.get("payload"), dict) else {}
            role = p.get("role") or e.get("role") or ("assistant" if "assistant" in e.get("event_name", "") else "user")
            text = p.get("display_text") or p.get("content") or e.get("display_text") or ""
            parsed.append({
                "seq": e.get("seq"),
                "role": role,
                "message_id": p.get("message_id") or e.get("message_id"),
                "text": text,
                "created_at_ms": p.get("started_at_ms") or e.get("occurred_at_ms"),
            })
        return parsed

    def send_message(self, text: str, session_id: Optional[str] = None, wait_reply: bool = True, timeout: float = 60.0) -> Dict[str, Any]:
        """Gửi prompt / tin nhắn đến Muse AI và chờ câu trả lời."""
        if not self.ws:
            self.connect()

        scope = {"session_id": session_id} if session_id else {}
        baseline_seq = 0
        try:
            h = self.request("chat.history", body={"limit": 1, **scope})
            evs = h.get("result", {}).get("chat_events", []) if "result" in h else h.get("chat_events", [])
            if evs:
                baseline_seq = max(e.get("seq", 0) for e in evs)
        except Exception:
            pass

        params = {
            "items": [{"type": "text", "text": text}],
            "node_id": self.node_id,
            "capabilities": {},
        }
        if session_id:
            params["session_id"] = session_id

        stream_sid = self._open_stream("chat.stream", body=params)
        if not wait_reply:
            return {"sent": True, "stream_id": stream_sid}

        # Poll history for genuine assistant reply
        reply = None
        deadline = time.time() + timeout
        while time.time() < deadline and reply is None:
            time.sleep(3)
            try:
                h = self.request("chat.history", body={"limit": 5, **scope})
            except Exception:
                continue

            evs = h.get("result", {}).get("chat_events", []) if "result" in h else h.get("chat_events", [])
            for ev in sorted(evs, key=lambda e: e.get("seq", 0)):
                if ev.get("seq", 0) <= baseline_seq:
                    continue
                p = ev.get("payload", {}) if isinstance(ev.get("payload"), dict) else {}
                role = p.get("role") or ("assistant" if "assistant" in ev.get("event_name", "") else None)
                if role == "assistant":
                    content = p.get("display_text") or p.get("content") or ev.get("display_text")
                    if content:
                        reply = {
                            "seq": ev.get("seq"),
                            "role": "assistant",
                            "message_id": p.get("message_id") or ev.get("message_id"),
                            "text": content,
                            "status": p.get("status", "completed"),
                        }
                        if p.get("status") == "completed" or not p.get("status"):
                            break

        if reply:
            return {"sent": True, "reply": reply}
        return {"sent": True, "reply": None, "note": f"Hết thời gian chờ phản hồi ({timeout}s)"}

    def vm_health(self) -> Dict[str, Any]:
        """Kiểm tra sức khoẻ VM cá nhân."""
        return self.request("vm.health")
