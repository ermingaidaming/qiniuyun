# CLAUDE.md — AI 小说转剧本工具

> **项目权威参考文件**：技术栈命令、代码风格、命名规范、Git 版本控制与 PR 自动化工作流程。
>
> 每次会话自动加载。所有开发行为必须遵守本文档规定。

---

## 目录

- [1. 项目概述](#1-项目概述)
- [2. 技术栈与架构](#2-技术栈与架构)
- [3. 项目结构](#3-项目结构)
- [4. 构建、测试与运行命令](#4-构建测试与运行命令)
- [5. 代码风格与命名规范](#5-代码风格与命名规范)
- [6. Git 分支策略与版本控制](#6-git-分支策略与版本控制)
- [7. 自动化 PR 工作流程](#7-自动化-pr-工作流程)
- [8. 双人团队身份管理](#8-双人团队身份管理)
- [9. "始终绿色"主分支规则](#9-始终绿色主分支规则)
- [10. 提交合规检查清单](#10-提交合规检查清单)

---

## 1. 项目概述

基于大语言模型的 **AI 小说自动转剧本工具**，面向比赛议题"基于大语言模型与实时音视频技术的下一代 AI 核心应用研发"。

### 核心功能

- 小说上传与章节解析
- **CPC（因果情节图构建）**：使用贪婪循环破除算法构建事件有向无环图 (DAG)
- **R2（读者-重写器框架）**：滑动窗口小说块扫描与改写
- **HAR（幻觉感知改进）**：利用向量 RAG 的自校正循环
- **ScreenYAML 生成**：符合 Draft 2026-01 剧本模式的结构化输出（验证 UUID、角色关系和明确元素类型：动作、角色、对话、括号）
- 剧本导出（Word / PDF）

### 当前状态

当前 `main` 分支为项目起步骨架（本地 mock 闭环），保证主分支从第一天起可运行。后续功能应通过**小粒度 Pull Request** 持续合入。

---

## 2. 技术栈与架构

### 前端 (`/frontend`)

| 类别 | 技术 |
|------|------|
| 框架 | **Next.js** (App Router) |
| 语言 | **TypeScript** (strict mode) |
| UI 库 | **React** 18+ |
| 样式 | **TailwindCSS** |
| 状态管理 | React Context + useReducer（按需引入 Zustand） |
| 测试 | Vitest + React Testing Library |
| 构建工具 | Next.js 内置 (Turbopack) |

### 后端 (`/backend`)

| 类别 | 技术 |
|------|------|
| 语言 | **Python 3.11+** |
| 框架 | **FastAPI** |
| 依赖管理 | **Poetry** |
| 类型检查 | mypy (strict mode) |
| 测试 | pytest + pytest-asyncio |
| 代码格式化 | ruff (format + lint) |
| 向量数据库 | ChromaDB / Qdrant（用于 HAR 的 RAG 检索） |
| 数据校验 | Pydantic v2 |

### 核心算法模块（原创实现）

| 模块 | 缩写 | 说明 |
|------|------|------|
| 读者-重写器框架 | **R2** | 滑动窗口扫描小说块，逐块分析并改写为剧本片段 |
| 因果情节图构建 | **CPC** | 贪婪循环破除算法，将事件关系构建为有向无环图 (DAG) |
| 幻觉感知改进 | **HAR** | 基于向量 RAG 的自校正循环，检测并修正 LLM 幻觉 |

### 目标架构图

```text
Browser (Next.js SPA)
  ├─ 小说上传界面
  ├─ 章节预览与编辑
  ├─ DAG 可视化
  └─ 剧本预览与导出
        │
        ▼
FastAPI REST API
  ├─ POST /api/novels/upload    小说上传与章节解析
  ├─ POST /api/cpc/build         CPC 因果图构建
  ├─ POST /api/r2/scan           R2 滑动窗口扫描
  ├─ POST /api/har/refine        HAR 自校正
  ├─ GET  /api/screenplay/{id}   获取 ScreenYAML
  └─ GET  /api/export/{id}       导出剧本文件
```

---

## 3. 项目结构

```text
.
├── frontend/                   # Next.js (TypeScript) 前端
│   ├── src/
│   │   ├── app/                # App Router 页面
│   │   ├── components/         # 可复用 UI 组件
│   │   ├── hooks/              # 自定义 React Hooks
│   │   ├── lib/                # 工具函数与 API 客户端
│   │   └── types/              # TypeScript 类型定义
│   ├── public/                 # 静态资源
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── next.config.ts
│   └── package.json
│
├── backend/                    # Python 3.11+ / FastAPI 后端
│   ├── app/
│   │   ├── api/                # API 路由
│   │   ├── core/               # 配置、依赖注入
│   │   ├── models/             # Pydantic 模型 / DB 模型
│   │   ├── services/           # 业务逻辑层
│   │   │   ├── r2/             # R2 读者-重写器
│   │   │   ├── cpc/            # CPC 因果图构建
│   │   │   ├── har/            # HAR 幻觉自校正
│   │   │   └── screenplay/     # ScreenYAML 生成与导出
│   │   └── main.py             # FastAPI 入口
│   ├── tests/                  # 测试
│   ├── pyproject.toml
│   └── README.md
│
├── docs/                       # 架构、开发计划、提交清单
├── .github/                    # PR 模板
├── .gitignore
├── README.md
└── CLAUDE.md                   # 本文件
```

---

## 4. 构建、测试与运行命令

### 前端 (`/frontend`)

```bash
# 安装依赖
cd frontend
npm install

# 开发模式启动（默认 http://localhost:3000）
npm run dev

# 生产构建
npm run build

# 启动生产服务器
npm run start

# 运行测试
npm run test

# 运行测试（watch 模式）
npm run test:watch

# TypeScript 类型检查
npm run typecheck

# Lint 检查
npm run lint

# Lint 自动修复
npm run lint:fix
```

### 后端 (`/backend`)

```bash
# 安装依赖
cd backend
poetry install

# 开发模式启动（默认 http://localhost:8000）
poetry run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# 生产启动
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000

# 运行全部测试
poetry run pytest

# 运行特定模块测试
poetry run pytest tests/test_cpc.py

# 运行测试并输出覆盖率
poetry run pytest --cov=app --cov-report=term-missing

# 类型检查
poetry run mypy app

# 代码格式化
poetry run ruff format app tests

# Lint 检查
poetry run ruff check app tests

# Lint 自动修复
poetry run ruff check --fix app tests
```

### 全栈联调

```bash
# 终端 1：启动后端
cd backend && poetry run uvicorn app.main:app --reload

# 终端 2：启动前端
cd frontend && npm run dev
```

---

## 5. 代码风格与命名规范

### 通用原则

- **最小改动** — 只做任务要求的，不顺手重构、不额外抽象
- **照抄现有模式** — 项目中已有的写法就是规范
- **YAGNI** — 第一次不要抽象、不要设计模式、不要过度工程化
- **核心优先** — 先让基本流程跑通，再处理边界情况

### Python（后端）

| 规范 | 说明 |
|------|------|
| 格式化 | `ruff format`（等同于 Black，120 字符行宽） |
| Lint | `ruff check`（替代 flake8/isort/pylint） |
| 类型注解 | 所有公共函数必须有完整类型注解，使用 `from __future__ import annotations` |
| 命名 | 文件：`snake_case` · 类：`PascalCase` · 函数/变量：`snake_case` · 常量：`UPPER_SNAKE` |
| 导入顺序 | `__future__` → 标准库 → 第三方 → 内部模块（ruff 自动处理） |
| Pydantic | 模型使用 `BaseModel`，配置 `model_config = ConfigDict(extra="forbid")` |
| 异步 | API 路由全部使用 `async def`，CPU 密集型操作使用 `run_in_executor` |

### TypeScript / React（前端）

| 规范 | 说明 |
|------|------|
| 格式化 | Prettier（通过 ESLint 插件） |
| Lint | ESLint + `@next/eslint-plugin-next` |
| 类型 | 严格模式 (`strict: true`)，禁止 `any`（除非有明确注释说明） |
| 命名 | 文件：`kebab-case` · 组件：`PascalCase` · 函数/变量：`camelCase` · 类型/接口：`PascalCase` |
| 组件 | 优先使用 Server Components，需要交互时使用 Client Components (`"use client"`) |
| 导出 | 组件使用 `export default function`，工具函数使用命名导出 |
| 样式 | 使用 TailwindCSS utility class，避免内联 `style` 和 CSS Module |
| 状态 | 单组件用 `useState`，跨组件用 Context，全局按需引入 Zustand |

### 提交信息规范

```
类型: 简述（中文，不超过 50 字）

类型包括：
  feat     新功能
  fix      修复 Bug
  refactor 代码重构（不改变功能）
  docs     文档变更
  test     测试变更
  chore    构建/依赖/工具变更
  style    格式变更（不影响逻辑）

示例：
  feat: 新增小说章节解析模块
  fix: 修复 CPC 图循环检测边界条件
  docs: 补充 API 接口文档
```

---

## 6. Git 分支策略与版本控制

### 分支命名规范

| 前缀 | 用途 | 示例 |
|------|------|------|
| `feat/` | 新功能开发 | `feat/novel-upload` |
| `fix/` | Bug 修复 | `fix/cpc-cycle-detect` |
| `refactor/` | 代码重构 | `refactor/r2-window-scan` |
| `docs/` | 文档更新 | `docs/api-reference` |
| `test/` | 测试补充 | `test/har-rag-coverage` |
| `chore/` | 构建/依赖 | `chore/update-deps` |

### 分支操作流程

```bash
# 1. 从 main 切出功能分支
git switch main
git pull origin main
git switch -c feat/<feature-name>

# 2. 在功能分支上开发（原子化提交）
git add <relevant-files>
git commit -m "feat: <description>"

# 3. 推送功能分支
git push -u origin feat/<feature-name>

# 4. 在 GitHub/Gitee 创建 PR 并合并

# 5. PR 合并后，切回功能分支并同步 main 的最新代码
git switch feat/<feature-name>
git pull origin main

# 6. 后续相关功能继续在该分支上迭代（不再创建新分支）
# 该分支在整个功能大项开发周期内持续保留
```

### 分支策略规则

1. **`main` 是唯一长期分支**，始终保持可部署、可运行
2. **所有开发在功能分支上进行**，禁止直接在 `main` 上提交
3. **每个功能大项一个独立分支**，该分支在整个功能开发周期内持续保留
4. **同一功能大项下的子功能、修复、改进均在同一分支上提交和 PR**
5. **禁止批量导入/转储提交** — 所有代码必须通过 PR 逐步合入
6. **commit 时间戳**必须落在比赛批次开始与截止时间之内
7. **禁止最后一天一次性导入全部代码**（反批量提交防护）
8. **功能分支不删除**，PR 合并后该分支继续用于后续相关开发

---

## 7. 自动化 PR 工作流程

> 每次创建 PR 时，AI 助手必须严格按照以下步骤自动执行。

### 7.1 PR 创建前检查

```bash
# 1. 确认当前分支
git branch --show-current

# 2. 确认本地测试通过
cd backend && poetry run pytest
cd frontend && npm run test

# 3. 确认代码格式正确
cd backend && poetry run ruff check app tests
cd frontend && npm run lint

# 4. 确认 main 分支同步
git fetch origin main
git diff origin/main --stat
```

### 7.2 PR 描述模板

> 以下模板在创建 PR 时必须完整填写，由 AI 助手根据本次变更自动生成。

```markdown
## 标题

[一句话说明本 PR 新增或修改了什么，中文，不超过 50 字]

## 功能描述

[说明该功能的作用、使用方式和影响范围]

## 实现思路

[说明核心实现逻辑、技术选型、关键文件和主要取舍]

### 算法说明（如适用）

- **CPC 相关**：说明使用的循环破除策略、DAG 构建逻辑
- **R2 相关**：说明滑动窗口参数、重写触发条件
- **HAR 相关**：说明 RAG 检索策略、自校正循环终止条件

### 第三方库声明

- 新增库：[列出所有新增的三方库及其必要性说明]
- 如无新增：本 PR 未引入新的第三方依赖

### 原创代码路径

[明确指出哪些代码是本项目的原创实现，哪些是调用第三方库]

## 测试方式

- [ ] 本地单元测试通过
- [ ] 本地集成测试通过
- [ ] 手动验证核心流程通过

验证步骤：
1. [具体操作步骤]
2. [预期结果]

```

### 7.3 团队分配页脚

```markdown
---
**团队分配**：本 PR 由 [开发者 A / 开发者 B] 负责实现与自测。
**关联 Issue**：[如有]
**依赖 PR**：[如有，列出必须先行合并的 PR]
```

### 7.4 PR 标题示例

```
feat: 新增小说章节解析模块
feat: 实现 CPC 因果图贪婪循环破除算法
feat: 新增 HAR 幻觉自校正循环
feat: 实现 ScreenYAML 结构化剧本导出
fix: 修复滑动窗口越界导致的章节丢失
docs: 补充 R2 框架设计文档
```

---

## 8. 双人团队身份管理

> **关键规则**：双人团队必须在 Git 历史中体现各自的独立贡献。

### 8.1 提交前身份验证

在执行任何 `git commit` 或 `git push` 之前，AI 助手**必须**：

```bash
# 1. 检查当前 Git 配置
git config user.name
git config user.email

# 2. 提示用户确认身份
# "当前 Git 身份：{user.name} <{user.email}>
#  请确认这是你的活动工作区吗？
#  - 开发者 A：[姓名] <[email]>
#  - 开发者 B：[姓名] <[email]>"
```

**如用户确认的身份与配置不一致**，必须先修正：

```bash
git config user.name "开发者真实姓名"
git config user.email "开发者真实邮箱"
```

### 8.2 身份保护规则

| 规则 | 说明 |
|------|------|
| **禁止代提交** | 不得由一人代另一人提交代码 |
| **独立 PR** | 每位队员通过独立 PR 体现贡献 |
| **真实账号** | 使用个人 GitHub/Gitee 账号，不得使用团队公用账号 |
| **PR 标注** | 每个 PR 描述中必须标注实际实现者 |
| **分工清晰** | 文档、测试、视频等非代码贡献也应通过独立 PR 体现 |

### 8.3 当前开发者配置

| 角色 | 用户名 | 邮箱 |
|------|--------|------|
| 开发者 A | `uYu` | `702669879@qq.com` |
| 开发者 B | `rayi` | `2447845922@qq.com` |

---

## 9. "始终绿色"主分支规则

### 9.1 `main` 分支铁律

1. **`main` 必须始终保持完全可部署和可运行的状态**
2. 任何导致 `main` 无法构建或运行的合并都是最高优先级事故
3. 合并前**必须**在本地通过全部测试

### 9.2 合并前强制检查

```bash
# === 后端检查 ===
cd backend
poetry run ruff check app tests       # Lint 零报错
poetry run mypy app                   # 类型检查通过
poetry run pytest                     # 全部测试通过

# === 前端检查 ===
cd frontend
npm run lint                          # Lint 零报错
npm run typecheck                     # TypeScript 类型检查通过
npm run test                          # 全部测试通过
npm run build                         # 生产构建成功
```

### 9.3 合并失败应急处理

如合并后发现 `main` 不可运行：

1. **立即**通知另一位队员
2. **回滚**可疑 PR（优先于修复，减少阻塞时间）
3. 在独立 `fix/` 分支上修复
4. 重新提交 PR，附上根因分析

---

## 10. 提交合规检查清单

> 每次 PR 合并、每次提交、每个开发阶段结束前，必须逐项核对。

### 仓库

- [ ] 远端仓库创建时间晚于官方开题时间
- [ ] 仓库可公开访问（评审阶段）
- [ ] `.gitignore` 排除密钥文件（`.env`、`.mcp.json`、`settings.local.json`、`cookies.txt`、`credentials.*`）
- [ ] 仓库中无 API key、token、密码

### Commit

- [ ] 所有 commit 时间戳在比赛批次时间范围内
- [ ] 持续提交，无集中批量导入
- [ ] 每位队员使用自己的账号提交
- [ ] commit message 符合规范（`类型: 简述`）

### PR

- [ ] 每个 PR 只做一件事
- [ ] PR 标题一句话说明变更
- [ ] PR 描述包含：功能描述、实现思路、测试方式
- [ ] PR 描述标注团队分配
- [ ] 新增第三方库已在 PR 描述和 README 中声明
- [ ] 复用代码已在 PR 描述中注明来源
- [ ] 合并前本地测试通过

### README

- [ ] 说明项目议题方向和核心功能
- [ ] 说明本地启动方式和环境要求
- [ ] 列明所有第三方依赖
- [ ] 说明原创功能范围
- [ ] Demo 视频链接可访问、可播放

---

## 附录 A：AI 助手行为准则

> 以下准则适用于本项目中 AI 助手的所有操作。

1. **先列计划再改动** — 多文件改动前先列出要改的文件，等确认
2. **不确定时先确认** — 不要猜测用户意图
3. **最小改动原则** — 只做用户要求的，不顺手重构
4. **优先跑通基本流程** — 再处理边界情况和优化
5. **每次任务结束写入记忆** — 技术决策、Bug 根因、用户偏好写入 `~/.claude/projects/qiniuyun/memory/`

## 附录 B：常用参考文件

| 文件 | 内容 |
|------|------|
| [README.md](README.md) | 项目介绍、技术栈、本地运行 |
| [docs/screenyaml-schema.md](docs/screenyaml-schema.md) | ScreenYAML 结构化剧本格式定义 |
| [docs/api-contract.md](docs/api-contract.md) | API 接口文档 |
| [docs/architecture.md](docs/architecture.md) | 架构设计与模块拆分 |
| [docs/submission-checklist.md](docs/submission-checklist.md) | 提交合规检查清单 |
| [docs/demo-video-script.md](docs/demo-video-script.md) | Demo 视频脚本 |
| [.github/pull_request_template.md](.github/pull_request_template.md) | GitHub PR 模板 |
