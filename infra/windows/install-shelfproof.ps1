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
if (!(Test-Path -LiteralPath (Join-Path $TaskRepo 'apps\shelfproof-web\dist\index.html'))) { throw 'Build ShelfProof first.' }
$TaskSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero)
$TaskTrigger = New-ScheduledTaskTrigger -AtStartup
foreach ($TaskRole in @('api', 'worker')) {
    if (Get-ScheduledTask -TaskName "AI-Cohort-ShelfProof-$TaskRole" -ErrorAction SilentlyContinue) { throw 'Existing task requires explicit review before update.' }
}
foreach ($TaskRole in @('api', 'worker')) {
    $TaskName = "AI-Cohort-ShelfProof-$TaskRole"
    $TaskAction = New-ScheduledTaskAction -Execute $TaskPython -Argument "`"$TaskRunner`" $TaskRole --product shelfproof" -WorkingDirectory $TaskRepo
    Register-ScheduledTask -TaskName $TaskName -Action $TaskAction -Trigger $TaskTrigger -Settings $TaskSettings -User $Credential.UserName -Password ($Credential.GetNetworkCredential().Password) -RunLevel Limited | Out-Null
    if ($Start) { Start-ScheduledTask -TaskName $TaskName }
    Write-Output "Installed $TaskName"
}
