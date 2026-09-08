# 知乎 / Zhihu（官方 Zhihu CLI）

## 安装与初始化（官方 CDN 一键包）

官方 Skill 包（含一键 setup 脚本，会自动从知乎官方 CDN 下载带四重校验的 CLI 二进制）：

```text
请下载安装 zhihu-cli skill 并完成初始化配置
https://developer-cdn.zhihu.com/zhihu-cli/releases/stable/skill/zhihu-cli-skill.zip
```

### 安装流程参考（Windows / PowerShell）：
```powershell
# 1. 下载并解压 zip 到 <profile>/skills/zhihu/
# 2. 安装与环境检查（自动从 developer-cdn.zhihu.com 下载，含 SHA-256 + 大小 + 域名 + 版本四重校验，装到用户本地目录）
powershell -ExecutionPolicy Bypass -File <skill-dir>\scripts\setup.ps1
# 3. 配置 Access Secret
#    密钥在 https://developer.zhihu.com/profile 生成（需实名认证）
#    配置环境变量即可：[Environment]::SetEnvironmentVariable("ZHIHU_ACCESS_SECRET","<新值>","User") 并填入 profile .env
```

> **说明**：知乎内容**不走普通网页抓取**（zhihu.com 反爬风控极严，普通抓取极易 403），通过官方 CLI（developer.zhihu.com 数据开放平台）直连是目前最稳定可靠的方案。

## 路径与调用方式

```powershell
# Zhihu CLI 默认安装在用户本地目录，例如 Windows 下：
$cli = "$env:LOCALAPPDATA\ZhihuCLI\current\zhihu-cli.exe"
# 终端执行：
powershell -Command "& '$cli' search zhihu --query '关键词' --count 5"
```

## 凭证存放位置与说明

| 位置 | 说明 |
|---|---|
| 用户环境变量 `ZHIHU_ACCESS_SECRET` | **CLI 实际读取的**（读取顺序：环境变量 > 系统密钥链） |
| profile `.env` | 可作为会话级环境变量或灾备副本 |
| 系统密钥链 | 备选存储介质（如 Windows Credential Manager / Keychain） |

- 凭证读取顺序：环境变量 > 系统密钥链 > AUTH_REQUIRED
- 换密钥：按平台更新 `ZHIHU_ACCESS_SECRET` 环境变量即可

## 常用命令速查

```powershell
# 搜知乎（返回标题/作者/摘要/Url/赞同数/评论数；摘要非全文）
powershell -Command "& '$cli' search zhihu --query '关键词' --count 5"

# 搜全网（站外新闻/官网，--search-db all|realtime|static）
powershell -Command "& '$cli' search global --query '关键词' --count 5"

# 知乎热榜（最多 30 条）
powershell -Command "& '$cli' hot --limit 20"

# 知乎直答（检索增强 AI 答案；模型 zhida-fast-1p5 | zhida-thinking-1p5 | zhida-agent）
powershell -Command "& '$cli' answer --query '问题'"

# 本人数据（当前不可用，见上）：me contents / me followees / me favorites lists|items|recent
# 知识库：knowledge bases / items / search / upload
# 额度查询（不消耗业务额度）
powershell -Command "& '$cli' quota"
```

## 额度（邀测期免费，自然日重置）

| 能力 | 每日额度 |
|---|---:|
| 知乎搜索 / 全网搜索 | 各 5,000 |
| 知乎用户数据 | 10,000 |
| 知乎热榜 / 知乎直答 | 各 100 |
| 知识库 | 500 |
| 小工具 | 10 |

## 使用边界

- `search` 返回的是**摘要**不是全文；读原文仍需配合网页抓取（知乎正文对抓取不友好，直答可做补充）
- 热榜适合发现议题，不等于事实核查
- 直答用于快速综合，深度研究优先用搜索拿原始来源
- 错误处理：`Code: 30001` 频率限制（停止重试）、`Code: 30002` 配额耗尽、退出码非 0 即失败（即使 HTTP 200 内含业务错误）
- 安全：不在回复/日志中复述完整 Access Secret；泄露后去个人中心删除重申
