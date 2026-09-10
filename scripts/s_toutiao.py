#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""今日头条文字内容抓取（解析页面 SSR 内嵌数据，免登录 / 免签名 / 纯标准库）

定位: 文字内容专精 —— 搜索 / 文章正文 / 微头条 / 评论 / 热榜。
      视频已放弃（技术不可行）：头条原生视频 ≈ 抖音系，视频流需登录态+签名，
      yt-dlp 内置 toutiao extractor 亦报 "No video formats found"。

为什么自建：
  - 公开的旧接口全部废弃：www.toutiao.com/api/search/content/ → 计数恒 0；
    /api/comment/list/ → 500；/2/comment/list/ → 404。
  - RSSHub 头条路由只有频道流、无关键词搜索，且需 Docker 常驻。
  - 通用抓取器（Firecrawl / better-webfetch）对头条失效：桌面版是 JS 空壳（0 可见文本），
    Firecrawl 抓文章页持续 500。
  - 真相：头条把搜索结果与正文都内嵌在页面 SSR 数据里，用对 UA 直接解析即可。

用法:
  python s_toutiao.py search "关键词" [--type article|weitoutiao|all] [--limit N] [--period 1|7|30|365]
  python s_toutiao.py read <gid|URL> [--comments N]        # 正文（自动判别 文章/微头条）+ 可选评论
  python s_toutiao.py comments <gid|URL> [--limit N] [--replies]
  python s_toutiao.py hot [--limit N]                      # 热榜
全局选项: --format json|md  (默认 md)

依赖: 仅标准库。无需 cookie、无需 API Key、无需登录。

关键实现要点（均为实测结论，勿随意改动）:
  1. 移动版域名必须用 iPhone UA —— 桌面 UA 会被 302 跳到 www 版（JS 空壳，抓不到正文）。
  2. 正文位置：<script id="RENDER_DATA"> → URL 解码 → JSON。
     文章: articleInfo.content         微头条: articleInfo.thread.threadBase.content
  3. 搜索结果是 <script data-druid-card-data-id="...">{JSON}</script> 卡片。
  4. 评论主接口的参数 aid=13 是必需的，缺了报 "params illegal"。
  5. 评论数据嵌在 data[i].comment 里；回复是空的，必须二段式调 reply_list。
  6. 搜索偶发"空手"（约 5%，**随机抖动，与频率无关**）→ 内建重试覆盖。
     压测 104 次请求成功率 99%（含零间隔连打），无硬性频率限制，不需要刻意降频。
     不要用 HTML 长度判断是否成功（会误伤视频页），只认"解析出的卡片数"。
"""
import argparse
import gzip
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# ---- 常量 ----
UA_PC = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
         "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
UA_M = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")

SEARCH_URL = "https://so.toutiao.com/search"
ARTICLE_URL = "https://m.toutiao.com/article/{gid}/"
WTT_URL = "https://m.toutiao.com/w/{gid}/"
HOT_URL = "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc"
COMMENT_URL = "https://api.toutiaoapi.com/article/v4/tab_comments/"
REPLY_URL = "https://www.toutiao.com/2/comment/v2/reply_list/"

PERIOD_MAP = {1: "一天内", 7: "一周内", 30: "一月内", 365: "一年内"}
# 只保留文字内容通道。video 已移除（见模块 docstring：头条视频抓取技术不可行）。
TYPE_MAP = {"article": "information", "weitoutiao": "weitoutiao"}

# 清空代理：本机 HTTP_PROXY 会污染请求路径导致 404（已知坑）
for _v in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    os.environ.pop(_v, None)


# ---- 基础工具 ----
def _fetch(url, ua=UA_PC, referer=None, timeout=25):
    """带重试的 GET，返回 (status, text)。"""
    headers = {
        "User-Agent": ua,
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept-Encoding": "gzip",
        "Accept": "text/html,application/xhtml+xml,application/json,*/*;q=0.8",
    }
    if referer:
        headers["Referer"] = referer
    last_err = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    body = gzip.decompress(body)
                return r.status, body.decode("utf-8", "ignore")
        except urllib.error.HTTPError as e:
            try:
                b = e.read()
                if e.headers.get("Content-Encoding") == "gzip":
                    b = gzip.decompress(b)
                return e.code, b.decode("utf-8", "ignore")
            except Exception:
                return e.code, ""
        except Exception as e:
            last_err = e
            time.sleep(1.5 * (attempt + 1))
    return None, "ERROR: %s" % last_err


def _strip_html(s):
    if not s:
        return ""
    if not isinstance(s, str):        # 视频卡片的 title/summary 可能是 dict
        if isinstance(s, dict):
            s = s.get("text") or s.get("title") or s.get("summary") or ""
        if not isinstance(s, str):
            s = str(s)
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = re.sub(r"</p>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("&nbsp;", " ").replace("&amp;", "&").replace("&quot;", '"').replace("&lt;", "<").replace("&gt;", ">")
    return re.sub(r"\n{3,}", "\n\n", s).strip()


def _looks_like_text(s):
    """判断是否像真实文本（过滤纯数字/编码串等噪声，如视频卡片的 summary 高亮编码）。"""
    if not s or not isinstance(s, str):
        return False
    s = s.strip()
    if len(s) < 2:
        return False
    # 含中文/字母/常见标点，且不是纯数字串
    if re.search(r"[\u4e00-\u9fa5A-Za-z]", s):
        return True
    return False


def _ts(v):
    """unix 时间戳 -> 字符串。"""
    try:
        n = int(v)
    except (TypeError, ValueError):
        return str(v or "")
    if n <= 0:
        return ""
    # 毫秒级时间戳归一
    if n > 10 ** 12:
        n //= 1000
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(n))


def _get_render_data(html):
    """从页面提取 RENDER_DATA（URL 编码的 JSON）。"""
    m = re.search(r'id="RENDER_DATA"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        return None
    try:
        return json.loads(urllib.parse.unquote(m.group(1)))
    except Exception:
        return None


def _extract_gid(s):
    """从 URL 或裸 ID 里取出内容 ID。"""
    s = (s or "").strip()
    m = re.search(r"/(?:article|group|item|w|video|trending)/(\d{10,25})", s)
    if m:
        return m.group(1)
    m = re.search(r"(\d{10,25})", s)
    return m.group(1) if m else s


# ---- 搜索 ----
def _native_url(gid, pd=None):
    """构造给人点击的链接。

    ⚠️ 必须用头条官方的 **group 形态** `https://toutiao.com/group/{gid}/`：
      - 它会按访问者 UA 自动派发：移动 UA → m.toutiao.com（SSR 真内容）；
        桌面 UA → 原站/网页版
      - **不要**自己拼 `/article/{gid}/` 或 `/w/{gid}/`：实测这两种形态
        在桌面和安卓 UA 下都返回反爬 JS 挑战页（72914 字节，无内容）。
    该字段即搜索卡片里的 `ttsearch_msite_url` / `item_source_url` / `seo_url`（去掉追踪参数后的干净形态）。
    """
    if not gid or not gid.lstrip("-").isdigit() or int(gid) <= 0:
        return ""
    return "https://toutiao.com/group/%s/" % gid


def _parse_cards(html, pd="information"):
    """解析搜索页 <script data-druid-card-data-id> 卡片。"""
    out = []
    for m in re.finditer(r'<script[^>]*data-druid-card-data-id="([^"]+)"[^>]*>(.*?)</script>',
                         html, re.S):
        body = m.group(2).strip()
        if not body.startswith("{"):
            continue
        try:
            d = json.loads(body).get("data")
        except Exception:
            continue
        if not isinstance(d, dict):
            continue

        title = d.get("title")
        if not title:
            em = d.get("emphasis")
            if isinstance(em, dict):
                title = em.get("rich_content")

        content = d.get("content")
        if isinstance(content, dict):
            content = content.get("text")

        gid = str(d.get("group_id") or d.get("item_id") or d.get("id") or "")

        # 外链来源（媒体号常指向原文站；视频卡片指向站外如 bilibili.com）
        ext = (d.get("article_url") or d.get("open_url") or d.get("source_url")
               or d.get("share_url") or d.get("seo_url") or d.get("url") or "")
        if ext and not ext.startswith("http"):
            ext = "https://www.toutiao.com" + ext if ext.startswith("/") else ""
        # 过滤 sslocal:// 等 App 内部 scheme（打不开，无意义）
        if ext and not ext.startswith("http"):
            ext = ""
        if ext and "toutiao.com" in ext:
            ext = ""

        # 主链接优先用头条站内链接（由 gid 构造），外链单独保留
        url = _native_url(gid, pd)
        title = _strip_html(title)
        content = _strip_html(content or "")
        abstract = _strip_html(d.get("abstract") or content or "")
        # 过滤噪声（视频卡片的 highlight 编码串等）
        if not _looks_like_text(abstract):
            abstract = ""

        # 微头条的 title 字段往往就是正文本身 → 用首行做标题，正文完整保留
        if title and content and title[:40] == content[:40]:
            title = ""
        if not title:
            first = (content or abstract).split("\n")[0].strip()
            if first:
                title = first[:50] + ("…" if len(first) > 50 else "")

        # 少数卡片结构不同：标题藏在 display 里（dict 或 list 两种形态）
        if not title and isinstance(d.get("display"), (dict, list)):
            disps = d["display"] if isinstance(d["display"], list) else [d["display"]]
            for disp in disps:
                if not isinstance(disp, dict):
                    continue
                emph = disp.get("emphasized") if isinstance(disp.get("emphasized"), dict) else {}
                info = disp.get("info") if isinstance(disp.get("info"), dict) else {}
                summ = disp.get("summary") if isinstance(disp.get("summary"), dict) else {}
                cands_t = [_strip_html(disp.get("title")), _strip_html(emph.get("title")),
                           _strip_html(disp.get("_title"))]
                cands_a = [_strip_html(disp.get("abstract")), _strip_html(emph.get("summary")),
                           _strip_html(summ.get("text"))]
                t = next((x for x in cands_t if _looks_like_text(x)), "")
                a = next((x for x in cands_a if _looks_like_text(x)), "")
                if t or a:
                    title = (t or a)[:60] + ("…" if len(t or a) > 60 else "")
                    if a and a != t:          # 摘要不要与标题重复
                        abstract = a
                    if info.get("site_name"):
                        d["_site"] = info["site_name"]
                    elif info.get("domain"):
                        d["_site"] = info["domain"]
                    break

        if not title and not abstract:
            continue

        out.append({
            "title": title,
            "abstract": abstract,
            "content": content,
            "source": d.get("_site") or d.get("media_name") or d.get("source") or d.get("detail_source") or "",
            "author": (d.get("user") or {}).get("name") if isinstance(d.get("user"), dict) else "",
            "time": _ts(d.get("publish_time") or d.get("create_time") or d.get("datetime")),
            "gid": gid,
            "url": url,
            "ext_url": ext,
            "digg": d.get("digg_count"),
            "comments": d.get("comment_count"),
            "is_video": bool(d.get("video_duration") or d.get("has_video")),
        })
    return out


def search(keyword, kind="article", limit=10, period=None):
    """关键词搜索。kind: article | weitoutiao | all（视频通道已移除，见模块 docstring）"""
    kinds = ["information", "weitoutiao"] if kind == "all" else [TYPE_MAP.get(kind, "information")]
    results = []
    errors = []

    for pd in kinds:
        url = ("%s?keyword=%s&pd=%s&dvpf=pc&source=input"
               % (SEARCH_URL, urllib.parse.quote(keyword), pd))
        if period:
            url += "&filter_period=%d" % period

        # 搜索偶发"空手"（实测约 12%，返回体明显偏小且无卡片）→ 重试
        # 注意：不要用 HTML 长度做判据（视频页 224KB、空响应 210KB，太接近会误伤），
        # 只认"解析出的卡片数"。
        cards = []
        for attempt in range(3):
            st, html = _fetch(url, UA_PC, "https://so.toutiao.com/")
            if st == 200:
                cards = _parse_cards(html, pd)
                if cards:
                    break
            time.sleep(1.5)
        if not cards:
            errors.append("pd=%s 未取到结果" % pd)
        for c in cards:
            c["type"] = pd
            results.append(c)
        time.sleep(0.8)

    if not results and errors:
        return {"status": "error", "error": "; ".join(errors), "results": []}
    return {
        "status": "ok",
        "keyword": keyword,
        "type": kind,
        "period": PERIOD_MAP.get(period) if period else None,
        "count": len(results[:limit]),
        "results": results[:limit],
        "fetched_at": time.strftime("%Y-%m-%d %H:%M"),
    }


# ---- 正文 ----
def read(gid_or_url):
    """读正文，自动判别 文章 / 微头条。"""
    gid = _extract_gid(gid_or_url)

    # 先试文章
    st, html = _fetch(ARTICLE_URL.format(gid=gid), UA_M, "https://m.toutiao.com/")
    data = _get_render_data(html) if st == 200 else None
    if data:
        ai = data.get("articleInfo", {}) or {}
        if ai.get("content"):
            return {
                "status": "ok", "kind": "article", "gid": gid,
                "title": _strip_html(ai.get("title")),
                "source": ai.get("source") or ai.get("detailSource") or "",
                "author": (ai.get("mediaUser") or {}).get("name") if isinstance(ai.get("mediaUser"), dict) else "",
                "time": _ts(ai.get("publishTime")),
                "content": _strip_html(ai.get("content")),
                "digg": ai.get("diggCount"), "comments": ai.get("commentCount"),
                "is_original": ai.get("isOriginal"),
                "url": _native_url(gid),
            }

    # 再试微头条
    st, html = _fetch(WTT_URL.format(gid=gid), UA_M, "https://m.toutiao.com/")
    data = _get_render_data(html) if st == 200 else None
    if data:
        ai = data.get("articleInfo", {}) or {}
        tb = ((ai.get("thread") or {}).get("threadBase") or {})
        content = _strip_html(tb.get("content"))
        if content:
            title = _strip_html(tb.get("title") or "")
            # 微头条的 title 字段常等于正文 → 去重，避免标题与正文重复
            if title and (title[:40] == content[:40] or len(title) > 120):
                title = ""
            if not title:
                first = content.split("\n")[0].strip()
                title = first[:50] + ("…" if len(first) > 50 else "")
            user = tb.get("user") if isinstance(tb.get("user"), dict) else {}
            return {
                "status": "ok", "kind": "weitoutiao", "gid": gid,
                "title": title,
                "source": user.get("name") or "",
                "author": user.get("name") or "",
                "time": _ts(tb.get("createTime") or tb.get("displayCreateTime")),
                "content": content,
                "digg": tb.get("diggCount"),
                "url": _native_url(gid),
            }

    if st is None:
        return {"status": "error", "error": html[:200], "gid": gid}
    return {"status": "error", "error": "未取到正文（可能 ID 无效、内容已删除或为纯视频）", "gid": gid}


# ---- 评论 ----
def comments(gid_or_url, limit=20, with_replies=False):
    """评论列表。主接口 + 可选二段式取回复。"""
    gid = _extract_gid(gid_or_url)
    url = ("%s?group_id=%s&tab_index=0&aid=13&count=%d&offset=0&avatar_use_awebp=true"
           % (COMMENT_URL, gid, min(limit, 50)))

    st, raw = _fetch(url, UA_M, "https://m.toutiao.com/")
    if st != 200 or not str(raw).strip().startswith("{"):
        return {"status": "error", "error": "评论接口返回异常 (status=%s)" % st, "results": []}
    try:
        obj = json.loads(raw)
    except Exception as e:
        return {"status": "error", "error": "评论 JSON 解析失败: %s" % e, "results": []}

    if obj.get("err_no") not in (0, None):
        return {"status": "error", "error": obj.get("message", "未知错误"), "results": []}

    items = []
    for it in (obj.get("data") or []):
        c = it.get("comment") if isinstance(it, dict) else None
        if not isinstance(c, dict):
            continue
        items.append({
            "comment_id": str(c.get("id_str") or c.get("id") or ""),
            "user": c.get("user_name"),
            "user_id": c.get("user_id"),
            "verified": bool(c.get("user_verified")),
            "text": c.get("text"),
            "digg": c.get("digg_count"),
            "reply_count": c.get("reply_count") or 0,
            "time": _ts(c.get("create_time")),
            "replies": [],
        })

    # 二段式取回复（主接口内嵌 reply_list 常为空，即使 reply_count>0）
    if with_replies:
        for c in items:
            if not c["reply_count"] or not c["comment_id"]:
                continue
            ru = ("%s?id=%s&tab_index=0&count=20&offset=0&aid=13"
                  % (REPLY_URL, c["comment_id"]))
            rst, rraw = _fetch(ru, UA_M, "https://m.toutiao.com/")
            if rst != 200 or not str(rraw).strip().startswith("{"):
                continue
            try:
                ro = json.loads(rraw)
            except Exception:
                continue
            rdata = ro.get("data")
            rlist = (rdata.get("data") if isinstance(rdata, dict) else rdata) or []
            for r in rlist:
                if not isinstance(r, dict):
                    continue
                u = r.get("user") or {}
                c["replies"].append({
                    "user": u.get("screen_name") or u.get("name"),
                    "text": r.get("text"),
                    "digg": r.get("digg_count"),
                    "time": _ts(r.get("create_time")),
                })
            time.sleep(0.5)

    return {
        "status": "ok",
        "gid": gid,
        "total": obj.get("total_number"),
        "count": len(items),
        "has_more": obj.get("has_more"),
        "results": items,
        "fetched_at": time.strftime("%Y-%m-%d %H:%M"),
    }


# ---- 热榜 ----
def hot(limit=50):
    st, raw = _fetch(HOT_URL, UA_PC, "https://www.toutiao.com/")
    if st != 200 or not str(raw).strip().startswith("{"):
        return {"status": "error", "error": "热榜接口异常 (status=%s)" % st, "results": []}
    try:
        obj = json.loads(raw)
    except Exception as e:
        return {"status": "error", "error": "热榜 JSON 解析失败: %s" % e, "results": []}

    items = []
    for d in (obj.get("data") or [])[:limit]:
        cid = str(d.get("ClusterId") or d.get("cluster_id") or "")
        # 原始 Url 带一长串埋点参数；用 cluster_id 构造干净的 trending 链接
        url = ("https://www.toutiao.com/trending/%s/" % cid) if cid else (d.get("Url") or "")
        items.append({
            "title": d.get("Title"),
            "hot": d.get("HotValue") or d.get("HotValueV2"),
            "url": url,
            "cluster_id": cid,
        })
    return {"status": "ok", "count": len(items), "results": items,
            "fetched_at": time.strftime("%Y-%m-%d %H:%M")}


# ---- 输出 ----
def render_md(data, mode):
    if data.get("status") != "ok":
        return "抓取失败: %s" % data.get("error", "未知错误")

    lines = []
    if mode == "search":
        lines.append("# 今日头条搜索: %s (共 %d 条)" % (data["keyword"], data["count"]))
        meta = []
        if data.get("type") and data["type"] != "article":
            meta.append("类型=%s" % data["type"])
        if data.get("period"):
            meta.append("时间范围=%s" % data["period"])
        if meta:
            lines.append("> " + " · ".join(meta))
        lines.append("")
        for i, it in enumerate(data["results"], 1):
            lines.append("### %d. %s" % (i, it["title"] or "(无标题)"))
            bits = []
            if it.get("source"):
                bits.append("来源: %s" % it["source"])
            if it.get("time"):
                bits.append(it["time"])
            if it.get("digg"):
                bits.append("赞 %s" % it["digg"])
            if it.get("comments"):
                bits.append("评 %s" % it["comments"])
            if bits:
                lines.append("- " + " | ".join(bits))
            if it.get("url"):
                lines.append("- %s" % it["url"])
            if it.get("ext_url"):
                lines.append("- 原文: %s" % it["ext_url"])
            body = it.get("content") or it.get("abstract")
            if body:
                lines.append("")
                lines.append(body[:400])
            lines.append("")

    elif mode == "read":
        lines.append("# %s" % (data.get("title") or "(无标题)"))
        bits = [data.get("kind") == "article" and "文章" or "微头条"]
        if data.get("source"):
            bits.append("来源: %s" % data["source"])
        if data.get("time"):
            bits.append(data["time"])
        if data.get("digg"):
            bits.append("赞 %s" % data["digg"])
        lines.append("> " + " | ".join(bits))
        if data.get("url"):
            lines.append("")
            lines.append("链接: %s" % data["url"])
        lines.append("")
        lines.append(data.get("content", ""))
        if data.get("comments_data"):
            cd = data["comments_data"]
            lines.append("")
            lines.append("---")
            lines.append("")
            lines.append("## 评论 (总 %s 条，本页 %d 条)" % (cd.get("total"), cd.get("count")))
            lines.append("")
            for i, c in enumerate(cd["results"], 1):
                v = " ✓认证" if c.get("verified") else ""
                lines.append("**%d. %s**%s · 赞%s · %s" % (i, c.get("user") or "?", v, c.get("digg"), c.get("time")))
                lines.append("")
                lines.append(str(c.get("text") or "")[:300])
                for r in c.get("replies", []):
                    lines.append("")
                    lines.append("　└─ **%s**: %s" % (r.get("user"), str(r.get("text"))[:200]))
                lines.append("")

    elif mode == "comments":
        lines.append("# 评论 (总 %s 条，本页 %d 条)" % (data.get("total"), data.get("count")))
        lines.append("")
        for i, c in enumerate(data["results"], 1):
            v = " ✓认证" if c.get("verified") else ""
            lines.append("**%d. %s**%s · 赞%s · 回复%s · %s"
                         % (i, c.get("user") or "?", v, c.get("digg"), c.get("reply_count"), c.get("time")))
            lines.append("")
            lines.append(str(c.get("text") or "")[:300])
            for r in c.get("replies", []):
                lines.append("")
                lines.append("　└─ **%s**: %s" % (r.get("user"), str(r.get("text"))[:200]))
            lines.append("")

    elif mode == "hot":
        lines.append("# 今日头条热榜 (共 %d 条)" % data["count"])
        lines.append("")
        for i, it in enumerate(data["results"], 1):
            lines.append("%2d. %s  (热度 %s)" % (i, it["title"], it.get("hot")))
            if it.get("url"):
                lines.append("    %s" % it["url"])
        lines.append("")

    lines.append("---")
    lines.append("数据来源: 今日头条 (so.toutiao.com / m.toutiao.com) · 抓取时间: %s"
                 % data.get("fetched_at", time.strftime("%Y-%m-%d %H:%M")))
    return "\n".join(lines)


def emit(data, mode, fmt):
    if fmt == "json":
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(render_md(data, mode))
    return 0 if data.get("status") == "ok" else 1


def main():
    p = argparse.ArgumentParser(
        description="今日头条内容抓取（搜索 / 正文 / 评论 / 热榜），免登录、纯标准库",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n"
               "  python s_toutiao.py search \"人工智能\" --limit 10\n"
               "  python s_toutiao.py search \"A股\" --type weitoutiao --period 7\n"
               "  python s_toutiao.py read 7682682663232176694 --comments 10\n"
               "  python s_toutiao.py comments 7682682663232176694 --replies\n"
               "  python s_toutiao.py hot --limit 20")
    p.add_argument("--format", choices=["md", "json"], default="md", help="输出格式（默认 md）")
    sub = p.add_subparsers(dest="cmd")

    s1 = sub.add_parser("search", help="关键词搜索（文字内容）")
    s1.add_argument("keyword")
    s1.add_argument("--type", choices=["article", "weitoutiao", "all"], default="article",
                    help="article=图文(默认) / weitoutiao=微头条 / all=两者都要")
    s1.add_argument("--limit", "-n", type=int, default=10)
    s1.add_argument("--period", type=int, choices=[1, 7, 30, 365], help="时间范围: 1天/7天/30天/1年")

    s2 = sub.add_parser("read", help="读正文（自动判别文章/微头条）")
    s2.add_argument("target", help="内容 ID 或 URL")
    s2.add_argument("--comments", "-c", type=int, default=0, help="同时抓取 N 条评论")

    s3 = sub.add_parser("comments", help="抓评论")
    s3.add_argument("target")
    s3.add_argument("--limit", "-n", type=int, default=20)
    s3.add_argument("--replies", action="store_true", help="同时抓取子回复（较慢）")

    s4 = sub.add_parser("hot", help="热榜")
    s4.add_argument("--limit", "-n", type=int, default=50)

    s5 = sub.add_parser("trending", help="热榜（同 hot）")
    s5.add_argument("--limit", "-n", type=int, default=50)

    args = p.parse_args()
    if not args.cmd:
        p.print_help()
        return 1

    if args.cmd == "search":
        return emit(search(args.keyword, args.type, args.limit, args.period), "search", args.format)

    if args.cmd == "read":
        data = read(args.target)
        if data.get("status") == "ok" and args.comments:
            data["comments_data"] = comments(args.target, args.comments)
        return emit(data, "read", args.format)

    if args.cmd == "comments":
        return emit(comments(args.target, args.limit, args.replies), "comments", args.format)

    if args.cmd in ("hot", "trending"):
        return emit(hot(args.limit), "hot", args.format)

    p.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
