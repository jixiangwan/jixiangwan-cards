#!/usr/bin/env python3
"""稿件自動檢查：把 SKILL.md 裡能量化的規則跑一遍。
用法：python3 check.py 稿子.txt
"""
import sys, re

s = open(sys.argv[1], encoding='utf-8').read()
body = re.sub(r'(?m)^#.*$', '', s)                       # 去掉標題行
body = re.sub(r'(?m)^[-－—]\s*$', '', body)              # 去掉分節線
paras = [p.strip() for p in re.split(r'\n\s*\n', body) if p.strip()]
plain = re.sub(r'\s', '', body)
n = len(plain)

# 句子（以。？！切）
sents = [x for x in re.split(r'[。？！]', body) if x.strip()]
slen = [len(re.sub(r'\s', '', x)) for x in sents]

def per_k(w):
    return round(body.count(w) / max(n, 1) * 1000, 1)

single = [p for p in paras if len(re.findall(r'[。？！]', p)) <= 1 and len(re.sub(r'\s','',p)) <= 20]
s1 = len(re.findall(r'不是[^，。」]{1,14}，\s*而?是', body))
commas, periods = body.count('，'), body.count('。')

def ok(c): return '✓' if c else '✗'

print(f"字數 {n}\n")
print("── 寫法 ──")
print(f" {ok(any(x>=70 for x in slen))} 最長句 {max(slen) if slen else 0} 字（要有 ≥70 的長句）")
print(f" {ok(any(x<=10 for x in slen))} 最短句 {min(slen) if slen else 0} 字")
need = 8 if n >= 800 else 3
print(f" {ok(len(single)>=need)} 單句成段 {len(single)} 處（需 ≥{need}）")
print(f" {ok(body.count('！')==0)} 驚嘆號 {body.count('！')} 個（需 0）")
print(f" {ok(body.count('#')<=2)} hashtag {body.count('#')} 個（需 ≤2）")
print(f" {ok('「' in body)} 引號 {body.count('「')} 處")

print("\n── 中文（歐化篩）──")
print(f" {ok(s1<=1)} 「A 不是 B，而是 C」 {s1} 次（需 ≤1）")
print(f" {ok(body.count('——')<=1)} 破折號 {body.count('——')} 個（需 ≤1）")
for w, lim in [('一個',2), ('自己',2), ('被',3), ('那個',2), ('這個',2)]:
    v = per_k(w)
    print(f" {ok(v<=lim)} 「{w}」每千字 {v}（需 ≤{lim}）")
r = round(commas / max(periods,1), 2)
print(f" {ok(r>=1.5)} 逗號÷句號 {r}（需 ≥1.5）")
