@echo off
TITLE Fanta-Dashboard Launcher
COLOR 0A

echo ========================================================
echo   AVVIO FANTA-DASHBOARD IN CORSO...
echo   (Non chiudere questa finestra nera)
echo ========================================================
echo.

:: 1. Si sposta nella cartella dove si trova questo file
cd /d "%~dp0"

:: 2. Lancia l'applicazione
streamlit run app.py

:: 3. Se si chiude per errore, lascia la finestra aperta per leggere l'errore
pause