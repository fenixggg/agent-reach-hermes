#!/usr/bin/env python3
"""twitter-cli 安全代理包装器 (Agent 侧 / Hermes 侧通用)

背景：Agent 桌面端在启动 agent 时向子进程注入一个**每会话变化**的
进程级代理 (HTTP_PROXY=127.0.0.1:<随机端口>)，该出口到不了 x.com，
表现为 `Connection timed out` / `SSL_connect: Connection closed abruptly`。
本机真实的 VPN 代理只写在 **用户级环境变量** HKCU\\Environment 里。

本包装器做三件事：
  1. 从注册表读用户级 HTTP(S)_PROXY（不硬编码端口），强制覆盖注入代理
  2. 从 ~/.hermes/.env 与 Hermes profile .env 读取 Twitter 凭证
  3. 透传参数调用 twitter.exe，并原样返回退出码

用法（等价于直接调 twitter）：
    python tw_run.py search "OpenAI" -n 10 --json
    python tw_run.py user-posts @sama -n 20 --yaml
    python tw_run.py feed -n 20

兜底：可用 --_proxy http://127.0.0.1:10809 手动指定；或 env TW_PROXY=... 覆盖。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

DEFAULT_PROXY = "http://127.0.0.1:10809"
ENV_FILES = [
    os.path.expanduser("~/.hermes/.env"),
    r"~/.hermes/.env",
]


def user_proxy() -> str:
    """读用户级代理；读不到则退回默认端口。"""
    if os.environ.get("TW_PROXY"):
        return os.environ["TW_PROXY"]
    try:
        import winreg  # noqa: PLC0415
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            vals = {}
            i = 0
            while True:
                try:
                    n, v, _ = winreg.EnumValue(k, i)
                    i += 1
                    vals[n.upper()] = v
                except OSError:
                    break
        for key in ("HTTPS_PROXY", "HTTP_PROXY"):
            if vals.get(key):
                return vals[key]
    except Exception:
        pass
    return DEFAULT_PROXY


def load_creds() -> dict:
    creds = {}
    for path in ENV_FILES:
        if not os.path.exists(path):
            continue
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    line = line.strip()
                    if line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k = k.strip()
                    if k.startswith("TWITTER_"):
                        creds.setdefault(k, v.strip())
        except Exception:
            continue
    return creds


def find_twitter() -> str:
    exe = shutil.which("twitter")
    if exe:
        return exe
    for cand in (
        os.path.expanduser("~/.local/bin/twitter.exe"),
        os.path.expanduser("~/.local/bin/twitter"),
    ):
        if os.path.exists(cand):
            return cand
    sys.exit("tw_run.py: 找不到 twitter 可执行文件（pipx install twitter-cli）")


def main() -> int:
    args = sys.argv[1:]
    proxy_override = None
    if args[:1] == ["--_proxy"]:
        proxy_override, args = args[1], args[2:]

    env = dict(os.environ)
    proxy = proxy_override or user_proxy()
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        env[k] = proxy
    env["NO_PROXY"] = "localhost,127.0.0.1"
    env["no_proxy"] = "localhost,127.0.0.1"
    env.update(load_creds())

    if not env.get("TWITTER_AUTH_TOKEN") or not env.get("TWITTER_CT0"):
        print("tw_run.py: 警告 — 未读到 TWITTER_AUTH_TOKEN / TWITTER_CT0", file=sys.stderr)

    proc = subprocess.run([find_twitter()] + args, env=env)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
