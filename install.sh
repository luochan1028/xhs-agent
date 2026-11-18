# AI生成
#!/usr/bin/env bash
# 小红书内容运营智能体 xhs-agent - 一键安装脚本（Linux / macOS）
# 用法：
#   bash install.sh                 # 安装必需依赖并自检
#   bash install.sh --with-cover    # 额外安装 Pillow（启用封面尺寸检查）
# 说明：仅安装依赖并自检，不启动服务；启动用 PORT=8081 python run.py
set -euo pipefail
cd "$(dirname "$0")"

PY="${PYTHON:-python3}"

if ! command -v "$PY" >/dev/null 2>&1; then
  echo "[ERROR] 未找到 $PY，请先安装 Python 3.7 及以上版本"
  exit 1
fi

if ! "$PY" -c 'import sys; sys.exit(0 if sys.version_info[:2] >= (3, 7) else 1)'; then
  echo "[ERROR] Python 版本过低，需要 3.7 及以上，当前：$("$PY" -V 2>&1)"
  exit 1
fi

echo "[1/4] 创建虚拟环境 .venv"
if [ -d .venv ]; then
  echo "      已存在 .venv，跳过创建"
else
  "$PY" -m venv .venv
fi

# shellcheck disable=SC1091
. .venv/bin/activate

echo "[2/4] 安装必需依赖（requirements.txt）"
python -m pip install -U pip -q
pip install -r requirements.txt -q

if [ "${1:-}" = "--with-cover" ]; then
  echo "[3/4] 安装可选依赖 Pillow（封面尺寸检查）"
  pip install pillow -q
else
  echo "[3/4] 跳过 Pillow（封面检查会自动降级，不影响其他功能）"
fi

echo "[4/4] 自检"
python - <<'PYEOF'
import sys
import yaml
print("      Python :", sys.version.split()[0])
print("      PyYAML :", getattr(yaml, "__version__", "unknown"))
try:
    import PIL
    print("      Pillow :", getattr(PIL, "__version__", "installed"))
except ImportError:
    print("      Pillow : 未安装（封面检查已禁用）")
PYEOF

echo ""
echo "安装完成。启动命令："
echo "  PORT=8081 python run.py"
echo "然后浏览器打开：http://localhost:8081"