@echo off
echo Starting SMC Terminal...
echo.

:: Start the Python Backend in a new window
echo Starting Backend (server.py)...
start cmd /k "python server.py"

:: Move to the frontend directory and start Vite
echo Starting Frontend (npm run dev)...
cd frontend && npm run dev
