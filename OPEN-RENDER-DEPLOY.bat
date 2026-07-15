@echo off
echo Opening Render one-click deploy for ronald6mk/bnexus ...
echo.
echo After the page loads:
echo  1. Sign in with GitHub (ronald6mk)
echo  2. Apply free instance
echo  3. Click Apply / Create Web Service
echo  4. Wait until status is Live
echo  5. Copy the URL (https://bnexus-xxxx.onrender.com)
echo.
start "" "https://render.com/deploy?repo=https://github.com/ronald6mk/bnexus"
timeout /t 2 >nul
start "" "https://dashboard.render.com/select-repo?type=web"
echo Browser opened. Complete Sign in + Create on the free plan.
pause
