# 手写 SVG 图表示例

所有图表必须内联，禁止外链图片、禁止图表库。五种模式覆盖课程里绝大多数需求：
分层架构、横向流程、左右对照、并列生态、决策树。

---

## 通用约定

- 外层：`<div class="svg-container">`，图下可跟 `<p class="fig-caption">图 N：…</p>`。
- 画布：`viewBox="0 0 800 300"`（竖向流程可 `0 0 800 360`），`width="100%"`，不要写死 px 宽度。
- 每个 `<svg>` 必须有 `role="img"` + `aria-label`，或一个 `<title>`；两者都有更好。
- 背景：`<rect x="0" y="0" width="800" height="300" fill="#F5F9FF" rx="10"/>`。
- 图内必须有中文标题，居中，字号 18~20，`font-weight="bold"`。
- 圆角矩形 `rx="6"~"10"`，描边 `stroke-width="2"`。
- 连线：实线=直接调用/数据流；虚线 `stroke-dasharray="6,5"`=间接/映射关系。
- 箭头 marker 的 `id` **全页唯一**：`arrow-arch`、`arrow-flow`、`arrow-tree`…
- 文字每行不超过 14 个汉字；字号不小于 13；长术语换行用 `<tspan x="…" dy="16">`。
- 颜色全部写**字面量 hex**，禁止 `var()`；深色主题下插图保持浅底，这是预期。
- 同一张图里色块不超过 5 种，颜色要对应语义（蓝=主体，绿=正向，橙=注意，红=危险，紫=辅助）。
- 深色块配白字时，底色对比度必须 ≥4.5：`#2F6FB3`（5.19）、`#2E7D32`（5.13）、`#A35A00`（5.22）、`#C2410C`（5.18）、`#9C27B0`（6.30）都达标；亮绿 `#4CAF50`（2.78）和亮橙 `#F5A623`（2.03）**只能配深色字或只作描边**。

### 图表色板

| 用途 | 色值 |
|---|---|
| 主色块 / 主流程 | `#2F6FB3` |
| 正向 / 优化后 | `#2E7D32`（配白字；`#4CAF50` 只作浅底描边） |
| 注意 / 中间态 | `#A35A00`（配白字；`#F5A623` 只作浅底描边或配深色字） |
| 深橙 / 对照 | `#C2410C` |
| 危险 / 反例 | `#D0021B` |
| 辅助 | `#9C27B0` |
| 浅底 A | `#F5F9FF` |
| 浅底 B | `#FFF3E0` |
| 深色文字 | `#1F2D3D` |
| 次要文字 | `#5A6B7C` |

---

## 模式一：分层架构图（最常用）

```html
<div class="svg-container">
<svg viewBox="0 0 800 300" role="img" aria-label="三层系统架构：底层硬件、中间运行时、上层应用">
    <title>系统分层架构</title>
    <rect x="0" y="0" width="800" height="300" fill="#F5F9FF" rx="10"/>
    <text x="400" y="34" text-anchor="middle" font-size="19" font-weight="bold" fill="#1F2D3D">系统分层架构</text>

    <rect x="60" y="64" width="680" height="58" rx="8" fill="#E3F2FD" stroke="#2F6FB3" stroke-width="2"/>
    <text x="400" y="99" text-anchor="middle" font-size="16" fill="#1F2D3D">上层：游戏引擎 / 交易系统 / 数据库</text>

    <rect x="100" y="136" width="600" height="58" rx="8" fill="#FFF3E0" stroke="#F5A623" stroke-width="2"/>
    <text x="400" y="171" text-anchor="middle" font-size="16" fill="#1F2D3D">中间层：内存管理、并发原语、无锁结构</text>

    <rect x="140" y="208" width="520" height="58" rx="8" fill="#E8F5E9" stroke="#4CAF50" stroke-width="2"/>
    <text x="400" y="243" text-anchor="middle" font-size="16" fill="#1F2D3D">底层：CPU Cache、SIMD、NUMA</text>

    <line x1="400" y1="122" x2="400" y2="136" stroke="#5A6B7C" stroke-width="2" marker-end="url(#arrow-arch)"/>
    <line x1="400" y1="194" x2="400" y2="208" stroke="#5A6B7C" stroke-width="2" marker-end="url(#arrow-arch)"/>

    <defs>
        <marker id="arrow-arch" markerWidth="10" markerHeight="10" refX="9" refY="3"
                orient="auto" markerUnits="strokeWidth">
            <path d="M0,0 L0,6 L9,3 z" fill="#5A6B7C"/>
        </marker>
    </defs>
</svg>
</div>
```

---

## 模式二：横向流程管道

```html
<div class="svg-container">
<svg viewBox="0 0 800 300" role="img" aria-label="数据处理管道：采集、清洗、聚合、输出">
    <title>实时数据处理管道</title>
    <rect x="0" y="0" width="800" height="300" fill="#F5F9FF" rx="10"/>
    <text x="400" y="34" text-anchor="middle" font-size="19" font-weight="bold" fill="#1F2D3D">实时数据处理管道</text>

    <rect x="40"  y="104" width="140" height="62" rx="8" fill="#2F6FB3" stroke="#1C5A9E" stroke-width="2"/>
    <text x="110" y="141" text-anchor="middle" fill="#FFFFFF" font-size="16" font-weight="bold">数据采集</text>

    <rect x="230" y="104" width="140" height="62" rx="8" fill="#2E7D32" stroke="#2E7D32" stroke-width="2"/>
    <text x="300" y="141" text-anchor="middle" fill="#FFFFFF" font-size="16" font-weight="bold">解析清洗</text>

    <rect x="420" y="104" width="140" height="62" rx="8" fill="#A35A00" stroke="#B26A00" stroke-width="2"/>
    <text x="490" y="141" text-anchor="middle" fill="#FFFFFF" font-size="16" font-weight="bold">窗口聚合</text>

    <rect x="610" y="104" width="140" height="62" rx="8" fill="#9C27B0" stroke="#6A1B9A" stroke-width="2"/>
    <text x="680" y="141" text-anchor="middle" fill="#FFFFFF" font-size="16" font-weight="bold">结果输出</text>

    <line x1="180" y1="135" x2="230" y2="135" stroke="#5A6B7C" stroke-width="2" marker-end="url(#arrow-flow)"/>
    <line x1="370" y1="135" x2="420" y2="135" stroke="#5A6B7C" stroke-width="2" marker-end="url(#arrow-flow)"/>
    <line x1="560" y1="135" x2="610" y2="135" stroke="#5A6B7C" stroke-width="2" marker-end="url(#arrow-flow)"/>

    <text x="110" y="196" text-anchor="middle" font-size="13" fill="#5A6B7C">Kafka / Socket</text>
    <text x="680" y="196" text-anchor="middle" font-size="13" fill="#5A6B7C">DB / MQ</text>

    <defs>
        <marker id="arrow-flow" markerWidth="10" markerHeight="10" refX="9" refY="3"
                orient="auto" markerUnits="strokeWidth">
            <path d="M0,0 L0,6 L9,3 z" fill="#5A6B7C"/>
        </marker>
    </defs>
</svg>
</div>
```

拐弯连线用 `<polyline points="410,80 410,110 350,110" stroke="#5A6B7C" stroke-width="2" fill="none"/>`。

---

## 模式三：左右对照（用户态/内核态、朴素/优化）

画布统一 800×300，左右各 320 宽，中间留 80 给箭头与说明。

```html
<div class="svg-container">
<svg viewBox="0 0 800 300" role="img" aria-label="用户态与内核态之间的数据拷贝对比">
    <title>用户态与内核态的数据路径</title>
    <rect x="0" y="0" width="800" height="300" fill="#F5F9FF" rx="10"/>
    <text x="400" y="34" text-anchor="middle" font-size="19" font-weight="bold" fill="#1F2D3D">用户态与内核态的数据路径</text>

    <rect x="50" y="70" width="300" height="170" rx="8" fill="#E3F2FD" stroke="#2F6FB3" stroke-width="2"/>
    <text x="200" y="102" text-anchor="middle" font-size="16" font-weight="bold" fill="#1F2D3D">用户态</text>
    <text x="200" y="140" text-anchor="middle" font-size="14" fill="#1F2D3D">应用缓冲区</text>
    <text x="200" y="170" text-anchor="middle" font-size="13" fill="#5A6B7C">read() / write()</text>

    <rect x="450" y="70" width="300" height="170" rx="8" fill="#FFF3E0" stroke="#F5A623" stroke-width="2"/>
    <text x="600" y="102" text-anchor="middle" font-size="16" font-weight="bold" fill="#1F2D3D">内核态</text>
    <text x="600" y="140" text-anchor="middle" font-size="14" fill="#1F2D3D">页缓存 / 磁盘</text>
    <text x="600" y="170" text-anchor="middle" font-size="13" fill="#5A6B7C">一次系统调用</text>

    <line x1="350" y1="155" x2="450" y2="155" stroke="#C2410C" stroke-width="2"
          stroke-dasharray="6,5" marker-end="url(#arrow-side)"/>
    <text x="400" y="140" text-anchor="middle" font-size="13" fill="#C2410C">拷贝</text>

    <defs>
        <marker id="arrow-side" markerWidth="10" markerHeight="10" refX="9" refY="3"
                orient="auto" markerUnits="strokeWidth">
            <path d="M0,0 L0,6 L9,3 z" fill="#C2410C"/>
        </marker>
    </defs>
</svg>
</div>
```

---

## 模式四：并列生态（4 个一组）

```html
<div class="svg-container">
<svg viewBox="0 0 800 300" role="img" aria-label="性能工具生态：编译期分析、运行时剖析、内存分析、基准测试">
    <title>性能工具生态</title>
    <rect x="0" y="0" width="800" height="300" fill="#F5F9FF" rx="10"/>
    <text x="400" y="34" text-anchor="middle" font-size="19" font-weight="bold" fill="#1F2D3D">性能工具生态</text>

    <circle cx="150" cy="140" r="48" fill="#2F6FB3"/>
    <text x="150" y="136" text-anchor="middle" fill="#FFFFFF" font-size="15" font-weight="bold">编译期</text>
    <text x="150" y="158" text-anchor="middle" fill="#FFFFFF" font-size="14">分析</text>
    <text x="150" y="212" text-anchor="middle" font-size="13" fill="#5A6B7C">-Wall -Wextra</text>

    <circle cx="316" cy="140" r="48" fill="#2E7D32"/>
    <text x="316" y="136" text-anchor="middle" fill="#FFFFFF" font-size="15" font-weight="bold">运行时</text>
    <text x="316" y="158" text-anchor="middle" fill="#FFFFFF" font-size="14">剖析</text>
    <text x="316" y="212" text-anchor="middle" font-size="13" fill="#5A6B7C">perf / VTune</text>

    <circle cx="482" cy="140" r="48" fill="#A35A00"/>
    <text x="482" y="136" text-anchor="middle" fill="#FFFFFF" font-size="15" font-weight="bold">内存</text>
    <text x="482" y="158" text-anchor="middle" fill="#FFFFFF" font-size="14">分析</text>
    <text x="482" y="212" text-anchor="middle" font-size="13" fill="#5A6B7C">Valgrind</text>

    <circle cx="648" cy="140" r="48" fill="#9C27B0"/>
    <text x="648" y="136" text-anchor="middle" fill="#FFFFFF" font-size="15" font-weight="bold">基准</text>
    <text x="648" y="158" text-anchor="middle" fill="#FFFFFF" font-size="14">测试</text>
    <text x="648" y="212" text-anchor="middle" font-size="13" fill="#5A6B7C">Google Benchmark</text>
</svg>
</div>
```

换行用 `<tspan x="…" dy="16">`，SVG 不支持 `<br>`。

---

## 模式五：决策树 / 流程树

```html
<div class="svg-container">
<svg viewBox="0 0 800 300" role="img" aria-label="容器选择决策：需要随机访问选 vector，否则选 list">
    <title>容器选择决策</title>
    <rect x="0" y="0" width="800" height="300" fill="#F5F9FF" rx="10"/>
    <text x="400" y="34" text-anchor="middle" font-size="19" font-weight="bold" fill="#1F2D3D">容器选择决策</text>

    <rect x="310" y="56" width="180" height="48" rx="8" fill="#2F6FB3" stroke="#1C5A9E" stroke-width="2"/>
    <text x="400" y="86" text-anchor="middle" fill="#FFFFFF" font-size="15" font-weight="bold">需要随机访问？</text>

    <line x1="400" y1="104" x2="220" y2="140" stroke="#5A6B7C" stroke-width="2" marker-end="url(#arrow-tree)"/>
    <line x1="400" y1="104" x2="580" y2="140" stroke="#5A6B7C" stroke-width="2" marker-end="url(#arrow-tree)"/>
    <text x="286" y="128" font-size="13" fill="#5A6B7C">是</text>
    <text x="506" y="128" font-size="13" fill="#5A6B7C">否</text>

    <rect x="120" y="148" width="200" height="48" rx="8" fill="#2E7D32" stroke="#2E7D32" stroke-width="2"/>
    <text x="220" y="178" text-anchor="middle" fill="#FFFFFF" font-size="15" font-weight="bold">vector / deque</text>

    <rect x="480" y="148" width="200" height="48" rx="8" fill="#A35A00" stroke="#B26A00" stroke-width="2"/>
    <text x="580" y="178" text-anchor="middle" fill="#FFFFFF" font-size="15" font-weight="bold">list / forward_list</text>

    <line x1="220" y1="196" x2="220" y2="232" stroke="#5A6B7C" stroke-width="2" marker-end="url(#arrow-tree)"/>
    <rect x="110" y="240" width="220" height="42" rx="8" fill="#E3F2FD" stroke="#2F6FB3" stroke-width="2"/>
    <text x="220" y="267" text-anchor="middle" font-size="14" fill="#1F2D3D">关注缓存局部性</text>

    <defs>
        <marker id="arrow-tree" markerWidth="10" markerHeight="10" refX="9" refY="3"
                orient="auto" markerUnits="strokeWidth">
            <path d="M0,0 L0,6 L9,3 z" fill="#5A6B7C"/>
        </marker>
    </defs>
</svg>
</div>
```

---

## 内联图标（替代 Font Awesome）

24×24 `viewBox`，Material Icons 风格：

```html
<!-- 信息 -->
<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/></svg>
<!-- 代码 -->
<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M9.4 16.6L4.8 12l4.6-4.6L8 6l-6 6 6 6 1.4-1.4zm5.2 0l4.6-4.6-4.6-4.6L16 6l6 6-6 6-1.4-1.4z"/></svg>
<!-- 分层 -->
<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 2l-9 7 9 13 9-13-9-7zm0 3.5l5 3.9-5 7.2-5-7.2 5-3.9z"/></svg>
<!-- 列表 -->
<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M3 13h2v-2H3v2zm0 4h2v-2H3v2zm0-8h2V7H3v2zm4 4h14v-2H7v2zm0 4h14v-2H7v2zM7 7v2h14V7H7z"/></svg>
<!-- 完成 -->
<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>
```

装饰性图标一律 `aria-hidden="true"`。

---

## 自检

- [ ] `viewBox="0 0 800 300"`，`width="100%"`，包在 `.svg-container` 内
- [ ] 有 `role="img"` + `aria-label`，或 `<title>`
- [ ] 图内有中文标题
- [ ] 所有 `fill`/`stroke` 是字面量 hex，没有 `var()`
- [ ] 同一页 marker id 不重复
- [ ] 文字不溢出：每行 ≤14 汉字、字号 ≥13
- [ ] 深底白字 / 浅底深字，没有撞色；深底白字对比度 ≥4.5
- [ ] 缩放后仍能读懂（不依赖 1px 细节）
