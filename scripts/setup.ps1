param([string]$ProjectRoot = (Get-Location).Path)
$ErrorActionPreference = "Stop"
Set-Location $ProjectRoot
python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)"
if (-not (Test-Path ".venv\Scripts\python.exe")) { python -m venv .venv }
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -e ".[dev]"
& $VenvPython -m quattroagents setup --project $ProjectRoot --providers codex,claude --profile economy --install-mcp recommended --yes
& $VenvPython -m quattroagents doctor --project $ProjectRoot --json
& $VenvPython -m quattroagents validate --project $ProjectRoot --json
