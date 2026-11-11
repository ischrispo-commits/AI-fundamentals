# NVIDIA Inference Context Memory Storage：為長上下文與 Agentic AI 推理打造的 G3.5 上下文儲存層

**NVIDIA Inference Context Memory Storage** (ICMS) 是 **NVIDIA Rubin** 平台面向推理場景引入的一類上下文儲存基礎設施，旨在將推理上下文（Key-Value, KV cache）作為一種 AI 原生資料類別進行高效複用與共享。其核心思路是在 GPU HBM 與通用共享儲存之間建立面向 KV cache 的 **G3.5** 層（乙太網連線的快閃記憶體層），並結合 **BlueField-4** 資料處理器與 **Spectrum-X** 乙太網 RDMA 互聯，為延遲敏感且可重建的 KV 資料提供更高吞吐、更優能效與更穩定的低抖動訪問路徑。

> 命名說明：NVIDIA 於 2026-03 將該平台更名為 **CMX Context Memory Storage**（官方部落格頁於 2026-03-16 更新並改題），本文沿用釋出時名稱 ICMS。

---

## 要點總結

- **ICMS** 在 **Rubin** 平台引入 **pod** 級的**推理上下文儲存層**（**G3.5 層**），乙太網連線快閃記憶體用於承載可複用的 KV cache。
- **BlueField-4** 作為資料處理器，為 KV I/O 提供加速能力，包括線速加密與 CRC 保護，並可在 DPU 側完成 NVMe-oF 與物件 / RDMA 等協議的終結（termination）。
- **Spectrum-X** 乙太網提供 RDMA 互聯，為共享 KV cache 提供可預期的低延遲、低抖動與高頻寬訪問路徑。
- **Dynamo / NIXL / DOCA** 等軟體元件協同進行上下文放置、KV block 管理與預置（prestage），降低 decode 階段 stall 並提升複用效率。
- 在長上下文與 Agentic AI 推理場景中，官方給出了量化收益口徑（TPS / 能效倍數與 TCO 改善），集中列於第五節表格。

> 注：本文所稱 **GPU pod** 對應原文的 **Compute pod** 概念，是由多機架 GPU、Spectrum-X 乙太網與儲存組成的伸縮單元；原文使用 “petabytes” 的量級表述描述其容量目標，並未在該處給出精確的上限數值。

---

## 一、問題背景：推理上下文 (KV Cache) 的儲存挑戰

現代大規模 AI 推理（尤其是 Agentic AI 和長上下文推理）對 **Key-Value (KV) cache** 的需求激增：

- **KV Cache** 相當於推理過程中模型的“短期與長期記憶”，避免重複計算歷史資訊。
- 隨著上下文視窗擴展至百萬級令牌，傳統記憶體層（GPU HBM、系統記憶體）容量受限，通用儲存層（物件/檔案儲存）雖然容量大，但訪問延遲高，效率低。
- 當前層級（G1–G4）從 HBM 到共享儲存之間存在明顯的延遲、頻寬與能效斷層：
  - **G1**：GPU HBM（納秒級訪問，最高效率）
  - **G2**：主機記憶體（十到百納秒）
  - **G3**：本地 SSD（微秒級）
  - **G4**：共享儲存（毫秒級）

這些層級在規模擴展時對實時、可複用的推理上下文支援不足。

> 注：上述延遲量級用於幫助理解 G1–G4 的相對層級差異；原文主要強調不同層級在推理場景中的職責分工與效率差異，並未在該處給出統一的端到端延遲測量資料。

![KV cache memory hierarchy, from on‑GPU memory (G1) to shared storage (G4)](./img/kv-cache-memory-hierarchy-latency-efficiency-tradeoffs-png.webp)

> 圖源說明：配圖為第三方報道轉載素材（檔名為轉載時命名），原始圖樣出自 NVIDIA 官方博客，以官方頁面為準。

---

## 二、ICMS 的核心定位與架構層次

### 引入 G3.5 層：面向 KV cache 的上下文儲存層

ICMS 引入了一個新的層級 **G3.5**，作為乙太網連線的快閃記憶體層，用於在高效能 GPU 記憶體與可擴展共享儲存之間提供面向 KV cache 的上下文儲存能力：

- **用途**：專門存放可複用的、延遲敏感的 KV cache 資料；
- **特性**：
  - 高頻寬、低延遲訪問；
  - 大規模共享上下文儲存（每個 **GPU pod** 可提供 petabytes 級共享容量）；
  - 延長 GPU 記憶體層（HBM & DRAM）的有效容量邊界；
  - 支援跨節點 KV cache 共享，提高資源複用率。

該層利用高速快閃記憶體（flash）和 RDMA 網路能力改善訪問延遲並提升能效表現。

---

## 三、ICMS 的系統架構構成

從整體架構看，ICMS 作為 Rubin 平台的 pod 級上下文儲存層（G3.5），位於推理編排層與計算節點之間：上層由 **NVIDIA Dynamo**、**NIXL** 等推理框架協調 prefill / decode 與 KV cache 訪問，並透過 KV block 管理機制將需要的上下文從 ICMS 預置回主機記憶體或 GPU HBM；下層由 **Spectrum-X** 乙太網 RDMA 互聯將 Rubin 計算節點連線到基於快閃記憶體的 ICMS 目標節點，提供可預期的低延遲與低抖動資料路徑；在資料平面上，**BlueField-4** 負責 KV I/O 相關加速與協議終結（termination，如 NVMe-oF 與物件 / RDMA），從而降低主機 CPU 負載並提升上下文共享效率。

> 注：原文語境中關於 “共享” 與 “跨節點” 的討論主要指 **同一 GPU pod 內** 的多節點共享與複用（跨節點但不必跨 pod）。

![NVIDIA Inference Context Memory Storage architecture within the NVIDIA Rubin platform, from inference pool to BlueField-4 ICMS target nodes](./img/nvidia-inference-context-memory-storage-architecture-1536x1441-png.webp)

> 圖源說明：同上，第三方報道轉載素材，原始圖樣出自 NVIDIA 官方博客。

### 3.1 BlueField-4 DPU 作為架構核心

ICMS 的控制與資料平面由 **NVIDIA BlueField-4 資料處理單元 (DPU)** 驅動：

- 提供 **800 Gb/s** 連線能力；
- 內建 64-核 NVIDIA Grace CPU 和高頻寬 LPDDR；
- 提供線速加密與 CRC 資料保護，用於 KV 資料路徑的安全與完整性校驗；
- 可高效終結 NVMe-oF 與物件 / RDMA 協議（termination），減少主機 CPU 負載。

> 規格出處：800 Gb/s 連線、64 核 Grace CPU 與高頻寬 LPDDR 見《Inside the NVIDIA Vera Rubin Platform》博客（"BlueField-4 integrates a 64-core Grace CPU and high-bandwidth LPDDR5X memory…"）與 BlueField-4 / CMX 官方產品頁，見第七節參考文獻；ICMS/CMX 官方博客原文只作功能性描述，未列出具體數字。

---

### 3.2 Spectrum-X 乙太網與 RDMA 網路

ICMS 依託 **Spectrum-X 乙太網** 提供低延遲、高頻寬的 RDMA 網路：

- 保證 pod 內計算節點與 ICMS 層之間的高效資料互動；
- 實現跨節點的 KV cache 共享和快速預取；
- 支援標準 RoCE 等協議，保證網路可擴展性與互操作性。

---

### 3.3 軟體與控制層協同

ICMS 的運作離不開 NVIDIA 的軟體生態協同：

| 元件                                         | 作用                                                                   |
| -------------------------------------------- | ---------------------------------------------------------------------- |
| **NVIDIA Dynamo**                            | 作為推理編排與框架之一，參與上下文放置、KV block 管理與排程協同        |
| **NVIDIA Inference Transfer Library (NIXL)** | 配合 Dynamo 等框架進行 KV block 的遷移與預置（prestage）               |
| **NVIDIA DOCA 框架**                         | 提供 KV 通訊與儲存層能力，將上下文快取作為一等資源用於管理、共享與放置 |

這些元件用於協調上下文在各層記憶之間的放置與遷移（G1 → G2 → G3 → G3.5 → G4，以及從 G3.5 預置回 G2 / G1），以減少 decode 階段 stall 並降低 GPU 空轉。

---

## 四、ICMS 在推理資料路徑中的定位

整體推理記憶體/儲存層次示意：

```text
G1: GPU HBM         ← 熱上下文、低延遲訪問
G2: 主機記憶體 DRAM    ← 熱/暖上下文緩衝
G3: 本地 SSD         ← 暖上下文儲存
G3.5: ICMS (flash + RDMA) ← 共享、高頻寬 KV cache
G4: 共享物件/檔案儲存 ← 冷資料與日誌等持久資料
```

- **G3.5 (ICMS)** 彌補了 G3 與 G4 之間的效能/容量鴻溝；
- 支援針對推理任務的高吞吐、低延遲訪問；
- 重用 KV cache 而無需在每個節點上單獨生成與儲存。

> 注：“彌補鴻溝”為對原文中 “ICMS fills the missing KV capacity between G1–G3 and G4” 的概括性表述，強調其作為上下文儲存層在容量與效率之間的定位。

---

## 五、設計目標與優勢

| 目標                 | 優勢                                                           |
| -------------------- | -------------------------------------------------------------- |
| **提升吞吐與響應性** | 最高可達 5× 更高持續 TPS（tokens/s），降低推理停頓             |
| **提高能效**         | 相比傳統通用儲存，最高可達 5× 能效提升（power efficiency）     |
| **擴展上下文規模**   | 每個 GPU pod 可提供 petabytes 級共享容量，使長上下文推理更經濟 |
| **跨節點共享**       | 支援多節點間上下文複用，適合 agentic AI 架構                   |

這種設計最佳化了從 GPU 到快閃記憶體再到共享儲存的整個資料路徑，使得可複用上下文資料不必反覆計算。

---

## 六、總評

CMX/ICMS 把推理上下文當作一等資料類別來建儲存層，方向上有兩點站得住：其一，G3.5 層瞄準的是 G3（本地 SSD）與 G4（共享儲存）之間真實的效能/容量斷層，而複用物件是可重建的 KV cache，用較低價值介質承擔高價值路徑的思路成立；其二，把 BlueField-4 的協議終結與線速加密下沉到 KV 資料路徑，與 DPU 的定位一致，確實能為主機 CPU 減負。

引用其結論前需要打折的地方：

- 5× TPS、5× 能效均為 NVIDIA 官方口徑，未附測試配置，也缺獨立第三方復現，宜當作設計目標而非實測結論；
- 「petabytes 級」是量級表述，官方未給出單 pod 的精確容量上限；
- G1–G4 的延遲數字是幫助理解層級的量級示意，官方未提供統一的端到端測量資料；
- 平台 2026-03 由 ICMS 更名為 CMX，Dynamo / NIXL / DOCA 的分工仍在演進，細節以官方頁面最新版本為準；
- G3.5 依賴 Rubin 代際硬體（BlueField-4 + Spectrum-X），存量叢集無法透過軟體升級直接受益。

---

## 七、參考文獻

- **參考資料**: 詳見 [DOCA 程式設計入門](../../../02_dpu_programming/doca/doca_programming_guide.md) 第 5.4 節「儲存虛擬化與模擬（`doca_devemu`）」（對應 BlueField-4 終結 NVMe-oF / 物件協議的場景）；控制平面解除安裝可參考第 5.2 節「控制平面解除安裝（`doca_comch`）」。

- NVIDIA Corporation. "Introducing NVIDIA BlueField-4-Powered Inference Context Memory Storage Platform for the Next Frontier of AI." NVIDIA Technical Blog. 2026-01-06. 訪問日期: 2026-01-07. [Online]. Available: https://developer.nvidia.com/blog/introducing-nvidia-bluefield-4-powered-inference-context-memory-storage-platform-for-the-next-frontier-of-ai/ （題名以釋出時為準；該頁 2026-03-16 更新後現題為 "Introducing NVIDIA BlueField-4-Powered CMX Context Memory Storage Platform…"，現名 CMX）

- NVIDIA Corporation. "Inside the NVIDIA Vera Rubin Platform: Six New Chips, One AI Supercomputer." NVIDIA Technical Blog. 2026-01-05. [Online]. Available: https://developer.nvidia.com/blog/inside-the-nvidia-rubin-platform-six-new-chips-one-ai-supercomputer （BlueField-4 規格出處：64 核 Grace CPU、高頻寬 LPDDR5X、最高 800 Gb/s 乙太網 / InfiniBand 連線）

- NVIDIA Corporation. CMX Context Memory Storage（官方產品頁）. [Online]. Available: https://www.nvidia.com/en-us/data-center/ai-storage/cmx/
