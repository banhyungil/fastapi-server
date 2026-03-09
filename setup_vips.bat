@echo off
chcp 65001 >nul

set "VIPS_URL=https://github.com/libvips/build-win64-mxe/releases/download/v8.18.0/vips-dev-w64-web-8.18.0.zip"
set "DOWNLOAD_PATH=%TEMP%\vips.zip"
set "INSTALL_DIR=C:\tools"
set "VIPS_BIN=%INSTALL_DIR%\vips-dev-8.18\bin"

:: 1) 다운로드
echo [1/3] libvips 다운로드 중...
curl -L -o "%DOWNLOAD_PATH%" "%VIPS_URL%"
if %errorlevel% neq 0 (
    echo 다운로드 실패
    exit /b 1
)

:: 2) 압축 해제
echo [2/3] C:\tools에 압축 해제 중...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
tar -xf "%DOWNLOAD_PATH%" -C "%INSTALL_DIR%"
del "%DOWNLOAD_PATH%"

:: 3) 시스템 PATH에 등록 (영구)
echo [3/3] PATH 등록 중...
reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path | findstr /i "%VIPS_BIN%" >nul 2>&1
if %errorlevel% neq 0 (
    for /f "tokens=2,*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path') do set "CURRENT_PATH=%%B"
    setx /M Path "%CURRENT_PATH%;%VIPS_BIN%"
    echo PATH 등록 완료. 새 터미널에서 적용됩니다.
) else (
    echo 이미 PATH에 등록됨 — 건너뜀
)

echo 완료!
