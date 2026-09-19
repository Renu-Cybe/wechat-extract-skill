# wechat-extract-skill

把**本机微信**的历史聊天记录取出来，交给 Agent 使用：导出或检索私聊、群聊、联系人、群成员，按关键词或时间筛选，输出 Markdown / JSON。

**这个包自带能用的工具本体**（`vendor/wechat-cli/`）——不需要 `git clone`，不需要联网拉代码。

## 30 秒确认你手里这份是对的

```cmd
findstr WINDOWS_CONFIG_CIPHER_NAME vendor\wechat-cli\wechat_cli\keys\scanner_windows.py
```

| 结果 | 含义 |
|---|---|
| **有输出** | ✅ 这份能解微信 4.1+，往下走 |
| **没有输出** | ❌ 是公开仓库的旧版：它只会扫内存，在微信 4.1+ 上**必然一个密钥都取不到** |

## 装法

把这个仓库（或 Release 里的 zip）放到你的 skills 目录，例如 `~/.agents/skills/wechat-extract-skill/`，然后：

```cmd
pip install "click>=8.1,<9" "pycryptodome>=3.19,<4" "zstandard>=0.22,<1"

cd /d <skill-dir>\vendor\wechat-cli
python <skill-dir>\scripts\find_db_dir.py
python entry.py init --db-dir "<第一步输出的路径>"
python entry.py sessions --limit 20
```

第二步跑之前先做上面那条 30 秒自检；提取密钥时**微信要保持运行**。

前置条件：Python ≥ 3.10；微信桌面版本机装过并登录过；Windows 上**不需要管理员权限**。

平台差异（macOS 要 `sudo` 且 init 会**给微信重签名**；Linux 要 root / `CAP_SYS_PTRACE`）、排错表、密钥何时要重跑，见 [`references/keys.md`](references/keys.md)。

## 为什么自带 `vendor/wechat-cli`

上游 [huohuoer/wechat-cli](https://github.com/huohuoer/wechat-cli) 的公开 `main` 分支**只有旧的内存扫描法**，微信 **4.1+ 之后这条路已死**——密钥不再以 raw 形式留在内存里，扫遍所有进程 0 命中。

能解 4.1+ 的 **Config.Cipher** 实现**不在公开分支上**，所以本包内置了这份实现。

来源仓库、基线提交、作者、许可证，以及一份可提上游的补丁，都在 [`vendor/NOTICE.md`](vendor/NOTICE.md)。

**实测**：微信 4.1.13.65 → `Config.Cipher 扫描匹配 20/20 salts` → `结果: 20/20 salts 找到密钥`，**3.1 秒**，日志里 `0 hex模式`（即没走旧路径）。

## 安全

- `~/.wechat-cli/all_keys.json` **等于微信数据库的钥匙**：别外传、别提交进 git、别放进任何会被同步或备份到别处的目录。
- **本仓库不含任何密钥**，也不含使用者的本机路径。
- 聊天内容里包含对话另一方的发言，属于对方的个人信息。

## 许可证

内置的 wechat-cli 副本为 **Apache License 2.0**（见 [`vendor/wechat-cli/LICENSE`](vendor/wechat-cli/LICENSE)）。
