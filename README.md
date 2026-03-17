# 滕王阁序量化交易系统

## 🚀 云端部署版已就绪！

### 一键部署到云端

```bash
cd /root/.openclaw/workspace/quant
./deploy.sh
```

支持平台：
- **Railway** (推荐) - 免费，有持久化存储
- **Vercel** - Serverless，全球CDN
- **Render** - 免费，自动休眠

部署完成后获得 `https://xxx.railway.app` 公网地址，手机/电脑都能访问。

---

## 功能特性

| 功能 | 本地版 | 云端版 |
|------|--------|--------|
| 实时持仓监控 | ✅ | ✅ |
| 止损/止盈/时间止损检测 | ✅ | ✅ |
| 一键卖出 | ✅ | ✅ |
| 交易记录统计 | ✅ | ✅ |
| 钉钉/飞书通知 | ✅ | ✅ |
| 手机端访问 | ❌ | ✅ |
| 自动定时扫描 | ✅ | ✅ |

---

## 项目结构

```
quant/
├── config.json              # 组合配置
├── engine.py                # 核心交易引擎
├── web_server.py            # Flask Web服务器
├── web_trading.html         # 网页界面
├── supabase_db.py           # ⭐ Supabase 数据库模块
├── migrate_to_supabase.py   # 数据迁移脚本
├── setup_supabase.sh        # Supabase 配置向导
├── deploy.sh                # ⭐ 一键部署脚本
├── Dockerfile               # Docker 配置
├── railway.json             # Railway 配置
├── vercel.json              # Vercel 配置
├── api/index.py             # Vercel Serverless 入口
├── requirements.txt         # Python依赖
├── DEPLOY.md                # 部署指南
├── SUPABASE_SETUP.md        # Supabase 配置指南
└── trades/                  # 交易记录目录
```

---

## 快速开始（3步搞定）

### Step 1: 本地测试
```bash
cd /root/.openclaw/workspace/quant
pip install -r requirements.txt
python3 web_server.py
# 浏览器访问 http://localhost:5000
```

### Step 2: 配置云端数据库（防止丢数据）
```bash
./setup_supabase.sh
```

### Step 3: 部署到云端
```bash
./deploy.sh
```

部署完成后获得 `https://xxx.railway.app` 公网地址，手机/电脑随时访问！

---

### 方式1：本地运行

```bash
# 命令行交互模式
python3 engine.py --interactive

# 或启动网页版（本地访问）
python3 web_server.py
```

### 方式2：云端部署（推荐）

```bash
# 一键部署
./deploy.sh

# 或手动部署到 Railway
npm install -g @railway/cli
railway login
railway init
railway up
```

---

## 网页版功能

![网页界面](https://via.placeholder.com/800x400/1a1a2e/f39c12?text=Web+Trading+Interface)

- 📊 **持仓监控** - 5个组合实时展示
- ⏰ **时间止损** - 自动检测超期持仓
- 🔴 **信号标记** - 红色高亮需卖出股票
- ☑️ **批量选择** - 勾选多只股票一键卖出
- ⚡ **快速操作** - "卖出所有信号股" 按钮
- 📜 **交易记录** - 完整历史 + 胜率统计

---

## 当前持仓问题

**金玉满堂组合** 9只持仓中：
- 🔴 4只触发止损（跌幅超5%）
- 🟢 4只触发止盈（涨幅超25%）
- ⏰ 1只触发时间止损（持有11天 > 3天限制）

**时间止损已生效** - 系统每天自动扫描并推送通知。

---

## 数据来源

- **AkShare** - 免费A股实时行情（东方财富）
- 5秒缓存，避免频繁请求
- 失败时自动降级到模拟数据

---

## 技术栈

- **后端**: Python + Flask
- **数据**: AkShare (免费行情)
- **部署**: Railway / Vercel / Render
- **容器**: Docker

---

## 🔧 Supabase 数据库配置（推荐）

云端部署后数据会丢失？配置 **Supabase** 免费数据库（500MB）：

### 快速配置

```bash
# 运行配置向导
./setup_supabase.sh
```

### 手动配置

1. **创建 Supabase 项目**
   - 访问 https://supabase.com
   - 创建项目，记住密码

2. **创建数据表**
   - 进入 SQL Editor
   - 执行 SUPABASE_SETUP.md 中的 SQL

3. **获取连接信息**
   - Project Settings → API
   - 复制 `URL` 和 `anon key`

4. **配置环境变量**
   ```bash
   cat > .env << EOF
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-anon-key
   EOF
   ```

5. **迁移数据**
   ```bash
   python3 migrate_to_supabase.py
   ```

配置完成后，即使重新部署云端应用，持仓和交易记录也不会丢失！
