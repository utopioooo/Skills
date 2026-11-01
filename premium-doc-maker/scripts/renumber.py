#!/usr/bin/env python3
"""按 manifest 顺序重编号：文件改名、页脚/头部/翻页/交叉引用同步、目录页重建。

用法：
    python scripts/renumber.py --dir ./out --dry-run
    python scripts/renumber.py --dir ./out
    python scripts/renumber.py --dir ./out --keep-orphans   # 有孤立页面时中止

典型场景：在中间插入一讲、删除一讲、调整顺序后，全量修正编号。

安全策略：
- manifest 里没有、磁盘上却存在的 NN.html（例如被删讲次的旧文件）默认移到
  `<课程目录>/_trash/`，不直接删除；加 --keep-orphans 则改为报错中止。
- 上次运行中途崩溃留下的 __tmp__NN.html：目标不存在就恢复，存在就归档到 _trash。
- 改名失败会回滚；正文先全部在内存里改好，最后才落盘。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _common as C
import scaffold


def _sub_once(pattern: str, replacement: str, text: str, flags: int = 0) -> str:
    """re.sub 的替换串按字面量处理：标题里的反斜杠不会被当成转义序列。"""
    return re.sub(pattern, lambda m: replacement, text, count=1, flags=flags)


def patch_chapter(html: str, ch: dict, manifest: dict, prev: dict | None, nxt: dict | None) -> str:
    brand, course, slogan, year = manifest["brand"], manifest["course"], manifest["slogan"], manifest["year"]
    author = manifest.get("author") or brand
    total = len(manifest["chapters"])
    n = ch["n"]
    title = ch["title"]
    summary = ch.get("summary") or "本讲要点"

    html = _sub_once(
        r"<title>.*?</title>",
        f"<title>{C.esc(title)} - {C.esc(brand)}</title>",
        html, re.S,
    )
    html = _sub_once(
        r'<meta name="description" content="[^"]*">',
        f'<meta name="description" content="{C.esc_attr(summary)}">',
        html,
    )
    html = _sub_once(r"<h1>.*?</h1>", f"<h1>{C.esc(title)}</h1>", html, re.S)
    html = _sub_once(
        r'<p class="kicker">.*?</p>',
        f'<p class="kicker">《{C.esc(course)}》第 <span data-n="{n}">{n}</span> 讲 · 共 {total} 讲</p>',
        html, re.S,
    )
    html = _sub_once(
        r'<p class="subtitle">.*?</p>',
        f'<p class="subtitle">{C.esc(summary)}</p>',
        html, re.S,
    )
    html = _sub_once(
        r'<p class="footer-brand">.*?</p>',
        f'<p class="footer-brand">{C.esc(brand)} · {C.esc(slogan)}</p>',
        html, re.S,
    )
    author_line = f'<p class="footer-author">作者：{C.esc(author)}</p>'
    if '<p class="footer-author">' in html:
        html = _sub_once(r'<p class="footer-author">.*?</p>', author_line, html, re.S)
    else:
        html = re.sub(
            r'(<p class="footer-brand">.*?</p>)',
            lambda m: m.group(1) + "\n        " + author_line,
            html, count=1, flags=re.S,
        )
    html = _sub_once(
        r"<p>《.*?》课程 · 共 \d+ 讲 · \d+</p>",
        f"<p>《{C.esc(course)}》课程 · 共 {total} 讲 · {C.esc(year)}</p>",
        html, re.S,
    )
    html = _sub_once(
        r'<p>第\s*<span data-n="\d+">\d+</span>\s*讲：<span data-title>.*?</span></p>',
        f'<p>第 <span data-n="{n}">{n}</span> 讲：<span data-title>{C.esc(title)}</span></p>',
        html, re.S,
    )

    def pager_link(target: dict | None, label: str) -> str:
        if target is None:
            return f'            <span class="pager-link disabled" aria-disabled="true">{label}</span>'
        return f'            <a class="pager-link" href="{target["file"]}">{label}</a>'

    pager_inner = "\n".join(
        [
            pager_link(prev, "← 上一讲"),
            '            <a class="pager-link" href="index.html">课程目录</a>',
            pager_link(nxt, "下一讲 →"),
        ]
    )
    html = re.sub(
        r'(<nav class="pager"[^>]*>).*?(</nav>)',
        lambda m: m.group(1) + "\n" + pager_inner + "\n        " + m.group(2),
        html, count=1, flags=re.S,
    )

    html = re.sub(
        r'(<span data-n="\d+">)\d+(</span>)',
        lambda m: f"{m.group(1)}{n}{m.group(2)}",
        html,
    )
    html = re.sub(
        r"(<span data-title>).*?(</span>)",
        lambda m: f"{m.group(1)}{C.esc(title)}{m.group(2)}",
        html, flags=re.S,
    )
    return html


def fix_crossrefs(html: str, old_to_new: dict[int, int], chapters: list[dict]) -> str:
    by_n = {c["n"]: c for c in chapters}

    def repl(m: re.Match) -> str:
        tag, before, old_s, after, inner = m.groups()
        old = int(old_s)
        new = old_to_new.get(old)
        if new is None:
            # 目标讲次已被删除：保留原样，由 validate 报“指向不存在的讲次”。
            return m.group(0)
        target = by_n.get(new)
        if target is None:
            return m.group(0)
        inner = re.sub(r"第\s*\d+\s*讲", f"第 {new} 讲", inner)
        attrs = before + after
        if tag == "a":
            attrs = re.sub(r'href="[^"]*"', f'href="{target["file"]}"', attrs)
        return f'<{tag}{attrs}data-ref="{new}">{inner}</{tag}>'

    return re.sub(r"<(a|span)([^>]*?)data-ref=\"(\d+)\"([^>]*)>(.*?)</\1>", repl, html, flags=re.S)


def _trash_path(trash: Path, name: str) -> Path:
    target = trash / name
    if not target.exists():
        return target
    stem, suffix = target.stem, target.suffix
    i = 1
    while (trash / f"{stem}.{i}{suffix}").exists():
        i += 1
    return trash / f"{stem}.{i}{suffix}"


def main():
    ap = argparse.ArgumentParser(description="按 manifest 顺序重编号整套文档")
    ap.add_argument("--dir", required=True, help="课程输出目录")
    ap.add_argument("--dry-run", action="store_true", help="只打印计划")
    ap.add_argument(
        "--keep-orphans", action="store_true",
        help="发现不在 manifest 里的 NN.html 时报错中止，而不是移到 _trash/",
    )
    args = ap.parse_args()

    outdir = Path(args.dir)
    manifest_path = outdir / "manifest.json"
    if not manifest_path.exists():
        C.die(f"找不到 {manifest_path}")
    manifest = C.load_json(manifest_path)

    chapters = manifest["chapters"]
    if not chapters:
        C.die("manifest 里没有 chapters")

    width = manifest.get("width", 2)
    old_to_new: dict[int, int] = {}
    records: list[dict] = []

    for idx, ch in enumerate(chapters, start=1):
        old_n = int(ch.get("n", idx))
        old_file = ch.get("file")
        new_file = C.chapter_file(idx, width)
        old_to_new[old_n] = idx
        ch["n"] = idx
        ch["file"] = new_file
        records.append({"ch": ch, "old_file": old_file, "new_file": new_file})

    # ---------- 运行前检查：正文文件一个都不能少 ----------
    missing = [
        str(outdir / r["old_file"])
        for r in records
        if not r["old_file"] or not (outdir / r["old_file"]).is_file()
    ]
    if missing:
        C.die("以下正文文件不存在，未做任何修改：\n  " + "\n  ".join(missing))

    # ---------- 上次崩溃遗留的 __tmp__ ----------
    manifest_files = {r["old_file"] for r in records}
    tmp_actions: list[tuple[Path, Path]] = []
    for tmp in sorted(outdir.glob("__tmp__*.html")):
        target = outdir / tmp.name[len("__tmp__"):]
        if target.exists() or target.name not in manifest_files:
            # 目标已存在，或本来就不是 manifest 里的讲次：归档，别把孤立页面“恢复”回来
            tmp_actions.append((tmp, outdir / "_trash" / tmp.name))
        else:
            tmp_actions.append((tmp, target))

    # ---------- 孤立页面（磁盘有、manifest 没有） ----------
    orphans = [
        p for p in sorted(outdir.glob("*.html"))
        if p.name != "index.html"
        and p.name not in manifest_files
        and not p.name.startswith("__tmp__")
    ]
    if orphans and args.keep_orphans:
        C.die(
            "发现不在 manifest 里的页面（可能删讲后没清理），未做任何修改：\n  "
            + "\n  ".join(p.name for p in orphans)
            + "\n确认要删除这些讲次，请先备份后手动删除，或去掉 --keep-orphans 让脚本归档到 _trash/。"
        )

    if args.dry_run:
        for tmp, target in tmp_actions:
            if target.parent.name == "_trash":
                print(f"[dry-run] 归档残留 {tmp.name} → _trash/")
            else:
                print(f"[dry-run] 恢复残留 {tmp.name} → {target.name}")
        for p in orphans:
            print(f"[dry-run] 归档孤立页面 {p.name} → _trash/")
        for r in records:
            if r["old_file"] != r["new_file"]:
                print(f"[dry-run] 重命名 {r['old_file']} → {r['new_file']}")
        for ch in chapters:
            print(f"[dry-run] 第 {ch['n']} 讲  {ch['file']}  {ch['title']}")
        print("[dry-run] 未写入任何文件")
        return

    # ---------- 先在内存里改好全部正文，避免改到一半留下半成品 ----------
    patched: list[tuple[Path, str]] = []
    for idx, r in enumerate(records):
        ch = r["ch"]
        path = outdir / r["old_file"]
        html = C.read_text(path)
        prev = chapters[idx - 1] if idx > 0 else None
        nxt = chapters[idx + 1] if idx + 1 < len(chapters) else None
        html = patch_chapter(html, ch, manifest, prev, nxt)
        html = fix_crossrefs(html, old_to_new, chapters)
        patched.append((outdir / r["new_file"], html))

    # ---------- 归档残留与孤立页面 ----------
    trash = outdir / "_trash"
    for src, dst in tmp_actions:
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst = _trash_path(trash, dst.name) if dst.parent == trash else dst
        src.rename(dst)
        if dst.parent == trash:
            print(f"归档残留 {src.name} → _trash/{dst.name}")
        else:
            print(f"恢复残留 {src.name} → {dst.name}")
    for p in orphans:
        trash.mkdir(exist_ok=True)
        dst = _trash_path(trash, p.name)
        p.rename(dst)
        print(f"归档孤立页面 {p.name} → _trash/{dst.name}")

    # ---------- 改名（带回滚） ----------
    moved: list[tuple[Path, Path]] = []
    plan = [r for r in records if r["old_file"] != r["new_file"]]

    def move(src: Path, dst: Path):
        if dst.exists():
            raise RuntimeError(f"目标已存在，已回滚：{dst}")
        src.rename(dst)
        moved.append((src, dst))

    try:
        for r in plan:
            move(outdir / r["old_file"], outdir / f"__tmp__{r['new_file']}")
        for r in plan:
            move(outdir / f"__tmp__{r['new_file']}", outdir / r["new_file"])
    except Exception as exc:
        for src, dst in reversed(moved):
            try:
                dst.rename(src)
            except OSError:
                pass
        C.die(str(exc))
    for r in plan:
        print(f"重命名 {r['old_file']} → {r['new_file']}")

    # ---------- 落盘 ----------
    for path, html in patched:
        C.save_text(path, html)

    style_data = C.load_style(manifest.get("style", C.DEFAULT_STYLE))
    index_html = scaffold.render_index(manifest, style_data)
    C.save_text(outdir / "index.html", index_html)
    C.save_json(manifest_path, manifest)

    print(f"已重编号 {len(chapters)} 讲")


if __name__ == "__main__":
    main()
