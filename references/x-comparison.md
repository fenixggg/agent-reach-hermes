# X/Twitter 内容获取：三种路径对比

Agent Reach 的 twitter-cli、Hermes 内置的 `x_search`、以及第三方 bird-cli 都能操作 X/Twitter，但原理、成本和稳定性完全不同。

## 对比总览

| 维度 | Agent Reach + twitter-cli | Hermes 内置 x_search | bird-twitter（bird-cli） |
|------|--------------------------|---------------------|------------------------|
| 原理 | 逆向 Twitter GraphQL API | xAI 官方 Responses API | GraphQL + Sweetistics SaaS |
| 语言/安装 | Python, `pipx install` | Hermes 内置（xAI 后端） | TypeScript, `pnpm + build` |
| 成本 | **免费**（维护 Cookie） | **付费**（订阅或 API key） | 免费（GraphQL）/ 另付（Sweetistics） |
| 搜索稳定性 | ⚠️ 经常 404 | ✅ 官方渠道，稳定 | ⚠️ 同 twitter-cli，除非上 Sweetistics |
| 读 Timeline | ✅ `twitter feed` | ❌ 不支持 | ✅ `bird home` |
| 读单条推+回复 | ✅ `twitter tweet <URL>` | ✅ 搜索+自动总结 | ✅ `bird read` / `bird thread` |
| Thread 全貌 | ⚠️ 单条+回复 | 搜索返回 | ✅ `bird thread`（完整会话链） |
| 搜关键词 | ⚠️ 不稳定 | ✅ 稳定 | ⚠️ 同 twitter-cli |
| 自动 AI 总结 | ❌ 需自己搭 pipeline | ✅ Grok 直接返回 | ❌ 需自己搭 |
| 用户时间线 | ✅ `twitter user-posts` | ✅ 支持 | ✅ `bird user-tweets` |
| 用户资料 | ✅ `twitter user @user` | ❌ 不确定 | ❌ 只有 `whoami`（看自己） |
| 趋势/热门 | ❌ 不支持 | ❌ 不确定 | ✅ `bird trending` / `bird news` |
| 关注管理 | ❌ 不支持 | ❌ 不支持 | ✅ `bird follow/unfollow` |
| 媒体上传 | ❌ 不支持 | ❌ 不支持 | ⚠️ 仅 Sweetistics（4图/1视频） |
| 删推 | ✅ `twitter delete` | ❌ 不支持 | ❌ 不支持 |
| 多平台 | ✅ 13 个平台 | ❌ 仅 X | ❌ 仅 Twitter |
| LLM 友好输出 | ✅ `--compact --yaml` | ✅ 自带 | ❌ 只有原始 JSON |
| Cookie 维护 | ✅ 需要定期更新 | ❌ 不需要 | ✅ 需要定期更新（Windows 下同） |

## 什么时候选哪个

### 优先用 twitter-cli（免费）
- 读自己的**首页时间线**（`twitter feed`）
- 看**单条推文 + 回复**，不需要 AI 总结
- 看**用户时间线/资料**
- **不想花钱**，偶尔用用
- 维护 Cookie 的成本可以接受
- 需要**多平台**切换（小红书/B站/GitHub 等）

### 优先用 x_search（付费）
- **搜关键词找热点/讨论** — 需要稳定搜索
- 需要**自动 AI 总结**搜索结果
- 做**投研/情报采集**，需要可信来源引用
- 已经付费了 SuperGrok 或 X Premium+

### 什么时候考虑 bird-twitter
- **需要趋势/热门数据**（`bird trending`），这是它唯一的硬优势
- **需要管理关注**（follow/unfollow）
- 能接受 Node.js 工具链维护成本
- 注意：搜索稳定性和 twitter-cli 一样差（同走 GraphQL），Sweetistics 需额外付费

### 不建议切换的情况
- Windows 环境：bird 的自动 cookie 提取只支持 macOS，Windows 上手设 env 和 twitter-cli 一样
- LLM pipeline 集成：bird 输出格式不如 twitter-cli 的 `--compact --yaml` 友好
- 日常读推/查用户：功能重叠，twitter-cli 还多一个删推

## x_search 认证方式

通过 xAI 官方。三种方式：

| 方式 | 费用 | 适用场景 |
|------|------|---------|
| SuperGrok OAuth | $30/月 | 个人重度用户 |
| X Premium+ OAuth | $22~$30/月 | 已有 X Premium 会员 |
| XAI_API_KEY | 按量计费 | 开发/API 集成 |

## xAI API 按量计费价格（2026年）

| 模型 | 输入/1M tokens | 输出/1M tokens |
|------|:---:|:---:|
| Grok 4.3（旗舰聊天） | $1.25 | $2.50 |
| Grok Build 0.1（编程） | $1.00 | $2.00 |

缓存输入：$0.20/1M tokens。Batch API 享 5-8 折。Priority 优先处理 2x。

### x_search 单次成本估算

x_search 费用 = Token 费 + 工具调用费

典型搜索（500 token 输入 + 800 token 输出 + 1次工具调用）≈ **$0.033/次**。

充值 $10 ≈ **约 300 次搜索**。日常投研每天搜 5 次能用约 2 个月。

## 常见场景推荐

```yaml
# 场景：日常刷推看时间线
方案: twitter-cli (free)
命令: twitter feed -n 20

# 场景：搜某个话题的实时讨论
方案: x_search (paid, 稳定)
命令: (Hermes 内置, 无 CLI)

# 场景：看某个用户最近发了什么
方案: twitter-cli (free)
命令: twitter user-posts @elonmusk -n 20

# 场景：分析一条 Thread 的要点
方案: twitter-cli 抓取 + LLM 总结 (free)
命令: twitter tweet <URL> --compact > t.txt
       (喂给当前模型总结)

# 场景：需要可靠搜索+自动总结
方案: x_search (paid, 一步到位)
命令: (Hermes 内置)

# 场景：查看当前趋势/热点话题
方案: bird-cli (free, 需编译 Node 项目)
命令: bird trending
注意: 仅此功能值得 bird，其余不如 twitter-cli

# 场景：管理大量关注列表
方案: bird-cli
命令: bird follow/unfollow
```

## 注意

- twitter-cli 的 `search` 命令频繁因 Twitter GraphQL 改动返回 404，不是本地配置问题
- bird-cli 的 `search` 同样走 GraphQL，稳定性一致，Sweetistics 通道可绕过但需额外付费
- `x_search` 需要显式配置 xAI 凭据到 Hermes 才能使用
- 三种方式可以互补：免费抓取 + 付费搜索总结
- bird-cli Windows 下需 `pnpm install && pnpm run build` 编译一次，macOS 才有自动 cookie 提取