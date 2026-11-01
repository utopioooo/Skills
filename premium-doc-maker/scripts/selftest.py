#!/usr/bin/env python3
"""自检：在临时目录跑通“生成 → 验收 → 重编号 → 打包”，并覆盖维护路径。

用法：
    python scripts/selftest.py

覆盖：
1. scaffold 生成 + 空壳被拦下
2. golden 成品课 0 error、可打包（zip 有顶层目录 / LICENSE / QA）
3. 真实重编号（换序）与删讲（孤立页面归档 _trash）
4. --add 改标题不会重复追加
5. 单页验收自动识别 manifest 里的风格包
6. 未转义尖括号、无 data-ref 的讲次引用能被拦下

不需要网络、不需要编译器；只依赖 Python 标准库与仓库内的示例。
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import traceback
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _common as C

SKILL = Path(__file__).resolve().parent.parent
PY = sys.executable
TMP_STYLE = "selftest-temp"


def run(args: list[str], expect: int | None = 0) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        [PY] + args,
        cwd=SKILL,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    if expect is not None and proc.returncode != expect:
        raise AssertionError(
            f"命令失败（期望 {expect}，实际 {proc.returncode}）：{' '.join(args)}\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return proc


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def mini_outline(path: Path, titles=("甲", "乙", "丙")) -> Path:
    lines = [
        "# 课程大纲：自检课",
        "- 课程名：自检课",
        "- 副标题：自检副标题",
        "- 品牌：翎光技术文档",
        "- 作者：自检作者",
        "- Slogan：自检口号",
        "- 年份：2026",
        "- 风格：blue-ink",
        "",
    ]
    for i, t in enumerate(titles, start=1):
        lines += [
            f"## 第 {i} 讲 {t}",
            f"- 摘要：{t}摘要",
            "- 阶段：基础",
            "### 小节",
            f"1. 引言：{t}",
            f"2. 一、{t}机制",
            f"3. 二、{t}实现",
            f"4. 三、{t}总结",
            "",
        ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def make_golden_course(root: Path) -> Path:
    """用 examples/golden/01.html + 一份单讲 manifest 组成最小可交付课程。"""
    out = root / "golden-course"
    out.mkdir()
    shutil.copy2(SKILL / "examples" / "golden" / "01.html", out / "01.html")
    manifest = {
        "version": 1,
        "course": "C++高性能编程与系统开发",
        "subtitle": "深入探索现代 C++ 性能极限，构建高效可靠的软件系统。",
        "brand": "翎光技术文档",
        "author": "翎光技术文档",
        "slogan": "探索技术深度，挖掘知识价值",
        "year": "2026",
        "style": "blue-ink",
        "width": 2,
        "chapters": [
            {
                "n": 1,
                "file": "01.html",
                "title": "CPU 缓存与数据局部性",
                "summary": "缓存层次、缓存行、伪共享、AoS 与 SoA",
                "stage": "核心机制",
                "level": "进阶",
                "minutes": "50",
                "sections": [
                    "引言：缓存决定性能上限",
                    "一、缓存层次与缓存行",
                    "二、伪共享与数据布局",
                    "三、访问模式与选型",
                    "四、总结与最佳实践",
                ],
            }
        ],
    }
    write_json(out / "manifest.json", manifest)
    run(["scripts/scaffold.py", "--index-only", "--outdir", str(out)])
    return out


def main() -> int:
    checks = []

    tmp_root = SKILL / ".selftest-tmp"
    shutil.rmtree(tmp_root, ignore_errors=True)
    tmp_root.mkdir()
    shutil.rmtree(SKILL / "styles" / TMP_STYLE, ignore_errors=True)
    try:
        root = tmp_root

        # 1. 脚手架
        out = root / "five"
        run(["scripts/scaffold.py", "--outline", "examples/outline.md", "--outdir", str(out), "--year", "2026"])
        manifest = json.loads(read(out / "manifest.json"))
        assert len(manifest["chapters"]) == 5, "应生成 5 讲"
        assert manifest["brand"] == "翎光技术文档", "品牌默认值应为翎光技术文档"
        assert manifest["author"] == "翎光技术文档", "未给作者时作者默认同品牌"
        assert (out / "index.html").exists() and (out / "05.html").exists()
        checks.append("scaffold：5 讲 + manifest + 目录页（品牌/作者）")

        # 2. 空壳必须被验收拦下
        proc = run(["scripts/validate.py", "--dir", str(out)], expect=1)
        assert "空小节" in proc.stdout, "空壳应报空小节"
        assert "待撰写" in proc.stdout, "空壳应报未完成标记"
        checks.append("validate：空壳被拦下")

        # 3. 成品课程：验收通过 + 打包结构
        golden = make_golden_course(root)
        proc = run(["scripts/validate.py", "--dir", str(golden)])
        assert "错误 0" in proc.stdout, f"成品课程应 0 错误：\n{proc.stdout}"
        checks.append("validate：golden 课程 0 错误")

        zip_path = root / "golden.zip"
        run(["scripts/pack.py", "--dir", str(golden), "--zip", str(zip_path)])
        names = zipfile.ZipFile(zip_path).namelist()
        prefix = "C++高性能编程与系统开发/"
        for required in ("README.txt", "LICENSE.txt", "QA.md", "manifest.json", "index.html", "01.html"):
            assert f"{prefix}{required}" in names, f"zip 缺少 {prefix}{required}"
        assert "作者：" in zipfile.ZipFile(zip_path).read(f"{prefix}README.txt").decode("utf-8")
        checks.append("pack：顶层目录 + README/LICENSE/QA")

        # 4. 真实重编号：换序后文件、标题、页脚、翻页全部同步
        mini = root / "mini"
        outline = mini_outline(root / "mini-outline.md")
        run(["scripts/scaffold.py", "--outline", str(outline), "--outdir", str(mini)])
        m = json.loads(read(mini / "manifest.json"))
        m["chapters"] = [m["chapters"][2], m["chapters"][0], m["chapters"][1]]
        write_json(mini / "manifest.json", m)
        run(["scripts/renumber.py", "--dir", str(mini)])
        m = json.loads(read(mini / "manifest.json"))
        assert [c["title"] for c in m["chapters"]] == ["丙", "甲", "乙"], "重编号后顺序不对"
        page01 = read(mini / "01.html")
        assert "<h1>丙</h1>" in page01, "01.html 应为丙"
        assert 'data-n="1"' in page01 and "共 3 讲" in page01, "页脚讲次/总数未同步"
        assert not list(mini.glob("__tmp__*")), "不应残留 __tmp__ 文件"
        checks.append("renumber：换序真实改名 + 页脚同步")

        # 5. 删讲：孤立页面归档到 _trash，不崩溃
        deleted = root / "mini-deleted"
        shutil.copytree(mini, deleted)
        m = json.loads(read(deleted / "manifest.json"))
        removed_title = m["chapters"][1]["title"]          # 删掉“甲”（当前 02.html）
        del m["chapters"][1]
        write_json(deleted / "manifest.json", m)
        run(["scripts/renumber.py", "--dir", str(deleted)])
        assert not list(deleted.glob("__tmp__*")), "删讲后不应残留 __tmp__ 文件"
        assert (deleted / "_trash").is_dir(), "孤立页面应归档到 _trash"
        assert "<h1>乙</h1>" in read(deleted / "02.html"), "删讲后 02.html 应为乙"
        assert removed_title == "甲"
        checks.append("renumber：删讲不崩溃 + 孤立页面归档")

        # 6. --add 改标题：按位置对齐，不重复追加
        added = root / "mini-added"
        run(["scripts/scaffold.py", "--outline", str(outline), "--outdir", str(added)])
        edited = mini_outline(root / "mini-outline-edited.md")
        text = read(edited).replace("## 第 2 讲 乙", "## 第 2 讲 乙改")
        edited.write_text(text, encoding="utf-8")
        proc = run(["scripts/scaffold.py", "--add", "--outline", str(edited), "--outdir", str(added)])
        m = json.loads(read(added / "manifest.json"))
        assert len(m["chapters"]) == 3, "--add 改标题不应新增讲次"
        assert "标题与 manifest 不一致" in proc.stdout, "应提示标题差异"
        checks.append("scaffold --add：改标题不重复")

        # 7. 单页验收自动使用 manifest 里的风格包
        style_dir = SKILL / "styles" / TMP_STYLE
        shutil.copytree(SKILL / "styles" / "blue-ink", style_dir)
        tokens = read(style_dir / "tokens.css").replace(
            "--header-a:     #1C5A9E;", "--header-a:     #123456;", 1
        )
        (style_dir / "tokens.css").write_text(tokens, encoding="utf-8")
        styled = root / "styled"
        run([
            "scripts/scaffold.py", "--style", TMP_STYLE,
            "--outline", str(outline), "--outdir", str(styled),
        ])
        proc = run(["scripts/validate.py", "--file", str(styled / "01.html")], expect=1)
        assert f"风格包：{TMP_STYLE}" in proc.stdout, "单页验收应识别 manifest 的风格包"
        assert "与风格包不一致" not in proc.stdout, "不应误报令牌不一致"
        checks.append("validate --file：自动读取 manifest 风格")

        # 8. 未转义的尖括号（行内代码）必须被拦下
        bad = root / "bad-escape.html"
        raw = read(SKILL / "examples" / "golden" / "01.html").replace(
            "<p>CPU 不以字节为单位搬运数据",
            "<p>例如 <code>std::vector<int></code> 很常见。CPU 不以字节为单位搬运数据",
            1,
        )
        bad.write_text(raw, encoding="utf-8")
        proc = run(["scripts/validate.py", "--file", str(bad)], expect=1)
        assert "疑似未转义" in proc.stdout, "行内未转义尖括号应被拦下"
        checks.append("validate：任意位置未转义尖括号")

        # 9. 无 data-ref 的讲次引用必须提示
        plain = read(mini / "01.html").replace(
            "</main>", "<p>另见第 2 讲。</p>\n</main>"
        )
        (mini / "01.html").write_text(plain, encoding="utf-8")
        proc = run(["scripts/validate.py", "--dir", str(mini)], expect=1)
        assert "没有 data-ref" in proc.stdout, "纯文本讲次引用应提示"
        checks.append("validate：无 data-ref 的讲次引用")

        # 10. 风格包校验 + 代码块枚举
        proc = run(["scripts/validate.py", "--style-only", "blue-ink"])
        assert "通过" in proc.stdout
        proc = run(["scripts/check_code.py", "--file", "examples/golden/01.html", "--list"])
        assert "2 个代码块" in proc.stdout
        checks.append("style-only / check_code 正常")
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)
        shutil.rmtree(SKILL / "styles" / TMP_STYLE, ignore_errors=True)

    print("自检通过：")
    for item in checks:
        print(f"  ✓ {item}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"自检失败：{exc}", file=sys.stderr)
        traceback.print_exc()
        raise SystemExit(1)
