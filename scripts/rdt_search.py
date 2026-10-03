#!/usr/bin/env python3
"""
rdt_search.py — rdt-cli 泛化搜索器（防上下文爆炸 + 紧凑解析）

问题背景（2026-10-03 实测，rdt-cli v0.4.2）：
  `rdt search --yaml` 单次可输出 30 万+ 字符（帖子全文+HTML+元数据），
  直接喂给 agent 会瞬间撑爆上下文；官方建议的 --yaml 对 agent 是反模式。

本脚本策略（对任何关键词通用）：
  1) 调 `rdt search <query> --json`，先走严格 json.loads（官方路径）；
  2) 失败则降级正则提取，只保留 agent 需要的六个字段；
  3) 文本模式每帖 2-3 行（ID/版块/赞/评论数/日期 + 标题 + 摘要），
     拿到 ID 列表后再用 rdt_read.py 逐帖深读。

用法：
  python rdt_search.py "medical tourism China" [--limit 10] [--snip 220]
  python rdt_search.py "dental China" --json --save-to out.json
"""
import argparse
import datetime
import json
import re
import subprocess
import sys

WARN_RE = re.compile(r"rdt_cli\.auth|▸ More")
RX_STR = r'"((?:\\.|[^"\\])*)"'


def run_rdt(query: str, limit: int):
    p = subprocess.run(
        ["rdt", "search", query, "--limit", str(limit), "--json"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return p.stdout or "", p.stderr or ""


def unj(s: str) -> str:
    try:
        return json.loads('"' + s + '"')
    except Exception:
        return s


def children_from_json(raw: str):
    lines = [l for l in raw.splitlines() if not WARN_RE.search(l)]
    data = json.loads("\n".join(lines))
    # envelope 形态1: {data: {data: {children}}}；形态2: 裸 Listing {data:{children}}
    node = data.get("data", data)
    inner = node.get("data", node) if isinstance(node, dict) else node
    children = inner.get("children") or []
    norm = []
    for c in children:
        if not isinstance(c, dict):
            continue
        kind = c.get("kind")
        d = c.get("data") or {}
        if kind in ("t3", "t1") and d:
            norm.append({"kind": kind, **d})
    return norm


def children_from_regex(raw: str):
    """按 kind 分段：先切出每个 child 的 kind，再在其窗口内提取字段。"""
    out = []
    for m in re.finditer(r'"kind":\s*"((?:\\.|[^"\\])*)"', raw):
        kind = unj(m.group(1))
        if kind not in ("t3", "t1"):
            continue
        seg = raw[m.end(): m.end() + 30000]
        nxt = re.search(r'"kind":\s*"t[13]"', seg)
        if nxt:
            seg = seg[: nxt.start()]

        def rxs(name, s=seg):
            mm = re.search(r'"%s":\s*%s' % (name, RX_STR), s)
            return unj(mm.group(1)) if mm else ""

        def rxi(name, s=seg):
            mm = re.search(r'"%s":\s*(-?\d+)' % name, s)
            return int(mm.group(1)) if mm else 0

        if kind == "t3":
            out.append({
                "kind": "t3",
                "id": rxs("id"),
                "subreddit": rxs("subreddit"),
                "title": rxs("title"),
                "score": rxi("score"),
                "num_comments": rxi("num_comments"),
                "created_utc": rxi("created_utc"),
                "selftext": rxs("selftext"),
                "permalink": rxs("permalink"),
            })
        else:
            out.append({
                "kind": "t1",
                "id": rxs("id"),
                "author": rxs("author"),
                "body": rxs("body"),
                "score": rxi("score"),
            })
    return out


def iso(ts) -> str:
    try:
        return datetime.datetime.fromtimestamp(float(ts), datetime.timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        return ""


def main():
    ap = argparse.ArgumentParser(description="rdt-cli compact search")
    ap.add_argument("query")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--snip", type=int, default=220, help="selftext 摘要长度")
    ap.add_argument("--json", action="store_true", help="输出 JSON（含摘要）")
    ap.add_argument("--save-to", help="JSON 落盘路径（UTF-8 无 BOM）")
    args = ap.parse_args()

    stdout, stderr = run_rdt(args.query, args.limit)

    children, mode = [], "regex"
    try:
        children = children_from_json(stdout)
        if children:
            mode = "json"
    except Exception:
        pass
    if not children:
        children = children_from_regex(stdout)

    posts = [c for c in children if isinstance(c, dict) and c.get("kind") == "t3"]
    if not posts:
        print("[rdt_search] 无结果或解析失败。", file=sys.stderr)
        print((stderr or stdout)[-300:], file=sys.stderr)
        sys.exit(2)

    for p in posts:
        p["created_iso"] = iso(p.get("created_utc", 0))
        st = p.get("selftext") or ""
        st = re.sub(r"\s+", " ", st).strip()
        p["snippet"] = st[: args.snip] + ("..." if len(st) > args.snip else "")
        p["url"] = "https://www.reddit.com" + (p.get("permalink") or "")

    envelope = {"status": "ok", "mode": mode, "query": args.query, "n": len(posts), "posts": posts}
    if args.save_to:
        with open(args.save_to, "w", encoding="utf-8") as f:
            json.dump(envelope, f, ensure_ascii=False, indent=2)
    if args.json:
        print(json.dumps(envelope, ensure_ascii=False, indent=2))
        return

    print(f"# rdt search: {args.query}  ({len(posts)} results, mode={mode})")
    for p in posts:
        print(f"ID={p['id']} | r/{p['subreddit']} | +{p['score']} | {p['num_comments']}cmts | {p['created_iso']}")
        print(f"  TITLE: {p['title']}")
        if p["snippet"]:
            print(f"  SNIP: {p['snippet']}")
        print()


if __name__ == "__main__":
    main()
