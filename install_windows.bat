@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"

echo [1/10] 프로젝트 폴더로 이동
echo %CD%

echo [2/10] Python 3.11 확인
py -3.11 -c "import sys; print(sys.executable); print(sys.version)" >nul 2>&1
if errorlevel 1 (
    echo Python 3.11을 찾을 수 없습니다. Python 3.11을 설치한 뒤 다시 실행하세요.
    exit /b 1
)

echo [3/10] 가상환경 확인
if not exist "%~dp0.venv\Scripts\python.exe" (
    echo .venv가 없어 Python 3.11로 생성합니다.
    py -3.11 -m venv "%~dp0.venv"
    if errorlevel 1 exit /b 1
)

echo [4/10] .venv Python 확인
if not exist "%~dp0.venv\Scripts\python.exe" (
    echo .venv\Scripts\python.exe를 찾을 수 없습니다.
    exit /b 1
)
set "PY=%~dp0.venv\Scripts\python.exe"
"%PY%" -c "import sys; print(sys.executable); print(sys.version)"
if errorlevel 1 exit /b 1

echo [5/10] pip, setuptools, wheel 업데이트
"%PY%" -m pip install --upgrade pip setuptools wheel
if errorlevel 1 exit /b 1

echo [6/10] stable-ts editable install
"%PY%" -m pip install -e .
if errorlevel 1 exit /b 1

echo [7/10] Windows 추가 의존성 설치
"%PY%" -m pip install -r requirements-windows.txt
if errorlevel 1 exit /b 1

echo [8/10] stable_whisper import 테스트
"%PY%" -c "import stable_whisper; print('stable-ts import OK')"
if errorlevel 1 exit /b 1

echo [9/10] NVIDIA, torch 및 CUDA 상태
where nvidia-smi >nul 2>&1
if errorlevel 1 (
    echo nvidia-smi를 찾을 수 없습니다. NVIDIA 드라이버 또는 PATH 상태를 확인하세요.
) else (
    nvidia-smi
)
"%PY%" -c "import torch; print('torch', torch.__version__); print('cuda available', torch.cuda.is_available()); print('torch cuda', torch.version.cuda)"
if errorlevel 1 exit /b 1

echo [10/10] pip check
"%PY%" -m pip check
if errorlevel 1 exit /b 1

echo 설치 및 기본 검증이 완료되었습니다.
