#!/usr/bin/env python3
"""把讀書計畫用到的簡體內容轉成繁體（台灣用語），保護檔名、連結與網址。

用法（repo 根目錄）：
    pip install opencc-python-reimplemented
    python3 00_study_plan/tools/to_traditional.py            # 轉換：學習層 + 課綱指定文章
    python3 00_study_plan/tools/to_traditional.py --check    # 只列出還有簡體的檔案，不寫入
    python3 00_study_plan/tools/to_traditional.py --list     # 列出課綱指定文章

同步上游後重跑一次即可（建議 `git merge -X theirs upstream/main` 先收上游版本，再重轉）。

規則：
- 逐行轉換，行數不變，所以講義與 K 點裡的 `檔案:行號` 仍然有效。
- 不轉：網址、連結目標的路徑、HTML 的 src／href、看起來像檔名或路徑的字串（檔名維持簡體，否則連結會斷）。
- 連結目標裡的錨點（# 之後）會跟著轉，因為標題也轉了；只限指向「同樣有轉換」的檔案。
- 只轉「含簡體字的那一串漢字」，已經是繁體的文字不動，所以可以安全重跑（冪等）。
- 用語例外表見 OVERRIDES：OpenCC 的預設轉法在 AI 硬體領域不自然的詞，強制改成慣用說法。
"""
import argparse, os, re, subprocess, sys, urllib.parse

try:
    from opencc import OpenCC
except ImportError:
    sys.exit("請先安裝：pip install opencc-python-reimplemented")

CC = OpenCC("s2twp")
CHAR = OpenCC("s2t")

# 簡體 → 慣用繁體（優先於 OpenCC 的詞組轉換）
OVERRIDES = {
    "台风": "颱風",
    "台": "台",          # 台灣慣用「台」，不轉成「臺」（一台、平台、台積電）
    "显存": "顯存", "顯存": "顯存",
    "网卡": "網卡", "網卡": "網卡",
    "算子": "算子",
    "进程": "行程",
    "全局内存": "全域記憶體",
    "质量": "品質",
    "激活": "激活",
    "智能体": "智能體",
    "数据中心": "資料中心",
    "参数": "參數",        # 不轉成「引數」（模型參數、7B 參數）
    "实例": "實例",        # 不轉成「例項」（MIG 實例、雲端實例）
    "扩展": "擴展",        # OpenCC 會誤轉成「擴充套件」
    "类型": "類型",
}
# 長的詞先替換，避免「台风」被「台」先吃掉
PH = {k: chr(0xE000 + i) for i, k in enumerate(sorted(OVERRIDES, key=len, reverse=True))}

# 繁體也照常使用、但 OpenCC 會當成簡體的字；判斷「這段是不是簡體」時忽略
SHARED = set("台里只干后面发系制准冲历云余了志注才谷丑卷布范松游借占几刮困朴仆千升咸姜岳折采钟周伙群峰")

EXT = r"(?:md|png|jpe?g|gif|svg|webp|html?|pdf|pptx?|ipynb|py|json|ya?ml|txt|sh|csv)"
PROTECT = re.compile(
    r"https?://[^\s)\]>\"'`]+"                                  # 網址
    r"|(?:src|href)\s*=\s*\"[^\"]*\"|(?:src|href)\s*=\s*'[^']*'"  # HTML 屬性
    r"|`[^`\n]*\." + EXT + r"(?::\d+(?:-\d+)?)?`"                # 反引號裡的檔名（可含空白）
    r"|[\w一-鿿%.\-/]*\." + EXT + r"(?::\d+(?:-\d+)?)?(?![\w])"  # 檔名／路徑（含 :行號）
)
CJK_RUN = re.compile(r"[一-鿿]+")
STUDY_MODE = False
LINK = re.compile(r"(\]\()([^)\s]*)(\s+\"[^\"]*\")?(\))")
REFDEF = re.compile(r"^(\s*\[[^\]]+\]:\s*)(\S+)(.*)$")

STUDY_DIRS = ("00_study_plan/", ".claude/skills/")


def has_simplified(text):
    return any(ch not in SHARED and CHAR.convert(ch) != ch for ch in text if "一" <= ch <= "鿿")


def conv_plain(text):
    # 只轉「含簡體字的那一串漢字」，已經是繁體的不動；這樣重跑也不會把「實例」再轉成「例項」
    return CJK_RUN.sub(lambda m: _conv(m.group(0)) if has_simplified(m.group(0)) else m.group(0), text)


def _conv(text):
    for k, v in PH.items():
        text = text.replace(k, v)
    text = CC.convert(text)
    for k, v in PH.items():
        text = text.replace(v, OVERRIDES[k])
    return text


def conv_segment(text):
    """轉換一段文字，但保留 PROTECT 命中的部分。"""
    out, last = [], 0
    for m in PROTECT.finditer(text):
        out.append(conv_plain(text[last:m.start()]))
        out.append(m.group(0))
        last = m.end()
    out.append(conv_plain(text[last:]))
    return "".join(out)


def conv_target(target, src_file, converted):
    if "#" not in target or target.startswith(("http://", "https://", "mailto:")):
        return target
    path, frag = target.split("#", 1)
    if path:
        dest = os.path.normpath(os.path.join(os.path.dirname(src_file), urllib.parse.unquote(path)))
        if dest not in converted:
            return target
    return path + "#" + conv_plain(urllib.parse.unquote(frag)) if "%" in frag else path + "#" + conv_plain(frag)


def conv_line(line, src_file, converted):
    m = REFDEF.match(line)
    if m:
        return conv_segment(m.group(1)) + conv_target(m.group(2), src_file, converted) + conv_segment(m.group(3))
    out, last = [], 0
    for m in LINK.finditer(line):
        out.append(conv_segment(line[last:m.start()]))
        out.append(m.group(1) + conv_target(m.group(2), src_file, converted) + (m.group(3) or "") + m.group(4))
        last = m.end()
    out.append(conv_segment(line[last:]))
    return "".join(out)


def tracked():
    return set(subprocess.check_output(["git", "ls-files", "-z"], text=True).split("\0"))


def syllabus_articles(files):
    found = set()
    s = open("00_study_plan/01_syllabus.md", encoding="utf-8").read()
    for t in re.findall(r"\]\((\.\./[^)#\s]+\.md)", s):
        found.add(os.path.normpath(os.path.join("00_study_plan", urllib.parse.unquote(t))))
    d = open(".claude/skills/course-handout-builder/references/weekly-day-plan.md", encoding="utf-8").read()
    for t in re.findall(r"`([0-9][0-9]_[^`]+?\.md)`", d):
        found.add(os.path.normpath(t))
    return sorted(f for f in found if f in files and not f.startswith(STUDY_DIRS))


def study_files(files):
    return sorted(f for f in files if f.startswith(STUDY_DIRS) and f.endswith(".md"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    files = tracked()
    articles = syllabus_articles(files)
    if a.list:
        print("\n".join(articles))
        return 0
    study = study_files(files)
    converted = set(articles) | set(study)
    changed = 0
    global STUDY_MODE
    for f in study + articles:
        STUDY_MODE = f.startswith(STUDY_DIRS)
        lines = open(f, encoding="utf-8").read().split("\n")
        new = []
        for line in lines:
            if not has_simplified(line):
                new.append(line)
            else:
                new.append(conv_line(line, f, converted))
        assert len(new) == len(lines), f
        if new != lines:
            changed += 1
            if a.check:
                print("待轉換：", f)
            else:
                open(f, "w", encoding="utf-8").write("\n".join(new))
    print(f"{'檢查' if a.check else '轉換'}完成：學習層 {len(study)} 檔、課綱文章 {len(articles)} 篇，{'需要轉換' if a.check else '有變動'} {changed} 檔")
    return 0


if __name__ == "__main__":
    sys.exit(main())
