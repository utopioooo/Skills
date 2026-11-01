#!/usr/bin/env python3
"""premium-doc-maker 共享工具：路径、清单、模板渲染、大纲解析、片段构建。

所有脚本只依赖 Python 标准库。
"""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
STYLES_DIR = SKILL_DIR / "styles"
DEFAULT_STYLE = "blue-ink"
DEFAULT_BRAND = "翎光技术文档"
DEFAULT_SLOGAN = "探索技术深度，挖掘知识价值"

# h2 图标（Material Icons 风格，24×24 path）
H2_ICONS = [
    "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z",
    "M9.4 16.6L4.8 12l4.6-4.6L8 6l-6 6 6 6 1.4-1.4zm5.2 0l4.6-4.6-4.6-4.6L16 6l6 6-6 6-1.4-1.4z",
    "M12 2l-9 7 9 13 9-13-9-7zm0 3.5l5 3.9-5 7.2-5-7.2 5-3.9z",
    "M3 13h2v-2H3v2zm0 4h2v-2H3v2zm0-8h2V7H3v2zm4 4h14v-2H7v2zm0 4h14v-2H7v2zM7 7v2h14V7H7z",
    "M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z",
    "M12 2l-5.5 9h11L12 2zm0 3.6L14.9 9h-5.8L12 5.6zM17.5 13l-5.5 9-5.5-9h11z",
]

ARROW_SVG = (
    '<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" aria-hidden="true">'
    '<path d="M8.59 16.59L13.17 12 8.59 7.41 10 6l6 6-6 6z"/></svg>'
)


def die(msg: str, code: int = 2):
    print(f"错误：{msg}", file=sys.stderr)
    raise SystemExit(code)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def save_text(path: Path, text: str, dry_run: bool = False):
    text = text.replace("\r\n", "\n")
    if dry_run:
        print(f"[dry-run] 写入 {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def load_json(path: Path):
    return json.loads(read_text(path))


def save_json(path: Path, data, dry_run: bool = False):
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    save_text(path, text, dry_run=dry_run)


def esc(text: str) -> str:
    """转义 HTML 文本节点。"""
    return html.escape(str(text), quote=False)


def esc_attr(text: str) -> str:
    return html.escape(str(text), quote=True)


def style_path(style: str) -> Path:
    p = STYLES_DIR / style
    if not p.is_dir():
        available = ", ".join(sorted(x.name for x in STYLES_DIR.iterdir() if x.is_dir()))
        die(f"风格包不存在：{style}（可用：{available}）")
    return p


def load_style(style: str) -> dict:
    """读取风格包：模板 + 注入用 CSS。"""
    p = style_path(style)
    for name in ("tokens.css", "components.css", "chapter.html", "index.html", "contrast.json"):
        if not (p / name).exists():
            die(f"风格包 {style} 缺少必需文件：{name}")
    css = read_text(p / "tokens.css").rstrip() + "\n\n" + read_text(p / "components.css").rstrip() + "\n"
    return {
        "dir": p,
        "css": css,
        "chapter_tpl": read_text(p / "chapter.html"),
        "index_tpl": read_text(p / "index.html"),
        "tokens_css": read_text(p / "tokens.css"),
        "contrast": load_json(p / "contrast.json"),
    }


def render(template: str, mapping: dict) -> str:
    for key, value in mapping.items():
        template = template.replace("{{" + key + "}}", str(value))
    return template


def chapter_file(n: int, width: int = 2) -> str:
    return f"{n:0{width}d}.html"


def default_sections(title: str) -> list[str]:
    return [
        f"引言：为什么需要{title}",
        "一、核心机制",
        "二、关键实现",
        "三、方案对比与选型",
        "四、总结与最佳实践",
    ]


def build_sections(chapter: dict) -> str:
    titles = chapter.get("sections") or default_sections(chapter["title"])
    blocks = []
    for i, title in enumerate(titles):
        icon = H2_ICONS[i % len(H2_ICONS)]
        blocks.append(
            f"""        <section>
            <h2><svg class="h2-icon" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="{icon}"/></svg>{esc(title)}</h2>
            <!-- 待撰写：本小节至少需要一种载体（段落 + 代码 / 表格 / SVG / 列表）。
                 组件片段见 references/markup-cookbook.md；内容标准见 references/content-blueprint.md。 -->
        </section>"""
        )
    return "\n\n".join(blocks)


def build_pager(chapters: list[dict], index: int) -> tuple[str, str]:
    prev_html = (
        f'            <a class="pager-link" href="{chapters[index - 1]["file"]}">← 上一讲</a>'
        if index > 0
        else '            <span class="pager-link disabled" aria-disabled="true">← 上一讲</span>'
    )
    next_html = (
        f'            <a class="pager-link" href="{chapters[index + 1]["file"]}">下一讲 →</a>'
        if index + 1 < len(chapters)
        else '            <span class="pager-link disabled" aria-disabled="true">下一讲 →</span>'
    )
    return prev_html, next_html


def build_card(ch: dict, width: int = 2) -> str:
    meta_bits = []
    if ch.get("level"):
        meta_bits.append(str(ch["level"]))
    if ch.get("minutes"):
        meta_bits.append(f'{ch["minutes"]} 分钟')
    meta_html = (
        f'\n                <p class="chapter-meta">{" · ".join(meta_bits)}</p>'
        if meta_bits
        else ""
    )
    return f"""            <article class="chapter-card">
                <div class="chapter-number">{ch["n"]:0{width}d}</div>
                <h3>{esc(ch["title"])}</h3>{meta_html}
                <p class="chapter-content">{esc(ch.get("summary") or "")}</p>
                <a class="chapter-link" href="{esc_attr(ch["file"])}">开始学习 {ARROW_SVG}</a>
            </article>"""


def build_stage_groups(chapters: list[dict], width: int = 2) -> str:
    groups: list[tuple[str, list[dict]]] = []
    for ch in chapters:
        stage = ch.get("stage") or "课程章节"
        if not groups or groups[-1][0] != stage:
            groups.append((stage, []))
        groups[-1][1].append(ch)

    out = []
    for gi, (stage, items) in enumerate(groups, start=1):
        cards = "\n\n".join(build_card(ch, width) for ch in items)
        out.append(
            f"""        <section class="stage">
            <h2 class="stage-title"><span class="stage-index">{gi:02d}</span>{esc(stage)}</h2>
            <div class="chapters">
{cards}
            </div>
        </section>"""
        )
    return "\n\n".join(out)


# ---------------------------------------------------------------- 大纲解析

META_KEYS = {
    "课程名": "course",
    "课程": "course",
    "副标题": "subtitle",
    "品牌": "brand",
    "作者": "author",
    "作者名": "author",
    "Slogan": "slogan",
    "slogan": "slogan",
    "口号": "slogan",
    "年份": "year",
    "风格": "style",
}


def _meta_value(line: str) -> tuple[str, str] | None:
    m = re.match(r"^[-*]\s*([^：:]+?)\s*[：:]\s*(.+)$", line)
    if not m:
        return None
    return m.group(1).strip(), m.group(2).strip()


def parse_outline(path: Path) -> tuple[dict, list[dict]]:
    """解析 outline.md，返回 (meta, chapters)。

    格式见 references/process.md；解析失败时尽量给出可定位的错误。
    """
    text = read_text(path)
    meta: dict = {}
    chapters: list[dict] = []
    cur: dict | None = None
    in_sections = False

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue

        if line.startswith("## "):
            heading = line[3:].strip()
            m = re.match(r"^第\s*(\d+)\s*讲\s*[：:、.\s]?\s*(.*)$", heading)
            if m:
                n = int(m.group(1))
                title = m.group(2).strip() or f"第 {n} 讲"
            else:
                n = len(chapters) + 1
                title = re.sub(r"^第\s*\d+\s*讲\s*[：:、.\s]?", "", heading).strip() or heading
            cur = {"n": n, "title": title, "summary": "", "stage": "", "sections": []}
            chapters.append(cur)
            in_sections = False
            continue

        if line.startswith("### "):
            in_sections = True
            continue

        if cur is None:
            kv = _meta_value(line)
            if kv and kv[0] in META_KEYS:
                meta[META_KEYS[kv[0]]] = kv[1]
            continue

        if in_sections:
            m = re.match(r"^\d+\s*[.、)]\s*(.+)$", line)
            if m:
                cur["sections"].append(m.group(1).strip())
            continue

        kv = _meta_value(line)
        if kv:
            key, value = kv
            if key == "摘要":
                cur["summary"] = value
            elif key == "阶段":
                cur["stage"] = value
            elif key == "能力点":
                cur["ability"] = value
            elif key == "前置":
                cur["prereq"] = value
            elif key == "难度":
                cur["level"] = value
            elif key == "时长":
                cur["minutes"] = value

    if not chapters:
        die(f"大纲里没有解析到任何 '## 第 N 讲 …' 章节：{path}")
    return meta, chapters


def parse_chapter_list(path: Path) -> list[dict]:
    """解析 txt/json 章节清单（无小节信息时用默认五段式）。"""
    if path.suffix.lower() == ".json":
        data = load_json(path)
        return [
            {
                "n": i,
                "title": str(d.get("title", "")).strip(),
                "summary": str(d.get("summary", "")).strip(),
                "stage": str(d.get("stage", "")).strip(),
            }
            for i, d in enumerate(data, start=1)
        ]

    chapters = []
    for raw in read_text(path).splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        line = re.sub(r"^[-*]\s*", "", line)
        parts = [p.strip() for p in line.split("|")]
        if not parts or not parts[0]:
            continue
        parts[0] = re.sub(r"^\d+\s*[.、)]\s*", "", parts[0]).strip()
        chapters.append(
            {
                "n": len(chapters) + 1,
                "title": parts[0],
                "summary": parts[1] if len(parts) > 1 else "",
                "stage": parts[2] if len(parts) > 2 else "",
            }
        )
    if not chapters:
        die(f"章节清单为空：{path}")
    return chapters


def normalize_chapters(chapters: list[dict], width: int = 2) -> list[dict]:
    out = []
    for i, ch in enumerate(chapters, start=1):
        item = dict(ch)
        item["n"] = i
        item["file"] = chapter_file(i, width)
        item["title"] = str(item.get("title", "")).strip()
        item["summary"] = str(item.get("summary", "")).strip()
        item["stage"] = str(item.get("stage", "")).strip()
        item["sections"] = list(item.get("sections") or [])
        out.append(item)
    return out
