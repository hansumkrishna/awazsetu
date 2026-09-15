@echo off
REM ============================================================================
REM  AwazSetu - double-click launcher.
REM
REM  Requires NOTHING to be installed. No Python, no FFmpeg, no Ollama, no PATH
REM  changes, no pip, no internet. Everything it needs sits next to this file:
REM      runtime\python\   embedded Python 3.10 with every package preinstalled
REM      runtime\bin\      ffmpeg.exe + ffprobe.exe
REM      models\           ASR / translation / voice / chat weights
REM
REM  Nothing is written outside this folder, so the whole thing can live on a USB
REM  stick and be deleted by dragging the folder to the bin.
REM ============================================================================
setlocal
cd /d "%~dp0"
set "AWAZ_HOME=%~dp0"

REM --- self-contained model + binary locations -------------------------------
set "AWAZ_MODELS_DIR=%AWAZ_HOME%models"
set "AWAZ_BIN_DIR=%AWAZ_HOME%runtime\bin"
set "AWAZ_LLM_DIR=%AWAZ_HOME%models\llm"
set "HF_HOME=%AWAZ_HOME%models\hf-cache"

REM --- hard offline: the app cannot reach the network even if one is present --
set "HF_HUB_OFFLINE=1"
set "TRANSFORMERS_OFFLINE=1"
set "AWAZ_OFFLINE=1"

REM --- bundled ffmpeg first, so a stray system copy cannot shadow it ----------
set "PATH=%AWAZ_HOME%runtime\bin;%PATH%"
set "PYTHONIOENCODING=utf-8"
set "PYTHONDONTWRITEBYTECODE=1"

set "AWAZ_PY=%AWAZ_HOME%runtime\python\python.exe"
if not exist "%AWAZ_PY%" (
  echo.
  echo   ERROR: runtime\python\python.exe is missing.
  echo   This package is incomplete - re-extract it, keeping the folder intact.
  echo.
  pause
  exit /b 1
)

echo.
echo   AwazSetu - starting. Everything runs on this machine, offline.
echo   A browser tab will open at http://127.0.0.1:5000
echo   Close this window to stop the application.
echo.

REM Give the server a moment before the browser asks for the page.
start "" /b cmd /c "timeout /t 3 /nobreak >nul & start "" http://127.0.0.1:5000"
"%AWAZ_PY%" "%AWAZ_HOME%app\run.py"

echo.
echo   AwazSetu has stopped.
pause
