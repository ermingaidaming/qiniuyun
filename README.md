# AI 小说转剧本工具

面向比赛议题「基于大语言模型与实时音视频技术的下一代 AI 核心应用研发」的 AI 小说自动转剧本工具。

用户上传小说 TXT 文件后，系统通过三大原创算法模块（CPC 因果图构建、R2 滑动窗口改写、HAR 幻觉校正）自动将小说文本转化为结构化的 **ScreenYAML** 剧本格式，支持 TXT / Word / YAML 导出。

---

## 核心功能

| 功能 | 说明 |
|------|------|
| 📖 小说上传与章节解析 | 上传 TXT 文件，自动识别中英文章节标题并拆分 |
| 🔗 CPC 因果情节图 | 事件抽取 + 因果关系识别 + 贪婪循环破除，构建合法 DAG |
| 🔄 R2 滑动窗口改写 | 4000 字窗口 + 800 字重叠，逐块 LLM 改写为剧本片段，Jaccard 去重 |
| 🔍 HAR 幻觉校正 | 5 类幻觉检测（角色/事件/对话/场景/细节），原文全文 fallback，最多 2 轮自校正 |
| 📜 ScreenYAML 输出 | 符合 Draft 2026-01 模式的四元素结构化剧本（动作/角色/对话/括号提示） |
| 📤 多格式导出 | 支持 TXT、Word (.docx)、YAML 三种格式 |

---

## 技术架构

```
Browser (Next.js SPA)
  ├─ 小说上传界面
  ├─ 剧本预览（ScreenYAML 渲染）
  ├─ R2 改写预览 + HAR 审核
  └─ 格式导出
        │
        ▼
FastAPI REST API (13 个端点)
  ├─ POST /api/novels/upload     小说上传与章节解析
  ├─ POST /api/cpc/build          CPC 因果图构建
  ├─ POST /api/r2/scan            R2 滑动窗口扫描
  ├─ POST /api/har/refine         HAR 自校正
  ├─ POST /api/pipeline/run       全流水线（CPC → R2 → HAR → ScreenYAML）
  ├─ POST /api/screenplay/generate  剧本生成
  ├─ GET  /api/export/{id}        剧本导出
  └─ ...
        │
        ▼
SQLite 持久化 + LLM API (DeepSeek / OpenAI 兼容)
```

### 流水线数据流

```
小说上传 → 章节解析 → CPC 因果图 → R2 滑动窗口改写 → Screenplay → HAR 幻觉校正 → ScreenYAML 输出
              │              │                    │                  │                   │
          章节存储       事件+关系 DAG        窗口场景片段        完整剧本草稿        校正后剧本
```

每步幂等——失败后重新运行自动跳过已完成的步骤。

---

## 核心算法（原创实现）

### CPC — 因果情节图构建

1. **事件抽取**：LLM 从每章提取关键事件（描述/角色/地点/时间）
2. **关系识别**：识别事件间因果关系（causes）、时序关系（before）、引用关系（references）
3. **贪婪循环破除**：检测 DAG 中的环，按置信度从低到高移除边，直到图无环

### R2 — 滑动窗口改写引擎

1. **窗口构建**：全文章节拼接后按窗口大小切分，记录每个窗口的中点所在章节
2. **逐窗 LLM 改写**：每窗口独立调用 LLM 转化为剧本场景（含 location / time / characters / elements）
3. **Jaccard 去重**：相邻窗口的相似场景（Jaccard ≥ 0.7）合并去重

### HAR — 幻觉感知自校正

1. **五类幻觉检测**：角色错误、事件虚构、对话编造、场景篡改、细节偏差
2. **原文对照**：按 `source_chapter` 定位原文；若章节索引为 0，使用全小说文本做 fallback
3. **自校正循环**：检测 → 基于原文证据修正 → 再验证，最多 2 轮

### ScreenYAML — 结构化剧本格式

原创设计的剧本交换格式（Draft 2026-01），基于 YAML 1.2，参考 Final Draft (.fdx) 和 Fountain 规范：

```yaml
scenes:
  - scene_id: 1
    location: "青云宗练功场"
    time: "白天"
    setting: "人头攒动的广场上，测试正在进行..."
    source_chapter: 1
    characters: ["萧炎", "中年测验员", "萧媚"]
    elements:
      - type: action
        content: "测验魔石碑上闪亮起五个大字..."
      - type: character
        name: "中年测验员"
      - type: dialogue
        character: "中年测验员"
        text: "萧炎，斗之力，三段！级别：低级！"
      - type: parenthetical
        character: "萧炎"
        text: "（面无表情）"
```

详细 Schema 见 [docs/screenyaml-schema.md](docs/screenyaml-schema.md)。

---

## 本地运行

### 环境要求

- Python 3.11+ / Poetry
- Node.js 18+ / npm
- LLM API Key（DeepSeek 或 OpenAI 兼容接口）

### 启动步骤

```bash
# 1. 克隆仓库
git clone https://github.com/ermingaidaming/qiniuyun.git
cd qiniuyun

# 2. 配置 LLM API
cp backend/.env.example backend/.env
# 编辑 backend/.env，填入你的 LLM_API_KEY、LLM_BASE_URL、LLM_MODEL

# 3. 启动后端（终端 1）
cd backend
poetry install
poetry run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# 4. 启动前端（终端 2）
cd frontend
npm install
npm run dev

# 5. 访问
# 前端：http://localhost:3000
# API 文档：http://localhost:8000/docs
```

> **注意**：不配置 `LLM_API_KEY` 时系统使用内置 mock 数据，方便验证流水线是否跑通。

---

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| POST | `/api/novels/upload` | 小说上传与章节解析 |
| GET | `/api/novels/{id}` | 获取小说详情 |
| POST | `/api/cpc/build` | CPC 因果图构建 |
| GET | `/api/cpc/{id}/graph` | 获取 DAG 图数据 |
| POST | `/api/r2/scan` | R2 滑动窗口扫描 |
| GET | `/api/r2/{id}/result` | 获取 R2 改写结果 |
| POST | `/api/har/refine` | HAR 幻觉自校正 |
| GET | `/api/har/{id}/report` | 获取 HAR 校正报告 |
| POST | `/api/screenplay/generate` | 剧本生成 |
| GET | `/api/screenplay/{id}` | 获取剧本详情 |
| POST | `/api/pipeline/run` | 全流水线执行 |
| GET | `/api/export/{id}` | 剧本导出（txt/docx/yaml） |

完整 API 合约见 [docs/api-contract.md](docs/api-contract.md)。

---

## 测试

```bash
cd backend
poetry run pytest                     # 41 个测试
poetry run pytest --cov=app --cov-report=term-missing
```

---

## 技术栈

### 后端
| 类别 | 技术 |
|------|------|
| 语言 | Python 3.12 |
| 框架 | FastAPI |
| 依赖管理 | Poetry |
| 数据校验 | Pydantic v2 |
| 数据库 | SQLite (aiosqlite) |
| 测试 | pytest + pytest-asyncio |
| 代码质量 | ruff (format + lint) |

### 前端
| 类别 | 技术 |
|------|------|
| 框架 | Next.js 16 (App Router) |
| 语言 | TypeScript (strict) |
| UI | React 18 + TailwindCSS |
| 构建 | Turbopack |

### 外部服务
| 服务 | 用途 |
|------|------|
| LLM API | 文本改写、事件抽取、幻觉检测（支持 DeepSeek / OpenAI 兼容接口） |

---

## 原创范围

以下模块为本项目的原创设计与实现：

- **CPC 贪婪循环破除算法**：非线性事件关系 → 合法 DAG 的核心逻辑
- **R2 滑动窗口重写策略**：窗口构建、章节边界追踪、Jaccard 去重的完整设计
- **HAR 五类幻觉检测 + 自校正循环**：检测→修正→再验证的完整闭环，含全文 fallback
- **ScreenYAML 格式设计**：Draft 2026-01 四元素剧本模式，从零设计的 YAML 交换格式
- **流水线编排**：CPC → R2 → Screenplay → HAR → ScreenYAML 全链路，每步幂等可续跑
- **前端 ScreenYAML 渲染**：带类型标签和说话人标注的剧本预览组件

---

## 目录结构

```text
.
├── backend/
│   ├── app/
│   │   ├── api/                # API 路由（cpc / r2 / har / screenplay / pipeline / export）
│   │   ├── core/               # 配置
│   │   ├── db/                 # 数据库引擎 + repository
│   │   ├── models/             # Pydantic 模型
│   │   └── services/           # 业务逻辑（llm / cpc / r2 / har / screenplay / screenyaml / pipeline / novel / export）
│   ├── tests/                  # 41 个测试
│   └── pyproject.toml
├── frontend/
│   └── src/
│       ├── app/                # 页面（首页 / 剧本预览 / R2 预览 / HAR 审核）
│       ├── lib/                # API 客户端
│       └── types/              # TypeScript 类型定义
├── docs/
│   ├── screenyaml-schema.md    # ScreenYAML 格式定义
│   ├── api-contract.md         # API 接口文档
│   ├── architecture.md         # 架构设计文档
│   ├── submission-checklist.md # 提交合规清单
│   └── demo-video-script.md    # Demo 视频脚本
└── README.md
```

---

## Demo 视频

> TODO: 补充视频链接

---

## 团队

| 角色 | GitHub |
|------|--------|
| 开发者 A — uYu | [@ermingaidaming](https://github.com/ermingaidaming) |
| 开发者 B — rayi | [@rayi](https://github.com/rayi) |

---

## 知识产权

本仓库未声明开源许可证。除比赛规则另有约定外，作品知识产权归提交队伍所有。使用的第三方库均遵守其各自许可证。
