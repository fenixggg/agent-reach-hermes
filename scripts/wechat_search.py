#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信公众号文章搜索与直链解析工具
基于搜狗微信搜索 (weixin.sogou.com) 与微信直链解密算法
"""

import sys
import os
import re
import json
import argparse
import urllib.request
import urllib.parse
from datetime import datetime

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'

def get_session_opener():
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
    return opener

def search_wechat(query, limit=5, resolve_links=True):
    opener = get_session_opener()
    headers = {
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9'
    }

    # 1. 访问首页初始化 Session 与 Cookie
    try:
        req_home = urllib.request.Request('https://weixin.sogou.com/', headers=headers)
        opener.open(req_home, timeout=10)
    except Exception as e:
        pass

    # 2. 发起搜索
    encoded_query = urllib.parse.quote(query)
    search_url = f'https://weixin.sogou.com/weixin?type=2&query={encoded_query}'
    req_search = urllib.request.Request(search_url, headers=headers)
    
    try:
        resp = opener.open(req_search, timeout=15)
        html = resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        return {"status": "error", "error": f"搜索请求失败: {str(e)}", "results": []}

    if 'antispider' in resp.url or '验证码' in html:
        return {
            "status": "antispider",
            "error": "触发搜狗微信频率安全验证(验证码)，请稍后再试或配置 Cookie",
            "results": []
        }

    # 3. 解析文章卡片
    items = re.findall(r'<div class="txt-box">(.*?)</div>\s*</li>', html, re.DOTALL)
    results = []

    for item in items[:limit]:
        title_m = re.search(r'<h3>.*?<a[^>]*>(.*?)</a>', item, re.DOTALL)
        link_m = re.search(r'<h3>.*?<a[^>]+href="([^"]+)"', item, re.DOTALL)
        author_m = re.search(r'<a[^>]+class="account"[^>]*>(.*?)</a>', item, re.DOTALL)
        summary_m = re.search(r'<p class="txt-info"[^>]*>(.*?)</p>', item, re.DOTALL)
        date_m = re.search(r's-p">.*?document\.write\(timeConvert\(\'(\d+)\'\)\)', item, re.DOTALL)

        title = re.sub(r'<[^>]+>', '', title_m.group(1)).strip() if title_m else "无标题"
        sogou_link = link_m.group(1).replace('&amp;', '&').strip() if link_m else ""
        if sogou_link and not sogou_link.startswith('http'):
            sogou_link = 'https://weixin.sogou.com' + sogou_link
        # 修复 Python 3.14 对 URL 空格/非法字符的严格校验
        if sogou_link:
            sogou_link = sogou_link.replace(' ', '%20')

        author = re.sub(r'<[^>]+>', '', author_m.group(1)).strip() if author_m else "微信公众号"
        summary = re.sub(r'<[^>]+>', '', summary_m.group(1)).strip() if summary_m else ""
        
        publish_time = ""
        if date_m:
            try:
                publish_time = datetime.fromtimestamp(int(date_m.group(1))).strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                pass

        real_url = ""
        if resolve_links and sogou_link:
            real_url = resolve_real_url(opener, sogou_link, search_url)

        results.append({
            "title": title,
            "author": author,
            "publish_time": publish_time,
            "summary": summary,
            "sogou_link": sogou_link,
            "url": real_url or sogou_link
        })

    return {
        "status": "ok",
        "query": query,
        "count": len(results),
        "results": results
    }

def resolve_real_url(opener, sogou_link, referer):
    headers = {
        'User-Agent': USER_AGENT,
        'Referer': referer,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }
    try:
        req = urllib.request.Request(sogou_link, headers=headers)
        resp = opener.open(req, timeout=10)
        content = resp.read().decode('utf-8', errors='ignore')
        js_parts = re.findall(r"url \+= '([^']+)';", content)
        if js_parts:
            real_wx_url = "".join(js_parts).replace("@", "")
            return real_wx_url
        if 'mp.weixin.qq.com' in resp.url:
            return resp.url
    except Exception:
        pass
    return ""

def main():
    parser = argparse.ArgumentParser(description="微信公众号搜索与文章链接提取")
    parser.add_argument("query", help="搜索关键词")
    parser.add_argument("--limit", "-n", type=int, default=5, help="返回结果数量 (默认 5)")
    parser.add_argument("--format", choices=["json", "md"], default="md", help="输出格式 (md 或 json)")
    args = parser.parse_args()

    data = search_wechat(args.query, limit=args.limit)

    if args.format == "json":
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return

    if data["status"] != "ok":
        print(f"搜索失败: {data.get('error', '未知错误')}")
        return

    print(f"# 微信公众号搜索结果: {data['query']} (共 {data['count']} 条)\n")
    for idx, item in enumerate(data["results"], 1):
        print(f"### {idx}. {item['title']}")
        pub = f" | 发布时间: {item['publish_time']}" if item['publish_time'] else ""
        print(f"- **来源公众号**: {item['author']}{pub}")
        print(f"- **文章直链**: {item['url']}")
        print(f"- **内容摘要**: {item['summary']}\n")

if __name__ == "__main__":
    main()
