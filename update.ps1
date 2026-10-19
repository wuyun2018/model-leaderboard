# Windows 一键更新（供任务计划程序或其他自动化工具调用）
# 用法: powershell -NoProfile -ExecutionPolicy Bypass -File update.ps1
# 可选: -Push  (git 提交并推送)
param([switch]$Push)

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

$logDir = Join-Path $PSScriptRoot 'logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir ("update-{0}.log" -f (Get-Date -Format 'yyyyMMdd-HHmmss'))

$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command python3 -ErrorAction SilentlyContinue }
if (-not $py) { throw 'python 未安装或不在 PATH 中' }

function Log($m) { $line = "[$(Get-Date -Format 'HH:mm:ss')] $m"; Write-Host $line; Add-Content -LiteralPath $log -Value $line -Encoding utf8 }

Log '=== 开始更新 ==='
& $py.Source fetch_aa.py 2>&1 | Tee-Object -FilePath $log -Append | Write-Host
if ($LASTEXITCODE -ne 0) { Log '!! AA 抓取失败，中止（不写坏数据）'; exit 1 }

& $py.Source fetch_openrouter.py 2>&1 | Tee-Object -FilePath $log -Append | Write-Host
if ($LASTEXITCODE -ne 0) { Log '!! OpenRouter 抓取失败，沿用上次 realdata.js' }

& $py.Source build.py 2>&1 | Tee-Object -FilePath $log -Append | Write-Host
if ($LASTEXITCODE -ne 0) { Log '!! 构建失败'; exit 1 }

if ($Push) {
    if (git status --porcelain) {
        git add -A
        git commit -q -m "chore: daily refresh $(Get-Date -Format 'yyyy-MM-dd')"
        git push -q
        Log '已推送'
    } else { Log '无变更，跳过提交' }
}

# 只保留最近 30 份日志
Get-ChildItem -LiteralPath $logDir -Filter 'update-*.log' | Sort-Object LastWriteTime -Descending |
    Select-Object -Skip 30 | Remove-Item -Force -ErrorAction SilentlyContinue

Log '=== 完成 ==='
