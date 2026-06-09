# AIGateway-Zero Startup Script for PowerShell
# 轻量级AI模型统一网关 PowerShell 启动脚本

param(
    [string]$Host = $env:AIGATEWAY_HOST,
    [int]$Port = 0,
    [string]$Config = $env:AIGATEWAY_CONFIG,
    [switch]$InitConfig,
    [switch]$Test,
    [switch]$Help
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir
$SrcDir = Join-Path $ProjectDir "src"

# Default values
if (-not $Host) { $Host = "0.0.0.0" }
if ($Port -eq 0) { $Port = 8080 }
if (-not $Config) { $Config = Join-Path $ProjectDir "aigateway.yaml" }

function Print-Banner {
    Write-Host @"
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║   🤖 AIGateway-Zero v1.0.0                                    ║
    ║   Lightweight AI Model Unified Gateway                        ║
    ║   轻量级AI模型统一网关                                          ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
"@ -ForegroundColor Cyan
}

function Print-Help {
    Write-Host @"
Usage: .\run.ps1 [OPTIONS]

Options:
  -Host HOST         Server host (default: 0.0.0.0)
  -Port PORT         Server port (default: 8080)
  -Config PATH       Config file path
  -InitConfig        Create demo config file
  -Test              Run unit tests
  -Help              Show this help message

Environment Variables:
  AIGATEWAY_HOST     Server host
  AIGATEWAY_PORT     Server port
  AIGATEWAY_CONFIG   Config file path
"@
}

function Run-Tests {
    Write-Host "Running unit tests..." -ForegroundColor Yellow
    Set-Location $ProjectDir
    python3 -m unittest discover -s tests -v
    Write-Host "Tests completed!" -ForegroundColor Green
}

function Init-Config {
    Write-Host "Creating demo configuration..." -ForegroundColor Yellow
    Set-Location $ProjectDir
    python3 "$SrcDir\main.py" --init-config
    Write-Host "Config file created: $Config" -ForegroundColor Green
    Write-Host "Please edit the config file and add your API keys." -ForegroundColor Yellow
}

function Start-Server {
    Print-Banner
    Write-Host "Starting AIGateway-Zero..." -ForegroundColor Green
    Write-Host "Host: $Host" -ForegroundColor Yellow
    Write-Host "Port: $Port" -ForegroundColor Yellow
    if (Test-Path $Config) {
        Write-Host "Config: $Config" -ForegroundColor Yellow
    } else {
        Write-Host "Config: Using defaults (no config file)" -ForegroundColor Yellow
    }
    Write-Host ""

    Set-Location $ProjectDir
    if (Test-Path $Config) {
        python3 "$SrcDir\main.py" -c $Config -H $Host -p $Port
    } else {
        python3 "$SrcDir\main.py" -H $Host -p $Port
    }
}

# Main
if ($Help) {
    Print-Help
    exit 0
}

if ($InitConfig) {
    Init-Config
    exit 0
}

if ($Test) {
    Run-Tests
    exit 0
}

Start-Server
