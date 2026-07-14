@echo off
chcp 65001 >nul
setlocal EnableExtensions

cd /d "%~dp0"

set "PY=%~dp0.venv\Scripts\python.exe"
set "PYTORCH_PACKAGES=torch torchvision torchaudio"
set "PYTORCH_CUDA_TAG=cu128"
set "PYTORCH_CUDA_INDEX_URL=https://download.pytorch.org/whl/%PYTORCH_CUDA_TAG%"
set "PYTORCH_CPU_INDEX_URL=https://download.pytorch.org/whl/cpu"
set "PYTORCH_CUDA_INSTALL_ARGS=--upgrade --force-reinstall %PYTORCH_PACKAGES% --index-url %PYTORCH_CUDA_INDEX_URL%"
set "PYTORCH_CPU_INSTALL_ARGS=--upgrade --force-reinstall %PYTORCH_PACKAGES% --index-url %PYTORCH_CPU_INDEX_URL%"
set "INSTALL_MODE=CPU"
set "VERIFY_EXPECTED=cpu"
set "NVIDIA_GPU=0"

echo [1/12] 프로젝트 폴더로 이동
echo %CD%

echo [2/12] Python 3.11 확인
if exist "%PY%" (
    echo 기존 .venv가 있어 .venv Python으로 버전을 확인합니다.
) else (
    py -3.11 -c "import sys; print(sys.executable); print(sys.version)"
    if errorlevel 1 (
        echo [ERROR] Python 3.11을 찾을 수 없습니다. Python 3.11을 설치한 뒤 다시 실행하세요.
        exit /b 1
    )
)

echo [3/12] 가상환경 확인
if not exist "%PY%" (
    echo .venv가 없어 Python 3.11로 생성합니다.
    py -3.11 -m venv "%~dp0.venv"
    if errorlevel 1 (
        echo [ERROR] .venv 생성에 실패했습니다.
        exit /b 1
    )
)

echo [4/12] .venv 활성화
if not exist "%~dp0.venv\Scripts\activate.bat" (
    echo [ERROR] .venv\Scripts\activate.bat를 찾을 수 없습니다.
    exit /b 1
)
call "%~dp0.venv\Scripts\activate.bat"
if errorlevel 1 (
    echo [ERROR] .venv 활성화에 실패했습니다.
    exit /b 1
)
echo VIRTUAL_ENV=%VIRTUAL_ENV%

echo [5/12] .venv Python 확인
if not exist "%PY%" (
    echo [ERROR] .venv\Scripts\python.exe를 찾을 수 없습니다.
    exit /b 1
)
"%PY%" -c "import sys; print(sys.executable); print(sys.version)"
if errorlevel 1 (
    echo [ERROR] .venv Python 실행에 실패했습니다.
    exit /b 1
)

echo [6/12] pip, setuptools, wheel 업데이트
"%PY%" -m pip install --upgrade pip setuptools wheel
if errorlevel 1 (
    echo [ERROR] pip, setuptools, wheel 업데이트에 실패했습니다.
    exit /b 1
)

echo [7/12] NVIDIA GPU 확인
where nvidia-smi >nul 2>&1
if not errorlevel 1 (
    nvidia-smi -L
    nvidia-smi -L | findstr /I /C:"GPU " >nul 2>&1
    if not errorlevel 1 (
        set "NVIDIA_GPU=1"
        echo [INFO] nvidia-smi에서 NVIDIA GPU를 확인했습니다.
    ) else (
        echo [INFO] nvidia-smi는 있지만 NVIDIA GPU 목록을 확인하지 못했습니다.
    )
) else (
    echo [INFO] nvidia-smi를 찾을 수 없습니다. Windows 비디오 컨트롤러 목록을 확인합니다.
)

if "%NVIDIA_GPU%"=="0" (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$gpu = Get-CimInstance Win32_VideoController -ErrorAction SilentlyContinue | Where-Object { $_.Name -match 'NVIDIA' }; if ($gpu) { $gpu | ForEach-Object { $_.Name }; exit 0 }; exit 1"
    if not errorlevel 1 (
        set "NVIDIA_GPU=1"
        echo [INFO] Windows 비디오 컨트롤러 목록에서 NVIDIA GPU를 확인했습니다.
    ) else (
        echo [INFO] NVIDIA GPU를 찾지 못했습니다. CPU 모드로 설치합니다.
    )
)

echo [8/12] PyTorch 선설치
if "%NVIDIA_GPU%"=="1" (
    set "INSTALL_MODE=CUDA"
    set "VERIFY_EXPECTED=cuda"
    echo [INFO] NVIDIA GPU 환경입니다. CUDA PyTorch를 먼저 설치합니다.
    echo "%PY%" -m pip install %PYTORCH_CUDA_INSTALL_ARGS%
    "%PY%" -m pip install %PYTORCH_CUDA_INSTALL_ARGS%
    if errorlevel 1 (
        echo [ERROR] CUDA PyTorch 설치에 실패했습니다.
        exit /b 1
    )
) else (
    set "INSTALL_MODE=CPU"
    set "VERIFY_EXPECTED=cpu"
    echo [INFO] NVIDIA GPU가 없어 CPU PyTorch를 설치합니다.
    echo "%PY%" -m pip install %PYTORCH_CPU_INSTALL_ARGS%
    "%PY%" -m pip install %PYTORCH_CPU_INSTALL_ARGS%
    if errorlevel 1 (
        echo [ERROR] CPU PyTorch 설치에 실패했습니다.
        exit /b 1
    )
)

echo [9/12] PyTorch CUDA/CPU 검증
if "%INSTALL_MODE%"=="CUDA" (
    "%PY%" "%~dp0scripts\verify_torch_install.py" --expected cuda --summary
    if errorlevel 1 (
        echo [ERROR] NVIDIA GPU가 감지되었지만 CUDA PyTorch 검증에 실패했습니다.
        exit /b 1
    )
) else (
    "%PY%" "%~dp0scripts\verify_torch_install.py" --expected cpu --summary
    if errorlevel 1 (
        echo [ERROR] CPU PyTorch 검증에 실패했습니다.
        exit /b 1
    )
)

echo [10/12] stable-ts editable install
"%PY%" -m pip install -e . --upgrade-strategy only-if-needed
if errorlevel 1 (
    echo [ERROR] stable-ts editable 설치에 실패했습니다.
    exit /b 1
)

echo [11/12] Gradio 및 추가 GUI 의존성 설치
"%PY%" -m pip install -r requirements-windows.txt --upgrade-strategy only-if-needed
if errorlevel 1 (
    echo [ERROR] Windows GUI 추가 의존성 설치에 실패했습니다.
    exit /b 1
)

echo [12/12] 최종 실행 테스트
"%PY%" -c "import stable_whisper, gradio; print('stable-ts and Gradio import OK')"
if errorlevel 1 (
    echo [ERROR] stable-ts 또는 Gradio import 테스트에 실패했습니다.
    exit /b 1
)

"%PY%" -m pip check
if errorlevel 1 (
    echo [ERROR] pip check에 실패했습니다.
    exit /b 1
)

"%PY%" "%~dp0scripts\verify_torch_install.py" --expected %VERIFY_EXPECTED% --summary
if errorlevel 1 (
    echo [ERROR] 최종 PyTorch 검증에 실패했습니다.
    exit /b 1
)

echo 설치 및 기본 검증이 완료되었습니다.
echo 설치 모드: %INSTALL_MODE%
