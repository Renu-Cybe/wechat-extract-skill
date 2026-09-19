# 本包内置的 wechat-cli

## 是什么

`vendor/wechat-cli/` 是 [wechat-cli](https://github.com/huohuoer/wechat-cli) 的一份**内置副本**，
用来解微信数据库密钥。用法与本技能 `SKILL.md` 写的一致：`python entry.py <命令>`。

## 为什么要内置

公开仓库的 `main` 分支**只有旧的内存扫描法**，微信 **4.1+ 之后已失效**（密钥不再以 raw 形式留在内存里）。
能解 4.1+ 的 **Config.Cipher** 实现**不在公开分支上**——只存在于下面这几个提交里。
所以本包直接把这份实现内置，避免"照着文档 clone 公开仓库、结果一个密钥都拿不到"。

## 来源与版本

| 项 | 值 |
|---|---|
| 上游仓库 | `https://github.com/huohuoer/wechat-cli` |
| 公开 main 的 HEAD（内置副本的基线） | `a378923` — docs: add acknowledgement to wechat-decrypt |
| 内置副本实际内容 | 本地分支 `pr22` 的 HEAD `acfcd60` |
| 关键提交 | `c3cbe6b` 支持微信 4.1.x 版本密钥提取 ／ `3e13dc7` 集成 Windows 4.1+ Config.Cipher 密钥扫描 ／ `acfcd60` 修复 struct 模块导入 |
| 提交作者与日期 | maomao3334，2026-08-29 |
| 相对公开 main 的改动 | 2 个文件：`wechat_cli/keys/scanner_windows.py`（+275）、`wechat_cli/keys/common.py`（+34） |
| 补丁存档 | `vendor/windows-4.1-plus-config-cipher.patch`（13.8 KB，UTF-8 / LF） |

**关于来源的一句如实交代**：这几个提交**不在任何远端分支上**（`git branch -r --contains` 全部为空），
分支名 `pr22` 暗示它对应某个 PR #22，但**我们没有核到该 PR 的地址**，也不知道作者 maomao3334 与本项目的关系。
本文件只记录可核到的事实。

## 改了什么（相对公开 main）

Windows 的密钥提取从"内存里搜 raw key"换成 **Config.Cipher 路径**：
找到字符串 `com.Tencent.WCDB.Config.Cipher` → 顺引用读配置对象 → 固定 mask XOR 解码 → HMAC-SHA1 校验数据库第一页。

## 内置了什么、没内置什么

- **内置**：`entry.py`、`wechat_cli/`（含 `keys/scanner_windows.py`、`keys/scanner_macos.py`、`keys/scanner_linux.py`、
  `wechat_cli/bin/` 下 macOS 辅助文件约 46 KB）、`pyproject.toml`、`LICENSE`。合计约 189 KB / 34 个文件。
- **没内置**：上游的 `image/`（README 截图，约 4.7 MB）、`npm/`、各 README。

## 许可证

上游为 **Apache License 2.0**，副本随附 `LICENSE`。本包未修改这些源码文件本身。

## 如果你要把它提上游

补丁基线是公开 main 的 `a378923`：

```bash
git clone https://github.com/huohuoer/wechat-cli.git && cd wechat-cli
git checkout a378923
git apply <skill-dir>/vendor/windows-4.1-plus-config-cipher.patch
```

补丁已实测：`git apply --check` 与真打均通过（基线 `a378923`），打完后 `wechat_cli/keys/scanner_windows.py` 第 21 行会出现 `WINDOWS_CONFIG_CIPHER_NAME`。
