#!/bin/bash
# 滕王阁序交易系统 - Supabase 快速配置向导

set -e

echo "🏮 滕王阁序交易系统 - Supabase 配置向导"
echo "=========================================="
echo ""

# 检查是否在项目目录
if [ ! -f "engine.py" ]; then
    echo "❌ 错误: 请在 quant 目录下运行此脚本"
    exit 1
fi

# 安装依赖
echo "📦 安装 Supabase 依赖..."
pip install supabase python-dotenv -q

echo ""
echo "=========================================="
echo "配置步骤:"
echo "=========================================="
echo ""
echo "1. 访问 https://supabase.com 创建项目"
echo "   - 项目名称: tengwangge-trading"
echo "   - 设置密码并记住"
echo ""
echo "2. 创建数据表:"
echo "   进入 SQL Editor，粘贴以下内容:"
echo ""

# 显示 SQL
cat << 'SQL'
-- 持仓表
CREATE TABLE IF NOT EXISTS positions (
    id SERIAL PRIMARY KEY,
    portfolio_id TEXT NOT NULL,
    stock TEXT NOT NULL,
    name TEXT NOT NULL,
    shares INTEGER NOT NULL,
    avg_cost NUMERIC(12,4) NOT NULL,
    buy_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(portfolio_id, stock)
);

-- 交易记录表
CREATE TABLE IF NOT EXISTS trades (
    id SERIAL PRIMARY KEY,
    trade_id TEXT UNIQUE NOT NULL,
    portfolio_id TEXT NOT NULL,
    portfolio_name TEXT NOT NULL,
    stock TEXT NOT NULL,
    stock_name TEXT NOT NULL,
    trade_type TEXT NOT NULL,
    shares INTEGER NOT NULL,
    price NUMERIC(12,4) NOT NULL,
    amount NUMERIC(14,2) NOT NULL,
    pnl NUMERIC(14,2),
    pnl_pct NUMERIC(8,4),
    reason TEXT,
    notes TEXT,
    date DATE NOT NULL,
    time TIME NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 组合配置表
CREATE TABLE IF NOT EXISTS portfolios (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    initial_capital NUMERIC(14,2) NOT NULL,
    cash NUMERIC(14,2) NOT NULL DEFAULT 0,
    config JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
SQL

echo ""
echo "=========================================="
echo "3. 获取连接信息:"
echo "   Project Settings → API"
echo "   复制 URL 和 anon/public key"
echo "=========================================="
echo ""

# 读取用户输入
read -p "请输入 SUPABASE_URL (如 https://xxx.supabase.co): " SUPABASE_URL
read -p "请输入 SUPABASE_KEY (anon key): " SUPABASE_KEY

# 创建 .env 文件
cat > .env << EOF
# Supabase 配置
SUPABASE_URL=${SUPABASE_URL}
SUPABASE_KEY=${SUPABASE_KEY}
EOF

echo ""
echo "✅ 配置已保存到 .env 文件"
echo ""

# 测试连接
echo "🧪 测试连接..."
python3 << 'PYEOF'
import sys
sys.path.insert(0, '.')
from supabase_db import SupabaseDB

db = SupabaseDB()
if db.enabled:
    print("✅ Supabase 连接成功!")
    
    # 测试查询
    portfolios = db.get_all_portfolios()
    print(f"   数据库中组合数: {len(portfolios)}")
else:
    print("❌ 连接失败，请检查 URL 和 KEY")
    sys.exit(1)
PYEOF

if [ $? -ne 0 ]; then
    echo "❌ 连接测试失败"
    exit 1
fi

echo ""
echo "=========================================="
echo "4. 迁移现有数据到 Supabase?"
echo "=========================================="
read -p "是否迁移现有数据? (y/N): " MIGRATE

if [ "$MIGRATE" = "y" ] || [ "$MIGRATE" = "Y" ]; then
    python3 migrate_to_supabase.py
fi

echo ""
echo "=========================================="
echo "🎉 配置完成!"
echo "=========================================="
echo ""
echo "Supabase 数据库已启用:"
echo "  - 持仓数据云端存储"
echo "  - 交易记录云端存储"
echo "  - 组合配置云端同步"
echo ""
echo "部署到 Railway 后数据不会丢失!"
echo ""
