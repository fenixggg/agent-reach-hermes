#!/usr/bin/env python3
"""微博关键词搜索（s.weibo.com 网页版解析）
为什么不用 weibo-cli search: 其 m.weibo.cn 移动API对 SUB cookie 返回 ok=-100(会话无效)，
而桌面端 s.weibo.com 网页搜索在 SUB cookie 下完全可用。本脚本解析其 HTML 为 JSON。
用法: python s_weibo_search.py <关键词> [页码]
依赖: 仅标准库。Cookie 从 ~/.config/weibo-cli/credential.json 读取。
"""
import re, json, sys, os, urllib.request, urllib.parse, time

def _cookie_header():
    cred_path = os.path.expanduser(os.path.join("~", ".config", "weibo-cli", "credential.json"))
    if not os.path.isfile(cred_path):
        return ""
    try:
        with open(cred_path, encoding="utf-8") as f:
            cookies = json.load(f).get("cookies", {})
        return "; ".join(f"{k}={v}" for k, v in cookies.items())
    except Exception:
        return ""

def s_search(keyword: str, page: int = 1) -> dict:
    url = f"https://s.weibo.com/weibo?q={urllib.parse.quote(keyword)}&page={page}"
    cookie = _cookie_header()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
        "Referer": "https://weibo.com/",
    }
    if cookie:
        headers["Cookie"] = cookie

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            html = r.read().decode("utf-8", "replace")
    except Exception as e:
        return {"error": f"Network error: {str(e)}"}

    if "passport.weibo.com/sso/signin" in html[:2000]:
        return {"error": "SESSION_EXPIRED", "hint": "cookie 失效, 请更新 ~/.config/weibo-cli/credential.json"}

    items = []
    for block in re.split(r'<div class="card-wrap"', html)[1:]:
        mid = re.search(r'mid="(\d+)"', block)
        nick = re.search(r'nick-name="([^"]+)"', block)
        content = re.search(r'<p[^>]*node-type="feed_list_content[^"]*"[^>]*>([\s\S]*?)</p>', block)
        time_m = re.search(r'class="from"[^>]*>.*?<a[^>]*>([^<]+)</a>', block)
        repost = re.search(r'转发[^<]*?(\d+)', block)
        comment = re.search(r'评论[^<]*?(\d+)', block)
        like = re.search(r'赞[^<]*?(\d+)', block)

        def _int(m):
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
            "author": nick.group(1) if nick else None,
            "text": text[:500],
            "time": time_m.group(1).strip() if time_m else None,
            "reposts": _int(repost),
            "comments": _int(comment),
            "likes": _int(like),
            "url": f"https://weibo.com/{mid.group(1)}",
        })
    return {"keyword": keyword, "page": page, "count": len(items), "items": items, "fetched_at": time.strftime("%Y-%m-%d %H:%M")}

if __name__ == "__main__":
    kw = sys.argv[1] if len(sys.argv) > 1 else ""
    pg = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    if not kw:
        print(json.dumps({"error": "usage: python s_weibo_search.py <keyword> [page]"}, ensure_ascii=False))
        sys.exit(1)
    print(json.dumps(s_search(kw, pg), ensure_ascii=False, indent=1))
