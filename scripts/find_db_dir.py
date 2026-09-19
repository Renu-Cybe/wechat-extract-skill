#!/usr/bin/env python3
"""找微信的 db_storage 目录 —— 因为上游的自动探测在实测中是失效的。

为什么需要它：
    `wechat-cli init` 不带 --db-dir 时会自动探测，但在 Windows 上实测**直接失败**
    （`[!] 未能自动检测到微信数据目录`）。

    原因在 `wechat_cli/core/config.py` 的 `_auto_detect_db_dir_windows()`：
    它读 `%APPDATA%\\Tencent\\xwechat\\config\\*.ini`，把文件**内容当成目录路径**判断。
    而微信 4.x 在那里写的不是路径，是简写：

        51a1fffe....ini  ->  "MyDocument:"     # 指"我的文档"，不是目录 → 被跳过
        98ae43cd....ini  ->  "D:"              # 恰好是个目录（D 盘根）→ 拿去做根，
                                               # 然后找 D:\\xwechat_files\\*\\db_storage，当然没有

    结果 candidates 为空，探测返回 None。

用法：
    python find_db_dir.py            # 打印找到的 db_storage 路径
    python find_db_dir.py --json     # JSON 输出

拿到路径后：
    python entry.py init --db-dir "<路径>"
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import pathlib
import platform
import sys


def _read_config_roots(appdata: str) -> list[str]:
    """把 %APPDATA%\\Tencent\\xwechat\\config\\*.ini 的简写解析成真实目录。"""
    roots: list[str] = []
    config_dir = os.path.join(appdata, "Tencent", "xwechat", "config")
    if not os.path.isdir(config_dir):
        return roots
    for ini_file in glob.glob(os.path.join(config_dir, "*.ini")):
        content = None
        for enc in ("utf-8", "gbk"):
            try:
                with open(ini_file, "r", encoding=enc) as handle:
                    content = handle.read(1024).strip()
                break
            except (UnicodeDecodeError, OSError):
                continue
        if not content or any(ch in content for ch in "\n\r\x00"):
            continue
        # 微信写的是简写，不是路径——这一步是上游缺的
        if content.rstrip(":").lower() == "mydocument":
            roots.append(os.path.join(os.path.expanduser("~"), "Documents"))
            continue
        # 单个盘符（"D:"）不是有效的数据根，跳过；上游会让它通过，然后白找一圈
        if len(content) <= 3 and content.endswith(":"):
            continue
        if os.path.isdir(content):
            roots.append(content)
    return roots


def candidate_roots() -> list[str]:
    system = platform.system().lower()
    home = os.path.expanduser("~")
    if system == "windows":
        roots = _read_config_roots(os.environ.get("APPDATA", ""))
        # 无论 ini 怎么说，默认位置都试一遍
        roots.append(os.path.join(home, "Documents"))
        for drive in "CDEFGH":
            roots.append(f"{drive}:\\xwechat_files")
        roots.append(os.path.join(home, "xwechat_files"))
    elif system == "darwin":
        roots = [os.path.join(home, "Library/Containers/com.tencent.xinWeChat/Data/Documents")]
    else:
        roots = [os.path.join(home, "Documents")]
    seen, unique = set(), []
    for root in roots:
        key = os.path.normcase(os.path.normpath(root))
        if key not in seen:
            seen.add(key)
            unique.append(root)
    return unique


def find() -> list[str]:
    found: list[str] = []
    for root in candidate_roots():
        for match in glob.glob(os.path.join(root, "xwechat_files", "*", "db_storage")):
            if os.path.isdir(match):
                found.append(os.path.abspath(match))
        # 有些机器直接把 db_storage 放在根下
        direct = os.path.join(root, "db_storage")
        if os.path.isdir(direct):
            found.append(os.path.abspath(direct))
    return sorted(set(found))


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

    parser = argparse.ArgumentParser(prog="find_db_dir", description="找微信 db_storage 目录")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    hits = find()
    if args.json:
        print(json.dumps({"db_dirs": hits}, ensure_ascii=False, indent=2))
        return 0 if hits else 1

    if not hits:
        print("没找到 db_storage。", file=sys.stderr)
        print("微信可能把数据放在别的盘——打开微信 设置 → 文件管理，看'文件保存位置'。", file=sys.stderr)
        print("然后手动指定：python entry.py init --db-dir \"<那个位置>\\xwechat_files\\<wxid>\\db_storage\"",
              file=sys.stderr)
        return 1

    for hit in hits:
        print(hit)
    print("\n用它初始化：", file=sys.stderr)
    print(f'  python entry.py init --db-dir "{hits[0]}"', file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
