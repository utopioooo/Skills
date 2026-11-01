#!/usr/bin/env python3
"""本地预览与截图：把“打开浏览器看一眼”变成可执行步骤。

用法：
    python scripts/preview.py --dir ./out                 # 起本地服务器并打开目录页
    python scripts/preview.py --dir ./out --screenshot    # 需要 pip install playwright
    python scripts/preview.py --dir ./out --screenshot --pages index.html,01.html

说明：
- 普通模式只用标准库（http.server + webbrowser），Ctrl+C 退出；
- 截图模式是可选的：未安装 Playwright 时打印安装方法并跳过，不影响交付；
- 截图默认覆盖目录页 + 第 1 讲，浅色/深色 × 1280/375 共 8 张，输出到 <dir>/_preview/。
"""

from __future__ import annotations

import argparse
import functools
import http.server
import sys
import threading
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _common as C


def pick_pages(outdir: Path, spec: str | None) -> list[str]:
    if spec:
        return [p.strip() for p in spec.split(",") if p.strip()]
    pages = ["index.html"]
    manifest_path = outdir / "manifest.json"
    if manifest_path.exists():
        manifest = C.load_json(manifest_path)
        chapters = manifest.get("chapters") or []
        if chapters:
            pages.append(chapters[0]["file"])
    else:
        others = sorted(p.name for p in outdir.glob("*.html") if p.name != "index.html")
        if others:
            pages.append(others[0])
    return [p for p in pages if (outdir / p).exists()]


def shoot(outdir: Path, pages: list[str]) -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(
            "未安装 Playwright，跳过截图。安装后可自动生成浅色/深色、桌面/手机四组截图：\n"
            "  pip install playwright\n"
            "  python -m playwright install chromium"
        )
        return 0

    out = outdir / "_preview"
    out.mkdir(exist_ok=True)
    count = 0
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for name in pages:
            url = (outdir / name).resolve().as_uri()
            for width, size in ((1280, "desktop"), (375, "mobile")):
                page = browser.new_page(viewport={"width": width, "height": 900})
                page.goto(url)
                page.wait_for_timeout(250)
                for theme in ("light", "dark"):
                    page.evaluate(
                        "t => document.documentElement.setAttribute('data-theme', t)", theme
                    )
                    page.wait_for_timeout(150)
                    target = out / f"{size}-{width}-{theme}-{name.replace('.html', '')}.png"
                    page.screenshot(path=str(target), full_page=True)
                    count += 1
                    print(f"  {target.name}")
                page.close()
        browser.close()
    print(f"已生成 {count} 张截图：{out}")
    print("请逐张检查：文字是否溢出、SVG 是否重叠、表格是否被裁、深色下是否有刺眼白块。")
    return 0


def serve(outdir: Path, port: int, open_browser: bool) -> int:
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(outdir))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    url = f"http://127.0.0.1:{port}/index.html"
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    print(f"本地预览：{url}")
    print("按 Ctrl+C 停止。")
    if open_browser:
        webbrowser.open(url)
    try:
        while True:
            thread.join(1)
    except KeyboardInterrupt:
        print("\n已停止。")
    finally:
        httpd.shutdown()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="课程文档本地预览与截图")
    ap.add_argument("--dir", required=True, help="课程输出目录")
    ap.add_argument("--port", type=int, default=8765, help="本地端口（默认 8765）")
    ap.add_argument("--no-browser", action="store_true", help="只起服务器，不自动打开浏览器")
    ap.add_argument("--screenshot", action="store_true", help="用 Playwright 生成截图（可选依赖）")
    ap.add_argument("--pages", help="截图页面，逗号分隔（默认 index.html + 第 1 讲）")
    args = ap.parse_args()

    outdir = Path(args.dir)
    if not outdir.is_dir():
        C.die(f"目录不存在：{outdir}")

    if args.screenshot:
        pages = pick_pages(outdir, args.pages)
        if not pages:
            C.die("没有可截图的 HTML 页面")
        print("开始截图：")
        return shoot(outdir, pages)
    return serve(outdir, args.port, not args.no_browser)


if __name__ == "__main__":
    raise SystemExit(main())
