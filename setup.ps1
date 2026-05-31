# setup.ps1
$ErrorActionPreference = "Stop"

Write-Output "--- Initializing Python ETL Toolkit Scaffold ---"

# Step 1: Verify Python availability
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Error: Python is not recognized. Please install Python 3.10+ and ensure it is on your PATH."
    exit 1
}

# FIX: Use $() subexpression so PowerShell expands the command output inside the string
$version = python -c "import sys; print(sys.version_info[0], sys.version_info[1], sep='.')"
Write-Output "Detected Python Version: $($version)"

# Step 2: Create virtual environment if it doesn't already exist
if (Test-Path -Path ".venv") {
    Write-Output "Virtual environment .venv already exists. Skipping creation."
} else {
    Write-Output "Creating isolated virtual environment in .venv ..."
    python -m venv .venv
}

# Step 3: Activate the virtual environment
Write-Output "Activating virtual environment..."
& .venv\Scripts\Activate.ps1

# Step 4: Upgrade pip
Write-Output "Upgrading pip..."
python -m pip install --upgrade pip --quiet

# Step 5: Install dependencies based on mode flag
if ($args[0] -eq "--dev") {
    Write-Output "Installing DEVELOPMENT dependencies (prod + linters + testing)..."
    pip install -r requirements/dev.txt
} else {
    Write-Output "Installing PRODUCTION dependencies..."
    pip install -r requirements/prod.txt
}

# Step 6: Set up .env if it doesn't exist
if (-not (Test-Path -Path ".env")) {
    Write-Output ""
    Write-Output "Creating .env from .env.example ..."
    Copy-Item ".env.example" ".env"
    Write-Output "ACTION REQUIRED: Open .env and fill in your API credentials before running the pipeline."
} else {
    Write-Output ".env already exists. Skipping."
}

Write-Output ""
Write-Output "Setup completed successfully!"
Write-Output ""
Write-Output "Next steps:"
Write-Output "  1. Fill in your credentials in .env"
Write-Output "  2. Run the pipeline  : python run_pipeline.py"
Write-Output "  3. Run the tests     : pytest tests/ -v"
