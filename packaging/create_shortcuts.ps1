<#
.SYNOPSIS
    Create SamboTL shortcuts (server and client) on the Desktop.

.DESCRIPTION
    Shortcuts point to dist\SamboTLServer.exe and dist\SamboTLClient.exe.
    Run after the build (packaging\build.ps1).
#>
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$desktop = [Environment]::GetFolderPath("Desktop")
$shell = New-Object -ComObject WScript.Shell

$targets = @(
    @{ Name = "SamboTL Server"; Exe = Join-Path $root "dist\SamboTLServer.exe";
       Desc = "Sambo tournament server";        WorkDir = (Join-Path $root "dist") },
    @{ Name = "SamboTL Client";  Exe = Join-Path $root "dist\SamboTLClient.exe";
       Desc = "Operator workstation";           WorkDir = (Join-Path $root "dist") }
)

foreach ($t in $targets) {
    if (-not (Test-Path $t.Exe)) {
        Write-Warning ("Missing: " + $t.Exe + " (skip shortcut " + $t.Name + ")")
        continue
    }
    $lnkPath = Join-Path $desktop ($t.Name + ".lnk")
    $shortcut = $shell.CreateShortcut($lnkPath)
    $shortcut.TargetPath = $t.Exe
    $shortcut.WorkingDirectory = $t.WorkDir
    $shortcut.Description = $t.Desc
    $shortcut.IconLocation = $t.Exe
    $shortcut.Save()
    Write-Host ("Shortcut created: " + $lnkPath)
}
