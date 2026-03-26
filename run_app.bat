@echo off
title TikTok Auto Video Generator
color 0A

echo ==================================================
echo       TikTok Auto Video Generator (Affiliate SaaS)
echo ==================================================
echo.

if not exist venv (
    echo [1/3] Creating Virtual Environment...
    python -m venv venv
)

echo [2/3] Installing Required Packages...
venv\Scripts\python.exe -m pip install --upgrade pip >nul 2>&1
venv\Scripts\python.exe -m pip install google-generativeai pydantic python-dotenv moviepy==1.0.3 edge-tts streamlit pillow

echo.
echo ==================================================
echo [OK] Ready! Starting Web Application...
echo ==================================================
echo (Please do NOT close this black window)
echo.

venv\Scripts\python.exe -m streamlit run app.py

pause
