#!/bin/bash
# QR Data Bridge Sender - 安装脚本

echo "🔧 QR Data Bridge Sender 安装程序"
echo "================================"
echo ""

# 检查 Python 版本
echo "检查 Python 版本..."
python3 --version

if ! python3 -c 'import sys; exit(0 if sys.version_info >= (3, 10) else 1)'; then
    echo "❌ 错误：需要 Python 3.10 或更高版本"
    echo "   当前版本：$(python3 --version)"
    exit 1
fi

echo "✅ Python 版本符合要求"
echo ""

# 创建虚拟环境
echo "📦 创建虚拟环境..."
python3 -m venv venv
echo "✅ 虚拟环境创建完成"
echo ""

# 激活虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate

# 安装依赖
echo "📥 安装依赖包..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "✅ 安装完成！"
echo ""
echo "运行程序:"
echo "  source venv/bin/activate"
echo "  python qr_sender.py"
echo ""
echo "或者使用启动脚本:"
echo "  ./run.sh"
