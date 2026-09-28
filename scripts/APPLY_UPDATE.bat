@echo off
REM ============================================================================
REM  AwazSetu - apply this update to an existing installation.
REM
REM  Put this file (and the rest of the update zip) INTO your AwazSetu folder,
REM  next to AwazSetu.bat, then double-click it.
REM
REM  It does the things that extracting a zip cannot:
REM
REM    * deletes every compiled .pyc cache. Python only reuses a cache when it
REM      looks newer than the source, and extracting an archive preserves the
REM      original timestamps - so a stale cache can shadow a file you just
REM      replaced, and the update appears not to have worked.
REM    * deletes documents this release withdrew. Extracting adds and replaces
REM      files; it never removes one.
REM    * corrects terminology in subtitles that were generated before the
REM      glossary knew about it, in place, without re-running any model.
REM    * rebuilds only the voiceovers whose words actually changed.
REM
REM  Your videos, uploads and settings are never touched.
REM ============================================================================
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo.
echo   AwazSetu - applying update
echo   ==========================
echo.

REM ---- 0. refuse to run anywhere except an AwazSetu folder ------------------
set "PY=%~dp0runtime\python\python.exe"
if not exist "%PY%" goto :wrongplace
if not exist "%~dp0app\run.py" goto :wrongplace

REM ---- same environment the application runs in ----------------------------
set "AWAZ_HOME=%~dp0"
set "AWAZ_MODELS_DIR=%AWAZ_HOME%models"
set "AWAZ_BIN_DIR=%AWAZ_HOME%runtime\bin"
set "AWAZ_LLM_DIR=%AWAZ_HOME%models\llm"
set "HF_HOME=%AWAZ_HOME%models\hf-cache"
set "HF_HUB_OFFLINE=1"
set "TRANSFORMERS_OFFLINE=1"
set "AWAZ_OFFLINE=1"
set "PATH=%AWAZ_HOME%runtime\bin;%PATH%"
set "PYTHONIOENCODING=utf-8"
set "PYTHONDONTWRITEBYTECODE=1"

REM ---- 1. compiled caches, only where sources actually changed --------------
echo   [1/6] removing compiled Python caches
"%PY%" "%~dp0scripts\clean_caches.py"

REM ---- 2. documents this release withdrew ----------------------------------
echo   [2/6] removing superseded documents
for %%f in (DELIVERY_PLAN.md SUBMISSION.md TASKS.md) do (
  if exist "%~dp0docs\%%f" ( del /q "%~dp0docs\%%f" & echo         docs\%%f )
)

REM ---- 3. stale derived files ----------------------------------------------
echo   [3/6] removing stale exports and scratch files
del /s /q "%~dp0app\data\work\bundle.mkv" >nul 2>&1
for /d %%w in ("%~dp0app\data\work\*") do (
  if exist "%%w\bundle.mkv"   del /q "%%w\bundle.mkv"
  if exist "%%w\voice_in.webm" del /q "%%w\voice_in.webm"
  if exist "%%w\voice_q.json"  del /q "%%w\voice_q.json"
  if exist "%%w\voice_ans.wav" del /q "%%w\voice_ans.wav"
  if exist "%%w\voice_ans.txt" del /q "%%w\voice_ans.txt"
  if exist "%%w\status.json"   del /q "%%w\status.json"
)

REM ---- 4. terminology in existing subtitles --------------------------------
echo   [4/6] correcting terminology in existing subtitles
"%PY%" "%~dp0scripts\apply_glossary.py"
if errorlevel 1 echo         WARNING: subtitle correction reported a problem

REM ---- 5. voiceovers whose words changed -----------------------------------
echo.
echo   [5/6] rebuilding only the voiceovers whose words changed
echo         (this is the slow step - a few minutes per track, and it may
echo          legitimately find nothing to do)
"%PY%" "%~dp0scripts\redub_changed.py"
if errorlevel 1 echo         WARNING: voiceover refresh reported a problem

REM ---- 6. preflight --------------------------------------------------------
echo.
echo   [6/6] checking the installation
"%PY%" "%~dp0scripts\doctor.py"
if errorlevel 1 goto :notready

echo.
echo   Update applied.
echo.
echo   One last thing: your browser remembers the language you chose last time
echo   in a cookie. That is intentional. If the interface looks unchanged,
echo   press Ctrl+F5 once on the page.
echo.
REM /noprompt lets this run unattended, which is how it is tested.
if /i "%~1"=="/noprompt" goto :done
choice /c YN /m "  Start AwazSetu now"
if errorlevel 2 goto :done
start "" "%~dp0AwazSetu.bat"
goto :done

:wrongplace
echo   This file is not in an AwazSetu folder.
echo.
echo   Put it next to AwazSetu.bat, alongside runtime\ models\ and app\,
echo   then run it again. Extracting the update zip into that folder puts
echo   everything in the right place by itself.
echo.
pause
exit /b 1

:notready
echo.
echo   The check above did not pass. Nothing is broken by this script - it only
echo   deleted caches and corrected text. Read the failing line above; it names
echo   exactly which component is unhappy.
echo.
pause
exit /b 1

:done
echo.
if /i not "%~1"=="/noprompt" pause
