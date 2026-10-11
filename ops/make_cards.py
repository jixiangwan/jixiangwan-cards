#!/usr/bin/env python3
"""
季向晚 圖卡產生器
用法： python3 make_cards.py 文稿.txt --series 想太多|英呎|身體 --out 資料夾
文稿：一行 --- 分格；**粗體** 標落點句
"""
import sys, os, re, html, subprocess, shutil, argparse

# 三個系列＝三個高度。地平線的位置就是你站的位置。
SERIES = {
    "想太多": {  # 童年與家庭 — 暮色，地平線在中間（平視）
        "name": "不要想太多",
        "top": (("#6b6a78", "#3b3a4a"), ("#4a4954", "#232230")),  # 起→迄
        "fg": "#ece9f0", "sub": "#9c98aa", "line": 0.50,
    },
    "英呎": {    # 高空 — 稀薄的冷光，地平線壓很低（你在上面）
        "name": "三萬英呎",
        "top": (("#c9d4dd", "#9fb0c0"), ("#8c9cab", "#5d6b79")),
        "fg": "#1c2630", "sub": "#54606d", "line": 0.80,
    },
    "身體": {    # 土 — 溫暖的陶土，地平線拉很高（你在地上）
        "name": "身體記得",
        "top": (("#d8cbb8", "#b9a68d"), ("#a08d74", "#6d5d4a")),
        "fg": "#2a231a", "sub": "#6b5c49", "line": 0.22,
    },
}

HTML = """<!doctype html><html><head><meta charset="utf-8"><style>
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:1080px;height:1350px}}
body{{background:linear-gradient(168deg,{c1} 0%,{c2} 100%);
  font-family:"Noto Serif CJK TC","Noto Serif TC",serif;color:{fg};
  display:flex;flex-direction:column;justify-content:center;
  padding:150px 106px 170px;position:relative;overflow:hidden}}
.horizon{{position:absolute;left:0;right:0;top:{ly}px;height:1px;
  background:{fg};opacity:.13}}
p{{font-size:40px;line-height:1.88;letter-spacing:.04em;margin-bottom:40px;
  position:relative;z-index:1}}
p:last-child{{margin-bottom:0}}
strong{{font-weight:700;letter-spacing:.055em}}
.meta{{position:absolute;bottom:74px;left:106px;right:106px;
  display:flex;justify-content:space-between;align-items:center;
  font-size:23px;color:{sub};letter-spacing:.3em}}
.bar{{position:absolute;bottom:0;left:0;height:3px;width:{pct}%;
  background:{fg};opacity:.22}}
</style></head><body>
<div class="horizon"></div>
{body}
<div class="meta"><span>{series}</span><span>{n:02d}</span></div>
<div class="bar"></div>
</body></html>"""

def chromium():
    for root, _, fs in os.walk("/opt/pw-browsers"):
        for f in fs:
            if f in ("chrome", "headless_shell"):
                return os.path.join(root, f)
    for n in ("chromium", "chromium-browser", "google-chrome"):
        q = shutil.which(n)
        if q: return q
    raise SystemExit("找不到 chromium")

def mix(a, b, t):
    """兩個 hex 之間插值 — 讓整組圖卡隨著滑動逐漸入夜"""
    f = lambda h: tuple(int(h[i:i+2], 16) for i in (1, 3, 5))
    x, y = f(a), f(b)
    return "#%02x%02x%02x" % tuple(round(x[i] + (y[i]-x[i])*t) for i in range(3))

def para(line):
    s = html.escape(line.strip())
    return "<p>" + re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s) + "</p>"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("--series", default="想太多", choices=list(SERIES))
    ap.add_argument("--out", default="out")
    a = ap.parse_args()

    S = SERIES[a.series]
    (s1, s2), (e1, e2) = S["top"]
    slides = [s.strip() for s in re.split(r'(?m)^---+\s*$',
              open(a.src, encoding="utf-8").read()) if s.strip()]
    total = len(slides)
    os.makedirs(a.out, exist_ok=True)
    cb = chromium()

    for i, sl in enumerate(slides, 1):
        t = (i-1)/max(total-1, 1)          # 0 → 1，整組逐格入夜
        page = HTML.format(
            c1=mix(s1, e1, t), c2=mix(s2, e2, t),
            fg=S["fg"], sub=S["sub"], ly=round(1350*S["line"]),
            body="\n".join(para(l) for l in sl.split("\n") if l.strip()),
            series=S["name"], n=i, pct=round(i/total*100, 2))
        hp = os.path.join(a.out, f"_{i:02d}.html")
        open(hp, "w", encoding="utf-8").write(page)
        png = os.path.join(a.out, f"card_{i:02d}.png")
        subprocess.run([cb, "--headless", "--disable-gpu", "--no-sandbox",
                        "--hide-scrollbars", "--force-device-scale-factor=1",
                        f"--screenshot={png}", "--window-size=1080,1350",
                        "file://" + os.path.abspath(hp)],
                       check=True, capture_output=True)
        os.remove(hp)
        print(f"  ✓ card_{i:02d}.png")
    print(f"\n{S['name']}：{total} 張 → {a.out}/")

main()
