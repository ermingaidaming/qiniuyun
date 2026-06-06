# AI 小说转剧本工具

面向比赛议题"基于大语言模型与实时音视频技术的下一代 AI 核心应用研发"的 AI 小说自动转剧本工具。

当前仓库是参赛项目的起步骨架，目标是先保证主分支可运行、提交记录可追踪、README 与 PR 描述符合评审规则。后续功能应通过小粒度 Pull Request 持续合入。

## 项目简介

基于大语言模型实现小说自动转剧本。用户上传小说后，系统通过三大核心算法模块（CPC 因果图构建、R2 滑动窗口扫描、HAR 幻觉自校正）自动将小说文本转化为符合 Draft 2026-01 剧本模式的 ScreenYAML 结构化剧本，并支持 Word/PDF 导出。

## 核心功能

- **小说上传与章节解析**：支持 TXT/EPUB 格式上传，自动识别章节边界
- **CPC 因果情节图构建**：使用贪婪循环破除算法将事件关系构建为有向无环图 (DAG)，确保因果链完整无循环
- **R2 读者-重写器框架**：滑动窗口扫描小说块，逐块分析并改写为剧本片段
- **HAR 幻觉感知改进**：基于向量 RAG 的自校正循环，检测并修正 LLM 生成中的事实性偏差
- **ScreenYAML 结构化输出**：生成符合 Draft 2026-01 剧本模式的 ScreenYAML（验证 UUID、角色关系和明确元素类型：动作、角色、对话、括号）
- **剧本导出**：支持 Word 和 PDF 格式导出

## 技术栈

### 后端

- Python 3.11+
- FastAPI
- Poetry（依赖管理）
- Pydantic v2（数据校验）
- pytest（测试）
- ruff（格式化 + Lint）
- mypy（类型检查）
- ChromaDB / Qdrant（向量数据库，用于 HAR 的 RAG 检索）

### 前端

- Next.js (App Router)
- TypeScript (strict mode)
- React 18+
- TailwindCSS
- Vitest + React Testing Library

## 目录结构

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
│   └── package.json
│
├── backend/                    # Python 3.11+ / FastAPI 后端
│   ├── app/
│   │   ├── api/                # API 路由
│   │   ├── core/               # 配置、依赖注入
│   │   ├── models/             # Pydantic 模型
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
├── docs/                       # 架构、开发计划、提交清单和视频脚本
├── .github/                    # PR 模板
├── .gitignore
├── .editorconfig
├── README.md
└── CLAUDE.md                   # 项目权威参考文件
```

## 本地运行

```bash
# 后端
cd backend
poetry install
poetry run uvicorn app.main:app --reload

# 前端（另开终端）
cd frontend
npm install
npm run dev
```

访问 http://localhost:3000 查看前端界面，http://localhost:8000/docs 查看后端 API 文档。

## 核心算法（原创实现）

| 模块 | 缩写 | 说明 |
|------|------|------|
| 读者-重写器框架 | R2 | 滑动窗口扫描小说块，逐块分析并改写为剧本片段 |
| 因果情节图构建 | CPC | 贪婪循环破除算法，将事件关系构建为有向无环图 (DAG) |
| 幻觉感知改进 | HAR | 基于向量 RAG 的自校正循环，检测并修正 LLM 幻觉 |

## 依赖声明

当前版本依赖：

- Python 3.11+ 标准库
- FastAPI + Uvicorn（Web 框架）
- Pydantic v2（数据校验）
- Next.js + React + TailwindCSS（前端框架）
- ChromaDB（向量检索，用于 HAR）

后续引入大模型 API、云服务 SDK 或其他第三方库时，必须同步更新本节，并说明哪些功能为原创实现、哪些能力来自第三方库或服务。

## 原创范围

原创内容包括：

- **CPC 贪婪循环破除算法**：将非线性事件关系转化为合法 DAG 的核心逻辑
- **R2 滑动窗口重写策略**：窗口调度、上下文拼接、重写触发条件的原创设计
- **HAR 自校正循环**：RAG 检索→幻觉检测→修正→再验证的完整闭环
- **ScreenYAML 生成与校验**：Draft 2026-01 模式的结构化输出与 UUID 验证
- **前端 DAG 可视化**：因果图的交互式渲染组件

如复用队员过往代码片段，必须在对应 PR 描述中写明来源、文件路径和改动范围。

## Demo 视频

Demo 视频链接待补充。提交前需要上传到可访问平台，并将链接替换到这里：

```text
TODO: https://example.com/demo-video
```

视频应包含声音讲解，覆盖核心模块、运行方式、主要功能和效果。

## 持续交付约定

- 远端仓库必须在官方开题后创建。
- 所有 commit 时间戳必须落在所选批次的开始与截止时间之内。
- 禁止最后一天一次性导入所有代码。
- 每个 PR 只做一件事，标题和描述必须与实际代码变更一致。
- PR 描述必须包含功能描述、实现思路、测试方式。
- 合并后 `main` 分支必须保持可运行。
- 多人组队时，每位队员使用自己的 GitHub/Gitee 账号提交 commit。

详细检查项见 [docs/submission-checklist.md](docs/submission-checklist.md)，远端仓库创建与 PR 流程见 [docs/repository-setup.md](docs/repository-setup.md)。

## 分支与 PR 命名示例

```text
feat/novel-upload        feat/chapter-parser       feat/cpc-dag-builder
feat/r2-window-scanner   feat/har-rag-refiner      feat/screenyaml-export
feat/dag-visualization   feat/screenplay-preview   docs/demo-video-script
```

PR 标题示例：

```text
feat: 新增小说上传与章节解析 API
feat: 实现 CPC 因果图贪婪循环破除算法
feat: 新增 R2 滑动窗口扫描与改写模块
feat: 实现 HAR 幻觉感知自校正循环
feat: 新增 ScreenYAML 结构化剧本导出
feat: 新增 DAG 因果图可视化组件
```

## 知识产权说明

本仓库当前未声明开源许可证。除比赛规则另有约定外，作品知识产权归提交队伍所有。公开仓库前应确认不包含未经授权的第三方代码、模型权重、音视频素材、密钥或内部资料。
