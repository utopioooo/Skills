# 组件片段手册

填正文时直接从本文件复制，改文字即可。所有片段与 `components.css` 的类名一一对应。
占位内容用 `…` 表示，交付前必须替换。

---

## 1. 小节骨架

```html
<section>
    <h2><svg class="h2-icon" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M9.4 16.6L4.8 12l4.6-4.6L8 6l-6 6 6 6 1.4-1.4zm5.2 0l4.6-4.6-4.6-4.6L16 6l6 6-6 6-1.4-1.4z"/></svg>一、小节标题</h2>

    <p>第一句给结论：…。后续解释机制：…。</p>

    <!-- 至少放一种载体：代码 / 表格 / SVG / 列表 -->
</section>
```

h2 图标可换，但同一页不要重复太多；`引言` 与 `总结` 可以不带图标。

---

## 2. 段落、强调、行内代码

```html
<p>关键判断用 <span class="highlight">行内强调</span>，术语用 <span class="keyword">cache line</span>，
API 名用 <code>std::vector</code>。一段最多 2~3 处，多了反而没有重点。</p>
```

---

## 3. 表格（必须包 `.table-wrap`）

```html
<div class="table-wrap">
    <table>
        <thead>
            <tr><th>方案</th><th>机制</th><th>适用场景</th></tr>
        </thead>
        <tbody>
            <tr><td><strong>方案 A</strong></td><td>…</td><td>…</td></tr>
            <tr><td><strong>方案 B</strong></td><td>…</td><td>…</td></tr>
        </tbody>
    </table>
</div>
```

3~6 行、2~4 列；首列加 `<strong>`；单元格写短语。

---

## 4. 代码块（尖括号必须转义）

```html
<div class="code-block">
<pre><code>#include &lt;vector&gt;

std::vector&lt;int&gt; make_buffer(std::size_t n) {
    std::vector&lt;int&gt; data;
    data.reserve(n);      // 预分配，避免多次扩容
    return data;
}</code></pre>
</div>
```

- `<` → `&lt;`，`>` → `&gt;`，`&` → `&amp;`；行内 `<code>` 与正文同理，
  `std::vector<int>` 不转义会丢掉 `<int>`。
- 15~40 行；超出用 `// ... 省略非关键部分`。

---

## 5. 插图（必须包 `.svg-container`）

```html
<div class="svg-container">
    <svg viewBox="0 0 800 300" role="img" aria-label="一句话描述这张图表达的结构或流向">
        <title>图内的中文标题</title>
        <rect x="0" y="0" width="800" height="300" fill="#F5F9FF" rx="10"/>
        <text x="400" y="36" text-anchor="middle" font-size="19" font-weight="bold" fill="#1F2D3D">中文标题</text>

        <!-- 结构、流程或对照；颜色用字面量，禁止 var() -->
    </svg>
</div>
<p class="fig-caption">图 1：一句话说明这张图在讲什么。</p>
```

- 一张图只表达一件事；画不出信息就删掉。
- 同一页多个 SVG，marker id 必须唯一（`arrow-fs`、`arrow-flow`…）。
- 详细模式见 `svg-patterns.md`。

---

## 6. 提示框

```html
<div class="tip-box">
    <strong>最佳实践：</strong>给出具体参数或准则，例如缓冲区取 4 KB 的整数倍。
</div>

<div class="warning-box">
    <strong>陷阱：</strong>写出误用方式与后果，不要只说“注意”。
</div>

<div class="key-point">
    <strong>结论：</strong>本节最重要的一句话。
</div>
```

---

## 7. 并列卡片

```html
<div class="grid">
    <div class="card">
        <h3>场景 A</h3>
        <p>…</p>
    </div>
    <div class="card">
        <h3>场景 B</h3>
        <p>…</p>
    </div>
</div>
```

3~6 个；每个卡片一段话，不要塞代码。

---

## 8. 时间线

```html
<div class="timeline">
    <div class="timeline-item">
        <h3>C++11</h3>
        <p>引入移动语义与 <code>constexpr</code>。</p>
    </div>
    <div class="timeline-item">
        <h3>C++17</h3>
        <p>…</p>
    </div>
</div>
```

用于版本演进、标准迭代、固定步骤链。

---

## 9. 双栏对照

```html
<div class="comparison">
    <div>
        <h3>朴素写法</h3>
        <p>…</p>
    </div>
    <div>
        <h3>优化写法</h3>
        <p>…</p>
    </div>
</div>
```

两侧都要有内容，不要一边空着。

---

## 10. 徽章

```html
<p>查找 <span class="badge">O(1)</span>，有序检索 <span class="badge info">O(log n)</span>，
遍历 <span class="badge warn">O(n)</span>。</p>
```

---

## 11. 交叉引用

```html
<p>无锁队列的内存回收见 <a href="07.html" data-ref="7">第 7 讲</a>。</p>
```

- `data-ref` = 目标讲次编号；`href` = 目标文件；正文写「第 N 讲」。
- 三处不一致会被 validate 判错；`renumber.py` 会自动同步。

---

## 12. 不要手改的部分

以下由模板与脚本生成，改了会被校验或重编号覆盖：

| 区域 | 维护方式 |
|---|---|
| `<head>` 的 `<style>` | 改 `styles/<pack>/tokens.css` / `components.css` |
| `<head>` 主题初始化脚本 | 不要动 |
| `header.chapter-header` 的 kicker | `renumber.py` |
| `nav.pager` | `renumber.py` |
| `footer`（品牌 / 作者 / 口号 / 共 N 讲 / 年份） | `renumber.py`；源数据在 manifest |
| `.fab-menu` | 不要动 |
| `index.html` 的卡片 | `scaffold.py --index-only` |

---

## 13. 保存前自查

- [ ] 每个 `<section>` 至少一种载体，没有空节
- [ ] 代码块数量 2~6，尖括号已转义
- [ ] 表格 1~3 张，都包了 `.table-wrap`
- [ ] 插图 1~6 张，都包了 `.svg-container`，有标题/说明
- [ ] 小节 4~6 个，编号风格与全书一致
- [ ] 没有 `TODO`、`{{…}}`、"待补充"
- [ ] 任意位置（含行内 `<code>`）都没有未转义的 `<`
- [ ] 跑 `python scripts/validate.py --file <本页>`（自动读取同目录 manifest 的风格包）
