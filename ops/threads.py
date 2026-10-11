#!/usr/bin/env python3
"""
Threads 發文 — 短句用。只用標準函式庫。

環境變數（存 Network secrets）：
    THREADS_ACCESS_TOKEN
    THREADS_USER_ID

用法：
    python3 threads.py post --text "今天那句話卡在喉嚨三秒才吞下去。"
    python3 threads.py queue --file ../brand/THREADS.md --tag 感 --n 1
"""
import os, re, sys, json, time, random, argparse, urllib.parse, urllib.request, urllib.error

BASE = os.environ.get("THREADS_API_BASE", "https://graph.threads.net/v1.0")
SENT_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".threads_sent.json")


def _env(n):
    v = os.environ.get(n)
    if not v:
        sys.exit(f"缺少環境變數 {n}。請加在 environment 的 Network secrets，不要貼在對話裡。")
    return v


def call(path, params=None, method="GET"):
    params = dict(params or {})
    params["access_token"] = _env("THREADS_ACCESS_TOKEN")
    url = f"{BASE}/{path.lstrip('/')}"
    data = None
    if method == "POST":
        data = urllib.parse.urlencode(params).encode()
    else:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Threads API {e.code}：{e.read().decode('utf-8','replace')}")


def post(text, dry_run=False):
    text = text.strip()
    if not text:
        sys.exit("沒有內容")
    if len(text) > 500:
        sys.exit(f"Threads 單則上限 500 字，你這則 {len(text)} 字")
    if dry_run:
        print("[dry-run]", text)
        return None
    uid = _env("THREADS_USER_ID")
    c = call(f"{uid}/threads", {"media_type": "TEXT", "text": text}, "POST")
    time.sleep(30)  # 官方建議建立容器後等 30 秒再發
    out = call(f"{uid}/threads_publish", {"creation_id": c["id"]}, "POST")
    print("已發佈 thread id =", out["id"])
    return out["id"]


def _load_sent():
    try:
        with open(SENT_LOG, encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()


def _save_sent(s):
    with open(SENT_LOG, "w", encoding="utf-8") as f:
        json.dump(sorted(s), f, ensure_ascii=False, indent=1)


def queue(path, tag=None, n=1, dry_run=False):
    """從 THREADS.md 挑還沒發過的句子。

    格式：`### 〔感〕標題` 起一個區段，底下用 `1. ` 開頭的編號塊，
    一塊可以跨多行，空行結束。
    """
    items, cur_tag, buf = [], None, []

    def flush():
        if buf and cur_tag:
            body = "\n".join(buf).strip()
            if body:
                items.append((cur_tag, body))
        buf.clear()

    for raw in open(path, encoding="utf-8"):
        line = raw.rstrip()
        m = re.match(r"^#{1,6}\s*〔(.)〕", line)
        if m:
            flush(); cur_tag = m.group(1); continue
        if re.match(r"^\d+\.\s", line):
            flush(); buf.append(re.sub(r"^\d+\.\s*", "", line)); continue
        if not line.strip():
            flush(); continue
        if buf:
            buf.append(line.strip())
    flush()

    pool = [b for t, b in items if (tag is None or t == tag)]
    if not pool:
        sys.exit(f"THREADS.md 裡找不到標籤〔{tag}〕的句子。")

    sent = _load_sent()
    fresh = [b for b in pool if b not in sent]
    if not fresh:
        sys.exit("這個標籤的句子都發過了，該補新的了。")

    random.shuffle(fresh)
    for body in fresh[:n]:
        post(body, dry_run)
        if not dry_run:
            sent.add(body)
    if not dry_run:
        _save_sent(sent)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("post"); p.add_argument("--text", required=True); p.add_argument("--dry-run", action="store_true")
    q = sub.add_parser("queue")
    q.add_argument("--file", default="../brand/THREADS.md")
    q.add_argument("--tag"); q.add_argument("--n", type=int, default=1)
    q.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.cmd == "post":
        post(a.text, a.dry_run)
    else:
        queue(a.file, a.tag, a.n, a.dry_run)


if __name__ == "__main__":
    main()
