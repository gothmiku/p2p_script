@echo off
setlocal

REM --- Configuration ---
set CERT_FILE=cert.pem
set KEY_FILE=key.pem
set CONFIG_FILE=config.json
set PYTHON_SCRIPT=p2p.py

REM --- Check for OpenSSL ---
where openssl >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] OpenSSL is not installed or not in PATH.
    pause
    exit /b
)

REM --- Generate certs if missing ---
if not exist %CERT_FILE% (
    echo [INFO] Generating TLS certificate and key...
    openssl req -new -x509 -days 365 -nodes -out %CERT_FILE% -keyout %KEY_FILE% -subj "/CN=Peer"
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to generate TLS cert.
        pause
        exit /b
    )
    echo [INFO] TLS certificate generated successfully.
) else (
    echo [INFO] TLS certificate already exists: %CERT_FILE%
)

REM --- Check Python installation ---
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    pause
    exit /b
)

REM --- Run Python script ---
echo [INFO] Starting P2P sharing script...
python %PYTHON_SCRIPT%

pause
