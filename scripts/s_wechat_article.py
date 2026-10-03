#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""微信公众号文章正文提取（curl_cffi TLS 指纹伪装 + 递归正文行走器）

定位: better-webfetch(httpx) 抓 mp.weixin.qq.com/s?... 直链被识别指纹返回 17KB 拦截页时，
      本脚本接管正文提取。与 wechat_search.py（找链接）分工协作，不互相替代。

为什么自建（2026-10-03 实测结论）:
  - better-webfetch 的 httpx 栈对签名直链拿到的是"环境异常"拦截页（js_content 缺失）。
  - 微信反爬卡的是 **TLS 指纹(JA3)**，不是 UA 头：curl_cffi impersonate=chrome 直接拿到
    3.5MB 完整页面；实测 **无需任何 Cookie**（NewsCrawler 写死的 FIXED_COOKIE 可以扔掉）。
  - 移植自 NewsCrawler 的 WechatContentParser，
    但去掉 pydantic/parsel/demjson3 依赖，只用 curl_cffi + lxml，风格与 s_toutiao.py 一致。

用法:
  python s_wechat_article.py <微信文章URL>                 # 默认 JSON（bwf 风格信封）
  python s_wechat_article.py <URL> --format md             # 纯 Markdown
  python s_wechat_article.py <URL> --save-to out.json      # 落盘（utf-8 无 BOM）
  python s_wechat_article.py <URL> --proxy none            # 清空代理环境变量

依赖: curl_cffi, lxml（系统 Python 3.14 已装 curl_cffi 0.16.3 + lxml 6.1.3）

指纹池（2026-10-03 教程精读落地，P0②）:
  单一 JA3 指纹高频使用会被风控聚类。每次请求会话级随机从 FINGERPRINT_POOL 抽取，
  impersonate 自动配平 UA/TLS，勿再手动塞 UA 制造指纹矛盾。自检: https://tls.browserleaks.com/json

维护要点（勿随意改动）:
  1. impersonate 必须用 chrome 系指纹；若微信升级识别，先试 "chrome"→"chrome124" 等轮换。
  2. 正文容器是 div#js_content；懒加载图片真实地址在 data-src，src 常为空占位。
  3. 拿到 200 但无 js_content → 视为拦截页，重试（签名链偶发风控，间隔几秒再试）。
  4. 搜狗来源的直链带 timestamp+signature 临时签名，2-3 天失效——失效不是本脚本的锅。
  5. SSR 兜底（cgiDataNew）仅在极少数纯 SSR 页触发，正则解析不引第三方 JSON 库。
"""
import argparse
import json
import os
import random
import re
import sys
import time
from html import unescape

try:
    from curl_cffi import requests as creq
except ImportError:
    print(json.dumps({"status": "error", "error": "curl_cffi not installed: pip install curl_cffi"}, ensure_ascii=False))
    sys.exit(2)

from lxml import html as lhtml

TIMEOUT = 15
MAX_ATTEMPTS = 3

# P0② 指纹池：会话级随机轮换，避免同 JA3 指纹被聚类风控（教程 02/03 章模式）
# ⚠️ impersonate 自动配平 UA 与 TLS 指纹，禁止再手动覆盖 UA
FINGERPRINT_POOL = ["chrome120", "chrome124", "edge101", "safari17_0"]


# ---------- 取数 ----------

def fetch(url, timeout=TIMEOUT):
    """带重试的 GET（TLS 指纹伪装，会话级随机指纹）。返回 HTML 文本；拦截页/非200 触发重试。"""
    last_err = None
    fp = random.choice(FINGERPRINT_POOL)
    for attempt in range(MAX_ATTEMPTS):
        try:
            r = creq.get(url, impersonate=fp, timeout=timeout, allow_redirects=True)
            if r.status_code != 200:
                last_err = f"HTTP {r.status_code}"
                time.sleep(1.5 * (attempt + 1))
                continue
            text = r.text
            # 拦截页指纹：无正文容器 / 显式风控提示
            if ('id="js_content"' not in text and 'cgiDataNew' not in text) or '环境异常' in text[:3000]:
                last_err = "blocked (anti-bot page)"
                time.sleep(2 * (attempt + 1))
                continue
            return text
        except Exception as e:  # noqa: BLE001
            last_err = f"{type(e).__name__}: {e}"
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"fetch failed after {MAX_ATTEMPTS} attempts: {last_err}")


# ---------- 元数据 ----------

def _js_decode(s):
    """还原微信页面里的 \\xNN 转义（NewsCrawler 实测要点）。"""
    if not s:
        return s
    for token, ch in (("\\x5c", "\\"), ("\\x0d", "\r"), ("\\x22", '"'), ("\\x26", "&"),
                      ("\\x27", "'"), ("\\x3c", "<"), ("\\x3e", ">"), ("\\x0a", "\n")):
        s = s.replace(token, ch)
    return s


def extract_meta(html_text, doc_tree):
    """标题 / 公众号名 / 发布时间。DOM 优先，JS 变量兜底。"""
    title = ""
    node = doc_tree.xpath('//h1[@id="activity-name"]')
    if node:
        title = " ".join(node[0].xpath("string(.)").split())
    if not title:
        m = doc_tree.xpath('//meta[@property="og:title"]/@content')
        title = (m[0] or "").strip() if m else ""
    if not title:
        m = re.search(r"var\s+msg_title\s*=\s*'((?:[^'\\]|\\.)*)'", html_text)
        title = _js_decode(m.group(1)).strip() if m else ""

    author = ""
    node = doc_tree.xpath('//span[@id="profileBt"]')
    if node:
        author = " ".join(node[0].xpath("string(.)").split())
    if not author:
        m = re.search(r"var\s+nickname\s*=\s*'([^']*)'", html_text)
        if not m:
            m = re.search(r'"nick_name":\s*"[^"]*"\s*,\s*"value":\s*"([^"]*)"', html_text)
        author = m.group(1).strip() if m else ""

    publish = ""
    m = re.search(r"var createTime = '(\d{4}-\d{2}-\d{2} \d{2}:\d{2}(:\d{2})?)';", html_text)
    if m:
        publish = m.group(1)
    else:
        m = re.search(r'ori_send_time.*?"(\d{4}-\d{2}-\d{2}[^"<]{0,14})"', html_text)
        publish = m.group(1).strip() if m else ""

    return title, author, publish


# ---------- 正文行走器（移植 NewsCrawler WechatContentParser，lxml 直写） ----------

_BLOCK_TAGS = {"section", "div", "article", "blockquote", "figure"}
_HEAD_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
_SKIP_TAGS = {"script", "style"}


def _node_text(el):
    t = "".join(el.itertext())
    return " ".join(t.split()) if t else ""


def _media_url(el):
    tag = el.tag if isinstance(el.tag, str) else ""
    if tag == "img":
        return el.get("src") or el.get("data-src") or ""
    if tag in ("video", "iframe"):
        return el.get("src") or ""
    return ""


def walk_children(el, blocks):
    """深度优先遍历：文本段与媒体按原文顺序产出。blocks: [(kind, text)]"""
    tag = el.tag if isinstance(el.tag, str) else ""
    if tag in _SKIP_TAGS:
        return

    if tag in _BLOCK_TAGS:
        own = "".join(el.xpath("./text()")).strip()
        if own:
            blocks.append(("text", own))
        for child in el.iterchildren():
            walk_children(child, blocks)
        return

    if tag in _HEAD_TAGS:
        t = _node_text(el)
        if t:
            blocks.append(("heading", t))
        return

    if tag in ("ul", "ol"):
        ordered = tag == "ol"
        idx = 0
        for li in el.iter("li"):
            t = _node_text(li)
            if not t:
                continue
            idx += 1
            blocks.append(("text", f"{idx}. {t}" if ordered else f"• {t}"))
        return

    if tag == "li":
        t = _node_text(el)
        if t:
            blocks.append(("text", f"• {t}"))
        return

    if tag == "p":
        for sub in el.iter():
            u = _media_url(sub)
            if u:
                blocks.append(("image", u))
        t = _node_text(el)
        if t:
            blocks.append(("text", t))
        return

    if tag in ("span", "strong", "a", "em", "b", "i"):
        for sub in el.iter():
            u = _media_url(sub)
            if u:
                blocks.append(("image", u))
        t = _node_text(el)
        if t:
            blocks.append(("text", t))
        return

    u = _media_url(el)
    if u:
        blocks.append(("image", u))
        return

    # 其它容器：继续下探
    for child in el.iterchildren():
        walk_children(child, blocks)


def parse_contents(html_text):
    tree = lhtml.fromstring(html_text)
    containers = tree.xpath('//div[@id="js_content"]')
    blocks = []
    if containers:
        for child in containers[0].iterchildren():
            walk_children(child, blocks)
    else:
        blocks = _parse_ssr_fallback(html_text)

    # 去重（微信页面常见整段重复），保持顺序
    seen, uniq = set(), []
    for kind, txt in blocks:
        key = f"{kind}:{txt}"
        if key not in seen:
            seen.add(key)
            uniq.append((kind, txt))
    return [b for b in uniq if b[1].strip()]


def _parse_ssr_fallback(html_text):
    """极少触发：纯 SSR 页从 cgiDataNew 取 content_noencode/desc。"""
    if "cgiDataNew" not in html_text:
        return []
    m = re.search(r"var\s+desc\s*=\s*'(.*?)';\s*\n", html_text, re.DOTALL)
    if not m:
        m = re.search(r"content_noencode:\s*'(.*?)'\s*,", html_text, re.DOTALL)
    if not m:
        return []
    raw = _js_decode(m.group(1))
    txt = re.sub(r"<[^>]+>", "\n", unescape(raw))
    paras = [" ".join(p.split()) for p in txt.split("\n") if p.strip()]
    return [("text", p) for p in paras]


# ---------- 输出 ----------

def to_markdown(title, author, publish, blocks):
    lines = [f"# {title}" if title else ""]
    meta = " · ".join(x for x in (author, publish) if x)
    if meta:
        lines.append(f"> {meta}")
    for kind, txt in blocks:
        if kind == "heading":
            lines.append(f"\n## {txt}")
        elif kind == "image":
            lines.append(f"\n![img]({txt})")
        else:
            lines.append(f"\n{txt}")
    return "\n".join(lines).strip() + "\n"


def main():
    ap = argparse.ArgumentParser(description="微信公众号文章正文提取 (curl_cffi 指纹伪装)")
    ap.add_argument("url", help="mp.weixin.qq.com 文章链接")
    ap.add_argument("--format", choices=["json", "md"], default="json")
    ap.add_argument("--save-to", default=None, help="落盘路径（utf-8 无 BOM）")
    ap.add_argument("--proxy", default=None, help="none=清空代理环境变量；否则指定代理 URL")
    ap.add_argument("--timeout", type=int, default=TIMEOUT)
    args = ap.parse_args()

    if args.proxy == "none":
        for v in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
            os.environ.pop(v, None)
    elif args.proxy:
        os.environ["HTTP_PROXY"] = os.environ["HTTPS_PROXY"] = args.proxy

    t0 = time.time()
    try:
        html_text = fetch(args.url, timeout=args.timeout)
        tree = lhtml.fromstring(html_text)
        title, author, publish = extract_meta(html_text, tree)
        blocks = parse_contents(html_text)
        if not blocks:
            raise RuntimeError("empty content (js_content missing?)")
    except Exception as e:  # noqa: BLE001
        err = {"status": "error", "url": args.url, "error": str(e)[:300],
               "elapsed": round(time.time() - t0, 1)}
        print(json.dumps(err, ensure_ascii=False))
        sys.exit(1)

    md = to_markdown(title, author, publish, blocks)
    if args.format == "md":
        out = md
    else:
        envelope = {
            "status": "ok", "url": args.url,
            "title": title, "author": author, "publish_time": publish,
            "content": md, "length": len(md),
            "n_text_blocks": sum(1 for k, _ in blocks if k != "image"),
            "n_images": sum(1 for k, _ in blocks if k == "image"),
            "elapsed": round(time.time() - t0, 1),
            "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        out = json.dumps(envelope, ensure_ascii=False, indent=2)

    if args.save_to:
        with open(args.save_to, "w", encoding="utf-8", newline="\n") as f:
            f.write(out)
    print(out)


if __name__ == "__main__":
    main()
