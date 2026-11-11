#!/usr/bin/env python3
"""講義結構檢查：章節齊全、圍欄閉合、K 點格式、file:line 可解析、題數與信心欄、Mermaid 數量、簡體比例。

用法：python3 check_handout.py <handout.md> [--repo-root PATH]
結束碼：0 無 ERROR；1 有 ERROR。WARN 不影響結束碼。
"""
import argparse
import os
import re
import sys

REQUIRED_HEADINGS = [
    "## 0. 先想再讀",
    "## 1. 今天的情境",
    "## 2. 核心概念",
    "## 3. 數字與口徑",
    "## 4. 常見誤區",
    "## 5. Pre-sales 口徑",
    "## 6. 精緻化提問",
    "## 7. 課後提取測驗",
    "## 8. 可測知識點",
    "## 來源索引",
]
K_LINE = re.compile(r"^(W\d{2}D\d{2}-K\d+)\s*\|\s*([1-4])\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*$")
FILE_LINE = re.compile(r"([\w./\-一-鿿]+\.md):(\d+)(?:-(\d+))?")
MC_PATTERN = re.compile(r"^\|[^|]*\|[^|]*\|[^|]*[（(]?\b[ABCD][)）.．]\s", re.M)
SIMPLIFIED_SAMPLE = "内发关这为时与对机术库显带宽级缓应该设实现数据网络连节点处计训练"  # 只放繁簡不同形的字
MERMAID_TYPES = ("flowchart", "sequenceDiagram", "timeline", "xychart-beta", "graph", "classDiagram", "stateDiagram")


def find_repo_root(start):
    cur = os.path.abspath(start)
    while True:
        if os.path.exists(os.path.join(cur, "CLAUDE.md")) and os.path.isdir(os.path.join(cur, ".git")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("handout")
    ap.add_argument("--repo-root", default=None)
    args = ap.parse_args()

    root = args.repo_root or find_repo_root(os.path.dirname(args.handout) or ".")
    if not root:
        print("ERROR 找不到 repo 根目錄（需要 CLAUDE.md 與 .git）；請用 --repo-root 指定")
        return 1

    text = open(args.handout, encoding="utf-8").read()
    lines = text.splitlines()
    errors, warns = [], []

    # 1. 章節
    for h in REQUIRED_HEADINGS:
        if not any(l.strip().startswith(h) for l in lines):
            errors.append(f"缺少章節：{h}")

    # 2. 圍欄閉合（``` 與 ```` 分開計）
    fence3 = sum(1 for l in lines if re.match(r"^\s*```(?!`)", l))
    fence4 = sum(1 for l in lines if re.match(r"^\s*````", l))
    if fence3 % 2:
        errors.append("``` 圍欄未閉合（奇數個）")
    if fence4 % 2:
        errors.append("```` 圍欄未閉合（奇數個）")

    # 3. Mermaid
    mermaid_blocks = re.findall(r"```mermaid\s*\n(.*?)```", text, flags=re.S)
    if len(mermaid_blocks) > 3:
        warns.append(f"Mermaid 圖 {len(mermaid_blocks)} 張，建議 ≤ 3")
    if len(mermaid_blocks) == 0:
        warns.append("沒有 Mermaid 圖；若機制可畫，建議至少一張")
    for i, b in enumerate(mermaid_blocks, 1):
        first = b.strip().splitlines()[0].strip() if b.strip() else ""
        if not first.startswith(MERMAID_TYPES):
            errors.append(f"Mermaid 第 {i} 張首行不是已知圖型：{first!r}")
        bad = re.findall(r"\[[^\]\"]*[()/#][^\]\"]*\]", b)
        if bad:
            warns.append(f"Mermaid 第 {i} 張節點文字含 ( ) / #，GitHub 可能渲染失敗：{bad[:2]}")

    # 4. K 點
    sec8 = re.search(r"## 8\. 可測知識點.*?(?=\n## |\Z)", text, flags=re.S)
    k_ids = []
    if sec8:
        for l in sec8.group(0).splitlines():
            if l.startswith("W") and "|" in l:
                m = K_LINE.match(l.strip())
                if not m:
                    errors.append(f"K 點格式錯誤：{l.strip()[:80]}")
                    continue
                k_ids.append(m.group(1))
                if not FILE_LINE.search(m.group(4)):
                    errors.append(f"K 點 {m.group(1)} 來源缺 file:line")
                if not re.search(r"\d", m.group(3)):
                    warns.append(f"K 點 {m.group(1)} 陳述不含數字；確認它是可檢驗的")
        if not (6 <= len(k_ids) <= 8):
            errors.append(f"K 點數量 {len(k_ids)}，要求 6～8")
        if len(k_ids) != len(set(k_ids)):
            errors.append("K 點編號重複")
        # 編號與檔名的週日一致
        m = re.search(r"/w(\d{2})/d(\d{2})_", args.handout.replace("\\", "/"))
        if m:
            prefix = f"W{m.group(1)}D{m.group(2)}-"
            for k in k_ids:
                if not k.startswith(prefix):
                    errors.append(f"K 點 {k} 與檔案路徑的週日 {prefix} 不符")

    # 5. file:line 可解析（全文）
    checked = set()
    for m in FILE_LINE.finditer(text):
        path, a, b = m.group(1), int(m.group(2)), m.group(3)
        if path in checked:
            continue
        checked.add(path)
        full = os.path.join(root, path)
        if not os.path.exists(full):
            # 允許只寫檔名（如 02_gpu_memory.md）：在 repo 內找唯一匹配
            hits = []
            for d, _, fs in os.walk(root):
                if "/.git" in d or "/node_modules" in d:
                    continue
                if os.path.basename(path) in fs:
                    hits.append(os.path.join(d, os.path.basename(path)))
            if len(hits) == 1:
                full = hits[0]
            elif len(hits) > 1:
                warns.append(f"來源 {path} 在 repo 有多個同名檔，請寫完整路徑")
                continue
            else:
                errors.append(f"來源檔案不存在：{path}")
                continue
        n = sum(1 for _ in open(full, encoding="utf-8", errors="ignore"))
        hi = int(b) if b else a
        if hi > n:
            errors.append(f"來源 {path}:{a}{'-' + b if b else ''} 超過檔案長度 {n}")

    # 6. 課後測驗
    sec7 = re.search(r"## 7\. 課後提取測驗.*?(?=\n## |\Z)", text, flags=re.S)
    if sec7:
        body = sec7.group(0)
        rows = [l for l in body.splitlines() if re.match(r"^\|\s*\d+\s*\|", l)]
        if len(rows) != 5:
            errors.append(f"課後測驗 {len(rows)} 題，要求 5 題")
        if "信心" not in body:
            errors.append("課後測驗表缺「信心」欄")
        if rows and "FR" not in rows[0]:
            warns.append("課後測驗第 1 題不是 FR（自由回憶）")
        if not any(t in body for t in ("| CA ", "口徑")):
            warns.append("課後測驗沒有計算題或口徑題")
        if MC_PATTERN.search(body):
            errors.append("課後測驗疑似出現選擇題選項（A. B. C.）")
        if not any("OR" in r for r in rows):
            warns.append("課後測驗沒有口說（OR）題")

    # 7. 第 5 節 Pre-sales 四段
    sec5 = re.search(r"## 5\. Pre-sales 口徑.*?(?=\n## |\Z)", text, flags=re.S)
    if sec5:
        body = sec5.group(0)
        for tag in ("CxO", "工程師", "配置", "反對"):
            if tag not in body:
                errors.append(f"第 5 節缺少「{tag}」段")
        cxo = re.search(r"CxO.*?(?=\n- \*\*|\Z)", body, flags=re.S)
        if cxo and re.search(r"\b(warp|SM|bank|NCCL|kernel)\b", cxo.group(0)):
            warns.append("CxO 版出現工程名詞（warp／SM／bank／NCCL／kernel）")

    # 8. 第 3 節口徑欄
    sec3 = re.search(r"## 3\. 數字與口徑.*?(?=\n## |\Z)", text, flags=re.S)
    if sec3:
        rows = [l for l in sec3.group(0).splitlines() if l.startswith("|") and not l.startswith("| ---") and "項目" not in l]
        empty = [r for r in rows if re.search(r"\|\s*\|\s*[^|]*\|\s*$", r) or r.count("|") < 6]
        if len(rows) < 3:
            warns.append("數字表少於 3 列")
        for r in rows:
            cells = [c.strip() for c in r.strip("|").split("|")]
            if len(cells) >= 5 and (not cells[3] or not cells[4]):
                errors.append(f"數字表有口徑或來源空白：{cells[0][:30]}")

    # 9. 字數
    body_text = re.sub(r"```.*?```", "", text, flags=re.S)
    cjk = len(re.findall(r"[一-鿿]", body_text))
    if cjk > 1800:
        warns.append(f"中文字數 {cjk}，超過 35 分鐘預算（建議 ≤ 1500）")
    if cjk < 900:
        warns.append(f"中文字數 {cjk}，偏少（建議 ≥ 1100）")

    # 10. 簡體比例（排除圍欄與引號內）
    plain = re.sub(r"[「“\"][^」”\"]*[」”\"]", "", body_text)
    simp = sum(plain.count(ch) for ch in SIMPLIFIED_SAMPLE)
    if cjk and simp / cjk > 0.01:
        warns.append(f"疑似簡體字比例偏高（樣本字 {simp} 個）；自己寫的句子應為繁體，引用請加引號")

    for e in errors:
        print("ERROR", e)
    for w in warns:
        print("WARN ", w)
    print(f"— {len(errors)} ERROR, {len(warns)} WARN, K 點 {len(k_ids)} 條, 中文字 {cjk}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
