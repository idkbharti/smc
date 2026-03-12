@echo off
setlocal

echo Starting SMC Terminal (Real Time Stack)...
echo.

:: Check for Python dependencies
echo [1/4] Checking Python dependencies...
python -m pip install -r "%~dp0terminal\requirements.txt" --quiet

echo [2/4]echo Launching Plotly Terminal...
python terminal/app.py
pause

:: Check for Node dependencies
echo [3/4] Checking Frontend dependencies...
cd /d "%~dp0terminal\frontend"
if not exist "node_modules" (
    echo node_modules not found, running npm install...
    call npm install
)

:: Start Vite Frontend
echo [4/4] Starting Frontend (Vite)...
npm run dev -- --open

pause
