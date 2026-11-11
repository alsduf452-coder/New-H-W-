param([switch]$EnableManual)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$pythonw = Join-Path $PSScriptRoot '.venv\Scripts\pythonw.exe'
$launcher = Join-Path $PSScriptRoot 'background_launcher.py'
foreach ($file in @($pythonw,$launcher,(Join-Path $PSScriptRoot 'run_daily.ps1'),(Join-Path $PSScriptRoot 'token.dpapi'))) {
    if (!(Test-Path -LiteralPath $file)) {throw "Required file missing: $file"}
}
$names = @('HW-Excel-Classic-Daily-0900','HW-Excel-Classic-Manual-Requests')
# Validate both existing tasks before changing either one. Triggers/principals/settings are retained.
$tasks = @($names | ForEach-Object {Get-ScheduledTask -TaskName $_ -ErrorAction Stop})
foreach ($task in $tasks) {
    $suffix = if ($task.TaskName -eq $names[1]) {' --manual'} else {''}
    $action = New-ScheduledTaskAction -Execute $pythonw -Argument ('"'+$launcher+'"'+$suffix) -WorkingDirectory $PSScriptRoot
    Set-ScheduledTask -TaskName $task.TaskName -Action $action | Out-Null
}
if ($EnableManual) {Enable-ScheduledTask -TaskName $names[1] | Out-Null}
Get-ScheduledTask -TaskName $names | Select-Object TaskName,State,@{Name='Program';Expression={$_.Actions.Execute}} | Format-Table -AutoSize
Write-Host 'Background launcher configured. No token change or new sync request was made.'
Write-Host 'Pause/absence settings still apply. PC must be logged in and Q: accessible.'
Write-Host 'Existing daily failure markers are preserved; inspect logs if a request is not processed.'
