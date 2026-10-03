#!/usr/bin/env python3
"""微博关键词搜索（s.weibo.com 网页版解析）
为什么不用 weibo-cli search: 其 m.weibo.cn 移动API对 SUB cookie 返回 ok=-100(会话无效)，
而桌面端 s.weibo.com 网页搜索在 SUB cookie 下完全可用。本脚本解析其 HTML 为 JSON。

⚠️ 2026-09-25 状态：s.weibo.com 搜索页被新的 wbBotDetector 机器人检测壳拦截
   （同壳也罩住 m.weibo.cn 移动API 和 weibo.com 的 HTML 页面层）。
   已实测全部绕行失败：游客系统握手(genvisitor2/老genvisitor)、cookie预热、
   Edge headless(本地真IP+JS执行)、Firecrawl/Exa 数据中心IP——全部弹登录/访客壳。
   仅 AJAX 接口(hot_band 热搜)和 side/search 联想词仍可用。
   本脚本遇到拦截壳时返回明确的 error 字段（不再静默返回 0 条）。

用法: python s_weibo_search.py <关键词> [页码] [--engine auto|http|edge]
     python s_weibo_search.py --resolve-hot <热搜词> [--engine auto|http|edge]
     python s_weibo_search.py --fix-links <mid1,mid2,...>
依赖: 仅标准库。Cookie 从 ~/.config/weibo-cli/credential.json 读取（http 引擎）。

┌─ 引擎说明（2026-09-25 新增）─────────────────────────────────────────────┐
│ http  : 纯 urllib。2026-09 起被 wbBotDetector 壳拦截，恒定返回 BOT_DETECT_SHELL │
│ edge  : headless Edge + 已登录 profile（C:\\Users\\fenix\\.wb-auto-profile）。   │
│         真浏览器指纹+登录态，实测过墙（2026-09-25 方案A验证通过）。            │
│         ⚠️ profile 需已登录微博；登录态失效时返回 EDGE_NOT_LOGGED_IN，           │
│         修复方法：弹出该 profile 的 Edge 窗口重新登录一次（见 SKILL 文档）。     │
│ auto  : 先试 edge（若 profile 存在），失败回落 http（保留壳识别报错）。         │
└──────────────────────────────────────────────────────────────────────────┘
"""
import re, json, sys, os, urllib.request, urllib.parse, time, subprocess

# ── Edge 引擎配置（2026-09-25 方案A）──
EDGE_EXE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]
EDGE_PROFILE = os.path.expanduser(r"~\.wb-auto-profile")

def _find_edge():
    for p in EDGE_EXE_CANDIDATES:
        if os.path.exists(p):
            return p
    return None

def _edge_fetch_dom(url: str, timeout_s: int = 40) -> dict:
    """headless Edge + 已登录 profile 取渲染后 DOM。
    返回 {html} 或 {error}。用 --dump-dom 直出（实验已验证，profile 独占使用）。
    """
    exe = _find_edge()
    if not exe:
        return {"error": "EDGE_NOT_FOUND", "hint": "本机未找到 Edge，改用 --engine http 或安装 DrissionPage(方案C)"}
    if not os.path.isdir(EDGE_PROFILE):
        return {"error": "EDGE_PROFILE_MISSING",
                "hint": f"profile 不存在: {EDGE_PROFILE}。首次设置：弹出该 profile 的 Edge 登录微博一次",
                "setup": f'Start-Process "{exe}" -ArgumentList "--user-data-dir={EDGE_PROFILE}","https://weibo.com"'}
    import tempfile
    # 清理同 profile 的残留进程（含孤儿进程——超时被杀的主进程会留下持锁子进程），避免锁冲突
    # 注: 这是专用自动化 profile, 全杀是安全的; 用户日常浏览器是另一个 profile 不受影响
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process -Filter \"Name='msedge.exe'\" | "
             "Where-Object { $_.CommandLine -like '*wb-auto-profile*' } | "
             "ForEach-Object { Invoke-CimMethod -InputObject $_ -MethodName Terminate | Out-Null }"],
            capture_output=True, timeout=20)
        time.sleep(1)
    except Exception:
        pass
    # 注意: profile 被占用(用户开着 Edge 窗口)时 headless 会失败 → 返回明确错误
    # ⚠️ --disable-extensions + --disable-sync 必须带:
    #   ① 登录态 profile 会同步账号扩展, 扩展加载拖垮 dump-dom(实测恒 0 字节)
    #   ② Edge 账号同步服务在国内网络下反复重试(ERR_ABORTED), 拖慢启动导致超时(实测)
    last_err = None
    for attempt in range(2):  # 一次失败自动重试一次
        try:
            p = subprocess.run(
                [exe, f"--user-data-dir={EDGE_PROFILE}", "--headless=new", "--disable-gpu",
                 "--disable-extensions", "--disable-sync", "--no-first-run",
                 "--virtual-time-budget=20000", f"--timeout={timeout_s * 1000}", "--dump-dom", url],
                capture_output=True, text=True, timeout=timeout_s + 90, errors="replace")
            html = p.stdout or ""
            if html.strip():
                return {"html": html}
            last_err = {"error": "EDGE_NO_OUTPUT",
                        "hint": "headless 无输出。常见原因: ①该 profile 的 Edge 窗口正开着(锁冲突), 关掉后重试 "
                                "②profile 登录态异常, 重新登录",
                        "stderr_head": (p.stderr or "")[:200]}
        except subprocess.TimeoutExpired:
            last_err = {"error": "EDGE_TIMEOUT",
                        "hint": f"headless dump 超时。常见原因: ①该 profile 的 Edge 窗口正开着(锁冲突), 关掉重试 ②网络异常"}
        # 重试前再清一次残留进程
        time.sleep(1)
    return last_err

def s_search_edge(keyword: str, page: int = 1) -> dict:
    """方案A引擎: headless Edge 渲染 s.weibo.com 搜索页 → 复用解析逻辑。"""
    url = f"https://s.weibo.com/weibo?q={urllib.parse.quote(keyword)}&page={page}"
    r = _edge_fetch_dom(url)
    if "error" in r:
        return {"error": r["error"], "engine": "edge", "keyword": keyword, "page": page,
                "hint": r.get("hint"), **({"setup": r["setup"]} if r.get("setup") else {})}
    html = r["html"]
    # 登录态失效时 Edge 会被踢到登录壳（与 http 引擎同样的识别逻辑）
    if "wbBotDetector" in html and "card-wrap" not in html:
        return {"error": "EDGE_NOT_LOGGED_IN", "engine": "edge", "keyword": keyword, "page": page,
                "hint": "profile 登录态失效（页面被弹到登录壳）。修复：运行 setup 命令弹出窗口重新登录微博",
                "setup": f'Start-Process "{_find_edge()}" -ArgumentList "--user-data-dir={EDGE_PROFILE}","https://weibo.com"'}
    if "Sina Visitor System" in html[:2000] and "card-wrap" not in html:
        return {"error": "EDGE_NOT_LOGGED_IN", "engine": "edge", "keyword": keyword, "page": page,
                "hint": "profile 被踢到访客系统，登录态丢失。重新登录微博",
                "setup": f'Start-Process "{_find_edge()}" -ArgumentList "--user-data-dir={EDGE_PROFILE}","https://weibo.com"'}
    items = _parse_search_html(html)
    return {"keyword": keyword, "page": page, "count": len(items), "items": items,
            "engine": "edge", "fetched_at": time.strftime("%Y-%m-%d %H:%M")}

def _cookie_header():
    cred_path = os.path.expanduser(r"~\.config\weibo-cli\credential.json")
    with open(cred_path, encoding="utf-8") as f:
        cookies = json.load(f)["cookies"]
    return "; ".join(f"{k}={v}" for k, v in cookies.items())

def _parse_search_html(html: str) -> list:
    """解析 s.weibo.com 搜索结果 HTML → items（http/edge 引擎共用）。
    ⚠️ 2026-09-26 修正: 结果卡的 DOM 是 <div action-type="feed_list_item" mid=".." class="card-wrap">，
    mid 属性在 class 之前。旧正则 `<div class="card-wrap"` 只能切出容器块（2个），全部解析失败。
    现在按 action-type="feed_list_item"（更精确的结果卡标记）切块，兼容老格式。
    """
    items = []
    blocks = re.split(r'<div[^>]*action-type="feed_list_item"[^>]*>', html)[1:]
    if not blocks:  # 兜底: 老格式（无 action-type 标记时）
        blocks = re.split(r'<div class="card-wrap"', html)[1:]
    for block in blocks:
        # ⚠️ 2026-09-26: 新版 DOM 的 mid 在被切掉的 div 头上(<div action-type="feed_list_item" mid="..">)，
        # 块内要改从 action-data 提取 mid/uid（注意 HTML 转义 &amp;）
        ad = re.search(r'action-data="([^"]*)"', block)
        mid = uid_m = None
        if ad:
            ad_dec = ad.group(1).replace("&amp;", "&")
            mid = re.search(r'(?:^|&)mid=(\d+)', ad_dec)
            uid_m = re.search(r'(?:^|&)uid=(\d+)', ad_dec)
        if not mid:  # 兜底: 块内其他位置的 mid
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
    return items

def s_search(keyword: str, page: int = 1, engine: str = "auto") -> dict:
    if engine in ("edge", "auto"):
        if engine == "edge" or os.path.isdir(EDGE_PROFILE):
            res = s_search_edge(keyword, page)
            if engine == "edge" or not res.get("error"):
                return res
            # auto 模式: edge 失败 → 回落 http，但保留 edge 失败原因供诊断
            fallback = s_search(keyword, page, engine="http")
            if fallback.get("error"):
                fallback["edge_error"] = res.get("error")
                fallback["edge_hint"] = res.get("hint")
            return fallback
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

    # ── bot/登录壳识别（2026-09-25 新增，防静默假阴性）──
    # 三种失败壳：wbBotDetector 登录壳 / 经典 Sina Visitor System / passport sso 跳转
    head2k = html[:2000]
    if "wbBotDetector" in html and "card-wrap" not in html:
        return {
            "error": "BOT_DETECT_SHELL",
            "keyword": keyword, "page": page,
            "hint": "s.weibo.com 搜索页被 wbBotDetector 机器人检测壳拦截（2026-09 起）。",
            "detail": "壳页=登录页(wbBotDetector指纹+易盾SDK)。已实测绕行全灭：游客握手/cookie预热/"
                      "headless浏览器/Firecrawl数据中心IP。cookie 本身未失效(hot_band 正常)。",
            "workaround": "关键词搜索暂无纯HTTP替代；用 weibo hot 热搜 + Tavily(site:weibo.com) "
                          "或 m.weibo.cn 热搜聚合页兜底；等待微博风控策略变化后重试",
            "fetched_at": time.strftime("%Y-%m-%d %H:%M"),
        }
    if "Sina Visitor System" in head2k and "card-wrap" not in html:
        return {
            "error": "VISITOR_SYSTEM",
            "keyword": keyword, "page": page,
            "hint": "被踢到游客系统(未识别为登录态)。",
            "workaround": "同 BOT_DETECT_SHELL",
            "fetched_at": time.strftime("%Y-%m-%d %H:%M"),
        }

    items = _parse_search_html(html)
    return {"keyword": keyword, "page": page, "count": len(items), "items": items,
            "engine": "http", "fetched_at": time.strftime("%Y-%m-%d %H:%M")}

def resolve_hot(hot_word: str, engine: str = "auto") -> dict:
    """热搜词 -> 找到对应热度最高的帖子 -> 返回 uid/mid/双段URL。
    weibo hot 的 realtime 条目只有 word 没有 mid/uid, 本函数补齐链接闭环。
    """
    res = s_search(hot_word, 1, engine=engine)
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
            if d.get("ok") == -100:
                # 2026-09-25: weibo.com 对 show 接口也加了会话/bot 校验，返回 ok=-100
                out.append({"mid": mid, "error": "SHOW_ENDPOINT_REJECTED",
                            "hint": "ajax/statuses/show 返回 ok=-100（bot壳连带影响）。"
                                    "链接需人工从浏览器取，或等风控变化后重试"})
                continue
            uid = d.get("user", {}).get("idstr")
            mblogid = d.get("mblogid")
            if not uid:
                out.append({"mid": mid, "error": "NO_UID_IN_RESPONSE"})
                continue
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
    # --engine 提取（可出现在任意位置）
    engine = "auto"
    if "--engine" in sys.argv:
        i = sys.argv.index("--engine")
        if i + 1 < len(sys.argv):
            engine = sys.argv[i + 1]
            del sys.argv[i:i + 2]
    # 参数守卫（2026-10-02）：-h/--help/无参数 直接打印用法退出，不发起网络请求
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        print("用法: python s_weibo_search.py <关键词> [页码] [--engine auto|http|edge]")
        print("      python s_weibo_search.py --resolve-hot <热搜词> [--engine auto|http|edge]")
        print("      python s_weibo_search.py --fix-links <mid1,mid2,...>")
        sys.exit(0)
    if sys.argv[1].startswith("-") and sys.argv[1] not in ("--resolve-hot", "--fix-links"):
        print(json.dumps({"error": "UNKNOWN_OPTION", "arg": sys.argv[1],
                          "hint": "用法见 -h"}, ensure_ascii=False))
        sys.exit(1)
    if len(sys.argv) > 2 and sys.argv[1] == "--fix-links":
        mids = sys.argv[2].split(",")
        print(json.dumps(fix_links(mids), ensure_ascii=False, indent=1))
        sys.exit(0)
    if len(sys.argv) > 2 and sys.argv[1] == "--resolve-hot":
        hot_word = sys.argv[2]
        print(json.dumps(resolve_hot(hot_word, engine=engine), ensure_ascii=False, indent=1))
        sys.exit(0)
    kw = sys.argv[1] if len(sys.argv) > 1 else ""
    pg = 1
    if len(sys.argv) > 2:
        try:
            pg = int(sys.argv[2])
        except ValueError:
            print(json.dumps({"error": "BAD_PAGE_NUMBER", "arg": sys.argv[2],
                              "hint": "页码必须是整数，如: python s_weibo_search.py 关键词 2"}, ensure_ascii=False))
            sys.exit(1)
    if not kw:
        print(json.dumps({"error": "usage: python s_weibo_search.py <keyword> [page] [--engine auto|http|edge] | --resolve-hot <hot_word> | --fix-links <mids>"}, ensure_ascii=False))
        sys.exit(1)
    print(json.dumps(s_search(kw, pg, engine=engine), ensure_ascii=False, indent=1))
