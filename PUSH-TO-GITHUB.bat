@echo off
cd /d "%~dp0"
echo.
echo === B-nexus push to github.com/ronald6mk/bnexus ===
echo.
echo STEP 1: Log in to GitHub CLI (browser will open once)
echo.
gh auth login -h github.com -p https -w
if errorlevel 1 (
  echo gh auth failed. Install/login manually: https://cli.github.com
  pause
  exit /b 1
)

echo.
echo STEP 2: Create repo ronald6mk/bnexus if missing, then push
echo.
gh repo view ronald6mk/bnexus >nul 2>&1
if errorlevel 1 (
  gh repo create bnexus --public --source=. --remote=origin --push
) else (
  git branch -M main
  git remote remove origin 2>nul
  git remote add origin https://github.com/ronald6mk/bnexus.git
  git push -u origin main
)

echo.
echo Done. Open: https://github.com/ronald6mk/bnexus
echo Next: Render.com -^> New Web Service -^> connect ronald6mk/bnexus
pause
