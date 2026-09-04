@echo off
echo Starting Alpaca Trading Agent API Server...
echo.
echo The API server will be available at: http://localhost:8000
echo The dashboard API will be available at: http://localhost:8000/api/dashboard
echo.
echo To view the dashboard, open: dashboard-html/index.html
echo (Or serve it with a static server to avoid CORS issues)
echo.
echo Press Ctrl+C to stop the server
echo.
uvicorn backend.app.main:app --reload