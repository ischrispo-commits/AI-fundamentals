# 00_study_plan：AI Infra GTM 速成讀書計畫（個人學習層）

> 這個目錄是本 fork 新增的「個人讀書計畫層」，以上游 [AI Fundamentals](../README.md) 的文章為教材，目標是在 12 週內具備應徵外商 **Pre-sales／Solutions Engineer（主軸，伺服器・AI Infra）**，以及備選的 **TMM／AI Evangelist／PMM（AI Infra・GPU・Data Center）／TAM** 的技術深度與表達能力。學習方法依《Make It Stick》（《超牢記憶法》）與《學生為什麼不喜歡上學？》操作化：**每天提取測驗、間隔與交錯、先想再讀、信心校準、具體先於抽象、故事開場**。本層內容以繁體中文撰寫；上游文章維持簡體，引用時不改寫。

## 怎麼開始（第一天 30 分鐘）

1. 讀 [01_syllabus.md](01_syllabus.md) 第 1～3 節與第 7 節（規定），把 12 週日期放進行事曆。
2. 讀 [02_assessment_spec.md](02_assessment_spec.md) 第 1、4、5 節：知道每天 6 題怎麼來、信心怎麼填。
3. 錯題本已建立在 [quizzes/error_log.md](quizzes/error_log.md)（含開課前診斷的 2 題）；進度看 [progress/log.md](progress/log.md)。
4. 打開 [roadmap.html](roadmap.html)（瀏覽器直接開）當進度看板。
5. 11/16（一）早上做 [quizzes/week01/d01_pretest.md](quizzes/week01/d01_pretest.md)，然後用 skill 產生第一份講義。

## 每日流程（1 小時版，2026-11-11 起；細節見 [01_syllabus.md](01_syllabus.md) 第 0 節）

```text
平日
  10 分鐘  閉卷做當日測驗（07:43 自動送到手機）→ 填信心 → 對答案 → 錯題進錯題本
  35 分鐘  讀當日講義（handouts/wNN/dMM_*.md）：先想再讀 3 題 → 情境 → 概念 → 數字口徑 → 誤區 → Pre-sales 口徑 → 課後提取 5 題
  10 分鐘  口說：對當日受眾講 60 秒（一 客戶 CxO／採購、二 客戶工程師、三 自家業務、四 客戶反對意見、五 面試官），錄音存 handouts/wNN/audio/
   5 分鐘  緩衝
週六 1 小時  週測 12 題（25 分鐘）→ 寫週作業 35 分鐘（只有 7 份必做，見總綱 6.1）
週日 1 小時  完成作業 45 分鐘 → 填 review.md 15 分鐘 → 22:00 前交（21:17 自動送週檢測）
```

時間不夠的那天，優先順序：**每日測驗 > 講義第 3、5、7 節 > 其他**。repo 原文（★）是有空再讀的延伸，不在每日 1 小時內。

## 用 skill 產生教材（給較便宜模型執行）

兩個專案級 skill 放在 `.claude/skills/`，任何支援 Claude Code skill 的模型都能用；設計上**只轉述 repo 原文、不創作事實**，每個數字帶 `file:line`，所以交給便宜模型執行也安全。

| 想做的事                                   | 說法範例                                                                 | skill                     | 產出位置                                   |
| ------------------------------------------ | ------------------------------------------------------------------------ | ------------------------- | ------------------------------------------ |
| 產生某一天的講義                           | 「用 course-handout-builder 產生 W01D02 的講義」                          | `course-handout-builder`  | `handouts/w01/d02_<slug>.md`               |
| 整週講義一次產生                           | 「產生第 2 週 D1～D5 的講義」                                              | `course-handout-builder`  | `handouts/w02/`                            |
| 產生當日測驗（含解答）                     | 「用 retrieval-quiz-builder 出 2026-11-24 的每日測驗」                     | `retrieval-quiz-builder`  | `quizzes/week02/d02_quiz.md` + answer_key  |
| 產生週測、週前測、模組考                   | 「出第 2 週週測」「出模組一的模組考」                                      | `retrieval-quiz-builder`  | `quizzes/week02/d06_weekly_quiz.md`、`quizzes/module1_exam.md` |
| 模組考沒過要重考                           | 「依錯題本出模組一的重考卷」                                               | `retrieval-quiz-builder`  | `quizzes/module1_retake.md`                |
| 產生某模組的模擬面試題                     | 「出模組二的模擬面試題庫（TAM 場）」                                        | `retrieval-quiz-builder`  | `quizzes/interview_bank_module2.md`        |

建議順序：**前一天晚上**先產生明天的講義與測驗（skill 會從講義的 K 點清單抽題），早上直接閉卷做。

## 檔案索引

| 檔案                                                             | 說明                                                                           |
| ---------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| [01_syllabus.md](01_syllabus.md)                                 | 課程總綱：基本資訊、教學目標、邊界、指定閱讀、12 週安排、作業與考試日期、評分與規定 |
| [02_assessment_spec.md](02_assessment_spec.md)                   | 測驗規格：體系、K 點、七種題型、組卷配方、Leitner 間隔、信心校準、解答格式、評分表   |
| [03_role_competency_map.md](03_role_competency_map.md)           | 五種職缺（★Pre-sales 主軸）× 能力 × 面試題型 × 作業對應；JD 關鍵字；作品集組合；自我定位問卷 |
| [roadmap.html](roadmap.html)                                     | 視覺化 12 週路線圖與進度勾選（存於瀏覽器 localStorage）                             |
| [progress/log.md](progress/log.md)                               | **跨對話共享的進度檔**：目前狀態、開課前基準線、每次檢查紀錄、給 Claude 的檢查流程（roadmap.html 的勾選 Claude 看不到，以這份為準） |
| [quizzes/error_log.md](quizzes/error_log.md)                     | 錯題本（Leitner 盒），每日與每週檢查都會更新                                         |
| [quizzes/baseline/](quizzes/baseline/2026-11-11_diagnostic.md)   | 開課前能力診斷（2026-11-11，16 題，7／16）                                          |
| [quizzes/week01/](quizzes/week01/README.md)                      | 第 1 週完整題庫：前測、每日測驗 ×4、週測、解答、K 點清單                            |
| [quizzes/interview_bank_module1.md](quizzes/interview_bank_module1.md) | 模組一模擬面試題庫（英文提問、中文要點）                                       |
| [handouts/](handouts/README.md)                                  | 講義、作業、週反思、錄音的存放處（由 skill 產生與索引）                             |
| [templates/](templates/)                                         | 錯題本、週反思模板                                                               |

## 與上游的關係

- 上游內容（`01_` ～ `99_` 目錄）不改寫內容；本層新增 `00_study_plan/` 與 `.claude/skills/`，並在 [CLAUDE.md](../CLAUDE.md) 加一節說明。
- **例外：課綱指定的 109 篇文章已轉成繁體（台灣用語）**，用 [tools/to_traditional.py](tools/to_traditional.py) 逐行轉換：行數不變（`file:line` 仍有效），檔名、連結路徑、網址不轉。「顯存」「網卡」「參數」「實例」「台」這幾個詞的簡體原文有例外表，避免轉成「視訊記憶體」「網絡卡」「引數」「例項」「臺」。其他文章仍是簡體。
- 若上游更新導致 K 點的 `file:line` 失效，跑 `python3 .claude/skills/course-handout-builder/scripts/check_handout.py <講義>` 會報錯，依報錯修行號即可。
- 同步上游：`git fetch upstream && git merge -X theirs upstream/main`（已轉繁體的文章一律先收上游版本），接著跑 `pip install opencc-python-reimplemented && python3 00_study_plan/tools/to_traditional.py` 重新轉換；`README.md` 與 `CLAUDE.md` 的新增段落需手動確認。
