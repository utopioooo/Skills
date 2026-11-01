#!/usr/bin/env python3
"""可选：对文档里的 C++ 代码块做语法检查（advisory，不阻塞交付）。

用法：
    python scripts/check_code.py --dir ./out
    python scripts/check_code.py --file ./examples/golden/01.html --strict

说明：
- 只做 `-fsyntax-only`，不链接、不运行；
- 片段缺少头文件、只截取关键行时会报错，这是正常的——本脚本用于发现明显的语法错误，
  不替代人工审阅；
- 机器上没有 g++/clang++ 时自动跳过，退出码 0。
"""

from __future__ import annotations

import argparse
import html
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _common as C

BLOCK_RE = re.compile(r"<pre[^>]*>\s*<code[^>]*>(.*?)</code>\s*</pre>", re.S)


def extract_blocks(path: Path) -> list[str]:
    raw = C.read_text(path)
    blocks = []
    for m in BLOCK_RE.finditer(raw):
        code = html.unescape(m.group(1)).strip("\n")
        if code.count("\n") >= 3:
            blocks.append(code)
    return blocks


def main():
    ap = argparse.ArgumentParser(description="C++ 代码块语法检查（可选）")
    target = ap.add_mutually_exclusive_group(required=True)
    target.add_argument("--dir", help="课程目录")
    target.add_argument("--file", help="单个 HTML")
    ap.add_argument("--compiler", default="g++", help="编译器命令（默认 g++）")
    ap.add_argument("--std", default="c++20", help="C++ 标准（默认 c++20）")
    ap.add_argument("--strict", action="store_true", help="有失败时返回退出码 1")
    ap.add_argument("--max-errors", type=int, default=20, help="最多打印多少个失败")
    ap.add_argument("--list", action="store_true", help="只列出每个文件有多少个代码块，不编译")
    args = ap.parse_args()

    files = [Path(args.file)] if args.file else sorted(Path(args.dir).glob("*.html"))

    if args.list:
        for path in files:
            print(f"{path.name}: {len(extract_blocks(path))} 个代码块")
        return 0

    compiler = shutil.which(args.compiler)
    if not compiler:
        print(f"未找到 {args.compiler}，跳过代码检查（安装编译器后可用）。")
        return 0

    total = 0
    failures = []

    for path in files:
        for idx, code in enumerate(extract_blocks(path), start=1):
            total += 1
            proc = subprocess.run(
                [compiler, f"-std={args.std}", "-fsyntax-only", "-x", "c++", "-"],
                input=code,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
            )
            if proc.returncode != 0:
                first = next(
                    (line for line in proc.stderr.splitlines() if "error:" in line),
                    proc.stderr.splitlines()[0] if proc.stderr else "未知错误",
                )
                failures.append((path.name, idx, first.strip()))

    print(f"检查 {total} 个代码块（{args.compiler} -std={args.std} -fsyntax-only）")
    for name, idx, msg in failures[: args.max_errors]:
        print(f"  FAIL {name} 代码块 #{idx}: {msg}")
    if len(failures) > args.max_errors:
        print(f"  … 另有 {len(failures) - args.max_errors} 个失败未列出")
    print(f"结果：{total - len(failures)} 通过 / {len(failures)} 失败")
    print("提示：片段缺头文件或只截取关键行时报错属正常，请人工判断。")

    return 1 if (args.strict and failures) else 0


if __name__ == "__main__":
    raise SystemExit(main())
