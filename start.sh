#!/usr/bin/env bash
#
# Meta Muse AI API Gateway & Control Center - Launcher for macOS / Linux
# Port: 7777
#

set -e

echo "========================================================"
echo "      META MUSE AI API GATEWAY & CONTROL CENTER"
echo "========================================================"
echo ""

# Kiểm tra file cookies.txt
if [ ! -f "cookies.txt" ]; then
    echo "[CANH BAO] Khong tim thay file cookies.txt!"
    echo "Vui long tao file cookies.txt va dan cookie Muse vao do."
    echo ""
    exit 1
fi

COOKIE_SIZE=$(wc -c < "cookies.txt")
if [ "$COOKIE_SIZE" -lt 20 ]; then
    echo "[THONG BAO] File cookies.txt dang trong hoac chua co cookie hop le!"
    echo "Vui long mo file cookies.txt va dan cookie tu trinh duyet vao truoc khi chay."
    echo ""
    exit 1
fi

# Kich hoa moit truong an neu co
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

echo "[1/2] Dang kiem tra thu vien Python..."
python3 -m pip install -r requirements.txt --quiet --no-warn-script-location

echo "[2/2] Dang khoi dong API Server tren cong 7777..."
echo ""
echo "========================================================"
echo " * Web Dashboard: http://localhost:7777"
echo " * OpenAI API Base: http://localhost:7777/v1"
echo " * Quick Ask API: http://localhost:7777/api/ask?prompt=..."
echo "========================================================"
echo ""

exec python3 server.py