#!/usr/bin/env python3
"""微博关键词搜索（s.weibo.com 网页版解析）
为什么不用 weibo-cli search: 其 m.weibo.cn 移动API对 SUB cookie 返回 ok=-100(会话无效)，
而桌面端 s.weibo.com 网页搜索在 SUB cookie 下完全可用。本脚本解析其 HTML 为 JSON。
用法: python s_weibo_search.py <关键词> [页码]
依赖: 仅标准库。Cookie 从 ~/.config/weibo-cli/credential.json 读取。
"""
import re, json, sys, os, urllib.request, urllib.parse, time

def _cookie_header():
    cred_path = os.path.expanduser("~/.config/weibo-cli/credential.json")
    with open(cred_path, encoding="utf-8") as f:
        cookies = json.load(f)["cookies"]
    return "; ".join(f"{k}={v}" for k, v in cookies.items())

def s_search(keyword: str, page: int = 1) -> dict:
    url = f"https://s.weibo.com/weibo?q={urllib.parse.quote(keyword)}&page={page}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
        "Cookie": _cookie_header(),
        "Referer": "https://weibo.com/",
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        html = r.read().decode("utf-8", "replace")

    if "passport.weibo.com/sso/signin" in html[:2000]:
        return {"error": "SESSION_EXPIRED", "hint": "cookie 失效, 重新 weibo login 或更新 credential.json"}

    items = []
    for block in re.split(r'<div class="card-wrap"', html)[1:]:
        mid = re.search(r'mid="(\d+)"', block)
        nick = re.search(r'nick-name="([^"]+)"', block)
        content = re.search(r'<p[^>]*node-type="feed_list_content[^"]*"[^>]*>([\s\S]*?)</p>', block)
        time_m = re.search(r'class="from"[^>]*>.*?<a[^>]*>([^<]+)</a>', block)
        # 从 action-data 提取作者 uid（正确帖子 URL 需要 uid+mid 双段）
        uid_m = re.search(r'uid=(\d+)', block) or re.search(r'//weibo\.com/u/(\d+)', block) or re.search(r'//weibo\.com/(\d{6,})\?', block)
        repost = re.search(r'转发[^<]*?(\d+)', block)
        comment = re.search(r'评论[^<]*?(\d+)', block)
        like = re.search(r'赞[^<]*?(\d+)', block)

        def _int(m):
            # 赞的正则会误吃 mid 等长数字串, 超过1千万视为误配
            if not m:
                return None
            v = int(m.group(1))
            return v if v < 10_000_000 else None

        if not (mid and content):
            continue
        text = re.sub(r'<[^>]+>', '', content.group(1))
        text = re.sub(r'\s+', ' ', text).strip()
        items.append({
            "mid": mid.group(1),
            "uid": uid_m.group(1) if uid_m else None,
            "author": nick.group(1) if nick else None,
            "text": text[:500],
            "time": time_m.group(1).strip() if time_m else None,
            "reposts": _int(repost),
            "comments": _int(comment),
            "likes": _int(like),
            # 正确格式: https://weibo.com/<uid>/<mid>（双段）。纯 mid 链接未登录会跳 passport.visitor 报错
            "url": f"https://weibo.com/{uid_m.group(1)}/{mid.group(1)}" if uid_m else f"https://m.weibo.cn/status/{mid.group(1)}",
        })
    return {"keyword": keyword, "page": page, "count": len(items), "items": items, "fetched_at": time.strftime("%Y-%m-%d %H:%M")}

def resolve_hot(hot_word: str) -> dict:
    """热搜词 -> 找到对应热度最高的帖子 -> 返回 uid/mid/双段URL。
    weibo hot 的 realtime 条目只有 word 没有 mid/uid, 本函数补齐链接闭环。
    """
    res = s_search(hot_word, 1)
    if res.get("error"):
        return res
    items = [i for i in res.get("items", []) if i.get("uid")]
    if not items:
        return {"word": hot_word, "error": "NO_MATCH", "hint": "搜索无结果或结果缺uid"}
    # 取互动数最高的(reposts+comments+likes 最大, None当0)
    def score(i):
        return sum(i.get(k) or 0 for k in ("reposts", "comments", "likes"))
    best = max(items, key=score)
    # 话题聚合页（含该词下全部讨论，比单帖更全面）——报告/跳转优先用这个
    import urllib.parse as _up
    topic_url = f"https://s.weibo.com/weibo?q={_up.quote(hot_word)}"
    return {"word": hot_word, "mid": best["mid"], "uid": best["uid"],
            "author": best["author"], "url": best["url"], "topic_url": topic_url,
            "text": best["text"][:200], "score": score(best)}


def fix_links(mids: list) -> list:
    """任意来源的 mid 列表 -> 逐个补 uid 出双段链接。
    用途: 自建采集管线(hot_band等)产出的 mid 没有 uid 时, 报告定稿前跑一次强制纠正。
    """
    import urllib.request as _uq
    cookies = _cookie_header()
    out = []
    for mid in mids:
        url = f"https://weibo.com/ajax/statuses/show?id={mid}"
        req = _uq.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Cookie": cookies, "Accept": "application/json", "Referer": "https://weibo.com/",
        })
        try:
            with _uq.urlopen(req, timeout=15) as r:
                d = json.loads(r.read().decode("utf-8"))
            uid = d.get("user", {}).get("idstr")
            mblogid = d.get("mblogid")
            out.append({
                "mid": mid, "uid": uid,
                "author": d.get("user", {}).get("screen_name"),
                "url": f"https://weibo.com/{uid}/{mblogid or mid}" if uid else None,
                "m_url": f"https://m.weibo.cn/status/{mid}",
                "text": (d.get("text_raw") or d.get("text") or "")[:200],
            })
        except Exception as e:
            out.append({"mid": mid, "error": str(e)[:120]})
    return out


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--fix-links":
        mids = sys.argv[2].split(",")
        print(json.dumps(fix_links(mids), ensure_ascii=False, indent=1))
        sys.exit(0)
    if len(sys.argv) > 2 and sys.argv[1] == "--resolve-hot":
        hot_word = sys.argv[2]
        print(json.dumps(resolve_hot(hot_word), ensure_ascii=False, indent=1))
        sys.exit(0)
    kw = sys.argv[1] if len(sys.argv) > 1 else ""
    pg = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    if not kw:
        print(json.dumps({"error": "usage: python s_weibo_search.py <keyword> [page] | --resolve-hot <hot_word>"}, ensure_ascii=False))
        sys.exit(1)
    print(json.dumps(s_search(kw, pg), ensure_ascii=False, indent=1))
