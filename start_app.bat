@echo off
echo Starting Asset Tracker Application...
echo.
echo The application will open in your browser automatically.
echo.
echo Login Credentials:
echo   Username: admin
echo   Password: admin123
echo.
timeout /t 2 /nobreak >nul
start http://localhost:8501
streamlit run app.py

