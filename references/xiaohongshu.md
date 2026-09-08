# 小红书 / XiaoHongShu (xhs-cli)

## 安装与初始化

```bash
# 推荐使用 pipx 进行独立环境安装
pipx install xiaohongshu-cli

# 初始化登录（自动从支持的浏览器如 Chrome/Edge 提取本地 Cookie）
xhs login
```

## 稳定可用的命令

```bash
# 搜索笔记（推荐入口）
xhs search "query"

# 阅读笔记详情（必须用搜索结果中的 URL 或 ID，不能裸 note_id）
xhs read NOTE_ID_OR_URL

# 查看评论
xhs comments NOTE_ID_OR_URL

# 浏览热门
xhs hot

# 推荐 feed
xhs feed
```

## 已知不稳定的命令（v0.6.4）

```bash
# 以下命令当前可能返回 API error，谨慎使用：
xhs user USER_ID          # 可能返回 {code: -1}
xhs user-posts USER_ID    # 可能返回 {code: -1}
xhs favorites              # 可能返回 API error
```

## 凭证存放位置与持久化说明

| 项 | 说明 |
|---|---|
| Cookie 文件 | `~/.xiaohongshu-cli/cookies.json`（**CLI 实际读取的**，含 web_session 等键） |
| .env | 无需条目（xhs-cli 默认直接认本地 cookie 文件） |
| 失效恢复 | `xhs login`（自动从支持的浏览器提取 Cookie，需浏览器已登录小红书网页版） |
| 安全注意 | cookie 含 `web_session` 登录态，注意本地文件权限 |

## 重要注意事项

> **安装**: `pipx install xiaohongshu-cli`，然后 `xhs login`（自动从浏览器提取 Cookie）。
> Cookie 文件路径: `~/.xiaohongshu-cli/cookies.json`
>
> **xsec_token 限制**: 小红书强制 xsec_token 机制，**不能直接用裸 note_id 去读**。正确流程是：先 `xhs search` 或 `xhs feed` 获取结果，再用结果中的 URL/ID 去 `xhs read`。直接构造 note_id 会被拦截。
>
> **频率控制**: 高频请求（批量搜索、深翻评论）会触发验证码，这是平台限制无法绕过。建议每次操作间隔 2-3 秒。
>
> **POST 操作风险**: 发帖(post)、评论(comment)、点赞(like) 等写操作在 v0.6.x 可能因签名问题返回 406。如需使用，建议降级到 v0.3.5 (`pipx install xiaohongshu-cli==0.3.5`)。
