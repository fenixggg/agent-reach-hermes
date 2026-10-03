#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quora 问答提取（Firecrawl 渲染 + Markdown 答案切割器）

定位: Quora 是 agent-reach 新增渠道。零浏览器路线已实测全灭（2026-10-03）：
  - curl_cffi 指纹伪装: www/m./RSS/embed/oembed/graphql POST → 全部 CF "Just a moment" 403
  - api.quora.com 老 REST: 活着但答案端点 404（API 已废弃）
  - Quetre 实例: iket.me 问题页 503、search 410，公共实例基本死光
  - 浏览器登录态偷取: Edge 127+ Cookie 库独占锁+App-Bound 加密，不可行
  - NewsCrawler 的 quora.py: 解析的是已下线的旧 push 数据块，移植=死渠道
唯一通路 = 浏览器渲染。本脚本直调 Firecrawl v2 scrape API（绕开 CLI 的 axios 代理 bug，
纯标准库 urllib），把渲染出的 Markdown 按「Profile photo 作者卡 + Upvote· 块尾」切成结构化答案。

用法:
  python s_quora.py "https://www.quora.com/<Question>/answer/<user>"      # 单答案页
  python s_quora.py "https://www.quora.com/<Question>" [--limit 5]        # 问题页多答案
  python s_quora.py URL --format md          # Markdown
  python s_quora.py URL --save-to out.json   # 落盘(无BOM)
  python s_quora.py URL --cookie-file q.txt  # 可选: 登录态提升长文完整度(每行 name=value)

关键实测结论（勿随意改动）:
  1. waitFor>=5000 才能拿到渲染后 DOM；空壳/CF占位时自动升一档重试一次（见 SCRAPE_WAIT）。
  2. 问题页长答案可能被 "Continue Reading" 截断（渲染后未见展开点击）；答案页(/answer/)一般完整。
     要某人的完整长答案 → 优先用 /answer/ 永久链接。
  3. 每次调用烧 Firecrawl 积分(1/次+截图0)。**本渠道不是轻量兜底，Quora 专用**——
     其它站点仍先走 better-webfetch。
  4. 页头 "Something went wrong..." 与页尾 Cloudflare turnstile 残块是固定噪声，已按边界切掉。
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error

API = "https://api.firecrawl.dev/v2/scrape"
PROFILE_RE = re.compile(r"\[!\[Profile photo for (.+?)\]\((https?://[^)]+)\)\]\((https?://[^)]+)\)")
UPVOTE_RE = re.compile(r"^(?:· )?Upvote ·\s*$")
FOOTER_CUTS = ("About the Author", "More answers from", "© Quora", "Checking your Browser",
               "[About](https://www.quora.com/about)")
NAV_PREFIXES = ("[Survey", "[Go to Quora Home", "Sign In", "Skip to", "[About](https://www.quora.com/about)")


def load_key():
    if os.environ.get("FIRECRAWL_API_KEY"):
        return os.environ["FIRECRAWL_API_KEY"].strip()
    for env_path in (r"~/.hermes/.env",
                     os.path.expanduser("~/.hermes/.env")):
        if os.path.exists(env_path):
            for line in open(env_path, encoding="utf-8", errors="ignore"):
                if line.strip().startswith("FIRECRAWL_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def scrape(url, key, wait=7000, timeout=120, cookies=None):
    payload = {"url": url, "formats": ["markdown"], "onlyMainContent": True,
               "waitFor": wait, "maxAge": 0}
    if cookies:
        payload["cookies"] = [{"name": k, "value": v, "domain": ".quora.com"}
                              for k, v in cookies.items()]
    req = urllib.request.Request(API, data=json.dumps(payload).encode(), method="POST",
                                 headers={"Authorization": "Bearer " + key,
                                          "Content-Type": "application/json"})
    try:
        with urllib.request.build_opener().open(req, timeout=timeout) as r:
            d = json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError("Firecrawl HTTP %s: %s" % (e.code, e.read()[:200].decode("utf-8", "ignore")))
    except Exception as e:  # noqa: BLE001
        raise RuntimeError("Firecrawl 请求失败: %s: %s" % (type(e).__name__, str(e)[:150]))
    if not d.get("success"):
        raise RuntimeError("Firecrawl 返回失败: %s" % json.dumps(d)[:200])
    data = d["data"]
    return data.get("markdown", "") or "", (data.get("metadata") or {})


def normalize(url):
    url = url.split("#")[0].split("?")[0]
    if "quora.com" not in url:
        raise ValueError("不是 Quora URL: %s" % url)
    mode = "answer" if "/answer/" in url else "question"
    return url, mode


def _dedupe_continue_reading(text):
    """Quora 长答案渲染有两种形态:
    A)「预览→Continue Reading→全文」: post 开头嵌在 pre 里 → 删预览保全文
    B)「纯折叠」: CR 前只有卡片/图片链接,正文全在 post → 也保 post
    两种都不像(真独立分段,罕见)才拼接并标记。返回 (text, deduped)。"""
    if "Continue Reading" not in text:
        return text, True
    idx = text.find("Continue Reading")
    pre, post = text[:idx], text[idx + len("Continue Reading"):].lstrip("\n ")
    def norm(s, links=False):
        s = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", s)
        if links:
            s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
        return re.sub(r"\s+", "", s)
    npre, npost = norm(pre), norm(post)
    # 全文段有时带折叠标记前缀(如 "+10"),先剥掉再做包含判定
    npost_cmp = re.sub(r"^\+\d+", "", npost)
    if len(npost_cmp) >= 200 and npost_cmp[:50] and npost_cmp[:50] in npre:
        return post, True                      # 形态A
    if len(norm(pre, links=True)) < 150 and len(npost) > 400:
        return post, True                      # 形态B(纯折叠)
    return pre + "\n" + post, False


NOISE_LINE_PATTERNS = [
    re.compile(r"^\[.+?\]\(https://www\.quora\.com/profile/"),          # 作者文字链接行
    re.compile(r"^(?:·\s*)?\[(?:\d+[yMwdh]?|Updated \d+[yMwdh]?)\]"),   # 时间/更新链接行
    re.compile(r"^Best Answer$"),
    re.compile(r"^\d[\d.,]*[KMB]? views?(?:\s*·)?\s*$"),                # "926 views" 行
    re.compile(r"^(?:· )?(?:View upvotes|Upvote)\s*·?\s*$"),
    re.compile(r"^\d{1,3}(?:,\d{3})*$"),                                # 尾块互动数(逗号形式)
    re.compile(r"^\d{2,7}$"),                                           # 尾块互动数(无逗号)
    re.compile(r"^\d{2,3}K?\s*$"),
    re.compile(r"^·?\s*\[(?:View |1 of )"),                             # "View 5 other answers" / "1 of 6 answers"
    re.compile(r"^See more Quora answers"),
    re.compile(r"^Add Quora as a preferred"),
    re.compile(r"^Add to Preferred Sources"),
    re.compile(r"^Originally Answered:"),                                # 转引行(单独入 metadata)
    re.compile(r"^Related\b"),                                           # 相关问题推荐卡
    re.compile(r"^\d+(?:\.\d+)?[KM]?\s+answers?\s*·"),                   # "12 answers · 69.6K views"
    re.compile(r"^What secret about"),                                  # Hottie 侧栏热答标题
    re.compile(r"^\+\d+ ?$"),                                            # 折叠计数行 "+10"
    re.compile(r"^Hottie\b"),
    re.compile(r"^People also ask"),
]
ORIG_Q_RE = re.compile(r"^Originally Answered:\s*\[(.+?)\]\((.+?)\)")


def _is_noise(s):
    return any(p.match(s) for p in NOISE_LINE_PATTERNS)


def _plainize(t):
    p = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", t)
    p = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", p)
    return re.sub(r"\n{3,}", "\n\n", p).strip()


def parse_answers(md, mode):
    """按 Profile photo 作者卡切块 → 答案列表"""
    marks = list(PROFILE_RE.finditer(md))
    # 页脚截断: About the Author / More answers from 之后的 profile 卡是侧栏 ghost
    for cut_marker in ("About the Author", "More answers from"):
        ci = md.find(cut_marker)
        if ci != -1:
            marks = [m for m in marks if m.start() < ci]
    answers = []
    for i, m in enumerate(marks):
        start = m.start()
        end = marks[i + 1].start() if i + 1 < len(marks) else len(md)
        block = md[start:end]
        author = m.group(1).strip()
        lines = block.split("\n")
        # 凭据: profile 卡与正文之间的短行(先剥 markdown 链接再量长度);记录已消耗行号,正文排除之
        creds_lines, consumed = [], set()
        for j in range(1, min(12, len(lines))):
            s = lines[j].strip()
            if not s:
                continue
            if re.match(r"^(?:·\s*)?\[(?:\d+[yMwdh]?|Updated)", s):
                break
            if _is_noise(s):
                consumed.add(j)
                continue
            bare = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s).strip()
            bare = re.sub(r"\s*·\s*", " · ", bare).strip(" ·")
            if bare and bare != author and bare.rstrip("· ") != author.rstrip("· "):
                if len(bare) < 140 and j - 1 < 6:
                    creds_lines.append(bare)
                    consumed.add(j)
            elif bare == author or bare.rstrip("· ") == author.rstrip("· "):
                consumed.add(j)     # 作者名链接行: 跳过不入库也不当正文
            elif len(bare) >= 140:
                break
        creds = " · ".join(c for c in creds_lines if c and c != "!")
        creds = re.sub(r"\s*·\s*[!·]+\s*$", "", creds).strip(" ·!")
        t = re.search(r"\[(\d+[yMwdh]?|Updated \d+[yMwdh]?)\]\([^)]*answer", block[:2500])
        time_ago = (t.group(1) if t else "")
        # 转引原问题
        original_q = ""
        for l in lines:
            mo = ORIG_Q_RE.match(l.strip())
            if mo:
                original_q = mo.group(1)
                break
        # 正文 = 过滤后剩余行(排除已计入 creds 的行)；遇页脚标记断块
        body = []
        for j, l in enumerate(lines):
            if j in consumed:
                continue
            s = l.strip()
            if not s:
                continue
            if any(s.startswith(c) for c in FOOTER_CUTS):
                break
            if _is_noise(s):
                continue
            body.append(s)
        text = "\n".join(body)
        text, cr_deduped = _dedupe_continue_reading(text)
        plain = _plainize(text)
        # plain 再过一遍黑名单+页脚标记(链接转文本后可能露出 "View 5 other answers" 等)
        def _strip_links(l):
            return re.sub(r"\[[^\]]*\]\([^)]*\)", "", l).strip()
        plain = "\n".join(l for l in plain.split("\n")
                          if l.strip() and not _is_noise(_strip_links(l))
                          and not any(_strip_links(l).startswith(c) for c in FOOTER_CUTS))
        if len(plain) < 2:
            continue
        upv = ""
        mu = re.search(r"Upvote\s*·\s*\n\s*(\d{1,3}(?:,\d{3})+|\d+)", block)
        if mu:
            upv = mu.group(1).replace(",", "")
        else:
            tail_nums = re.findall(r"(?m)^(\d{1,3}(?:,\d{3})+|\d{2,7})$", block[-260:])
            if tail_nums:
                upv = str(max(int(x.replace(",", "")) for x in tail_nums))
        mv = re.search(r"([\d.,]+[KMB]?) views", block)
        images = re.findall(r"!\[\]\((https://qph[^)]+)\)", text)
        answers.append({"author": author, "credentials": creds, "time_ago": time_ago,
                        "upvotes": upv, "views": mv.group(1) if mv else "",
                        "original_question": original_q, "cr_deduped": cr_deduped,
                        "text": plain, "text_chars": len(plain),
                        "images": images[:20], "with_images": text})
    # 去重: 同作者取最长文本(侧栏bio块自然落选);再按 author+前80字防真重复
    by_author = {}
    for a in answers:
        prev = by_author.get(a["author"])
        if prev is None or a["text_chars"] > prev["text_chars"]:
            by_author[a["author"]] = a
    ordered = sorted(by_author.values(), key=lambda a: answers.index(a))
    seen, uniq = set(), []
    for a in ordered:
        key = a["author"] + "|" + a["text"][:80]
        if key in seen:
            continue
        seen.add(key)
        uniq.append(a)
    return uniq


def title_from(meta, url, mode):
    t = (meta.get("title") or "").strip()
    t = re.sub(r"'s answer to ", " ▸ ", t)
    t = re.sub(r"\s*-\s*Quora\s*$", "", t)
    return t or url.split("quora.com/", 1)[-1][:80]


def to_markdown(title, url, answers):
    out = ["# %s" % title, "> Quora · %s" % url, ""]
    for i, a in enumerate(answers, 1):
        head = "## %s%s%s" % (a["author"],
                              (" · ▲" + a["upvotes"]) if a["upvotes"] else "",
                              (" · %s前" % a["time_ago"]) if a["time_ago"] else "")
        out += [head]
        if a["credentials"]:
            out.append("> %s" % a["credentials"])
        out += ["", a["with_images"], ""]
    return "\n".join(out).strip() + "\n"


def main():
    ap = argparse.ArgumentParser(description="Quora 答案提取 (Firecrawl 渲染 + Markdown 切割)")
    ap.add_argument("url")
    ap.add_argument("--format", choices=["json", "md"], default="json")
    ap.add_argument("--limit", type=int, default=8, help="问题页最多取几答")
    ap.add_argument("--wait", type=int, default=7000, help="渲染等待 ms")
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--save-to", default=None)
    ap.add_argument("--cookie-file", default=None, help="可选: 每行 name=value 的 quora 登录 Cookie")
    args = ap.parse_args()

    key = load_key()
    if not key:
        print(json.dumps({"status": "error", "error": "FIRECRAWL_API_KEY 未找到(profile .env / ~/.hermes/.env)"}, ensure_ascii=False))
        sys.exit(1)

    url, mode = normalize(args.url)
    cookies = None
    if args.cookie_file and os.path.exists(args.cookie_file):
        cookies = {}
        for line in open(args.cookie_file, encoding="utf-8"):
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.strip().split("=", 1)
                cookies[k] = v

    t0 = time.time()
    md, meta, tries = "", {}, 0
    for wait in (args.wait, min(args.wait + 5000, 15000)):
        tries += 1
        md, meta = scrape(url, key, wait=wait, timeout=args.timeout, cookies=cookies)
        hit = PROFILE_RE.search(md)
        if hit and not re.search(r"Just a moment", md[:500]):
            break
    if not PROFILE_RE.search(md):
        print(json.dumps({"status": "error", "url": url,
                          "error": "页面未渲染出答案结构(tries=%d, mdlen=%d)——可能是登录墙内容/已删除/CF拦截,换 /answer/ 永久链接或 --cookie-file 再试" % (tries, len(md)),
                          "elapsed": round(time.time() - t0, 1)}, ensure_ascii=False))
        sys.exit(1)

    answers = parse_answers(md, mode)[:args.limit]
    if not answers:
        print(json.dumps({"status": "error", "url": url, "error": "答案块解析为空(mdlen=%d)" % len(md)}, ensure_ascii=False))
        sys.exit(1)

    title = title_from(meta, url, mode)
    if args.format == "md":
        out = to_markdown(title, url, answers)
    else:
        slim = [{k: v for k, v in a.items() if k != "with_images"} for a in answers]
        out = json.dumps({"status": "ok", "url": url, "mode": mode, "title": title,
                          "n_answers": len(answers), "answers": slim,
                          "elapsed": round(time.time() - t0, 1), "tries": tries,
                          "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S")},
                         ensure_ascii=False, indent=2)
    if args.save_to:
        with open(args.save_to, "w", encoding="utf-8", newline="\n") as f:
            f.write(out)
    print(out)


if __name__ == "__main__":
    main()
