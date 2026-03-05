#!/bin/bash
# QR Data Bridge Sender - 运行脚本

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ 虚拟环境不存在，请先运行安装脚本:"
    echo "   ./install.sh"
    exit 1
fi

# 激活虚拟环境
source venv/bin/activate

# 运行程序
echo "🚀 启动 QR Data Bridge Sender..."
python qr_sender.py
