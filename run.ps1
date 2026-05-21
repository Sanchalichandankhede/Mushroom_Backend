$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $projectRoot

$venvPath = Join-Path $projectRoot ".venv"
if (-Not (Test-Path "$venvPath\Scripts\Activate.ps1")) {
    Write-Host "Creating virtual environment..."
    python -m venv $venvPath
}

Write-Host "Activating virtual environment..."
& "$venvPath\Scripts\Activate.ps1"

Write-Host "Upgrading pip and installing dependencies..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

Write-Host "Starting Mushroom backend..."
python main.py

Pop-Location
