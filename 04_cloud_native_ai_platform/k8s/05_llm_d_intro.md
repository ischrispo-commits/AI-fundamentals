# 云原生高性能分布式 LLM 推理框架 llm-d 介紹

`llm-d` 是一個開源的、`Kubernetes` 原生的分布式 `LLM` 推理服務棧（serving stack），目標是把單機推理引擎擴展成生產級的叢集化服務。專案由 `Red Hat`、`Google Cloud`、`IBM Research`、`CoreWeave` 和 `NVIDIA` 共同发起，現為 `CNCF` sandbox 專案，當前已釋出 v1.0（本文核對日 2026-11-05，版本資訊以官方釋出頁為準）。

它不重新造推理引擎：真正執行模型計算的仍是 `vLLM`、`SGLang` 這類模型伺服器。`llm-d` 補的是它們之外的部分——請求路由、字首快取感知排程、預填充/解碼分離、`KV Cache` 分層解除安裝、多機模型服務編排，以及一套經過測試的部署路徑。官方描述它為「production deployments on Kubernetes 最佳化的高效能分散式推理服務棧」，在 `NVIDIA`、`AMD`、`Intel GPU` 和 `Google TPU` 上都驗證過。

## 目錄

- [云原生高性能分布式 LLM 推理框架 llm-d 介紹](#云原生高性能分布式-llm-推理框架-llm-d-介紹)
  - [目錄](#目錄)
  - [1. 它要解決什麼問題](#1-它要解決什麼問題)
  - [2. 核心機制](#2-核心機制)
    - [2.1 入口：Gateway API + 推理擴展](#21-入口gateway-api--推理擴展)
    - [2.2 EPP：端點選擇器](#22-epp端點選擇器)
    - [2.3 字首快取感知路由](#23-字首快取感知路由)
    - [2.4 P/D 分離](#24-pd-分離)
  - [3. KV Cache 分層與 offloader](#3-kv-cache-分層與-offloader)
    - [3.1 分層結構](#31-分層結構)
    - [3.2 offloader 的三種實現](#32-offloader-的三種實現)
    - [3.3 LMCache 一節](#33-lmcache-一節)
  - [4. 模型服務編排：基於 LWS](#4-模型服務編排基於-lws)
  - [5. Well-Lit Paths：官方部署路徑](#5-well-lit-paths官方部署路徑)
  - [6. 效能資料與口徑](#6-效能資料與口徑)
  - [7. 總評](#7-總評)
  - [參考資料](#參考資料)

---

## 1. 它要解決什麼問題

單機 `vLLM` 或 `SGLang` 跑到生產規模，會遇到幾層問題，`llm-d` 的每個元件基本都對應其中一層：

**路由層：** `Kubernetes` 原生的 `Service` 負載均衡按連線分發請求，不看模型伺服器手裡有什麼。兩條 prompt 字首相同的請求被分到不同實例，各自重新算一遍相同的 `prefill`，`GPU` 在重複勞動上空燒。多副本場景下，`KV Cache` 的命中率完全靠運氣。

**資源形態層：** `prefill` 是計算密集型，`decode` 是訪存密集型，兩者對硬體的要求相反，混在同一實例裡互相拖累。長上下文和多實例並存時，這種錯配會被放大。

**`KV Cache` 層：** `HBM` 裝不下的 `KV` 塊被驅逐後直接丟棄，下一輪請求命中不了；跨實例之間沒有共享機制，同一個會話換個副本就要全部重算。

**編排層：** 多機張量並行的推理服務是一個「要麼全起、要麼全廢」的組，`Deployment` 和 `StatefulSet` 的單 Pod 語義管不住它，故障恢復需要整組原子操作。

這些問題沒有一個是新問題，但 `llm-d` 之前，它們散落在各家自研閘道器和排程器裡，沒有形成開源的標準件。

## 2. 核心機制

### 2.1 入口：Gateway API + 推理擴展

`llm-d` 的流量入口是一個符合 `Gateway API Inference Extension`（社群裡常縮寫為 `GAIE`）的高性能 `L7` 代理。`Gateway API Inference Extension` 是 `Kubernetes` 社群為 AI 推理流量定義的標準擴展——它給 `Gateway` 增加了「按模型服務池路由」和「把推理負載特徵暴露給路由器」的能力，`llm-d` 是這個擴展的主要實現方之一。

### 2.2 EPP：端點選擇器

路由決策的核心元件是 `EPP`（`Endpoint Picker`，端點選擇器）。官方架構文件對它的定義是：

- 一個可擴展的 **Filter-Score-Pick 流水線**，先過濾候選端點，再逐個打分，最後選出目標；
- 依據實時指標、`KV Cache` 親和性（`KV-cache affinity`）和已配置的策略對模型伺服器 Pod 打分；
- 支援用宣告式 `YAML` 配置打分插件，可以按需替換打分邏輯。

EPP 是 `llm-d` 與傳統閘道器的本質區別：傳統閘道器知道「哪個副本活著」，EPP 知道「哪個副本手裡已經有這條 prompt 的字首快取、當前負載多少」。

### 2.3 字首快取感知路由

EPP 的打分鏈路裡有一類字首快取感知的 scorer：透過跟蹤各模型伺服器的 `KV Cache` 事件（官方描述為「event-driven tracking of cache state across all model servers」），路由器能知道哪台伺服器快取了請求的字首，把請求發過去就能省掉重複 `prefill`。官方把這條路徑稱為「Precise Prefix-Cache Aware Routing」，提供了啟發式和精確兩類命中判斷技術。

這裡要拆清一個容易混淆的術語：**字首快取感知路由**解決的是「請求發到哪個副本」，**P/D 分離**解決的是「prefill 和 decode 在哪裡執行」，兩個是獨立機制，可以單獨啟用也可以組合使用。下文的 P/D 分離特指 prefill/decode 解耦，與字首快取無關。

### 2.4 P/D 分離

`prefill`（計算密集）和 `decode`（訪存密集）被拆到各自的專用 worker 上，`prefill` 完成後透過高速 `RDMA` 通道把 `KV` 狀態傳給 `decode` 側（官方架構描述為「high-speed RDMA KV transfer」）。底層依賴 `vLLM` 的 `NixlConnector` 做 `RDMA` 傳輸。官方引用的 `AWS` 基準顯示，在 `B200` 上對比標準 `vLLM` 部署，分離式部署的吞吐最高提升 70%（廠商口徑，見第 6 節）。

## 3. KV Cache 分層與 offloader

### 3.1 分層結構

`HBM` 裡驅逐的 `KV` 塊不丟棄，而是下沉到 `CPU` 記憶體，可選再下沉到共享檔案系統，後續請求命中字首時再載入回來。官方 `tiered-prefix-cache` 指南描述的層級是：

```text
GPU HBM → CPU RAM → (可選) ReadWriteMany 共享檔案系統
```

共享檔案系統層是 2026 年 2 月新增的能力（官方博客「Native KV Cache Offloading to Any Filesystem」），多個副本可以複用同一份 `KV` 儲存，官方給出的對比資料是 TTFT 最多快 16.8 倍（廠商口徑）。

路由器側配合做第二層快取感知：scorer 除了跟蹤各伺服器 `GPU` 裡的字首，還會跟蹤 `CPU` 層各持有哪些字首（`gpu-prefix-cache-producer` / `cpu-prefix-cache-producer` 兩個索引），因為 `vLLM` 不上報 `CPU` 層的大小，這一層的容量需要手工設定 `lruCapacityPerServer`。

### 3.2 offloader 的三種實現

分層快取透過 `CONNECTOR` 參數選擇實現，官方指南列出三類：

| CONNECTOR           | 實現                                                                       | 支援層級    | 適用引擎                            |
| ------------------- | -------------------------------------------------------------------------- | ----------- | ----------------------------------- |
| `native`（推薦）    | `vLLM OffloadingConnector`；`SGLang HiCache`；`vLLM TPU offload connector` | `cpu`、`fs` | vLLM / SGLang / TPU                 |
| `lmcache-connector` | [LMCache](https://lmcache.ai)                                              | `cpu`、`fs` | vLLM（NVIDIA / AMD GPU、Intel XPU） |
| `mooncake-store`    | `MooncakeStore`（`CPU DRAM` 池 + `SSD`，走 `RDMA`）                        | `cpu`、`fs` | —                                   |

### 3.3 LMCache 一節

`LMCache` 是三種 offloader 中社群認知度最高的一個，也是 [本倉庫 KV Cache 系列文章](../../09_inference_system/kv_cache/02_systems/01_lmcache/01_lmcache_overview.md) 單獨深析過的元件，這裡只講它與 `llm-d` 的介面關係：

- `llm-d` 透過 `CONNECTOR=lmcache-connector` 啟用 `LMCache` 作為 offloader，覆蓋 `cpu` 與 `fs` 兩層；
- `CPU` 層容量按 `LMCACHE_MAX_LOCAL_CPU_SIZE` 配置（單位 GiB，按張量並行 rank 計）；
- 指標走 `LMCache` 自己的匯出項，如 `lmcache:retrieve_hit_rate`（檢索命中率）和 `lmcache:local_cache_usage`（本地快取佔用）。

`LMCache` 本身的多層級儲存架構、`CacheGen` 壓縮、`NIXL` 傳輸後端等細節，見 [LMCache 架構概覽](../../09_inference_system/kv_cache/02_systems/01_lmcache/01_lmcache_overview.md)。

## 4. 模型服務編排：基於 LWS

多機推理服務（張量並行或專家並行跨節點展開）以 Leader-Worker 組為單位執行：Leader 起主行程，Worker 隨後加入，故障時整組重建。`llm-d` 的模型服務編排直接採用 [`LeaderWorkerSet`](./04_lws_intro.md)（`LWS`）實現這種組語義，`LWS` 也因此與 `llm-d` 專案協同設計——這是 `K8s` 社群裡「控制器原語為推理負載而改」的一個實際案例。

## 5. Well-Lit Paths：官方部署路徑

`llm-d` 把經過測試、帶基準資料的部署模式稱為 `Well-Lit Paths`（照明路徑），每條路徑帶 `Helm chart`、調優參數、基準結果和可觀測性配置。截至核對日，官方站點列出的路徑包括：

- **Precise Prefix-Cache Aware Routing**：精確字首快取感知路由
- **Tiered Prefix Cache**：分層字首快取（`CPU` / 檔案系統解除安裝）
- **P2P Prefix Cache Sharing**：副本間字首快取共享
- **Prefill/Decode Disaggregation**：預填充/解碼分離
- **Route Requests by Predicted Latency**：按預測延遲路由
- **Flow Control and Fairness**：流量控制與公平性
- **Autoscale your Inference Pool**：推理池自動擴縮容

生產落地建議從對應路徑的 `Helm chart` 入手改參數，而不是從零拼元件——這些路徑的基準數字也是這麼測出來的。

## 6. 效能資料與口徑

以下是官方渠道公佈的效能宣告，**均為廠商口徑**，未在本倉庫獨立複測：

| 宣告                                             | 出處                    |
| ------------------------------------------------ | ----------------------- |
| 輸出吞吐最高 3 倍                                | llm-d.ai 官網           |
| TTFT 最快 2 倍                                   | llm-d.ai 官網           |
| P/D 分離對比標準 vLLM，`B200` 上吞吐最高提升 70% | 官方 README（AWS 基准） |
| TTFT 與 ITL 降低 40%（`Google Vertex` 場景）     | llm-d.ai 官網           |
| 檔案系統 `KV` 解除安裝使 TTFT 最多快 16.8 倍         | 官方博客（2026-02）     |

這類數字的生成條件（模型、負載、硬件、對比基線）各不相同，直接遷移到你自己的環境大機率打折。專案迭代很快，介面和路徑都在動，部署前以官方最新文件為準，本資料核對日 2026-11-05。

## 7. 總評

`llm-d` 把「推理閘道器 + 快取排程 + 分層 KV + 多機編排」這條鏈路做成了 `Kubernetes` 上的標準開源件，架構落在社群標準（`Gateway API Inference Extension`、`LWS`、`CDI`）之上，而不是私有協議，這是它區別於各家自研推理閘道器的根本點。v1.0 发布后，核心 `API` 已穩定，適合認真評估生產引入。

**折扣清單**（採用前需要接受的條件）：

1. **效能數字全部是廠商口徑**，不同宣告的測試條件不透明，落地前必須用自己負載複測；
2. **元件鏈路長**：`Gateway` + `EPP` + offloader + `LWS` + 模型伺服器，每一層都有自己的配置空間和故障面，運維成本明顯高於單機 `vLLM`；
3. **`RDMA` 依賴**：`P/D` 分離和 `MooncakeStore` 路徑需要叢集具備 `RDMA` 網路，純乙太網叢集收益打折；
4. **`CPU` 層快取容量需手工設定**（`lruCapacityPerServer`），引擎不上報 `CPU` 層大小，容量配錯會直接影響命中率；
5. **版本迭代快**：`Well-Lit Paths` 的參數形態隨版本變動，鎖定版本再部署。

## 參考資料

- [llm-d 官網](https://llm-d.ai)
- [llm-d GitHub 倉庫](https://github.com/llm-d/llm-d)
- [llm-d 架構文件](https://llm-d.ai/docs/architecture)
- [Tiered Prefix Cache 官方指南](https://github.com/llm-d/llm-d/blob/main/guides/tiered-prefix-cache/README.md)
- [LeaderWorkerSet 官方文件](https://lws.sigs.k8s.io)
- [LMCache 官網](https://lmcache.ai)
- 本倉庫相關文章：[vLLM + LWS 多機多卡推理](./04_lws_intro.md) · [LMCache 架構概覽](../../09_inference_system/kv_cache/02_systems/01_lmcache/01_lmcache_overview.md)
