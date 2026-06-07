# 项目审视报告：AI 小说转剧本工具

> 2026-06-07 · 基于同类产品调研与代码深度分析的独立评估

---

## 目录

1. [核心发现：项目渊源](#1-核心发现项目渊源)
2. [架构不合理之处](#2-架构不合理之处)
3. [数据层问题](#3-数据层问题)
4. [算法实现差距](#4-算法实现差距)
5. [前端与异步差距](#5-前端与异步差距)
6. [流水线设计缺陷](#6-流水线设计缺陷)
7. [竞争力分析（与同类产品对比）](#7-竞争力分析)
8. [改进建议（优先级排序）](#8-改进建议)

---

## 1. 核心发现：项目渊源

### 1.1 项目源头

本项目的核心算法命名（CPC / R2 / HAR）与 ICLR 2025 论文 **"R²: A LLM Based Novel-to-Screenplay Generation Framework with Causal Plot Graphs"**（arXiv: 2503.15655）**完全一致**。

| 本项目 | 论文 | 一致性 |
|--------|------|--------|
| CPC（Causal Plot Graph） | CPC（Causal Plot-Graph Construction） | 名称、算法思路相同 |
| R2（Reader-Rewriter） | R²（Reader-Rewriter） | 名称完全相同 |
| HAR（Hallucination-Aware Refinement） | HAR（Hallucination-Aware Refinement） | 名称完全相同 |
| ScreenYAML | 论文输出格式 | 概念相同 |

论文作者来自中国科学技术大学、安徽建筑大学、安徽大学。项目 README 将 CPC、R2、HAR 标记为"原创实现"，但未提及该论文。

### 1.2 影响

- **比赛合规风险**：比赛通常要求声明参考来源。论文发表于 2025 年 3 月，已是公开学术成果
- **"原创"声明可能被质疑**：README 的"原创范围"一节声称 CPC/R2/HAR 为原创，但核心架构来自已发表论文
- **建议**：在 README 和 PR 中明确声明参考了该论文，说明哪些是论文思路的工程实现、哪些是真正的原创改进

---

## 2. 架构不合理之处

### 2.1 R2 与 Screenplay 数据完全重复  **[严重]**

当前存在两套几乎完全相同的表结构：

```
R2 侧：                          Screenplay 侧：
r2_scans                        screenplays
├── r2_scenes                    ├── scenes
│   └── r2_scene_elements        │   └── scene_elements
```

`R2SceneTable` 和 `SceneTable` 的字段有 80% 重叠（index、setting、location、time_of_day、characters、elements）。同一个"场景"概念被存储了两遍。

**问题**：
- R2 生成的场景存入 `r2_scenes`，Screenplay 生成的场景存入 `scenes`——数据不互通
- HAR 操作的是 screenplay 生成的 scenes，但 R2 也生成 scenes——HAR 无法直接消费 R2 的输出
- 流水线中 R2 → HAR → ScreenYAML 的理论数据流断裂：HAR 从 screenplay 表取数据，而非从 R2 表

**合理做法**：
- 合并为统一的 `scenes` 表，增加 `source` 字段标记生成来源（`screenplay_generate` / `r2_scan`）
- 或者 R2 直接写入 screenplay 的 scenes 表（当前 R2 功能与 screenplay_service 高度重叠）

### 2.2 CPC、R2、HAR 三个垂直孤岛  **[严重]**

三个核心算法模块之间存在明显的"数据孤岛"：

```
CPC ─── 产出 CausalGraph（存入 cpc_graphs）
R2 ─── 产出 R2ScanResult（存入 r2_scans） 
HAR ─── 产出 HARReport（存入 har_reports）
        └── 但它操作的是 screenplay 表的 scenes，不是 R2 的
```

R2 论文中的设计是：**CPC 产出的因果图 → 指导 R2 的窗口调度策略**。但当前实现中：
- R2 完全不知道 CPC 的存在，只是机械地滑动窗口
- HAR 不知道 CPC 的因果关系，无法做因果级幻觉检测
- 三个模块各自独立运行，流水线只是简单的顺序 try/except

### 2.3 缺少 Alembic 数据库迁移  **[中等]**

[engine.py](backend/app/db/engine.py) 使用 `Base.metadata.create_all(_sync_engine)` 在模块导入时创建表。这是开发玩具的做法，不适合任何生产或比赛场景：

- 无法追踪 schema 变更历史
- 字段修改需要手动删库重建
- 多人协作时 schema 冲突无法解决
- 比赛中评审可能要求审查 schema 演进过程

### 2.4 FastAPI 路由层没有依赖注入  **[中等]**

CLAUDE.md 提到 FastAPI 规则要求使用 `Depends()` 注入数据库会话和依赖。当前的实际做法是每个 service 函数内部自己创建 session：

```python
# 当前做法 (每个 service 函数里)
async with async_session() as session:
    ...
```

导致：
- 无法在测试中替换数据库依赖
- 每个 service 函数独立管理事务边界，无法做跨 service 事务
- 与 FastAPI 最佳实践不符

---

## 3. 数据层问题

### 3.1 SQLite 用于多步骤长事务流水线  **[严重]**

当前使用 SQLite + aiosqlite。流水线（CPC → R2 → HAR → ScreenYAML）是全异步、多步骤、长耗时的操作。SQLite 的问题：

- **单写者锁**：任何写操作会锁定整个数据库。流水线各步骤无法并发写入
- **无连接池**：aiosqlite 实际上在异步模式下也是串行的
- **不适合 Web 服务**：SQLite 适合嵌入式/移动端/单用户场景，不适合多并发 API

对于比赛场景，可能评估者会同时上传多个小说——多个流水线并发执行时 SQLite 会成为瓶颈。建议至少使用 PostgreSQL（或比赛环境支持的任意关系数据库）。

### 3.2 缺少向量数据库实现  **[严重]**

README 和 CLAUDE.md 声称使用 ChromaDB / Qdrant 做向量 RAG 检索。**实际代码中完全没有向量数据库的使用**。

[HAR 服务](backend/app/services/har_service.py) 的 `_detect_hallucinations` 函数直接将整段原文塞进 LLM prompt：

```python
source_text=chapter.content[: settings.max_chapter_length_chars],
```

这不是 RAG——这是 context stuffing。真正的 RAG 应该：
1. 将小说文本向量化并建索引
2. 对每个场景做语义检索，找到最相关的原文片段
3. 将检索结果作为上下文提供给幻觉检测

### 3.3 数据模型 ID 生成不一致  **[低]**

- CPC 事件 ID 使用确定性算法：`short_novel_id-e{index}`
- 其他所有实体使用 `str(uuid.uuid4())`
- 混用两种策略但没有文档说明原因

---

## 4. 算法实现差距

### 4.1 HAR 幻觉检测严重简化  **[严重]**

论文中的 HAR 是多轮迭代的自校正循环（检测 → 定位 → 上下文检索 → 修正 → 再验证）。当前实现：

- **RAG 部分完全缺失**：没有向量检索，只是截取章节前 16000 字符
- **修正逻辑过于简单**：只是字符串替换 `elem.content.replace(hallucinated_text, suggested_fix)`
- **source_chapter 永远为 0**：R2 产出的场景 `source_chapter=0`，导致 HAR 的章节查找全部失败
- **自校正最多 2 轮**但实际通常 1 轮就退出了

关键 bug 位置 [har_service.py:161](backend/app/services/har_service.py)：
```python
chapter = chapter_map.get(scene.source_chapter)  # ← source_chapter 总是 0
if chapter is None:
    continue  # ← 跳过所有 R2 生成的场景！
```

### 4.2 CPC 贪婪循环破除算法实现有误  **[中等]**

论文中的 CPC 使用了"类 Prim 的贪婪算法"构建 DAG。当前实现的 Kahn 拓扑排序 + 贪婪边移除是标准做法，但有 bug：

在 [cpc_service.py:182-183](backend/app/services/cpc_service.py) 的 Kahn 算法中，`kept_edges` 在遍历邻接表时添加边，但没有考虑入度 > 1 的节点——可能导致边被错误保留。

### 4.3 缺少评估框架  **[中等]**

论文使用了 7 个维度（Interesting, Coherent, Human-like, Diction & Grammar, Transition, Script Format Compliance, Consistency）的 GPT-4o 评判 + 人工评估。当前项目没有任何自动化质量评估。

比赛评审可能会问：**你怎么证明生成的剧本质量好？**

---

## 5. 前端与异步差距

### 5.1 前端类型严重落后后端  **[严重]**

[前端 types](frontend/src/types/index.ts) 只有 39 行，缺少大量后端已实现的模型：

| 后端已有 | 前端缺失 |
|----------|----------|
| CausalGraph / Event / CausalRelation | ❌ 全部缺失 |
| R2ScanResult / R2ScanRequest | ❌ 全部缺失 |
| HARReport / HARFinding / HARRefineRequest | ❌ 全部缺失 |
| PipelineRunResult / PipelineStep / PipelineRunRequest | ❌ 全部缺失 |
| Scene 的 location / time_of_day / source_chapter / characters | ❌ 全部缺失 |
| Screenplay 的 source_novel / novel_author / total_chapters / generated_by | ❌ 全部缺失 |

API 合约文档明确标注"B 需要同步更新"，但前端未行动。

### 5.2 前端 API 客户端覆盖不全  **[严重]**

[api.ts](frontend/src/lib/api.ts) 只有 56 行，仅封装了：
- `uploadNovel` / `getNovel`
- `generateScreenplay` / `getScreenplay`
- `exportUrl`

缺失 CPC/R2/HAR/Pipeline 全部前端调用。**后端 13 个端点全部可用，前端只能用到 5 个。**

### 5.3 UI 功能极度简陋  **[中等]**

当前前端只有两个页面：
- 首页：上传小说
- 剧本页：生成剧本 + 预览

README 承诺但未实现的功能：
- CPC DAG 可视化
- R2 改写预览与对比
- HAR 校正审核界面
- 一键流水线按钮 + 步骤进度
- YAML 导出按钮

### 5.4 前端直接硬编码后端地址  **[低]**

[page.tsx:25](frontend/src/app/page.tsx) 的 `handleUpload` 直接写死了 `http://localhost:8000`，而 `api.ts` 使用 `NEXT_PUBLIC_API_URL` 环境变量。同一项目里两种做法并存。

---

## 6. 流水线设计缺陷

### 6.1 数据流断裂  **[严重]**

流水线的设计意图是 CPC → R2 → HAR → ScreenYAML，但实际数据流是：

```
CPC  → 写入 cpc_graphs（但 R2 不读取）
R2   → 写入 r2_scenes（但 HAR 不读取）
HAR  → 读取 screenplay.scenes（来自 screenplay_service，非 R2！）
      → 写入 har_reports（但 ScreenYAML 不读取）
ScreenYAML → 读取 screenplay.scenes（来自 screenplay_service）
```

**R2 的产出完全没有被后续步骤使用。** HAR 和 ScreenYAML 消费的是 `screenplay_service.generate_screenplay()` 的产物，与 R2 并行存在但数据不相通。

### 6.2 幂等性实现不一致  **[中等]**

三个服务的幂等检查模式相同但分散在不同文件，没有统一的幂等 decorator 或 mixin：

```python
# 每个 service 都重复这段
async with async_session() as session:
    existing = await _db_get_xxx(session, novel.id)
    if existing is not None:
        return existing
```

### 6.3 缺少超时与重试  **[中等]**

LLM 调用（`_call_llm`）没有重试机制。在生产环境中，API 偶尔会超时或返回 5xx，没有重试意味着整个流水线步骤失败。

---

## 7. 竞争力分析（与同类产品对比）

### 7.1 竞品矩阵

| 维度 | 本项目 | Noval | InfinityCN | Toonflow | Novel-to-Script | R² 论文 |
|------|--------|-------|------------|----------|-----------------|---------|
| **剧本生成** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **因果图** | ✅ CPC | ❌ | ❌ | ✅ 事件图 | ❌ | ✅ CPC |
| **滑动窗口** | ✅ R2 | ❌ | ❌ | ❌ | ❌ | ✅ R2 |
| **幻觉检测** | ⚠️ 半成品 | ❌ | ❌ | ❌ | ❌ | ✅ HAR |
| **RAG 检索** | ❌ 未实现 | ❌ | ❌ | ❌ | ❌ | ✅ |
| **结构化输出** | ✅ YAML | ✅ | ❌ | ❌ | ❌ | ✅ |
| **DAG 可视化** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **离线可用** | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **多格式导出** | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| **情绪分析** | ❌ | ❌ | ✅ | ✅ | ✅ BERT | ❌ |
| **多模型支持** | ❌ 仅DeepSeek | ✅ | ✅ 7种 | ✅ | ❌ 仅DeepSeek | — |
| **评估框架** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ 7维评估 |
| **视频生成** | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |

### 7.2 本项目独特优势

与同类产品相比，本项目有明确的学术理论支撑（R² 论文）和完整的 CPC/R2/HAR 架构设计——这是竞品不具备的差异化优势。但目前实现完整度不到论文的 50%。

### 7.3 最大风险

**比赛评审如果搜索到 R² 论文，而项目未声明引用，会被判定为学术不端。** 正确的做法是：
- 明确声明基于论文实现
- 说明工程化改进（论文没有的：ScreenYAML、前端 UI、流水线编排）
- 展示"站在巨人肩膀上"的增量贡献

---

## 8. 改进建议（优先级排序）

### P0 — 赛前必须修复

| # | 问题 | 建议 |
|---|------|------|
| 1 | README 未声明论文来源 | 在 README 和 CLAUDE.md 中引用 R² 论文，说明工程实现与改进点 |
| 2 | HAR 缺少 RAG 实现 | 接入 ChromaDB/Qdrant，实现真正的向量检索→幻觉检测闭环 |
| 3 | 数据流断裂 | 让 R2 产出直接写入 screenplay 表，或统一场景数据模型 |
| 4 | R2/Screenplay 表重复 | 合并场景表，消除数据孤岛 |

### P1 — 评审前应完成

| # | 问题 | 建议 |
|---|------|------|
| 5 | 前端类型同步 | 补全 TypeScript 类型，与 API 合约对齐 |
| 6 | 前端功能补全 | 至少实现流水线一键按钮 + DAG 可视化 + HAR 审核界面 |
| 7 | 添加评估框架 | 实现论文的 7 维度 GPT-4o 自动评判 |
| 8 | LLM 调用加重试 | 指数退避重试（3次），避免临时网络波动导致流水线失败 |

### P2 — 时间允许时改进

| # | 问题 | 建议 |
|---|------|------|
| 9 | 数据库迁移 | 接入 Alembic，替代 `create_all` |
| 10 | 依赖注入 | 使用 FastAPI `Depends()` 统一会话管理 |
| 11 | 多模型支持 | 支持 OpenAI/Claude 兼容接口，不锁定单一厂商 |
| 12 | 离线 fallback | 参考 InfinityCN 的做法，无 API key 时降级为纯算法模式 |

### P3 — 长期优化

| # | 问题 | 建议 |
|---|------|------|
| 13 | SQLite → PostgreSQL | 生产部署时切换数据库 |
| 14 | 情绪/张力分析 | 接入情感分析模型，参考 InfinityCN 的 tension scoring |
| 15 | 视频生成 | 探索接入视频模型，形成端到端小说→视频 pipeline |

---

## 附录 A：调研来源

| 来源 | 链接 |
|------|------|
| R² 论文 | https://arxiv.org/abs/2503.15655 |
| Noval (Open Script Studio) | https://github.com/MossHK/noval |
| InfinityCN | https://github.com/Pushyanth02/InfinityCN |
| Toonflow | https://github.com/HBAI-Ltd/Toonflow-app |
| Novel-to-Script | https://github.com/ZhengDongHang/Novel-to-Script |
| Openframe | https://github.com/murongg/openframe |
| Jellyfish | https://github.com/Forget-C/Jellyfish |
| Seedance2-Storyboard-Generator | https://github.com/liangdabiao/Seedance2-Storyboard-Generator |
