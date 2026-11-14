# 7 年前，AI 記住一個字要 4.5 MiB；今天只要 890 B——七張圖講透 KV Cache

圖解入門版：七張手繪圖講清 KV Cache 的賬。技術細節與全部數字的出處，見參考長文 [Attention 演進與 KV Cache 之變：每 token 從 4.5 MiB 到 890 B](attention_evolution_kv_cache.md)——17 個代表性模型逐欄位對照 config.json 與引擎原始碼核對。

> 嚴謹說明：「一個字」指一個 token；所有數字按訓練精度 2 位元組/元素計算，混合模型只計全注意力層。

2020 年，GPT-3 每生成一個字，要花 4.5 MiB 顯存去「記住」它。到今年 9 月，DeepSeek-V4.1-Flash 把這個數字壓到了 890 B。七年，約 5000 倍。這篇用七張圖，把 KV Cache 這筆賬算清楚。

![圖1：KV Cache 是顯存裡唯一越用越多的部分](assets/kvcache-01-hook.png)

**圖 1**：推理的顯存裡有兩筆賬：模型權重是固定的，KV Cache 卻隨上下文線性增長。拿 Llama-3-8B 算：每 token 128 KiB，4K 上下文只要 0.5 GB，到 128K 就要 16 GB——追平權重。這就是長上下文又慢又貴的根源。

![圖2：MHA 每個頭各存一份 K/V](assets/kvcache-02-mha.png)

**圖 2**：最原始的存法叫 MHA：注意力有多少個頭，就存多少份 K/V。頭的獨立性是好事，代價是按頭數計費：7B 模型 32 個頭，每 token 512 KiB。

![圖3：GQA 幾個頭共用一份 K/V](assets/kvcache-03-gqa.png)

**圖 3**｜第一輪省法：讓幾個頭共用一份 K/V，這就是 GQA。70B 的大模型用上它，每 token 320 KiB，反而比 7B 的老款還小。代價：頭少了，能力略降。

![圖4：MLA 壓縮打包](assets/kvcache-04-mla.png)

**圖 4**：第二輪更徹底：DeepSeek 的 MLA 不共享了，把所有頭的 K/V 直接壓進一個小小的隱向量。671B 的模型，每 token 只要 68 KiB，比 7B 的 GQA 還小一半。代價：拆包費工，引擎要為它寫專門的核心。

![圖5：SWA 只留最近一個視窗](assets/kvcache-05-swa.png)

**圖 5**：第三輪最簡單粗暴：滑動視窗注意力（SWA）只留最近一個視窗，視窗外當場扔掉。滑窗層的賬從此固定（gpt-oss 只要 3 MiB），但長文件裡「看過但想不起」的錯誤，多半來自這裡。

![圖6：2026 年的三條路線](assets/kvcache-06-routes.png)

**圖 6**：到 2026 年，這本賬分成了三種演算法，而且不可互相比較：DeepSeek 的序列壓縮把 KV 壓到幾乎不漲（890 B/token）；GLM-5.3 的稀疏選擇只省計算、不省儲存，KV 照舊線性漲；Kimi K3 的線性混合乾脆把大部分 KV 換成固定狀態。

![圖7：七年之間每 token 的 KV 賬縮水約 5000 倍](assets/kvcache-07-seven-years.png)

**圖 7**：七個代表模型放到一根對數軸上：七年之間，每 token 的賬從 4.5 MiB 縮到 890 B，約 5000 倍。省下的不是算力，是顯存——和模型大小無關。

這筆賬還在變。下一篇講系統側怎麼接招：PagedAttention、字首複用與淘汰——同樣的卡，為什麼 vLLM 出來之後吞吐翻倍。

想往深處走：完整技術版是 [Attention 演進與 KV Cache 之變](attention_evolution_kv_cache.md)（17 個模型逐一對照 config 的長文）；2026 年序列壓縮路線的深挖在 [KV 壓縮推到極限三部曲](../../../09_inference_system/kv_cache/07_kv_compression/README.md)。
