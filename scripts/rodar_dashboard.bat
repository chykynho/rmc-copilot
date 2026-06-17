@echo off
setlocal

cd /d "%~dp0\.."

if not exist "%cd%\.rmc_win\Scripts\python.exe" (
    echo ERRO: ambiente virtual nao encontrado em:
    echo %cd%\.rmc_win
    pause
    exit /b 1
)

"%cd%\.rmc_win\Scripts\python.exe" -m streamlit run app\dashboard_streamlit.py --server.address 0.0.0.0 --server.port 8501

pause
