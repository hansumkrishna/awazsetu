@echo off
REM Preflight self-test. Run before a demo; it changes nothing and downloads nothing.
setlocal
cd /d "%~dp0"
set "AWAZ_HOME=%~dp0"
set "AWAZ_MODELS_DIR=%AWAZ_HOME%models"
set "AWAZ_BIN_DIR=%AWAZ_HOME%runtime\bin"
set "AWAZ_LLM_DIR=%AWAZ_HOME%models\llm"
set "HF_HOME=%AWAZ_HOME%models\hf-cache"
set "HF_HUB_OFFLINE=1"
set "TRANSFORMERS_OFFLINE=1"
set "PATH=%AWAZ_HOME%runtime\bin;%PATH%"
set "PYTHONIOENCODING=utf-8"
"%AWAZ_HOME%runtime\python\python.exe" "%AWAZ_HOME%scripts\doctor.py"
pause
