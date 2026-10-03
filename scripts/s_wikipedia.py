#!/usr/bin/env python3
"""Wikipedia 抓取 — 官方 API，免密钥、免登录。

设计取舍（全部经本机实测，2026-09）:
  * REST /page/summary/{title}   —— 摘要 + 元信息 + 规范 URL。zh/en 均可用。
  * action=parse&prop=text       —— 【正文首选】已渲染 HTML → 剥标签得纯文本。
       en.wiki 实测 0 处 wikitext 残留、512KB；zh 237KB。见 op_page docstring。
  * REST /page/html/{title}      —— 仅用于取 <section> 分节结构（sections 动作）。
       正文不要用它：会把 infobox/模块原始 wikitext 以 JSON 形式内嵌
       （en 1425 处 `{"wt":` / zh 734 处），剥完标签残渣污染正文，体积近两倍。
  * action=query&list=search     —— 搜索。zh/en 均可用。
  * action=query&prop=langlinks  —— 跨语言版本。
  * ⚠️ action=query&prop=extracts —— 【zh.wikipedia.org 返回空字符串！】
       TextExtracts 扩展在中文维基未启用，explaintext/exintro 组合一律 extract:""。
       英文维基正常。所以本脚本【绝不】依赖 prop=extracts 取正文。
  * ⚠️ action=parse 遇重定向页只返回 '#REDIRECT [[...]]'（~58B）。已默认带 redirects=1。

限流（实测踩坑）：匿名请求连续约 10 次即触发
  "You are making too many requests to the API."。
  对策：带符合 Wikimedia UA policy 的真实 UA + 请求间 sleep + 失败指数退避。
  识别特征：响应文本含 "too many requests" → 抛 RateLimited，内部已退避重试。
  可用环境变量 WIKI_MIN_INTERVAL（默认 0.8s）与 WIKI_UA 调节。

依赖：仅标准库。用法见 --help。
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html import unescape

# 符合 Wikimedia User-Agent policy（须含联系方式，否则可能被限流/封禁）
UA = os.environ.get(
    "WIKI_UA",
    "agent-reach/1.0 (https://github.com/agent-reach; wikipedia channel)",
)
# 官方对所有匿名 API 客户的礼貌限速建议：串行 + 间隔
MIN_INTERVAL = float(os.environ.get("WIKI_MIN_INTERVAL", "0.8"))
_last_call = [0.0]
MAX_RETRY = 3


class RateLimited(RuntimeError):
    pass


class WikiError(RuntimeError):
    pass


def _throttle():
    gap = time.time() - _last_call[0]
    if gap < MIN_INTERVAL:
        time.sleep(MIN_INTERVAL - gap)
    _last_call[0] = time.time()


def _get(url: str, *, as_json: bool = True):
    """带限速 + 指数退避的 GET。429/限流文本自动退避重试。"""
    last_err = None
    for attempt in range(MAX_RETRY):
        _throttle()
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json" if as_json else "text/html"})
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                body = r.read().decode("utf-8", "replace")
            if "too many requests" in body[:400].lower():
                raise RateLimited(body[:120])
            return json.loads(body) if as_json else body
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "replace")
            if e.code in (429, 503) or "too many requests" in raw[:400].lower():
                last_err = RateLimited(f"HTTP {e.code}")
            elif e.code == 404:
                raise WikiError(f"NOT_FOUND: 条目不存在 ({url})") from e
            else:
                last_err = WikiError(f"HTTP {e.code}: {raw[:160]}")
        except Exception as e:  # noqa: BLE001 — 网络层错误统一退避
            last_err = e
        # 退避：1.5s, 3s, 6s
        time.sleep(1.5 * (2**attempt))
    raise last_err if isinstance(last_err, Exception) else WikiError("unknown")


def _api(lang: str, params: dict) -> dict:
    params = {**params, "format": "json", "utf8": "1", "redirects": "1"}
    return _get(f"https://{lang}.wikipedia.org/w/api.php?{urllib.parse.urlencode(params)}")


def _rest(lang: str, path: str, *, as_json: bool = True):
    return _get(f"https://{lang}.wikipedia.org/api/rest_v1/{path}", as_json=as_json)


# ---------- 各动作 ----------

def op_summary(lang: str, title: str) -> dict:
    """条目摘要 + 元信息。首选端点。"""
    d = _rest(lang, f"page/summary/{urllib.parse.quote(title, safe='')}")
    return {
        "lang": lang,
        "title": d.get("title"),
        "type": d.get("type"),  # standard | disambiguation | ...
        "description": d.get("description"),  # 简短定义
        "extract": d.get("extract"),
        "extract_html": d.get("extract_html"),
        "thumbnail": (d.get("thumbnail") or {}).get("source"),
        "coordinates": d.get("coordinates"),
        "url": ((d.get("content_urls") or {}).get("desktop") or {}).get("page"),
        "wikidata_id": d.get("wikibase_item"),
        "timestamp": d.get("timestamp"),
        "note": "type=disambiguation 表示消歧义页，需用户澄清具体所指" if d.get("type") == "disambiguation" else None,
    }


def op_search(lang: str, query: str, limit: int = 10) -> dict:
    """全文搜索。zh/en 均可用。"""
    d = _api(lang, {"action": "query", "list": "search", "srsearch": query, "srlimit": str(limit), "srprop": "snippet|wordcount|timestamp"})
    items = []
    for it in (d.get("query", {}).get("search") or []):
        items.append({
            "title": it.get("title"),
            "pageid": it.get("pageid"),
            "size": it.get("size"),
            "wordcount": it.get("wordcount"),
            "timestamp": it.get("timestamp"),
            "snippet": re.sub(r"<[^>]+>", "", unescape(it.get("snippet") or "")),
            "url": f"https://{lang}.wikipedia.org/wiki/{urllib.parse.quote(it.get('title', '').replace(' ', '_'))}",
        })
    return {"lang": lang, "query": query, "count": len(items), "items": items}


def _strip_html(html: str, *, drop_hatnotes: bool = True) -> str:
    """粗剥 HTML 标签 → 纯文本。用于 REST /page/html 正文。

    drop_hatnotes=True 时丢弃首页那堆维护模板框（"本條目存在以下問題…"
    "需要編修/補充來源/翻譯品質不佳"），它们在 API 返回里体积很大且无信息量，
    会淹没正文开头。对应 class="ambox|tmbox|mbox-*" 与 role="note" 的 box。
    """
    html = re.sub(r"<(script|style)[^>]*>[\s\S]*?</\1>", "", html, flags=re.I)
    if drop_hatnotes:
        # 维护/提示模板框：整块删除（含嵌套 div 的常见形态）
        html = re.sub(r'<div[^>]*class="[^"]*(?:ambox|tmbox|ombox|mbox-|hatnote|dablink|rellink|metadata)[^"]*"[^>]*>[\s\S]*?</div>\s*</div>', "", html, flags=re.I)
        html = re.sub(r'<table[^>]*class="[^"]*(?:ambox|tmbox|metadata|plainlinks)[^"]*"[^>]*>[\s\S]*?</table>', "", html, flags=re.I)
        html = re.sub(r'<div[^>]*role="note"[^>]*>[\s\S]*?</div>', "", html, flags=re.I)
    html = re.sub(r"<sup[^>]*class=\"[^\"]*reference[^\"]*\"[^>]*>[\s\S]*?</sup>", "", html, flags=re.I)
    # 块级标签转换行，避免文字粘连
    html = re.sub(r"</(p|div|li|h[1-6]|section|tr)>", "\n", html, flags=re.I)
    html = re.sub(r"<br\s*/?>", "\n", html, flags=re.I)
    html = re.sub(r"<[^>]+>", "", html)
    html = unescape(html)
    # 清理 REST html 里未渲染的 wikitext 残留（en.wiki 常见；zh 较少）
    # [[target|label]] -> label ; [[target]] -> target
    html = re.sub(r"\[\[[^\]|]*\|([^\]]*)\]\]", r"\1", html)
    html = re.sub(r"\[\[([^\]]*)\]\]", r"\1", html)
    # {{模板|x|y}} -> 删除（引用模板体积大且无正文价值）
    html = re.sub(r"\{\{[^{}]*\}\}", "", html)
    html = re.sub(r"\}\}", "", html)  # 残留的孤立 }}
    html = re.sub(r"</?ref[^>]*>", "", html, flags=re.I)
    html = re.sub(r"[ \t]+", " ", html)
    html = re.sub(r" *\n *", "\n", html)
    html = re.sub(r"\n{3,}", "\n\n", html)
    return html.strip()


def op_page(lang: str, title: str, *, max_chars: int = 0) -> dict:
    """条目全文（纯文本）。

    ⚠️ 端点选择经实测（2026-09）：正文【必须】走 action=parse&prop=text，
    不能用 REST /page/html。后者会把 infobox/模块的原始 wikitext 以 JSON 形式
    内嵌在 HTML 里（en.wiki 实测 1425 处 `{"wt":` 残留，zh 734 处），
    剥标签后这些残渣会污染正文，且体积接近两倍（864KB vs 512KB）。
    parse&prop=text 返回已渲染 HTML，同页 0 处残留、体积减半。

    代价：parse 不返回 <section> 结构 → 分节功能由 op_sections 单独走 REST html。

    max_chars>0 时截断（返回 truncated=True）。
    """
    d = _api(lang, {"action": "parse", "page": title, "prop": "text"})
    if "parse" not in d:
        err = (d.get("error") or {}).get("info") or "parse 返回异常"
        raise WikiError(f"PARSE_FAIL: {err}")
    html = d["parse"]["text"]["*"]
    text = _strip_html(html)
    truncated = False
    if max_chars and len(text) > max_chars:
        text = text[:max_chars]
        truncated = True
    return {
        "lang": lang,
        "title": d["parse"].get("title") or title,
        "chars": len(text),
        "truncated": truncated,
        "text": text,
        "url": f"https://{lang}.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}",
    }


def op_sections(lang: str, title: str) -> dict:
    """条目分节标题列表（来自 REST html 的 <section> 结构），配合 page 精读。"""
    html = _rest(lang, f"page/html/{urllib.parse.quote(title, safe='')}", as_json=False)
    secs = []
    for m in re.finditer(r'<section[^>]*data-mw-section-id="(\d+)"[^>]*>[\s\S]*?<h([1-6])[^>]*>([\s\S]*?)</h\2>', html):
        sid, lvl, inner = m.group(1), int(m.group(2)), m.group(3)
        heading = _strip_html(inner)
        heading = re.sub(r"\[.*?\]$", "", heading).strip()  # 去 [编辑] 尾巴
        if heading:
            secs.append({"id": int(sid), "level": lvl, "heading": heading})
    return {"lang": lang, "title": title, "count": len(secs), "sections": secs}


def op_langs(lang: str, title: str) -> dict:
    """某条目在所有语言版本的标题 + 跨语言链接。"""
    d = _api(lang, {"action": "query", "titles": title, "prop": "langlinks", "lllimit": "500"})
    pages = d.get("query", {}).get("pages", {})
    page = next(iter(pages.values()), {}) if pages else {}
    links = [{"lang": x.get("lang"), "title": x.get("*"), "url": f"https://{x.get('lang')}.wikipedia.org/wiki/{urllib.parse.quote(str(x.get('*', '')).replace(' ', '_'))}"} for x in (page.get("langlinks") or [])]
    return {"lang": lang, "title": page.get("title"), "count": len(links), "langlinks": links}


def op_random(lang: str, n: int = 1, with_extract: bool = True) -> dict:
    """随机条目。可用于发现/调试。注意：不依赖 prop=extracts，改用 summary。"""
    d = _api(lang, {"action": "query", "generator": "random", "grnnamespace": "0", "grnlimit": str(n)})
    pages = list((d.get("query", {}).get("pages") or {}).values())
    out = []
    for p in pages:
        entry = {"title": p.get("title"), "pageid": p.get("pageid")}
        if with_extract:
            try:
                s = op_summary(lang, p.get("title", ""))
                entry["extract"] = s.get("extract")
                entry["url"] = s.get("url")
            except Exception as e:  # noqa: BLE001
                entry["error"] = str(e)[:120]
        out.append(entry)
    return {"lang": lang, "count": len(out), "items": out}


ACTIONS = {
    "summary": lambda a: op_summary(a.lang, a.title),
    "search": lambda a: op_search(a.lang, a.query, a.limit),
    "page": lambda a: op_page(a.lang, a.title, max_chars=a.max_chars),
    "sections": lambda a: op_sections(a.lang, a.title),
    "langs": lambda a: op_langs(a.lang, a.title),
    "random": lambda a: op_random(a.lang, a.count),
}


def main() -> int:
    p = argparse.ArgumentParser(description="Wikipedia 抓取（官方 API，免密钥）")
    p.add_argument("action", choices=sorted(ACTIONS), help="动作")
    p.add_argument("target", nargs="?", help="条目标题（summary/page/sections/langs）或搜索词（search）")
    p.add_argument("--lang", default="zh", help="语言代码，默认 zh；en/ja/... ")
    p.add_argument("--limit", type=int, default=10, help="search 结果数")
    p.add_argument("--count", type=int, default=1, help="random 条数")
    p.add_argument("--max-chars", type=int, default=0, help="page 正文截断字符数，0=不截断")
    p.add_argument("--raw", action="store_true", help="紧凑单行 JSON（默认缩进美化）")
    a = p.parse_args()

    if a.action != "random" and not a.target:
        print(json.dumps({"error": f"{a.action} 需要 target 参数"}, ensure_ascii=False))
        return 2
    if a.action == "search":
        a.query = a.target
    else:
        a.title = a.target

    try:
        res = ACTIONS[a.action](a)
        res["fetched_at"] = time.strftime("%Y-%m-%d %H:%M")
        print(json.dumps(res, ensure_ascii=False, indent=None if a.raw else 1))
        return 0
    except RateLimited as e:
        print(json.dumps({"error": "RATE_LIMITED", "hint": "已重试 %d 次仍被限流；调大 WIKI_MIN_INTERVAL 或稍后再试" % MAX_RETRY, "detail": str(e)}, ensure_ascii=False))
        return 3
    except WikiError as e:
        print(json.dumps({"error": "WIKI_ERROR", "detail": str(e)}, ensure_ascii=False))
        return 4
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"error": type(e).__name__, "detail": str(e)[:200]}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
