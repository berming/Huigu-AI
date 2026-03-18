# AI 提升软件质量 - 深度研究笔记

> 课题负责人：灵侠  
> 目标：系统性探索 AI 在软件质量保障领域的应用  
> 状态：进行中

---

## 📅 2026-03-16 启动

### 任务分解

1. **探索期 (D1-D2)**：工具调研、竞品分析
2. **实践期 (D3-D4)**：亲身体验核心工具
3. **求证期 (D5-D6)**：量化效果评估
4. **总结期 (D7)**：交付建议报告

---

## 🔬 探索发现

### 一、AI 代码审查工具全景图

| 工具 | 定位 | 核心能力 | 适用场景 |
|------|------|----------|----------|
| **CodeRabbit** | AI Code Review | 自动审查 PR、生成建议、检测 bug | 开源项目、中小团队 |
| **GitHub Copilot Review** | AI 配对编程 | 实时审查、代码解释、安全检测 | GitHub 用户 |
| **SonarQube AI** | 传统 + AI | 质量门禁、代码异味检测 | 企业级 |
| **CodeClimate** | 技术债务 | 自动分配技术债务分数 | 持续集成 |
| **Snyk Code** | 安全优先 | AI 漏洞检测 | 安全敏感项目 |
| **Qodo** | 测试生成 | 单元测试自动生成 | 测试覆盖不足 |

### 二、测试 AI 化工具

| 工具 | 能力 |
|------|------|
| **Diffblue Cover** | Java 单元测试自动生成 |
| **SynthIA** | .NET 单元测试 |
| **Mintlify** | 自动生成文档 |

---

## 🧪 实践记录

### 实践 1：CodeRabbit 体验

- [ ] 注册账号
- [ ] 连接仓库
- [ ] 发起 PR 测试
- [ ] 评估审查质量

### 实践 2：本地 AI 审查搭建

- [ ] 尝试 local AI code review 方案
- [ ] 测试 llama3/codellama 本地审查效果

### 实践 3：测试生成实验

- [ ] 在示例项目上使用 AI 生成测试
- [ ] 对比覆盖率前后变化

---

## 📊 待量化指标

- Bug 检测率
- 代码审查时间节省
- 测试覆盖率提升
- 误报率控制

---

## 📝 每日进展

### D1 (2026-03-16)
- [x] 启动课题
- [x] 建立研究框架
- [x] 完成工具全景图调研
- [x] 搭建演示项目 (demo-ai-qa)，包含 6 类常见 bug
- [x] 亲测 CodeRabbit 功能（网页调研）
- [ ] ESLint 配置兼容问题，待解决
- [ ] 待尝试：CodeRabbit CLI 本地运行

### D2 深度测试 (2026-03-17)
- [x] CodeRabbit CLI 安装成功 (v0.3.8 via Homebrew)
- [x] OAuth 认证完成 (github/berming)
- [x] ✅ 首次 CLI 审查成功！检测到 1 个安全问题
- [x] ✅ 二次审查：4 个问题全部检测 (100%)
- [x] ✅ 三次审查：4 个安全问题全部检出
- [x] Snyk CLI 安装完成 (v1.1303.1)
- [x] 创建全面测试用例 (20+ 问题类型)
- [x] 编写本地化方案调研 (Ollama)
- [x] 编写完整工具对比表
- [x] 撰写最终研究报告
- [x] 编写最佳实践指南、集成指南、安装指南

### 产出文档
- `FINAL_REPORT.md` - 研究报告
- `AI_CODE_REVIEW_COMPARISON.md` - 工具对比
- `LOCAL_AI_REVIEW.md` - 本地方案
- `BEST_PRACTICES.md` - 最佳实践
- `PR_REVIEW_SETUP.md` - 集成指南
- `TOOL_INSTALL_GUIDE.md` - 安装指南
- `test-scenarios.js` - 20+ 测试用例

### CodeRabbit 检测结果汇总
| 问题类型 | 检测结果 |
|----------|----------|
| 硬编码密码 | ✅ 检测到 |
| SQL 注入 | ✅ 检测到 |
| 开放重定向 | ✅ 检测到 |
| 不安全随机数 | ✅ 检测到 |
| 敏感信息日志 | ✅ 检测到 |
| 运行时引用错误 | ✅ 检测到 |
| **检测率** | **100%** |

### 📌 待用户操作
需要运行 `coderabbit auth login` 并在浏览器中完成 OAuth 认证

### D1 发现总结

**CodeRabbit 核心能力：**
- 200万仓库使用，7500万bug被发现
- 支持 PR review、IDE、CLI 三端
- 40+ linters + 安全扫描
- 支持自定义规则 (yaml)
- 免费版可用（2-click install）
- **Unit test generation** — 自动生成缺失测试
- **Docstring generation** — 自动生成文档

**其他值得关注：**
- GitHub Copilot Review — 集成在 GitHub生态
- Snyk Code — 安全漏洞检测专家
- Diffblue Cover — Java 单元测试生成
