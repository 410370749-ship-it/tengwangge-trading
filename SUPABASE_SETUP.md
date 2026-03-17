# Supabase 配置指南

## 1. 创建 Supabase 项目

1. 访问 https://supabase.com
2. 点击 "New Project"
3. 填写项目名称（如：tengwangge-trading）
4. 设置数据库密码（记住这个密码）
5. 选择最近的区域（如：Singapore）
6. 点击 "Create new project"

等待约 2 分钟项目创建完成。

---

## 2. 获取连接信息

项目创建完成后：

1. 点击左侧 "Project Settings" → "Database"
2. 找到 "Connection string" 部分
3. 选择 "URI" 格式
4. 复制连接字符串，类似：
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.xxxxx.supabase.co:5432/postgres
   ```

5. 或者用 "Connection parameters"：
   - Host: `db.xxxxx.supabase.co`
   - Port: `5432`
   - Database: `postgres`
   - User: `postgres`
   - Password: `[你的密码]`

---

## 3. 创建数据表

在 Supabase 的 SQL Editor 中执行以下 SQL：

```sql
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

-- 创建索引
CREATE INDEX idx_positions_portfolio ON positions(portfolio_id);
CREATE INDEX idx_trades_portfolio ON trades(portfolio_id);
CREATE INDEX idx_trades_date ON trades(date);
```

---

## 4. 配置环境变量

创建 `.env` 文件：

```bash
cd /root/.openclaw/workspace/quant
cat > .env << 'EOF'
# Supabase 配置
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
DATABASE_URL=postgresql://postgres:your-password@db.your-project.supabase.co:5432/postgres

# 或使用连接参数
DB_HOST=db.your-project.supabase.co
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=your-password
EOF
```

---

## 5. 安装依赖

```bash
pip install supabase py-postgresql psycopg2-binary python-dotenv
```

---

## 6. 测试连接

```bash
python3 -c "
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')

supabase = create_client(url, key)
response = supabase.table('positions').select('*').limit(1).execute()
print('连接成功!')
print(response)
"
```

---

## 7. 迁移现有数据

```bash
python3 migrate_to_supabase.py
```

---

## 注意事项

1. **免费额度**：500MB 存储，足够使用
2. **连接池**：Supabase 限制 60 个并发连接
3. **Row Level Security (RLS)**：生产环境建议启用
4. **备份**：Supabase 自动每日备份

---

## 获取帮助

- Supabase 文档：https://supabase.com/docs
- 连接问题：https://supabase.com/docs/guides/database/connecting-to-postgres
