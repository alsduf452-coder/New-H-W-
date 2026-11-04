param([switch]$Manual)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
try {
    # ConvertFrom-SecureString uses Windows DPAPI for this Windows user.
    $encrypted = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'token.dpapi') -Raw
    $secure = ConvertTo-SecureString $encrypted
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try { $env:LOCAL_SYNC_TOKEN = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer) }
    $script = if ($Manual) { "manual_sync.py" } else { "daily_sync.py" }
    & "$PSScriptRoot\.venv\Scripts\python.exe" "$PSScriptRoot\$script"
    $result = $LASTEXITCODE
} catch {
    # Do not log exception contents, tokens, or database credentials.
    New-Item -ItemType Directory -Path "$PSScriptRoot\daily-state" -Force | Out-Null
    Add-Content -LiteralPath "$PSScriptRoot\daily-state\launcher.log" -Value "$(Get-Date -Format s) Scheduled launcher failed. Check Python installation and saved token." -Encoding UTF8
    $result = 1
} finally {
    Remove-Item Env:LOCAL_SYNC_TOKEN -ErrorAction SilentlyContinue
}
exit $result
