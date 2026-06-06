# 架构设计

## 当前最小闭环

当前 `main` 分支为项目起步骨架，保证主分支从第一天起可运行。后续每个 PR 在此基础上替换或增强单一模块。

```text
Browser (Next.js SPA)
  └─ 基础页面框架（待搭建）
        │
        ▼
FastAPI REST API
  └─ Health check 端点（待搭建）
```

## 目标架构

```text
Browser (Next.js SPA)
  ├─ 小说上传与章节管理界面
  ├─ CPC 因果图 DAG 可视化
  ├─ R2 改写预览与对比
  ├─ HAR 校正结果审核
  └─ ScreenYAML 剧本预览与导出
        │
        ▼
FastAPI REST API
  ├─ POST /api/novels/upload       小说上传与章节解析
  ├─ GET  /api/novels/{id}          获取小说详情
  ├─ POST /api/cpc/build            CPC 因果图构建
  ├─ GET  /api/cpc/{id}/graph       获取 DAG 图数据
  ├─ POST /api/r2/scan              R2 滑动窗口扫描
  ├─ GET  /api/r2/{id}/result       获取改写结果
  ├─ POST /api/har/refine           HAR 自校正
  ├─ GET  /api/har/{id}/report      获取校正报告
  ├─ POST /api/screenplay/generate  ScreenYAML 生成
  ├─ GET  /api/screenplay/{id}      获取剧本
  └─ GET  /api/export/{id}          导出剧本文件
        │
        ▼
AI Orchestrator（算法核心层）
  ├─ CPC：事件抽取 → 关系识别 → 贪婪循环破除 → DAG 构建
  ├─ R2：滑动窗口分块 → 上下文拼接 → 逐块改写 → 结果合并
  ├─ HAR：RAG 检索 → 幻觉检测 → 修正建议 → 再验证
  └─ ScreenYAML：内容映射 → Schema 校验 → UUID 验证 → 结构化输出
        │
        ▼
Data Layer
  ├─ 向量数据库（ChromaDB / Qdrant）：HAR 检索索引
  ├─ 关系数据库：小说、章节、剧本元数据
  └─ 文件存储：上传文件、导出文件
```

## 模块拆分

- **frontend**：Next.js + TypeScript + TailwindCSS。小说上传、章节管理、DAG 可视化、改写预览、剧本导出界面。
- **backend**：FastAPI + Python 3.11+。API 路由、CPC/R2/HAR 算法编排、ScreenYAML 生成与校验、文件管理。
- **docs**：架构设计、开发计划、Demo 视频脚本、提交检查清单。

## 核心数据流

### 小说→剧本 完整流程

```text
用户上传小说 (TXT/EPUB)
      │
      ▼
章节解析 ────── 识别章节边界，拆分文本块
      │
      ▼
CPC 因果图构建 ────── 事件抽取 → 关系识别 → 循环破除 → DAG
      │
      ▼
R2 滑动窗口扫描 ────── 按窗口逐块改写为剧本片段
      │
      ▼
HAR 幻觉自校正 ────── RAG 检索事实 → 检测幻觉 → 修正
      │
      ▼
ScreenYAML 生成 ────── 内容映射 → Schema 校验 → 结构化输出
      │
      ▼
剧本导出 (Word/PDF)
```

## 后续真实能力接入顺序

1. FastAPI 后端骨架 + Next.js 前端骨架（替换当前 mock）。
2. 小说上传与章节解析 API + 前端上传界面。
3. CPC 因果情节图构建算法 + DAG 可视化。
4. R2 滑动窗口扫描与改写引擎 + 前端改写预览。
5. HAR 幻觉自校正循环 + 前端校正审核。
6. ScreenYAML 生成与校验 + 剧本预览与导出。

每一步应单独建 PR，避免大功能一次性合并。
