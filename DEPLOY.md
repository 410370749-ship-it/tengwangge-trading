# 云端部署指南

## 方案A：Railway（推荐，简单免费）

### 1. 准备代码
```bash
cd /root/.openclaw/workspace/quant
git init
git add .
git commit -m "Initial commit"
```

### 2. 部署到 Railway

**方式1：Railway CLI**
```bash
# 安装 Railway CLI
npm install -g @railway/cli

# 登录
railway login

# 创建项目
railway init

# 部署
railway up

# 获取域名
railway domain
```

**方式2：GitHub + Railway**
1. 把代码推送到 GitHub
2. 登录 [railway.app](https://railway.app)
3. 点击 "New Project" → "Deploy from GitHub repo"
4. 选择你的仓库
5. 自动部署完成，会分配一个 `xxx.up.railway.app` 域名

### 3. 访问
部署成功后，访问分配的域名即可。

---

## 方案B：Vercel（Serverless，免费）

### 1. 准备代码
```bash
cd /root/.openclaw/workspace/quant

# 确保有这些文件
# - vercel.json
# - api/index.py
# - requirements.txt
# - web_trading.html
```

### 2. 部署

**方式1：Vercel CLI**
```bash
# 安装 Vercel CLI
npm install -g vercel

# 登录
vercel login

# 部署
vercel

# 生产部署
vercel --prod
```

**方式2：GitHub + Vercel**
1. 把代码推送到 GitHub
2. 登录 [vercel.com](https://vercel.com)
3. 点击 "Add New Project"
4. 导入 GitHub 仓库
5. 点击 Deploy

### 3. 访问
部署成功后，访问 `https://你的项目名.vercel.app`

---

## 方案C：Render（免费，有休眠限制）

### 部署步骤
1. 把代码推送到 GitHub
2. 登录 [render.com](https://render.com)
3. 点击 "New" → "Web Service"
4. 连接 GitHub 仓库
5. 配置：
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python3 web_server.py`
6. 点击 Create Web Service

---

## ⚠️ 重要说明

### 数据持久化问题

**免费 Serverless 平台的问题**：
- Vercel/Railway 的无服务器实例是**无状态的**
- 每次部署或实例重启，本地文件（config.json、交易记录）会丢失

**解决方案**：

#### 方案1：使用云数据库（推荐）
把 `config.json` 和交易记录存储到：
- **Supabase**（免费 PostgreSQL）
- **MongoDB Atlas**（免费 512MB）
- **Railway 自带数据库**

#### 方案2：GitHub 作为存储（简单但不实时）
每次交易后自动 commit 到 GitHub

#### 方案3：使用 Railway（Docker 模式）
Railway 的 Docker 部署有持久化存储，不会丢失数据

---

## 推荐的最终方案

**Railway Docker 部署** = 免费 + 持久化 + 简单

```bash
# 1. 配置 railway.json（已创建）

# 2. 部署
railway login
railway init
railway up

# 3. 完成！获得 https://xxx.up.railway.app
```

需要我帮你配置 **Supabase 数据库** 来持久化数据吗？这样即使重新部署也不会丢失持仓和交易记录。
