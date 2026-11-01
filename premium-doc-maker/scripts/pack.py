#!/usr/bin/env python3
"""验收 + 打包：先跑 validate.py，再把整门课打成带顶层目录的 zip。

用法：
    python scripts/pack.py --dir ./out
    python scripts/pack.py --dir ./out --zip ./C++高性能编程.zip
    python scripts/pack.py --dir ./out --skip-validate

zip 结构（买家解压后是一个独立的课程文件夹，多门课不会互相覆盖）：
    <课程名>/
        README.txt    打开方式与说明
        LICENSE.txt   版权与使用范围
        QA.md         验收记录
        manifest.json
        index.html
        01.html … NN.html
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import zipfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _common as C


def safe_filename(text: str) -> str:
    return re.sub(r'[\\/:*?"<>|]+', "-", text).strip() or "course"


README_TEMPLATE = """《{course}》
{line}

课程副标题：{subtitle}
作者：{author}
出品：{brand}
讲次数量：{total} 讲
版本：{year}

【怎么打开】
1. 解压后进入「{folder}」文件夹（不要只解压单个文件）；
2. 双击 index.html，用任意现代浏览器打开；
3. 页面右下角可切换浅色/深色主题，正文页底部可翻页。

【说明】
- 本套文档为单文件 HTML，全部样式与插图内联，离线可用；
- 每一讲包含讲解、代码示例、对比表与手写 SVG 图；
- 版权与使用范围见 LICENSE.txt；机器验收记录见 QA.md。
"""

LICENSE_TEMPLATE = """《{course}》文档版权与使用声明
{line}

作者：{author}
出品：{brand}
版本：{year}

1. 本套文档仅供购买者本人学习使用，不得转售、再分发或公开传播。
2. 未经 {brand} 书面授权，不得复制、改编后用于商业培训、课程或出版物。
3. 文档中的代码示例可在购买者自己的项目中自由使用；由此产生的技术风险由使用者承担。
4. 文档中涉及的第三方技术、商标与标准，其知识产权归各自权利人所有。
5. 如需团队授权、企业内训或二次开发授权，请联系 {brand}。
"""

QA_TEMPLATE = """# 交付验收记录

- 课程：{course}
- 作者：{author}
- 出品：{brand}
- 讲次：{total} 讲
- 风格包：{style}
- 打包日期：{date}

## 机器验收（validate.py）

```
{validate_output}
```

## 人工验收（必须另行确认）

- [ ] 1280px 与 375px 宽度下实际打开过目录页与至少一讲
- [ ] 浅色/深色主题切换正常，插图颜色不随主题变化
- [ ] 抽查至少 20% 讲次：无车轱辘话、性能数字有来源、代码能运行
- [ ] README、LICENSE 中的课程名/作者/品牌与本记录一致

> 机器验收只覆盖结构、令牌与一致性；内容质量与视觉呈现仍需人工确认。
"""


def run_validate(outdir: Path) -> tuple[int, str]:
    script = Path(__file__).resolve().parent / "validate.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--dir", str(outdir)],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def main():
    ap = argparse.ArgumentParser(description="验收并打包课程文档")
    ap.add_argument("--dir", required=True, help="课程输出目录")
    ap.add_argument("--zip", help="输出 zip 路径（默认：<课程名>.zip，放在输出目录的上一级）")
    ap.add_argument("--skip-validate", action="store_true", help="跳过验收（不推荐）")
    ap.add_argument("--year", help="README / LICENSE 里的版本年份（默认取 manifest）")
    args = ap.parse_args()

    outdir = Path(args.dir)
    manifest_path = outdir / "manifest.json"
    if not manifest_path.exists():
        C.die(f"找不到 {manifest_path}，先运行 scaffold.py")

    validate_output = "已跳过（--skip-validate）"
    if not args.skip_validate:
        code, output = run_validate(outdir)
        if code != 0:
            print(output)
            C.die("验收未通过，已停止打包；修完 validate.py 的 ERROR 后重跑。")
        validate_output = output

    manifest = C.load_json(manifest_path)
    chapters = manifest["chapters"]
    html_files = [outdir / "index.html"] + [outdir / ch["file"] for ch in chapters]
    missing = [p.name for p in html_files if not p.exists()]
    if missing:
        C.die(f"缺少文件：{', '.join(missing)}")

    course = manifest["course"]
    brand = manifest.get("brand", "")
    author = manifest.get("author") or brand
    year = args.year or manifest.get("year") or str(date.today().year)
    folder = safe_filename(course)

    zip_path = Path(args.zip) if args.zip else outdir.parent / f"{folder}.zip"
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    common = dict(
        course=course,
        line="=" * max(8, len(course) * 2),
        subtitle=manifest.get("subtitle", ""),
        author=author,
        brand=brand,
        total=len(chapters),
        year=year,
        folder=folder,
    )
    readme = README_TEMPLATE.format(**common)
    license_text = LICENSE_TEMPLATE.format(**common)
    qa = QA_TEMPLATE.format(
        **common,
        style=manifest.get("style", ""),
        date=str(date.today()),
        validate_output=validate_output,
    )

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        zf.writestr(f"{folder}/README.txt", readme)
        zf.writestr(f"{folder}/LICENSE.txt", license_text)
        zf.writestr(f"{folder}/QA.md", qa)
        zf.write(manifest_path, f"{folder}/manifest.json")
        for path in html_files:
            zf.write(path, f"{folder}/{path.name}")

    total_bytes = sum(p.stat().st_size for p in html_files) + manifest_path.stat().st_size
    print(f"已打包：{zip_path}")
    print(f"  顶层目录：{folder}/")
    print(f"  讲次：{len(chapters)} 讲")
    print(f"  原始体积：{total_bytes / 1024:.0f} KB")
    print(f"  压缩后：{zip_path.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
