#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B站纯 API 扫码登录（零浏览器）— crawler-auth-credentials 4.2 节落地（P1⑤）

流程（教程 07 章 B站 API 版）：
  1. GET  passport.bilibili.com/x/passport-login/web/qrcode/generate → qrcode_key + 登录 URL
  2. 二维码双通道渲染：终端 ASCII（qrcode 库 print_ascii）+ PNG 落盘（pypng，可发聊天卡片）
  3. 每 2s 轮询 GET .../web/qrcode/poll?qrcode_key=xxx
     状态码：86101=未扫描  86090=已扫描待手机确认  0=成功  86038=二维码过期
  4. 成功时从 Set-Cookie 取 SESSDATA / bili_jct / DedeUserID
  5. 备份旧凭证 → 按 bilibili-cli 格式覆写 credential.json → nav API 终验（isLogin + uname）

用法：
  python bili_qr_login.py                       # 全流程：出码+轮询+写凭证+验证
  python bili_qr_login.py --png-out PATH.png    # PNG 落盘位置（默认 scratchpad）
  python bili_qr_login.py --no-write            # 只验证不落盘（dry-run）

退出码：0=成功且已写入；3=二维码过期未扫；4=用户中止；2=其他错误
依赖：curl_cffi, qrcode(+pypng 用于 PNG)。B站是国内站，默认清空代理直连。
"""
import argparse
import json
import os
import shutil
import sys
import time
from urllib.parse import parse_qsl

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

try:
    from curl_cffi import requests as creq
except ImportError:
    print(json.dumps({"error": "curl_cffi not installed"}))
    sys.exit(2)

PROFILE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
ENV_PATH = os.path.join(PROFILE, ".env")

GEN_URL = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"
POLL_URL = "https://passport.bilibili.com/x/passport-login/web/qrcode/poll"
NAV_URL = "https://api.bilibili.com/x/web-interface/nav"
QR_LIFETIME = 175  # 二维码有效期 ~180s，留 5s 余量


def clear_proxy():
    for v in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
        os.environ.pop(v, None)


def read_env_credential_path():
    with open(ENV_PATH, encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line.startswith("BILIBILI_CREDENTIAL_PATH="):
                p = line.split("=", 1)[1].strip().strip('"')
                return os.path.expandvars(p).replace("%USERPROFILE%", os.environ.get("USERPROFILE", ""))
    return None


def make_qr(url, png_path):
    """ASCII + PNG 双渲染。PNG 走 qrcode 的 pypng 工厂（免 PIL）。"""
    import qrcode
    from qrcode.image.pure import PyPNGImage

    qr = qrcode.QRCode(border=2, error_correction=qrcode.constants.ERROR_CORRECT_L)
    qr.add_data(url)
    qr.make(fit=True)
    print("\n===== 请用 B站 App 扫码（右上角 + → 扫一扫）=====")
    qr.print_ascii(invert=True)
    img = qr.make_image(image_factory=PyPNGImage)
    os.makedirs(os.path.dirname(os.path.abspath(png_path)), exist_ok=True)
    img.save(png_path)
    print(f"===== PNG 二维码已保存: {png_path} =====\n", flush=True)


def main():
    ap = argparse.ArgumentParser(description="B站纯 API 扫码登录")
    ap.add_argument("--png-out", default=os.path.join(os.path.dirname(PROFILE), "scratchpad", "bili_qr.png"))
    ap.add_argument("--no-write", action="store_true", help="只验证不写入凭证文件")
    ap.add_argument("--poll-seconds", type=int, default=QR_LIFETIME)
    args = ap.parse_args()

    clear_proxy()  # 国内站直连，避免走 VPN 出口
    s = creq.Session(impersonate="chrome124")

    # 1. 生成
    r = s.get(GEN_URL, timeout=10)
    j = r.json()
    if j.get("code") != 0:
        print(json.dumps({"error": f"generate 失败: {j}"}))
        sys.exit(2)
    qrcode_key = j["data"]["qrcode_key"]
    qr_url = j["data"]["url"]
    make_qr(qr_url, args.png_out)

    # 2. 轮询
    deadline = time.time() + args.poll_seconds
    last_state = None
    while time.time() < deadline:
        pr = s.get(POLL_URL, params={"qrcode_key": qrcode_key}, timeout=10)
        pj = pr.json()
        code = pj.get("data", {}).get("code", pj.get("code"))
        if code == 86101:
            if last_state != 86101:
                print("[等待扫码] ……（每 2s 轮询）", flush=True)
                last_state = 86101
        elif code == 86090:
            if last_state != 86090:
                print("[已扫描] 请在手机上确认登录 ✔", flush=True)
                last_state = 86090
        elif code == 0:
            print("[登录成功] 从 Set-Cookie 提取凭证", flush=True)
            break
        elif code == 86038:
            print("[二维码已过期] 重新运行本脚本获取新码", flush=True)
            sys.exit(3)
        else:
            print(f"[未知状态] code={code} raw={pj.get('message','')}", flush=True)
        time.sleep(2)
    else:
        print("[超时] 未在有效期内完成扫码", flush=True)
        sys.exit(3)

    # 3. 提取凭证（轮询响应的 Set-Cookie）
    cookies = {c.name: c.value for c in pr.cookies.jar if c.value}
    sessdata = cookies.get("SESSDATA", "")
    bili_jct = cookies.get("bili_jct", "")
    dedeuid = cookies.get("DedeUserID", cookies.get("bili_dedeuserid", ""))
    if not sessdata:
        print(json.dumps({"error": "响应未含 SESSDATA", "cookie_names": list(cookies)}))
        sys.exit(2)

    # 4. 终验（带新 cookie 调 nav）
    vr = s.get(NAV_URL, timeout=10)
    vj = vr.json()
    logged_in = vj.get("code") == 0 and (vj.get("data") or {}).get("isLogin")
    uname = (vj.get("data") or {}).get("uname", "?") if isinstance(vj.get("data"), dict) else "?"
    print(f"[nav 终验] isLogin={logged_in} uname={uname}", flush=True)
    if not logged_in:
        print(json.dumps({"error": "新 cookie 终验未通过", "nav_message": vj.get("message")}))
        sys.exit(2)

    # 5. 写凭证（备份旧的）
    cred_path = read_env_credential_path()
    result = {"status": "ok", "uname": uname, "wrote": False, "cred_path": cred_path}
    if args.no_write:
        print(json.dumps(result, ensure_ascii=False))
        return
    if cred_path and os.path.isfile(cred_path):
        bak = f"{cred_path}.bak-{time.strftime('%Y%m%d-%H%M%S')}"
        shutil.copy2(cred_path, bak)
        result["backup"] = bak
        print(f"[备份] 旧凭证 → {bak}", flush=True)
    if cred_path:
        cred = {
            "sessdata": sessdata,
            "bili_jct": bili_jct,
            "ac_time_value": cookies.get("ac_time_value", ""),
            "buvid3": cookies.get("buvid3", ""),
            "buvid4": cookies.get("buvid4", ""),
            "dedeuserid": dedeuid,
            "saved_at": time.time(),
        }
        os.makedirs(os.path.dirname(cred_path), exist_ok=True)
        with open(cred_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(cred, f, ensure_ascii=False, indent=3)
        result["wrote"] = True
        print(f"[已写入] {cred_path}", flush=True)
    else:
        result["note"] = ".env 未找到 BILIBILI_CREDENTIAL_PATH，凭证未落盘"

    # 清理二维码临时文件
    try:
        os.remove(args.png_out)
        result["qr_png_cleaned"] = True
    except OSError:
        pass
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
