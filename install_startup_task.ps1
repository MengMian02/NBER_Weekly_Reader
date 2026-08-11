$ErrorActionPreference = 'Stop'

$folder = Split-Path -Parent $MyInvocation.MyCommand.Path
$runner = Join-Path $folder 'run_send.bat'
$startup = [Environment]::GetFolderPath('Startup')
$shortcutPath = Join-Path $startup 'NBER Weekly Reader.lnk'

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $env:ComSpec
$shortcut.Arguments = '/c "' + $runner + '"'
$shortcut.WorkingDirectory = $folder
$shortcut.WindowStyle = 7
$shortcut.Description = 'Sends the NBER Weekly Reader digest at Windows logon.'
$shortcut.Save()

Write-Host "Created startup shortcut: $shortcutPath"
Write-Host 'It will run at the next Windows logon.'

