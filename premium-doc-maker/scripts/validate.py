#!/usr/bin/env python3
"""验收脚本：把"精品文档"的硬性约束变成可执行检查。

用法：
    python scripts/validate.py --dir ./out
    python scripts/validate.py --file ./examples/golden/01.html
    python scripts/validate.py --style-only blue-ink
    python scripts/validate.py --dir ./out --strict     # 警告也视为失败
    python scripts/validate.py --dir ./out --json

退出码：0 全部通过；1 有错误（--strict 下警告也算错误）；2 参数/环境错误。
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _common as C

VOID = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}

# 允许出现的标签白名单。解析器遇到白名单外的标签，几乎一定是未转义的尖括号
# （例如 <code>std::vector<int></code> 里的 <int>），浏览器会把这段文字吞掉。
KNOWN_TAGS = {
    "html", "head", "body", "meta", "title", "style", "script", "link", "base",
    "header", "main", "section", "article", "nav", "footer", "aside", "div",
    "span", "p", "h1", "h2", "h3", "h4", "h5", "h6", "a", "img", "picture",
    "figure", "figcaption", "ul", "ol", "li", "dl", "dt", "dd", "table",
    "caption", "thead", "tbody", "tfoot", "tr", "th", "td", "col", "colgroup",
    "pre", "code", "kbd", "samp", "var", "br", "hr", "wbr", "strong", "em",
    "b", "i", "u", "s", "del", "ins", "mark", "small", "sub", "sup", "abbr",
    "cite", "q", "blockquote", "time", "details", "summary", "button",
    "input", "label", "form", "fieldset", "legend", "select", "option",
    "textarea", "video", "audio", "source", "track", "iframe", "object",
    "embed", "canvas", "template", "noscript",
    # SVG
    "svg", "g", "defs", "symbol", "use", "path", "rect", "circle", "ellipse",
    "line", "polyline", "polygon", "text", "tspan", "textpath", "desc",
    "marker", "pattern", "clippath", "mask", "lineargradient", "radialgradient",
    "stop", "filter", "fegaussianblur", "feoffset", "femerge", "femergenode",
    "feblend", "fecolormatrix", "image", "switch", "foreignobject",
    "animate", "animatetransform", "set",
}

CN_NUM = r"[一二三四五六七八九十]+、"
AR_NUM = r"\d+\s*[.、)]"

# 允许出现的"省略"写法（content-blueprint.md 规定）
ALLOWED_ELLIPSIS = "省略非关键部分"

CARRIER_TAGS = {"p", "pre", "table", "svg", "ul", "ol", "blockquote"}
CARRIER_CLASSES = {
    "tip-box", "warning-box", "key-point", "grid", "card",
    "comparison", "timeline", "code-block", "table-wrap", "svg-container",
}


# --------------------------------------------------------------------------- 基础工具


REQUIRED_CHAPTER_PLACEHOLDERS = [
    "{{STYLE_CSS}}", "{{TITLE}}", "{{SUMMARY}}", "{{SUMMARY_ATTR}}", "{{COURSE}}",
    "{{BRAND}}", "{{AUTHOR}}", "{{SLOGAN}}", "{{YEAR}}", "{{N}}", "{{TOTAL}}",
    "{{SECTIONS}}", "{{PREV_LINK}}", "{{NEXT_LINK}}",
]
REQUIRED_INDEX_PLACEHOLDERS = [
    "{{STYLE_CSS}}", "{{COURSE}}", "{{SUBTITLE}}", "{{SUBTITLE_ATTR}}",
    "{{BRAND}}", "{{AUTHOR}}", "{{SLOGAN}}", "{{YEAR}}", "{{TOTAL}}",
    "{{STAGE_GROUPS}}",
]
REQUIRED_CLASSES = [
    "chapter-header", "kicker", "subtitle", "container", "table-wrap",
    "code-block", "svg-container", "fig-caption", "tip-box", "warning-box",
    "key-point", "grid", "card", "timeline", "badge", "comparison",
    "pager", "pager-link", "fab-menu", "fab-btn", "index-header",
    "directory-intro", "stage", "stage-title", "chapters", "chapter-card",
    "chapter-number", "chapter-content", "chapter-meta", "chapter-link",
    "h2-icon", "highlight", "keyword", "complexity-badge", "footer-brand",
    "footer-author", "course-icon",
]
REQUIRED_TOKENS = [
    "--bg", "--surface", "--surface-2", "--text", "--text-mute", "--border",
    "--accent", "--accent-2", "--link", "--on-accent",
    "--header-a", "--header-b", "--on-header",
    "--th-bg", "--th-text", "--row-hover", "--row-zebra",
    "--code-bg", "--code-text",
    "--tip-bg", "--warn-bg", "--warn-border", "--key-bg", "--key-border",
    "--footer-bg", "--footer-text",
    "--badge-bg", "--badge-ink", "--badge-2-bg", "--badge-2-ink",
    "--badge-3-bg", "--badge-3-ink",
    "--radius", "--radius-sm", "--shadow", "--shadow-hover", "--focus",
]


class Issue:
    __slots__ = ("level", "file", "line", "msg")

    def __init__(self, level, file, line, msg):
        self.level = level
        self.file = file
        self.line = line
        self.msg = msg


class Report:
    def __init__(self):
        self.items: list[Issue] = []

    def add(self, level, file, line, msg):
        self.items.append(Issue(level, file, line, msg))

    def error(self, file, line, msg):
        self.add("ERROR", file, line, msg)

    def warn(self, file, line, msg):
        self.add("WARN", file, line, msg)

    @property
    def errors(self):
        return [i for i in self.items if i.level == "ERROR"]

    @property
    def warnings(self):
        return [i for i in self.items if i.level == "WARN"]

    def dump(self, as_json: bool, strict: bool):
        if as_json:
            print(json.dumps(
                {
                    "errors": [i.__dict__ for i in self.errors],
                    "warnings": [i.__dict__ for i in self.warnings],
                },
                ensure_ascii=False, indent=2,
            ))
            return

        files = sorted({i.file for i in self.items})
        for f in files:
            print(f"\n{f}")
            for issue in self.items:
                if issue.file != f:
                    continue
                loc = f":{issue.line}" if issue.line else ""
                print(f"  {issue.level:<5} {f}{loc}  {issue.msg}")

        print(f"\n汇总：错误 {len(self.errors)}，警告 {len(self.warnings)}")


class Node:
    __slots__ = ("tag", "attrs", "children", "parent", "line")

    def __init__(self, tag="", attrs=None, line=0):
        self.tag = tag
        self.attrs = attrs or {}
        self.children = []
        self.parent = None
        self.line = line

    def add(self, child):
        child.parent = self
        self.children.append(child)

    def classes(self):
        return set(self.attrs.get("class", "").split())

    def text(self):
        parts = []
        for child in self.children:
            parts.append(child if isinstance(child, str) else child.text())
        return "".join(parts)

    def walk(self):
        for child in self.children:
            if isinstance(child, str):
                continue
            yield child
            yield from child.walk()

    def find_all(self, tag=None, cls=None):
        for node in self.walk():
            if tag and node.tag != tag:
                continue
            if cls and cls not in node.classes():
                continue
            yield node

    def find(self, tag=None, cls=None):
        return next(self.find_all(tag, cls), None)

    def ancestor(self, cls):
        node = self.parent
        while node is not None:
            if cls in node.classes():
                return node
            node = node.parent
        return None

    def ancestor_tag(self, tag):
        node = self.parent
        while node is not None:
            if node.tag == tag:
                return node
            node = node.parent
        return None


class TreeParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#document")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag, dict(attrs), self.getpos()[0])
        self.stack[-1].add(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        node = Node(tag, dict(attrs), self.getpos()[0])
        self.stack[-1].add(node)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def squish(text: str) -> str:
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "", text or "")


def cjk_count(text: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]", text or ""))


def visible_text(node: Node) -> str:
    """拼接可见文本，跳过 script/style。"""
    parts = []

    def rec(n):
        for child in n.children:
            if isinstance(child, str):
                parts.append(child)
            elif child.tag in ("script", "style"):
                continue
            else:
                rec(child)

    rec(node)
    return "".join(parts)


def iter_text_nodes(node: Node):
    """逐个产出 (父节点, 文本)，用于检查正文里的纯文本引用。"""
    for child in node.children:
        if isinstance(child, str):
            yield node, child
        else:
            yield from iter_text_nodes(child)


def ancestors(node: Node):
    n = node
    while n is not None:
        yield n
        n = n.parent


def line_of(raw: str, pos: int) -> int:
    return raw.count("\n", 0, pos) + 1


# --------------------------------------------------------------------------- CSS


def extract_block(css: str, selector_regex: str):
    """返回 (inner, start, end)；end 为右花括号之后。"""
    m = re.search(selector_regex, css)
    if not m:
        return None, -1, -1
    brace = css.find("{", m.end() - 1)
    if brace < 0:
        return None, -1, -1
    depth = 0
    for i in range(brace, len(css)):
        if css[i] == "{":
            depth += 1
        elif css[i] == "}":
            depth -= 1
            if depth == 0:
                return css[brace + 1:i], brace + 1, i + 1
    return None, -1, -1


def strip_media_print(css: str) -> str:
    out = css
    while True:
        m = re.search(r"@media\s+print\s*\{", out)
        if not m:
            return out
        depth = 0
        start = out.find("{", m.start())
        end = len(out)
        for i in range(start, len(out)):
            if out[i] == "{":
                depth += 1
            elif out[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        out = out[:m.start()] + out[end:]


def parse_tokens(css: str):
    light_inner, _, _ = extract_block(css, r":root\s*\{")
    dark_inner, _, _ = extract_block(css, r'html\[data-theme="dark"\]\s*\{')
    if light_inner is None or dark_inner is None:
        return None, None

    def to_map(inner):
        data = {}
        for m in re.finditer(r"(--[A-Za-z0-9-]+)\s*:\s*([^;]+);", inner):
            data[m.group(1)] = m.group(2).strip()
        return data

    return to_map(light_inner), to_map(dark_inner)


def remove_spans(text: str, spans):
    for start, end in sorted(spans, reverse=True):
        text = text[:start] + text[end:]
    return text


def hex_colors(css: str) -> list[tuple[str, int]]:
    return [(m.group(0), m.start()) for m in re.finditer(r"#[0-9A-Fa-f]{3,8}\b", css)]


def _linear(channel: float) -> float:
    return channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4


def luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * _linear(r) + 0.7152 * _linear(g) + 0.0722 * _linear(b)


def contrast(fg: str, bg: str) -> float:
    a, b = luminance(fg), luminance(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def check_style_pack(style: str, rep: Report) -> dict:
    """返回 {'light': {...}, 'dark': {...}}，同时校验令牌完备与对比度。"""
    p = C.style_path(style)
    tokens_css = C.read_text(p / "tokens.css")
    light, dark = parse_tokens(tokens_css)
    if light is None or dark is None:
        rep.error("tokens.css", 0, "缺少 :root 或 html[data-theme=\"dark\"] 令牌块")
        return {"light": {}, "dark": {}}

    missing = sorted(set(light) - set(dark))
    extra = sorted(set(dark) - set(light))
    if missing:
        rep.error("tokens.css", 0, f"深色主题缺少令牌：{', '.join(missing)}")
    if extra:
        rep.error("tokens.css", 0, f"深色主题多出令牌：{', '.join(extra)}")
    for token in REQUIRED_TOKENS:
        if token not in light or token not in dark:
            rep.error("tokens.css", 0, f"缺少必需令牌：{token}（两套主题都要定义）")

    contrast_file = p / "contrast.json"
    if contrast_file.exists():
        spec = C.load_json(contrast_file)
        for theme_name, table in (("light", light), ("dark", dark)):
            for pair in spec.get("pairs", []):
                fg, bg, minimum = pair["fg"], pair["bg"], float(pair.get("min", 4.5))
                if fg not in table or bg not in table:
                    rep.error("tokens.css", 0, f"对比度契约引用了不存在的令牌：{fg} / {bg}")
                    continue
                if not re.fullmatch(r"#[0-9A-Fa-f]{3,8}", table[fg]) or not re.fullmatch(r"#[0-9A-Fa-f]{3,8}", table[bg]):
                    continue
                value = contrast(table[fg], table[bg])
                if value + 1e-3 < minimum:
                    rep.error(
                        "tokens.css", 0,
                        f"[{theme_name}] {pair.get('label', fg + '/' + bg)} 对比度 {value:.2f}:1 "
                        f"低于 {minimum}:1（{fg}={table[fg]}, {bg}={table[bg]}）",
                    )
    else:
        rep.error("contrast.json", 0, "缺少对比度契约文件")

    components = C.read_text(p / "components.css")
    bad = hex_colors(strip_media_print(components))
    if bad:
        rep.error(
            "components.css", 0,
            f"组件样式出现裸色值 {len(bad)} 处（{', '.join(h for h, _ in bad[:5])}）；必须用 var(--token)",
        )
    for cls in REQUIRED_CLASSES:
        if f".{cls}" not in components:
            rep.error("components.css", 0, f"缺少组件样式：.{cls}")

    chapter_tpl = C.read_text(p / "chapter.html")
    for token in REQUIRED_CHAPTER_PLACEHOLDERS:
        if token not in chapter_tpl:
            rep.error("chapter.html", 0, f"缺少占位符：{token}")
    index_tpl = C.read_text(p / "index.html")
    for token in REQUIRED_INDEX_PLACEHOLDERS:
        if token not in index_tpl:
            rep.error("index.html", 0, f"缺少占位符：{token}")

    return {"light": light, "dark": dark}


def check_css(css: str, filename: str, rep: Report, pack: dict, style: str):
    light, dark = parse_tokens(css)
    if light is None or dark is None:
        rep.error(filename, 0, "页面内联 CSS 缺少 :root 或深色主题令牌块（不要手改模板，重新生成页面）")
        return

    required = set(pack.get("light") or {})
    missing_light = sorted(required - set(light))
    if missing_light:
        rep.error(filename, 0, f"浅色主题缺少令牌：{', '.join(missing_light)}")
    missing_dark = sorted(required - set(dark))
    if missing_dark:
        rep.error(filename, 0, f"深色主题缺少令牌：{', '.join(missing_dark)}")
    missing_pair = sorted(set(light) - set(dark))
    extra_pair = sorted(set(dark) - set(light))
    if missing_pair:
        rep.error(filename, 0, f"深色主题缺少令牌：{', '.join(missing_pair)}")
    if extra_pair:
        rep.error(filename, 0, f"深色主题多出令牌：{', '.join(extra_pair)}")

    # 与风格包同步（防止页面生成后风格包被改、页面没重生成）
    for token, value in (pack.get("light") or {}).items():
        if token in light and norm(light[token]).lower() != norm(value).lower():
            rep.error(filename, 0, f"令牌 {token} 与风格包不一致（{light[token]} != {value}），请重新生成页面")

    without_print = strip_media_print(css)
    light_inner, ls, le = extract_block(without_print, r":root\s*\{")
    dark_inner, ds, de = extract_block(without_print, r'html\[data-theme="dark"\]\s*\{')
    spans = [(s, e) for s, e in ((ls, le), (ds, de)) if s >= 0]
    rest = remove_spans(without_print, spans)
    bad_hex = hex_colors(rest)
    if bad_hex:
        sample = ", ".join(h for h, _ in bad_hex[:5])
        rep.error(
            filename, 0,
            f"组件 CSS 出现裸色值 {len(bad_hex)} 处（{sample}）；必须改用 var(--token)",
        )

    if "filter:" in css.replace(" ", ""):
        rep.warn(filename, 0, "CSS 里出现 filter：不要对插图做滤镜，否则深色主题会改变插图颜色")
    if "@media (max-width: 768px)" not in css and "@media (max-width:768px)" not in css:
        rep.error(filename, 0, "缺少 @media (max-width: 768px) 响应式规则")
    if ":focus-visible" not in css:
        rep.error(filename, 0, "缺少 :focus-visible 焦点样式（键盘可达性）")
    if "prefers-reduced-motion" not in css:
        rep.warn(filename, 0, "缺少 prefers-reduced-motion 降级")


# --------------------------------------------------------------------------- 页面公共检查


def check_common(path: Path, raw: str, node: Node, rep: Report, pack: dict, style: str):
    name = path.name
    css = "\n".join(s.text() for s in node.find_all("style"))

    if not raw.lstrip().lower().startswith("<!doctype html>"):
        rep.error(name, 1, "缺少 <!DOCTYPE html>")
    html_node = node.find("html")
    if html_node is None or html_node.attrs.get("lang") != "zh-CN":
        rep.error(name, 1, '必须声明 <html lang="zh-CN">')
    if node.find("meta") is None or not any(
        m.attrs.get("charset", "").lower() == "utf-8" for m in node.find_all("meta")
    ):
        rep.error(name, 1, '缺少 <meta charset="UTF-8">')
    if not any("width=device-width" in m.attrs.get("content", "") for m in node.find_all("meta")):
        rep.error(name, 1, "缺少 viewport meta")

    head = node.find("head")
    titles = list(head.find_all("title")) if head is not None else []
    if len(titles) != 1 or not norm(titles[0].text()):
        rep.error(name, 1, "必须且只能有一个非空 <title>（注意：SVG 内的 <title> 不算）")

    # 未转义的尖括号：解析器会把 <int> 当成标签，浏览器随后吞掉这段文字
    for el in node.walk():
        if el.tag in KNOWN_TAGS:
            continue
        if el.ancestor_tag("pre") is not None:
            continue  # 代码块里有更精确的检查
        rep.error(
            name, el.line,
            f"未知标签 <{el.tag}>：疑似未转义的尖括号（应写 &lt;{el.tag}&gt;）",
        )

    # 资源：src / url() / link 必须全内联；正文里的纯文本 URL 不算依赖
    for el in node.walk():
        if el.attrs.get("src"):
            rep.error(name, el.line, f"禁止任何 src 资源（<{el.tag}> 必须内联）")
        value = (el.attrs.get("href") or "").strip()
        if re.match(r"(?:https?:)?//", value):
            rep.warn(name, el.line, f"外链跳转：{value}（离线文档建议去掉或改为文字引用）")
        style_attr = el.attrs.get("style", "")
        if re.search(r"url\(\s*['\"]?(?:https?:)?//", style_attr):
            rep.error(name, el.line, "禁止在 style 中引用外部资源")
    if re.search(r"url\(\s*['\"]?(?:https?:)?//", css):
        rep.error(name, 0, "CSS 中禁止 url() 外部资源")
    if re.search(r"<link\b[^>]*stylesheet", raw, re.I):
        rep.error(name, line_of(raw, re.search(r"<link\b[^>]*stylesheet", raw, re.I).start()), "禁止 <link rel=stylesheet>")
    if "@import" in css:
        rep.error(name, 0, "CSS 中禁止 @import")

    scripts = list(node.find_all("script"))
    if len(scripts) != 2:
        rep.error(name, 1, f"必须恰好两段内联脚本，实际 {len(scripts)} 段")
    for s in scripts:
        if "src" in s.attrs:
            rep.error(name, s.line, "脚本必须是内联的，禁止 src")
    if len(scripts) == 2:
        head_end = raw.find("</head>")
        if raw.find("<script", 0, max(head_end, 0)) < 0:
            rep.error(name, 0, "主题初始化脚本必须放在 <head> 中（否则深色用户会闪白）")

    if len(list(node.find_all("style"))) != 1:
        rep.error(name, 0, "必须且只能有一段内联 <style>")

    # 主题契约
    check_css(css, name, rep, pack, style)
    if not any(b.attrs.get("id") == "theme-toggle" for b in node.find_all("button")):
        rep.error(name, 0, "缺少 #theme-toggle 主题切换按钮")

    # 插图：只检查内容插图，跳过图标类装饰
    for svg in node.find_all("svg"):
        cls = svg.classes()
        parent = svg.parent
        parent_classes = parent.classes() if parent else set()
        w_raw = re.sub(r"[^\d.]", "", svg.attrs.get("width", "") or "")
        small_icon = bool(w_raw) and float(w_raw) <= 28
        decorative = (
            "h2-icon" in cls
            or "course-icon" in cls
            or "index-icon" in cls
            or "fab-btn" in parent_classes
            or "chapter-link" in parent_classes
            or "footer-brand" in parent_classes
            or svg.ancestor("fab-btn") is not None
            or small_icon
        )
        if decorative:
            continue
        if svg.ancestor("svg-container") is None:
            rep.warn(name, svg.line, "SVG 不在 .svg-container 内（内容插图应包容器）")
        if svg.attrs.get("role") != "img" and svg.find("title") is None:
            rep.warn(name, svg.line, "SVG 缺少 role=\"img\" 或 <title>（无障碍）")

    svg_spans = [(m.start(), m.end()) for m in re.finditer(r"<svg\b.*?</svg>", raw, re.S)]
    for start, end in svg_spans:
        chunk = raw[start:end]
        if re.search(r"var\s*\(\s*--", chunk):
            rep.error(name, line_of(raw, start), "SVG 内部禁止使用 var()：插图颜色必须写死，才能不随主题变化")
        if re.search(r"\bfilter\s*=", chunk):
            rep.error(name, line_of(raw, start), "SVG 上禁止 filter 属性")
        if re.search(r'fill="#(?:4CAF50|F5A623)"', chunk, re.I):
            rep.warn(
                name, line_of(raw, start),
                "亮绿 #4CAF50 / 亮橙 #F5A623 作块底色时白字对比度不足；"
                "请配深色字，或改用 #2E7D32 / #A35A00",
            )

    # id 唯一
    seen = {}
    for m in re.finditer(r'\bid="([^"]+)"', raw):
        ident = m.group(1)
        if ident in seen:
            rep.error(name, line_of(raw, m.start()), f"重复 id：{ident}")
        seen[ident] = m.start()

    # 占位符 / TODO
    for m in re.finditer(r"\{\{[^}]+\}\}", raw):
        rep.error(name, line_of(raw, m.start()), f"残留占位符：{m.group(0)}")
    for word in ("TODO", "待补充", "待撰写", "此处省略", "Lorem ipsum"):
        for m in re.finditer(word, raw):
            if word == "此处省略" and ALLOWED_ELLIPSIS in raw[max(0, m.start() - 20):m.end() + 20]:
                continue
            rep.error(name, line_of(raw, m.start()), f"出现未完成标记：{word}")

    # 悬浮菜单
    fab = node.find("div", cls="fab-menu")
    if fab is None:
        rep.error(name, 0, "缺少右下悬浮菜单 .fab-menu")
    else:
        buttons = [n for n in fab.walk() if n.tag in ("button", "a")]
        if len(buttons) < 2:
            rep.error(name, fab.line, "悬浮菜单至少需要主题切换与回到顶部")


# --------------------------------------------------------------------------- 正文页检查


def check_chapter(path: Path, raw: str, node: Node, rep: Report, manifest: dict | None):
    name = path.name
    chapters = manifest["chapters"] if manifest else []
    ch = next((c for c in chapters if c.get("file") == name), None)

    title = ch["title"] if ch else (norm(node.find("h1").text()) if node.find("h1") else "")
    if ch:
        expected_title = f"{title} - {manifest['brand']}"
        if norm(node.find("title").text()) != expected_title:
            rep.error(name, node.find("title").line, f"<title> 应为「{expected_title}」")

    h1s = list(node.find_all("h1"))
    if len(h1s) != 1:
        rep.error(name, 1, f"必须且只能有一个 <h1>，实际 {len(h1s)} 个")
    elif norm(h1s[0].text()) != title:
        rep.error(name, h1s[0].line, f"h1 必须等于讲标题「{title}」")

    header = node.find("header")
    if header is None or "chapter-header" not in header.classes():
        rep.error(name, 0, "缺少 <header class=\"chapter-header\">")

    if ch:
        kicker = node.find("p", cls="kicker")
        if kicker is None or not re.search(rf"第\s*{ch['n']}\s*讲", kicker.text()):
            rep.error(name, kicker.line if kicker else 0, f"头部缺少「第 {ch['n']} 讲」标识")
        if kicker is not None and f"共 {len(chapters)} 讲" not in norm(kicker.text()):
            rep.error(
                name, kicker.line,
                f"头部「共 N 讲」与 manifest 不一致（应为共 {len(chapters)} 讲）；跑 renumber.py 同步",
            )
        subtitle = node.find("p", cls="subtitle")
        if subtitle is not None and ch.get("summary") and norm(subtitle.text()) != norm(ch["summary"]):
            rep.error(name, subtitle.line, "副标题与 manifest 中的摘要不一致")
        for span in node.find_all("span"):
            if "data-n" in span.attrs and norm(span.text()) != str(ch["n"]):
                rep.error(name, span.line, f"data-n 应为 {ch['n']}，实际 {span.text()}")
        if not ch.get("summary"):
            rep.warn(name, 0, "manifest 中缺少本讲摘要")

    if node.find("main") is None:
        rep.error(name, 0, "缺少 <main> 内容容器")
    sections = list(node.find("main").find_all("section")) if node.find("main") else []
    if not (4 <= len(sections) <= 6):
        rep.error(name, 0, f"正文应有 4~6 个 <section>，实际 {len(sections)} 个")

    # manifest.sections 是唯一计划源；正文改了小标题要同步回 manifest
    if ch and ch.get("sections") and len(sections) == len(ch["sections"]):
        for sec, expected in zip(sections, ch["sections"]):
            h2 = sec.find("h2")
            if h2 is not None and norm(h2.text()) != norm(expected):
                rep.warn(
                    name, h2.line,
                    f"小节标题与 manifest.sections 不一致：「{norm(h2.text())}」≠「{expected}」",
                )

    for sec in sections:
        h2s = list(sec.find_all("h2"))
        if len(h2s) != 1:
            rep.error(name, sec.line, f"每个 section 必须恰好一个 <h2>，实际 {len(h2s)} 个")
        has_carrier = False
        for d in sec.walk():
            if d.tag == "h2" or d.ancestor_tag("h2") is not None:
                continue
            if "h2-icon" in d.classes():
                continue
            if d.tag in CARRIER_TAGS or (d.classes() & CARRIER_CLASSES):
                has_carrier = True
                break
        if not has_carrier:
            rep.error(name, sec.line, "空小节：至少要有一段正文 / 代码 / 表格 / SVG / 列表")

    pre_blocks = list(node.find_all("pre"))
    if not (2 <= len(pre_blocks) <= 6):
        rep.error(name, 0, f"代码块应为 2~6 个，实际 {len(pre_blocks)} 个")
    for pre in pre_blocks:
        if pre.ancestor("code-block") is None:
            rep.error(name, pre.line, "<pre> 必须包在 .code-block 内")
        code = pre.find("code")
        if code is None or not norm(code.text()):
            rep.error(name, pre.line, "代码块为空")
        else:
            body = code.text()
            if not re.search(r"(//|#|/\*|--|;)", body):
                rep.warn(name, pre.line, "代码块没有注释，建议写清“为什么这么写”")

    tables = list(node.find_all("table"))
    if not (1 <= len(tables) <= 3):
        rep.error(name, 0, f"表格应为 1~3 张，实际 {len(tables)} 张")
    for table in tables:
        if table.ancestor("table-wrap") is None:
            rep.error(name, table.line, "表格必须包在 .table-wrap 内（窄屏横向滚动）")
        if table.find("th") is None:
            rep.error(name, table.line, "表格缺少表头 <th>")

    svgs = [s for s in node.find_all("svg") if s.ancestor("svg-container") is not None]
    if not (1 <= len(svgs) <= 6):
        rep.error(name, 0, f"内容插图应为 1~6 张，实际 {len(svgs)} 张")

    # 代码转义
    for m in re.finditer(r"<pre[^>]*>\s*<code[^>]*>(.*?)</code>\s*</pre>", raw, re.S):
        body = m.group(1)
        lt = body.find("<")
        if lt >= 0:
            rep.error(name, line_of(raw, m.start(1) + lt), "代码块内有未转义的 <（应写 &lt;）")
        for amp in re.finditer(r"&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)", body):
            rep.warn(name, line_of(raw, m.start(1) + amp.start()), "代码块内有未转义的 &（应写 &amp;）")

    # 页脚
    footer = node.find("footer")
    if footer is None:
        rep.error(name, 0, "缺少 <footer>")
    else:
        if ch and norm(manifest["brand"]) not in norm(footer.text()):
            rep.error(name, footer.line, "页脚缺少品牌名")
        title_span = next((s for s in footer.find_all("span") if "data-title" in s.attrs), None)
        if title_span is None:
            rep.error(name, footer.line, "页脚缺少 <span data-title>（重编号依赖它定位标题）")
        elif ch and norm(title_span.text()) != norm(title):
            rep.error(name, title_span.line, "页脚标题与 manifest 不一致")
        if ch and f"共 {len(chapters)} 讲" not in norm(footer.text()):
            rep.error(
                name, footer.line,
                f"页脚「共 N 讲」与 manifest 不一致（应为共 {len(chapters)} 讲）",
            )
        if ch and str(manifest.get("year", "")) not in norm(footer.text()):
            rep.error(name, footer.line, f"页脚缺少 manifest 年份 {manifest.get('year')}")
        if ch:
            author = manifest.get("author") or manifest["brand"]
            author_p = node.find("p", cls="footer-author")
            if author_p is None:
                rep.error(name, footer.line, "页脚缺少作者行 <p class=\"footer-author\">")
            elif norm(author_p.text()) != f"作者：{norm(author)}":
                rep.error(name, author_p.line, f"页脚作者应为「作者：{norm(author)}」")

    # 翻页
    pager = node.find("nav", cls="pager")
    if pager is None:
        rep.error(name, 0, "缺少 .pager 翻页导航")
    elif ch:
        links = [n for n in pager.walk() if n.tag == "a"]
        hrefs = [n.attrs.get("href", "") for n in links]
        if "index.html" not in hrefs:
            rep.error(name, pager.line, "翻页导航缺少「课程目录」链接")
        idx = chapters.index(ch)
        if idx > 0:
            if chapters[idx - 1]["file"] not in hrefs:
                rep.error(name, pager.line, f"缺少上一讲链接 {chapters[idx - 1]['file']}")
        if idx + 1 < len(chapters):
            if chapters[idx + 1]["file"] not in hrefs:
                rep.error(name, pager.line, f"缺少下一讲链接 {chapters[idx + 1]['file']}")

    # 悬浮菜单按钮数量（正文页 3 个）
    fab = node.find("div", cls="fab-menu")
    if fab is not None:
        buttons = [n for n in fab.walk() if n.tag in ("button", "a")]
        if len(buttons) != 3:
            rep.error(name, fab.line, f"正文页悬浮菜单应为 3 个按钮，实际 {len(buttons)} 个")

    # 交叉引用
    for ref in node.find_all(None, cls=None):
        if "data-ref" not in ref.attrs:
            continue
        target_n = ref.attrs["data-ref"]
        if manifest and not any(str(c["n"]) == target_n for c in chapters):
            rep.error(name, ref.line, f"交叉引用指向不存在的讲次：{target_n}")
            continue
        if manifest:
            target = next(c for c in chapters if str(c["n"]) == target_n)
            if ref.tag == "a" and ref.attrs.get("href") != target["file"]:
                rep.error(name, ref.line, f"交叉引用链接应为 {target['file']}")
            if not re.search(rf"第\s*{target_n}\s*讲", ref.text()):
                rep.warn(name, ref.line, f"交叉引用文字建议写成「第 {target_n} 讲」")

    # 没有 data-ref 的讲次引用：renumber 不会同步，必须提示
    for parent, text in iter_text_nodes(node):
        parents = list(ancestors(parent))
        if any("data-ref" in a.attrs for a in parents):
            continue
        if any(a.tag in ("script", "style") for a in parents):
            continue
        for m in re.finditer(r"第\s*\d+\s*讲", text):
            rep.warn(
                name, parent.line,
                f"「{m.group(0)}」没有 data-ref，重编号不会同步；应写成带 data-ref 的链接",
            )

    # 长度（汉字；不含脚本与样式）
    body = node.find("body")
    if body is not None:
        count = cjk_count(visible_text(body))
        if not (600 <= count <= 3000):
            rep.error(name, 0, f"正文汉字数 {count}，超出 600~3000 的硬性范围")
        elif not (800 <= count <= 2200):
            rep.warn(name, 0, f"正文汉字数 {count}，建议 800~2200")

    # 内容质量提示（warning）：结构合格不等于内容合格
    prose = visible_text(body) if body is not None else ""
    for phrase in (
        "下面我们来看", "下面来看", "相信大家已经了解", "总的来说",
        "综上所述", "众所周知", "浅谈", "初探", "漫谈",
    ):
        if phrase in prose:
            rep.warn(name, 0, f"出现空洞/口水表达：「{phrase}」")

    for p in node.find_all("p"):
        t = norm(p.text())
        if re.search(r"\d+\s*(?:%|倍)", t) and not re.search(
            r"实测|典型值|来源|测试环境|基准测试|SDM|官方文档|据[^，。]{0,6}", t
        ):
            rep.warn(name, p.line, "性能数字没有标注来源（实测 / 典型值 / 据…）")

    for table in tables:
        rows = list(table.find_all("tr"))
        tbody = table.find("tbody")
        body_rows = list(tbody.find_all("tr")) if tbody is not None else rows[1:]
        if body_rows and not (3 <= len(body_rows) <= 6):
            rep.warn(name, table.line, f"表格正文 {len(body_rows)} 行，建议 3~6 行")
        head_cells = list(rows[0].find_all("th")) if rows else []
        if head_cells and not (2 <= len(head_cells) <= 4):
            rep.warn(name, table.line, f"表格 {len(head_cells)} 列，建议 2~4 列")

    if sections:
        last = sections[-1]
        ols = list(last.find_all("ol"))
        if not any(4 <= len(list(o.find_all("li"))) <= 6 for o in ols):
            rep.warn(name, last.line, "最后一节建议用 4~6 条有序列表收尾（总结与最佳实践）")

    for pre in pre_blocks:
        code = pre.find("code")
        if code is None:
            continue
        lines = [ln for ln in code.text().splitlines() if ln.strip()]
        if lines and not (10 <= len(lines) <= 40):
            rep.warn(
                name, pre.line,
                f"代码块 {len(lines)} 行，建议 15~40 行（截断时用「省略非关键部分」）",
            )

    # 标题里不要用 emoji
    for h in list(node.find_all("h1")) + list(node.find_all("h2")) + list(node.find_all("h3")):
        if re.search(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]", h.text()):
            rep.warn(name, h.line, "标题里出现 emoji，印刷与跨平台观感不稳定")


# --------------------------------------------------------------------------- 目录页检查


def check_index(path: Path, raw: str, node: Node, rep: Report, manifest: dict):
    name = path.name
    chapters = manifest["chapters"]
    width = manifest.get("width", 2)

    expected_title = f"《{manifest['course']}》课程目录"
    got = norm(node.find("title").text()) if node.find("title") else ""
    if got != expected_title:
        rep.error(name, 1, f"目录页 <title> 应为「{expected_title}」")

    h1 = node.find("h1")
    if h1 is None or norm(h1.text()) != norm(manifest["course"]):
        rep.error(name, h1.line if h1 else 0, "目录页 h1 应为课程名")

    subtitle = node.find("p", cls="subtitle")
    if subtitle is not None and norm(subtitle.text()) != norm(manifest["subtitle"]):
        rep.error(name, subtitle.line, "目录页副标题与 manifest 不一致")

    intro = node.find("section", cls="directory-intro")
    if intro is None:
        rep.error(name, 0, "缺少 .directory-intro 课程说明")
    elif f"共 {len(chapters)} 讲" not in norm(intro.text()):
        rep.error(
            name, intro.line,
            f"课程说明里的「共 N 讲」与 manifest 不一致（应为共 {len(chapters)} 讲）；用 --index-only 重建",
        )

    cards = list(node.find_all("article", cls="chapter-card"))
    if len(cards) != len(chapters):
        rep.error(name, 0, f"章节卡片 {len(cards)} 张，manifest 有 {len(chapters)} 讲")

    for idx, card in enumerate(cards):
        if idx >= len(chapters):
            break
        ch = chapters[idx]
        number = card.find("div", cls="chapter-number")
        if number is None or norm(number.text()) != f"{ch['n']:0{width}d}":
            rep.error(name, card.line, f"第 {idx + 1} 张卡片序号应为 {ch['n']:0{width}d}")
        h3 = card.find("h3")
        if h3 is None or norm(h3.text()) != norm(ch["title"]):
            rep.error(name, card.line, f"第 {idx + 1} 张卡片标题与 manifest 不一致")
        content = card.find("p", cls="chapter-content")
        if content is None or norm(content.text()) != norm(ch.get("summary") or ""):
            rep.error(name, card.line, f"第 {idx + 1} 张卡片摘要与 manifest 不一致")
        meta = card.find("p", cls="chapter-meta")
        if (ch.get("level") or ch.get("minutes")) and meta is None:
            rep.warn(name, card.line, f"第 {idx + 1} 张卡片缺少难度/时长（manifest 里有值）")
        link = card.find("a", cls="chapter-link")
        if link is None or link.attrs.get("href") != ch["file"]:
            rep.error(name, card.line, f"第 {idx + 1} 张卡片链接应为 {ch['file']}")
        elif "开始学习" not in norm(link.text()):
            rep.warn(name, link.line, "卡片按钮文字建议统一为「开始学习」")

    stages = list(node.find_all("section", cls="stage"))
    if not stages:
        rep.error(name, 0, "目录页没有任何阶段分组（.stage）")
    grouped = sum(len(list(st.find_all("article", cls="chapter-card"))) for st in stages)
    if grouped != len(cards):
        rep.error(name, 0, f"有 {len(cards) - grouped} 张卡片不在 .stage 分组内")

    footer = node.find("footer")
    if footer is None:
        rep.error(name, 0, "目录页缺少 <footer>")
    else:
        ft = norm(footer.text())
        if norm(manifest["brand"]) not in ft:
            rep.error(name, footer.line, "页脚缺少品牌名")
        if f"共 {len(chapters)} 讲" not in ft:
            rep.error(name, footer.line, f"页脚「共 N 讲」应为共 {len(chapters)} 讲")
        if str(manifest.get("year", "")) not in ft:
            rep.error(name, footer.line, f"页脚缺少 manifest 年份 {manifest.get('year')}")
        author = manifest.get("author") or manifest["brand"]
        author_p = node.find("p", cls="footer-author")
        if author_p is None:
            rep.error(name, footer.line, "页脚缺少作者行 <p class=\"footer-author\">")
        elif norm(author_p.text()) != f"作者：{norm(author)}":
            rep.error(name, author_p.line, f"页脚作者应为「作者：{norm(author)}」")

    fab = node.find("div", cls="fab-menu")
    if fab is not None:
        buttons = [n for n in fab.walk() if n.tag in ("button", "a")]
        if len(buttons) != 2:
            rep.error(name, fab.line, f"目录页悬浮菜单应为 2 个按钮，实际 {len(buttons)} 个")
    if node.find("nav", cls="pager") is not None:
        rep.error(name, 0, "目录页不应有翻页导航")


# --------------------------------------------------------------------------- 清单检查


def check_manifest(manifest: dict, outdir: Path, rep: Report):
    name = "manifest.json"
    for key in ("course", "subtitle", "brand", "slogan", "year", "style", "chapters"):
        if not manifest.get(key):
            rep.error(name, 0, f"缺少字段：{key}")
    if not manifest.get("author"):
        rep.warn(name, 0, "缺少 author 字段，页脚作者会回落到品牌名")
    if manifest.get("version") != 1:
        rep.warn(name, 0, "manifest.version 不是 1，脚本可能不兼容")

    chapters = manifest.get("chapters") or []
    seen_titles = {}
    for idx, ch in enumerate(chapters, start=1):
        where = f"第 {idx} 讲"
        if ch.get("n") != idx:
            rep.error(name, 0, f"{where} 的 n 应为 {idx}，实际 {ch.get('n')}")
        expected = C.chapter_file(idx, manifest.get("width", 2))
        if ch.get("file") != expected:
            rep.error(name, 0, f"{where} 文件名应为 {expected}，实际 {ch.get('file')}")
        if not (outdir / expected).exists():
            rep.error(name, 0, f"{where} 文件不存在：{expected}")
        if not ch.get("title"):
            rep.error(name, 0, f"{where} 缺少标题")
        elif ch["title"] in seen_titles:
            rep.error(name, 0, f"标题重复：{ch['title']}（第 {seen_titles[ch['title']]} 讲与{where}）")
        else:
            seen_titles[ch["title"]] = idx
        if not ch.get("summary"):
            rep.warn(name, 0, f"{where} 缺少摘要（目录卡片会显得空）")
        sections = ch.get("sections") or []
        if not (4 <= len(sections) <= 6):
            rep.error(name, 0, f"{where} 小节数 {len(sections)}，要求 4~6")
        if not ch.get("stage"):
            rep.warn(name, 0, f"{where} 缺少阶段，目录页将归入“课程章节”")
        level = ch.get("level")
        if level and level not in ("入门", "进阶", "实战", "专家"):
            rep.warn(name, 0, f"{where} 的难度「{level}」不在 入门/进阶/实战/专家 之内")
        minutes = ch.get("minutes")
        if minutes and not str(minutes).isdigit():
            rep.warn(name, 0, f"{where} 的时长应为纯数字（分钟），实际「{minutes}」")


# --------------------------------------------------------------------------- 横切检查


def check_cross(pages: dict, rep: Report):
    """pages: {filename: (raw, node)}，只含正文页。"""
    numbering = {"cn": 0, "ar": 0}
    paragraphs: dict[str, list[str]] = {}

    for filename, (raw, node) in pages.items():
        for h2 in node.find_all("h2"):
            text = norm(h2.text())
            if re.match("^" + CN_NUM, text):
                numbering["cn"] += 1
            elif re.match("^" + AR_NUM, text):
                numbering["ar"] += 1

        for p in node.find_all("p"):
            key = squish(p.text())
            if len(key) >= 60:
                paragraphs.setdefault(key, []).append(filename)

    if numbering["cn"] and numbering["ar"]:
        rep.error(
            "（全书）", 0,
            f"h2 编号风格混用：中文序号 {numbering['cn']} 个 / 阿拉伯序号 {numbering['ar']} 个；"
            f"全书只能选一种（content-blueprint.md §9）",
        )

    for key, files in paragraphs.items():
        if len({f for f in files}) > 1:
            rep.error("（全书）", 0, f"跨讲重复段落：{'、'.join(sorted(set(files)))}")

    # 近似重复（只在不完全相同时提示）
    keys = list(paragraphs)
    flagged = 0
    for i in range(len(keys)):
        if flagged >= 10:
            break
        for j in range(i + 1, len(keys)):
            a, b = keys[i], keys[j]
            if not (a[:30] == b[:30] or abs(len(a) - len(b)) < 40):
                continue
            ratio = difflib.SequenceMatcher(None, a, b).ratio()
            if ratio >= 0.9 and a != b:
                rep.warn(
                    "（全书）", 0,
                    f"疑似重复段落（相似度 {ratio:.2f}）：{'、'.join(sorted(set(paragraphs[a])))} / "
                    f"{'、'.join(sorted(set(paragraphs[b])))}",
                )
                flagged += 1
                break


# --------------------------------------------------------------------------- 主流程


def main():
    ap = argparse.ArgumentParser(description="精品技术课程文档验收")
    target = ap.add_mutually_exclusive_group()
    target.add_argument("--dir", help="课程输出目录（含 manifest.json）")
    target.add_argument("--file", help="只检查单个 HTML 文件")
    target.add_argument("--style-only", metavar="STYLE", help="只检查风格包的令牌与对比度")

    ap.add_argument("--style", help="风格包（默认取 manifest，否则 blue-ink）")
    ap.add_argument("--json", action="store_true", help="机器可读输出")
    ap.add_argument("--strict", action="store_true", help="警告也视为失败")
    args = ap.parse_args()

    rep = Report()

    if args.style_only:
        pack = check_style_pack(args.style_only, rep)
        if not any(i.level == "ERROR" for i in rep.items):
            print(
                f"风格包 {args.style_only} 通过："
                f"{len(pack['light'])} 个令牌 × 2 主题，对比度契约全部达标"
            )
        rep.dump(args.json, args.strict)
        return 1 if rep.errors or (args.strict and rep.warnings) else 0

    if not args.dir and not args.file:
        C.die("需要 --dir 或 --file（只查风格包用 --style-only）")

    if args.file:
        files = [Path(args.file)]
        outdir = files[0].parent
        # 单页验收也要读同目录 manifest：否则派生风格会被误报成“令牌不一致”
        manifest_path = outdir / "manifest.json"
        manifest = C.load_json(manifest_path) if manifest_path.exists() else None
        style = args.style or (manifest or {}).get("style") or C.DEFAULT_STYLE
    else:
        outdir = Path(args.dir)
        if not outdir.is_dir():
            C.die(f"目录不存在：{outdir}")
        manifest_path = outdir / "manifest.json"
        manifest = C.load_json(manifest_path) if manifest_path.exists() else None
        style = args.style or (manifest or {}).get("style") or C.DEFAULT_STYLE
        files = sorted(outdir.glob("*.html"))
        if not files:
            C.die(f"目录下没有 HTML：{outdir}")

    print(f"风格包：{style}")
    pack = check_style_pack(style, rep)

    if manifest and not args.file:
        check_manifest(manifest, outdir, rep)
    elif not args.file:
        rep.warn("manifest.json", 0, "没有 manifest.json：跳过标题/页脚/目录一致性检查")

    pages = {}
    for path in files:
        raw = C.read_text(path)
        parser = TreeParser()
        parser.feed(raw)
        node = parser.root
        check_common(path, raw, node, rep, pack, style)
        if path.name == "index.html":
            if manifest:
                check_index(path, raw, node, rep, manifest)
        else:
            check_chapter(path, raw, node, rep, manifest)
            pages[path.name] = (raw, node)

    if manifest and not args.file:
        check_cross(pages, rep)

    rep.dump(args.json, args.strict)
    failed = bool(rep.errors) or (args.strict and bool(rep.warnings))
    if failed:
        print("\n未通过：修完上面的 ERROR 后重跑本脚本。", file=sys.stderr)
    else:
        print("\n通过：可以打包交付。")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
