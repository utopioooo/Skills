# 风格包协议

一个"风格"= 一套 CSS 令牌 + 一套组件样式 + 两个页面模板。流程、脚本、校验对风格无感。
本文件规定：一个风格包必须提供什么，才能被 `scaffold.py` 正确注入、被 `validate.py` 正确验收。

---

## 1. 目录结构

```
styles/<style-name>/
├── tokens.css      必需：浅色/深色两套令牌，键必须一致
├── components.css  必需：全部组件样式，禁止裸色值
├── contrast.json   必需：关键文字/控件的对比度契约
├── chapter.html    必需：正文页模板，含占位符
└── index.html      必需：目录页模板，含占位符
```

`styles/blue-ink/` 是参考实现。派生新风格：

```bash
python scripts/new_style.py --name sunset
```

它会复制默认包并立即跑一次 `--style-only` 校验；不通就不允许使用。

---

## 2. 令牌契约

### 2.1 必须定义的组

| 组 | 令牌 |
|---|---|
| 基底 | `--bg` `--surface` `--surface-2` `--text` `--text-mute` `--border` |
| 强调 | `--accent` `--accent-2` `--link` `--on-accent` |
| 头图 | `--header-a` `--header-b` `--on-header` |
| 表格 | `--th-bg` `--th-text` `--row-hover` `--row-zebra` |
| 代码 | `--code-bg` `--code-text` |
| 提示 | `--tip-bg` `--warn-bg` `--warn-border` `--key-bg` `--key-border` |
| 页脚 | `--footer-bg` `--footer-text` |
| 徽章 | `--badge-bg` `--badge-ink` `--badge-2-bg` `--badge-2-ink` `--badge-3-bg` `--badge-3-ink` |
| 尺度 | `--radius` `--radius-sm` `--shadow` `--shadow-hover` `--focus` |

### 2.2 规则

1. `:root` 与 `html[data-theme="dark"]` 的**键集合完全相同**；缺一个就报错。
2. 颜色值用 `#RRGGBB`；阴影可以用 `rgba()`；不要用命名色（`white`、`black`）以外的花哨写法。
3. 组件只引用令牌；`components.css` 剥掉令牌块和 `@media print` 后不得再出现 `#hex`。
4. 新增令牌必须同时补两套主题，并更新本文档的组表。

### 2.3 对比度契约（`contrast.json`）

```json
{
  "pairs": [
    { "fg": "--text", "bg": "--surface", "min": 7.0, "label": "正文/卡片" },
    { "fg": "--on-header", "bg": "--header-b", "min": 4.5, "label": "头图/渐变终点" }
  ]
}
```

- 正文/卡片底最低 7.0；次要文字、链接、强调色、表头、代码、页脚最低 4.5；图标控件最低 3.0。
- `validate.py --style-only <name>` 会逐对计算 WCAG 对比度，任何一对不达标即失败。
- 头图渐变要两端都验：白色文字配亮蓝渐变，浅端往往只有 2:1，是常见翻车点。

---

## 3. 模板契约

模板里的占位符是脚本与风格之间的接口，**名称不能改**。

### 3.1 `chapter.html`

| 占位符 | 含义 |
|---|---|
| `{{STYLE_CSS}}` | 注入 tokens.css + components.css（放在 `<style>` 内） |
| `{{TITLE}}` | 讲标题 |
| `{{SUMMARY}}` | 关键词摘要（正文可见） |
| `{{SUMMARY_ATTR}}` | 关键词摘要（HTML 属性转义，用于 meta description） |
| `{{COURSE}}` | 课程名 |
| `{{BRAND}}` | 品牌名 |
| `{{AUTHOR}}` | 作者名（页脚） |
| `{{SLOGAN}}` | 品牌口号 |
| `{{YEAR}}` | 年份 |
| `{{N}}` | 讲次（数字） |
| `{{TOTAL}}` | 总讲数 |
| `{{SECTIONS}}` | 由脚本生成的小节块 |
| `{{PREV_LINK}}` | 上一讲链接或禁用占位 |
| `{{NEXT_LINK}}` | 下一讲链接或禁用占位 |

必须包含的稳定锚点（`validate.py` 与 `renumber.py` 依赖）：

- `<header class="chapter-header">` + `p.kicker` + `h1` + `p.subtitle`
- `<main class="container">`
- `<nav class="pager">`，内部顺序为 上一讲 / 课程目录 / 下一讲
- `<footer>` 含 `p.footer-brand`、`p.footer-author` 与 `<span data-title>`
- 页脚讲次写成 `第 <span data-n="N">N</span> 讲`
- `.fab-menu` 三个按钮：`href="index.html"`、`#theme-toggle`、`#back-to-top`
- 恰好两段内联 `<script>`

### 3.2 `index.html`

| 占位符 | 含义 |
|---|---|
| `{{STYLE_CSS}}` | 同上 |
| `{{COURSE}}` `{{SUBTITLE}}` `{{SUBTITLE_ATTR}}` `{{BRAND}}` `{{AUTHOR}}` `{{SLOGAN}}` `{{YEAR}}` `{{TOTAL}}` | 课程与品牌信息 |
| `{{STAGE_GROUPS}}` | 由脚本生成的阶段分组与卡片 |

稳定锚点：`.index-header`、`h1`、`p.subtitle`、`section.directory-intro`、`section.stage`、`article.chapter-card`、`div.chapter-number`、`h3`、`p.chapter-content`、`a.chapter-link`、`footer`、两个 `.fab-btn`。

---

## 4. 组件契约

以下类名是"风格"与"内容"的共同接口，必须存在且有样式：

```
section / h2 / h2.h2-icon / h3
.table-wrap / table / th / td
.code-block / pre / code
.svg-container / .fig-caption
.tip-box / .warning-box / .key-point
.highlight / .keyword
.grid / .card
.timeline / .timeline-item
.badge / .complexity-badge（.on / .ologn）
.comparison
.pager / .pager-link / .pager-link.disabled
footer / .footer-brand / .footer-author
.fab-menu / .fab-btn
.chapter-header / .kicker / .subtitle
.index-header / .course-icon / .directory-intro
.stage / .stage-title / .stage-index / .chapters
.chapter-card / .chapter-number / .chapter-meta / .chapter-content / .chapter-link
```

可以换视觉，不必保留默认的圆角/阴影/渐变；但：

- 两套主题都要覆盖，且插图颜色恒定；
- `.svg-container` 与 `.table-wrap` 必须保留横向滚动（窄屏可读性）；
- 必须保留 `:focus-visible`、`prefers-reduced-motion`、`@media (max-width: 768px)`、`@media print`；
- 悬浮菜单与翻页的 DOM 结构不变（脚本按 id 查找）。

---

## 5. 插图配色

插图不跟随主题，因此每个风格包要自带一套**浅底可读**的图表色板，写在 `svg-patterns.md` 里（或风格包 README）。

默认 `blue-ink` 的图表色板：

| 用途 | 色值 |
|---|---|
| 主色块 | `#2F6FB3` |
| 副色块 | `#2E7D32`（配白字；`#4CAF50` 只作浅底描边） |
| 强调/警示 | `#A35A00` / `#C2410C`（配白字） |
| 危险 | `#D0021B` |
| 辅助 | `#9C27B0` |
| 图表底 | `#F5F9FF` / `#FFF3E0` |
| 文字 | `#1F2D3D`（浅底）/ `#FFFFFF`（深色块上） |

深色主题下插图仍是浅底，**不要**为深色主题另做一套图。

---

## 6. 派生新风格的完整流程

1. `python scripts/new_style.py --name <name>`（复制 + 首轮校验）
2. 改 `tokens.css`：
   - 先定浅色主题的 6 个基底色与 3 个强调色；
   - 再按同一色相关系推深色主题；
   - 头图渐变、表格、代码、提示框逐个配。
3. 改 `contrast.json`（如果提高了门槛）并跑：
   ```bash
   python scripts/validate.py --style-only <name>
   ```
4. 用新风格生成 1 讲样张：
   ```bash
   python scripts/scaffold.py --style <name> --outline outline.md --outdir ./out
   ```
5. 填第 1 讲，实际打开看浅色/深色、1280/375；确认插图、表格、代码块、提示框。
6. 通过后批量。
7. 如果改的是默认风格 `blue-ink`，记得把 `examples/golden/01.html` 里的 `<style>` 用新的
   `tokens.css` + `components.css` 重新注入，再跑 `scripts/selftest.py`，避免样张与风格包漂移。

---

## 7. 新风格验收清单

- [ ] 5 个文件齐全，占位符一个不少
- [ ] `validate.py --style-only` 0 error
- [ ] 浅色/深色都能切换，刷新保持
- [ ] 头图、表头、代码块、页脚在两种主题下都可读
- [ ] 插图在深色下颜色不变
- [ ] 375px 宽下表格与插图可横向滚动，正文不溢出
- [ ] 打印预览是浅色、无悬浮菜单
- [ ] 键盘 Tab 能看到焦点环
- [ ] 样张通过 `validate.py --file`
