#!/usr/bin/env python3
"""Wikidata 抓取 — 官方 API + SPARQL，免密钥、免登录。

与 s_wikipedia.py 是天然一对：Wikipedia 的 summary 返回 wikibase_item（Q 编号），
拿来喂本脚本即可取结构化事实 / 多语言标签 / 跨语言等价判定。

全部经本机实测（2026-09）。四个端点分工：
  * Special:EntityData/{Q}.json  —— 【实体全量】labels/descriptions/aliases/sitelinks/claims
       最省事，一次拿到全部字段，含 aliases（wbgetentities 不显式请求就没有）。
  * action=wbgetentities          —— 【批量】一次取多个 Q，可限定 props/languages 省流量。
  * action=wbsearchentities       —— 【实体搜索】关键词 → Q 编号候选（含 description 消歧）。
  * query.wikidata.org/sparql     —— 【结构化查询】任意 SPARQL，拿 Wikipedia 正文里没有的事实。

⚠️ 实测踩坑：
  1. wbgetentities 的 props 必须显式列全。只写 "labels|descriptions" 时
     aliases/sitelinks/claims 一律不返回（不是默认全给）。
  2. SPARQL 响应【没有】x-ratelimit-* 头（Wikipedia REST 有 ETag，这里没有预告头）。
     限流表现为直接 429 / "Query timeout"。只能靠 429 重试 + 语义化 query 兜。
  3. SPARQL 查询超时 60s 硬上限。大范围查询必须带 LIMIT 且尽量精确。
  4. claims 里 datavalue.value.id 可能返回多个（如 P159 总部 → Q189471 Q22041180），
     那是限定符/多值，取 mainsnak 才是主值。

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

UA = os.environ.get(
    "WD_UA",
    "agent-reach/1.0 (https://github.com/agent-reach; wikidata channel)",
)
MIN_INTERVAL = float(os.environ.get("WD_MIN_INTERVAL", "0.8"))
_last_call = [0.0]
MAX_RETRY = 3

# 常用属性的中文名（供 fact 动作把 P 编号翻译成人话，不必每次查标签）
PROP_LABELS = {
    "P31": "instance of / 是…的实例",
    "P279": "subclass of / 上级分类",
    "P361": "part of / 隶属于",
    "P571": "inception / 成立时间",
    "P576": "dissolved / 解散时间",
    "P159": "headquarters location / 总部",
    "P17": "country / 国家",
    "P112": "founded by / 创始人",
    "P127": "owned by / 所有者",
    "P169": "CEO / 首席执行官",
    "P108": "employer / 雇主",
    "P69": "educated at / 母校",
    "P106": "occupation / 职业",
    "P569": "date of birth / 出生日期",
    "P570": "date of death / 逝世日期",
    "P19": "place of birth / 出生地",
    "P27": "country of citizenship / 国籍",
    "P50": "author / 作者",
    "P57": "director / 导演",
    "P86": "composer / 作曲",
    "P136": "genre / 类型",
    "P577": "publication date / 出版日期",
    "P175": "performer / 表演者",
    "P264": "record label / 唱片公司",
    "P400": "platform / 平台",
    "P277": "programming language / 编程语言",
    "P348": "software version / 软件版本",
    "P856": "official website / 官网",
    "P1566": "GeoNames ID",
    "P625": "coordinate location / 坐标",
    "P18": "image / 图像",
    "P373": "Commons category / 共享资源分类",
    "P910": "topic's main category",
}


class RateLimited(RuntimeError):
    pass


class WdError(RuntimeError):
    pass


def _throttle():
    gap = time.time() - _last_call[0]
    if gap < MIN_INTERVAL:
        time.sleep(MIN_INTERVAL - gap)
    _last_call[0] = time.time()


def _get(url: str, *, accept: str = "application/json"):
    last_err = None
    for attempt in range(MAX_RETRY):
        _throttle()
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                body = r.read().decode("utf-8", "replace")
            low = body[:400].lower()
            if "too many requests" in low or "query timeout" in low:
                raise RateLimited(body[:160])
            return json.loads(body)
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "replace")
            if e.code in (429, 503):
                last_err = RateLimited(f"HTTP {e.code}: {raw[:120]}")
            elif e.code == 404:
                raise WdError(f"NOT_FOUND: {url}") from e
            elif e.code == 400:
                raise WdError(f"BAD_REQUEST: {raw[:200]}") from e
            else:
                last_err = WdError(f"HTTP {e.code}: {raw[:160]}")
        except Exception as e:  # noqa: BLE001
            last_err = e
        time.sleep(1.5 * (2**attempt))
    raise last_err if isinstance(last_err, Exception) else WdError("unknown")


def _api(params: dict):
    params = {**params, "format": "json"}
    return _get(f"https://www.wikidata.org/w/api.php?{urllib.parse.urlencode(params)}")


def _norm_ids(raw: str):
    ids = [x.strip().upper() for x in raw.replace(",", "|").split("|") if x.strip()]
    bad = [x for x in ids if not (x.startswith("Q") or x.startswith("P")) or not x[1:].isdigit()]
    if bad:
        raise WdError(f"BAD_ID: 需 Q/P 编号格式，收到 {bad}")
    return ids


def _snak_value(snak):
    """从 claim 的 snak 里提取人类可读值。"""
    if not snak or snak.get("snaktype") != "value":
        return None
    dv = snak.get("datavalue") or {}
    t, v = dv.get("type"), dv.get("value")
    if t == "wikibase-entityid":
        return v.get("id")
    if t == "time":
        return f"{v.get('time', '')[1:11]}"
    if t == "quantity":
        return v.get("amount")
    if t == "monolingualtext":
        return v.get("text")
    if t == "globecoordinate":
        return f"{v.get('latitude')},{v.get('longitude')}"
    if t == "string":
        return v
    return v


def _qids_in_claim(claim):
    """从 claim 的 mainsnak 里提取被引用的实体 Q 编号（若有）。"""
    ms = claim.get("mainsnak") or {}
    v = _snak_value(ms)
    return [v] if isinstance(v, str) and v.startswith("Q") else []


# ---------- 各动作 ----------

def op_entity(qid: str, *, languages: str = "zh|en", with_claims: bool = True, max_claims: int = 30) -> dict:
    """实体全量：labels/descriptions/aliases/sitelinks（+ 可选 claims）。"""
    d = _get(f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json")
    q = (d.get("entities") or {}).get(qid)
    if not q:
        raise WdError(f"NOT_FOUND: 实体 {qid} 不存在")

    langs = [x for x in languages.replace(",", "|").split("|") if x]
    labels = {k: v.get("value") for k, v in (q.get("labels") or {}).items() if k in langs}
    descs = {k: v.get("value") for k, v in (q.get("descriptions") or {}).items() if k in langs}
    aliases = {k: [a.get("value") for a in (q.get("aliases") or {}).get(k, [])] for k in langs if (q.get("aliases") or {}).get(k)}

    # 所有语言的标签（消歧时有用，但可能上百个 → 只在需要时给）
    all_label_langs = sorted((q.get("labels") or {}).keys())

    # sitelinks：只保留各语言维基百科（消歧/跨语言定位用），最多 12 条
    sitelinks = {}
    for site, sl in (q.get("sitelinks") or {}).items():
        if not (site.endswith("wiki") and not site.endswith(("wikiquote", "wiktionary", "wikisource", "wikinews", "wikivoyage"))):
            continue
        lang_code = site[:-4]  # 去掉 "wiki"
        title = sl.get("title") or ""
        sitelinks[site] = {
            "title": title,
            "url": f"https://{lang_code}.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}",
        }

    out = {
        "id": qid,
        "labels": labels,
        "descriptions": descs,
        "aliases": aliases,
        "label_languages": all_label_langs,
        "sitelink_count": len(q.get("sitelinks") or {}),
        "sitelinks": {k: v for k, v in list(sitelinks.items())[:12]},
        "url": f"https://www.wikidata.org/wiki/{qid}",
    }

    if with_claims:
        claims = q.get("claims") or {}
        facts = []
        for pid, arr in claims.items():
            if not arr:
                continue
            main = arr[0]
            val = _snak_value(main.get("mainsnak") or {})
            if val is None:
                continue
            facts.append({
                "property": pid,
                "property_label": PROP_LABELS.get(pid),
                "value": val,
                "value_kind": "entity_ref" if isinstance(val, str) and val.startswith("Q") else "literal",
                "value_url": f"https://www.wikidata.org/wiki/{val}" if isinstance(val, str) and val.startswith("Q") else None,
                "claim_count": len(arr),
            })
        # 优先输出有中文标签的常用属性
        facts.sort(key=lambda f: (f["property_label"] is None, f["property"]))
        out["facts"] = facts[:max_claims]
        out["facts_total"] = len(facts)
        out["facts_truncated"] = len(facts) > max_claims
    return out


def op_batch(raw_ids: str, *, languages: str = "zh|en") -> dict:
    """批量取多个实体的标签/描述（轻量，适合消歧对比）。"""
    ids = _norm_ids(raw_ids)
    if len(ids) > 50:
        raise WdError("BATCH_TOO_LARGE: 建议 ≤50，分批请求")
    d = _api({"action": "wbgetentities", "ids": "|".join(ids), "props": "labels|descriptions|aliases", "languages": languages})
    out = []
    for qid in ids:
        e = (d.get("entities") or {}).get(qid) or {}
        if not e or e.get("missing") is not None:
            out.append({"id": qid, "error": "NOT_FOUND"})
            continue
        out.append({
            "id": qid,
            "labels": {k: v.get("value") for k, v in (e.get("labels") or {}).items()},
            "descriptions": {k: v.get("value") for k, v in (e.get("descriptions") or {}).items()},
            "aliases": {k: [a.get("value") for a in v] for k, v in (e.get("aliases") or {}).items()},
            "url": f"https://www.wikidata.org/wiki/{qid}",
        })
    return {"count": len(out), "items": out}


def op_search(query: str, *, language: str = "zh", limit: int = 7) -> dict:
    """按关键词搜实体 → 返回 Q 编号候选 + description（消歧关键）。"""
    d = _api({"action": "wbsearchentities", "search": query, "language": language, "uselang": language, "limit": str(limit), "type": "item"})
    items = [{
        "id": x.get("id"),
        "label": x.get("label"),
        "description": x.get("description"),
        "aliases": x.get("aliases") or [],
        "match": (x.get("match") or {}).get("text"),
        "url": x.get("concepturi") or f"https://www.wikidata.org/wiki/{x.get('id')}",
    } for x in (d.get("search") or [])]
    return {"query": query, "language": language, "count": len(items), "items": items}


def op_sparql(query: str) -> dict:
    """任意 SPARQL 查询（60s 超时硬上限；务必带 LIMIT）。

    ⚠️ 实测坑：
      * 不写 LIMIT 会返回海量行（实测 `wd:Q42 ?p ?x` 无 LIMIT → 972 行垃圾，
        含上千条 statement URI）。所以本函数在无 LIMIT 时自动追加 LIMIT 200 并在
        note 里告知——防止 agent 误吞几十万行。
      * SELECT 的变量必须在 WHERE 里真实绑定，否则【不报错】只返回空 bindings
        （实测 SELECT ?pLabel 但 WHERE 未绑 ?pLabel → bindings 全是 {}）。
      * 通过 PowerShell/命令行传 SPARQL 时，`"zh,en"` 的引号极易被 shell 剥掉
        → label service 语法错误。务必用 --query 配合单引号，或写进文件再读。
    """
    if len(query) > 4000:
        raise WdError("QUERY_TOO_LONG: SPARQL 查询建议 <4000 字符")
    auto_limit = False
    if not re.search(r"\bLIMIT\b", query, flags=re.I):
        query = query.rstrip().rstrip(".") + " LIMIT 200"
        auto_limit = True
    u = f"https://query.wikidata.org/sparql?{urllib.parse.urlencode({'query': query, 'format': 'json'})}"
    d = _get(u, accept="application/sparql-results+json")
    try:
        vars_ = d["head"]["vars"]
        rows = []
        for b in d["results"]["bindings"]:
            rows.append({v: (b.get(v) or {}).get("value") for v in vars_})
        out = {"vars": vars_, "count": len(rows), "rows": rows}
        if auto_limit:
            out["note"] = "查询未含 LIMIT，已自动追加 LIMIT 200（防超大结果集）"
        if rows and all(not any(r.values()) for r in rows):
            out["warning"] = "所有行均为空：SELECT 的变量可能未在 WHERE 中绑定（SPARQL 静默失败）"
        return out
    except (KeyError, TypeError) as e:
        raise WdError(f"BAD_SPARQL_RESULT: {str(d)[:200]}") from e


def _resolve_labels(qids: list, *, languages: str = "zh|en") -> dict:
    """把一批 Q 编号解析成 {qid: {lang: label}}。用于让 fact 输出可读。

    实测：wbgetentities 一次最多 50 个 id，超出需分批。
    """
    qids = [q for q in dict.fromkeys(qids) if q]
    out = {}
    for i in range(0, len(qids), 50):
        chunk = qids[i:i + 50]
        try:
            d = _api({"action": "wbgetentities", "ids": "|".join(chunk), "props": "labels", "languages": languages})
        except Exception:  # noqa: BLE001 — 解析失败不该让主流程崩
            return out
        for qid, e in (d.get("entities") or {}).items():
            labs = {k: v.get("value") for k, v in (e.get("labels") or {}).items()}
            if labs:
                out[qid] = labs
        if len(qids) > 50:
            time.sleep(1.0)
    return out


def op_fact(qid: str, *, languages: str = "zh|en") -> dict:
    """精简结构化事实摘要（人读友好），从 entity 里挑常用属性。

    会把引用到的 Q 编号解析成中文标签——否则用户看到 "Q483382" 毫无意义。
    """
    e = op_entity(qid, languages=languages, with_claims=True, max_claims=200)
    interesting = ["P31", "P279", "P361", "P571", "P576", "P159", "P17", "P112", "P127", "P169",
                   "P106", "P569", "P570", "P19", "P27", "P50", "P57", "P86", "P136", "P577",
                   "P175", "P400", "P277", "P348", "P856", "P625"]
    picked = [f for f in e.get("facts", []) if f["property"] in interesting]

    # 解析引用的实体标签
    refs = [f["value"] for f in picked if f.get("value_kind") == "entity_ref"]
    label_map = _resolve_labels(refs, languages=languages) if refs else {}
    for f in picked:
        if f.get("value_kind") == "entity_ref":
            labs = label_map.get(f["value"]) or {}
            f["value_label"] = labs.get("zh") or labs.get("en")
            f["value_label_all"] = labs or None

    return {
        "id": qid,
        "label": e["labels"].get("zh") or e["labels"].get("en"),
        "description": e["descriptions"].get("zh") or e["descriptions"].get("en"),
        "facts": picked,
        "fact_count": len(picked),
        "url": e["url"],
    }


ACTIONS = {
    "entity": lambda a: op_entity(a.target, languages=a.languages, with_claims=not a.no_claims, max_claims=a.max_claims),
    "fact": lambda a: op_fact(a.target, languages=a.languages),
    "batch": lambda a: op_batch(a.target, languages=a.languages),
    "search": lambda a: op_search(a.target, language=a.search_lang, limit=a.limit),
    "sparql": lambda a: op_sparql(a.query or a.target),
}


def main() -> int:
    p = argparse.ArgumentParser(description="Wikidata 抓取（官方 API + SPARQL，免密钥）")
    p.add_argument("action", choices=sorted(ACTIONS), help="动作")
    p.add_argument("target", nargs="?", help="Q编号(entity/fact) | Q列表(batch) | 关键词(search) | SPARQL(sparql)")
    p.add_argument("--languages", default="zh|en", help="标签语言，默认 zh|en")
    p.add_argument("--search-lang", default="zh", help="search 的检索语言")
    p.add_argument("--limit", type=int, default=7, help="search 结果数")
    p.add_argument("--max-claims", type=int, default=30, help="entity 最多返回多少条 facts")
    p.add_argument("--no-claims", action="store_true", help="entity 不取 claims（更快）")
    p.add_argument("--query", help="SPARQL 语句（替代 target 传参，避免转义问题）")
    p.add_argument("--query-file", help="从文件读 SPARQL 语句（推荐——含双引号的 label service 用命令行传必被剥引号）")
    p.add_argument("--raw", action="store_true", help="紧凑单行 JSON")
    a = p.parse_args()

    # --query-file 优先：从文件读 SPARQL，绕过 shell/argparse 剥引号问题
    if a.query_file:
        if not os.path.isfile(a.query_file):
            print(json.dumps({"error": f"--query-file 不存在: {a.query_file}"}, ensure_ascii=False))
            return 2
        with open(a.query_file, encoding="utf-8-sig") as f:  # utf-8-sig 吃掉 BOM
            a.query = f.read().strip()

    if a.action == "sparql" and not (a.query or a.target):
        print(json.dumps({"error": "sparql 需要 --query-file（推荐）或 --query 或 target 提供 SPARQL 语句"}, ensure_ascii=False))
        return 2
    if a.action != "sparql" and not a.target:
        print(json.dumps({"error": f"{a.action} 需要 target 参数"}, ensure_ascii=False))
        return 2

    try:
        res = ACTIONS[a.action](a)
        res["fetched_at"] = time.strftime("%Y-%m-%d %H:%M")
        print(json.dumps(res, ensure_ascii=False, indent=None if a.raw else 1))
        return 0
    except RateLimited as e:
        print(json.dumps({"error": "RATE_LIMITED", "hint": f"已重试 {MAX_RETRY} 次仍被限流（SPARQL 尤其严格）；调大 WD_MIN_INTERVAL 或稍后再试", "detail": str(e)}, ensure_ascii=False))
        return 3
    except WdError as e:
        print(json.dumps({"error": "WD_ERROR", "detail": str(e)}, ensure_ascii=False))
        return 4
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"error": type(e).__name__, "detail": str(e)[:200]}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
