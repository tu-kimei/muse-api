@echo off
chcp 65001 >nul
title Meta Muse AI API Gateway (Port 7777)

echo ========================================================
echo       META MUSE AI API GATEWAY & CONTROL CENTER
echo ========================================================
echo.

if not exist "cookies.txt" (
    echo [CANH BAO] Khong tim thay file cookies.txt!
    echo Vui long tao file cookies.txt va dan cookie Muse vao do.
    echo.
    pause
    exit /b
)

for %%A in ("cookies.txt") do if %%~zA lss 20 (
    echo [THONG BAO] File cookies.txt dang trong hoac chua co cookie hop le!
    echo Vui long mo file cookies.txt va dan cookie tu trinh duyet vao truoc khi chay.
    echo.
    pause
    exit /b
)

echo [1/2] Dang kiem tra thu vien Python...
python -m pip install -r requirements.txt --quiet --no-warn-script-location

echo [2/2] Dang khoi dong API Server tren cong 7777...
echo.
echo ========================================================
echo  * Web Dashboard: http://localhost:7777
echo  * OpenAI API Base: http://localhost:7777/v1
echo  * Quick Ask API: http://localhost:7777/api/ask?prompt=...
echo ========================================================
echo.

python server.py
pause
