@echo off

echo ============================================
echo   Image Processing App Update
echo ============================================
echo.

echo [1/3] Pulling latest images...
docker compose pull

echo.
echo [2/3] Restarting services...
docker compose up -d

echo.
echo [3/3] Status check
docker compose ps

echo.
echo Update complete!
pause
