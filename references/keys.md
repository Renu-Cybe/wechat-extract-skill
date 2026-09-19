# 密钥：为什么需要、怎么拿、拿不到怎么办

这是整套东西唯一有技术难点的一步。查询本身很简单，**卡住的人基本都卡在这里**。

> **本文里的文件路径与行号，指的是本包内置的 `vendor/wechat-cli/`（分支 `pr22` / `acfcd60`）。**
> 公开仓库 `huohuoer/wechat-cli` 的 main 分支**没有**这份 Config.Cipher 实现，拿着行号去公开仓库找会对不上——
> 上一版文档就栽在这里：读文档的人找不到代码，于是不信文档、自己另找路。

---

## 密钥是什么

微信本地数据库（`db_storage` 下的 `message_*.db`、`contact.db` 等）是**加密的**，
每个 `.db` 各有一个密钥。密钥**不在磁盘上任何文件里**，只在微信进程的内存里——
但**不是**以 raw 形式放着，而是藏在 `com.Tencent.WCDB.Config.Cipher` 指向的配置对象里（见「原理」一节）。

所以 `init` 做的事是：**找到那个配置对象 → XOR 解码 → 取出每个库的密钥**，写进：

```
~/.wechat-cli/all_keys.json     # 密钥（敏感的钥匙）
~/.wechat-cli/config.json       # 数据目录路径
```

`all_keys.json` 的结构（`wechat_cli/core/config.py` 的 `STATE_DIR` / `KEYS_FILE`，
写入逻辑见 `wechat_cli/keys/common.py`）：

```json
{
  "bizchat\\bizchat.db": {
    "enc_key": "<十六进制密钥>",
    "salt": "<十六进制 salt>",
    "size_mb": 12.3
  }
}
```

（键是相对 `db_storage` 的路径，用平台原生分隔符；上面是 Windows 上的实际样子。
字段名 `enc_key` / `salt` / `size_mb` 已核对。）

**`all_keys.json` 是钥匙，不是配置。** 拿到它就等于拿到整个微信数据库，别外传、别进 git、
别放进任何会被同步或备份到别处的目录。

---

## 怎么拿：一条命令，但有前提

```cmd
python entry.py init          # 已初始化过就加 --force
```

**前提（缺一不可）：**

1. **微信必须正在运行，并且已登录。** 这不是建议——`scanner_windows.py` 里的 `_get_pids()`
   找不到 `Weixin.exe` 进程会**直接抛 `RuntimeError("Weixin.exe 未运行")`**。
2. **权限够。** 见下方平台差异。
3. **微信桌面版在这台机器上登录过。** 它读的是本地文件，别人的记录在别人的机器上。

数据目录**不要指望自动探测**——它在上游是坏的（见下节），一律用技能自带的
`scripts/find_db_dir.py` 拿路径，再显式传给 `--db-dir`。

---

## 平台差异：权限完全不同，别照抄

| 平台 | 需要什么 | 实现 |
|---|---|---|
| **Windows** | **不需要管理员权限**（实测） | `keys/scanner_windows.py`，用 `tasklist` 找 `Weixin.exe`，走 `Config.Cipher`（**本包 `vendor/wechat-cli/` 这份才有**；公开仓库 main 是旧的内存扫描） |
| macOS | 要 `sudo`；init 会**给微信重签名**（保留原有权限 + 加 `get-task-allow` 调试权限），并要求重启微信 | `keys/scanner_macos.py`，走 `task_for_pid`，**超时 120 秒** |
| Linux | 要 root，或 `CAP_SYS_PTRACE`（`sudo setcap cap_sys_ptrace=ep $(which python3)`） | `keys/scanner_linux.py`，读 `/proc/<pid>/mem` |

**结论：Windows 上不要习惯性提权。** 同一用户、同一完整性级别的进程，普通权限就能读微信内存；
先提权再排查，只会把问题搅浑。

macOS 那步**改动的是微信本体**（重签名），属于有副作用的操作，执行前先确认。

---

## 上游的自动探测是坏的（实测）

`wechat-cli init` **不带 `--db-dir`** 时，会去自动找数据目录——**在 Windows 上实测直接失败**：

```
[!] 未能自动检测到微信数据目录
```

原因在 `wechat_cli/core/config.py` 的 `_auto_detect_db_dir_windows()`：它读
`%APPDATA%\Tencent\xwechat\config\*.ini`，**把文件内容当成目录路径**判断。
而微信 4.x 在那儿写的不是路径，是简写：

| ini 文件 | 内容 | 探测代码的结果 |
|---|---|---|
| 某个 `.ini` | `MyDocument:` | 不是目录 → 跳过（**它其实指"我的文档"**） |
| 另一个 `.ini` | `D:` | 恰好是个目录（D 盘根）→ 拿去做根，再找 `D:\xwechat_files\*\db_storage`，当然没有 |

于是候选为空，`auto_detect_db_dir()` 返回 `None`，`init` 报错退出。

**绕过办法（也是技能里的默认做法）**：用 `scripts/find_db_dir.py` 拿路径，再显式传。

```cmd
python <skill-dir>/scripts/find_db_dir.py
python entry.py init --db-dir "C:\Users\<你>\Documents\xwechat_files\<wxid>\db_storage"
```

那个脚本解析简写（`MyDocument:` → 我的文档），并跳过光秃秃的盘符，再按三个平台的默认位置找。
它**也不保证覆盖所有情况**——微信允许把文件放到别的盘，真找不到就去
微信「设置 → 文件管理」看"文件保存位置"。

> 这是上游可以修的 bug，修好了 `init` 就能一把过。没修之前，技能里这一步必须显式传路径。

---

## 原理：为什么不能"扫内存找密钥"

**旧做法**：在微信进程内存里搜 `x'<64位十六进制>'` 这种形态，直接命中密钥。
**微信 4.1+ 之后这条路死了**——密钥不再以 raw 形式留在内存里。

实测代价：扫遍所有微信进程、几千个候选，**一个都没命中**。

> ⚠️ **公开仓库 `huohuoer/wechat-cli` 的 main 分支上就只有这个旧做法**，所以从它 clone 下来、在微信 4.1+ 上**必然 0 命中**。
> 本包内置的 `vendor/wechat-cli/` 才是下面这条能用的路径。

**现在 Windows 上的做法**（`keys/scanner_windows.py`）：

1. 内存里找字符串 `com.Tencent.WCDB.Config.Cipher`（常量 `WINDOWS_CONFIG_CIPHER_NAME`，第 21 行）
2. 顺着引用找到配置对象，读出一个 blob
3. **用固定 mask 循环异或解码**：`_xor_repeat(blob, WINDOWS_CONFIG_XOR_MASK)`（第 85 行），
   常量在第 22 行
4. 从解码结果里取密钥候选，用 **HMAC-SHA1 校验数据库第一页**确认

**版本绑定，这是最大的脆弱点**：那个 XOR mask 和结构偏移都是**和微信版本绑死的**。
微信大改内部结构，这一步就要重新适配（等上游更新，或再逆向一次）。
微信大版本升级后这一步可能整体失效，要等上游适配——这是使用前提，不是故障。

---

## 排错：源码里会打出来的确切信息

| 你看到 | 含义 | 怎么办 |
|---|---|---|
| `[!] 未能自动检测到微信数据目录` | 上游自动探测失效（见上节） | 用 `scripts/find_db_dir.py` 拿路径，显式传 `--db-dir` |
| `Weixin.exe 未运行` | 找不到微信进程 | 打开微信并登录，重跑 |
| `[+] Weixin.exe PID=… (…MB)` | 找到了，正在扫 | 正常，等它跑完 |
| `Config.Cipher 扫描: 找到 N 个名称匹配` | 找到了配置对象 | 正常 |
| `结果: N/M salts 找到密钥` | 一共 M 个库，解出 N 个 | N == M 就完了；N < M 见下 |
| `MISSING: <路径> (salt=…)` | 这个库没解出密钥 | 它对应的消息读不到；微信开着重跑一次（通常是刚生成新分片） |
| `未能从任何微信进程中提取到密钥` | 一个都没解出来 | ① 确认微信开着、权限够 ② **确认跑的是本包 `vendor/wechat-cli/` 这份**（`findstr WINDOWS_CONFIG_CIPHER_NAME wechat_cli\keys\scanner_windows.py` 必须有输出）③ 都满足仍失败：把完整输出交 Owner，**不要换工具、不要自己重写** |
| macOS：`task_for_pid 权限不足，正在对微信重新签名` | 正常流程 | 按提示重启微信，再 `sudo … init` |
| macOS：`密钥提取超时（120s）` | 超时 | 重试；仍失败看上游 issue |
| Linux：`需要 root 权限或 CAP_SYS_PTRACE` | 权限不够 | `sudo`，或 `setcap` |

---

## 什么时候要重跑

| 情况 | 要不要重跑 |
|---|---|
| 平时查聊天 | **不用**，密钥已缓存 |
| 微信升级之后 | **要**（可能连重跑都失效，见上面的版本绑定） |
| 换了微信账号 / 重装微信 | **要** |
| 读不到新消息 | **要**（微信通常新建了消息分片） |
| 微信重装但账号没变 | 试试，通常要 |

重跑就是加 `--force`：`python entry.py init --force`，**微信要保持开着**。
