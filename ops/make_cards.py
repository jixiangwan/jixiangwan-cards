#!/usr/bin/env python3
"""
季向晚 圖卡產生器
用法： python3 make_cards.py 文稿.txt --series 想太多|英呎|身體 --out 資料夾
文稿：一行 --- 分格；**粗體** 標落點句
"""
import sys, os, re, html, subprocess, shutil, argparse

# 三個系列＝三個高度。地平線的位置就是你站的位置。
SERIES = {
    "關於": {   # 米白，最暖最亮
        "name": "",
        "top": (("#f2ebe0", "#e0d4c3"), ("#f2ebe0", "#e0d4c3")),
        "fg": "#3b332a", "sub": "#8d8273", "line": 0.65,
    },
    "想太多": {  # 暖灰藕，淺底深字
        "name": "不要想太多",
        "top": (("#e6dfe0", "#cfc4c7"), ("#e6dfe0", "#cfc4c7")),
        "fg": "#3a3338", "sub": "#8a7f85", "line": 0.50,
    },
    "英呎": {    # 霧藍，但提亮
        "name": "三萬英呎",
        "top": (("#e4ebef", "#c8d5dd"), ("#e4ebef", "#c8d5dd")),
        "fg": "#2c3741", "sub": "#7b8a95", "line": 0.80,
    },
    "身體": {    # 陶土提亮
        "name": "身體記得",
        "top": (("#efe3d2", "#dbc8ae"), ("#efe3d2", "#dbc8ae")),
        "fg": "#3a2f23", "sub": "#8a7a64", "line": 0.22,
    },
}

HTML = """<!doctype html><html><head><meta charset="utf-8"><style>
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:1080px;height:1350px}}
body{{background:linear-gradient(168deg,{c1} 0%,{c2} 100%);
  font-family:"Noto Serif CJK TC","Noto Serif TC",serif;color:{fg};
  display:flex;flex-direction:column;justify-content:{vj};
  padding:150px 106px 170px;position:relative;overflow:hidden}}
.horizon{{position:absolute;left:0;right:0;top:{ly}px;height:1px;
  background:{fg};opacity:.18}}
p{{font-size:40px;line-height:1.88;letter-spacing:.04em;margin-bottom:64px;
  position:relative;z-index:1}}
p:last-child{{margin-bottom:0;margin-top:24px}}
p:first-child{{margin-top:0}}
strong{{font-weight:700;letter-spacing:.055em}}
.cover p{{font-size:40px}}
.cover p:first-of-type{{font-size:54px;line-height:1.8;margin-bottom:76px}}
.cover{{justify-content:center;padding:200px 106px 200px}}
.title{{margin-top:84px;font-size:27px;color:{sub};letter-spacing:.3em}}
.tag{{position:absolute;top:104px;left:106px;font-size:25px;
  color:{sub};letter-spacing:.42em}}
.meta{{position:absolute;bottom:74px;left:106px;right:106px;
  display:flex;justify-content:space-between;align-items:center;
  font-size:23px;color:{sub};letter-spacing:.3em}}
.bar{{position:absolute;bottom:0;left:0;height:3px;width:{pct}%;
  background:{fg};opacity:.22}}
</style></head><body class="{cls}">
{tag}
<div class="horizon"></div>
{body}
<div class="meta"><span>季向晚</span><span>{n:02d} / {tot:02d}</span></div>
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

def para(block):
    """空行分段；段落內部的換行用 <br> 接起來，不另外加段距"""
    lines = [html.escape(l.strip()) for l in block.strip().split("\n") if l.strip()]
    s = "<br>".join(lines)
    return "<p>" + re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s) + "</p>"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("--series", default="想太多", choices=list(SERIES))
    ap.add_argument("--out", default="out")
    ap.add_argument("--title", default="")
    a = ap.parse_args()

    S = SERIES[a.series]
    (s1, s2), (e1, e2) = S["top"]
    raw = open(a.src, encoding="utf-8").read()
    title = a.title
    m = re.match(r'(?m)^#\s*title:\s*(.+?)\s*$\n+', raw)
    if m:
        title = title or m.group(1)
        raw = raw[m.end():]
    slides = [s.strip() for s in re.split(r'(?m)^---+\s*$', raw) if s.strip()]
    total = len(slides)
    os.makedirs(a.out, exist_ok=True)
    cb = chromium()

    for i, sl in enumerate(slides, 1):
        t = 0                               # 同系列同顏色：整組不變色
        page = HTML.format(
            c1=mix(s1, e1, t), c2=mix(s2, e2, t),
            fg=S["fg"], sub=S["sub"], ly=round(1350*S["line"]),
            body="\n".join(para(blk) for blk in re.split(r"\n\s*\n", sl) if blk.strip())
                 + (('<div class="title">' + title + '</div>') if (i == 1 and title) else ""),
            series=S["name"], n=i, tot=total, pct=round(i/total*100, 2),
            vj="center",
            cls="cover" if i == 1 else "",
            tag=('<div class="tag">' + S["name"] + '</div>') if (i == 1 and S["name"]) else "")
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
