# 慧股AI (HuiGu AI)

> 面向中国A股投资者的下一代智能行情交易软件

**技术栈:** Next.js 15 + React Native (Expo) + FastAPI + Claude AI + AKShare

---

## 三大核心引擎

| 引擎 | 功能 |
|------|------|
| 🏦 基础看盘引擎 | 沪深A股实时行情、K线图（日/周/月）、技术指标、盘口、模拟交易 |
| 📡 多维情报聚合引擎 | 微博/小红书/知乎/雪球/股吧舆情、情感仪表盘、达人胜率榜、异动溯源 |
| 🤖 AI深度投研引擎 | Claude驱动的智能分析、多空辩论室、公告AI速读、热点概念追踪 |

---

## 客户端一览

| 客户端 | 技术 | 说明 |
|--------|------|------|
| 🌐 Web | Next.js 15 standalone | 浏览器访问，需配合后端或直接内置 API |
| 🖥️ macOS | Electron + Next.js | 桌面单机版，内置 Next.js 服务器，**无需后端** |
| 📱 Android | Expo React Native | 移动单机版，数据内置，**无需后端**；CI 产出可直接安装的 APK |

---

## 快速启动

### 方式一：单机运行（无需后端）

macOS 和 Android 客户端均为单机版，内置完整的模拟数据（行情、舆情、AI 分析），
下载安装包即可直接使用，无需启动任何后端服务。

- **macOS**：从 [Actions](../../actions/workflows/macos-build.yml) 下载 DMG，拖入「应用程序」，双击打开。
- **Android**：从 [Actions](../../actions/workflows/android-build.yml) 下载 APK，允许「安装未知来源应用」后安装。

---

### 方式二：本地开发（带真实数据）

#### 1. 后端 (FastAPI)

```bash
cd backend

# 安装依赖（推荐 Python 3.11+）
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env，至少填入：
#   ANTHROPIC_API_KEY=sk-ant-...   # AI 功能必须
#   TUSHARE_TOKEN=...               # 可选，用于更丰富的行情数据
#   REDIS_URL=redis://localhost:6379 # 可选，用于缓存加速

# 启动服务（监听 8000 端口）
uvicorn app.main:app --reload --port 8000
```

访问 http://localhost:8000/docs 查看交互式 API 文档。

---

#### 2. Web 端 (Next.js)

```bash
cd apps/web

npm install

# 开发模式（需后端已启动）
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

访问 http://localhost:3000

---

#### 3. 移动端 (Expo)

```bash
cd apps/mobile

npm install

# 启动 Expo 开发服务器
npx expo start
```

- **真机调试**：扫描终端中的二维码，用 Expo Go App 打开。
- **Android 模拟器**：按 `a` 键启动（需已安装 Android Studio）。
- **无需后端**：移动端已内置模拟数据，即使不启动 FastAPI 也能正常运行。

如需连接真实后端数据，在 `src/services/api.ts` 将 mock 调用替换为 axios 请求，
并配置：

```bash
export EXPO_PUBLIC_API_URL=http://<本机IP>:8000
```

> **注意**：Expo Go 中模拟器用 `http://10.0.2.2:8000`，真机用本机局域网 IP。

---

#### 4. macOS 桌面端 (Electron)

```bash
# 先构建 Web 端
cd apps/web && npm install && npm run build

# 启动 Electron（开发模式）
cd ../macos && npm install && npm start
```

如需 AI 功能（Claude 真实调用），在启动前设置：

```bash
export ANTHROPIC_API_KEY=sk-ant-...
npm start
```

---

## 环境变量

### 后端 (`backend/.env`)

| 变量 | 说明 | 是否必须 |
|------|------|----------|
| `ANTHROPIC_API_KEY` | Claude API 密钥 | AI 功能必须 |
| `TUSHARE_TOKEN` | Tushare Pro token | 可选 |
| `REDIS_URL` | Redis 连接地址 | 可选，缓存加速 |
| `APP_ENV` | `development` / `production` | 可选，默认 development |

### macOS Electron 端

| 变量 | 说明 |
|------|------|
| `ANTHROPIC_API_KEY` | 设置后启用真实 Claude AI 分析，否则显示内置模拟分析 |

---

## 项目结构

```
Huigu-AI/
├── backend/                    # FastAPI 后端（可选，提供真实数据）
│   ├── app/
│   │   ├── api/                # API 路由
│   │   │   ├── market.py       # 行情接口
│   │   │   ├── sentiment.py    # 舆情接口
│   │   │   └── ai.py           # AI 分析接口
│   │   ├── services/
│   │   │   ├── market/         # AKShare 数据服务
│   │   │   ├── sentiment/      # 舆情聚合服务
│   │   │   └── ai/             # Claude API 服务
│   │   └── models/             # Pydantic 数据模型
│   └── requirements.txt
│
└── apps/
    ├── web/                    # Next.js 15 Web 端
    │   ├── app/
    │   │   ├── api/            # Next.js API Routes（内置 mock，Electron 使用）
    │   │   │   ├── market/     # 行情接口
    │   │   │   ├── sentiment/  # 舆情接口
    │   │   │   └── ai/         # AI 分析接口（支持真实 Claude）
    │   │   └── (pages)/        # 行情、热议、AI投研、我的
    │   ├── lib/
    │   │   ├── api.ts          # API 客户端（自动检测 Electron）
    │   │   └── store.ts        # Zustand 状态管理
    │   └── components/
    │
    ├── macos/                  # Electron macOS 桌面端
    │   ├── main.js             # 主进程（内嵌 Next.js 服务器）
    │   └── preload.js
    │
    └── mobile/                 # Expo React Native 移动端
        ├── src/
        │   ├── screens/
        │   │   ├── Market/     # 行情 & 自选股
        │   │   ├── Sentiment/  # 社区热议
        │   │   ├── Research/   # AI 投研
        │   │   └── Profile/    # 个人中心
        │   ├── components/
        │   ├── store/          # Zustand 状态管理
        │   └── services/
        │       ├── api.ts      # 数据服务（当前为单机 mock）
        │       └── mock.ts     # 内置模拟数据
        └── App.tsx
```

---

## API 接口

后端（FastAPI）与 Web 端（Next.js API Routes）提供相同接口：

### 行情
- `GET /api/market/overview` — 市场概览（大盘指数、涨跌家数）
- `GET /api/market/quote/{symbol}` — 个股实时行情
- `GET /api/market/kline/{symbol}?period=D` — K线数据
- `GET /api/market/search?q=贵州` — 股票搜索
- `POST /api/market/watchlist/quotes` — 批量自选股报价

### 舆情
- `GET /api/sentiment/{symbol}/score` — 情感评分
- `GET /api/sentiment/{symbol}/posts` — 社区帖子列表
- `GET /api/sentiment/{symbol}/influencers` — 达人榜

### AI 分析
- `GET /api/ai/analyze/{symbol}` — 流式 AI 综合分析（SSE）
- `POST /api/ai/debate/{symbol}` — 多空辩论室
- `POST /api/ai/summarize-post` — 帖子 AI 摘要

---

## 数据说明

| 数据类型 | 来源 |
|----------|------|
| 实时行情 | AKShare（免费 A 股数据）；无法获取时自动降级为内置模拟数据 |
| 社区舆情 | 股吧真实数据 + 微博/小红书/雪球模拟数据（真实 API 需商业授权） |
| AI 分析 | Claude claude-sonnet-4-6；未配置 API Key 时显示内置模拟分析 |

> ⚠️ 所有 AI 分析内容仅供参考，不构成投资建议。投资有风险，入市须谨慎。
