@echo off
title MedEdge Intelligence - Direct Tunnel Server
:: Always run from the directory containing this script
cd /d "%~dp0"

echo ============================================================
echo   MedEdge Intelligence - Direct Cloudflare Tunnel Server
echo ============================================================
echo.
echo   Starting local FastAPI backend on http://127.0.0.1:8000 ...
echo.

start /B python -m uvicorn main:app --host 0.0.0.0 --port 8000

timeout /t 3 /nobreak >nul

echo.
echo   Starting Cloudflare Tunnel (Direct Access - No IP Prompts)...
echo   Keep this window open to maintain the live connection!
echo.
.\cloudflared.exe tunnel --url http://127.0.0.1:8000 --edge-ip-version 4 --protocol http2
