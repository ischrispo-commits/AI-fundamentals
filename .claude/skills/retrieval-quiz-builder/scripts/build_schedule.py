#!/usr/bin/env python3
"""依日期算出每日測驗的抽題來源（D-1／D-3／D-7／D-14+）、各來源日的 K 點，以及錯題本到期題。

用法：python3 build_schedule.py --date 2026-11-24 --type daily [--repo-root PATH] [--json]
      python3 build_schedule.py --code W02D02 --type daily
類型：daily | pretest | weekly | module
"""
import argparse
import datetime as dt
import glob
import json
import os
import re
import sys

COURSE_START = dt.date(2026, 11, 16)   # W1 D1（週一）
REVIEW_WEEK = 7                        # 不產生講義與每日測驗的複習週
MODULE_OF_WEEK = {1: 1, 2: 1, 3: 1, 4: 2, 5: 2, 6: 2, 7: 2, 8: 3, 9: 3, 10: 3, 11: 4, 12: 4}
AUDIENCE = {1: "CxO", 2: "工程師", 3: "TAM", 4: "Demo", 5: "面試官"}
K_RE = re.compile(r"^(W(\d{2})D(\d{2})-K\d+)\s*\|")


def find_repo_root(start="."):
    cur = os.path.abspath(start)
    while True:
        if os.path.exists(os.path.join(cur, "CLAUDE.md")) and os.path.isdir(os.path.join(cur, ".git")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return os.path.abspath(start)
        cur = parent


def date_to_code(d):
    delta = (d - COURSE_START).days
    if delta < 0:
        raise SystemExit(f"{d} 早於課程開始日 {COURSE_START}")
    week = delta // 7 + 1
    day = d.weekday() + 1  # 1=Mon … 7=Sun
    return week, day


def code_to_date(code):
    m = re.match(r"W(\d{2})D(\d{2})", code)
    if not m:
        raise SystemExit("代碼格式應為 W02D03")
    w, d = int(m.group(1)), int(m.group(2))
    return COURSE_START + dt.timedelta(days=(w - 1) * 7 + (d - 1))


def is_study_day(d):
    w, day = date_to_code(d)
    return 1 <= day <= 5 and w != REVIEW_WEEK and w >= 1


def study_days_back(d, n):
    """往前數 n 個上課日。"""
    cur = d
    count = 0
    while count < n:
        cur -= dt.timedelta(days=1)
        if cur < COURSE_START:
            return None
        if is_study_day(cur):
            count += 1
    return cur


def load_k_points(root):
    """從 quizzes/week*/k_points.md 與 handouts/w*/d*_*.md 收集 K 點 → {code: [ids]}"""
    pools = {}
    files = glob.glob(os.path.join(root, "00_study_plan/quizzes/week*/k_points.md"))
    files += glob.glob(os.path.join(root, "00_study_plan/handouts/w*/d*_*.md"))
    for f in files:
        for line in open(f, encoding="utf-8", errors="ignore"):
            m = K_RE.match(line.strip())
            if m:
                code = f"W{m.group(2)}D{m.group(3)}"
                pools.setdefault(code, {"ids": [], "files": set()})
                if m.group(1) not in pools[code]["ids"]:
                    pools[code]["ids"].append(m.group(1))
                pools[code]["files"].add(os.path.relpath(f, root))
    return {k: {"ids": v["ids"], "files": sorted(v["files"])} for k, v in pools.items()}


def load_error_log(root, today):
    path = os.path.join(root, "00_study_plan/quizzes/error_log.md")
    due, pending = [], []
    if not os.path.exists(path):
        return due, pending
    for line in open(path, encoding="utf-8", errors="ignore"):
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 10 or not re.match(r"\d{4}-\d{2}-\d{2}", cells[0]):
            continue
        logged = dt.date.fromisoformat(cells[0][:10])
        kid, status = cells[1], cells[-1]
        if "移出" in status:
            continue
        retests = [c for c in cells[6:9] if c]
        last = logged
        for c in retests:
            m = re.search(r"(\d{4}-\d{2}-\d{2})", c)
            if m:
                last = max(last, dt.date.fromisoformat(m.group(1)))
        item = {"k_point": kid, "logged": str(logged), "retests": len(retests), "last": str(last), "status": status}
        if (not retests and (today - logged).days >= 1) or (retests and len(retests) < 3 and (today - last).days >= 3):
            due.append(item)
        else:
            pending.append(item)
    return due, pending


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--code")
    ap.add_argument("--type", default="daily", choices=["daily", "pretest", "weekly", "module"])
    ap.add_argument("--repo-root")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    root = a.repo_root or find_repo_root()

    if a.code:
        target = code_to_date(a.code)
    elif a.date:
        target = dt.date.fromisoformat(a.date)
    else:
        target = dt.date.today()
    week, day = date_to_code(target)
    pools = load_k_points(root)
    due, pending = load_error_log(root, target)

    out = {"date": str(target), "code": f"W{week:02d}D{day:02d}", "week": week, "day": day,
           "module": MODULE_OF_WEEK.get(week), "type": a.type, "slots": [], "error_log_due": due,
           "error_log_pending": len(pending), "notes": []}

    if week == REVIEW_WEEK:
        out["notes"].append("第 7 週為複習週：每日測驗改為錯題本重測與跨模組累積測驗，從模組一、二全部 K 點抽題")
    if a.type == "daily":
        if day > 5:
            out["notes"].append("週六為週測、週日為反思；每日測驗只在週一至週五")
        offsets = [("1", "D-1", "FR"), ("2", "D-1", "SA/CA"), ("3", "D-3", "SA/CA"), ("4", "D-7", "MT/TJ"), ("5", "D-14+", "任意")]
        for seq, slot, qtype in offsets:
            n = {"D-1": 1, "D-3": 3, "D-7": 7, "D-14+": 14}[slot]
            src = study_days_back(target, n)
            entry = {"seq": seq, "slot": slot, "qtype": qtype}
            if src is None:
                entry["source"] = "missing"
                entry["fallback"] = "本週較早日或前測回收" if n <= 3 else "前測回收或本週 K 點"
            else:
                sw, sd = date_to_code(src)
                code = f"W{sw:02d}D{sd:02d}"
                entry["source"] = code
                entry["source_date"] = str(src)
                entry["k_points"] = pools.get(code, {}).get("ids", [])
                entry["files"] = pools.get(code, {}).get("files", [])
                if not entry["k_points"]:
                    entry["status"] = "missing"
                    entry["fallback"] = "用 course-handout-builder/references/weekly-day-plan.md 的來源文章現場建暫定 K 點"
            if slot == "D-14+" and due:
                entry["prefer_error_log"] = [d["k_point"] for d in due]
            out["slots"].append(entry)
        out["slots"].append({"seq": "6", "slot": "本週任一", "qtype": "OR", "audience": AUDIENCE.get(day, "工程師"),
                             "k_points": sum((pools.get(f"W{week:02d}D{d:02d}", {}).get("ids", []) for d in range(1, day + 1)), [])})
    elif a.type == "pretest":
        if week not in (1, 4, 8, 11):
            out["notes"].append("週前測只在模組首週（W1、W4、W8、W11）")
        out["slots"] = [{"day": f"W{week:02d}D{d:02d}", "k_points": pools.get(f"W{week:02d}D{d:02d}", {}).get("ids", []), "count": 2} for d in range(1, 6)]
    elif a.type == "weekly":
        out["slots"] = [{"section": "本週", "days": [f"W{week:02d}D{d:02d}" for d in range(1, 6)], "count": 10,
                         "k_points": {f"W{week:02d}D{d:02d}": pools.get(f"W{week:02d}D{d:02d}", {}).get("ids", []) for d in range(1, 6)}},
                        {"section": "前幾週", "weeks": list(range(1, week)), "count": 6},
                        {"section": "遷移", "count": 2}, {"section": "客戶信 CX", "count": 1}, {"section": "口說 OR 3 分鐘工程師版", "count": 1}]
    elif a.type == "module":
        mod = MODULE_OF_WEEK.get(week)
        weeks = [w for w, m in MODULE_OF_WEEK.items() if m == mod and w != REVIEW_WEEK]
        prev = [w for w, m in MODULE_OF_WEEK.items() if m == (mod - 1) and w != REVIEW_WEEK]
        out["slots"] = [{"section": "本模組", "weeks": weeks, "count": 20}, {"section": "前模組", "weeks": prev, "count": 10},
                        {"section": "長答", "count": 2}, {"section": "白板", "count": 1, "difficulty": "3-4"}]

    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(f"目標：{out['date']}（{out['code']}，模組 {out['module']}，類型 {a.type}）")
        for n in out["notes"]:
            print("  注意：", n)
        for s in out["slots"]:
            print("  ", json.dumps(s, ensure_ascii=False))
        print(f"  錯題本到期 {len(due)} 題：", [d['k_point'] for d in due], f"；未到期 {len(pending)} 題")
    return 0


if __name__ == "__main__":
    sys.exit(main())
