"""
Video-to-Raw-Text Tool — 视频音频转文字
=======================================
Downloads audio & transcribes with Groq Whisper (free). Outputs raw text.
Hermes Agent then formats it into structured Markdown.

Supported platforms:
  - B站/Bilibili  (BV号或完整URL)
  - YouTube       (youtube.com / youtu.be)
  - 小红书          (xiaohongshu.com/explore/NOTE_ID) — 直接提取内嵌字幕，无需Whisper
  - 通用兜底       (其他平台 → 尝试 yt-dlp)

Usage:
  python transcribe.py <视频URL或BV号或小红书笔记ID> [输出目录]

Two-phase workflow:
  Phase 1 (this script):  下载音频 → Groq Whisper → raw.txt + meta.json
                          小红书: 直接从 xhs read 提取字幕，跳过 Whisper
  Phase 2 (Hermes):       raw.txt → 润色加标点 → 结构化 .md

Credentials:
  GROQ_API_KEY in Hermes .env  (已配置)
  小红书 xhs CLI 需已登录（xhs login）
"""

import sys, os, json, re, time, urllib.request, tempfile, shutil

# ─── Config ────────────────────────────────────────────────
GROQ_BASE = "https://api.groq.com/openai/v1"
WHISPER_MODEL = "whisper-large-v3"

# ─── Read Groq key from env ────────────────────────────────
def get_groq_key():
    """从 Hermes .env 或环境变量读取 GROQ_API_KEY"""
    key = os.getenv("GROQ_API_KEY", "")
    if key:
        return key
    # 尝试从 Hermes .env 文件读取（按优先级尝试本机已知 home 位置）
    candidates = []
    hh = os.getenv("HERMES_HOME")
    if hh:
        candidates.append(os.path.join(hh, ".env"))
    # 本机 Desktop profile 真身，~/.hermes 仅作为通用兜底
    candidates.append(r"~/.hermes/.env")
    candidates.append(os.path.join(os.path.expanduser("~"), ".hermes", ".env"))
    for env_path in candidates:
        if os.path.isfile(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("GROQ_API_KEY="):
                        return line.split("=", 1)[1].strip()
    raise RuntimeError(
        "GROQ_API_KEY not found. "
        "Add to Hermes .env: GROQ_API_KEY=gsk_xxxxx"
    )

GROQ_KEY = get_groq_key()

# ─── Helpers ───────────────────────────────────────────────
def log(msg):
    print(f"  [{time.strftime('%H:%M:%S')}] {msg}")

# ─── Step 1a: B站音频下载 ─────────────────────────────────
def get_bilibili_audio(bvid):
    """Download B站 audio via official API. Returns (audio_path, title, duration_s)."""
    import requests as req_lib
    req = urllib.request.Request(
        f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}",
        headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.bilibili.com/"}
    )
    d = json.loads(urllib.request.urlopen(req).read())["data"]
    title = d["title"]
    cid = d["cid"]
    aid = d["aid"]
    duration = d["duration"]
    log(f"平台: B站 | {title} ({duration // 60}m{duration % 60}s)")

    req2 = urllib.request.Request(
        f"https://api.bilibili.com/x/player/playurl?avid={aid}&cid={cid}&qn=0&fnver=0&fnval=4048",
        headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.bilibili.com/"}
    )
    d2 = json.loads(urllib.request.urlopen(req2).read())["data"]
    audio_info = d2["dash"]["audio"][-1]  # highest quality
    audio_url = audio_info.get("backup_url", [audio_info["base_url"]])[0]

    tmp = tempfile.gettempdir()
    m4s_path = os.path.join(tmp, f"ar_{bvid}.m4s")
    m4a_path = os.path.join(tmp, f"ar_{bvid}.m4a")

    r = req_lib.get(audio_url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": f"https://www.bilibili.com/video/{bvid}",
    }, stream=True, timeout=120)
    with open(m4s_path, "wb") as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)
    shutil.copy2(m4s_path, m4a_path)
    os.remove(m4s_path)
    size_kb = os.path.getsize(m4a_path) // 1024
    log(f"音频下载: {size_kb} KB")
    return m4a_path, title, duration

# ─── Step 1b: YouTube / 通用平台音频下载 (yt-dlp) ────────
def get_ytdlp_audio(url):
    """Download audio via yt-dlp. Supports YouTube, Douyin, and many others.
    Returns (audio_path, title, duration_s)."""
    import subprocess
    tmp = tempfile.gettempdir()
    out_template = os.path.join(tmp, "ar_yt_%(id)s.%(ext)s")

    # Find yt-dlp in PATH
    yt_dlp = "yt-dlp"

    # Get JSON info
    result = subprocess.run(
        [yt_dlp, "--dump-json", url],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp failed: {result.stderr[:200]}")
    info = json.loads(result.stdout)
    title = info["title"]
    duration = info.get("duration", 0)
    extractor = info.get("extractor_key", "Unknown")
    log(f"平台: {extractor} | {title} ({duration // 60}m{duration % 60}s)")

    # Download audio as mp3
    result2 = subprocess.run(
        [yt_dlp, "-x", "--audio-format", "mp3", "-o", out_template, url],
        capture_output=True, timeout=300
    )
    if result2.returncode != 0:
        raise RuntimeError(f"yt-dlp audio download failed: {result2.stderr[:200]}")

    mp3_path = os.path.join(tmp, f"ar_yt_{info['id']}.mp3")
    if not os.path.exists(mp3_path):
        # yt-dlp might use a different ID format, try glob
        import glob
        matches = glob.glob(os.path.join(tmp, f"ar_yt_{info['id']}.*.mp3"))
        if matches:
            mp3_path = matches[0]
        else:
            raise RuntimeError("yt-dlp output file not found")

    size_kb = os.path.getsize(mp3_path) // 1024
    log(f"音频下载: {size_kb} KB")
    return mp3_path, title, duration

# ─── Step 2: Groq Whisper 转录 ────────────────────────────
def transcribe(audio_path):
    """Send audio to Groq Whisper API, return raw text."""
    import requests
    log("转录中: Groq Whisper ...")
    with open(audio_path, "rb") as f:
        files = {"file": (os.path.basename(audio_path), f, "audio/mp4")}
        data = {"model": WHISPER_MODEL, "language": "zh", "response_format": "json"}
        r = requests.post(f"{GROQ_BASE}/audio/transcriptions",
                          headers={"Authorization": f"Bearer {GROQ_KEY}"},
                          files=files, data=data, timeout=300)
    if r.status_code != 200:
        raise RuntimeError(f"Whisper API error {r.status_code}: {r.text[:200]}")
    text = r.json()["text"]
    log(f"转录完成: {len(text)} 字符")
    return text

# ─── URL 识别 ──────────────────────────────────────────────
def detect_source(url_or_bvid):
    """Return (type, key, xsec_token) where type is 'bilibili'/'xhs'/'ytdlp'.
    xsec_token is extracted from the URL for xiaohongshu."""
    s = url_or_bvid.strip()
    xsec = None

    # Extract xsec_token from any URL
    m_tok = re.search(r'xsec_token=([^&]+)', s)
    if m_tok:
        xsec = m_tok.group(1)

    # 小红书: https://www.xiaohongshu.com/explore/NOTE_ID
    if "xiaohongshu.com" in s:
        m = re.search(r'/(?:explore|discovery/item)/(\w+)', s)
        if m:
            return ("xhs", m.group(1), xsec)
        return ("xhs", s, xsec)
    # 也可能是裸 note_id（纯24位hex字符串）
    if re.match(r'^[a-f0-9]{24}$', s, re.I):
        return ("xhs", s, xsec)

    # B站
    if s.startswith("BV") and len(s) >= 12:
        return ("bilibili", s, None)
    if "bilibili.com" in s:
        m = re.search(r'BV\w+', s)
        if m:
            return ("bilibili", m.group(), None)
        return ("bilibili", s, None)
    if "youtube.com" in s or "youtu.be" in s:
        return ("ytdlp", s, None)
    # Fallback
    return ("ytdlp", s, None)


# ─── 小红书内容提取（字幕优先，无字幕走Whisper兜底） ─────
def get_xhs_content(note_id, xsec_token=None):
    """Extract text from a xiaohongshu note.
    Priority: 1) embedded SRT subtitles → 2) video audio + Whisper → 3) desc text.
    xsec_token is required for some notes (from URL xsec_token parameter).
    Returns (text_content, title, duration_s, source_label)."""
    import subprocess, json

    # 1. Run xhs read (with xsec_token if available)
    log(f"读取小红书笔记: {note_id}" + (" (带xsec_token)" if xsec_token else ""))
    cmd = ["xhs", "read", note_id]
    if xsec_token:
        cmd = ["xhs", "read", "--xsec-token", xsec_token, note_id]
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        raise RuntimeError(f"xhs read failed: {result.stderr[:200]}")
    data = json.loads(result.stdout)

    for item in data.get("data", {}).get("items", []):
        card = item.get("note_card", {})
        title = card.get("title", card.get("display_title", "未知标题")) or "未知标题"
        desc = card.get("desc", "") or ""

        # media_v2 is a JSON string nested inside
        media_raw = card.get("media_v2", "")
        if isinstance(media_raw, str):
            try:
                media = json.loads(media_raw)
            except json.JSONDecodeError:
                media = {}
        elif isinstance(media_raw, dict):
            media = media_raw
        else:
            # No media at all — photo-only note, use desc
            return (desc, title, 0, "desc")

        # Try 1: Subtitles (zh-CN or source)
        subs = media.get("subtitles", {})
        for lang in ["zh-CN", "source"]:
            sub_list = subs.get(lang, [])
            if sub_list and sub_list[0].get("url", ""):
                sub_url = sub_list[0]["url"]
                try:
                    req = urllib.request.Request(sub_url,
                        headers={"User-Agent": "Mozilla/5.0"})
                    resp = urllib.request.urlopen(req, timeout=15)
                    srt_text = resp.read().decode("utf-8", errors="replace")
                    log(f"✓ 字幕提取成功: {lang} | {len(srt_text)} 字符")
                    return (srt_text, title, desc, "subtitle")
                except Exception as e:
                    log(f"字幕下载失败: {e}")

        # Try 2: Video stream + Whisper (h264 or h265 with audio)
        streams = media.get("stream", {})
        for codec in ["h265", "h264"]:
            stream_list = streams.get(codec, [])
            for s in stream_list:
                if s.get("audio_codec") and s.get("master_url"):
                    master_url = s["master_url"]
                    log(f"发现带音频的视频流({codec}/{s['audio_codec']}), 下载中...")
                    try:
                        import subprocess as sp
                        tmp = tempfile.gettempdir()
                        out_mp3 = os.path.join(tmp, f"ar_xhs_{note_id}.mp3")
                        sp.run(
                            ["yt-dlp", "-x", "--audio-format", "mp3",
                             "-o", out_mp3, master_url],
                            capture_output=True, timeout=120
                        )
                        if not os.path.exists(out_mp3):
                            continue
                        raw_text = transcribe(out_mp3)
                        os.remove(out_mp3)
                        log(f"✓ Whisper转录完成: {len(raw_text)} 字符")
                        return (raw_text, title, desc, "whisper")
                    except Exception as e:
                        log(f"视频流转录失败 ({codec}): {e}")
                        continue
                    break

        # Try 3: Fallback to desc
        log("无字幕且无可用视频音频流, 回退到 desc 文字")
        return (desc, title, 0, "desc")

    raise RuntimeError(f"未找到笔记: {note_id}")

# ─── Main ──────────────────────────────────────────────────
def main():
    # 参数守卫（2026-10-02）：-h/--help 打印用法退出，不进下载逻辑
    if len(sys.argv) < 2 or sys.argv[1].strip() in ("-h", "--help"):
        print("Usage: python transcribe.py <视频URL 或 BV号 或 小红书笔记ID> [输出目录]")
        print()
        print("支持平台:")
        print("  B站:     BV1xxx 或 https://www.bilibili.com/video/BV1xxx")
        print("  YouTube: https://www.youtube.com/watch?v=xxx")
        print("  小红书:  https://www.xiaohongshu.com/explore/xxxx 或裸note_id")
        print("  其他:    自动尝试 yt-dlp 支持的平台")
        sys.exit(0)

    url_or_bvid = sys.argv[1].strip()
    output_dir = sys.argv[2] if len(sys.argv) > 2 else os.getcwd()
    os.makedirs(output_dir, exist_ok=True)

    # Phase 1: 下载音频 → Whisper 转录 / 小红书字幕提取
    source_type, source_key, xsec_token = detect_source(url_or_bvid)

    if source_type == "bilibili":
        source_url = f"https://www.bilibili.com/video/{source_key}"
        audio_path, title, duration = get_bilibili_audio(source_key)
        raw_text = transcribe(audio_path)
        os.remove(audio_path)
    elif source_type == "xhs":
        source_url = f"https://www.xiaohongshu.com/explore/{source_key}"
        content, title, desc, source_label = get_xhs_content(source_key, xsec_token)

        if source_label == "subtitle":
            # SRT → plain text (remove timestamps)
            raw_lines = []
            for line in content.split("\n"):
                line = line.strip()
                if re.match(r'^\d+$', line):
                    continue
                if "-->" in line:
                    continue
                if not line:
                    continue
                raw_lines.append(line)
            raw_text = "\n".join(raw_lines)
            duration = 0
            log(f"✓ 小红书字幕提取完成: {len(raw_text)} 字符")
        elif source_label == "whisper":
            raw_text = content
            duration = 0
            log(f"✓ 小红书Whisper转录完成: {len(raw_text)} 字符")
        else:
            raw_text = content
            duration = 0
            log(f"⚠ 小红书仅获取到 desc 文字: {len(raw_text)} 字符")
    elif source_type == "ytdlp":
        source_url = source_key
        audio_path, title, duration = get_ytdlp_audio(source_key)
        raw_text = transcribe(audio_path)
        os.remove(audio_path)
    else:
        print(f"无法识别的URL: {url_or_bvid}")
        sys.exit(1)

    # Build safe filename from title
    safe_title = re.sub(r'[\\/:*?"<>|]', '_', title)[:80]

    # Save raw output
    raw_path = os.path.join(output_dir, f"{safe_title}_raw.txt")
    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(raw_text)

    meta_path = os.path.join(output_dir, f"{safe_title}_meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump({
            "title": title,
            "duration_s": duration,
            "source_url": source_url,
            "platform": source_type,
            "raw_chars": len(raw_text)
        }, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*50}")
    print(f"✅ Phase 1 完成!")
    print(f"   原始文稿: {raw_path}")
    print(f"   元数据:   {meta_path}")
    print(f"{'='*50}")
    print()
    print(f"接下来请 Hermes Agent 执行 Phase 2:")
    print(f"  → 读取 raw.txt")
    print(f"  → 润色加标点+分段")
    print(f"  → 按 transcribe_format.md 规范输出 .md")
    print()
    print(f"--- RAW TEXT (for formatting) ---")
    print(raw_text)
    print("--- END RAW TEXT ---")

if __name__ == "__main__":
    main()