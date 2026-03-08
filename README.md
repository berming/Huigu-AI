# 慧股AI (HuiGu AI)

> 面向中国A股投资者的下一代智能行情交易软件

**技术栈:** React Native (Expo) + FastAPI + Claude AI + AKShare

---

## 三大核心引擎

| 引擎 | 功能 |
|------|------|
| 🏦 基础看盘引擎 | 沪深A股实时行情、K线图（日/周/月）、技术指标、盘口、模拟交易 |
| 📡 多维情报聚合引擎 | 微博/小红书/知乎/雪球/股吧舆情、情绪仪表盘、达人胜率榜、异动溯源 |
| 🤖 AI深度投研引擎 | Claude驱动的智能分析、多空辩论室、公告AI速读、热点概念追踪 |

---

## 快速启动

### 1. 后端 (FastAPI)

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入 ANTHROPIC_API_KEY

# 启动服务
uvicorn app.main:app --reload --port 8000
```

访问 http://localhost:8000/docs 查看 API 文档

### 2. 移动端 (Expo)

```bash
cd apps/mobile

# 安装依赖
npm install

# 配置 API 地址 (在 src/services/api.ts 中修改 BASE_URL)
# 或设置环境变量
export EXPO_PUBLIC_API_URL=http://your-local-ip:8000

# 启动 Expo
npx expo start
```

扫描二维码在手机上安装 Expo Go，即可在真机上运行。

---

## 环境变量

| 变量 | 说明 | 必须 |
|------|------|------|
| `ANTHROPIC_API_KEY` | Claude API 密钥 | AI功能必须 |
| `TUSHARE_TOKEN` | Tushare Pro token | 可选 |
| `REDIS_URL` | Redis 连接地址 | 可选，用于缓存 |

---

## 项目结构

```
Huigu-AI/
├── backend/                    # FastAPI 后端
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
└── apps/mobile/                # Expo React Native 移动端
    ├── src/
    │   ├── screens/
    │   │   ├── Market/         # 行情 & 自选股
    │   │   ├── Sentiment/      # 社区热议
    │   │   ├── Research/       # AI 投研
    │   │   └── Profile/        # 个人中心
    │   ├── components/
    │   │   ├── charts/         # K线图
    │   │   ├── market/         # 行情组件
    │   │   ├── sentiment/      # 舆情组件
    │   │   └── ai/             # AI 组件
    │   ├── store/              # Zustand 状态管理
    │   └── services/           # API 客户端
    └── App.tsx
```

---

## API 接口

### 行情
- `GET /api/market/overview` — 市场概览（大盘指数、涨跌家数）
- `GET /api/market/quote/{symbol}` — 个股实时行情
- `GET /api/market/kline/{symbol}` — K线数据
- `GET /api/market/search?q=贵州` — 股票搜索

### 舆情
- `GET /api/sentiment/{symbol}/score` — 情绪评分
- `GET /api/sentiment/{symbol}/posts` — 社区帖子列表
- `GET /api/sentiment/{symbol}/influencers` — 达人榜

### AI 分析
- `GET /api/ai/analyze/{symbol}` — 流式 AI 综合分析 (SSE)
- `POST /api/ai/debate/{symbol}` — 多空辩论室
- `POST /api/ai/summarize-post` — 帖子 AI 摘要

---

## 数据说明

- **实时行情**：AKShare 提供免费 A 股数据（AKShare 安装成功时自动使用）
- **社区舆情**：股吧真实数据 + 微博/小红书/雪球模拟数据（真实 API 需商业授权）
- **AI 分析**：由 Anthropic Claude claude-sonnet-4-6 驱动

> ⚠️ 所有 AI 分析内容仅供参考，不构成投资建议。
> 投资有风险，入市须谨慎。
