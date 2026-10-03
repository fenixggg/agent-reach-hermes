#!/usr/bin/env python3
"""幂等重打补丁：让 twitter-cli 的 SearchTimeline 走 POST。

问题：x.com 自 2026-09 起对 `GET /i/api/graphql/<id>/SearchTimeline` 返回
HTTP 404（空 body）。同一端点、同一 queryId、同一 header，换成 **POST** 即
HTTP 200 正常返回。上游 twitter-cli 0.8.5 / xclienttransaction 1.0.3 均未适配，
`pipx upgrade` 会覆盖本补丁，因此升级后重跑本脚本即可。

改动（3 处，全部向后兼容，use_post 默认 False）：
  1. `_fetch_timeline()` 签名增加 `use_post=False`
  2. `_fetch_timeline()` 内按 `use_post` 选择 `_graphql_post` / `_graphql_get`
  3. `fetch_search()` 传 `use_post=True`

用法：
    python patch_twitter_search_post.py          # 打补丁（幂等）
    python patch_twitter_search_post.py --check  # 只检查状态
    python patch_twitter_search_post.py --revert # 从 .bak 还原
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys

SIG_OLD = (
    "    def _fetch_timeline(self, operation_name, count, get_instructions, "
    "extra_variables=None, override_base_variables=False, field_toggles=None):"
)
SIG_NEW = (
    "    def _fetch_timeline(self, operation_name, count, get_instructions, "
    "extra_variables=None, override_base_variables=False, field_toggles=None, use_post=False):"
)

CALL_OLD = (
    "            data = self._graphql_get(operation_name, variables, FEATURES, "
    "field_toggles=field_toggles)"
)
CALL_NEW = (
    "            if use_post:\n"
    "                data = self._graphql_post(operation_name, variables, FEATURES)\n"
    "            else:\n"
    "                data = self._graphql_get(operation_name, variables, FEATURES, "
    "field_toggles=field_toggles)"
)

SEARCH_OLD = """                "querySource": "typed_query",
                "product": product,
            },
            override_base_variables=True,
        )"""
SEARCH_NEW = """                "querySource": "typed_query",
                "product": product,
            },
            override_base_variables=True,
            use_post=True,
        )"""

MARKER = "use_post=True,"


def client_path() -> str:
    try:
        import twitter_cli  # noqa: PLC0415
        return os.path.join(os.path.dirname(twitter_cli.__file__), "client.py")
    except ImportError:
        sys.exit("找不到 twitter_cli 包。请用 twitter-cli 所在 venv 的 python 运行本脚本，"
                 "例如：~/pipx/venvs/twitter-cli/Scripts/python.exe")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只检查是否已打补丁")
    ap.add_argument("--revert", action="store_true", help="从 .bak 还原")
    a = ap.parse_args()

    path = client_path()
    bak = path + ".bak"
    print(f"client.py = {path}")

    if a.check:
        src = open(path, encoding="utf-8").read()
        print("已打补丁" if MARKER in src else "未打补丁")
        return 0

    if a.revert:
        if not os.path.exists(bak):
            sys.exit(f"没有备份文件 {bak}，无法还原")
        shutil.copy2(bak, path)
        print(f"已从 {bak} 还原")
        return 0

    src = open(path, encoding="utf-8").read()
    if MARKER in src:
        print("补丁已存在，跳过（幂等）")
        return 0

    for label, old in (("签名", SIG_OLD), ("调用点", CALL_OLD), ("fetch_search", SEARCH_OLD)):
        if old not in src:
            sys.exit(f"锚点不匹配（{label}）—— 上游代码可能已变更，请人工核对后再打补丁")

    if not os.path.exists(bak):
        shutil.copy2(path, bak)
        print(f"已备份 -> {bak}")

    src = src.replace(SIG_OLD, SIG_NEW, 1)
    src = src.replace(CALL_OLD, CALL_NEW, 1)
    src = src.replace(SEARCH_OLD, SEARCH_NEW, 1)
    open(path, "w", encoding="utf-8", newline="\n").write(src)
    print("补丁已应用：SearchTimeline 改用 POST")
    print("验证：python tw_run.py search \"OpenAI\" -n 3 --json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
