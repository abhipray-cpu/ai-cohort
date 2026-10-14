param(
    [Parameter(Mandatory = $true)][string]$RepoPath,
    [Parameter(Mandatory = $true)][PSCredential]$Credential,
    [switch]$Start
)
$ErrorActionPreference = 'Stop'
$TaskRepo = (Resolve-Path -LiteralPath $RepoPath).Path
$TaskPython = Join-Path $TaskRepo '.venv\Scripts\python.exe'
$TaskRunner = Join-Path $TaskRepo 'scripts\run_product_service.py'
if (!(Test-Path -LiteralPath $TaskPython) -or !(Test-Path -LiteralPath $TaskRunner)) {
    throw 'Install the Python workspace and verify the repository path first.'
}
if (!(Test-Path -LiteralPath (Join-Path $TaskRepo 'apps\resolvedesk-web\dist\index.html'))) {
    throw 'Build the ResolveDesk web application first.'
}
# Installs startup tasks only. It does not install Codex, change firewall rules,
# configure Cloudflare, or validate authentication under the service account.
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero)
$Trigger = New-ScheduledTaskTrigger -AtStartup
foreach ($Role in @('api', 'worker')) {
    $Name = "AI-Cohort-ResolveDesk-$Role"
    if (Get-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue) {
        throw "Task $Name already exists. Review the installed configuration before updating."
    }
}
foreach ($Role in @('api', 'worker')) {
    $Name = "AI-Cohort-ResolveDesk-$Role"
    $Action = New-ScheduledTaskAction -Execute $TaskPython -Argument "`"$TaskRunner`" $Role" -WorkingDirectory $TaskRepo
    Register-ScheduledTask -TaskName $Name -Action $Action -Trigger $Trigger -Settings $Settings -User $Credential.UserName -Password ($Credential.GetNetworkCredential().Password) -RunLevel Limited | Out-Null
    if ($Start) { Start-ScheduledTask -TaskName $Name }
    Write-Output "Installed $Name"
}
