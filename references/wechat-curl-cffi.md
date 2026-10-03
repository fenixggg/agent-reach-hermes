# 微信正文 curl_cffi 兜底（2026-10-03 实测配方）

## 症状判别
- wechat_search.py 产出的搜索直链 `mp.weixin.qq.com/s?src=11&timestamp=..&signature=..`：
  - better-webfetch(httpx) 返回 200 但只有 ~17KB，**页面无 `id="js_content"`** → fetch.py 报
    `"Markdown conversion produced empty output"`。空正文 ≠ 成功。
  - curl_cffi 同 URL 返回 ~3.5MB 完整页，含 `js_content`。
  - 分水岭是 **TLS 栈指纹**，不是 UA/header/cookie。

## 取数配方（实测通过）
```python
import os
from curl_cffi import requests as cr
r = cr.get(url, impersonate="chrome", timeout=20, proxy=os.environ.get("HTTPS_PROXY"))
ok = 'id="js_content"' in r.text   # True=拿到真页面
```
- `impersonate="chrome"` ✅；裸 curl_cffi + 普通 Chrome UA（不带 impersonate）也 ✅——关键在用 curl_cffi 而不是 httpx。
- **指纹池轮换（2026-10-03 教程精读落地，P0②）**：单一 JA3 指纹高频使用会被风控聚类。`s_wechat_article.py`
  已改为会话级随机轮换 `FINGERPRINT_POOL = ["chrome120","chrome124","edge101","safari17_0"]`。
  ⚠️ impersonate 自动配平 UA 与 TLS 指纹，**勿手动塞 UA 制造指纹矛盾**。自检: https://tls.browserleaks.com/json
- NewsCrawler 源码写死的 `FIXED_COOKIE="RK=..;wxtokenkey=777"` **非必需**（无 cookie 实测通过），移植时删除，别把别人的凭证当依赖。
- 本机代理保持即可（clear/keep 两种都验证成功）。

## 解析要点（若日后自建 s_wechat_article.py）
- 正文容器 `div#js_content`；公众号排版是深层 section 嵌套，需**递归 DOM 行走**按原文顺序输出 text/img/video；懒加载图取 `data-src`。
- 发布时间正则：`var createTime = '(\d{4}-\d{2}-\d{2} \d{2}:\d{2})';`；作者 `//span[@id='profileBt']`。
- 参考实现：NewsCrawler `crawlers/wechat.py`（391 行，parsel；含 cgiDataNew / `__QMTPL_SSR_DATA__` 兜底、`JsDecode('\x22..')` 反转义、`'xxx' * 1` 还原等踩坑细节；依赖 demjson3）。
- 克隆位置（研究快照）：`E:\AI Output\Hermes-Workspace\_research\NewsCrawler`。

## 风险备注
curl_cffi 过微信属猫鼠游戏，通道可能随时失效；失效时先按"症状判别"节重诊（对比响应体积 + js_content 探针），再考虑 firecrawl 渲染兜底。
