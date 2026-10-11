#!/usr/bin/env python3
"""
IG 營運工具 — 發文 + 數據。只用標準函式庫，不裝任何東西。

需要的環境變數（存在 environment 的 Network secrets，不要貼在對話裡）：
    IG_ACCESS_TOKEN   長效 token
    IG_USER_ID        Instagram 專業帳號的 ID（純數字）

用法：
    python3 ig.py limit                         查今天還能發幾篇
    python3 ig.py publish --urls urls.txt --caption cap.txt [--dry-run]
    python3 ig.py insights [--days 30]          抓近期貼文的七個數字
    python3 ig.py comments --media <id>         抓單篇留言
"""
import os, sys, json, time, argparse, urllib.parse, urllib.request, urllib.error

# 兩條路線，host 不一樣：
#   Instagram Login（推薦，不用 FB 粉絲頁）→ graph.instagram.com
#   Facebook Login（要粉絲頁，但能用 hashtag 搜尋、廣告）→ graph.facebook.com
GRAPH = os.environ.get("IG_API_BASE", "https://graph.instagram.com/v23.0")
MAX_CAROUSEL = 10          # IG 輪播 API 硬上限，App 手動可以更多，API 不行
CONTAINER_TTL_HOURS = 24   # 容器 24 小時不發就過期，所以不能提前排程


# 認證有兩種模式：
#   header（預設）— token 存在環境的 Network secrets，由代理在送出時注入
#                   Authorization 標頭。程式看不到 token，也不該看到。
#   query         — 本機測試用，token 放在環境變數 IG_ACCESS_TOKEN。
IG_USER = os.environ.get("IG_USER_ID", "me")


def _token():
    return os.environ.get("IG_ACCESS_TOKEN")


def call(path, params=None, method="GET"):
    params = dict(params or {})
    tok = _token()
    if tok:
        params["access_token"] = tok
    url = f"{GRAPH}/{path.lstrip('/')}"
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
        body = e.read().decode("utf-8", "replace")
        raise SystemExit(f"Graph API {e.code}：{body}")


# ---------- token ----------

def whoami():
    """確認 token 活著，順便把 IG_USER_ID 撈出來。"""
    return call("me", {"fields": "user_id,id,username,account_type"})


def refresh_token():
    """長效 token 60 天到期。至少每 50 天跑一次，要在到期前、且發行超過 24 小時才換得到。"""
    d = call("refresh_access_token", {"grant_type": "ig_refresh_token"})
    days = round(d.get("expires_in", 0) / 86400, 1)
    print(f"新 token（{days} 天後到期）：")
    print(d["access_token"])
    print("\n→ 把它貼回 environment 設定的 Network secrets，覆蓋 IG_ACCESS_TOKEN。")
    return d


# ---------- 發文 ----------

def publishing_limit():
    ig = IG_USER
    d = call(f"{ig}/content_publishing_limit", {"fields": "quota_usage,config"})
    return d.get("data", [{}])[0]


def wait_ready(container_id, timeout=300):
    """容器要等 Meta 下載完圖片才會變 FINISHED，不等就發會失敗。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        d = call(container_id, {"fields": "status_code,status"})
        code = d.get("status_code")
        if code == "FINISHED":
            return
        if code in ("ERROR", "EXPIRED"):
            raise SystemExit(f"容器 {container_id} 失敗：{d}")
        time.sleep(5)
    raise SystemExit(f"容器 {container_id} 超過 {timeout} 秒還沒好")


def publish(image_urls, caption, dry_run=False):
    if not 2 <= len(image_urls) <= MAX_CAROUSEL:
        sys.exit(f"輪播要 2–{MAX_CAROUSEL} 張，你給了 {len(image_urls)} 張。")

    lim = publishing_limit()
    used = lim.get("quota_usage")
    cap = (lim.get("config") or {}).get("quota_total")
    print(f"今日已用 {used} / {cap}")
    if used is not None and cap is not None and used >= cap:
        sys.exit("已達今日發文上限，明天再發。")

    if dry_run:
        print(f"[dry-run] 會發 {len(image_urls)} 張：")
        for u in image_urls:
            print("   ", u)
        print("[dry-run] 文案前 80 字：", caption[:80].replace("\n", " ⏎ "))
        return None

    ig = IG_USER

    children = []
    for i, u in enumerate(image_urls, 1):
        c = call(ig + "/media", {"image_url": u, "is_carousel_item": "true"}, "POST")
        print(f"  建立第 {i} 張容器 {c['id']}")
        children.append(c["id"])

    for c in children:
        wait_ready(c)

    parent = call(ig + "/media", {
        "media_type": "CAROUSEL",
        "children": ",".join(children),
        "caption": caption,
    }, "POST")
    wait_ready(parent["id"])

    out = call(ig + "/media_publish", {"creation_id": parent["id"]}, "POST")
    print("已發佈，media id =", out["id"])
    return out["id"]


# ---------- 數據 ----------

# 這幾個是 IG 官方的 media insight metric 名稱。欄位會隨 API 版本變動，
# 抓不到的指標直接略過，不要用估的填。
MEDIA_METRICS = ["reach", "saved", "shares", "comments", "total_interactions", "follows", "profile_visits"]


def insights(days=30):
    ig = IG_USER
    since = int(time.time()) - days * 86400
    media = call(f"{ig}/media", {
        "fields": "id,caption,media_type,media_product_type,permalink,timestamp,like_count,comments_count",
        "limit": 50,
    }).get("data", [])

    rows = []
    for m in media:
        ts = m.get("timestamp", "")
        if ts and time.mktime(time.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S")) < since:
            continue
        row = {
            "id": m["id"],
            "date": ts[:10],
            "type": m.get("media_type"),
            "permalink": m.get("permalink"),
            "caption_head": (m.get("caption") or "").split("\n")[0][:30],
            "comments": m.get("comments_count"),
        }
        try:
            ins = call(f"{m['id']}/insights", {"metric": ",".join(MEDIA_METRICS)})
            for d in ins.get("data", []):
                vals = d.get("values") or []
                row[d["name"]] = vals[0].get("value") if vals else d.get("total_value", {}).get("value")
        except SystemExit as e:
            row["insight_error"] = str(e)[:120]
        rows.append(row)

    print(json.dumps(rows, ensure_ascii=False, indent=2))
    return rows


def comments(media_id):
    d = call(f"{media_id}/comments", {"fields": "id,text,username,timestamp,like_count", "limit": 100})
    print(json.dumps(d.get("data", []), ensure_ascii=False, indent=2))
    return d.get("data", [])


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("limit")
    sub.add_parser("whoami")
    sub.add_parser("refresh")
    p = sub.add_parser("publish")
    p.add_argument("--urls", required=True, help="一行一個公開圖片網址的檔案")
    p.add_argument("--caption", required=True, help="文案檔")
    p.add_argument("--dry-run", action="store_true")
    i = sub.add_parser("insights"); i.add_argument("--days", type=int, default=30)
    c = sub.add_parser("comments"); c.add_argument("--media", required=True)
    a = ap.parse_args()

    if a.cmd == "whoami":
        print(json.dumps(whoami(), ensure_ascii=False, indent=2))
    elif a.cmd == "refresh":
        refresh_token()
    elif a.cmd == "limit":
        print(json.dumps(publishing_limit(), ensure_ascii=False, indent=2))
    elif a.cmd == "publish":
        urls = [l.strip() for l in open(a.urls, encoding="utf-8") if l.strip()]
        cap = open(a.caption, encoding="utf-8").read().strip()
        publish(urls, cap, a.dry_run)
    elif a.cmd == "insights":
        insights(a.days)
    elif a.cmd == "comments":
        comments(a.media)


if __name__ == "__main__":
    main()
