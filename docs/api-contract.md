# 前后端 API 协定

> **目的**：让开发者 A（后端）和开发者 B（前端）可以并行工作，互不阻塞。
>
> **核心原则**：API 形状是本文件的"合约"。合约稳定期内，双方各自独立开发，不互相等待。
>
> 最后更新：2026-06-07 · 当前分支：`feat/screenyaml-mvp`

---

## 1. 并行工作边界

```
开发者 A（uYu / 后端）              开发者 B（rayi / 前端）
─────────────────────────          ─────────────────────────
feat/screenyaml-mvp                 feat/frontend-yaml
     │                                    │
     ├─ FastAPI 路由                         ├─ Next.js 页面
     ├─ Pydantic 模型（← 合约源）            ├─ TypeScript 类型（→ 照抄模型）
     ├─ 业务服务层                           ├─ API 客户端 (lib/api.ts)
     ├─ 测试                                ├─ UI 组件
     └─ 算法核心（CPC/R2/HAR）              └─ 样式 / 交互
```

**B 不依赖 A 的内部实现，只依赖 API 合约。** 合约由后端 Pydantic 模型定义，前端 TypeScript 类型应与之同步。

---

## 2. 当前 API 端点总览

| 方法 | 路径 | 说明 | 状态 |
|------|------|------|------|
| `GET` | `/api/health` | 健康检查 | ✅ 稳定 |
| `POST` | `/api/novels/upload` | 上传小说 TXT | ✅ 稳定 |
| `GET` | `/api/novels/{id}` | 获取小说详情 | ✅ 稳定 |
| `POST` | `/api/screenplay/generate` | 生成剧本 | ⚠️ 当前为 mock |
| `GET` | `/api/screenplay/{id}` | 获取已生成剧本 | ✅ 稳定 |
| `GET` | `/api/export/{id}?format=` | 导出剧本文件 | ✅ 稳定 |

后端默认运行在 `http://localhost:8000`。

---

## 3. 数据模型（合约源：后端 Pydantic → 前端 TypeScript 对应）

### 3.1 Novel（小说）

**后端** `app/models/novel.py`：

```python
class Chapter(BaseModel):
    id: str           # UUID
    index: int        # 章节序号，从 1 开始
    title: str        # 章节标题
    content: str      # 章节正文
    word_count: int   # 字数

class Novel(BaseModel):
    id: str           # UUID
    title: str        # 小说标题（从文件名推断）
    filename: str     # 原始上传文件名
    chapters: list[Chapter]
    created_at: datetime  # ISO 8601 UTC
```

**前端** 应在 `types/index.ts` 中对应：

```typescript
interface Chapter {
  id: string;
  index: number;
  title: string;
  content: string;
  word_count: number;
}

interface Novel {
  id: string;
  title: string;
  filename: string;
  chapters: Chapter[];
  created_at: string;  // ISO 8601
}
```

### 3.2 Screenplay（剧本）

**后端** `app/models/screenplay.py`：

```python
class SceneElement(BaseModel):
    type: Literal["action", "character", "dialogue", "parenthetical"]
    content: str
    character: str | None = None  # 仅 dialogue/parenthetical 时有值

class Scene(BaseModel):
    index: int                    # 场景序号
    setting: str = ""             # 场景描述
    location: str = ""            # 地点
    time_of_day: str = ""         # 时间（日/夜/黄昏/黎明）
    source_chapter: int = 0       # 来源章节序号
    characters: list[str] = []    # 出场角色
    elements: list[SceneElement]  # 剧本元素列表

class Screenplay(BaseModel):
    id: str                       # UUID
    novel_id: str                 # 关联的小说 ID
    title: str                    # 剧本标题
    source_novel: str = ""        # 原著名称
    novel_author: str = ""        # 原著作者
    total_chapters: int = 0       # 原著总章节数
    generated_by: str = ""        # 生成方式（LLM 模型名 或 "mock"）
    scenes: list[Scene]
```

**前端** 应在 `types/index.ts` 中对应（当前前端类型**缺少** `location`、`time_of_day`、`source_chapter`、`characters`、`source_novel`、`novel_author`、`total_chapters`、`generated_by` —— **B 需要同步更新**）：

```typescript
type SceneElementType = "action" | "character" | "dialogue" | "parenthetical";

interface SceneElement {
  type: SceneElementType;
  content: string;
  character: string | null;
}

interface Scene {
  index: number;
  setting: string;
  location: string;         // ← 新增
  time_of_day: string;      // ← 新增
  source_chapter: number;   // ← 新增
  characters: string[];     // ← 新增
  elements: SceneElement[];
}

interface Screenplay {
  id: string;
  novel_id: string;
  title: string;
  source_novel: string;     // ← 新增
  novel_author: string;     // ← 新增
  total_chapters: number;   // ← 新增
  generated_by: string;     // ← 新增
  scenes: Scene[];
}
```

### 3.3 导出格式

| format 参数 | 文件类型 | Content-Type | 说明 |
|---|---|---|---|
| `txt` | `.txt` | `text/plain; charset=utf-8` | 纯文本剧本 |
| `docx` | `.docx` | `application/vnd.openxmlformats...` | Word 文档 |
| `yaml` | `.yaml` | `application/x-yaml; charset=utf-8` | ScreenYAML 结构化格式 |

---

## 4. API 详细合约

### 4.1 POST /api/novels/upload

```
请求: multipart/form-data
  字段: file (TXT 文件，最大 500KB)

成功响应 200:
{
  "id": "uuid",
  "title": "西游记",
  "filename": "西游记.txt",
  "chapters": [
    {
      "id": "uuid",
      "index": 1,
      "title": "第一回 灵根育孕源流出...",
      "content": "诗曰：混沌未分天地乱...",
      "word_count": 1234
    }
  ],
  "created_at": "2026-06-07T12:00:00Z"
}

错误响应:
  400 - 文件类型非 TXT / 文件过大 / 编码无法识别
```

### 4.2 GET /api/novels/{novel_id}

```
成功响应 200: Novel 对象（同上）
错误响应 404: { "detail": "Novel not found" }
```

### 4.3 POST /api/screenplay/generate

```
请求: application/json
{
  "novel_id": "uuid"
}

成功响应 200: Screenplay 对象
错误响应 404: { "detail": "Novel not found" }

注意:
  - 当前为 mock 实现，不调用真实 LLM
  - 幂等：同一 novel_id 多次调用返回同一个已生成的剧本
  - 后续接入真实 LLM 后，响应形状不变
```

### 4.4 GET /api/screenplay/{screenplay_id}

```
成功响应 200: Screenplay 对象
错误响应 404: { "detail": "Screenplay not found" }
```

### 4.5 GET /api/export/{screenplay_id}?format=txt|docx|yaml

```
成功响应 200: 文件下载（Content-Disposition: attachment）
错误响应 404: { "detail": "Screenplay not found" }
```

---

## 5. 当前状态：哪些稳定、哪些在变

| 范围 | 稳定性 | 说明 |
|------|--------|------|
| API 路径和方法 | ✅ 稳定 | 不会改 |
| Novel / Screenplay 字段 | ✅ 稳定 | 只增不减 |
| 响应状态码和错误格式 | ✅ 稳定 | `{ "detail": "..." }` |
| 后端内部服务实现 | ⚠️ 在变 | A 会重构，不影响合约 |
| LLM 生成质量 | ⚠️ 在变 | 当前 mock，后续接入真实模型 |
| 新增 API（CPC/R2/HAR） | 📋 规划中 | 会新增端点，不影响现有端点 |

---

## 6. 并行工作建议

### B 可以独立推进的工作（不依赖 A 当前进度）

1. **同步前端类型** — 按第 3 节补全 TypeScript 类型定义
2. **YAML 导出按钮** — 后端 `format=yaml` 已通，前端加个按钮即可
3. **剧本预览增强** — 利用 `location`、`time_of_day`、`characters` 等新字段丰富页面展示
4. **章节管理界面** — 基于 `Novel.chapters` 做章节列表和内容预览
5. **错误处理 UI** — 各 API 的错误状态展示
6. **上传体验优化** — 拖拽上传、进度条等

### A 当前正在做的事（B 不需要等）

- 修复 mypy 类型检查错误（纯后端代码质量，不影响 API）
- 后续：实现 CPC / R2 / HAR 算法核心

---

## 7. 协作规则

1. **API 合约变更**：A 如果要改 API 形状（增删字段、改路径），必须先更新本文档并通知 B
2. **新增字段**：后端 Pydantic 模型新增字段时，前端类型应同步新增（不删旧字段即可兼容）
3. **各自分支**：A 在 `feat/screenyaml-mvp`，B 在 `feat/frontend-yaml`，通过 PR 合入 main
4. **不互相等待**：B 不需要等 A 的算法实现完成再写 UI；用 mock 数据联调即可
