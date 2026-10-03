#!/usr/bin/env python3
"""X（推特）当日热点扫描 —— 多路主题并行采集 + 互动量排序 + 去重。

为什么这么做：X 没有公开趋势榜 API，且**纯过滤词查询会被服务端拒绝**
（`ERROR_NONCLOSE_FORM`，实测 `search --min-likes 5000` 无关键词直接报错）。
所以"当日热点"只能靠「主题关键词 × 互动门槛 × 日期窗口」多路扫描聚合，再用
互动量加权排序。本脚本把这套流程固化，避免每次重写。

依赖：twitter-cli（pipx）+ 用户级 VPN 代理（Agent 注入的代理到不了 x.com）。
      代理与凭证的解析逻辑复用同目录的 tw_run.py。

用法：
    python x_hot_topics.py                          # 默认全量扫描
    python x_hot_topics.py --hours 24               # 只看近 24 小时
    python x_hot_topics.py --themes ai,nvidia,china # 只跑指定主题
    python x_hot_topics.py --out ./x_hot.json       # 落盘原始数据
    python x_hot_topics.py --since 2026-09-13

输出：stdout 打印排序后的热点摘要（可直接读/喂 LLM）；--out 时另存完整 JSON。
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from tw_run import find_twitter, load_creds, user_proxy
except ImportError:
    sys.exit("x_hot_topics.py: 需要与 tw_run.py 同目录（代理与凭证复用其逻辑）")

# ── 主题集：关键词 → (min-likes 门槛, 抓取条数) ───────────────────────────
THEMES = {
    # AI / 算力
    "AI": ("AI", 1500, 40),
    "OpenAI": ("OpenAI", 1000, 30),
    "Anthropic": ("Anthropic", 400, 25),
    "Nvidia": ("Nvidia", 1000, 30),
    "Grok": ("Grok", 800, 20),
    "semiconductor": ("semiconductor", 500, 30),
    "TSMC": ("TSMC", 300, 20),
    "datacenter": ("data center", 300, 20),
    # 科技公司
    "Apple": ("Apple", 1500, 25),
    "Tesla": ("Tesla", 1500, 25),
    "Google": ("Google", 1500, 20),
    "Microsoft": ("Microsoft", 1000, 20),
    "Meta": ("Meta", 1000, 20),
    # 市场 / 宏观
    "market": ("stock market", 800, 30),
    "Fed": ("Federal Reserve", 500, 20),
    "economy": ("economy", 1000, 20),
    "crypto": ("Bitcoin", 1500, 20),
    "gold": ("gold", 800, 15),
    "astock": ("A股", 100, 20),
    # 地缘 / 综合
    "China": ("China", 2000, 35),
    "Trump": ("Trump", 3000, 30),
    "Ukraine": ("Ukraine", 1000, 25),
    "Gaza": ("Gaza", 1000, 20),
    "Japan": ("Japan", 1000, 20),
    "India": ("India", 1000, 20),
    "breaking": ("breaking", 2000, 30),
}

# ── 账号时间线补充源 ─────────────────────────────────────────────────────
ACCOUNTS = {
    "feed": None,                      # 个人首页时间线（--n 60）
    "sama": "@sama",
    "Reuters": "@Reuters",
    "business": "@business",
    "OpenAI": "@OpenAI",
    "nvidia": "@nvidia",
    "spectatorindex": "@spectatorindex",
}


def build_env() -> dict:
    env = dict(os.environ)
    proxy = user_proxy()
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        env[k] = proxy
    env["NO_PROXY"] = "localhost,127.0.0.1"
    env["no_proxy"] = "localhost,127.0.0.1"
    env.update(load_creds())
    return env


def score(t: dict) -> float:
    m = t.get("metrics") or {}
    return ((m.get("likes") or 0) + 2 * (m.get("retweets") or 0)
            + 3 * (m.get("quotes") or 0) + 0.5 * (m.get("replies") or 0))


def parse_ts(t: dict):
    try:
        return dt.datetime.fromisoformat(t.get("createdAtISO"))
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default=None,
                    help="搜索起始日期 YYYY-MM-DD（默认今天北京时间的日期）")
    ap.add_argument("--hours", type=int, default=None, help="只保留最近 N 小时")
    ap.add_argument("--themes", default=None, help="逗号分隔的主题子集，默认全部")
    ap.add_argument("--accounts", action="store_true", help="额外抓账号时间线（默认关，须显式传）")
    ap.add_argument("--top", type=int, default=40, help="摘要打印条数")
    ap.add_argument("--out", default=None, help="原始 JSON 落盘路径")
    ap.add_argument("--workers", type=int, default=6, help="并发数，别调太高以免触发风控")
    a = ap.parse_args()

    now = dt.datetime.now(dt.timezone.utc)
    since = a.since or (now.astimezone(dt.timezone(dt.timedelta(hours=8))).date().isoformat())
    env = build_env()
    exe = find_twitter()

    jobs = []
    names = list(THEMES) if not a.themes else [t.strip() for t in a.themes.split(",") if t.strip()]
    for n in names:
        if n not in THEMES:
            print(f"  跳过未知主题: {n}", file=sys.stderr)
            continue
        q, ml, cnt = THEMES[n]
        jobs.append((f"q:{n}", ["search", q, "--since", since, "--min-likes", str(ml),
                                "-n", str(cnt), "--type", "top", "--json"]))
    if a.accounts:
        for n, acct in ACCOUNTS.items():
            if acct is None:
                jobs.append((f"tl:{n}", ["feed", "-n", "60", "--json"]))
            else:
                jobs.append((f"tl:{n}", ["user-posts", acct, "-n", "30", "--json"]))

    print(f"[x_hot_topics] since={since} 任务数={len(jobs)} 并发={a.workers}", file=sys.stderr)

    def run(job):
        name, args = job
        t0 = time.time()
        try:
            r = subprocess.run([exe] + args, capture_output=True, text=True, env=env,
                               encoding="utf-8", errors="replace", timeout=200)
            d = json.loads(r.stdout) if r.stdout.strip().startswith("{") else \
                {"ok": False, "err": (r.stdout or r.stderr)[:200]}
        except Exception as ex:
            d = {"ok": False, "err": f"{type(ex).__name__}: {ex}"}
        return name, d, time.time() - t0

    results, fails = {}, []
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        for fut in as_completed([pool.submit(run, j) for j in jobs]):
            name, d, secs = fut.result()
            results[name] = d
            n = len(d["data"]) if isinstance(d.get("data"), list) else 0
            print(f"  [{'OK ' if d.get('ok') else 'FAIL'}] {name:20s} {secs:5.1f}s items={n}",
                  file=sys.stderr)
            if not d.get("ok"):
                fails.append((name, str(d.get("err") or d.get("error"))[:120]))

    # 去重 + 合并来源
    merged: dict = {}
    for name, d in results.items():
        if not isinstance(d.get("data"), list):
            continue
        for t in d["data"]:
            if not isinstance(t, dict) or not t.get("id"):
                continue
            tid = t["id"]
            if tid in merged:
                if name not in merged[tid]["_src"]:
                    merged[tid]["_src"].append(name)
            else:
                t["_src"] = [name]
                merged[tid] = t

    items = list(merged.values())
    if a.hours:
        cut = now - dt.timedelta(hours=a.hours)
        items = [t for t in items if parse_ts(t) and parse_ts(t) >= cut]
    items.sort(key=score, reverse=True)

    print(f"\n[x_hot_topics] 去重后 {len(merged)} 条"
          + (f"，窗口内 {len(items)} 条" if a.hours else ""), file=sys.stderr)
    if fails:
        print("[x_hot_topics] 失败项: " + "; ".join(f"{n}:{e}" for n, e in fails), file=sys.stderr)

    print(f"\n{'='*84}\nX 当日热点 TOP {a.top}  (since {since}, 按互动量加权)\n{'='*84}")
    for i, t in enumerate(items[:a.top], 1):
        au = t.get("author") or {}
        m = t.get("metrics") or {}
        txt = (t.get("text") or "").replace("\n", " ").strip()
        print(f"\n[{i:02d}] score={score(t):,.0f} | 赞{m.get('likes',0):,} "
              f"转{m.get('retweets',0):,} 阅{m.get('views',0):,}")
        print(f"     @{au.get('screenName')} ({au.get('name')}) | {t.get('createdAtLocal')} "
              f"| src={','.join(t['_src'])}")
        print(f"     {txt[:320]}")
        if t.get("urls"):
            print(f"     LINK: {t['urls'][:2]}")
        print(f"     https://x.com/{au.get('screenName')}/status/{t.get('id')}")

    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        json.dump({"since": since, "generated": now.isoformat(),
                   "count": len(items), "items": items},
                  open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"\n[x_hot_topics] 已落盘 -> {a.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
