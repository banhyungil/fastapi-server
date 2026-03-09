@echo off
chcp 65001 >nul
echo ============================================
echo   FastAPI Server - 환경 설치
echo ============================================
echo.

:: 1) Python 가상환경
if not exist ".venv" (
    echo [1/3] 가상환경 생성 중...
    python -m venv .venv
) else (
    echo [1/3] 가상환경 이미 존재 — 건너뜀
)

:: 가상환경 활성화
call .venv\Scripts\activate.bat

:: 2) Python 패키지
echo [2/3] Python 패키지 설치 중...
pip install -r requirements.txt --quiet

:: 3) 시스템 라이브러리 — libvips
echo [3/3] libvips 설치 확인 중...
:: call 해줘야 다시 현재 스택으로 돌아와 그 다음 라인이 진행됨.
call setup_vips.bat

echo.
echo ============================================
echo   설치 완료!
echo.
echo   서버 실행: uvicorn app.main:app --reload
echo   테스트:    pytest -v
echo ============================================
