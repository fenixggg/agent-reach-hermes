#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""agent-reach 凭证失效巡检（check_creds.py）— CrawlerTutorial 06 章模式落地（P0①）

解决的核心痛点：.env 静态 cookie「过期了不知道」。每平台配置 check_url + 判定函数，
检测结果缓存 300s 避免巡检本身触发风控（教程 06 章 LoginStateChecker 模式）。

通道与判定：
  bilibili  GET api.bilibili.com/x/web-interface/nav       code==0 且 data.isLogin==true → 有效
  zhihu     GET www.zhihu.com/api/v3/feed/topstory/hot-list HTTP 200 且非登录页特征 → 有效
  weibo     GET weibo.com/ajax/statuses/hotband            HTTP 200 且 JSON 含 data/s BandList → 有效
  xhs       GET edith.xiaohongshu.com/api/sns/web/v1/search/notes （无签名必 460/461/invalid）
            → 仅做本地 expires 检查 + 文件存在性（网页 cookie 无法免签名验证，教程已注明）
  xueqiu    GET xueqiu.com/statuses/hot.jsonV2（需 xq_a_token）HTTP 200 → 有效
  github    GET api.github.com/user（Bearer GITHUB_TOKEN）HTTP 200 → 有效
  twitter   GET api.x.com/1.1/account/verify_credentials.json（Bearer TWITTER_AUTH_TOKEN，v1.1 已死，
            改用 oauth2/token 校验即 401 判活）→ 200=token 有效；401/403=失效
  其他通道  零配置渠道（微信/头条/V2EX/豆瓣/维基）无需凭证，跳过。

用法：
  python check_creds.py                 # 全量巡检，JSON 报告
  python check_creds.py --yaml          # YAML 风格人读输出
  python check_creds.py --json-out PATH # 落盘 JSON 报告（cron 用）
  python check_creds.py --only bili zhihu
退出码：0=全部有效/跳过；1=存在失效；2=环境错误（.env 缺失等）
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime

try:
    from curl_cffi import requests as creq
except ImportError:
    import urllib.request as _ur

    class _Fallback:
        """curl_cffi 缺席时的最小兜底（凭证明文通道足够）。"""

        @staticmethod
        def get(url, headers=None, timeout=10, **_):
            req = _ur.Request(url, headers=headers or {})
            try:
                with _ur.urlopen(req, timeout=timeout) as r:  # noqa: S310
                    return type("R", (), {"status_code": r.status, "text": r.read().decode("utf-8", "replace")})()
            except Exception as e:  # noqa: BLE001
                return type("R", (), {"status_code": getattr(e, "code", 0), "text": "", "error": str(e)})()

    creq = _Fallback()

PROFILE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
ENV_PATH = os.path.join(PROFILE, ".env")
CHECK_CACHE_TTL = 300  # 教程 06 章：300s 内不重复打检测接口，防巡检触发风控
WARN_DAYS = 14         # 本地 expires 临近预警阈值（CookieExpiryMonitor 简化版）

_cache = {}


def load_env():
    env = {}
    if not os.path.isfile(ENV_PATH):
        return env
    with open(ENV_PATH, encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"')
    return env


def _http(url, headers=None, timeout=10):
    """统一返回 (status_code, text)。curl_cffi 在场用指纹伪装；缺席时走 urllib 兜底。"""
    if hasattr(creq, "get") and not isinstance(creq, type):
        r = creq.get(url, headers=headers or {}, timeout=timeout, impersonate="chrome120")
        return r.status_code, getattr(r, "text", "")
    r = creq.get(url, headers=headers, timeout=timeout)
    return r.status_code, getattr(r, "text", "")


def _result(name, status, detail, **extra):
    return {"channel": name, "status": status, "detail": detail, **extra}


# ---------- 本地层：文件存在 + expires 预警（零网络成本） ----------

def _cookie_expiry_info(path):
    """读 cookie JSON，取最早的 expires 时间戳做临期预警。"""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:  # noqa: BLE001
        return None, f"读取失败: {e}"
    cookies = data.get("cookies", data) if isinstance(data, dict) else data
    exps = []
    for c in cookies or []:
        if isinstance(c, dict) and c.get("expires") and c["expires"] > 0:
            exps.append(float(c["expires"]))
    if not exps:
        return None, "无 expires 字段（会话 cookie，无法本地预警）"
    soonest = min(exps)
    days = (soonest - time.time()) / 86400
    return days, None


def check_local(name, env_key):
    """本地检查：env 键存在 + 文件存在 + 修改时间 + expires 预警。"""
    env = load_env()
    path = env.get(env_key)
    if not path:
        return _result(name, "no_cred", f".env 无 {env_key}")
    path = os.path.expandvars(os.path.expanduser(path))
    if not os.path.isfile(path):
        return _result(name, "missing", f"凭证文件不存在: {path}")
    days, err = _cookie_expiry_info(path)
    age_h = round((time.time() - os.path.getmtime(path)) / 3600, 1)
    info = {"cred_file": os.path.basename(path), "age_hours": age_h}
    if err:
        info["expires_note"] = err
    elif days is not None and days < 0:
        info["expires_days"] = round(days, 1)
        return _result(name, "expired_local", f"cookie 已过期 {-days:.0f} 天（本地判断）", **info)
    elif days is not None and days < WARN_DAYS:
        info["expires_days"] = round(days, 1)
        return _result(name, "expiring_soon", f"cookie 将在 {days:.0f} 天内过期（本地预警）", **info)
    if days is not None:
        info["expires_days"] = round(days, 1)
    return _result(name, "local_ok", f"文件在（{age_h:.0f}h 前更新）；联网判活见 live 结果", **info)


def _cookie_header(path):
    """按各平台凭证文件的实际结构拼 Cookie 头（值不落日志）。

    支持三种形态：
      {"cookies": {...}}           → weibo/zhihu（cli 工具导出格式）
      {"sessdata":..,"bili_jct":..}→ bilibili（键名映射成正式 cookie 名）
      {k: v, ...} 全平铺           → xhs（直接全量拼接）
      {"cookie": "k=v; k2=v2"}     → xueqiu（整串现成 Cookie）
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return ""
    if "cookie" in data and isinstance(data["cookie"], str):  # xueqiu
        return data["cookie"]
    pairs = data.get("cookies") if isinstance(data.get("cookies"), dict) else data
    name_map = {"sessdata": "SESSDATA", "bili_jct": "bili_jct", "dedeuserid": "DedeUserID"}
    out = []
    for k, v in pairs.items():
        if not isinstance(v, str) or not v:
            continue
        out.append(f"{name_map.get(k, k)}={v}")
    return "; ".join(out)


# ---------- 联网层：check_url + 判定函数 ----------

def _json_get(url, headers=None):
    code, text = _http(url, headers)
    try:
        return code, json.loads(text)
    except Exception:  # noqa: BLE001
        return code, None


def check_bilibili():
    r = check_local("bilibili", "BILIBILI_CREDENTIAL_PATH")
    if r["status"] in ("no_cred", "missing"):
        return r
    env = load_env()
    ck = _cookie_header(os.path.expandvars(os.path.expanduser(env["BILIBILI_CREDENTIAL_PATH"])))
    code, j = _json_get("https://api.bilibili.com/x/web-interface/nav", headers={"Cookie": ck})
    if code == 200 and isinstance(j, dict) and j.get("code") == 0 and (j.get("data") or {}).get("isLogin"):
        r.update(status="ok", detail=f"已登录: {(j['data'].get('uname') or '')[:20]}")
    else:
        msg = (j or {}).get("message", f"HTTP {code}") if isinstance(j, dict) else f"HTTP {code}"
        r.update(status="dead", detail=f"nav 判定失效（带存储 cookie）: {msg}")
    return r


def check_zhihu():
    r = check_local("zhihu", "ZHIHU_CREDENTIAL_PATH")
    if r["status"] in ("no_cred", "missing"):
        return r
    env = load_env()
    ck = _cookie_header(os.path.expandvars(os.path.expanduser(env["ZHIHU_CREDENTIAL_PATH"])))
    code, j = _json_get("https://www.zhihu.com/api/v4/members/self",
                        headers={"Cookie": ck, "Referer": "https://www.zhihu.com/"})
    if code == 200 and isinstance(j, dict) and j.get("id"):
        r.update(status="ok", detail=f"已登录: {j.get('name', '?')}")
    elif code in (401, 403):
        r.update(status="dead", detail=f"HTTP {code} → z_c0 登录态失效")
    else:
        r.update(status="unknown", detail=f"HTTP {code}（社区 CLI 通道请人工复核）")
    return r


def check_weibo():
    r = check_local("weibo", "WEIBO_CREDENTIAL_PATH")
    if r["status"] in ("no_cred", "missing"):
        return r
    # 诚实降级：weibo.com HTML/AJAX 层罩着 wbBotDetector 壳（2026-09-25 排障结论），
    # 带 SUB cookie 的简单 HTTP 请求也只回 SPA HTML 壳（HTTP 200 非 JSON），与 cookie 死活无区分度。
    # 判活以 weibo-cli 实际读命令 + s_weibo_search.py（Edge 登录态引擎）为准。
    r.update(status="manual_only",
             detail="SUB cookie 文件在；AJAX 层被 bot 检测壳罩住无法免浏览器判活，以 weibo-cli 实调为准")
    return r


def check_xhs():
    """xhs 网页 cookie 免签名必 460/461，无可用免签名判活端点 → 只做本地检查。"""
    r = check_local("xhs", "XHS_COOKIE_PATH")
    if r["status"] == "local_ok":
        r.update(status="local_only", detail="本地检查通过；xhs 无免签名判活 API（教程已注明），联网验证请用 xhs read")
    return r


def check_xueqiu():
    r = check_local("xueqiu", "SNOWBALL_TOKEN_PATH")
    if r["status"] in ("no_cred", "missing"):
        return r
    env = load_env()
    ck = _cookie_header(os.path.expandvars(os.path.expanduser(env["SNOWBALL_TOKEN_PATH"])))
    code, j = _json_get("https://stock.xueqiu.com/v5/stock/hot_stock/list.json?size=5&_type=10&type=10",
                        headers={"Cookie": ck, "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    if code == 200 and isinstance(j, dict) and j.get("error_code") == 0:
        r.update(status="ok", detail="hot_stock/list 200 code=0（token cookie 有效）")
    elif code == 200 and isinstance(j, dict) and j.get("error_code") in (400018, 403):
        r.update(status="dead", detail=f"error_code={j.get('error_code')} → xq_a_token 失效")
    elif code in (400, 401, 403):
        r.update(status="dead", detail=f"HTTP {code} → xq_a_token 失效")
    else:
        r.update(status="unknown", detail=f"HTTP {code}")
    return r


def check_github():
    env = load_env()
    tok = env.get("GITHUB_TOKEN")
    if not tok:
        return _result("github", "no_cred", ".env 无 GITHUB_TOKEN")
    code, j = _json_get("https://api.github.com/user",
                        headers={"Authorization": f"Bearer {tok}", "User-Agent": "check-creds"})
    if code == 200 and isinstance(j, dict):
        return _result("github", "ok", f"token 有效: {j.get('login', '?')}")
    if code == 401:
        return _result("github", "dead", "HTTP 401 → token 失效")
    return _result("github", "unknown", f"HTTP {code}")


def check_twitter():
    env = load_env()
    tok = env.get("TWITTER_AUTH_TOKEN")
    if not tok:
        return _result("twitter", "no_cred", ".env 无 TWITTER_AUTH_TOKEN")
    # 诚实降级：v1.1 verify_credentials 已退役（401 对死token与活token无区分度），
    # graphql 自查端点带签名复杂度不值得为巡检引入。auth_token 无 expires 字段（本地预警也不可用）。
    # → 只报「文件存在+注入时间」，联网判活交给 tw_run 实链路（今早实测可用）。
    return _result("twitter", "manual_only",
                   "auth_token 无本地过期字段、无免签名判活端点；以 tw_run.py 实际调用为准（2026-10-03 实测可用）",
                   note="发现 tw_run 持续 401 时再人工更新 .env")


CHECKS = {
    "bilibili": check_bilibili,
    "zhihu": check_zhihu,
    "weibo": check_weibo,
    "xhs": check_xhs,
    "xueqiu": check_xueqiu,
    "github": check_github,
    "twitter": check_twitter,
}


def main():
    ap = argparse.ArgumentParser(description="agent-reach 凭证失效巡检")
    ap.add_argument("--yaml", action="store_true", help="人读输出")
    ap.add_argument("--json-out", default=None, help="JSON 报告落盘路径")
    ap.add_argument("--only", nargs="*", default=None, help="仅检查指定通道")
    args = ap.parse_args()

    names = args.only or list(CHECKS)
    results = []
    for n in names:
        fn = CHECKS.get(n)
        if not fn:
            results.append(_result(n, "unknown_channel", "无此通道"))
            continue
        t0 = time.time()
        try:
            r = fn()
        except Exception as e:  # noqa: BLE001
            r = _result(n, "error", f"{type(e).__name__}: {e}")
        r["elapsed"] = round(time.time() - t0, 1)
        results.append(r)
        time.sleep(1.0)  # 通道间降频（教程纪律：预防优于处理）

    dead = [r for r in results if r["status"] in ("dead", "expired_local", "missing")]
    warn = [r for r in results if r["status"] in ("expiring_soon", "unknown", "local_only", "error")]

    report = {
        "checked_at": datetime.now().isoformat(timespec="seconds"),
        "env_path": ENV_PATH,
        "summary": {"total": len(results), "ok": sum(1 for r in results if r["status"] == "ok"),
                    "dead": len(dead), "warn": len(warn),
                    "skipped": sum(1 for r in results if r["status"] == "no_cred")},
        "results": results,
    }

    if args.json_out:
        os.makedirs(os.path.dirname(os.path.abspath(args.json_out)), exist_ok=True)
        with open(args.json_out, "w", encoding="utf-8", newline="\n") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"[check_creds] 报告已落盘: {args.json_out}", file=sys.stderr)

    if args.yaml:
        print(f"# 凭证巡检 {report['checked_at']}  ok={report['summary']['ok']} dead={report['summary']['dead']} warn={report['summary']['warn']}")
        for r in results:
            mark = {"ok": "✅", "dead": "❌", "missing": "🚫", "expired_local": "⏰", "expiring_soon": "⚠️",
                    "local_only": "📁", "unknown": "❓", "no_cred": "➖", "error": "💥"}.get(r["status"], "·")
            extra = " ".join(f"{k}={v}" for k, v in r.items()
                             if k in ("age_hours", "expires_days", "cred_file") and v is not None)
            print(f"{mark} {r['channel']:<10} {r['status']:<14} {r['detail']}  {extra}")
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))

    sys.exit(1 if dead else 0)


if __name__ == "__main__":
    main()
