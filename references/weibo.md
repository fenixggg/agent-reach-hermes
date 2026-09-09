# 微博 / Weibo (weibo-cli + s_weibo_search.py)

## 安装与初始化

```bash
# 推荐使用 uv 或 pipx 安装 kabi-weibo-cli（命令名为 weibo）
uv tool install kabi-weibo-cli
# 或: pipx install kabi-weibo-cli

# 登录方式 1: 终端二维码（微博 App 扫码确认，约 3 分钟窗口）
weibo login --qrcode

# 状态验证
weibo status
```

> **登录机制与避坑（手动配置 Cookie）**：
> 部分系统或开启了 App-Bound Encryption 的浏览器（如 Chromium / Edge）可能无法直接通过本地浏览器提取登录态。此时可采用手动配置：
> 1. 浏览器登录 weibo.com → 按 `F12` 打开开发者工具 → `Application` → `Cookies`；
> 2. 复制 `SUB` 和 `SUBP` 两个核心 Cookie 键值；
> 3. 写入配置文件 `~/.config/weibo-cli/credential.json`：
>    ```json
>    {
>      "cookies": {
>        "SUB": "你的SUB值",
>        "SUBP": "你的SUBP值"
>      },
>      "saved_at": 1725800000
>    }
>    ```

## 凭证存放位置与维护说明

| 位置 | 说明 |
|---|---|
| `~/.config/weibo-cli/credential.json` | **CLI 与搜索脚本读取的主凭证**，包含 `{"cookies": {"SUB", "SUBP"}}` |
| profile `.env` | 可选灾备副本（如配置 `WEIBO_SUB`） |

- **凭证 7 天 TTL 机制与真相**：
  - `SUB` cookie 本身无内嵌过期（非 JWT），服务器端实际有效期通常 30 天以上；
  - `kabi-weibo-cli` 内部设置了 7 天的本地刷新建议期，TTL 到期后 CLI 会尝试从浏览器重新提取，提取失败时会输出警告 `using existing cookies` 自动回退；
  - **关键原则**：只要 API 没有返回 `ok=-100` 或搜索脚本没有报 `SESSION_EXPIRED`，现有凭据就完全可以继续使用，无需频繁重新扫码。真正失效时再重新抓取 SUB/SUBP 写入即可。

## 能力矩阵

| 功能 | 工具 | 状态 |
|---|---|---|
| 热搜榜 | `weibo hot --count 10` | ✅ 免登录也可用 |
| 关键词搜索 | **`s_weibo_search.py`** | ✅ 网页端精准解析，避开移动端风控 |
| 微博详情 | `weibo detail <mid>` | ✅ 完整正文+互动统计 |
| 评论流 | `weibo comments <mid> --count 10` | ✅ |
| 转发列表 | `weibo reposts <mid>` | ✅ |
| 用户资料/微博列表/关注/粉丝 | `weibo profile/posts/... <uid>` | ✅ |
| 热门时间线 | `weibo feed` | ✅ |
| 关注者时间线 | `weibo home` | 需登录（已配置） |

## 常用命令速查

```bash
# 1. 微博热搜榜 (免登录可用)
weibo hot --count 10

# 2. 微博关键词搜索 (使用自带 s_weibo_search 脚本，绕过移动版风控，精准稳定)
python <skill-path>/scripts/s_weibo_search.py "关键词" 1

# 3. 阅读单条微博全文 (mid 可从搜索结果或热搜中取得)
weibo detail <mid> --json

# 4. 评论与转发读取
weibo comments <mid> --count 10
weibo reposts <mid> --count 5

# 5. 用户资料与微博流
weibo profile <uid> --json
weibo posts <uid> --count 10

# 6. 时间线
weibo feed --count 10
```

## 已知避坑指南

- **`weibo search` 不可用**：官方移动 API 容器接口对 SUB cookie 常返回 `ok=-100`（会话无效）。搜索推荐统一调用本 Skill 内置的 `s_weibo_search.py`（直连 `s.weibo.com` 网页解析，非常稳定）。
- **`weibo login --cookie-source edge` 权限受限**：Edge 开启 App-Bound Encryption 会触发 `RequiresAdminError`。手动配置 `credential.json` 是最稳健的方案。
- **输出格式**：非 TTY 环境下 CLI 默认输出 YAML；在脚本或代码中解析时加上 `--json` 即可输出干净的 JSON 字典。
