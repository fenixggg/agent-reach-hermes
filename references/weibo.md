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

- **凭证有效期**：微博网页端 SUB cookie 通常具有滑动有效期。
- **失效识别**：搜索脚本报 `SESSION_EXPIRED` 时，重新扫码或更新 `credential.json` 即可。

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

## 注意事项

- **搜索机制说明**：`weibo-cli` 自带的 `weibo search` 走移动端 API，部分情况下可能返回会话无效；因此关键词搜索推荐统一使用本 Skill 内置的 `s_weibo_search.py` 脚本，该脚本直连 `s.weibo.com` 网页解析，兼容性更强。
- **输出格式**：非 TTY 环境默认输出 YAML；如果需要结构化数据，加上 `--json` 参数即可。
