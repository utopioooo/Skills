# 设计系统（默认风格包 `blue-ink`）

本文件说明这套视觉**怎么用**。真正的样式只有两份文件：

- `styles/blue-ink/tokens.css` —— 颜色与尺度令牌（两套主题）
- `styles/blue-ink/components.css` —— 全部组件样式

`scaffold.py` 在生成页面时把这两份文件内联进 `<style>`，所以产物仍是单文件。
**不要手改页面里的 `<style>`**：改了会和风格包脱节，`validate.py` 会报"令牌与风格包不一致"。

> 换风格见 `style-protocol.md`；所有颜色/尺寸以 `tokens.css` 为准，本文件不复制色值。

---

## 1. 主题定位

| 主题 | 基调 | 页面底 | 卡片/内容块 | 强调色 | 正文 |
|---|---|---|---|---|---|
| `light` | 蓝白 | 浅蓝白 | 纯白 | 深蓝 → 亮蓝 | 深蓝灰 |
| `dark` | 黑橙 | 近黑 | 深灰黑 | 橙 → 浅橙 | 暖白 |

- 切换只覆盖令牌：`html[data-theme="dark"]` 重定义同名变量，组件样式一行不改。
- 两套主题的令牌键必须完全一致（`validate.py --style-only` 校验）。
- 插图颜色**不随主题变化**：深色主题下插图仍是浅底，这是预期效果。

---

## 2. 令牌分组

| 组 | 令牌 | 用途 |
|---|---|---|
| 基底 | `--bg` `--surface` `--surface-2` `--text` `--text-mute` `--border` | 页面/卡片/次要文字/描边 |
| 强调 | `--accent` `--accent-2` `--link` `--on-accent` | h2/h3、链接、按钮文字 |
| 头图 | `--header-a` `--header-b` `--on-header` | 渐变起止 + 其上的文字 |
| 表格 | `--th-bg` `--th-text` `--row-hover` `--row-zebra` | 表头、hover、斑马纹 |
| 代码 | `--code-bg` `--code-text` | 代码块 |
| 提示 | `--tip-bg` `--warn-bg` `--warn-border` `--key-bg` `--key-border` | 三类提示框 |
| 页脚 | `--footer-bg` `--footer-text` | 页脚 |
| 徽章 | `--badge-bg` `--badge-ink` `--badge-2-*` `--badge-3-*` | 复杂度/标签 |
| 尺度 | `--radius` `--radius-sm` `--shadow` `--shadow-hover` `--focus` | 圆角、阴影、焦点环 |

### 对比度契约（`contrast.json`，脚本逐项计算）

| 组合 | 最低 |
|---|---|
| 正文 / 卡片底、正文 / 页面底 | 7.0 |
| 次要文字、链接、h2/h3 强调色 | 4.5 |
| 头图文字 / 渐变两端 | 4.5 |
| 悬浮按钮图标 / 渐变终点 | 3.0 |
| 表头、代码、页脚、徽章 | 4.5 |

改色后必须跑：

```bash
python scripts/validate.py --style-only blue-ink
```

---

## 3. 版式尺度

| 元素 | 规格 |
|---|---|
| 正文容器 | `max-width: 1120px`，左右 20px（移动端 14px） |
| 头图 | 上下 2.8rem，渐变，底部圆角，轻微径向高光 |
| 小节卡片 | 白底、1px 边框、左侧 6px 强调条、`padding: 2.2rem` |
| h1 | `clamp(1.9rem, 4.2vw, 2.9rem)` |
| h2 | `clamp(1.4rem, 2.4vw, 1.75rem)`，前置 26px 图标，底部细线 |
| h3 | 1.22rem |
| 正文 | 16px / 行高 1.75，两端对齐 |
| 代码 | 0.92rem 等宽，横向滚动 |
| 表格 | 0.98rem，`min-width: 560px` |

尺度令牌不随主题变化，但为满足"键一致"契约，深色块里也同步声明了 `--radius` / `--radius-sm`。

---

## 4. 正文页结构

```html
<header class="chapter-header">
  <p class="kicker">《课程名》第 N 讲 · 共 M 讲</p>
  <h1>讲标题</h1>
  <p class="subtitle">关键词摘要</p>
</header>
<main class="container">
  <section>…</section>   <!-- 4~6 个 -->
  <nav class="pager">上一讲 / 课程目录 / 下一讲</nav>
</main>
<footer>
  <p class="footer-brand">品牌 · 口号</p>
  <p class="footer-author">作者：…</p>
  <p>课程名 · 共 N 讲 · 年份</p>
  <p>第 N 讲：标题</p>
</footer>
<div class="fab-menu">返回目录 / 主题切换 / 回到顶部</div>
```

要点：

- `h1` 只能是讲标题，**不能**用课程名（这是提取语料时最常见的错误）。
- `kicker`、页脚、翻页里的讲次由模板占位符生成，`renumber.py` 负责全量同步。
- 页脚品牌 / 作者 / 口号分别来自 manifest 的 `brand` / `author` / `slogan`；作者行固定是
  `<p class="footer-author">作者：…</p>`，不要逐页手写。
- 每页恰好两段内联脚本：`<head>` 里的主题初始化、`</body>` 前的交互。

---

## 5. 组件清单

所有片段可从 `markup-cookbook.md` 直接复制。

| 组件 | 类名 | 用途 |
|---|---|---|
| 小节 | `section` + `h2` + `.h2-icon` | 内容主块 |
| 表格 | `.table-wrap > table` | 对比 / 选型 / 指标 |
| 代码 | `.code-block > pre > code` | 可运行片段 |
| 插图 | `.svg-container > svg` + `.fig-caption` | 结构 / 流程 / 对照 |
| 提示 | `.tip-box` / `.warning-box` / `.key-point` | 实践 / 陷阱 / 结论 |
| 网格 | `.grid > .card` | 并列概念 |
| 时间线 | `.timeline > .timeline-item` | 演进 / 步骤 |
| 对照 | `.comparison > div` | A/B 方案 |
| 徽章 | `.badge` / `.complexity-badge` | 复杂度 / 标签 |
| 页脚 | `footer` / `.footer-brand` / `.footer-author` | 品牌 / 口号 / 作者 / 课程信息 |
| 翻页 | `.pager > .pager-link` | 上一讲 / 目录 / 下一讲 |
| 悬浮菜单 | `.fab-menu > .fab-btn` | 工具按钮 |

---

## 6. 主题机制

### 6.1 初始化（`<head>`，防闪白）

```html
<script>
(function () {
  var t;
  try { t = localStorage.getItem('doc-theme'); } catch (e) {}
  if (!t) {
    t = (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches)
      ? 'dark' : 'light';
  }
  document.documentElement.setAttribute('data-theme', t);
})();
</script>
```

### 6.2 交互（`</body>` 前）

- 点击 `#theme-toggle`：切换 `data-theme`、写 `localStorage`、更新 `aria-pressed`
- 点击 `#back-to-top`：`window.scrollTo({ top: 0, behavior: 'smooth' })`
- `localStorage` 读写必须 `try/catch`（`file://` 下可能被禁用）
- 少数浏览器在 `file://` 下不持久化主题，翻页会回到默认主题；这是浏览器限制，可接受，或用任意静态服务器打开

### 6.3 三条铁律

1. 组件颜色只用 `var(--xxx)`，不写裸色值。
2. SVG 内部只用字面量 hex，不用 `var()`。
3. 不给 `svg` 加 `filter: invert()` 或覆盖 `fill` 的规则。

`validate.py` 会扫描裸色值、SVG 内 `var()`、`filter` 属性。

---

## 7. 插图规则

- 统一 `viewBox="0 0 800 300"`（竖向流程可 800×360），`width="100%"`，由容器控制缩放。
- 每张图必须：
  - 包在 `.svg-container` 内；
  - 有 `role="img"` + `aria-label`，或一个 `<title>`；
  - 图内有中文标题；必要时下方加 `.fig-caption` 说明"图 N：…"。
- 配色用固定字面量：`#2F6FB3` 蓝、`#4CAF50` 绿、`#F5A623` 橙、`#C2410C` 深橙、`#D0021B` 红、`#9C27B0` 紫；文字 `#1F2D3D`，浅底 `#F5F9FF`。
- 深色主题下插图保持浅底，不要试图改成深色——那会破坏"插图恒定"的一致性。
- 同一页多个 SVG 的 `marker id` 必须唯一（`arrow-fs`、`arrow-flow`…）。

---

## 8. 目录页

```html
<header class="index-header">  <!-- 火箭图标 + 课程名 + 副标题 + 共 N 讲 -->
<section class="directory-intro">  <!-- 课程说明 -->
<section class="stage">            <!-- 每个阶段一组 -->
  <h2 class="stage-title"><span class="stage-index">01</span>基础认知</h2>
  <div class="chapters">
    <article class="chapter-card">
      <div class="chapter-number">01</div>
      <h3>标题</h3>
      <p class="chapter-meta">进阶 · 45 分钟</p>   <!-- 可选：manifest 里有难度/时长才出现 -->
      <p class="chapter-content">摘要</p>
      <a class="chapter-link" href="01.html">开始学习 →</a>
    </article>
  </div>
</section>
<footer>品牌 · 课程名 · 共 N 讲</footer>
```

- 卡片按 `manifest` 里的 `stage` 分组，连续同名阶段自动合并。
- 卡片序号、标题、摘要、链接全部由 manifest 渲染，禁止手改。
- 目录页只有两个悬浮按钮（主题 + 回到顶部）。

---

## 9. 响应式

断点 `768px`：

- 容器与小节内边距收窄；头图字号降到 2rem 级。
- `.chapters`、`.comparison` 变单列；`.pager` 变纵向。
- **插图不缩字**：`.svg-container` 横向滚动，`svg` 保持 `min-width: 560px`，避免 800 宽的图在手机上把 16px 文字缩成 7px。
- **表格不挤压**：`.table-wrap` 横向滚动，`table` 保持 `min-width: 560px`。
- 悬浮按钮 42px，右下 12px。

---

## 10. 无障碍

- 所有可交互元素有 `:focus-visible` 焦点环（`--focus`）。
- 主题按钮有 `aria-label` 与 `aria-pressed`；纯装饰 SVG 加 `aria-hidden="true"`。
- 内容插图有可读名称（`role="img"` + `aria-label` 或 `<title>`）。
- 尊重 `prefers-reduced-motion`：关闭过渡与平滑滚动。
- 文字对比度见 §2 契约；图标类控件最低 3:1。

---

## 11. 打印

`@media print` 已内置：

- 隐藏悬浮菜单与翻页；
- 头图、页面底强制浅色，避免深色主题打印出黑底；
- 去掉阴影，保留表格边框；
- `@page` 边距 14mm。

需要 PDF 时用浏览器"打印 → 另存为 PDF"，不要用截图。

---

## 12. 一致性红线

- 同一套文档只用一个风格包；不要在某一讲里局部覆盖颜色。
- 圆角、阴影、间距、字号全部来自令牌；新增值先进 `tokens.css`。
- 只允许 hover 位移与主题过渡，不加自动播放动画。
- 图标一律内联 SVG，禁止 Font Awesome / CDN / 外链图片。
- 页面 `<style>` 由脚本注入，不手改；要改样式改 `styles/<pack>/`。

---

## 13. 排查

| 现象 | 检查 |
|---|---|
| 切换主题没反应 | 是否有 `html[data-theme="dark"]` 块；组件是否用了裸色值 |
| 刷新后回到浅色 | 初始化脚本是否在 `<head>`；`localStorage` 是否被禁用 |
| 插图变暗 | SVG 内是否有 `var()`；是否给 svg 加了 filter |
| 手机上字糊成一团 | 是否漏了 `.svg-container` 的横向滚动 |
| 表格右边被裁 | 是否漏了 `.table-wrap` |
| 深色下表头刺眼 | `--th-bg` / `--th-text` 是否成对改 |
| 打印是黑底 | 是否删掉了 `@media print` 覆盖 |
