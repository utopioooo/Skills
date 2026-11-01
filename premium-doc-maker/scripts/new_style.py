#!/usr/bin/env python3
"""从现有风格派生一个新风格包。

用法：
    python scripts/new_style.py --name sunset --from blue-ink

生成 styles/<name>/ 下的 5 个文件。接下来：
  1. 改 tokens.css 里的颜色（两套主题都要改，键必须一致）；
  2. 改 contrast.json 里的对比度门槛（默认 4.5，正文 7.0）；
  3. 跑 python scripts/validate.py --style-only <name>；
  4. 用 python scripts/scaffold.py --style <name> ... 生成新课程。
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _common as C

FILES = ("tokens.css", "components.css", "contrast.json", "chapter.html", "index.html")


def main():
    ap = argparse.ArgumentParser(description="派生新的风格包")
    ap.add_argument("--name", required=True, help="新风格名（目录名，建议 kebab-case）")
    ap.add_argument("--from", dest="base", default=C.DEFAULT_STYLE, help="基础风格包")
    ap.add_argument("--force", action="store_true", help="覆盖已存在的同名风格")
    args = ap.parse_args()

    if not args.name.replace("-", "").isalnum():
        C.die("风格名只能包含字母、数字和连字符")

    src = C.style_path(args.base)
    dst = C.STYLES_DIR / args.name
    if dst.exists():
        if not args.force:
            C.die(f"风格包已存在：{dst}（覆盖请加 --force）")
        shutil.rmtree(dst)
    dst.mkdir(parents=True)

    for name in FILES:
        shutil.copy2(src / name, dst / name)

    tokens_path = dst / "tokens.css"
    text = C.read_text(tokens_path)
    text = text.replace(f"Style pack: {args.base}", f"Style pack: {args.name}")
    C.save_text(tokens_path, text)

    print(f"已创建风格包：{dst}")
    for name in FILES:
        print(f"  - {name}")

    script = Path(__file__).resolve().parent / "validate.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--style-only", args.name],
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        C.die("新风格包没有通过对比度/令牌校验，先修 tokens.css 再使用")

    print("\n下一步：")
    print(f"  1) 编辑 styles/{args.name}/tokens.css（两套主题同时改）")
    print(f"  2) python scripts/validate.py --style-only {args.name}")
    print(f"  3) python scripts/scaffold.py --style {args.name} --outline outline.md --outdir ./out")


if __name__ == "__main__":
    main()
