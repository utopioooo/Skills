---
name: premium-doc-maker
description: 把一门技术主题编排成可交付、可售卖的精品技术课程文档——单文件、零外部依赖、高颜值中文 HTML（课程目录页 + 分讲正文页）。内置可替换风格包（默认 blue-ink：浅色蓝白 / 深色黑橙）、品牌信息（品牌 / 作者 / 口号）、内容骨架与写作方法论、手写 SVG 规范，以及脚手架 / 验收 / 重编号 / 预览 / 打包脚本。当用户需要"把资料整理成精品文档/课程"、"做一套课程页面"、"照着某种风格再做一套技术文档"、"整理成可出售的文档产品"、"设置品牌作者和口号"、"给课程补一讲 / 重排讲次 / 换个风格"时使用。
version: 2.1.0
---

# 精品技术课程文档生产线

## 目的

把散乱的技术知识加工成**结构统一、视觉精良、单文件可离线分发**的中文课程文档。产物是纯静态 HTML，双击即开，可直接打包出售或放进任意站点。

产物固定为：

```
<课程名>/
├── index.html      课程目录页：品牌头图 + 课程说明 + 按阶段分组的章节卡片
├── 01.html         第 1 讲正文
├── 02.html         …
├── NN.html         第 N 讲正文
└── manifest.json   讲次清单（课程/品牌/作者/口号/年份/风格 + 各讲标题/摘要/阶段），
                    所有一致性检查的唯一事实源
```

品牌信息（`brand` / `author` / `slogan`）只写在 manifest 与大纲里，由模板渲染到每页页脚；
不要在某一页手写作者或口号，否则重编号与换品牌时会漂移。

**风格不在产物里，而在 `styles/<风格名>/`。** 换风格只需换一个风格包，流程、脚本、校验全部复用。

## 何时使用

- 把 PDF / 笔记 / 代码仓库 / 视频课转写成体系化课程页
- 照现有风格再做一套别的主题（Rust、K8s、量化、AI 工程…）
- 给已有课程补一讲、删一讲、调整顺序、换品牌、换风格
- 需要一套"能验收、能打包、能维护"的文档，而不是一次性页面

## 不变量（任何风格都必须满足）

1. **单文件、零外部依赖**：CSS 内联、图标与图表内联 SVG；禁止 CDN、外链图片、外链字体、外部 JS。
   禁止任何 `<img>` 与 `src`（包括 base64 data URI）——需要图就画 SVG。
   唯一例外：两段内联 `<script>`（主题切换 + 回到顶部），见 `references/design-system.md`。
2. **双主题 + 右下悬浮菜单**：浅色/深色只覆盖 CSS 令牌；组件里禁止裸色值，插图里禁止 `var()`。
3. **中文优先**：`<html lang="zh-CN">`；术语保留英文并括注，如 `RAII（资源获取即初始化）`。
4. **内容真实**：禁止 TODO、伪代码、"此处省略"；代码自包含、可编译；性能数字必须标注实测/典型值/来源。
5. **一致性由 manifest 驱动**：标题、讲次、页脚、目录卡片、翻页一律由脚本生成或同步，不手改。
6. **每讲结构**：4~6 个小节、2~6 个代码块、1~3 张表、1~6 张 SVG（下限 1），正文 800~2200 汉字。
7. **转义**：任何位置（正文、行内 `<code>`、`<pre>`）的 `<` 都必须写成 `&lt;`；
   `&` 在可能构成实体时写成 `&amp;`。解析器出现未知标签（如 `<int>`）即视为未转义。
8. **验收**：`validate.py` 必须 0 error；warning 逐条判断；再跑内容评审表（见文末）。
   机器验收只覆盖结构与一致性，不等于内容达到精品标准。

## 七阶段工作流

脚本用本 skill 的绝对路径调用（`python <skill-dir>/scripts/validate.py ...`），
输出目录也用绝对路径；`cd` 到 skill 根目录后用 `scripts/...` 也可以。
不要假设当前项目目录里有 `scripts/`。

### 阶段 0 — 规格确认（人工）

确认：课程名、目标读者、讲次数量（默认 20~30）、风格包、**品牌名 / 作者 / 口号（slogan）**、年份。
作者默认同品牌；三者都会渲染到每页页脚，所以要在开工前定下来。
拿不准就给默认值并在交付时说明。**风格包先选默认 `blue-ink`**；要做新风格见文末"给新风格的最小步骤"。

### 阶段 1 — 素材 → 大纲（产物：`outline.md`）

把素材拆成"能力点"，排依赖顺序，写出每讲的摘要与 4~6 个小节标题。
格式见 `references/process.md` 第 2 节；**大纲必须给用户确认后再批量生产**。

抽不出 4~6 个小节，说明这一讲边界不清，回到能力点重新切。

### 阶段 2 — 样张（产物：1 讲成品）

先只做第 1 讲，质量对齐 `examples/golden/01.html`，交用户确认视觉与内容密度；
同时确认页脚的品牌 / 作者 / 口号写法。
**跳过这一步直接批量，是最贵的返工来源。**

### 阶段 3 — 生成骨架

```bash
python scripts/scaffold.py --outline outline.md --outdir ./out
```

生成 `manifest.json`、`index.html`、各讲正文壳。壳里只有结构与写作提示，空小节会被 `validate.py` 判错。

### 阶段 4 — 逐讲填内容

打开 `NN.html`，把每个 `<section>` 里的提示注释替换为正文。
组件片段从 `references/markup-cookbook.md` 复制；内容标准见 `references/content-blueprint.md`。
图表从 `references/svg-patterns.md` 挑模式改文字与坐标，不要凭空发挥。

### 阶段 5 — 验收

```bash
python scripts/validate.py --dir ./out
```

0 error 才算完成；warning 逐条判断。它会查占位符、外链、脚本数、令牌、裸色值、SVG 内 `var()`、
任意位置的未转义尖括号、marker id、页脚/标题/编号/共 N 讲/作者一致、数量下限、跨讲重复等 40 余项，
并给出内容质量提示（空洞表达、无来源性能数字、表格形状、总结是否有 4~6 条准则）。
**不要靠人眼看 30 页。**

然后做**视觉验收**（机器查不了渲染）：

```bash
python scripts/preview.py --dir ./out              # 起本地服务器，人工看
python scripts/preview.py --dir ./out --screenshot # 可选：Playwright 生成 8 张截图
```

至少检查目录页 + 第 1 讲在 1280px / 375px、浅色 / 深色下的文字溢出、SVG 重叠、表格裁切。

### 阶段 6 — 打包交付

```bash
python scripts/pack.py --dir ./out
```

先跑验收，通过后生成 zip：顶层是课程文件夹，内含 `README.txt`、`LICENSE.txt`、`QA.md`、
`manifest.json` 与全部 HTML。多门课解压到同一目录也不会互相覆盖。

### 阶段 7 — 维护

| 需求 | 命令 |
|---|---|
| 补一讲 | 大纲末尾加一节 → `scaffold.py --add` → `renumber.py` |
| 删一讲 / 调顺序 | 改 `manifest.json` 的 chapters → `renumber.py`（旧文件会归档到 `_trash/`） |
| 只重建目录页 | `python scripts/scaffold.py --index-only --outdir ./out` |
| 换品牌 / 作者 / 口号 / 年份 / 副标题 | 改 manifest，跑 `renumber.py` |
| 派生新风格 | `python scripts/new_style.py --name sunset`，改 tokens，跑 `--style-only` |
| 重新打包 | `python scripts/pack.py --dir ./out` |

## 命令速查

| 命令 | 作用 |
|---|---|
| `python scripts/scaffold.py --outline outline.md --outdir ./out` | 生成 manifest + 目录页 + 各讲壳 |
| `python scripts/scaffold.py ... --brand X --author Y --slogan Z` | 覆盖大纲里的品牌信息 |
| `python scripts/scaffold.py --index-only --outdir ./out` | 只重建目录页 |
| `python scripts/validate.py --dir ./out` | 全量验收（退出码 1 = 有错误） |
| `python scripts/validate.py --file x.html` | 单页验收（自动读取同目录 manifest 的风格包） |
| `python scripts/validate.py --dir ./out --strict` | 警告也视为失败（交付前建议跑一次） |
| `python scripts/validate.py --style-only blue-ink` | 只验风格包令牌与对比度 |
| `python scripts/renumber.py --dir ./out` | 重编号并同步页脚/翻页/交叉引用；孤立页面归档 `_trash/` |
| `python scripts/renumber.py --dir ./out --keep-orphans` | 有孤立页面时中止，不做任何修改 |
| `python scripts/preview.py --dir ./out` | 本地预览（标准库）；`--screenshot` 需 Playwright |
| `python scripts/pack.py --dir ./out` | 验收并打包（课程文件夹 + README/LICENSE/QA） |
| `python scripts/check_code.py --dir ./out` | 可选：C++ 课程代码语法检查（其他语言跳过；无编译器自动跳过） |
| `python scripts/new_style.py --name X` | 派生风格包 |
| `python scripts/selftest.py` | 自检整条链路（改脚本或风格包后跑） |

脚本只依赖 Python 3.9+ 标准库，无需安装第三方包。

## 资源索引

| 文件 | 用途 | 何时读 |
|---|---|---|
| `references/process.md` | 七阶段的产物、门禁、`outline.md` 格式、增量操作、完工定义 | 开工前 / 排期时 |
| `references/content-blueprint.md` | 一讲怎么切、五段骨架、五步法、颗粒度、代码/表格规范、禁忌 | 写大纲与正文前必读 |
| `references/design-system.md` | 默认风格包的结构、令牌、组件、主题机制、响应式、无障碍、打印 | 改样式或排查显示问题 |
| `references/style-protocol.md` | 一个"风格包"必须提供什么；如何派生与验收新风格 | 做新风格时 |
| `references/svg-patterns.md` | 五种手写 SVG 模式 + 图标 + 自检 | 画图时 |
| `references/markup-cookbook.md` | 所有组件的可复制 HTML 片段 | 填正文时 |
| `styles/blue-ink/` | 默认风格包：`tokens.css` + `components.css` + 两个模板 | 构建时由脚本注入 |
| `examples/golden/01.html` | 一讲成品样张（可直接对照密度与写法） | 阶段 2 / 4 |
| `examples/outline.md` | 大纲样例 | 阶段 1 |
| `examples/glossary.md` | 术语表样例（跨讲统一叫法） | 阶段 1 / 4 |
| `scripts/*.py` | 脚手架、验收、重编号、预览截图、打包、派生风格 | 全程 |

## 交付前自检（与 validate 对应）

- [ ] `validate.py` 0 error，warning 已逐条判断（建议再跑 `--strict`）
- [ ] 内容评审表（文末）全部通过，至少抽查 20% 讲次
- [ ] 每讲 4~6 小节，每节至少一种载体（段落+代码/表格/SVG/列表）
- [ ] 代码块 ≥2、表格 ≥1、内容 SVG ≥1；正文 800~2200 汉字
- [ ] 深色主题实测可切、刷新保持、翻页不跳色；插图颜色不变
- [ ] 目录卡片数与实际讲次一致，链接都能打开
- [ ] 页脚品牌 / 作者 / 口号、课程名、讲次、共 N 讲与 manifest 一致
- [ ] 全书 h2 编号风格统一（中文序号或阿拉伯序号，二选一）
- [ ] 浏览器实际打开：桌面 1280 宽 + 手机 375 宽各看一遍（或 `preview.py --screenshot`）
- [ ] 无占位符、无 TODO、任何位置都没有未转义尖括号
- [ ] zip 解压后是独立课程文件夹，README / LICENSE / QA.md 齐全

## 常见偏差与纠正

| 现象 | 根因 | 纠正 |
|---|---|---|
| 深色主题切不动 | 组件里写了裸十六进制 | 改 `var(--token)`；`validate.py` 会报裸色值 |
| 插图跟着变暗 | SVG 里用了 `var()` 或给 svg 加 filter | 插图颜色一律字面量 hex |
| 页面像模板 | 只改标题没填内容 | 空小节 / 占位符会被 validate 判错；对照 golden 的密度 |
| 目录卡片点不开 | 手改 index 没同步 manifest | 用 `--index-only` 重建，不要手改 |
| 补一讲后编号全乱 | 手改文件名和页脚 | 改 manifest 后跑 `renumber.py` |
| 删讲后 renumber 报“目标已存在” | 被删讲次的旧文件还在磁盘 | 2.1 起会自动归档到 `_trash/`；旧版本先手动删文件 |
| 30 页页脚各不相同 | 每页手写页脚 / 作者 / 口号 | 页脚只由模板生成；品牌信息写在 manifest，renumber 统一同步 |
| 单页验收报“令牌不一致” | 换了风格但 `--file` 没指定风格 | 2.1 起自动读同目录 manifest；旧版本加 `--style <name>` |
| 正文里的 `<int>` 不见了 | 行内代码没转义 | 任意位置 `<` 都要写 `&lt;`；validate 会报“未知标签” |
| 文字压深色底 | 新增组件用了浅色固定值 | 只用令牌；跑 `--style-only` 验对比度 |
| 手机上字太小/表格溢出 | SVG 没横向滚动、表格没包容器 | `.svg-container` / `.table-wrap` 已内置滚动 |

## 给"新风格"的最小步骤

1. `python scripts/new_style.py --name <name>`
2. 改 `styles/<name>/tokens.css`（两套主题键必须一致）
3. 改 `styles/<name>/contrast.json` 的门槛并跑 `python scripts/validate.py --style-only <name>`
4. `python scripts/scaffold.py --style <name> --outline outline.md --outdir ./out`
5. 做 1 讲样张，确认后再批量

## 量产节奏（20~30 讲）

一次写 30 讲再验收，返工面最大。建议：

1. 阶段 2 样张确认后，按 **3~5 讲一批**生产。
2. 每批：填正文 → `validate.py --file` 逐页 → 本批全过再开下一批。
3. 每批结束跑一次 `validate.py --dir`，防止跨讲漂移（重复段落、编号混用、共 N 讲不一致）。
4. 可在 manifest 的每讲里加 `status`（draft / reviewed / published）记录进度；至少维护一份批次清单。
5. 任何一讲改了标题或小节：先改 manifest，再 `renumber.py`，最后 `validate.py`。

## 商业化交付

`pack.py` 生成的 zip 已包含：

- 顶层课程文件夹（多门课解压到同一目录不会互相覆盖）；
- `README.txt`：打开方式、品牌 / 作者 / 口号、讲次；
- `LICENSE.txt`：个人学习授权、禁止转售与再分发；
- `QA.md`：机器验收输出 + 人工验收清单；
- `manifest.json` 与全部 HTML。

按产品定位可选增强：

- 试读页：单独打包 1~2 讲，或截取目录页；
- 封面图：用目录页截图 + 品牌色即可，不必引入设计软件；
- 水印 / 购买者编号：在 README 与页脚追加；批量定制需另写脚本；
- PDF：浏览器“打印 → 另存为 PDF”，`@media print` 已做浅色覆盖；
- 素材授权：从他人课程/书籍提炼时，保留事实与技术判断、重写表达，并注明来源与授权状态；
  整讲照搬不得交付。

## 内容评审表（机器查不了的部分）

抽查至少 20% 讲次，逐项打勾：

- [ ] 每讲开篇第一段直接给判断，不铺垫。
- [ ] 每个机制都能落到“明天上班能做的动作”。
- [ ] 有具体数字 / 参数 / 条件，且标了实测、典型值或来源。
- [ ] 代码解释“为什么这么写”，不是逐行翻译。
- [ ] 对比表能直接支持选型，不是百科罗列。
- [ ] 图承载结构、流向或对照，删掉图会损失信息。
- [ ] 没有“下面我们来看 / 总的来说 / 众所周知”等口水话。
- [ ] 没有把官方 API 列表整段搬入。
- [ ] 同一概念全书叫法一致（对照 `glossary.md`）。
- [ ] 结尾 4~6 条准则可执行，最后一句不是空洞口号。
