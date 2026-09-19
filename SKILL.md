---
name: wechat-extract-skill
description: "把本机微信的历史聊天记录提取出来交给 Agent：导出或检索私聊、群聊、联系人、群成员，按时间范围或关键词过滤，输出 Markdown 或 JSON。用户想把微信聊天记录导出给 AI、搜索微信历史消息、取某个人或某个群几个月甚至几年的聊天历史时，使用此技能。"
---

# WeChat Extract Skill

这个技能只做一件事：**把本机微信的聊天记录取出来，交给 Agent 使用。**
取到之后怎么用，由 Agent 按用户的需求处理。

**本包自带能用的工具本体**（`vendor/wechat-cli/`）：不需要 `git clone`，不需要联网拉代码。
为什么自带，见「为什么本包要自带一份工具」。

## 能拿到什么

命令都在 `vendor/wechat-cli/` 目录里跑，形式是 `python entry.py <命令>`：

| 命令 | 拿到什么 |
|---|---|
| `sessions --limit N` | 最近会话列表（谁最近在聊、未读数） |
| `history "某人或群名" --limit N` | 聊天记录本体 |
| `search "关键词" --chat "群名"` | 全库或指定会话内检索 |
| `export "对象" --format json/markdown --output out.json` | **导出成文件，交给 Agent 用这个** |
| `members "群名"` | 群成员 |
| `contacts` | 联系人 |
| `stats "群名"` | 发言人、消息类型、活跃时段 |
| `favorites` | 收藏 |
| `new_messages` | 上次之后的新消息 |

`history` / `search` / `export` 的 `--limit` 是默认值，不是上限，写大点能取全。

## 安装

前置条件：

- **Python ≥ 3.10**
- **微信桌面版已在这台机器上安装并登录过**——它读的是本地数据库，别的机器上的记录拿不到

```cmd
cd /d <skill-dir>\vendor\wechat-cli
pip install "click>=8.1,<9" "pycryptodome>=3.19,<4" "zstandard>=0.22,<1"

python <skill-dir>\scripts\find_db_dir.py                 # 1) 找数据目录
python entry.py init --db-dir "<第一步输出的路径>"          # 2) 提取密钥（微信要保持运行）
```

依赖清单以包内的 `pyproject.toml` 为准。Windows 上不需要管理员权限。

### ⚠️ 第 2 步之前，先花 30 秒确认你手里这份是对的

```cmd
findstr WINDOWS_CONFIG_CIPHER_NAME wechat_cli\keys\scanner_windows.py
```

| 结果 | 含义 | 怎么办 |
|---|---|---|
| **有输出** | ✅ 这份能解微信 4.1+ | 继续第 2 步 |
| **没有输出** | ❌ 你手里是**公开仓库的旧版**：它只会扫内存，在微信 4.1+ 上**必然一个密钥都取不到** | 停下来，改用本包 `vendor/wechat-cli/` 这份 |

**记牢这条判据**：没有命中时，继续跑下去得到 `0/N` 不是"环境问题"、不是"版本不被支持"，也不需要换工具或等上游——**是版本不对**。

### 为什么本包要自带一份工具

- 公开仓库 `huohuoer/wechat-cli` 的 **main 分支只有旧的内存扫描法**；微信 **4.1+ 之后这条路已死**
  （密钥不再以 raw 形式留在内存里，实测扫遍所有微信进程 0 命中）。
- 能解 4.1+ 的 **Config.Cipher** 实现**不在公开分支上**，所以本包直接把这份实现内置了。
- **不要 `git clone` 公开仓库来跑**——那正是"0 个密钥"的来源。若确实要 clone，也必须先确认上面那条 `findstr` 有输出，再往下走。
- 来源、提交号与许可证见 `vendor/NOTICE.md`；补丁另存 `vendor/windows-4.1-plus-config-cipher.patch`（可提上游）。

## 密钥

微信的数据库是**加密的**，每个 `.db` 各有自己的密钥，所有查询都靠它。

`init` 做的事是：在微信进程内存里找到字符串 `com.Tencent.WCDB.Config.Cipher` → 顺着引用读出配置对象 →
用固定 mask 做 **XOR 解码** → 从解码结果里取真密钥 → 用 **HMAC-SHA1 校验数据库第一页**确认。
结果写进 `~/.wechat-cli/all_keys.json`，同时把数据目录写进 `config.json`。

> ⚠️ **不是**"在内存里搜 `x'<64位十六进制>'` 那样直接捞密钥"——那个老办法在微信 4.1+ 上已经失效。
> 如果你看到的日志里**没有** `Config.Cipher 扫描: 找到 N 个名称匹配` 这一行，说明你跑的是旧实现。
> 细节与源码位置见 `references/keys.md`。

**三个前提：**

1. **微信必须正在运行并已登录。** 找不到进程会直接报 `Weixin.exe 未运行`。
2. **权限按平台不同：**

   | 平台 | 需要什么 |
   |---|---|
   | **Windows** | **不需要管理员**。同用户、同完整性级别即可 |
   | macOS | 要 `sudo`，且 init 会**给微信重签名**加调试权限（有副作用，会碰 TCC 权限） |
   | Linux | 要 root 或 `CAP_SYS_PTRACE` |

3. **只做一次。** 日常查询不用重跑。

**什么时候要重跑**（`python entry.py init --force`，微信要保持运行）：
微信升级之后 / 换了微信账号或重装微信 / 读不到新消息（通常是微信新建了消息分片）。

**怎么看成功没有**：结束时打 `结果: N/M salts 找到密钥`，并逐条列 `OK:` / `MISSING:`。

| 看到什么 | 什么意思 | 怎么办 |
|---|---|---|
| `Weixin.exe 未运行` | 微信没开 | 打开并登录微信，再跑一次 |
| 日志里没有 `Config.Cipher 扫描` 行 | **你跑的是公开仓库那份旧实现** | 改用本包 `vendor/wechat-cli/` 这份，别在旧版上继续排查 |
| `未能从任何微信进程中提取到密钥` | 一个都没取到 | ① 确认微信开着、权限够 ② **确认跑的是本包这份**（见上面 `findstr` 判据）③ 两者都满足仍失败，把**完整输出**交给 Owner 判断，**不要自行改换工具、也不要自己写实现** |
| `MISSING:` 若干行 | 部分分片没解出来 | 这些库对应的消息读不到；微信开着重跑一次（通常是刚新建了分片） |

细节见 `references/keys.md`。

## 日常用法

```cmd
set PYTHONIOENCODING=utf-8
cd /d <skill-dir>\vendor\wechat-cli
python entry.py sessions --limit 20
python entry.py history "某人或群名" --limit 2000
python entry.py export "对象" --format json --output chat.json
```

密钥已缓存在 `~/.wechat-cli/all_keys.json`（Windows 上是 `%USERPROFILE%\.wechat-cli\`），
平时不用重跑。

> **不要用 PowerShell 的 `>` 存输出**——会写成 UTF-16，之后读出来是二进制。
> 用 `cmd /c "... > file"`，或者直接用 `--output` 让工具自己写文件。

## 已知限制

- **图片和视频的内容读不出来**，只有 `[图片]` / `[视频]` 占位符。语音同理。
- **撤回和已删除的消息拿不到。**
- 只能读**本机、本账号、本机登录过**的记录。
- 那套解码依赖两个**与微信版本绑死**的东西：固定的 XOR mask 和配置对象的结构偏移（社区逆向，非官方接口）。
  微信大改内部结构时这一步可能整体失效——**届时是"等上游适配"，不是"自己重写"**。

## 数据与隐私

- 取到的是**这台机器、这个账号**的数据；换台机器就拿不到。
- `~/.wechat-cli/all_keys.json` **等于微信数据库的钥匙**：不要外传、不要提交进 git、
  不要放进任何会被同步或备份到别处的目录。
- 聊天内容里包含对话另一方的发言，那是对方的个人信息。怎么用、给谁看，自己把握。

## 排错

| 现象 | 去哪 |
|---|---|
| `[!] 未能自动检测到微信数据目录` | 用 `scripts/find_db_dir.py` 拿路径，显式传 `--db-dir` |
| `Weixin.exe 未运行` | 打开微信并登录，重跑 |
| 拿到 `0/N` 个密钥 / 日志里没有 `Config.Cipher 扫描` 行 | 先查上面那条 `findstr` 判据——**八成是你跑的是公开仓库的旧版** |
| `MISSING:` | 「密钥」一节的表 |
| 读不到新消息 / 微信升级后失效 | 重跑密钥（`init --force`），微信要保持运行 |
| 确认用的是本包这份、微信开着、权限够，仍然失败 | 把完整输出交 Owner；**不要自行换工具或重写实现** |
| 其他装不上、报错 | `vendor/NOTICE.md` 里的上游地址与 issue |
