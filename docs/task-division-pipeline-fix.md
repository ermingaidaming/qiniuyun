# 流水线数据流修复 — 分工方案

> 目标：打通 CPC → R2 → HAR → ScreenYAML 端到端数据流
>
> 原则：两条分支互不冲突、可并行开发、独立验证
>
> 阅读对象：开发者 A (uYu) 和开发者 B (rayi)

---

## 背景：三个断裂点

```
CPC ✅ → R2 ✅ → HAR ❌ → ScreenYAML ❌
                  ↑              ↑
            断层②            断层①③

断层①：R2 产出写入了 r2_scenes 表，HAR 从 screenplays 表读取
       → HAR 找不到 R2 结果，被迫自己调 LLM 重新生成剧本

断层②：R2 场景的 source_chapter=0，HAR 按章节号查原文失败
       → 所有场景被 continue 跳过，HAR 实际没检测到任何幻觉

断层③：HAR 修正后的场景存入 har_reports（JSON 列），未写回 screenplays 表
       → ScreenYAML 导出的是原始未修正版本
```

---

## 分工总览

| 开发者 | 分支 | 修改文件 | 解决断层 | 依赖 |
|--------|------|----------|----------|------|
| **B (rayi)** | `feat/har-fallback` | `har_service.py` | ② | 无 |
| **A (uYu)** | `feat/pipeline-bridge` | `pipeline_service.py` + `screenplays.py` | ①③ | B 先合 |

**两个分支修改的文件零重叠，完全并行安全。**

---

## 仓库当前状态

```
main                        ← 已合并 PR #4 (R2) + PR #5 (HAR)
feat/screenyaml-mvp (本地)   ← A 的后端 MVP 分支，含流水线代码（尚未合并到 main）
feat/frontend-yaml (远端)    ← B 的前端分支
```

所有要改的代码都在 `feat/screenyaml-mvp` 上。两人都从这个分支切出。

---

# B 的任务：修复 HAR 章节查找（断层②）

## B 的操作步骤（完整 bash 命令，可逐条复制执行）

### 步骤 1：身份检查

```bash
# 确认当前 Git 身份是 B
git config user.name    # 应该输出: rayi
git config user.email   # 应该输出: 2447845922@qq.com

# 如果不是，先设置：
# git config user.name "rayi"
# git config user.email "2447845922@qq.com"
```

### 步骤 2：进入仓库，拉取最新代码

```bash
cd /e/code/QiniuYun/qiniuyun

# 拉取远端最新状态
git fetch origin

# 切换到 A 的最新后端分支
git switch feat/screenyaml-mvp

# 如果本地没有这个分支，从远端拉：
# git switch -c feat/screenyaml-mvp origin/feat/screenyaml-mvp
```

### 步骤 3：切出修复分支

```bash
git switch -c feat/har-fallback
# 现在你在 feat/har-fallback 分支上，代码和 feat/screenyaml-mvp 完全一样
```

### 步骤 4：安装后端环境

```bash
cd backend

# 安装 Python 依赖（首次需要，后续不用）
poetry install

# 确认环境正常——跑现有 HAR 测试
poetry run pytest tests/test_har.py -v
# 预期输出: 5 passed
```

### 步骤 5：改代码

**只改一个文件**：`backend/app/services/har_service.py`

---

#### 改动 A：修改 `_detect_hallucinations` 函数

**位置**：约第 152 行，函数签名处

**改前**：
```python
async def _detect_hallucinations(
    scenes: list[Scene],
    chapter_map: dict[int, Any],    # ← 删除这个参数
    round_num: int,
) -> list[HARFinding]:
    findings: list[HARFinding] = []

    for scene in scenes:
        chapter = chapter_map.get(scene.source_chapter)  # ← 0 → None
        if chapter is None:
            continue    # ← BUG：跳过所有 R2 场景！

        elements_text = "\n".join(
            f"[{e.type}] {e.character + ': ' if e.character else ''}{e.content}"
            for e in scene.elements
        )

        try:
            raw = await _call_llm(
                HAR_SYSTEM_PROMPT,
                HAR_USER_TEMPLATE.format(
                    chapter_index=chapter.index,
                    chapter_title=chapter.title,
                    source_text=chapter.content[: settings.max_chapter_length_chars],
                    scene_index=scene.index,
                    setting=scene.setting,
                    location=scene.location,
                    time=scene.time_of_day,
                    elements_text=elements_text,
                ),
                temperature=0.3,
            )
            # ... 后面解析逻辑不变 ...
```

**改后**：
```python
async def _detect_hallucinations(
    scenes: list[Scene],
    novel: Novel,    # ← 直接接收 novel（文件顶部已导入 Novel，不需要加 import）
    round_num: int,
) -> list[HARFinding]:
    findings: list[HARFinding] = []

    # 构建章节查找表 + 全文 fallback
    chapter_map: dict[int, Any] = {ch.index: ch for ch in novel.chapters}
    full_text = "\n\n".join(ch.content for ch in novel.chapters)

    for scene in scenes:
        # 按 source_chapter 查找对应原文；查不到则用全文
        chapter = chapter_map.get(scene.source_chapter) if scene.source_chapter > 0 else None
        if chapter is not None:
            source_text = chapter.content[: settings.max_chapter_length_chars]
            chapter_index = chapter.index
            chapter_title = chapter.title
        else:
            source_text = full_text[: settings.max_chapter_length_chars * 2]
            chapter_index = 0
            chapter_title = "全文"

        elements_text = "\n".join(
            f"[{e.type}] {e.character + ': ' if e.character else ''}{e.content}"
            for e in scene.elements
        )

        try:
            raw = await _call_llm(
                HAR_SYSTEM_PROMPT,
                HAR_USER_TEMPLATE.format(
                    chapter_index=chapter_index,
                    chapter_title=chapter_title,
                    source_text=source_text,
                    scene_index=scene.index,
                    setting=scene.setting,
                    location=scene.location,
                    time=scene.time_of_day,
                    elements_text=elements_text,
                ),
                temperature=0.3,
            )
            # ... 后面解析和 findings.append 逻辑完全不变 ...
```

**关键变化**：
- 参数从 `chapter_map: dict[int, Any]` 改为 `novel: Novel`
- 函数内部自己构建 `chapter_map` 和 `full_text`
- `source_chapter=0` 或找不到章节时用全文替代，不再 `continue` 跳过

---

#### 改动 B：修改 `refine()` 中调用 `_detect_hallucinations` 的地方

**位置**：约第 115-120 行

**改前**：
```python
    chapter_map = {ch.index: ch for ch in novel.chapters}  # ← 删掉这整行

    all_findings: list[HARFinding] = []
    corrected_scenes = deepcopy(scenes)

    for round_num in range(1, MAX_VERIFICATION_ROUNDS + 1):
        round_findings = await _detect_hallucinations(corrected_scenes, chapter_map, round_num)
```

**改后**：
```python
    all_findings: list[HARFinding] = []
    corrected_scenes = deepcopy(scenes)

    for round_num in range(1, MAX_VERIFICATION_ROUNDS + 1):
        round_findings = await _detect_hallucinations(corrected_scenes, novel, round_num)
```

**只改两行**：删掉 `chapter_map = ...` 那行，把调用里的 `chapter_map` 改成 `novel`。

---

### 步骤 6：验证

```bash
cd backend

# 1. 代码格式检查
poetry run ruff check app/services/har_service.py

# 2. 类型检查
poetry run mypy app/services/har_service.py

# 3. HAR 模块测试
poetry run pytest tests/test_har.py -v
# 预期: 5 passed

# 4. 全部测试
poetry run pytest -v
# 预期: 41 passed
```

如果任何一步失败，检查改动是否正确。常见问题：
- `mypy` 报类型错误 → 确认函数签名里的 `novel: Novel` 写对了
- 测试失败 → 确认 `refine()` 里的调用处也改了

### 步骤 7：提交并推送

```bash
# 回到仓库根目录
cd /e/code/QiniuYun/qiniuyun

# 查看改动
git diff

# 暂存
git add backend/app/services/har_service.py

# 提交
git commit -m "fix: HAR 场景原文查找支持全文 fallback，修复 source_chapter=0 时跳过所有场景的 bug"

# 推送
git push -u origin feat/har-fallback
```

### 步骤 8：创建 PR

在 GitHub/Gitee 上创建 Pull Request：

| 字段 | 值 |
|------|-----|
| **Base 分支** | `feat/screenyaml-mvp`（注意：不是 main！） |
| **Head 分支** | `feat/har-fallback` |
| **标题** | `fix: HAR 场景原文查找支持全文 fallback` |
| **Reviewer** | uYu |

**PR 描述模板**：

```markdown
## 功能描述

修复 HAR 幻觉检测中 `source_chapter=0` 导致所有场景被跳过的 bug。

## 实现思路

`_detect_hallucinations` 原来接收 `chapter_map` 参数，按 `scene.source_chapter` 查找对应章节原文。但 R2 产出的场景 `source_chapter=0`（未设置），导致 `chapter_map.get(0)` 返回 None，场景被 `continue` 跳过。

改为接收 `novel` 参数，函数内部构建 chapter_map 和全文 fallback：
- `source_chapter > 0` 且能找到章节 → 用该章节原文
- 否则 → 用拼接后的全小说文本

## 测试方式

- [x] HAR 模块测试（5 passed）
- [x] 全部后端测试（41 passed）

## 团队分配

本 PR 由开发者 B (rayi) 负责实现与自测。
```

---

# A 的任务：流水线数据桥接（断层①③）

## A 的操作步骤

### 步骤 1：等 B 的 PR 合并

在 GitHub 上 review B 的 PR `feat/har-fallback` → `feat/screenyaml-mvp`，确认无误后合并。

### 步骤 2：同步并切分支

```bash
cd /e/code/QiniuYun/qiniuyun

# 确认身份
git config user.name    # uYu
git config user.email   # 702669879@qq.com

# 同步
git fetch origin
git switch feat/screenyaml-mvp
git pull origin feat/screenyaml-mvp   # 拉取 B 刚合并的改动

# 切出 A 的修复分支
git switch -c feat/pipeline-bridge
```

### 步骤 3：改代码（2 个文件）

#### 文件 A：`backend/app/db/repository/screenplays.py`

在文件末尾（`_element_id` 函数之后）新增 `replace_screenplay` 函数：

```python
async def replace_screenplay(session: AsyncSession, screenplay: Screenplay) -> None:
    """Delete any existing screenplay for the novel, then insert the new one.

    Used by the pipeline to overwrite screenplay scenes after R2 generation
    and after HAR correction — ensures ScreenYAML always reads the latest version.
    """
    existing = await session.execute(
        select(ScreenplayTable).where(ScreenplayTable.novel_id == screenplay.novel_id)
    )
    row = existing.scalar_one_or_none()
    if row is not None:
        await session.delete(row)
        await session.flush()
    await save_screenplay(session, screenplay)
```

注意：`select` 已在文件顶部导入（`from sqlalchemy import select`），`ScreenplayTable` 也已导入 ——不需要新增 import。

---

#### 文件 B：`backend/app/services/pipeline_service.py`

需要改 3 处：

**① 加导入**（文件顶部）：

```python
from app.core.config import settings
from app.db.engine import async_session
from app.db.repository.screenplays import replace_screenplay as _replace_screenplay
from app.models.screenplay import Screenplay
```

**② Step 2（R2）后：保存 R2 场景为 Screenplay**

改前：
```python
    # ── Step 2: R2 ───────────────────────────────────────────────────
    try:
        await r2_service.scan_novel(novel)
        steps.append(PipelineStep(name="r2", status=StepStatus.completed))
    except Exception as exc:
        steps.append(PipelineStep(name="r2", status=StepStatus.failed, error=str(exc)))
        return _partial(novel_id, steps)
```

改后：
```python
    # ── Step 2: R2 ───────────────────────────────────────────────────
    try:
        scan_result = await r2_service.scan_novel(novel)
        steps.append(PipelineStep(name="r2", status=StepStatus.completed))

        # 将 R2 场景保存为 Screenplay，供 HAR 步骤使用
        screenplay = Screenplay(
            novel_id=novel.id,
            title=f"《{novel.title}》剧本",
            source_novel=novel.title,
            total_chapters=len(novel.chapters),
            generated_by=settings.llm_model if settings.llm_api_key else "r2",
            scenes=scan_result.scenes,
        )
        async with async_session() as session:
            await _replace_screenplay(session, screenplay)
    except Exception as exc:
        steps.append(PipelineStep(name="r2", status=StepStatus.failed, error=str(exc)))
        return _partial(novel_id, steps)
```

**③ Step 3（HAR）后：写回修正后的场景**

改前：
```python
    # ── Step 3: HAR ──────────────────────────────────────────────────
    try:
        await har_service.refine(novel)
        steps.append(PipelineStep(name="har", status=StepStatus.completed))
    except Exception as exc:
        steps.append(PipelineStep(name="har", status=StepStatus.failed, error=str(exc)))
        return _partial(novel_id, steps)
```

改后：
```python
    # ── Step 3: HAR ──────────────────────────────────────────────────
    try:
        har_report = await har_service.refine(novel)
        steps.append(PipelineStep(name="har", status=StepStatus.completed))

        # 将 HAR 修正后的场景写回 Screenplay
        screenplay.scenes = har_report.corrected_scenes
        async with async_session() as session:
            await _replace_screenplay(session, screenplay)
    except Exception as exc:
        steps.append(PipelineStep(name="har", status=StepStatus.failed, error=str(exc)))
        return _partial(novel_id, steps)
```

### 步骤 4：验证

```bash
cd backend

# 格式 + 类型
poetry run ruff check app/services/pipeline_service.py app/db/repository/screenplays.py
poetry run mypy app/services/pipeline_service.py app/db/repository/screenplays.py

# Pipeline 测试
poetry run pytest tests/test_pipeline.py -v
# 预期: 6 passed

# 全部测试
poetry run pytest -v
# 预期: 41+ passed
```

### 步骤 5：提交并推送

```bash
cd /e/code/QiniuYun/qiniuyun

git diff
git add backend/app/services/pipeline_service.py backend/app/db/repository/screenplays.py
git commit -m "fix: 修复流水线数据流——R2 产出写入 Screenplay，HAR 修正写回"
git push -u origin feat/pipeline-bridge
```

### 步骤 6：创建 PR

| 字段 | 值 |
|------|-----|
| **Base 分支** | `feat/screenyaml-mvp` |
| **Head 分支** | `feat/pipeline-bridge` |
| **标题** | `fix: 修复流水线数据流——R2→Screenplay→HAR→ScreenYAML` |
| **Reviewer** | rayi |

---

## 执行顺序

```
现在 ──────────────────────────────────────────→ 完成

B: git switch feat/screenyaml-mvp
   git switch -c feat/har-fallback
   ├── 改 har_service.py（2 处改动）
   ├── poetry run pytest -v  # 确认 41 passed
   ├── git commit + push
   └── GitHub 创建 PR → base: feat/screenyaml-mvp

A: GitHub 上 review B 的 PR → 确认 → 合并
   （两人都在 feat/screenyaml-mvp 这条线上改，
    合并后自动进入同一个分支）

A: git pull origin feat/screenyaml-mvp
   git switch -c feat/pipeline-bridge
   ├── 改 pipeline_service.py + screenplays.py
   ├── poetry run pytest -v  # 确认全部通过
   ├── git commit + push
   └── GitHub 创建 PR → base: feat/screenyaml-mvp

B: GitHub 上 review A 的 PR → 确认 → 合并

最终: feat/screenyaml-mvp 上流水线数据流完全打通
```

---

## 两个分支为什么不冲突

| 文件 | feat/har-fallback (B) | feat/pipeline-bridge (A) |
|------|----------------------|--------------------------|
| `app/services/har_service.py` | ✅ 修改 | ❌ 不动 |
| `app/services/pipeline_service.py` | ❌ 不动 | ✅ 修改 |
| `app/db/repository/screenplays.py` | ❌ 不动 | ✅ 修改 |

---

## 常见问题

### Q: 为什么 PR 目标是 `feat/screenyaml-mvp` 而不是 `main`？

因为流水线代码（pipeline_service.py 等）只在 `feat/screenyaml-mvp` 上，还没合并到 main。PR 到 `feat/screenyaml-mvp` 后，整条分支最终会一起合并到 main。

### Q: 如果测试失败了怎么办？

1. 读报错信息，确认是哪一步失败
2. 常见原因：改了函数签名但漏了调用点（B 要改两处，A 要改两处）
3. 如果解决不了，在 PR 里留 comment 说明情况

### Q: poetry install 报错？

检查 Python 版本 >= 3.11：
```bash
python --version
```
