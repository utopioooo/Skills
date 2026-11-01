# 变更记录

## 2.1.0 — 维护路径与交付闭环

技能更名为 `premium-doc-maker`；默认品牌改为「翎光技术文档」。

### 修复

- `renumber.py`：删讲不再崩溃。manifest 里没有的 `NN.html` 默认归档到 `_trash/`，
  `--keep-orphans` 改为中止；改名失败会回滚；正文先在内存改好再落盘；
  上次崩溃遗留的 `__tmp__` 文件会自动恢复或归档。
- 未转义尖括号不再只查 `<pre>`：用已知标签白名单检测任意位置的未知标签
  （如行内 `<code>std::vector<int></code>`），并报“疑似未转义”。
- `validate.py --file` 自动读取同目录 `manifest.json` 的风格包，派生风格不再误报
  “令牌不一致”。
- `scaffold.py --add` 改为按位置对齐，改标题不会被误判成新讲并追加重复条目。
- `renumber.py` 不再把标题里的反斜杠当正则转义序列。
- `.complexity-badge` 变体统一为小写 `.on` / `.ologn`，与组件契约一致。

### 新增

- 品牌信息：`manifest.author`、大纲 `- 作者：`、`scaffold --author`；
  页脚新增 `<p class="footer-author">作者：…</p>`，由模板与 renumber 统一渲染。
- 页脚/头部一致性：校验「共 N 讲」、年份、作者；目录页课程说明的「共 N 讲」升级为错误。
- 内容质量提示（warning）：空洞表达、无来源性能数字、表格行列数、总结缺 4~6 条准则、代码块长度。
- `validate.py` 提示没有 `data-ref` 的纯文本「第 N 讲」，避免重编号后引用过期。
- 风格包必需令牌清单（37 个）与更多必需组件类名校验。
- `scripts/preview.py`：本地预览；可选 Playwright 生成浅色/深色 × 桌面/手机截图。
- `pack.py`：zip 增加顶层课程文件夹、`LICENSE.txt`、`QA.md`；README 增加作者字段。
- `SKILL.md`：量产节奏（3~5 讲一批）、商业化交付、内容评审表。
- `selftest.py` 扩到 11 项：真实换序/删讲、`--add` 改标题、非默认风格单页验收、
  未转义尖括号、纯文本引用、zip 结构。

### 变更

- 默认品牌与示例统一为「翎光技术文档」；示例大纲新增 `- 作者：`。
- SVG 色板：深底白字的绿/橙改为 `#2E7D32` / `#A35A00`（对比度 ≥5:1）；
  `#4CAF50` / `#F5A623` 只作描边或配深色字。
- `contrast.json` 增加卡片按钮、提示框、链接等 6 组检查。

## 2.0.0 — 结构化重构

按审查报告修复了"能生成页面但无法稳定交付"的问题，重点是**单一事实源 + 可执行验收 + 风格可替换**。

### 修复

- 统一设计令牌：原先文档（调色板 A/B/C、§12 语义令牌）与模板三套并存，现只有 `styles/blue-ink/tokens.css` 一份；模板通过 `{{STYLE_CSS}}` 注入，不再复制 CSS。
- 消除文档矛盾：删除"无 script"与"必须两段 script"并存、"禁止 Font Awesome"与 `fas fa-rocket` 并存、组件示例写死 `#fff` 等冲突。
- 修正标定：正文字数由声称的 2000~4000 改为实测口径 800~2200（硬范围 600~3000）；小节数明确 4~6。
- 页头对比度：默认渐变改为深蓝（白字 ≥5:1）/ 深色主题改为亮橙（深字 ≥7:1），并通过 `contrast.json` 固化检查。
- 响应式：`.svg-container` 与 `.table-wrap` 内置横向滚动，SVG 最小宽度 560px，解决手机上 800 宽图表文字缩到 7px 的问题。
- 深色主题：复杂度徽章改为令牌驱动；表格 hover / 斑马纹全部令牌化，不再出现白块。
- 打印：新增 `@media print` 浅色覆盖，避免深色主题打印黑底。
- 无障碍：`:focus-visible`、`aria-pressed`、`aria-hidden`、`prefers-reduced-motion`、SVG `role/title`。
- 语料 bug：修复原 30 讲中 `25.html` 的未转义 `<int>`（浏览器会吞掉代码片段）。

### 新增

- `scripts/validate.py`：30 余项验收（占位符、外链、脚本数、令牌、裸色值、SVG `var()`、`<pre>` 转义、id 重复、页脚/标题/讲次/翻页一致、数量下限、跨讲重复、对比度）。退出码可用于 CI。
- `scripts/renumber.py`：插讲/删讲/换序后统一文件名、页脚、翻页、交叉引用、目录页。
- `scripts/pack.py`：先验收再打 zip，附 README。
- `scripts/new_style.py`：从默认风格派生新风格包，并立即做对比度校验。
- `scripts/check_code.py`：可选地对 C++ 代码块做 `-fsyntax-only` 检查（无编译器自动跳过）。
- `scripts/selftest.py`：在临时目录跑通"生成→验收→重编号→打包"，改脚本后先跑它。
- `manifest.json`：讲次清单成为唯一事实源，目录页与页脚由它渲染。
- `outline.md` 规范与解析（`scaffold.py --outline`），支持每讲 4~6 个小节标题。
- 可选字段：难度（入门/进阶/实战/专家）与时长（分钟），显示在目录卡片上。
- `--add` / `--index-only` / `--dry-run` / `--force`：增量维护不再覆盖已写正文。
- `examples/golden/01.html`：一讲成品样张；`examples/outline.md`：大纲样例。
- 流程文档：`process.md`、`style-protocol.md`、`markup-cookbook.md`。

### 变更

- `SKILL.md` 改为风格无关的七阶段流程；风格细节下放到 `references/` 与 `styles/`。
- 目录页按阶段分组；正文页新增上一讲/下一讲导航。
- 页脚、kicker、meta description 由 manifest 驱动，可被 renumber 同步。

### 移除

- `assets/`（旧模板，CSS 与文档三处不一致）
- `scripts/scaffold_course.py`（旧脚手架，重跑覆盖正文、无验收）

### 迁移提示（从 1.x 升级）

- 1.x 生成的页面没有 `manifest.json`、`data-n` / `data-title` / `.pager` 锚点，**不能直接跑 `renumber.py`**。
  正确做法：用 2.0 的 `scaffold.py` 重新生成到新目录，再把各讲 `<section>` 内容搬过去，最后 `validate.py`。
- 旧页面内联的是旧 CSS（三套令牌），不要逐页手改；统一重新注入后再改。
- 原 30 讲语料只修了 `25.html` 的真实渲染 bug（未转义 `<int>`），其余结构问题保留为"源材料现状"；
  如需把语料本身规范化，应作为一次独立的迁移任务，用新模板重排后再跑验收。
