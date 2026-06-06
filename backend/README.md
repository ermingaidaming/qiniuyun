# Backend — AI 小说转剧本工具

Python 3.11+ / FastAPI 后端服务，提供小说管理、CPC 因果图构建、R2 滑动窗口改写、HAR 幻觉自校正和 ScreenYAML 结构化剧本生成等 API。

## 技术栈

- **Web 框架**：FastAPI
- **依赖管理**：Poetry
- **数据校验**：Pydantic v2
- **测试**：pytest + pytest-asyncio
- **代码质量**：ruff (format + lint) + mypy
- **向量数据库**：ChromaDB / Qdrant（HAR 模块使用）

## 运行

```bash
# 安装依赖
poetry install

# 开发模式启动（http://localhost:8000）
poetry run uvicorn app.main:app --reload

# 生产启动
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

启动后访问 http://localhost:8000/docs 查看 Swagger API 文档。

## 测试

```bash
# 运行全部测试
poetry run pytest

# 运行指定模块测试
poetry run pytest tests/ -k "health"

# 覆盖率报告
poetry run pytest --cov=app --cov-report=term-missing
```

## 代码检查

```bash
# 格式化
poetry run ruff format app tests

# Lint
poetry run ruff check app tests

# 类型检查
poetry run mypy app
```

## API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| POST | `/api/novels/upload` | 小说上传与章节解析 |
| GET | `/api/novels/{id}` | 获取小说详情 |
| POST | `/api/cpc/build` | CPC 因果图构建 |
| GET | `/api/cpc/{id}/graph` | 获取 DAG 图数据 |
| POST | `/api/r2/scan` | R2 滑动窗口扫描 |
| GET | `/api/r2/{id}/result` | 获取改写结果 |
| POST | `/api/har/refine` | HAR 自校正 |
| GET | `/api/har/{id}/report` | 获取校正报告 |
| POST | `/api/screenplay/generate` | ScreenYAML 生成 |
| GET | `/api/screenplay/{id}` | 获取剧本 |
| GET | `/api/export/{id}` | 导出剧本文件 |

## 目录结构

```text
backend/
├── app/
│   ├── api/                # API 路由
│   ├── core/               # 配置、依赖注入
│   ├── models/             # Pydantic 数据模型
│   ├── services/           # 业务逻辑层
│   │   ├── r2/             # R2 读者-重写器
│   │   ├── cpc/            # CPC 因果图构建
│   │   ├── har/            # HAR 幻觉自校正
│   │   └── screenplay/     # ScreenYAML 生成与导出
│   └── main.py             # FastAPI 入口
├── tests/                  # 测试
├── pyproject.toml
└── README.md
```

## 核心算法模块

| 模块 | 缩写 | 说明 |
|------|------|------|
| 读者-重写器框架 | R2 | 滑动窗口扫描小说块，逐块分析并改写为剧本片段 |
| 因果情节图构建 | CPC | 贪婪循环破除算法，将事件关系构建为有向无环图 (DAG) |
| 幻觉感知改进 | HAR | 基于向量 RAG 的自校正循环，检测并修正 LLM 幻觉 |

后续真实实现应在独立 PR 中逐步开发，每个模块一个 PR。
