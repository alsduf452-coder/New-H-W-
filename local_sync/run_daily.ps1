param([switch]$Manual)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$stage = 'TOKEN_FILE'
try {
    $encrypted = (Get-Content -LiteralPath (Join-Path $PSScriptRoot 'token.dpapi') -Raw).Trim()
    $stage = 'TOKEN_DECRYPT'
    $secure = ConvertTo-SecureString $encrypted
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try { $env:LOCAL_SYNC_TOKEN = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer) }
    $stage = 'PYTHON_MISSING'
    $python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    if (!(Test-Path -LiteralPath $python)) { throw 'Missing Python' }
    $stage = 'SCRIPT_MISSING'
    $script = if ($Manual) { 'manual_sync.py' } else { 'daily_sync.py' }
    if (!(Test-Path -LiteralPath (Join-Path $PSScriptRoot $script))) { throw 'Missing script' }
    $stage = 'PYTHON_START'
    & $python (Join-Path $PSScriptRoot $script)
    $result = $LASTEXITCODE
} catch {
    # Log stage only: never include token or raw exception text.
    $message = "$(Get-Date -Format s) Launcher failed: $stage"
    New-Item -ItemType Directory -Path "$PSScriptRoot\daily-state" -Force | Out-Null
    Add-Content -LiteralPath "$PSScriptRoot\daily-state\launcher.log" -Value $message -Encoding UTF8
    Write-Host $message
    $result = 1
} finally {
    Remove-Item Env:LOCAL_SYNC_TOKEN -ErrorAction SilentlyContinue
}
exit $result
