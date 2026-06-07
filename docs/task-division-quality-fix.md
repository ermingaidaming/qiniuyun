# 质量修复四合一 — 分工方案

> 目标：HAR 接入 RAG、CPC 指导 R2 调度、R2 字段补全、LLM 加重试
>
> 原则：两条分支零文件冲突、可并行开发、独立验证
>
> 阅读对象：开发者 A (uYu) 和开发者 B (rayi)

---

## 背景：四个待修复问题

```
① HAR 无 RAG（最严重）：当前用 context stuffing（截取整章前 16000 字）
   → 向量检索 → 精准定位相关原文 → 幻觉检测准确率大幅提升

② CPC 因果图未指导 R2：论文核心创新落地缺失
   → R2 按章节事件密度动态分配窗口数

④ R2 场景字段丢弃：LLM 返回的 location/time_of_day/characters 未映射
   → YAML 输出中这些字段永远为空

⑤ LLM 调用无重试：DeepSeek API 偶发 5xx → 整个步骤失败
   → 指数退避重试 3 次
```

---

## 分工总览

| 开发者 | 分支 | 修改文件 | 修复 | 依赖 |
|--------|------|----------|------|------|
| **B (rayi)** | `feat/retry-fields` | `llm_service.py` + `r2_service.py` | ④⑤ | 无 |
| **A (uYu)** | `feat/har-rag` | `rag_service.py`(新) + `har_service.py` + `r2_service.py` + `pipeline_service.py` | ①② | B 先合 |

**唯一重叠文件 `r2_service.py`**：B 改字段映射（Scene 创建处），A 改窗口构建（`_build_windows` + `scan_novel` 签名）——改动在文件不同区域，B 先合后 A rebase 即可。

---

# B 的任务：LLM 重试 + R2 字段映射（修复④⑤）

## B 的操作步骤

### 步骤 1：同步并切分支

```bash
cd /e/code/QiniuYun/qiniuyun

git config user.name    # rayi
git config user.email   # 2447845922@qq.com

git fetch origin
git switch feat/screenyaml-mvp
git pull origin feat/screenyaml-mvp

# 切出修复分支
git switch -c feat/retry-fields
```

### 步骤 2：安装新增依赖

```bash
cd backend

# tenacity 用于 LLM 重试
poetry add tenacity

# 确认安装成功
poetry run python -c "import tenacity; print(tenacity.__version__)"
```

### 步骤 3：改代码

**修改两个文件**：`backend/app/services/llm_service.py` + `backend/app/services/r2_service.py`

---

#### 改动 A：`llm_service.py` — 加重试装饰器

**位置**：文件顶部 import 区 + `_call_llm` 函数签名前

**改前**（第 1-8 行附近 + 第 57 行）：
```python
from __future__ import annotations

import json
import re
from typing import Any, cast

from httpx import AsyncClient

from app.core.config import settings


async def _call_llm(system_prompt: str, user_prompt: str, *, temperature: float = 0.7, max_tokens: int = 4096) -> str:
    """Generic LLM call. Returns the content of the first choice."""
```

**改后**：
```python
from __future__ import annotations

import json
import re
from typing import Any, cast

from httpx import AsyncClient, HTTPStatusError, TransportError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings


@retry(
    retry=retry_if_exception_type((HTTPStatusError, TransportError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
async def _call_llm(system_prompt: str, user_prompt: str, *, temperature: float = 0.7, max_tokens: int = 4096) -> str:
    """Generic LLM call with exponential backoff retry (3 attempts).

    Retries on network errors and 5xx responses only.
    Client errors (4xx) are NOT retried — they indicate a problem with the request itself.
    """
```

**注意**：httpx 的 `AsyncClient` 不会对 5xx 自动抛异常——需要在函数内部手动 raise。所以还需要改函数体内的错误处理：

**位置**：函数体内 `response.status_code != 200` 那行（约第 77 行）

**改前**：
```python
    if response.status_code != 200:
        raise RuntimeError(f"LLM API error: {response.status_code} {response.text[:200]}")
```

**改后**：
```python
    if response.status_code >= 500:
        raise HTTPStatusError(
            f"LLM server error: {response.status_code}",
            request=response.request,
            response=response,
        )
    if response.status_code != 200:
        raise RuntimeError(f"LLM API error: {response.status_code} {response.text[:200]}")
```

---

#### 改动 B：`r2_service.py` — 补全 Scene 字段映射

**位置**：约第 89-97 行，`Scene(...)` 创建处

**改前**：
```python
                all_scenes.append(
                    (
                        win["index"],
                        Scene(
                            index=scene_counter,
                            setting=raw_scene.get("setting", f"窗口 {win['index'] + 1}"),
                            elements=elements,
                        ),
                    )
                )
```

**改后**：
```python
                all_scenes.append(
                    (
                        win["index"],
                        Scene(
                            index=scene_counter,
                            setting=raw_scene.get("setting", f"窗口 {win['index'] + 1}"),
                            location=raw_scene.get("location", ""),
                            time_of_day=raw_scene.get("time_of_day", ""),
                            characters=raw_scene.get("characters", []),
                            elements=elements,
                        ),
                    )
                )
```

**注意**：placeholder 场景（处理失败分支，约第 102-109 行）不需要改，保持原样即可。

---

### 步骤 4：验证

```bash
cd backend

# 代码格式
poetry run ruff check app/services/llm_service.py app/services/r2_service.py

# 类型检查
poetry run mypy app/services/llm_service.py app/services/r2_service.py

# R2 模块测试
poetry run pytest tests/test_r2.py -v
# 预期: 7 passed

# 全量测试
poetry run pytest -v
# 预期: 41 passed
```

### 步骤 5：提交并推送

```bash
cd /e/code/QiniuYun/qiniuyun

git diff
git add backend/app/services/llm_service.py backend/app/services/r2_service.py backend/pyproject.toml backend/poetry.lock
git commit -m "fix: LLM 调用加重试（指数退避 3 次）+ R2 场景补全字段映射"

git push -u origin feat/retry-fields
```

### 步骤 6：创建 PR

在 GitHub 上创建 Pull Request：

| 字段 | 值 |
|------|-----|
| **Base 分支** | `feat/screenyaml-mvp` |
| **Head 分支** | `feat/retry-fields` |
| **标题** | `fix: LLM 加重试 + R2 场景字段补全` |
| **Reviewer** | uYu |

---

# A 的任务：HAR RAG + CPC 指导 R2 调度（修复①②）

## A 的操作步骤

### 步骤 1：等 B 的 PR 合并

在 GitHub 上 review B 的 PR `feat/retry-fields` → `feat/screenyaml-mvp`，确认无误后合并。

### 步骤 2：同步并切分支

```bash
cd /e/code/QiniuYun/qiniuyun

git config user.name    # uYu
git config user.email   # 702669879@qq.com

git fetch origin
git switch feat/screenyaml-mvp
git pull origin feat/screenyaml-mvp   # 拉取 B 刚合并的改动

git switch -c feat/har-rag
```

### 步骤 3：安装新增依赖

```bash
cd backend

poetry add scikit-learn

# 确认
poetry run python -c "from sklearn.feature_extraction.text import TfidfVectorizer; print('ok')"
```

### 步骤 4：改代码（4 个文件）

---

#### 文件 A：新建 `backend/app/services/rag_service.py`

```python
"""Lightweight RAG service — TF-IDF based chapter chunking and retrieval.

Uses sklearn TfidfVectorizer + cosine similarity for zero-external-dependency
vector search.  Alternative to ChromaDB/Qdrant — works in any Python environment.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ── Chunking ───────────────────────────────────────────────────────────


def chunk_novel(chapters: list[Any], chunk_size: int = 800, overlap: int = 200) -> list[dict[str, Any]]:
    """Split novel chapters into overlapping text chunks with metadata.

    Returns a list of dicts with keys: text, chapter_index, chapter_title.
    """
    chunks: list[dict[str, Any]] = []
    for ch in chapters:
        content = ch.content
        if not content.strip():
            continue
        start = 0
        while start < len(content):
            end = min(start + chunk_size, len(content))
            chunk_text = content[start:end]
            if len(chunk_text.strip()) >= 50:  # skip tiny trailing fragments
                chunks.append({
                    "text": chunk_text,
                    "chapter_index": ch.index,
                    "chapter_title": ch.title,
                })
            if end >= len(content):
                break
            start += chunk_size - overlap
    return chunks


# ── Retrieval ──────────────────────────────────────────────────────────


def build_index(chunks: list[dict[str, Any]]) -> tuple[TfidfVectorizer, np.ndarray]:
    """Build TF-IDF index from text chunks.

    Returns (vectorizer, matrix) where matrix shape is (n_chunks, n_features).
    """
    vectorizer = TfidfVectorizer(
        max_features=5000,
        ngram_range=(1, 2),
        analyzer="char_wb",
    )
    texts = [c["text"] for c in chunks]
    matrix = vectorizer.fit_transform(texts)
    return vectorizer, matrix


def retrieve(
    query: str,
    chunks: list[dict[str, Any]],
    vectorizer: TfidfVectorizer,
    matrix: np.ndarray,
    top_k: int = 3,
) -> list[dict[str, Any]]:
    """Retrieve top-k most relevant chunks for a query.

    Args:
        query: The scene text to find relevant source material for.
        chunks: Chunk list from chunk_novel().
        vectorizer: Fitted TfidfVectorizer from build_index().
        matrix: TF-IDF matrix from build_index().
        top_k: Number of chunks to return.

    Returns:
        List of top-k chunks, each with text, chapter_index, chapter_title, and score.
    """
    if matrix.shape[0] == 0:
        return []

    query_vec = vectorizer.transform([query])
    similarities = cosine_similarity(query_vec, matrix).flatten()

    top_indices = np.argsort(similarities)[::-1][:top_k]

    results: list[dict[str, Any]] = []
    for idx in top_indices:
        if similarities[idx] <= 0.0:
            continue
        results.append({
            **chunks[idx],
            "score": float(similarities[idx]),
        })
    return results
```

#### 文件 B：修改 `backend/app/services/har_service.py`

**① 加导入**（文件顶部）：

```python
from app.services.rag_service import build_index, chunk_novel, retrieve
```

**② 修改 `refine()` 函数**：

**位置**：约第 115 行，`chapter_map` 那一行之后

**改前**（B 的 fix 后的版本）：
```python
    all_findings: list[HARFinding] = []
    corrected_scenes = deepcopy(scenes)

    for round_num in range(1, MAX_VERIFICATION_ROUNDS + 1):
        round_findings = await _detect_hallucinations(corrected_scenes, novel, round_num)
```

**改后**：
```python
    # Build RAG index once for all rounds
    all_chunks = chunk_novel(novel.chapters)
    vectorizer, chunk_matrix = build_index(all_chunks)

    all_findings: list[HARFinding] = []
    corrected_scenes = deepcopy(scenes)

    for round_num in range(1, MAX_VERIFICATION_ROUNDS + 1):
        round_findings = await _detect_hallucinations(
            corrected_scenes, novel, round_num, all_chunks, vectorizer, chunk_matrix
        )
```

**③ 修改 `_detect_hallucinations()` 函数签名和正文**：

**位置**：约第 159-196 行

**改前**（B 的 fix 后的版本，约完整函数）：
```python
async def _detect_hallucinations(
    scenes: list[Scene],
    novel: Novel,
    round_num: int,
) -> list[HARFinding]:
    """Detect hallucinations by comparing each scene against source text.

    When source_chapter > 0, use the specific chapter as context.
    When source_chapter == 0 (e.g. R2-generated scenes), fall back to full novel text.
    """
    findings: list[HARFinding] = []

    chapter_map: dict[int, Any] = {ch.index: ch for ch in novel.chapters}
    full_text = "\n\n".join(ch.content for ch in novel.chapters)

    for scene in scenes:
        # Find source text by chapter; fall back to full text
        chapter = chapter_map.get(scene.source_chapter) if scene.source_chapter > 0 else None
        if chapter is not None:
            source_text = chapter.content[: settings.max_chapter_length_chars]
            chapter_index = chapter.index
            chapter_title = chapter.title
        else:
            source_text = full_text[: settings.max_chapter_length_chars * 2]
            chapter_index = 0
            chapter_title = "全文"

        # Build scene text for LLM
        elements_text = "\n".join(
            f"[{e.type}] {e.character + ': ' if e.character else ''}{e.content}" for e in scene.elements
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
            # ... 后续解析和 findings.append 逻辑不变 ...
```

**改后**（完整函数）：
```python
async def _detect_hallucinations(
    scenes: list[Scene],
    novel: Novel,
    round_num: int,
    chunks: list[dict[str, Any]],
    vectorizer: Any,
    chunk_matrix: Any,
) -> list[HARFinding]:
    """Detect hallucinations by comparing each scene against RAG-retrieved source text.

    Uses TF-IDF retrieval to find the most relevant novel passages for each scene,
    then passes them as context to the LLM for hallucination detection.
    Falls back to chapter lookup if RAG returns no results.
    """
    findings: list[HARFinding] = []

    chapter_map: dict[int, Any] = {ch.index: ch for ch in novel.chapters}
    full_text = "\n\n".join(ch.content for ch in novel.chapters)

    for scene in scenes:
        # Build scene text for retrieval query
        elements_text = "\n".join(
            f"[{e.type}] {e.character + ': ' if e.character else ''}{e.content}"
            for e in scene.elements
        )
        query = f"{scene.setting} {scene.location} {elements_text}"

        # RAG retrieval
        retrieved = retrieve(query, chunks, vectorizer, chunk_matrix, top_k=3)

        if retrieved:
            # Use RAG-retrieved chunks as context
            rag_context = "\n\n---\n\n".join(
                f"[第{r['chapter_index']}章 {r['chapter_title']}] (相关度: {r['score']:.2f})\n{r['text'][:settings.max_chapter_length_chars // 2]}"
                for r in retrieved
            )
            source_text = rag_context
            chapter_index = 0
            chapter_title = "RAG 检索结果"
        else:
            # Fallback: chapter lookup or full text
            chapter = chapter_map.get(scene.source_chapter) if scene.source_chapter > 0 else None
            if chapter is not None:
                source_text = chapter.content[: settings.max_chapter_length_chars]
                chapter_index = chapter.index
                chapter_title = chapter.title
            else:
                source_text = full_text[: settings.max_chapter_length_chars * 2]
                chapter_index = 0
                chapter_title = "全文"

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
            parsed = _parse_har_response(raw)
            for f in parsed:
                findings.append(
                    HARFinding(
                        scene_index=int(f.get("scene_index", scene.index)),
                        severity=f.get("severity", "minor"),
                        category=f.get("category", "detail"),
                        description=str(f.get("description", "")),
                        hallucinated_text=str(f.get("hallucinated_text", "")),
                        suggested_fix=str(f.get("suggested_fix", "")),
                        source_evidence=str(f.get("source_evidence", "")),
                    )
                )
        except Exception:
            continue

    return findings
```

---

#### 文件 C：修改 `backend/app/services/r2_service.py`

**目标**：让 R2 的窗口构建感知 CPC 因果图中的事件密度，事件密集的章节获得更多窗口。

**① 加导入**（文件顶部，约第 9-13 行后）：

```python
from collections import Counter

from app.models.cpc import CausalGraph
```

**② 修改 `scan_novel()` 签名和调用**：

**位置**：约第 36 行，函数签名 + 约第 51 行 `_build_windows` 调用

**改前**：
```python
async def scan_novel(novel: Novel) -> R2ScanResult:
    """Run R2 sliding-window scan on a novel.
    ...
    """
    # Idempotent: return existing scan if already done
    async with async_session() as session:
        existing = await _db_get_scan(session, novel.id)
        if existing is not None:
            return existing

    # ── 1. Build sliding windows ───────────────────────────────────
    windows = _build_windows(
        novel.chapters,
        window_size=settings.r2_window_size,
        overlap=settings.r2_overlap_size,
    )
```

**改后**：
```python
async def scan_novel(novel: Novel, causal_graph: CausalGraph | None = None) -> R2ScanResult:
    """Run R2 sliding-window scan on a novel.

    If a causal_graph is provided, window density is adjusted per chapter
    based on event count — chapters with more events get finer-grained windows.
    ...
    """
    # Idempotent: return existing scan if already done
    async with async_session() as session:
        existing = await _db_get_scan(session, novel.id)
        if existing is not None:
            return existing

    # ── 1. Build event density map from causal graph ─────────────────
    chapter_event_counts: dict[int, int] = {}
    if causal_graph is not None and causal_graph.events:
        chapter_event_counts = dict(Counter(e.chapter_index for e in causal_graph.events))

    # ── 2. Build sliding windows ───────────────────────────────────
    windows = _build_windows(
        novel.chapters,
        window_size=settings.r2_window_size,
        overlap=settings.r2_overlap_size,
        chapter_event_counts=chapter_event_counts,
    )
```

**③ 修改 `_build_windows()`**：

**位置**：约第 142 行

**改前**：
```python
def _build_windows(
    chapters: list[Any],
    window_size: int,
    overlap: int,
) -> list[dict[str, Any]]:
    """Build overlapping sliding windows from chapter texts.

    Returns a list of dicts with keys: index, text.
    """
    # Concatenate all chapter texts with separators
    parts: list[str] = []
    for ch in chapters:
        parts.append(ch.content)
    full_text = "\n\n".join(parts).strip()

    if not full_text:
        return []

    # Short text: use a single window
    if len(full_text) <= window_size:
        return [{"index": 0, "text": full_text}]

    step = max(window_size - overlap, 1)  # ensure positive step
    windows: list[dict[str, Any]] = []
    pos = 0
    win_idx = 0

    while pos < len(full_text):
        window_text = full_text[pos : pos + window_size]
        # Skip tiny trailing windows
        if len(window_text.strip()) < 100:
            break
        windows.append({"index": win_idx, "text": window_text})
        win_idx += 1
        pos += step

    return windows
```

**改后**：
```python
def _build_windows(
    chapters: list[Any],
    window_size: int,
    overlap: int,
    chapter_event_counts: dict[int, int] | None = None,
) -> list[dict[str, Any]]:
    """Build sliding windows with event-density-aware step sizing.

    Chapters with more CPC events get denser window coverage (smaller step),
    while low-event chapters get sparser coverage (larger step).

    Each window also tracks which chapter it overlaps with most, so the
    caller can set source_chapter accurately.
    """
    if not chapters:
        return []

    # Per-chapter windowing: each chapter gets its own windows
    windows: list[dict[str, Any]] = []
    win_idx = 0

    for ch in chapters:
        text = ch.content.strip()
        if not text:
            continue

        # Determine step size based on event density
        event_count = (chapter_event_counts or {}).get(ch.index, 0)

        if event_count >= 5:
            step = max(window_size - overlap * 2, window_size // 2)
        elif event_count >= 2:
            step = max(window_size - overlap, window_size // 2)
        elif len(text) <= window_size:
            step = window_size  # single window for short/low-event chapters
        else:
            step = max(window_size - overlap // 2, window_size // 4 * 3)

        pos = 0
        while pos < len(text):
            window_text = text[pos : pos + window_size]
            if len(window_text.strip()) < 50:
                break
            windows.append({
                "index": win_idx,
                "text": window_text,
                "chapter_index": ch.index,
                "chapter_title": ch.title,
            })
            win_idx += 1
            pos += step

    return windows
```

**④ 修改窗口处理处的 `source_chapter`**：

现在每个 window 带有 `chapter_index`，创建 Scene 时可以正确设置。修改约第 89-97 行 Scene 创建处：

**改前**（B 的 fix 后的版本）：
```python
                all_scenes.append(
                    (
                        win["index"],
                        Scene(
                            index=scene_counter,
                            setting=raw_scene.get("setting", f"窗口 {win['index'] + 1}"),
                            location=raw_scene.get("location", ""),
                            time_of_day=raw_scene.get("time_of_day", ""),
                            characters=raw_scene.get("characters", []),
                            elements=elements,
                        ),
                    )
                )
```

**改后**：
```python
                all_scenes.append(
                    (
                        win["index"],
                        Scene(
                            index=scene_counter,
                            setting=raw_scene.get("setting", f"窗口 {win['index'] + 1}"),
                            location=raw_scene.get("location", ""),
                            time_of_day=raw_scene.get("time_of_day", ""),
                            source_chapter=win.get("chapter_index", 0),
                            characters=raw_scene.get("characters", []),
                            elements=elements,
                        ),
                    )
                )
```

---

#### 文件 D：修改 `backend/app/services/pipeline_service.py`

**目标**：把 CPC 产出的 CausalGraph 传给 R2。

**位置**：Step 2（R2），约第 48-66 行

**改前**：
```python
    # ── Step 2: R2 ───────────────────────────────────────────────────
    try:
        scan_result = await r2_service.scan_novel(novel)
```

**改后**：
```python
    # ── Step 2: R2 ───────────────────────────────────────────────────
    try:
        scan_result = await r2_service.scan_novel(novel, causal_graph=causal_graph)
```

需要从 Step 1 的 CPC 调用中获取 causal_graph：

**位置**：Step 1（CPC），约第 40-46 行

**改前**：
```python
    # ── Step 1: CPC ──────────────────────────────────────────────────
    try:
        await cpc_service.build_causal_graph(novel)
        steps.append(PipelineStep(name="cpc", status=StepStatus.completed))
```

**改后**：
```python
    # ── Step 1: CPC ──────────────────────────────────────────────────
    try:
        causal_graph = await cpc_service.build_causal_graph(novel)
        steps.append(PipelineStep(name="cpc", status=StepStatus.completed))
```

---

### 步骤 5：验证

```bash
cd backend

# 格式 + 类型（所有修改的文件）
poetry run ruff check app/services/rag_service.py app/services/har_service.py app/services/r2_service.py app/services/pipeline_service.py
poetry run mypy app/services/rag_service.py app/services/har_service.py app/services/r2_service.py app/services/pipeline_service.py

# RAG 模块独立测试
poetry run python -c "
from app.services.rag_service import chunk_novel, build_index, retrieve
print('RAG module OK')
"

# 核心测试
poetry run pytest tests/test_har.py tests/test_r2.py tests/test_pipeline.py -v
# 预期: 7 (R2) + 7 (HAR) + 6 (Pipeline) = 20 passed

# 全量测试
poetry run pytest -v
# 预期: 41+ passed
```

### 步骤 6：提交并推送

```bash
cd /e/code/QiniuYun/qiniuyun

git diff
git add backend/app/services/rag_service.py \
        backend/app/services/har_service.py \
        backend/app/services/r2_service.py \
        backend/app/services/pipeline_service.py \
        backend/pyproject.toml \
        backend/poetry.lock

git commit -m "feat: HAR 接入 TF-IDF RAG + CPC 事件密度指导 R2 窗口调度

- 新增 rag_service.py：TF-IDF 向量化 + 余弦相似度检索
- HAR _detect_hallucinations 优先使用 RAG 检索结果作为上下文
- R2 _build_windows 按章节事件密度动态调整窗口步长
- pipeline_service 将 CPC CausalGraph 传入 R2
- R2 Scene 正确设置 source_chapter（按窗口所属章节）"

git push -u origin feat/har-rag
```

### 步骤 7：创建 PR

| 字段 | 值 |
|------|-----|
| **Base 分支** | `feat/screenyaml-mvp` |
| **Head 分支** | `feat/har-rag` |
| **标题** | `feat: HAR RAG 检索 + CPC 指导 R2 窗口调度` |
| **Reviewer** | rayi |

---

## 执行顺序

```
现在 ──────────────────────────────────────────────→ 完成

B: git switch feat/retry-fields
   ├── poetry add tenacity
   ├── 改 llm_service.py（重试装饰器 + 5xx 检测）
   ├── 改 r2_service.py（Scene 字段补全）
   ├── poetry run pytest -v  # 41 passed
   ├── git commit + push
   └── GitHub PR → base: feat/screenyaml-mvp

A: GitHub 上 review B 的 PR → 确认 → 合并
   （B 的改动进入 feat/screenyaml-mvp）

A: git pull origin feat/screenyaml-mvp
   git switch -c feat/har-rag
   ├── poetry add scikit-learn
   ├── 新建 rag_service.py（TF-IDF 检索）
   ├── 改 har_service.py（接入 RAG）
   ├── 改 r2_service.py（CPC 密度调度 + source_chapter）
   ├── 改 pipeline_service.py（CPC → R2 传入）
   ├── poetry run pytest -v  # 全部通过
   ├── git commit + push
   └── GitHub PR → base: feat/screenyaml-mvp

B: GitHub 上 review A 的 PR → 确认 → 合并

最终: feat/screenyaml-mvp 上四个质量修复全部落地
```

---

## 重叠文件处理

唯一重叠文件 `r2_service.py`：

| 区域 | feat/retry-fields (B) | feat/har-rag (A) |
|------|----------------------|------------------|
| 函数签名（scan_novel） | 不改 | ✅ 新增 causal_graph 参数 |
| Scene 创建处 | ✅ 补全字段 | ✅ 新增 source_chapter |
| _build_windows | 不改 | ✅ 按章节 + 密度调度 |
| 其他代码 | 不动 | 不动 |

B 改的是 Scene 实例化的属性列表（行 89-97），A 改的是函数签名 + `_build_windows` + Scene 的 `source_chapter`（三处不同位置）。B 先合后，A rebase 时只有 Scene 创建处会冲突——手动合并即可（两边的新字段都保留）。

---

## 常见问题

### Q: 为什么用 TF-IDF 而不是 ChromaDB？

ChromabDB 需要额外系统依赖（sqlite3 向量扩展或 onnxruntime），比赛评审环境可能不支持。sklearn 是纯 Python，`poetry add scikit-learn` 即装即用。

### Q: tenacity 和 scikit-learn 会增加多少依赖体积？

- tenacity: ~50KB，纯 Python
- scikit-learn: ~30MB（含 numpy/scipy），但都属于 Python 标准科学计算栈

如果担心依赖体积，后续可换用纯手写的 TF-IDF + 余弦相似度（~100 行代码），完全去 sklearn 依赖。

### Q: _build_windows 改成按章节分窗口，会影响 R2 的 mock 测试吗？

当前 `test_r2.py` 的 `test_build_windows` 测试传入的是模拟数据。按章节分窗口后，测试中的 `_build_windows` 调用需要更新（传入 chapters 而非拼接文本）。B 的 test 不改这块，A 需要同步更新。
