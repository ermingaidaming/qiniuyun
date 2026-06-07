# ScreenYAML Schema — Draft 2026-01

> AI 小说自动转剧本的结构化输出格式。  
> 版次：Draft 2026-01  
> 维护者：uYu (A), rayi (B)

---

## 目录

1. [设计目标](#1-设计目标)
2. [为什么选择 YAML](#2-为什么选择-yaml)
3. [Schema 定义](#3-schema-定义)
4. [完整示例](#4-完整示例)
5. [与后端模型映射](#5-与后端模型映射)
6. [LLM Prompt 指引](#6-llm-prompt-指引)
7. [版本演进计划](#7-版本演进计划)

---

## 1. 设计目标

ScreenYAML 是 AI 小说转剧本工具的**核心输出格式**。它服务于三类用户：

| 用户 | 需求 |
|------|------|
| **作者** | 拿到可读、可编辑的剧本初稿，不需要懂 JSON |
| **LLM** | 有明确的输出约束，减少幻觉、提高结构化程度 |
| **下游工具** | 可被 Final Draft、fountain.js 等剧本工具导入 |

### 关于"ScreenYAML"

> **ScreenYAML 是为本项目原创设计的剧本交换格式，并非现有行业标准。**

设计参考了以下来源：
- [Final Draft (.fdx)](https://www.finaldraft.com/) — 行业标准剧本软件的 XML 格式，其 Paragraph 元素的 Type 分类（Scene Heading / Action / Character / Dialogue / Parenthetical）是四元素模型的主要参照
- [Fountain](https://fountain.io/) — 开源剧本标记语言的纯文本约定
- [YAML 1.2 规范](https://yaml.org/spec/1.2.2/) — 定义了合法的 YAML 结构

我们不声称 ScreenYAML 兼容 Final Draft 或 Fountain，它是一个**独立的、面向 AI 生成场景**的格式化方案。

### 设计原则

1. **人类优先** — YAML 比 JSON 更适合人阅读和手动编辑
2. **结构完整** — 覆盖剧本四大元素：动作描述、角色标记、对话、括号提示
3. **可扩展** — 预留 CPC 因果图、R2 改写追踪、HAR 幻觉标记字段
4. **与模型解耦** — Schema 独立于 Pydantic 实现，前后端共享这份文档作为契约

---

## 2. 为什么选择 YAML

### 2.1 与 JSON 对比

| 维度 | JSON | YAML |
|------|------|------|
| 可读性 | 引号和括号密集，长文本阅读困难 | 缩进表示层级，更像自然排版 |
| 手动编辑 | 引号转义、逗号末尾等问题频发 | 极少需要转义，直接写中文 |
| 注释 | **不支持** | `#` 行注释 |
| 多行文本 | `\n` 转义，不可读 | `|` 字面量块，所见即所得 |
| 剧本行业 | 无使用先例 | Fountain (Markdown-like) 相近 |

### 2.2 剧本文本的特殊性

剧本中对话和动作描述常包含大量中文标点（`""''：：（（））`），JSON 的字符串转义会让作者难以直接编辑。例如：

```json
"content": "\"废柴也敢上台？\"赵无极轻蔑一笑，\"三招之内，让你躺下。\""
```

同等 YAML：

```yaml
text: |
  "废柴也敢上台？"赵无极轻蔑一笑，"三招之内，让你躺下。"
```

### 2.3 多行对话支持

长对话在 YAML 中可以用 `|` 保留换行：

```yaml
- type: dialogue
  character: 林轩
  text: |
    你们都说我是废柴。
    但今天，我要用这柄剑证明——
    废柴也能劈开这天。
```

---

## 3. Schema 定义

### 3.1 顶层结构

```yaml
# ScreenYAML Document
meta:     Meta       # 剧本元信息（必填）
scenes:   Scene[]    # 场景列表（必填）
```

### 3.2 Meta（元信息）

```yaml
meta:
  title: string              # 剧本标题，如 "《剑道风云》剧本"
  source_novel: string       # 源小说名
  novel_author: string       # 原著作者（若已知）
  total_chapters: int        # 源小说总章节数
  generated_by: string       # 生成模型，如 "deepseek-chat"
  screenplay_version: string # ScreenYAML 版本，当前 "2026-01"
  created_at: string         # ISO 8601 时间戳
```

### 3.3 Scene（场景）

```yaml
scenes:
  - scene_id: int           # 场景序号，从 1 开始递增
    location: string        # 地点，如 "青云宗练功场"
    time: string            # 时间，如 "清晨"、"深夜"、"次日午后"
    setting: string         # 场景描述（一句话概括氛围）
    source_chapter: int     # 来源章节号
    characters: string[]    # 本场景出场角色列表
    elements: Element[]     # 场景元素列表（动作/角色/对话/括号）
```

`setting` 与 `location`/`time` 的区别：
- `location` 和 `time` 是结构化字段，方便下游工具索引和搜索
- `setting` 是自然语言描述，直接用于剧本阅读，如 "练功场内，数百弟子挥剑，晨光中剑光如星"

### 3.4 Element（场景元素）

每个场景由四种元素类型组成，按剧本标准顺序排列：

#### 3.4.1 action — 动作/环境描述

```yaml
- type: action
  content: string   # 动作描述、环境描写、转场说明
```

对应剧本格式中的**动作行**（Action Line），描述场景中发生的动作、环境变化、或人物行为。

#### 3.4.2 character — 角色出场标记

```yaml
- type: character
  name: string      # 角色名（同时也是 content 的值）
```

对应剧本格式中的**角色行**（Character Cue），标记接下来的对话由谁说。必须出现在 dialogue 之前。

#### 3.4.3 dialogue — 对话

```yaml
- type: dialogue
  character: string # 说话角色名
  text: string      # 对话内容（支持 | 多行）
```

对应剧本中的**对话行**。`character` 必须与紧邻的 character 元素的 `name` 一致。

#### 3.4.4 parenthetical — 括号提示

```yaml
- type: parenthetical
  character: string # 所属角色名
  text: string      # 提示内容，不含外层括号
```

对应剧本中角色名下方的括号提示（Parenthetical），如 "(激动地)"、"(低声)"、"(拔剑)"。渲染时自动包裹在括号中。必须出现在 character 之后、dialogue 之前（或两段 dialogue 之间）。

### 3.5 场景元素排序规则

一个标准场景的元素顺序为：

```
[action]          ← 开场的环境和动作描述
[action]          ← 可以多个
character         ← 说话人出场
[parenthetical]   ← 可选：情绪/动作提示
dialogue          ← 实际对话
[parenthetical]   ← 可选：对话中的情绪转折
dialogue          ← 继续对话
[character]       ← 切换说话人
dialogue
action            ← 结束动作或转场
```

核心规则：
1. **dialogue 前必须有 character**（确定说话人）
2. **parenthetical 和 dialogue 必须有 character 字段**
3. **action 可以出现在任何位置**（描述环境、动作、转场）

### 3.6 可选扩展字段（后续版本）

```yaml
scenes:
  - scene_id: 1
    # ... 基础字段 ...

    # CPC 因果图扩展（vNext）
    cpc_events:            # 本场景的关键事件节点
      - event_id: "e1"
        description: "林轩报名参加大比"
        causes: []           # 前置事件 ID
        effects: ["e2"]      # 后置事件 ID

    # R2 改写追踪（vNext）
    r2_tracking:
      source_segment: "原文第 45-62 行"
      rewrite_confidence: 0.92
      rewritten_by: "deepseek-chat"

    # HAR 幻觉标记（vNext）
    har_flags:
      hallucination_risk: "low"
      verified_elements: ["character:林轩", "location:练功场"]
      uncertain_elements: []
```

---

## 4. 完整示例

> 以下示例基于《西游记》第一回"灵根育孕源流出 心性修持大道生"的真实文本。

```yaml
meta:
  title: "《西游记》剧本"
  source_novel: "西游记"
  novel_author: "吴承恩"
  total_chapters: 100
  generated_by: "deepseek-chat"
  screenplay_version: "2026-01"
  created_at: "2026-06-06T14:40:30Z"

scenes:
  - scene_id: 1
    location: "花果山山顶"
    time: "远古时代"
    setting: "东胜神洲海外傲来国，海中花果山山顶。一块三丈六尺五寸高的仙石，受天真地秀、日精月华，内育仙胞。"
    source_chapter: 1
    characters: []
    elements:
      - type: action
        content: "海外东胜神洲，傲来国近海处，矗立着一座花果山。山顶之上，一块高三丈六尺五寸、围圆二丈四尺的仙石，正在吸收日月精华。"

      - type: action
        content: "仙石突然迸裂，产出一颗石卵。石卵见风，化作一只石猴。石猴五官俱备、四肢皆全，随即学会了爬走。"

      - type: action
        content: "石猴双目射出两道金光，直冲云霄，惊动了天庭玉皇大帝。"

  - scene_id: 2
    location: "花果山水帘洞前"
    time: "同年夏日"
    setting: "一群猴子在山涧中洗澡，顺流寻源，发现一道瀑布飞泉。众猴约定：能钻进瀑布寻到源头且不伤身体者，拜他为王。"
    source_chapter: 1
    characters:
      - "石猴"
      - "众猴"
    elements:
      - type: action
        content: "天气炎热，一群猴子在松荫下玩耍，随后去山涧中洗澡。顺涧爬山，直至源流之处，乃是一股瀑布飞泉。"

      - type: character
        name: "众猴"

      - type: dialogue
        character: "众猴"
        text: "那一个有本事的，钻进去寻个源头出来，不伤身体者，我等即拜他为王！"

      - type: action
        content: "连呼三声，忽见丛杂中跳出一只石猴，高声应诺。"

      - type: character
        name: "石猴"

      - type: dialogue
        character: "石猴"
        text: "我进去！我进去！"

      - type: action
        content: "石猴瞑目蹲身，将身一纵，径直跳入瀑布泉中。"

  - scene_id: 3
    location: "水帘洞内"
    time: "同日"
    setting: "石猴穿过瀑布，见里面无水无波，乃是一座铁板桥。桥后是天然洞府，正中立一石碣，上镌'花果山福地，水帘洞洞天'。"
    source_chapter: 1
    characters:
      - "石猴"
      - "众猴"
    elements:
      - type: action
        content: "石猴穿过瀑布，睁眼一看，里面却无水无波，明明朗朗是一座铁板桥。桥下之水，冲贯于石窍之间，倒挂流出去，遮闭了桥门。"

      - type: action
        content: "石猴走过桥，见正当中有一座石碣，碣上镌着'花果山福地，水帘洞洞天'十个大字。洞内有石锅石灶、石碗石盆、石床石凳，一应俱全。"

      - type: character
        name: "石猴"

      - type: dialogue
        character: "石猴"
        text: "大造化！大造化！"

      - type: action
        content: "石猴跳出瀑布，回到群猴中间，将所见景象细细讲述。"

      - type: character
        name: "众猴"

      - type: parenthetical
        character: "众猴"
        text: "（欢喜雀跃）"

      - type: dialogue
        character: "众猴"
        text: "大王！大王！带我们进去！"

      - type: action
        content: "石猴带领众猴穿过瀑布，进入水帘洞。众猴抢盆夺碗、占灶争床，搬过来移过去，直至力倦神疲方止。石猴端坐高处，正式成为美猴王。"
```

---

## 5. 与后端模型映射

后端 Pydantic 模型与 YAML 字段的对应关系：

| YAML 路径 | Pydantic 字段 | 类型 |
|-----------|--------------|------|
| `meta.title` | `Screenplay.title` | `str` |
| `meta.created_at` | `Screenplay.created_at` | `datetime` |
| `scenes[].scene_id` | `Scene.index` | `int` |
| `scenes[].location` | `Scene.location` | `str` |
| `scenes[].time` | `Scene.time_of_day` | `str` |
| `scenes[].setting` | `Scene.setting` | `str` |
| `scenes[].source_chapter` | `Scene.source_chapter` | `int` |
| `scenes[].characters` | `Scene.characters` | `list[str]` |
| `scenes[].elements[]` | `Scene.elements[]` | `list[SceneElement]` |
| `elements[].type` | `SceneElement.type` | `Literal["action","character","dialogue","parenthetical"]` |
| `elements[].content` (action) | `SceneElement.content` | `str` |
| `elements[].name` (character) | `SceneElement.content` | `str` |
| `elements[].text` (dialogue/parenthetical) | `SceneElement.content` | `str` |
| `elements[].character` (dialogue/parenthetical) | `SceneElement.character` | `str` |

### 5.1 序列化函数

```python
# backend/app/services/screenyaml.py (新增)

import yaml
from app.models.screenplay import Screenplay

def screenyaml_dumps(screenplay: Screenplay) -> str:
    """序列化 Screenplay → ScreenYAML 字符串"""
    ...

def screenyaml_loads(yaml_str: str) -> Screenplay:
    """反序列化 ScreenYAML 字符串 → Screenplay（含校验）"""
    ...
```

### 5.2 文件名约定

```
《西游记》剧本.screenyaml
```

扩展名 `.screenyaml` 用于标识本文件遵循 ScreenYAML Draft 2026-01 规范（本项目的内部格式约定）。

---

## 6. LLM Prompt 指引

向 LLM 描述输出格式时，使用以下 Prompt 模板：

```
你是一位专业剧本编剧。请将以下小说章节转化为 ScreenYAML 格式的剧本。

## 输出格式 (ScreenYAML Draft 2026-01)

输出必须为合法的 YAML，结构如下：

```yaml
scenes:
  - scene_id: <从1开始的整数>
    location: "<地点>"
    time: "<时间>"
    setting: "<场景一句话描述>"
    source_chapter: <章节号>
    characters: ["<角色1>", "<角色2>"]
    elements:
      - type: action
        content: "<动作或环境描述>"
      - type: character
        name: "<角色名>"
      - type: parenthetical
        character: "<角色名>"
        text: "<情绪或动作提示>"
      - type: dialogue
        character: "<角色名>"
        text: "<对话内容>"
```

## 规则

1. 每个 elements 序列以 action 开头，描述场景环境和氛围
2. 对话前必须有 character 元素
3. parenthetical 是可选的，用于标注情绪/动作提示
4. 对话 text 中的引号使用中文引号 ""，YAML 中无需转义
5. 多行对话使用 | 语法
6. 角色名保持一致，同一角色不应出现多个称呼
7. 只输出 YAML，不要输出任何解释性文字
```

---

## 7. 版本演进计划

| 版本 | 新增内容 | 预计时间 |
|------|----------|----------|
| **2026-01** | 基础四元素模型（action/character/dialogue/parenthetical） | 当前 |
| 2026-02 | CPC 因果事件图字段（`cpc_events`） | 后续 PR |
| 2026-03 | R2 滑动窗口改写追踪（`r2_tracking`） | 后续 PR |
| 2026-04 | HAR 幻觉检测标记（`har_flags`） | 后续 PR |
| 2026-05 | 过渡/转场类型（`transition` element） | 后续 PR |
| 1.0 | 冻结，提交比赛 | 截止日 |

---

## 附录 A：与 Final Draft (.fdx) 的对比

| 维度 | Final Draft (.fdx) | ScreenYAML |
|------|---------------------|------------|
| 格式 | XML | YAML |
| 可读性 | 需专用软件 | 任何文本编辑器 |
| 版本控制 | XML diff 难读 | YAML diff 友好 |
| AI 生成 | 无标准 schema | 内置 LLM prompt 模板 |
| 中文支持 | 需配置字体 | 原生支持 |
| 扩展性 | 封闭 | 预留 CPC/R2/HAR 扩展 |

## 附录 B：典型错误与修正

**错误**：dialogue 前缺少 character

```yaml
# ❌ 错误
elements:
  - type: dialogue
    character: "林轩"
    text: "你好。"
```

```yaml
# ✅ 正确
elements:
  - type: character
    name: "林轩"
  - type: dialogue
    character: "林轩"
    text: "你好。"
```

**错误**：parenthetical 出现在 character 之前

```yaml
# ❌ 错误
elements:
  - type: parenthetical
    character: "林轩"
    text: "（激动）"
  - type: character
    name: "林轩"
```

```yaml
# ✅ 正确
elements:
  - type: character
    name: "林轩"
  - type: parenthetical
    character: "林轩"
    text: "（激动）"
```
