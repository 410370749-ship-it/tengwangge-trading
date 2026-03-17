#!/bin/bash
# 滕王阁序交易系统 - 一键部署脚本
# 支持: Railway / Vercel / Render

set -e

echo "🏮 滕王阁序交易系统 - 云端部署"
echo "================================"
echo ""

# 检查是否在项目目录
if [ ! -f "web_server.py" ]; then
    echo "❌ 错误: 请在 quant 目录下运行此脚本"
    echo "   cd /root/.openclaw/workspace/quant"
    exit 1
fi

# 显示选项
echo "请选择部署平台:"
echo "1) Railway (推荐，免费，有持久化存储)"
echo "2) Vercel (Serverless，免费)"
echo "3) Render (免费，有休眠限制)"
echo "4) 仅生成部署文件，手动部署"
echo ""
read -p "输入选项 (1-4): " choice

# 安装 Node.js 依赖
echo ""
echo "📦 检查 Node.js 环境..."
if ! command -v npm &> /dev/null; then
    echo "正在安装 Node.js..."
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
    apt-get install -y nodejs
fi

case $choice in
    1)
        echo ""
        echo "🚀 部署到 Railway..."
        
        # 安装 Railway CLI
        if ! command -v railway &> /dev/null; then
            echo "安装 Railway CLI..."
            npm install -g @railway/cli
        fi
        
        # 检查是否已登录
        if ! railway whoami &> /dev/null; then
            echo ""
            echo "请先在浏览器中登录 Railway:"
            railway login
        fi
        
        # 初始化项目
        if [ ! -d ".railway" ]; then
            echo "初始化 Railway 项目..."
            railway init
        fi
        
        # 部署
        echo "开始部署..."
        railway up
        
        echo ""
        echo "✅ 部署完成!"
        echo ""
        echo "🌐 访问地址:"
        railway domain
        ;;
        
    2)
        echo ""
        echo "🚀 部署到 Vercel..."
        
        # 安装 Vercel CLI
        if ! command -v vercel &> /dev/null; then
            echo "安装 Vercel CLI..."
            npm install -g vercel
        fi
        
        # 部署
        echo "开始部署..."
        vercel --prod
        
        echo ""
        echo "✅ 部署完成!"
        ;;
        
    3)
        echo ""
        echo "📋 Render 部署指南:"
        echo ""
        echo "1. 把代码推送到 GitHub"
        echo "   git init"
        echo "   git add ."
        echo "   git commit -m 'Initial commit'"
        echo "   git push -u origin main"
        echo ""
        echo "2. 登录 https://render.com"
        echo "3. 点击 'New' → 'Web Service'"
        echo "4. 连接 GitHub 仓库"
        echo "5. 配置:"
        echo "   - Runtime: Python 3"
        echo "   - Build Command: pip install -r requirements.txt"
        echo "   - Start Command: python3 web_server.py"
        echo "6. 点击 Create Web Service"
        ;;
        
    4)
        echo ""
        echo "📦 已生成以下部署文件:"
        echo "  - Dockerfile (Docker 容器配置)"
        echo "  - railway.json (Railway 配置)"
        echo "  - vercel.json (Vercel 配置)"
        echo "  - api/index.py (Vercel Serverless 入口)"
        echo "  - .github/workflows/deploy-railway.yml (GitHub Actions)"
        echo "  - DEPLOY.md (详细部署指南)"
        echo ""
        echo "请查看 DEPLOY.md 获取手动部署步骤"
        ;;
        
    *)
        echo "❌ 无效选项"
        exit 1
        ;;
esac

echo ""
echo "================================"
echo "部署完成!"
