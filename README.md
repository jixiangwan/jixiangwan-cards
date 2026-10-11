# jixiangwan-cards

季向晚的圖卡與發文工具。

- `post01/` — 〈哭多了就會好〉10 張 JPEG，1080×1350
- `posts/` — 文稿、文案、圖片網址清單
- `ops/` — 發文與數據工具

這個 repo 是公開的，**只放本來就要公開的東西**。草稿、寫作協議、個人材料不在這裡。

## 用法

Token 不存在這裡。它存在執行環境的 Network secrets，由代理在送出請求時注入
Authorization 標頭，程式從頭到尾看不到它。

```
python3 ops/ig.py whoami                                      # 確認接通
python3 ops/ig.py limit                                       # 今日額度
python3 ops/ig.py publish --urls posts/post01_urls.txt \
                          --caption posts/post01_caption.txt --dry-run
python3 ops/ig.py insights --days 30                          # 發文後的數據
python3 ops/ig.py refresh                                     # 60 天到期前換 token

python3 ops/make_cards.py posts/post01.txt --series 想太多 --out post01
```

## 兩個硬限制

- 輪播 API 上限 **10 張**（App 手動可到 20，API 不行）
- 媒體容器 **24 小時**過期，不能提前排程，只能當天建當天發
