param(
    [Parameter(Mandatory = $true)][string]$RepoPath,
    [Parameter(Mandatory = $true)][PSCredential]$Credential,
    [switch]$Start
)
$ErrorActionPreference = 'Stop'
$TaskRepo = (Resolve-Path -LiteralPath $RepoPath).Path
$TaskPython = Join-Path $TaskRepo '.venv\Scripts\python.exe'
$TaskRunner = Join-Path $TaskRepo 'scripts\run_product_service.py'
if (!(Test-Path -LiteralPath $TaskPython) -or !(Test-Path -LiteralPath $TaskRunner)) { throw 'Install Python workspace first.' }
if (!(Test-Path -LiteralPath (Join-Path $TaskRepo 'apps\relaydesk-web\dist\index.html'))) { throw 'Build RelayDesk frontend first.' }
if (!(Test-Path -LiteralPath (Join-Path $TaskRepo 'var\models\relaydesk-minilm\manifest.json'))) { throw 'Provision and verify the CPU encoder before installation.' }
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero)
$Trigger = New-ScheduledTaskTrigger -AtStartup
foreach ($Role in @('api', 'worker')) {
    if (Get-ScheduledTask -TaskName "AI-Cohort-RelayDesk-$Role" -ErrorAction SilentlyContinue) { throw 'Existing task must be reviewed before update.' }
}
foreach ($Role in @('api', 'worker')) {
    $Name = "AI-Cohort-RelayDesk-$Role"
    $Action = New-ScheduledTaskAction -Execute $TaskPython -Argument "`"$TaskRunner`" $Role --product relaydesk" -WorkingDirectory $TaskRepo
    Register-ScheduledTask -TaskName $Name -Action $Action -Trigger $Trigger -Settings $Settings -User $Credential.UserName -Password ($Credential.GetNetworkCredential().Password) -RunLevel Limited | Out-Null
    if ($Start) { Start-ScheduledTask -TaskName $Name }
    Write-Output "Installed $Name"
}
