# 微信公众号搜索与文章提取 (WeChat Public Search)

基于搜狗微信官方数据源 (`weixin.sogou.com`)，专门解决 AI Agent 无法检索微信公众号文章的孤岛痛点。

---

## 1. 快速使用

### 搜索公众号文章 (默认返回 Markdown 列表)

```bash
python scripts/wechat_search.py "搜索关键词" --limit 5
```

### 搜索并输出结构化 JSON

```bash
python scripts/wechat_search.py "搜索关键词" --limit 5 --format json
```

---

## 2. 微信文章全文提取 (Fetch 工具兼容性测试结论)

获取到微信真实文章链接（`https://mp.weixin.qq.com/s?...`）后，各 fetch 工具的兼容性横评如下：

| 工具 | 速度 | 成本 | 提取质量 | 适用性与推荐 |
|:---|:---:|:---:|:---|:---|
| 🥇 **better-webfetch** | ⚡ **~0.3s** | 免费 (本地) | ⭐⭐⭐⭐⭐ (完全提取正文，自动剥离脚本与广告，转成干净 Markdown) | **第一首选** |
| 🥈 **Firecrawl scrape** | 🐢 ~3-5s | 消耗点数 | ⭐⭐⭐⭐☆ (依赖浏览器渲染，效果完整但速度慢、烧配额) | 备选兜底 |
| 🥉 **curl + Jina Reader** | 🐢 ~2-4s | 免费 | ⭐⭐⭐☆☆ (偶尔受到微信防外链影响或提示请在微信客户端打开) | 降级备用 |

### 最佳工作流
1. 调用 `python scripts/wechat_search.py "关键词" --limit 5` 获取真实微信 URL；
2. 选定目标文章后，调用抓取工具（如 `better-webfetch` 或其他网页提取脚本）提取全文：
   ```bash
   python <skills-path>/better-webfetch/scripts/fetch.py "微信直链URL"
   ```

---

## 凭证存放位置

**微信搜索无登录态**（2026-09-08 核实 wechat_search.py 源码）：脚本走搜狗微信（weixin.sogou.com），自动初始化 session cookie，无账号体系。唯一风险是高频触发搜狗验证码——报错时等几分钟再试即可，没有凭证可配。

## 频率与时效

- **频率控制**：单次任务搜索间隔至少 1 秒，避免触发搜狗 IP 点选验证码
- **链接时效**：搜狗解析出的微信链接带 timestamp+signature 临时签名，有效期约 2-3 天，搜索后应及时提取或归档
