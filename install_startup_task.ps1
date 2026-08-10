$ErrorActionPreference = 'Stop'
$folder = Split-Path -Parent $MyInvocation.MyCommand.Path
$runner = Join-Path $folder 'run_send.bat'
$action = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument ('/c "' + $runner + '"') -WorkingDirectory $folder
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 20)
Register-ScheduledTask -TaskName 'NBER Weekly Reader' -Action $action -Trigger $trigger -Settings $settings -Description '每次登录时检查并每周发送一次开放的 NBER 论文精选' -Force
Write-Host '已创建启动任务：NBER Weekly Reader'

