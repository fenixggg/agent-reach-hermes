# Agent-Reach for Hermes Agent

> **声明 / Attribution**:
> 本项目是基于 [Panniantong/Agent-Reach](https://github.com/Panniantong/Agent-Reach)（MIT License）针对 **Hermes Agent** 架构深度重构与适配的专有 Skill 版本。

---

## 🌟 简介

`agent-reach` 是专为 **Hermes Agent** 设计的全网信息触达与社交/内容平台采集 Skill。它将分散在各个平台的开源 CLI、官方开放接口及抓取脚本无缝聚合为清晰的路由器，赋予 AI 智能体直接读取全网公开内容、音视频字幕、社区讨论与行业动态的能力。

### ✨ 支持平台与能力矩阵

| 平台 / 类别 | 工具载体 | 核心能力 | 认证需求 |
| :--- | :--- | :--- | :--- |
| **知乎 (Zhihu)** | 官方 Zhihu CLI | 搜索、热榜、直答 | 需平台 Secret |
| **雪球 (Xueqiu)** | `snowball-cli` | 实时热帖、KOL观点、社区讨论 | 需 Cookie |
| **小红书 (XHS)** | `xhs-cli` | 笔记搜索、图文阅读（带 xsec） | 需本地 Cookie |
| **推特 / X** | `twitter-cli` | 推文读取、用户主页、时间线 | 需 Auth Token |
| **B站 (Bilibili)** | `bilibili-cli` | 视频详情、官方原生字幕提取、用户动态 | 公开只读免登录 |
| **Reddit** | `rdt-cli` | 帖子阅读、评论流、Subreddit 热门 | 需 Session / JWT |
| **微信公众号** | `wechat_search.py` | 搜狗微信直搜、落地真实 URL 解析 | 免登录 |
| **V2EX** | 官方公开 API | 节点主题、全站热门 | 免登录 |
| **豆瓣电影** | Rexxar API | 电影详情、影评、短评深度抓取 | 免登录 |
| **音视频转录** | `transcribe.py` (Whisper) | B站/YouTube/小红书音视频提取与 Groq 快速转录 | 需 Groq API Key |
| **GitHub / 开发** | `gh` CLI | 代码库检索、Issue/PR 联动 | 需 GitHub Auth |
| **网页全文阅读** | Jina / Firecrawl / better-webfetch | 通用正文提取与降噪 | 视选型而定 |

---

## 🚀 安装与使用

### 1. 安装到 Hermes Agent
将本项目克隆到你的 Hermes profile skills 目录下：

```bash
# 进入你正在使用的 Hermes profiles/xxx/skills 目录
cd path/to/hermes-home/profiles/<your-profile>/skills/

# 克隆仓库
git clone https://github.com/fenixggg/agent-reach-hermes.git agent-reach
```

### 2. 依赖工具配置（按需安装）
根据你需要的平台，安装对应的开源 CLI 工具：

```bash
# Python 平台 CLI
pipx install xiaohongshu-cli
pipx install bilibili-cli
pipx install "git+https://github.com/public-clis/rdt-cli.git"
pipx install twitter-cli

# Node / npm 工具 (如有需要)
npm install -g @snowball-tools/snowball-cli
```

### 3. 配置环境变量 / 凭据
根据 `references/` 目录下各平台的文档指引，配置你的 `.env` 或本地 CLI 认证文件。常见凭据说明：
- **Groq API Key** (`GROQ_API_KEY`): 用于 `scripts/transcribe.py` 的音视频高速 Whisper 转录。
- **Twitter Token** (`TWITTER_AUTH_TOKEN`, `TWITTER_CT0`): 写入环境变量供 `twitter-cli` 读取。
- **知乎 Access Secret** (`ZHIHU_ACCESS_SECRET`): 供知乎官方 CLI 调用。

---

## 📂 目录结构

```text
agent-reach/
├── SKILL.md                 # 核心路由定义与使用指令
├── LICENSE                  # MIT 开源许可证
├── README.md                # 项目文档
├── references/              # 16 个平台的单独运维与最佳实践指导
│   ├── bilibili.md
│   ├── douban.md
│   ├── reddit.md
│   ├── twitter.md
│   ├── xiaohongshu.md
│   ├── xueqiu.md
│   ├── zhihu.md
│   └── ...
└── scripts/                 # 辅助脚本
    ├── wechat_search.py     # 微信公众号搜索与直链解析
    ├── transcribe.py        # 多平台音视频转文字稿
    └── transcribe_format.md # 转录文本格式规范
```

---

## ⚖️ 开源协议与鸣谢

- 本项目基于 [MIT License](LICENSE) 开源。
- 感谢 [Panniantong/Agent-Reach](https://github.com/Panniantong/Agent-Reach) 提供的灵感与原始架构设计。
