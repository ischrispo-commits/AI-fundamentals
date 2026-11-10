#!/usr/bin/env python3
"""測驗檔檢查：欄位、題數、題型配方、無選擇題、解答的 K 點與 file:line 可解析。

用法：python3 check_quiz.py <quiz.md> [--key answer_key.md] [--repo-root PATH]
"""
import argparse
import glob
import os
import re
import sys

MC = re.compile(r"^\|[^|]*\|[^|]*\|[^|]*[（(]?\b[ABCD][)）.．]\s", re.M)
FILE_LINE = re.compile(r"([\w./\-一-鿿]+\.md):(\d+)(?:-(\d+))?")
KID = re.compile(r"W\d{2}D\d{2}-K\d+")


def find_repo_root(start):
    cur = os.path.abspath(start)
    while True:
        if os.path.exists(os.path.join(cur, "CLAUDE.md")) and os.path.isdir(os.path.join(cur, ".git")):
            return cur
        p = os.path.dirname(cur)
        if p == cur:
            return None
        cur = p


def known_k_points(root):
    ids = set()
    for f in glob.glob(os.path.join(root, "00_study_plan/quizzes/week*/k_points.md")) + glob.glob(os.path.join(root, "00_study_plan/handouts/w*/d*_*.md")):
        for line in open(f, encoding="utf-8", errors="ignore"):
            m = re.match(r"^(W\d{2}D\d{2}-K\d+)\s*\|", line.strip())
            if m:
                ids.add(m.group(1))
    return ids


def rows_of(text):
    rows = []
    for l in text.splitlines():
        if re.match(r"^\|\s*[A-Z]*\d+\s*\|", l):
            cells = [c.strip() for c in l.strip().strip("|").split("|")]
            rows.append(cells)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("quiz")
    ap.add_argument("--key")
    ap.add_argument("--repo-root")
    a = ap.parse_args()
    root = a.repo_root or find_repo_root(os.path.dirname(a.quiz) or ".")
    errors, warns = [], []
    text = open(a.quiz, encoding="utf-8").read()
    name = os.path.basename(a.quiz)

    if "信心" not in text:
        errors.append("缺「信心」欄")
    if "題型" not in text:
        errors.append("缺「題型」欄")
    if MC.search(text):
        errors.append("疑似選擇題選項（A. B. C.）")
    rows = rows_of(text)
    types = [r[1] for r in rows if len(r) > 1]
    expected = None
    if "pretest" in name:
        expected = 10
    elif re.match(r"d0[1-5]_quiz", name):
        expected = 6
        if types and types[-1] != "OR":
            errors.append("每日測驗最後一題必須是 OR（口說）")
        if types and types[0] != "FR":
            warns.append("每日測驗第 1 題建議為 FR")
        if "來源" not in text:
            errors.append("每日測驗缺「來源」欄（D-1／D-3／D-7…）")
    elif "weekly" in name:
        expected = 20
        for sec in ("客戶信", "口說"):
            if sec not in text:
                errors.append(f"週測缺「{sec}」題")
    elif "exam" in name or "retake" in name:
        if len(rows) < 30:
            errors.append(f"模組考／重考題數 {len(rows)}，要求 ≥ 30")
    if expected and len(rows) != expected:
        # 週測的 CX／OR 以段落呈現，表格列數可少 2
        if not ("weekly" in name and len(rows) == expected - 2):
            errors.append(f"題數 {len(rows)}，要求 {expected}")
    for r in rows:
        if len(r) > 1 and r[1] not in ("FR", "SA", "CA", "MT", "TJ", "CX", "OR", ""):
            errors.append(f"未知題型 {r[1]}（第 {r[0]} 題）")
    bad = [r[0] for r in rows if len(r) > 3 and re.search(r"(?<![A-Za-z])\d{3,}", r[3]) and r[1] in ("TJ",)]
    if bad:
        warns.append(f"TJ 題幹含三位以上數字，檢查是否洩漏答案：{bad}")

    if a.key and root:
        key = open(a.key, encoding="utf-8").read()
        known = known_k_points(root)
        refs = set(KID.findall(key))
        unknown = sorted(k for k in refs if k not in known)
        if unknown:
            errors.append(f"解答引用的 K 點不存在：{unknown[:8]}")
        if not refs:
            errors.append("解答沒有引用任何 K 點")
        if "精緻化提問" not in key:
            warns.append("解答沒有精緻化提問")
        checked = set()
        for m in FILE_LINE.finditer(key):
            path, hi = m.group(1), int(m.group(3) or m.group(2))
            if path in checked:
                continue
            checked.add(path)
            full = os.path.join(root, path)
            if not os.path.exists(full):
                hits = [os.path.join(d, os.path.basename(path)) for d, _, fs in os.walk(root) if os.path.basename(path) in fs and "/.git" not in d]
                if len(hits) == 1:
                    full = hits[0]
                else:
                    errors.append(f"解答來源檔不存在或不唯一：{path}")
                    continue
            n = sum(1 for _ in open(full, encoding="utf-8", errors="ignore"))
            if hi > n:
                errors.append(f"解答來源 {path}:{hi} 超過檔案長度 {n}")

    for e in errors:
        print("ERROR", e)
    for w in warns:
        print("WARN ", w)
    print(f"— {len(errors)} ERROR, {len(warns)} WARN, 題數 {len(rows)}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
