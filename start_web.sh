#!/bin/bash
# 启动滕王阁序交易系统 - Web版

cd /root/.openclaw/workspace/quant

echo "🏮 滕王阁序交易系统 - Web版"
echo "============================"
echo ""
echo "正在启动..."
echo ""

# 检查依赖
python3 -c "import flask" 2>/dev/null || {
    echo "正在安装依赖..."
    pip install flask flask-cors pandas requests -q --break-system-packages
}

# 启动服务器
python3 web_server.py