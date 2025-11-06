# Asset Tracker Startup Script
Write-Host "Starting Asset Tracker Application..." -ForegroundColor Green
Write-Host ""
Write-Host "The application will open in your browser automatically." -ForegroundColor Yellow
Write-Host ""
Write-Host "Login Credentials:" -ForegroundColor Cyan
Write-Host "  Username: admin" -ForegroundColor White
Write-Host "  Password: admin123" -ForegroundColor White
Write-Host ""
Write-Host "Waiting for server to start..." -ForegroundColor Gray
Start-Sleep -Seconds 3
Start-Process "http://localhost:8501"
Write-Host "Starting Streamlit server..." -ForegroundColor Green
streamlit run app.py

