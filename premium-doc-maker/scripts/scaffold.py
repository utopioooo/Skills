#!/usr/bin/env python3
"""生成课程骨架：manifest.json + index.html + 各讲正文壳。

用法：
    python scripts/scaffold.py --outline outline.md --outdir ./out
    python scripts/scaffold.py --chapters chapters.txt --course "..." --outdir ./out
    python scripts/scaffold.py --index-only --outdir ./out

章节壳只包含结构与写作提示，正文需要按 references/markup-cookbook.md 填写；
validate.py 会把"空小节"判为错误，所以骨架不会被误当成成品。
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _common as C


def parse_args():
    ap = argparse.ArgumentParser(description="生成精品技术课程文档骨架")
    ap.add_argument("--outline", help="大纲文件（.md，推荐；含每讲小节标题）")
    ap.add_argument("--chapters", help="章节清单（.txt 每行 title|summary|stage，或 .json）")
    ap.add_argument("--outdir", required=True, help="输出目录")

    ap.add_argument("--course", help="课程名（覆盖大纲）")
    ap.add_argument("--subtitle", help="课程副标题（覆盖大纲）")
    ap.add_argument("--brand", help="品牌名（覆盖大纲）")
    ap.add_argument("--author", help="作者名（覆盖大纲；默认同品牌）")
    ap.add_argument("--slogan", help="品牌口号（覆盖大纲）")
    ap.add_argument("--year", help="页脚年份（默认当前年；固定值可保证重跑一致）")
    ap.add_argument("--style", help="风格包名（默认取大纲，否则 blue-ink）")
    ap.add_argument("--width", type=int, help="讲次文件名补零位数（默认 2，>99 讲自动扩位）")

    ap.add_argument("--force", action="store_true", help="覆盖已存在的 manifest 与正文（会丢失已写内容）")
    ap.add_argument("--add", action="store_true", help="追加新讲：保留已有正文，只生成新增讲次")
    ap.add_argument("--index-only", action="store_true", help="只按 manifest 重建目录页，不碰正文")
    ap.add_argument("--no-index", action="store_true", help="不生成目录页")
    ap.add_argument("--dry-run", action="store_true", help="只打印计划，不写文件")
    return ap.parse_args()


def render_index(manifest: dict, style_data: dict) -> str:
    chapters = manifest["chapters"]
    return C.render(
        style_data["index_tpl"],
        {
            "STYLE_CSS": style_data["css"],
            "COURSE": C.esc(manifest["course"]),
            "SUBTITLE": C.esc(manifest["subtitle"]),
            "SUBTITLE_ATTR": C.esc_attr(manifest["subtitle"]),
            "BRAND": C.esc(manifest["brand"]),
            "AUTHOR": C.esc(manifest.get("author") or manifest["brand"]),
            "SLOGAN": C.esc(manifest["slogan"]),
            "YEAR": C.esc(manifest["year"]),
            "TOTAL": len(chapters),
            "STAGE_GROUPS": C.build_stage_groups(chapters, manifest.get("width", 2)),
        },
    )


def main():
    args = parse_args()
    outdir = Path(args.outdir)
    manifest_path = outdir / "manifest.json"

    # ---------- 仅重建目录页 ----------
    if args.index_only:
        if not manifest_path.exists():
            C.die(f"--index-only 需要已有的 {manifest_path}")
        manifest = C.load_json(manifest_path)
        style_data = C.load_style(manifest.get("style", C.DEFAULT_STYLE))
        html = render_index(manifest, style_data)
        C.save_text(outdir / "index.html", html, dry_run=args.dry_run)
        print(f"已重建 index.html（{len(manifest['chapters'])} 讲，风格 {manifest.get('style')}）")
        return

    if not args.outline and not args.chapters:
        C.die("需要 --outline 或 --chapters（只重建目录页请用 --index-only）")

    if args.outline:
        meta, chapters = C.parse_outline(Path(args.outline))
    else:
        meta, chapters = {}, C.parse_chapter_list(Path(args.chapters))

    course = args.course or meta.get("course")
    if not course:
        C.die("缺少课程名：用 --course 指定，或在大纲头部写 '- 课程名：…'")

    subtitle = args.subtitle or meta.get("subtitle") or f"{course}：从原理到工程实践"
    brand = args.brand or meta.get("brand") or C.DEFAULT_BRAND
    author = args.author or meta.get("author") or brand
    slogan = args.slogan or meta.get("slogan") or C.DEFAULT_SLOGAN
    style = args.style or meta.get("style") or C.DEFAULT_STYLE
    year = args.year or meta.get("year") or str(date.today().year)

    width = args.width or max(2, len(str(len(chapters))))
    chapters = C.normalize_chapters(chapters, width)

    empty_titles = [ch["n"] for ch in chapters if not ch["title"]]
    if empty_titles:
        C.die(f"以下讲次缺少标题：{empty_titles}")

    for ch in chapters:
        if ch["sections"] and not (4 <= len(ch["sections"]) <= 6):
            C.die(
                f"第 {ch['n']} 讲给了 {len(ch['sections'])} 个小节，要求 4~6 个（见 content-blueprint.md）"
            )
        if not ch["sections"]:
            ch["sections"] = C.default_sections(ch["title"])
        if not ch["summary"]:
            print(f"提示：第 {ch['n']} 讲缺少摘要，目录卡片将只显示标题。")

    style_data = C.load_style(style)
    manifest = {
        "version": 1,
        "course": course,
        "subtitle": subtitle,
        "brand": brand,
        "author": author,
        "slogan": slogan,
        "year": str(year),
        "style": style,
        "width": width,
        "chapters": chapters,
    }

    existing_manifest = manifest_path.exists()
    if existing_manifest and not (args.force or args.add):
        C.die(
            f"{manifest_path} 已存在。继续生成会覆盖正文；确认请加 --force（重建整门课），"
            f"追加新讲用 --add，只重建目录页用 --index-only。"
        )

    if args.add:
        if not existing_manifest:
            C.die("--add 需要已有的 manifest，请先完整生成一次")
        old = C.load_json(manifest_path)
        old_chapters = old["chapters"]
        old_n = len(old_chapters)

        if len(chapters) < old_n:
            C.die(
                f"大纲只有 {len(chapters)} 讲，少于 manifest 的 {old_n} 讲。"
                f"删讲请直接编辑 manifest.json 的 chapters 后运行 renumber.py。"
            )

        # 按位置对齐：只有超出现有讲数的部分才是新增。
        # 旧版按标题匹配，改一个标题就会被误判成新讲并追加重复条目。
        changed = [
            (i, old_ch.get("title", ""), parsed["title"])
            for i, (parsed, old_ch) in enumerate(zip(chapters[:old_n], old_chapters), start=1)
            if parsed["title"] != old_ch.get("title")
        ]
        if changed:
            print("提示：以下讲次的标题与 manifest 不一致，已保留 manifest 标题：")
            for i, old_title, new_title in changed:
                print(f"  - 第 {i} 讲：{old_title} → {new_title}")
            print("  如需改名，请编辑 manifest.json 的 title 后运行 renumber.py；"
                  "或用 --force 重新生成（会覆盖正文）。")

        new_chapters = chapters[old_n:]
        if not new_chapters:
            print("大纲里没有新增讲次，未做修改。")
            return
        existing_titles = {c.get("title") for c in old_chapters}
        dupes = [ch["title"] for ch in new_chapters if ch["title"] in existing_titles]
        if dupes:
            C.die(f"新增讲次标题与已有讲次重复：{'、'.join(dupes)}；请先改名。")
        start = old_n
        for i, ch in enumerate(new_chapters, start=start + 1):
            ch["n"] = i
            ch["file"] = C.chapter_file(i, old.get("width", width))
        old_chapters.extend(new_chapters)
        manifest = old
        chapters = manifest["chapters"]
        style = manifest.get("style", style)
        style_data = C.load_style(style)
        course, brand = manifest["course"], manifest["brand"]
        author = manifest.get("author") or brand
        slogan, year = manifest["slogan"], manifest["year"]
        to_render = chapters[start:]
        print(f"追加 {len(to_render)} 讲（从第 {start + 1} 讲开始）")
    else:
        to_render = chapters

    total = len(chapters)

    # ---------- 逐讲渲染 ----------
    rendered = []
    skipped = []
    for ch in to_render:
        idx = chapters.index(ch)
        target = outdir / ch["file"]
        if target.exists() and not args.force:
            skipped.append(ch)
            continue
        prev_html, next_html = C.build_pager(chapters, idx)
        page = C.render(
            style_data["chapter_tpl"],
            {
                "STYLE_CSS": style_data["css"],
                "COURSE": C.esc(course),
                "BRAND": C.esc(brand),
                "AUTHOR": C.esc(author),
                "SLOGAN": C.esc(slogan),
                "YEAR": C.esc(year),
                "TITLE": C.esc(ch["title"]),
                "SUMMARY": C.esc(ch["summary"] or "本讲要点"),
                "SUMMARY_ATTR": C.esc_attr(ch["summary"] or "本讲要点"),
                "N": ch["n"],
                "TOTAL": total,
                "SECTIONS": C.build_sections(ch),
                "PREV_LINK": prev_html,
                "NEXT_LINK": next_html,
            },
        )
        rendered.append((ch, page))

    if not args.dry_run:
        outdir.mkdir(parents=True, exist_ok=True)
        C.save_json(manifest_path, manifest)
        if not args.no_index:
            C.save_text(outdir / "index.html", render_index(manifest, style_data))

    for ch, page in rendered:
        C.save_text(outdir / ch["file"], page, dry_run=args.dry_run)

    print(f"风格包：{style}")
    print(f"输出目录：{outdir.resolve()}")
    if not args.no_index:
        print("  - index.html（目录页，按阶段分组）")
    for ch, _ in rendered:
        print(f"  - {ch['file']}  {ch['title']}")
    for ch in skipped:
        print(f"  - {ch['file']}  已存在，跳过（--force 可覆盖）")
    if args.dry_run:
        print("\n[dry-run] 未写入任何文件。")

    print("\n下一步：")
    print("  1) 按 references/markup-cookbook.md 填写每个 <section> 的内容")
    if args.add:
        print(f"  2) python scripts/renumber.py --dir \"{outdir}\"（同步上一讲的“下一讲”链接）")
        print(f"  3) python scripts/validate.py --dir \"{outdir}\"")
    else:
        print(f"  2) python scripts/validate.py --dir \"{outdir}\"")
        print(f"  3) python scripts/pack.py --dir \"{outdir}\"")


if __name__ == "__main__":
    main()
