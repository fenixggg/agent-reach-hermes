#!/usr/bin/env python3
"""
rdt_read.py — rdt-cli 泛化安全读帖器（修复 read --json 的序列化 bug）

问题背景（2026-10-03 实测，rdt-cli v0.4.2）：
  `rdt read <id> --json` 输出恒为非法 JSON —— comments 数组结束后跟着一个
  没有键名的裸 ID 数组（"parent_id 回执"），任何 JSON 解析器都会报
  Invalid object。但原始文本里每条评论都在，正则可完整提取。

本脚本策略（对任何帖子通用，不绑定特定任务）：
  1) 先对 rdt 的 stdout 做严格 json.loads（若官方修了 bug 自动走干净路径）；
  2) 失败则降级为正则提取 post 元数据 + 评论五元组；
  3) 两种路径输出同一结构，文本模式按赞数排序（agent 最省 token）。

用法：
  python rdt_read.py <POST_ID 或完整URL> [--max-comments 30] [--order top|asreturned]
  python rdt_read.py 1wd8i8m --json                       # JSON 信封
  python rdt_read.py https://www.reddit.com/r/China/comments/1tkzfl3/xxx/ --save-to out.json
说明：
  - ID 支持裸 ID / t3_ 前缀 / reddit 链接（自动提取）
  - 文本模式：每条评论一行头 [u/author | +score (reply)]，正文截断 --max-body
  - JSON 模式：{"status","mode","post":{...},"comments":[{author,score,parent,body,is_reply}]}
    --save-to 落盘为 UTF-8（无 BOM）
"""
import argparse
import datetime
import json
import re
import subprocess
import sys

WARN_RE = re.compile(r"rdt_cli\.auth|▸ More")
RX_STR = r'"((?:\\.|[^"\\])*)"'
RX_COMMENT = re.compile(
    r'"author":\s*' + RX_STR + r'\s*,\s*"body":\s*' + RX_STR +
    r'\s*,\s*"parent_fullname":\s*"([^"]*)"\s*,\s*"score":\s*(-?\d+)'
)


def run_rdt(post_id: str):
    p = subprocess.run(
        ["rdt", "read", post_id, "--json"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return p.stdout or "", p.stderr or ""


def unj(s: str) -> str:
    """把正则捕获的 JSON 字符串字面量还原为真实文本"""
    try:
        return json.loads('"' + s + '"')
    except Exception:
        return s


def extract_post_id(token: str) -> str:
    token = token.strip().rstrip("/")
    m = re.search(r"/comments/([a-z0-9]+)", token, re.I)
    if m:
        return m.group(1)
    return re.sub(r"^t3_", "", token, flags=re.I)


def iso(ts) -> str:
    try:
        return datetime.datetime.fromtimestamp(float(ts), datetime.timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        return ""


# ---------- 路径 A：严格 JSON（官方修复后生效 / 兼容原始 listing 形态） ----------
def parse_json_mode(raw: str):
    lines = [l for l in raw.splitlines() if not WARN_RE.search(l)]
    data = json.loads("\n".join(lines))
    node = data.get("data", data) if isinstance(data, dict) else {}

    post, comments = {}, []
    if isinstance(node, dict) and isinstance(node.get("post"), dict):
        post = node["post"]
        comments = node.get("comments") or []
    elif isinstance(node, dict):
        inner = node.get("data", node)
        for k in (inner.get("children") or []):
            if k.get("kind") == "t3" and not post:
                post = k.get("data", {})
            elif k.get("kind") == "t1":
                comments.append(k.get("data", {}))
    return post, comments


# ---------- 路径 B：正则降级（当前 rdt-cli 的实际可用路径） ----------
def parse_regex_mode(raw: str):
    def rxs(name):
        m = re.search(r'"%s":\s*%s' % (name, RX_STR), raw)
        return unj(m.group(1)) if m else ""

    def rxi(name):
        m = re.search(r'"%s":\s*(-?\d+(?:\.\d+)?)' % name, raw)
        return float(m.group(1)) if m else 0

    post = {
        "title": rxs("title"),
        "subreddit": rxs("subreddit"),
        "author": rxs("author"),
        "score": int(rxi("score")),
        "num_comments": int(rxi("num_comments")),
        "created_utc": rxi("created_utc"),
        "selftext": rxs("selftext"),
        "permalink": rxs("permalink"),
    }
    comments, seen = [], set()
    for m in RX_COMMENT.finditer(raw):
        author = unj(m.group(1))
        body = unj(m.group(2))
        parent = m.group(3)
        score = int(m.group(4))
        if not author or not body or body in ("[deleted]", "[removed]"):
            continue
        key = (author, body[:60])
        if key in seen:
            continue
        seen.add(key)
        comments.append({
            "author": author,
            "score": score,
            "parent": parent,
            "body": body,
        })
    return post, comments


def normalize(comment: dict) -> dict:
    body = comment.get("body", "")
    if isinstance(body, str):
        body = body.replace("\r\n", "\n")
    parent = comment.get("parent_fullname") or comment.get("parent_id") or comment.get("parent") or ""
    return {
        "author": comment.get("author", ""),
        "score": int(comment.get("score", 0) or 0),
        "parent": parent,
        "body": body,
        "is_reply": bool(parent) and not parent.startswith("t3_"),
    }


def main():
    ap = argparse.ArgumentParser(description="rdt-cli safe reader (fixes malformed --json)")
    ap.add_argument("post", help="帖子 ID（裸 ID/t3_ 前缀）或完整 reddit URL")
    ap.add_argument("--max-comments", type=int, default=30)
    ap.add_argument("--order", choices=["top", "asreturned"], default="top")
    ap.add_argument("--max-body", type=int, default=700, help="文本模式单条评论截断长度")
    ap.add_argument("--json", action="store_true", help="输出 JSON 信封（不截断正文）")
    ap.add_argument("--save-to", help="JSON 信封落盘路径（UTF-8 无 BOM）")
    args = ap.parse_args()

    post_id = extract_post_id(args.post)
    stdout, stderr = run_rdt(post_id)

    post_raw, comments_raw, mode = {}, [], "regex"
    try:
        post_raw, comments_raw = parse_json_mode(stdout)
        if post_raw or comments_raw:
            mode = "json"
    except Exception:
        pass
    if not post_raw and not comments_raw:
        post_raw, comments_raw = parse_regex_mode(stdout)

    if not post_raw and not comments_raw:
        print(f"[rdt_read] 无法从 rdt 输出提取内容（post={post_id}）。", file=sys.stderr)
        tail = (stderr or stdout)[-300:]
        print(tail, file=sys.stderr)
        sys.exit(2)

    post = dict(post_raw)
    post.pop("replies", None)
    post.pop("selftext_html", None)
    post.setdefault("created_iso", iso(post.get("created_utc", 0)))
    comments = [normalize(c) for c in comments_raw]
    comments = [c for c in comments if c["body"] and c["body"] not in ("[deleted]", "[removed]")]
    if args.order == "top":
        comments.sort(key=lambda c: c["score"], reverse=True)
    comments = comments[: args.max_comments]

    envelope = {
        "status": "ok",
        "post_id": post_id,
        "mode": mode,
        "post": post,
        "n_comments_returned": len(comments),
        "comments": comments,
    }

    if args.save_to:
        with open(args.save_to, "w", encoding="utf-8") as f:
            json.dump(envelope, f, ensure_ascii=False, indent=2)

    if args.json:
        print(json.dumps(envelope, ensure_ascii=False, indent=2))
        return

    # ---- 紧凑文本模式 ----
    print(f"=== POST: {post.get('title', '(无标题)')}")
    print(f"r/{post.get('subreddit', '?')} | u/{post.get('author', '?')} | +{post.get('score', 0)}"
          f" | {post.get('num_comments', '?')}cmts | {post.get('created_iso', '')}")
    body = post.get("selftext", "")
    if body and len(body) > 5:
        if len(body) > 2800:
            body = body[:2800] + " ...[TRUNC]"
        print("--- BODY ---")
        print(body)
    print(f"\n=== COMMENTS ({len(comments)}, order={args.order}, mode={mode}) ===")
    for c in comments:
        b = c["body"].replace("\n\n", "\n")
        if len(b) > args.max_body:
            b = b[: args.max_body] + "...[TRUNC]"
        tag = " (reply)" if c["is_reply"] else ""
        print(f"[u/{c['author']} | +{c['score']}{tag}] {b}")
        print("----")


if __name__ == "__main__":
    main()
