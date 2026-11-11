$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$taskName = 'HW-Excel-Classic-Daily-0900'
$manualTask = 'HW-Excel-Classic-Manual-Requests'
$settingsPath = Join-Path $PSScriptRoot 'schedule.json'
function Save-Settings($settings) {
    $settings | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $settingsPath -Encoding UTF8
}
if (!(Test-Path -LiteralPath $settingsPath)) {
    Save-Settings @{paused=$false;absence=@()}
}
while ($true) {
    Write-Host "`n1. Register 09:00 + manual request tasks / save token"
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
                if (!(Test-Path '.venv\Scripts\pythonw.exe')) {throw 'Run install.bat in this folder first.'}
                if (!(Test-Path 'config.toml')) {throw 'Copy your config.toml into this folder first.'}
                if (!(Test-Path 'background_launcher.py')) {throw 'Update background_launcher.py first.'}
                $token = Read-Host 'Enter SYNC_TOKEN for hw-excel-sync-classic (hidden)' -AsSecureString
                if ($token.Length -lt 43) {throw 'Token must contain at least 43 characters.'}
                ConvertFrom-SecureString $token | Set-Content -LiteralPath "$PSScriptRoot\token.dpapi" -Encoding ASCII
                $user = [Security.Principal.WindowsIdentity]::GetCurrent().Name
                $action = New-ScheduledTaskAction -Execute "$PSScriptRoot\.venv\Scripts\pythonw.exe" -Argument "`"$PSScriptRoot\background_launcher.py`"" -WorkingDirectory $PSScriptRoot
                $trigger = New-ScheduledTaskTrigger -Daily -At '09:00'
                $principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
                $options = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 20) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
                # No StartWhenAvailable, WakeToRun, or RestartCount: no catch-up/retry.
                Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $options -Force | Out-Null
                $manualAction = New-ScheduledTaskAction -Execute "$PSScriptRoot\.venv\Scripts\pythonw.exe" -Argument "`"$PSScriptRoot\background_launcher.py`" --manual" -WorkingDirectory $PSScriptRoot
                $manualTrigger = New-ScheduledTaskTrigger -Daily -At '00:00'
                $repeat = New-ScheduledTaskTrigger -Once -At '00:00' -RepetitionInterval (New-TimeSpan -Minutes 1) -RepetitionDuration (New-TimeSpan -Days 1)
                $manualTrigger.Repetition = $repeat.Repetition
                Register-ScheduledTask -TaskName $manualTask -Action $manualAction -Trigger $manualTrigger -Principal $principal -Settings $options -Force | Out-Null
                Write-Host 'Registered: 09:00 automatic sync + manual request check every minute.'
                Write-Host 'Manual requests require login, network access, and no absence/pause.'
                Write-Host 'Keep Windows time zone set to Korea. Stop any old start.bat watcher.'
            }
            '2' {$settings.paused=$true;Save-Settings $settings;Write-Host 'Paused.'}
            '3' {$settings.paused=$false;Save-Settings $settings;Write-Host 'Resumed. Next 09:00 automatic sync; manual request checks also resume.'}
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
                Get-ScheduledTask -TaskName $taskName,$manualTask -ErrorAction SilentlyContinue | Select-Object TaskName,State | Format-Table | Out-Host
                foreach ($name in @($taskName,$manualTask)) { Write-Host $name; Get-ScheduledTaskInfo -TaskName $name -ErrorAction SilentlyContinue | Select-Object LastRunTime,LastTaskResult,NextRunTime | Format-List | Out-Host }
                Write-Host "Logs: $PSScriptRoot\daily-state"
            }
            '7' {Unregister-ScheduledTask -TaskName $taskName,$manualTask -Confirm:$false -ErrorAction SilentlyContinue;Write-Host 'Task removed. Files retained.'}
            '0' {exit 0}
            default {Write-Host 'Choose 0 through 7.'}
        }
    } catch {Write-Host ('Could not complete: '+$_.Exception.Message)}
}

