# 小红书内容运营智能体 xhs-agent - 一键安装脚本（Windows PowerShell）
# 用法（在仓库根目录）：
#   powershell -ExecutionPolicy Bypass -File .\install.ps1
#   powershell -ExecutionPolicy Bypass -File .\install.ps1 -WithCover   # 额外安装 Pillow
# 说明：仅安装依赖并自检，不启动服务；启动用 $env:PORT=8081; python run.py
param(
    [switch]$WithCover
)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

# 检查 python
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    throw "未找到 python，请先安装 Python 3.7 及以上版本并加入 PATH"
}
$ver = & python -c "import sys; print('%d.%d' % sys.version_info[:2])"
if ([version]$ver -lt [version]'3.7') {
    throw "Python 版本过低：当前 $ver，需要 3.7 及以上"
}

Write-Host "[1/4] 创建虚拟环境 .venv"
if (Test-Path .\.venv) {
    Write-Host "      已存在 .venv，跳过创建"
} else {
    python -m venv .venv
}
. .\.venv\Scripts\Activate.ps1

Write-Host "[2/4] 安装必需依赖（requirements.txt）"
python -m pip install -U pip -q
pip install -r requirements.txt -q

if ($WithCover) {
    Write-Host "[3/4] 安装可选依赖 Pillow（封面尺寸检查）"
    pip install pillow -q
} else {
    Write-Host "[3/4] 跳过 Pillow（封面检查会自动降级，不影响其他功能）"
}

Write-Host "[4/4] 自检"
python -c "import sys, yaml; print('      Python :', sys.version.split()[0]); print('      PyYAML :', getattr(yaml, '__version__', 'unknown'))"
python -c "`ntry:`n    import PIL; print('      Pillow :', getattr(PIL, '__version__', 'installed'))`nexcept ImportError:`n    print('      Pillow : 未安装（封面检查已禁用）')"

Write-Host ""
Write-Host "安装完成。启动命令："
Write-Host '  $env:PORT=8081; python run.py'
Write-Host "然后浏览器打开：http://localhost:8081"