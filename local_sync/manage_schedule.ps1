$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$taskName = 'HW-Excel-Classic-Daily-0900'
$settingsPath = Join-Path $PSScriptRoot 'schedule.json'
function Save-Settings($settings) {
    $settings | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $settingsPath -Encoding UTF8
}
if (!(Test-Path -LiteralPath $settingsPath)) {
    Save-Settings @{paused=$false;absence=@()}
}
while ($true) {
    Write-Host "`n1. Register daily 09:00 task / save token"
    Write-Host '2. Pause sync'
    Write-Host '3. Resume sync (absence dates still apply)'
    Write-Host '4. Add absence period (inclusive)'
    Write-Host '5. Clear absence periods'
    Write-Host '6. Show settings and task status'
    Write-Host '7. Remove scheduled task'
    Write-Host '0. Exit'
    $choice = Read-Host 'Select'
    try {
        $settings = Get-Content -LiteralPath $settingsPath -Raw | ConvertFrom-Json
        switch ($choice) {
            '1' {
                if (!(Test-Path '.venv\Scripts\python.exe')) {throw 'Run install.bat in this folder first.'}
                if (!(Test-Path 'config.toml')) {throw 'Copy your config.toml into this folder first.'}
                $token = Read-Host 'Enter SYNC_TOKEN for hw-excel-sync-classic (hidden)' -AsSecureString
                if ($token.Length -lt 43) {throw 'Token must contain at least 43 characters.'}
                ConvertFrom-SecureString $token | Set-Content -LiteralPath "$PSScriptRoot\token.dpapi" -Encoding ASCII
                $user = [Security.Principal.WindowsIdentity]::GetCurrent().Name
                $action = New-ScheduledTaskAction -Execute "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -Argument "-NoProfile -NonInteractive -ExecutionPolicy RemoteSigned -WindowStyle Hidden -File `"$PSScriptRoot\run_daily.ps1`"" -WorkingDirectory $PSScriptRoot
                $trigger = New-ScheduledTaskTrigger -Daily -At '09:00'
                $principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
                $options = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 20) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
                # No StartWhenAvailable, WakeToRun, or RestartCount: no catch-up/retry.
                Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $options -Force | Out-Null
                Write-Host 'Registered: daily 09:00, current user logged in only. No wake/catch-up/retry.'
                Write-Host 'Keep Windows time zone set to Korea. Stop any old start.bat watcher.'
            }
            '2' {$settings.paused=$true;Save-Settings $settings;Write-Host 'Paused.'}
            '3' {$settings.paused=$false;Save-Settings $settings;Write-Host 'Resumed. Next eligible 09:00 only.'}
            '4' {
                $start = Read-Host 'First absent day (YYYY-MM-DD)'
                $end = Read-Host 'Last absent day (YYYY-MM-DD)'
                $first = [datetime]::ParseExact($start,'yyyy-MM-dd',[Globalization.CultureInfo]::InvariantCulture)
                $last = [datetime]::ParseExact($end,'yyyy-MM-dd',[Globalization.CultureInfo]::InvariantCulture)
                if ($last -lt $first) {throw 'End must not precede start.'}
                $settings.absence = @($settings.absence) + @{start=$start;end=$end}
                Save-Settings $settings;Write-Host 'Absence period saved.'
            }
            '5' {$settings.absence=@();Save-Settings $settings;Write-Host 'Absence periods cleared.'}
            '6' {
                $settings | ConvertTo-Json -Depth 5 | Write-Host
                Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue | Select-Object TaskName,State
                Get-ScheduledTaskInfo -TaskName $taskName -ErrorAction SilentlyContinue | Select-Object LastRunTime,LastTaskResult,NextRunTime
                Write-Host "Logs: $PSScriptRoot\daily-state"
            }
            '7' {Unregister-ScheduledTask -TaskName $taskName -Confirm:$false;Write-Host 'Task removed. Files retained.'}
            '0' {exit 0}
            default {Write-Host 'Choose 0 through 7.'}
        }
    } catch {Write-Host ('Could not complete: '+$_.Exception.Message)}
}
