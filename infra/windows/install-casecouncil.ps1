param(
    [Parameter(Mandatory = $true)][string]$RepoPath,
    [Parameter(Mandatory = $true)][PSCredential]$Credential,
    [switch]$Start
)
$ErrorActionPreference = 'Stop'
$TaskRepo = (Resolve-Path -LiteralPath $RepoPath).Path
$TaskPython = Join-Path $TaskRepo '.venv\Scripts\python.exe'
$TaskRunner = Join-Path $TaskRepo 'scripts\run_product_service.py'
if (!(Test-Path -LiteralPath $TaskPython) -or !(Test-Path -LiteralPath $TaskRunner)) { throw 'Install the Python workspace first.' }
if (!(Test-Path -LiteralPath (Join-Path $TaskRepo 'apps\casecouncil-web\dist\index.html'))) { throw 'Build the CaseCouncil frontend first.' }
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero)
$Trigger = New-ScheduledTaskTrigger -AtStartup
foreach ($Role in @('api', 'worker')) {
    if (Get-ScheduledTask -TaskName "AI-Cohort-CaseCouncil-$Role" -ErrorAction SilentlyContinue) { throw 'Existing task requires explicit review before update.' }
}
foreach ($Role in @('api', 'worker')) {
    $Name = "AI-Cohort-CaseCouncil-$Role"
    $Action = New-ScheduledTaskAction -Execute $TaskPython -Argument "`"$TaskRunner`" $Role --product casecouncil" -WorkingDirectory $TaskRepo
    Register-ScheduledTask -TaskName $Name -Action $Action -Trigger $Trigger -Settings $Settings -User $Credential.UserName -Password ($Credential.GetNetworkCredential().Password) -RunLevel Limited | Out-Null
    if ($Start) { Start-ScheduledTask -TaskName $Name }
    Write-Output "Installed $Name"
}
