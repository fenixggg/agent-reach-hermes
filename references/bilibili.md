# B站 / Bilibili (bilibili-cli)

## 安装与环境配置

```bash
# 推荐使用 pipx 或 uv 安装
pipx install bilibili-cli
# 或: uv tool install bilibili-cli
```

> **说明**：属于 `public-clis/bilibili-cli` 系列。免登录即可支持视频详情、字幕提取、热门排行榜、搜索等；用户收藏夹/动态互动等功能需扫码或配置 Cookie。

## 视频命令速查

```bash
# 视频详情（含播放量、点赞、投币、收藏等统计）
bili video BV19xwKeTEye
bili video BV19xwKeTEye --yaml          # Agent 友好结构化输出
bili video BV19xwKeTEye --json          # JSON 格式

# 字幕
bili video BV19xwKeTEye --subtitle      # 纯文本字幕
bili video BV19xwKeTEye --subtitle-timeline     # 带时间线字幕
bili video BV19xwKeTEye -st --subtitle-format srt  # 导出 SRT

# AI 总结 + 评论 + 相关推荐
bili video BV19xwKeTEye --ai            # B站 AI 总结
bili video BV19xwKeTEye --comments      # 热门评论
bili video BV19xwKeTEye --related       # 相关推荐
bili video BV19xwKeTEye --comments --related --json   # 合并输出
```

## 搜索

```bash
# 搜索用户（默认）
bili search "关键词"

# 搜索视频
bili search "关键词" --type video
bili search "关键词" --type video --max 5
```

## 发现

```bash
bili hot                                # 热门视频（第1页）
bili hot --page 2 --max 10              # 翻页
bili rank                               # 全站排行榜（3日）
bili rank --day 7 --max 30              # 7日榜
```

## 用户

```bash
bili user 27534330                      # UP 主资料
bili user "影视飓风"                     # 按用户名搜索
bili user-videos 27534330 --max 20      # 视频列表
```

## 收藏夹与动态

```bash
bili favorites                          # 收藏夹列表（需登录）
bili watch-later                        # 稍后再看
bili history                            # 观看历史
bili feed                               # 动态时间线（需登录）
```

## 互动（需登录）

```bash
bili like BV19xwKeTEye                  # 点赞
bili coin BV19xwKeTEye                  # 投币
bili triple BV19xwKeTEye                # 一键三连
```

## 认证

```bash
bili status                             # 检查登录状态
bili login                              # 扫码登录
```

大部分读命令无需登录。字幕、收藏夹、动态需要登录。

## 凭证存放位置与持久化说明

| 项 | 说明 |
|---|---|
| 登录态文件 | `~/.bilibili-cli/credential.json`（**CLI 实际读取的**，字段：sessdata/bili_jct/ac_time_value/buvid3/buvid4/dedeuserid/saved_at） |
| 登录状态机制 | SESSDATA 写入后支持收藏/动态/互动等完整权限 |
| 修复方式（推荐） | 浏览器登录 bilibili.com → F12 → Application → Cookies → 复制 `SESSDATA`、`bili_jct`、`dedeuserid`（buvid3/buvid4 可选）→ 直接改写 `credential.json` 对应字段 |
| 扫码登录的坑 | `bili login` 扫码确认后可能因风控拿不到 cookie（credential 全空），此时可用上述手动复制方式写入 |
| 需要登录的命令 | `favorites` / `watch-later` / `history` / `feed` / `like` / `coin` / `triple` |
| 免登录正常 | `hot` / `search` / `video` / `rank` / `user` / 字幕（实测正常） |

## 注意

> 与 yt-dlp 不同，**bilibili-cli 不会触发 412 反爬拦截**，因为它使用 B站官方 API 并正确处理了请求头。
> 如果遇到 `HTTP 412` / `RateLimitError`，稍等重试或减小 `--max`。
> 建议用 `--yaml` 输出，对 AI agent 更友好（非 TTY 环境默认输出 YAML）。
