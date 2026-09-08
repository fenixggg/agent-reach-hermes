# Twitter/X (twitter-cli)

## 稳定命令

```bash
# 首页时间线（最稳定）
twitter feed -n 20

# 读取单条推文（含回复）
twitter tweet URL_OR_ID

# 读取长文 / X Article
twitter article URL_OR_ID

# 用户时间线
twitter user-posts @username -n 20

# 用户资料
twitter user @username
```

## 可能不稳定的命令

```bash
# 搜索推文（Twitter 频繁改 GraphQL 端点，可能 404）
twitter search "query" -n 10
# 如果 search 返回 404，升级 twitter-cli：pipx upgrade twitter-cli

# likes（2024 年后只能看自己的，平台限制）
twitter likes
```

## 重要注意事项

> **安装**: `pipx install twitter-cli`（确保 v0.8.5+）
>
> **认证**: Hermes `.env` 中已配置 `AUTH_TOKEN` 和 `CT0`，twitter-cli 会自动读取环境变量。
>
> **IP 风控**: 不要在 VPS/数据中心 IP 上频繁调用，尤其是 followers/following，有封号风险。使用住宅代理或本地环境。
>
> **search 可能失效**: Twitter 频繁修改 GraphQL API，search 命令可能随时返回 404。如遇到，先 `pipx upgrade twitter-cli`。如果最新版仍不行，说明上游还没跟上 Twitter 的改动，用 `twitter feed` 替代。
>
> **输出格式**: 建议用 `--yaml` 或 `--json` 获得结构化输出，对 AI agent 更友好。
> **LLM-friendly 输出**: 用 `--compact` flag 获取精简字段输出（去掉了截断符号、时间格式等人类阅读优化），专为喂给 LLM 做后续总结/分析而设计。

## 凭证存放位置（2026-09-08 实测）

| 项 | 状态 |
|---|---|
| profile `.env` 的 `TWITTER_AUTH_TOKEN` + `TWITTER_CT0` | **CLI 实际读取的**（twitter-cli 自动读环境变量） |
| 独立凭据文件 | 无 |
| 当前状态 | ✅ 有效（实测 `twitter user` / `twitter feed` 正常返回） |
| 已知噪音 | `Failed to init ClientTransaction` 警告——不影响结果，忽略 |
| 失效恢复 | Cookie 过期后：浏览器登录 x.com → F12 → Application → Cookies → twitter.com → 导出 `auth_token` 和 `ct0` 值 → 更新 .env 两个变量 |

## LLM 集成：抓取 → 总结 Pipeline

twitter-cli **只负责抓取，不做总结**。常见的 Agent 工作流是两步走：

```bash
# step 1: 抓取结构化的推文数据
twitter user-posts @username -n 20 --compact --yaml

# step 2: 把输出喂给 LLM（当前 Hermes 模型 / xAI Grok API / Claude / GPT 均可）
# 在 prompt 里说："根据以下推文，总结这个人最近在关注什么话题"
```

> ⚠️ **区分清楚：**
> - **X Premium 内置的 "Summarize" 按钮** — X 官方 UI 功能（Grok 驱动），仅限 X.com/app 上使用，无法通过 CLI 调用。
> - **xAI Grok API** — 独立的 LLM API（`api.x.ai`），可以用它做第 2 步的总结，但需要额外配置 API key。
> - **本 skill 的定位** — 提供第 1 步的数据抓取能力，总结层复用 Hermes 已配置的任何模型。`--compact` 和 `--yaml`/`--json` flag 就是为这个 pipeline 设计的。
