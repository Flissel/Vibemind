@echo off
REM Quick test for GitHub agent with OpenRouter

echo ============================================
echo GitHub Agent OpenRouter Quick Test
echo ============================================
echo.

echo Creating session...
curl -X POST http://127.0.0.1:8765/api/sessions ^
  -H "Content-Type: application/json" ^
  -d "{\"name\": \"github-quick-test\", \"model\": \"gpt-4\", \"tools\": [\"github\"], \"task\": \"List popular Python repositories\"}" ^
  > session.json

echo.
echo Session created. Starting...
echo.

REM Extract session_id (simple approach - assumes format)
for /f "tokens=2 delims=:," %%a in ('findstr "session_id" session.json') do (
    set SESSION_ID=%%a
)
set SESSION_ID=%SESSION_ID:"=%
set SESSION_ID=%SESSION_ID: =%

echo Session ID: %SESSION_ID%
echo.

REM Start session
curl -X POST http://127.0.0.1:8765/api/sessions/%SESSION_ID%/start ^
  -H "Content-Type: application/json" ^
  -d "{}"

echo.
echo.
echo Waiting 10 seconds for agent to process...
timeout /t 10 /nobreak > nul

echo.
echo Checking events...
curl -s http://127.0.0.1:8765/api/mcp/github/sessions/%SESSION_ID%/events > events.json

echo.
echo Event log saved to events.json
echo.

REM Check for OpenRouter usage
findstr /C:"OpenRouter" events.json > nul
if %errorlevel% equ 0 (
    echo [SUCCESS] OpenRouter integration detected!
    findstr /C:"Using model" events.json | findstr /C:"github"
) else (
    echo [WARNING] OpenRouter not detected - using legacy config
)

echo.
echo Check for errors:
findstr /C:"error" events.json | findstr /V /C:"error_count"

echo.
echo ============================================
echo Test complete
echo ============================================
echo.
echo Full event log available in events.json
echo Session response in session.json

del session.json
