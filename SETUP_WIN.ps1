# J.A.R.V.I.S Windows Setup Script
# Run this in PowerShell as Administrator if possible

Write-Host "🚀 Starting J.A.R.V.I.S Windows Setup..." -ForegroundColor Cyan

# 1. Check Python
if (!(Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Python not found. Please install Python 3.12+ from python.org" -ForegroundColor Red
    exit
}

# 2. Create Virtual Environment
if (!(Test-Path "venv")) {
    Write-Host "📦 Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

# 3. Activate and Install
Write-Host "🛠️ Installing dependencies..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"
python -m pip install --upgrade pip

# Special handling for common Windows issues
Write-Host "💡 Note: If 'dlib' or 'pyaudio' fail, ensure you have Visual Studio C++ Build Tools installed." -ForegroundColor Magenta

pip install -r requirements.txt

# 4. Environment File
if (!(Test-Path ".env")) {
    Write-Host "📝 Creating .env from template..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "⚠️  Please edit your .env file and set CLAW_PATH and other variables!" -ForegroundColor Cyan
}

# 5. Model check
Write-Host "🤖 Remember to run 'ollama pull gemma2:2b' to get the brain ready." -ForegroundColor Green

Write-Host "`n✅ Setup complete! Run J.A.R.V.I.S with: python main_async.py" -ForegroundColor Green
