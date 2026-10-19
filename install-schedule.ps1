# 纯本地定时更新（Windows 计划任务）：不推 GitHub，只刷新本机文件
# 用法:
#   powershell -NoProfile -ExecutionPolicy Bypass -File install-schedule.ps1
#   ... -File install-schedule.ps1 -Time 08:15
#   ... -File install-schedule.ps1 -Remove
#   ... -File install-schedule.ps1 -RunNow
#   ... -File install-schedule.ps1 -Serve        (顺带起本地静态服务器给手机看)
param(
    [string]$Time = '07:30',
    [switch]$Remove,
    [switch]$RunNow,
    [switch]$Serve
)

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$taskName = 'ModelLeaderboard'
$ps1 = Join-Path $PSScriptRoot 'update.ps1'

if (-not (Test-Path $ps1)) { throw "找不到 update.ps1" }

if ($Remove) {
    schtasks /Delete /TN $taskName /F 2>$null | Out-Null
    Write-Host "已删除计划任务 $taskName"
    return
}

if ($RunNow) {
    & $ps1
    return
}

New-Item -ItemType Directory -Force -Path (Join-Path $PSScriptRoot 'logs') | Out-Null

$tr = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$ps1`""
schtasks /Create /TN $taskName /TR $tr /SC DAILY /ST $Time /F | Out-Null

if ($LASTEXITCODE -ne 0) {
    Write-Host "创建失败：试试用管理员身份运行 PowerShell" -ForegroundColor Yellow
    exit 1
}

Write-Host "已安装计划任务 $taskName，每天 $Time 运行" -ForegroundColor Green
Write-Host "  命令: $tr"
Write-Host ""
Write-Host "立即跑一次: powershell -File install-schedule.ps1 -RunNow"
Write-Host "查看状态:   schtasks /Query /TN $taskName /V /FO LIST"

if ($Serve) {
    Write-Host ""
    Write-Host "启动本地服务器（Ctrl+C 停止）—— 手机同网段访问 http://<本机IP>:8080" -ForegroundColor Cyan
    Start-Process "http://localhost:8080"
    python -m http.server 8080
}
