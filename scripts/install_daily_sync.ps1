# Registra a tarefa agendada do Windows que roda scripts/sync_results.py
# todos os dias às 03:00. Execute uma vez:
#
#   powershell -ExecutionPolicy Bypass -File scripts\install_daily_sync.ps1
#
# -WakeToRun acorda o PC (se estiver hibernando) para rodar no horário.
# -StartWhenAvailable garante que, se o PC estiver desligado às 3h, a
# sincronização roda assim que ele for ligado novamente.

$TaskName   = 'BolaoCopa2026_SyncResultados'
$RepoRoot   = Split-Path -Parent $PSScriptRoot
$ScriptPath = Join-Path $RepoRoot 'scripts\sync_results.py'
$PythonExe  = "$env:LOCALAPPDATA\Microsoft\WindowsApps\python3.13.exe"

if (-not (Test-Path $PythonExe)) {
    $PythonExe = (Get-Command python3.13 -ErrorAction SilentlyContinue).Source
}
if (-not $PythonExe) {
    throw 'Não foi possível localizar o interpretador Python (python3.13).'
}

$Action   = New-ScheduledTaskAction -Execute $PythonExe -Argument "`"$ScriptPath`"" -WorkingDirectory $RepoRoot
$Trigger  = New-ScheduledTaskTrigger -Daily -At 3:00AM
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun `
            -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 5) `
            -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger `
    -Settings $Settings -Force `
    -Description 'Sincroniza diariamente os resultados reais da Copa do Mundo 2026 no Bolão.'

Write-Host "Tarefa '$TaskName' registrada — roda todo dia às 03:00."
