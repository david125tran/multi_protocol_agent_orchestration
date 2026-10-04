@echo off

cd /d "%~dp0"

echo Starting A2A-REST-MCP FastAPI app...
echo.

uvicorn app.main:app --reload --reload-include "*.py" --reload-include "*.yaml" --reload-include "*.json"

pause