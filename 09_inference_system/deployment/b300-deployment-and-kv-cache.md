# B300 上的模型部署與 KV Cache：官方手冊最佳實踐

**as-of 2026-09-15** ｜ 本文整理 vLLM 與 SGLang 官方手冊推薦的配置、調優判據和現成配方，以及廠商 model card 上跑透過的組合。§三 是唯一一節非手冊內容：按官方 cookbook 與 SGLang 原始碼，把 Kimi-K3 從 16 卡擴到 64 卡的三筆賬（權重 / KV / 通信）逐軸算清楚。每條推薦都標了出處。

## 口徑與來源

| 標註           | 含義                                                               |
| -------------- | ------------------------------------------------------------------ |
| **【SGLang】** | SGLang 官方文件，本地檢出 `c415f977b8`（2026-09-10）               |
| **【vLLM】**   | vLLM 官方文件，本地檢出 `43d691ec6b`（v0.26.1rc0-459，2026-08-07） |
| **【NVIDIA】** | NVIDIA model card、官方博客或 MIG 產品頁                           |
| **【原始碼】**   | 對本地 vLLM/SGLang 檢出逐行核對                                    |
| **【實測】**   | 有測量資料的第三方結果                                             |
| **【llm-d】**  | llm-d 專案官方部落格與文件（llm-d.ai）                               |

---

## 一、模型部署

### 1.1 先過三道門檻

**① SM103 是獨立 target，不是 SM100。**

`sm_100a` 的 cubin 不能直接跑在 B300 上，必須走 `sm_100f` family 目標或 `sm_103a`。這是大量 `no kernel image is available` 事故的根因。**用 CUDA 13 映象是充分條件**，不必去找所謂的「SM103 專用 tag」：SGLang 安裝頁裡 grep `SM103`/`B300` 是零命中。

**② INT8 在這塊卡上不可用。**

PTX 的 `.kind::i8` 目標列表是 `sm_100a / sm_101a / sm_110a`，**從未擴展到 sm_103a**；CUTLASS 按 arch guard 跳過 INT8 UMMA；vLLM 沒有 INT8 GEMM。所以所有量化方案只能走 FP8 / NVFP4。

⚠️ **失敗時機很坑**：vLLM 是在**模型完整載入之後**才硬報錯。POC 階段先用 ~1B 模型冒煙，不要等 405B 下載完。

**③ vLLM 映象 tag 有個反轉陷阱。**

≥ v0.20.0 起**無字尾 = CUDA 13**，`-cu129` 才是 CUDA 12 退出版；v0.19.x 及更早相反。NVIDIA 自己在 Model-Optimizer PR #2042 裡記了這條：`Don't trust the tag name — select a tag reporting CUDA_VERSION >= 13`。

### 1.2 引擎與映象

| 引擎         | 版本（as-of 2026-09-15） | 映象                                            | 備註                                                                  |
| ------------ | ------------------------ | ----------------------------------------------- | --------------------------------------------------------------------- |
| **vLLM**     | v0.29.0                  | `vllm/vllm-openai:v0.29.0`                      | 三家唯一正式 release；官方推薦 B300 用 CUDA 13                        |
| **SGLang**   | v0.5.19                  | `lmsysorg/sglang:v0.5.19-cu130-runtime`         | CUDA 12 lane 已退役                                                   |
| TensorRT-LLM | **1.3.0rc26**            | `nvcr.io/nvidia/tensorrt-llm/release:1.3.0rc26` | **迭代 26 個 RC 仍無 GA**；legacy TensorRT backend 已移除。不建議主線 |

**映象已知問題（未修復）**：

- vLLM 官方映象的 `TORCH_CUDA_ARCH_LIST` **不含 `10.3`**（v0.29.0 實測仍只有 `10.0`，PR #44344 未合併）→ 建議自建映象顯式加入
- vLLM：DeepEP MoE all-to-all 在 SM103/GB300 **不可用**（issue #41687 仍 open），實測「通信占 decode kernel 時間 ~93%」
- SGLang：tcgen05 kernel 在 sm_103 失敗 Xid 13（#34340 open）；MegaMoE 路徑 `CUDA_ERROR_ILLEGAL_ADDRESS`（#37559 open）

### 1.3 vLLM 的四個最佳化等級

vLLM 提供 `-O0` 到 `-O3` 四檔，用啟動時間換穩態效能【vLLM】：

| 等級              | 內容                                                      |
| ----------------- | --------------------------------------------------------- |
| `-O0`             | 無最佳化，啟動最快                                          |
| `-O1`             | 簡單編譯 + 快速融合 + PIECEWISE cudagraphs                |
| **`-O2`（預設）** | **額外編譯區間、額外融合、FULL_AND_PIECEWISE cudagraphs** |
| `-O3`             | 激進最佳化（當前等於 O2）                                   |

**三個官方給的啟動加速手段**：

1. **複用編譯快取**：`torch.compile` 產物存在 `VLLM_CACHE_ROOT`（預設 `~/.cache/vllm`），可跨機器複製、也可烤進映象。設 `VLLM_FORCE_AOT_LOAD=1` 讓快取未命中時顯式報錯，而不是靜默重編
2. **`--kv-cache-memory-bytes` 跳過顯存 profiling**：啟動日誌會列印能復現當前分配的精確值，下次啟動傳回去即可跳過測量與 CUDA graph 估算。該值只在同卡、同初始空閒顯存下有效
3. **`--enforce-eager` 跳過 CUDA graph**：啟動最快，代價是穩態 decode 性能

### 1.4 按模型給配方

以下命令均來自官方 cookbook / model card，可直接作為起點。

#### Kimi-K3 on B300 1×8

節點數由硬體決定，不是獨立選擇：**B300 1×8 = TP8 / DCP8**（Balanced 檔）。全系列節點配置：

| 硬件     | 節點    | 說明                           |
| -------- | ------- | ------------------------------ |
| B200     | 2×8     |                                |
| GB200    | 4×4     |                                |
| **B300** | **1×8** |                                |
| GB300    | 2×4     |                                |
| H200     | 2×8     | Unified High-Throughput 用 4×8 |

**大規模預設（32 GPU @ B300，每節點跑相同命令、只改 `--node-rank`）**【SGLang】：

```bash
SGLANG_OPT_DEEPGEMM_MEGA_MOE_NUM_MAX_TOKENS_PER_RANK=20480 \
sglang serve \
  --trust-remote-code \
  --model-path moonshotai/Kimi-K3 \
  --tp-size 32 --ep-size 32 \
  --enable-dp-attention --dp-size 4 --enable-dp-lm-head \
  --nnodes 4 --node-rank <rank> --dist-init-addr <node0-ip>:20000 \
  --moe-a2a-backend megamoe --moe-runner-backend deep_gemm \
  --kv-cache-dtype fp8_e4m3 \
  --mamba-ssm-dtype bfloat16 \
  --mamba-radix-cache-strategy extra_buffer_lazy \
  --mem-fraction-static 0.92 \
  --reasoning-parser kimi_k3 --tool-call-parser kimi_k3 \
  --host 0.0.0.0 --port 30000
```

擴展方式：**保持每 replica 的形狀不變，只動 replica 數**。這個形狀鎖死在 8 卡；從 16 擴到 64 卡買到什麼、買不到什麼，見 §三。

| GPUs | B200/B300 節點 | `--tp-size` / `--ep-size` | `--dp-size` |
| ---- | -------------- | ------------------------- | ----------- |
| 16   | 2×8            | 16                        | 2           |
| 32   | 4×8            | 32                        | 4           |
| 64   | 8×8            | 64                        | 8           |

**這兩個 flag 為什麼必須給**：

- `--kv-cache-dtype fp8_e4m3` 是承重的。cookbook 原文：`bf16 KV does not fit 128 requests per replica`
- `--mamba-ssm-dtype bfloat16`：KDA state 的 dtype 決定每卡賬單，只有 attention-TP 寬度、SSM dtype、cache 策略三個旋鈕能動它

#### DeepSeek-V4 系列

**單節點 TP=4**（B200/B300/GB200/GB300/H200 通用；RTX PRO 6000 用 TP=2，H100 用 TP=8）【SGLang】。

**Agentic 長上下文 + HiCache DRAM offload**（B200 FP4 + DSpark，TP8，併發 8–16）【SGLang】：

```bash
SGLANG_ENABLE_UNIFIED_RADIX_TREE=1 \
python3 -m sglang.launch_server \
  --model-path deepseek-ai/DeepSeek-V4-Pro-0813 \
  --trust-remote-code --tp 8 \
  --moe-runner-backend flashinfer_mxfp4 \
  --enable-deepseek-v4-fp4-indexer \
  --disable-flashinfer-autotune \
  --mem-fraction-static 0.90 \
  --swa-full-tokens-ratio 0.1 \
  --chunked-prefill-size 8192 \
  --speculative-algorithm DSPARK --speculative-dspark-block-size 6 \
  --enable-hierarchical-cache \
  --hicache-ratio 2.75 \
  --hicache-write-policy write_through \
  --hicache-io-backend direct \
  --hicache-mem-layout page_first_direct
```

高併發檔（DEP8 + DP attention，併發 64–160）換 `--dp 8 --enable-dp-attention --ep-size 8 --mem-fraction-static 0.88 --swa-full-tokens-ratio 0.02 --hicache-ratio 8`，並把 `--chunked-prefill-size` 提到 49152。

⚠️ **`--chunked-prefill-size` 是全域性預算，會被 `--dp` 均分**：上面那個 49152 除以 dp8 才是每 rank 的 6144。

⚠️ **DSv4 的 HiCache host 層用 `--hicache-ratio`（host/device token 比）定容，不是 `--hicache-size`**。

### 1.5 並行策略

**① MLA 模型上，attention TP > 1 會複製 KV，不是切分。**

這一點在【原始碼】里可以直接看到：

```python
# vllm/config/model.py:1504-1509
if self.use_mla:
    # When using MLA during decode it becomes MQA
    return 1
...
return max(1, total_num_kv_heads // parallel_config.tensor_parallel_size)
```

注意 GQA 分支：**KV heads 少於 TP 時也是「複製」**：Qwen3-235B（4 個 KV head）上開 TP8，8 卡各存一份完整副本。

**SGLang cookbook 把這條寫成了 Deep PP 的依據**：Deep PP 用 `--tp-size 1 --pp-size 8`（B300/GB300），因為

> `--tp-size 1` is also what buys context: above TP1 the MLA KV is replicated across the TP ranks, so **TP2 × PP8 holds roughly half the tokens of TP1 × PP16 for the same memory**.

實測（GB200，ISL 8192 / 併發 32）【SGLang】：

| 形狀           | prefill tok/s/GPU |
| -------------- | ----------------- |
| **PP16 × TP1** | **4550**          |
| PP8 × TP2      | 3596              |
| TEP16          | 2407              |
| TP16           | 1652              |

**但併發低於 ~8 時反過來**：pipeline 填不滿，TEP16 領先（1947 vs 1227），此時用 `--tp-size 16 --ep-size 16`。

**② vLLM 官方的「何時用哪種並行」**【vLLM】：

| 策略   | 官方給的適用場景                                                       |
| ------ | ---------------------------------------------------------------------- |
| **TP** | 模型單卡裝不下；或需要降低每卡權重佔用，以騰出更多 KV 空間             |
| **PP** | TP 已吃滿但還要繼續切；跨節點；很深很窄的模型                          |
| **EP** | **MoE 專用**。設 `enable_expert_parallel=True`，用 EP 替代 MoE 層的 TP |
| **DP** | 有足夠 GPU 複製整個模型；要擴吞吐而非擴模型；多使用者環境                |

**SGLang 官方的表述更直接**：`Data parallelism is better for throughput. When there is enough GPU memory, always favor data parallelism for throughput.`【SGLang】所以大 MoE 的預設形態是 Attention DP + MoE EP，不是單一 TP。

**③ GB300 跨 pod MNNVL 傳輸要加三個環境變數。**

cookbook 原文：某些 GB300 叢集上跨 pod NVLink 傳 KV 會失敗於 `nvlink_transport.cpp:497 Requested address ... not found!`，解法是在 prefill 和 decode 兩側的 `sglang serve` 前都加上【SGLang】：

```bash
MC_FORCE_MNNVL=1 NCCL_MNNVL_ENABLE=1 NCCL_CUMEM_ENABLE=1
```

### 1.6 CPU 與 NUMA：一條官方公式

vLLM V1 是多行程架構，每個行程都要 CPU。官方給出的**最低物理核數公式**【vLLM】：

```text
單 DP：至少 2 + N 個物理核（1 API server + 1 engine core + N GPU worker）
多 DP：A + DP + N + (1 if DP > 1 else 0)
```

其中 `A` 是 API server 數（預設等於 DP），`N` 是 GPU 總數。官方舉的例子：8 卡上 `DP=4, TP=2` → 4 API server + 4 engine core + 8 GPU worker + 1 DP coordinator = **17 個行程**。

> **官方警告原文**：`Using fewer physical CPU cores than processes will cause contention and significantly degrade throughput and latency. The engine core process runs a busy loop and is particularly sensitive to CPU starvation.`

⚠️ 注意是**物理核**：開了超執行緒的話，1 vCPU = 1 超執行緒 = 半個物理核，所以要 `2 × (2 + N)` 個 vCPU 起。

**NUMA 繫結**：多路伺服器上用 `--numa-bind`，vLLM 會自動探測 GPU-to-NUMA 對映並施加 `--cpunodebind=<node> --membind=<node>`。需要自定義時加 `--numa-bind-nodes` / `--numa-bind-cpus`。容器里可能需要 `--cap-add SYS_NICE`。

### 1.7 PD 分離

vLLM 文件開篇直寫 `Disaggregated prefill DOES NOT improve throughput`【vLLM】。

Dynamo 自己的 GB300 實測（Kimi-K3，agentic 負載）【NVIDIA】：

| 配置                          | 系統吞吐 tok/s/GPU | 每使用者 tok/s | TTFT P50   |
| ----------------------------- | ------------------ | ------------ | ---------- |
| SGLang **Aggregated**         | **84.4**           | 51.3         | **573 ms** |
| SGLang **Disaggregated 1P1D** | 61.0               | **75.9**     | 4,809 ms   |
| vLLM **Aggregated**           | **62.2**           | 57.8         | 879 ms     |
| vLLM **Disaggregated 1P1D**   | 50.3               | **90.0**     | 6,357 ms   |

**聚合部署的系統吞吐更高、TTFT 低 5–6 倍**；PD 分離只在 per-user 吞吐上贏。

**它會減少 decode 側的 KV 容量**（Dynamo 明文）：`Moving prefill to dedicated workers ... reserves GPUs for a pool whose KV cache is not used during decode`。

**Dynamo 明確拒絕給固定 P:D 比**：`Treat replica counts as a response to observed bottlenecks rather than as fixed ratios.`

**實際配 PD 時要處理的細節**【SGLang】：

- 混合模型（如 K3）的傳輸要搬**兩樣**：paged MLA KV **和** KDA recurrent state
- 端口：prefill `30000`、decode `30100`，派生的 ZMQ/dist 範圍不能在同一台機器上撞車
- `--prefill` 後面那個位置參數 `8998` 必須和 `--disaggregation-bootstrap-port` 一致，否則只有 decode worker 會註冊
- `--disaggregation-decode-extra-slots` **要顯式釘住**：不釘的話，32 請求以下預設翻倍、以上預設**歸零**

---

## 二、KV Cache

### 2.1 先把三個數分清

| 數字       | 含義                           | 來源                             |
| ---------- | ------------------------------ | -------------------------------- |
| **288 GB** | B300 **卡規格**                | 【NVIDIA】Blackwell Ultra 博客   |
| **279 GB** | GB300 NVL72 形態下**單卡可用** | 【NVIDIA】MIG 產品頁 `1x 279 GB` |
| **270 GB** | HGX B300 形態下**單卡可用**    | 【NVIDIA】MIG 產品頁 `1x 270 GB` |

MIG 頁尾註標明這些是 `Preliminary specifications`。**讀規格表用 288，做容量規劃用 279 或 270。**

**`gpu_memory_utilization` 的分母是總顯存，不是剩餘顯存**【原始碼】：

```python
# vllm/v1/worker/utils.py:446-456
requested_memory = math.ceil(init_snapshot.total_memory * cache_config.gpu_memory_utilization)
```

預設 **0.92**（`vllm/config/cache.py:68`）。網上大量二手資料寫 0.9，會算錯。

⚠️ **TensorRT-LLM 用的是相反約定**：`free_gpu_memory_fraction` 分母是初始化時的**空閒**顯存。跨引擎混用必錯。

### 2.2 量化：官方推薦 `fp8_e4m3`

SGLang 官方手冊有專門的 Best Practices 小節，三條【SGLang】：

1. **優先用離線量化的模型**：scaling factor 已包含在 checkpoint 里
2. **格式選 `fp8_e4m3`（推薦）**；`fp8_e5m2` 用於更大動態範圍；`nvfp4` / `fp4_mx_block16` 用於最大顯存節省（**實驗性**）
3. **確認 attention backend 支持**量化 KV

**官方警告**：量化 KV 在 attention 里使用前要反量化，**如果反量化沒有和 attention kernel 融合，效能會極慢**，可能抵消掉顯存收益。

**顯存收益（官方數字）**【SGLang】：

| 對比        | 可容納 token 數 |
| ----------- | --------------- |
| FP4 vs BF16 | **≈ 3.56×**     |
| FP4 vs FP8  | **≈ 1.78×**     |

（已計入 block scaling factor 的額外開銷）

**精度對照表（官方實測，KV16 = BF16 / KV8 = FP8 E4M3 / KV4 = FP4 E2M1）**【SGLang】：

| 模型             | 資料集       | KV16   | KV8    | KV4        |
| ---------------- | ------------ | ------ | ------ | ---------- |
| Qwen3-235B-A22B  | gsm8k        | 0.9168 | 0.9181 | 0.9186     |
| Qwen3-235B-A22B  | aime25       | 0.7733 | 0.7333 | **0.6000** |
| Qwen3-235B-A22B  | gpqa_diamond | 0.7010 | 0.6899 | 0.6778     |
| DeepSeek-R1-0528 | gsm8k        | 0.9157 | 0.9154 | 0.9124     |
| DeepSeek-R1-0528 | aime25       | 0.5067 | 0.4934 | **0.4000** |
| DeepSeek-R1-0528 | gpqa_diamond | 0.7707 | 0.7697 | 0.7273     |
| GPT-OSS-120B     | gsm8k        | 0.9161 | 0.9163 | 0.9152     |
| GPT-OSS-120B     | aime25       | 0.7533 | 0.7667 | **0.3533** |
| GPT-OSS-120B     | gpqa_diamond | 0.5081 | 0.5434 | **0.3202** |

**官方給的三條結論**：

- **簡單資料集**（gsm8k）：FP4 在兩種規模上都接近 FP8/BF16
- **模型越大越能容忍 FP4**（200B+ 明顯好於小模型）
- **長上下文可能退化更明顯**：量化誤差會累積

> 官方 Tip 原文：`Large models on simpler tasks typically show minimal degradation, while smaller models or complex reasoning tasks may require FP8 or BF16 for acceptable accuracy.`

**工程含義**：`fp8_e4m3` 是安全預設；FP4 KV 只在「大模型 + 簡單任務」上考慮，且必須自己複測。

**FP8 在實踐裡是承重項。** SGLang cookbook 寫得很直接：`--kv-cache-dtype fp8_e4m3` **is load-bearing**，因為 bf16 KV 裝不下每 replica 128 個請求。

**NVFP4 KV 的生產禁用理由**（vLLM issue #55673，2026-09-07 開，**仍 open**）【實測】：

4×B200、Qwen3.5-397B、FlashInfer TRT-LLM attention，1,319 題 GSM8K：

| KV cache / max seqs | Flexible exact match | Invalid responses |
| ------------------- | -------------------- | ----------------- |
| **FP8, 512**        | **96.664%**          | 0.682%            |
| NVFP4, 64           | 6.520%               | 93.177%           |
| NVFP4, 512          | **4.549%**           | **94.920%**       |

報告人排除了「高併發偽影」（兩個併發上限都失敗，FP8 對照組用同一後端）。**根因至今未定位**：PR #55670 修了一個真實的 scale 轉換缺陷，打補丁後仍是 4.776%，說明該缺陷 `is not sufficient to explain this Qwen failure`。

**適用範圍**：特定几何（`head_dim=256 / 8 query heads / 1 KV head`）上的問題，不等於所有模型都會掛。但**同族、同后端、對照組正常、根因未定位**，足以構成生產禁用。

**兩個記賬陷阱**：

- **MLA 的 per-token KV 有兩種口徑，差 13.9%**：

| 口徑                                            | 每 token 每層 | 61 層全模型  |
| ----------------------------------------------- | ------------- | ------------ |
| BF16 未量化                                     | 1152 B        | 70,272 B     |
| FP8 樸素口徑（`kv_lora_rank 512 + qk_rope 64`） | 576 B         | 35,136 B     |
| **FP8 vLLM 實際打包 `fp8_ds_mla`**              | **656 B**     | **40,016 B** |

NVIDIA + SGLang 的 GB300 長文用的是樸素 576；vLLM 實際是 512 B FP8 NoPE + 16 B scales + **128 B BF16 RoPE**。**按 576 算容量會少算 14%。**

- **`--cpu-offload-gb` 是權重解除安裝，不是 KV 解除安裝**；**`--swap-space` 已從 vLLM 移除**。

### 2.3 分層：HiCache 的實際配置

#### SGLang HiCache

SGLang 官方文件寫得很直接【SGLang】：

> L1 和 L2 是**單實例私有**的；只有 L3 能共享。`Host memory cannot be pooled across instances or across hosts, not even for two instances on the same node.`

所以想要跨實例複用，**必須配 `--hicache-storage-backend`**。`file` 後端預設落在節點本地 `/tmp/hicache`；`mooncake` / `hf3fs` / `nixl` / `aibrix` 在共享同一 namespace 時可達叢集級。

**核心參數與官方推薦值**【SGLang】：

```bash
--page-size 64                        # 快取管理的頁大小
--enable-hierarchical-cache           # 啟用 HiCache
--hicache-ratio 2                     # host 記憶體為 GPU 顯存的 2 倍
--hicache-size 100                    # 直接給 GB 數，會覆蓋上面的 ratio
--hicache-io-backend kernel           # CPU↔GPU 搬運的 I/O 后端
--hicache-write-policy write_through  # GPU→CPU 的寫策略
--hicache-storage-backend             # 可選：hf3fs / mooncake / nixl / aibrix
```

**記憶體佈局的相容性（官方）**：

| 布局                | 兼容性                                                             |
| ------------------- | ------------------------------------------------------------------ |
| `page_first`        | **只兼容 `kernel` I/O 后端**；用 `direct` 會自動切到 `layer_first` |
| `page_first_direct` | 專為 `direct` 後端設計，兼容 fa3，零複製效能與 `page_first` 相同   |
| `layer_first`       | —                                                                  |

**預取策略三選一（官方）**：

| 策略            | 語義                         |
| --------------- | ---------------------------- |
| `best_effort`   | 需要時終止預取               |
| `wait_complete` | 保證完整預取，快取複用率更高 |
| `timeout`       | 兩者折中                     |

**與 PD 分離的兩種官方組合**：

1. **僅 Prefill 開 HiCache**：讓 Prefill 實例之間共享 KV（適合 SystemPrompt 場景）
2. **Prefill 開 HiCache + Decode 開非同步解除安裝**：讓 Prefill 能複用 Decode 節點的 KV（適合多輪對話）

第二種的 Decode 側多一個 flag：`--disaggregation-decode-enable-offload-kvcache`。

**異構 TP 支持**：不同部署用不同 TP（如 tp=4 和 tp=8）共享同一儲存時，用 `--hicache-storage-backend-extra-config '{"tp_lcm_size": 8}'`，值是所有 TP size 的**最小公倍數**。

**現成的 Mooncake 部署樣例（官方）**：

```bash
export MOONCAKE_TE_META_DATA_SERVER="http://127.0.0.1:8080/metadata"
export MOONCAKE_GLOBAL_SEGMENT_SIZE=816043786240
export MOONCAKE_PROTOCOL="rdma"
export MOONCAKE_DEVICE="$DEVICE_LIST"
export MOONCAKE_MASTER=127.0.0.1:50051

python3 -m sglang.launch_server \
  --model-path $MODEL_PATH --tp 8 --page-size 64 \
  --enable-hierarchical-cache --hicache-ratio 2 \
  --hicache-mem-layout page_first_direct --hicache-io-backend direct \
  --hicache-storage-backend mooncake --hicache-write-policy write_through \
  --hicache-storage-prefetch-policy timeout
```

**一條容易踩的坑**（K3 的 DCP recipe）：host 層還沒完全 DCP-aware。

- L3 **總是**丟掉 DCP flag
- L1+L2 **開著 Spec Decode 時**也丟；關掉 Spec Decode 才保留
- 丟掉 DCP 之后，MLA KV 退回 TP 複製，**每請求的 KV 容量相應縮水**

#### vLLM KV 解除安裝

**兩套 spec**，由 `kv_connector_extra_config` 的 `spec_name` 選【vLLM】：

- `CPUOffloadingSpec`（預設）：單 CPU 層，完成的 GPU block 拷進 pinned host memory
- `TieringOffloadingSpec`：多級，CPU 主層 + 一個或多個二級層

**關鍵約束（官方）**：`Only the CPU primary tier has direct GPU access. Secondary tiers cannot read from or write to GPU memory; all GPU↔secondary transfers are staged through the CPU primary tier.`

**單層（純 CPU）最小配置**：

```bash
vllm serve <model> \
  --kv-transfer-config '{
    "kv_connector": "OffloadingConnector",
    "kv_role": "kv_both",
    "kv_connector_extra_config": {
      "block_size": 64,
      "cpu_bytes_to_use": 1000000000
    }
  }'
```

**多層（CPU + 檔案系統）**：

```bash
vllm serve <model> \
  --kv-transfer-config '{
    "kv_connector": "OffloadingConnector",
    "kv_role": "kv_both",
    "kv_connector_extra_config": {
      "spec_name": "TieringOffloadingSpec",
      "cpu_bytes_to_use": 10737418240,
      "block_size": 16,
      "eviction_policy": "lru",
      "secondary_tiers": [
        {"type": "fs", "root_dir": "/mnt/kv_cache",
         "n_read_threads": 32, "n_write_threads": 16}
      ]
    }
  }'
```

**官方的 Tuning Tips（原文照譯）**【vLLM】：

- `cpu_bytes_to_use` 越大越好：更大的 CPU 層意味著更少去訪問更慢的二級層、命中率更高。**這個值是所有 worker 的總和，不是每 worker**
- **單層（純 CPU）配置時，`cpu_bytes_to_use` 要大於 GPU KV 總量**。因為解除安裝是即時的，CPU 層比 GPU 小就只是映象，不提升命中率
- `block_size` / `blocks_per_chunk`：更大的解除安裝塊減少簿記開銷，但會加大查詢粒度
- **FS 執行緒數**：`n_read_threads` / `n_write_threads` 按儲存能承受的併發調。**讀在 prefill 路徑上對延遲敏感，prefill 命中率高時多給讀執行緒**
- 共享 `root_dir` 的多實例：模型、`block_size`、並行佈局、dtype 都一樣才會共用一個 `<digest>` 子目錄；改任何一項都會生成新目錄，舊的成為孤兒（無害，可刪）

**跨實例共享的硬前提**：`PYTHONHASHSEED` 必須在所有實例上設成同一個固定值（如 `0`），否則每個行程的 block 內容雜湊種子不同，**同樣內容會算出不同檔名**。P2P 層會**強制校驗**這一點：沒設就啟動失敗，握手裡發現對端值不同會被拒絕。

**解除安裝的收益與代價（實測資料）**：

| 層級轉移        | 實測效果                                                                                    | 口徑     |
| --------------- | ------------------------------------------------------------------------------------------- | -------- |
| CPU DRAM        | TTFT 降 2–22×，吞吐最高 9×                                                                  | 【vLLM】 |
| 命中 vs 重算    | 1k tokens 時 2.2×，80k 時 32.8×                                                             | 【實測】 |
| CPU DRAM on/off | 10k/40k/80k 改善 1.30/1.18/1.08×；**1k 時四種配置無差別**                                   | 【實測】 |
| SSD 盈虧平衡    | 8k prompt 需 **77.8%** 字首複用才回本；80k 時降到 7.8%                                      | 【實測】 |
| SSD 超大規模    | 100k prompt 超 HBM 時 −79% TTFT、+264% 吞吐；但 cache 達 12.6–13.7M tokens 時最好也只有 −3% | 【實測】 |

**核心獨立結論**：`a cache hit is not sufficient for caching to be beneficial` / `External KV caching should therefore be treated as a setup specific admission decision`。【實測】

**頻寬現實**：GPU↔CPU 在 PCIe 5.0 ×16 上實測 54–56 GB/s（理論的 40–45%）；NVMe 單盤 6–13.5 GB/s。**不要把鏈路速率當吞吐。**

⚠️ **一條反直覺的實測**：GPUDirect Storage（KvikIO/cuFile）在這個負載上 `was slower than all our other implementations`。

### 2.4 複用：兩項已經被實測的收益

**Prefix Caching / RadixAttention**：

Agent 場景的真實命中率 **95.7%**（~4,300 個 Claude Code + Codex session，~350,000 LLM steps）【實測】：

- fresh tokens 只占 append tokens 的 **19.0%**，約 81% 的 prefill 原則上可命中
- miss 是**空閒驅動**的：間隔超 5 分鐘開始出現低命中，1 小時後幾乎全 miss
- **cache 命中占 agent 總成本 59.5%**，append 占 29.2%，output 只占 11.2%

**一個直接可用的調參**：超時從 1 分钟提到 1 小時，命中率 85.4% → 98.6%，但儲存比從 R=0.74 漲到 5.07（**約 7 倍**）。**大部分收益是便宜的**：5 分鐘時已達 ~94% 命中，R≈1.9。

**官方給的排程策略**【SGLang】：`--schedule-policy lpm`（longest prefix match）會重排請求以提升快取命中，代價是排程開銷增加；共享字首多的負載用。

**Radix cache 不是永遠開著好**：K3 cookbook 明確寫了，**對無字首的流量（離線批處理、評測）關掉它**，因為一個請求佔 4–5 個 state slot，關掉只佔 1 個。

**cache-aware 路由**：

| 排程器                 | 輸出 tok/s | TTFT p90    |
| ---------------------- | ---------- | ----------- |
| **precise-scheduling** | **8730**   | **0.542 s** |
| approximate            | 6944       | 31.083 s    |
| load-based             | 4429       | 94.865 s    |
| random                 | 4429       | 92.551 s    |

（8 vLLM pod / 16×H100，Qwen3-32B，150 個 B2B 客戶 × 6,000-token 共享上下文）【llm-d】

**但有反方觀點**（Anyscale，作者含 NVIDIA 人員）：`balancing KV cache reuse with token load leads to better overall serving performance than maximizing KV cache reuse alone`。兩個具名失效模式：**request herding** 與 **session-level imbalance**。

**私有化多租戶必須配 `cache_salt`**：它注入首個 block 的 hash，保證只有同 salt 的請求能複用 KV block。**不配會跨租戶洩露。**

**harness 側的硬規則**（可直接抄進開發規範）：

- 保持 prompt 字首穩定：**哪怕一個 token 的差異都會讓從該點起的快取全部失效**
- 系統提示開頭放時間戳會直接殺掉命中率
- 上下文保持 append-only
- **序列化必須確定性**：很多庫不保證 JSON key 順序穩定，會靜默破壞快取

### 2.5 容量與併發：實際調過的數字

**同一份硬體上的真實併發**（GB300 NVL72，NVIDIA + SGLang 聯署）【實測】：

| 指標                                    | GB300                              | GB200       |
| --------------------------------------- | ---------------------------------- | ----------- |
| `mem_fraction_static = 0.75` 下靜態預算 | ≈216 GB                            | ≈144 GB     |
| 權重（DeepSeek-R1 NVFP4, EP16/TP16）    | ≈40 GB                             | ≈40 GB      |
| **KV 池**                               | **≈176 GB**                        | ≈104 GB     |
| 單請求 KV（136K cached tokens）         | ≈4.45 GiB                          | —           |
| 理論上限                                | **≈40 req/GPU**                    | ≈24 req/GPU |
| 按 ~85% 運維目標                        | **36 req/GPU**（DEP16 → 576 併發） | 20 req/GPU  |

⚠️ **該頁自身有內部不一致**：TL;DR 按 DEP8 寫「288 concurrent」，正文按 DEP16 寫 576；加速比出現 1.38X–1.58X / 1.4X–1.6X / 1.4X–1.5X 三種表述。

**Kimi-K3 on 8×B300 的現成配置**【NVIDIA model card】：

```bash
--quantization modelopt_mixed --tensor-parallel-size 8
--moe-backend flashinfer_trtllm --kv-cache-dtype fp8
--max-model-len 196608 --max-num-seqs 32
--attention-backend FLASHINFER_MLA
```

配套限制：`flashinfer_trtllm` **是強制的**，`auto-resolution never triggers the TRT-LLM deferred-finalize path, and flashinfer_cutlass lacks a SiTU kernel for routed experts`；且 `a pip-installed SGLang cannot load this checkpoint`（SGLang 路徑需專用映象）。

**DCP 換併發**【SGLang】：`--dcp-size 8` 去重 attention-TP 組內的 MLA KV：**同等引擎吞吐下併發上限 +72%，代價是 ITL 約 1.8×**。適用於上下文 ≥ ~16K，或每 replica 併發超過 128。

### 2.6 常見誤算

**那個 `GPU KV cache size` 日誌行不是容量承諾**【原始碼】：

```python
# vllm/v1/core/kv_cache_utils.py:1871
return int(max_concurrency * max_model_len), max_concurrency
```

它字面上就是 `max_concurrency × max_model_len`，**派生的最壞情況乘積**。maintainer 原話：`That log message simply shows a theoretical upper bound ... KV cache blocks are allocated lazily and incrementally, not all at once.`

**按危害排序的誤算清單**：

1. **activation / CUDA graph 顯存沒算進去**（vLLM 現已預設開啟估算並列印等效換算）
2. **profiling 看不到的臨時 buffer**：KDA 的 chunked-scan buffer 隨 `max_num_batched_tokens` 線性增長、在 forward 內部瞬時分配，**啟動 profiling 覆蓋不到**；超出某個 chunk size 後引擎會在**服務中途**死掉
3. **把 `max_model_len × 併發` 當 KV 需求**
4. **preemption 在 OOM 之前先毀掉 p99**：讀 `vllm:num_preemptions`，不要從日誌推斷
5. **hybrid attention 模型給滑窗層分配了全上下文 KV**（修復後 SWA 層改用 `SlidingWindowSpec`）
6. **`max_num_seqs` 一職兩用，且等待佇列無界**（`--max-num-queued-tokens` 預設關閉）
7. **block size 在 hybrid 模型上被逼到病態值**：GLM-5.3-Flash 上曾出現 block size 7808，一個 12-token 的 prompt 占掉 32.9% 的池
8. **按 576 B/token 算 MLA 容量**（實際打包是 656 B，少算 14%）

**一條最好的單變數對照**（RTX 4090 / Qwen3-8B bf16）【提交者自測】：`max_num_batched_tokens` 從 2048 提到 8192，KV 池縮 10%，**p99 TTFT 漲 71%**（23.9s → 40.8s），goodput 從 54.7% 掉到 46.2%，而總吞吐不變。

---

## 三、擴展賬：Kimi-K3 從 16 卡到 64 卡

§1.4 那張擴展表看著像「加卡」，但它生成的每一條命令都把**單 replica 的形狀鎖死在 8 卡**。這一章逐軸算清楚擴到 64 卡到底買到了什麼。結論裡最反直覺的一條是：**每卡的 KV 容量三檔完全一樣**。

**這一章只有 Kimi-K3。** SGLang cookbook 的 16–64 卡大規模預設目前只給了這一個模型：`configs/` 下帶「Cluster Size」面板的只有 `kimi-k3.jsx`。DeepSeek-V4 最大的 recipe 停在 2 節點 TP=16（`DeepSeek-V4.mdx:174`），沒有可比的擴展表。下面的演算法對任何 MLA + MoE 模型都成立，但只有 K3 有可核對的官方數字。

### 3.1 形狀鎖死在 8 卡

預設的生成邏輯在 `kimi-k3.jsx:975-987`，兩行決定一切：

```js
const dp = n / 8;
`--tp-size ${n}`, `--ep-size ${n}`,
...(dp > 1 ? ["--enable-dp-attention", `--dp-size ${dp}`, "--enable-dp-lm-head"] : []),
```

`--tp-size` 和 `--ep-size` 都等於卡數 n，`--dp-size` 等於 `n/8`。於是 attention-TP 寬度 = `tp/dp` **恆等於 8**：

| GPUs | `--tp-size` / `--ep-size` | `--dp-size` | **attnTP = tp/dp** | 專家/GPU（896/n） | B300 節點數 |
| ---- | ------------------------- | ----------- | ------------------ | ----------------- | ----------- |
| 16   | 16                        | 2           | **8**              | 56                | 2           |
| 32   | 32                        | 4           | **8**              | 28                | 4           |
| 64   | 64                        | 8           | **8**              | 14                | 8           |

8 正好是 B300 的單節點卡數。cookbook 把設計意圖寫明瞭：`The per-step KDA all-reduce stays within one 8-GPU B200/B300 node`（`Kimi-K3.mdx:397`）。KDA 每步都要 all-reduce，把 attnTP 釘在節點寬度上，這條延遲敏感的集合通訊就永遠不跨網路。

代價是**擴展只加副本，不加寬度**。下面三節逐軸展開。

### 3.2 權重：唯一隨 n 縮小的軸

K3 的 geometry 是固定的：`hidden_size = 7168`（`kimi_k3/attn_res.py:22` 等多處硬編碼），routed expert 走 latent 3584（`kimi_k3.py:661-663`），896 routed expert + 2 shared（HF config `num_shared_experts=2`），top-k = 16。checkpoint 是 MXFP4，**約 1.5 TB**（`test/registered/amd/accuracy/mi35x/test_kimi_k3_eval_mi35x.py:19-21`）。

按逐投影形狀累加，attention + embedding 部分約 **16.3 GB**（非官方數字，估算），剩下 ≈ 1.474 TB 全是專家。**專家按 EP = n 切，非專家按 attnTP = 8 切**：

| GPUs | 專家/GPU | 專家權重 | 非專家權重 | **權重/GPU** |
| ---- | -------- | -------- | ---------- | ------------ |
| 8    | 112      | 184.2 GB | 2.0 GB     | **186.2 GB** |
| 16   | 56       | 92.1 GB  | 2.0 GB     | **94.1 GB**  |
| 32   | 28       | 46.1 GB  | 2.0 GB     | **48.1 GB**  |
| 64   | 14       | 23.0 GB  | 2.0 GB     | **25.1 GB**  |

n=8 那一行可以校驗：AMD 的 perf 測試註釋寫 `roughly 192 GB of the 288 GB on each of the 8 GPUs`（`test/registered/amd/accuracy/mi35x/test_kimi_k3_eval_mi35x.py:19-21`），模型算出 186.2 GB，差 3%。

**非專家那 2.0 GB 是地板**：再擴副本也壓不掉，因為它只切 8 份。16 卡時它佔權重的 2%，64 卡時佔 8%。

### 3.3 KV 與 state：一個位元組都不變

這是全篇最反直覺的一條。K3 的 KV 几何在 SGLang 計算器原始碼裡寫死了（`_kimi_k3_mamba_ratio_calculator.jsx:117-126`）：

```text
MLA: 24 層 × (512 + 64) × 1 B   = 13,824 B/token        （FP8）
KDA: 69 層 × (96/8 × 128 × 128 × 2 B + 3×3 × 96/8 × 128 × 2 B)
                                = 27.69 MiB/slot         （bf16, attnTP=8）
```

每請求佔幾個 slot 由**快取策略**決定，與 n 無關【原始碼】：`kv_cache_configurator.py:167-172` 給出 `base = 3`，`extra_buffer_lazy` + overlap scheduler 給 `+1`，共 **4 個 slot**。預設釘的正是 `--mamba-radix-cache-strategy extra_buffer_lazy`。

| 項                         | 16 卡          | 32 卡  | 64 卡  |
| -------------------------- | -------------- | ------ | ------ |
| 每卡 MLA KV                | 13,824 B/token | **同** | **同** |
| 每卡 KDA state             | 27.69 MiB/slot | **同** | **同** |
| **每請求 state（4 slot）** | **110.8 MiB**  | **同** | **同** |

單請求總賬（FP8 KV + bf16 state），三檔共用同一組數字：

| 上下文 | KV        | state     | **合計**       |
| ------ | --------- | --------- | -------------- |
| 8K     | 108.0 MiB | 110.8 MiB | **218.8 MiB**  |
| 32K    | 432.0 MiB | 110.8 MiB | **542.8 MiB**  |
| 128K   | 1728 MiB  | 110.8 MiB | **1838.8 MiB** |

記憶體怎麼分給這兩個池也是固定的【原始碼】，見 `kv_cache_configurator.py:2493-2497`：

```text
mamba_budget = total_rest_memory × r / (1 + r)      # r = --mamba-full-memory-ratio
```

按計算器預設 L = 11264 算，Peak Throughput 的 r ≈ 0.75（state 拿 43%，KV 拿 57%）。

**開不開 DCP 只動 KV 那一半。** Peak Throughput 不開 DCP，於是這 432 MiB 在 attnTP 組內**被複制 8 份**；KDA state 按頭分片、不復制。一個 32K 請求的叢集實佔 = MLA KV 432 MiB × 8 份 + KDA state 110.8 MiB/卡 × 8 卡 ≈ **4.2 GiB**（4,342 MiB）。Peak Capacity 的 `--dcp-size 8` 把這 8 份去重，state 的 110.8 MiB/卡一分不動。所以那一檔的收益（官方口徑：**同等引擎吞吐下併發 +72%，代價 ITL 約 1.8×**）全部來自 KV 去重，而 state 池仍是併發天花板——cookbook 的原話是 `The KDA state pool is the concurrency ceiling`（`Kimi-K3.mdx:391`）。

### 3.4 通信：唯一變貴的軸

**不變的那半**：KDA 的 per-step all-reduce 永遠在 attnTP = 8 的組內，就是一個 B300 節點。從 16 卡擴到 64 卡，這條一個字不變。

**變貴的那半**：MoE all-to-all。一個 token 的 top-k = 16 個專家散落在 n 個 rank 上，期望命中的不同 rank 數是 `n × (1 − (1 − 1/n)^16)`：

| GPUs | 期望目的 rank | 跨節點佔比 | **跨節點目的 rank** |
| ---- | ------------- | ---------- | ------------------- |
| 16   | 10.3          | 50%        | 5.15                |
| 32   | 12.8          | 75%        | 9.56                |
| 64   | 14.3          | 87.5%      | **12.47**           |

跨節點的 fan-out 從 5.15 漲到 12.47，**2.4×**。這筆開銷不體現在權重表，也不體現在 KV 表里。

⚠️ **一個前提要說清**：上表假設專家在 rank 間隨機放置。若按 EPLB 連續/分組放置，一個 token 的 16 個專家在 16 卡和 32 卡下可能全落在 1 個 rank 內（`ceil(16 / (896/n))` = 1），64 卡才變 2 個。**放置策略的影響比 n 本身還大**。上表應視為隨機放置下的上界。

### 3.5 三個不能照搬的結論

**①「64 卡 ~3K tok/s per GPU」不是這個預設的成績。** cookbook 明說它屬於另一個形狀：`--dp-size` = 卡數、attention-TP 1、必須 288 GB 卡、radix 強制關閉，並且 `is not a preset`（`Kimi-K3.mdx:401`）。拿它當 64 卡預設的預期會嚴重高估。

**② 別給 DCP 疊 EP a2a。** `Don't use EP with an a2a backend: a2a buffers reclaim the KV that DCP buys`（`Kimi-K3.mdx:191`）。兩者搶的是同一塊顯存。

**③ 絕對併發數本文不給。** 從 n=8 反推時可以看到：靜態預算裡除了權重還有約 **36 GB 的非權重預留**（CUDA graph + activation）。純用 state 池反算 B300 1×8 Balanced 公布的 101 併發會差 3.7 倍，補上這個預留才自洽。而這個預留依賴 batch 和 graph 捕獲配置，倉庫裡沒有可引用的數字。所以 §3.2 那張表的「權重/GPU」是下限，能分給兩個池的還要再扣掉它。

---

## 四、官方調優方法

### 4.1 SGLang：看日誌裡的三個數

**啟動後看 `available_gpu_mem`**【SGLang】：

```text
[2025-08-11 17:17:03] max_total_num_tokens=665690, chunked_prefill_size=8192,
max_prefill_tokens=16384, max_running_requests=4096, context_len=65536, available_gpu_mem=13.50 GB
```

官方判據：

- **5–8 GB = 合適**（留給 activations 和 CUDA graph）
- **10–20 GB = 太高**，調大 `--mem-fraction-static` 把記憶體給 KV
- **太低 = 有 OOM 風險**，調小

`mem_fraction_static = (模型權重 + KV cache pool) / GPU 顯存容量`。官方給的實操法：**以 0.01 為步長往上加，直到你的負載出現 OOM**。

**穩態看 `token usage` 和 `#queue-req`**【SGLang】：

```bash
Decode batch. #running-req: 233, #token: 370959, token usage: 0.82, cuda graph: True, gen throughput (token/s): 4594.01, #queue-req: 317
```

- `#queue-req` 健康區間 **100–2000**。**頻繁看到 0 = 客戶端提交太慢**
- **`token usage > 0.9` 才算利用得好**。若 < 0.9 且 `#queue-req > 0`，說明服務端太保守，把 `--schedule-conservativeness` 降到 **0.3**
- 反之若頻繁看到 `KV cache pool is full. Retract requests.`，把 `--schedule-conservativeness` 提到 **1.3**。**每分鐘約 1 次是可以接受的**

**OOM 的三條處置（官方）**：

- prefill 時 OOM → `--chunked-prefill-size` 降到 **4096 或 2048**（代價：長 prompt 的 prefill 變慢）
- decode 時 OOM → 降 `--max-running-requests`
- 都可以再降 `--mem-fraction-static` 到 **0.8 或 0.7**（代價：限制併發上限、降峰值吞吐）

**CUDA graph 上限**：預設只對小 batch（<160 或 256）開。大 TP 的模型上 CUDA graph 到 512 或 768 仍有用，可調大 `--cuda-graph-max-bs-decode`，但要同時降 `--mem-fraction-static`。

**`--mem-fraction-static` 的實踐取值**：SGLang 在 B300 上給 VLM 的保守起點是 **0.82**（`raise it toward 0.85 if startup reports insufficient memory`）；大 MoE 吞吐檔用 0.88–0.92。DSv4 的 DSpark 路徑明確要 `Keep --mem-fraction-static 0.90 to leave enough headroom for the batch-256 verify graph`。

### 4.2 vLLM：preemption 的四條處置

出現這條 warning 說明 KV 不夠【vLLM】：

```bash
WARNING ... Sequence group 0 is preempted by PreemptionMode.RECOMPUTE mode
because there is not enough KV cache space. This can affect the end-to-end
performance. Increase gpu_memory_utilization or tensor_parallel_size to
provide more KV cache memory.
```

**官方給的四個動作**：

1. 提高 `gpu_memory_utilization`
2. 降低 `max_num_seqs` 或 `max_num_batched_tokens`
3. 提高 `tensor_parallel_size`（切分權重騰出顯存，但同步開銷上升）
4. 提高 `pipeline_parallel_size`（層分到多卡，但有延遲懲罰）

**監控**：`vllm:num_preemptions`。V1 的預設 preemption 模式是 `RECOMPUTE` 而非 `SWAP`。

### 4.3 chunked prefill 的調參

vLLM V1 **預設開啟** chunked prefill。官方給的調參方向【vLLM】：

- **調小**（如 2048）→ ITL 更好（prefill 更少打斷 decode）
- **調大** → TTFT 更好
- **官方推薦**：`For optimal throughput, we recommend setting max_num_batched_tokens > 8192 especially for smaller models on large GPUs`

---

## 五、上線前必測項

| #   | 項                                                            | 理由                                                                                                                                                                            |
| --- | ------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ①   | **KV 量化的 ≥100K needle retrieval**                          | vLLM #56700 原話：`Wrong interpretation passes short-prompt smoke tests and only fails at ≥100K needle retrieval — silent numerical corruption.` **短 prompt 冒煙測試等於沒測** |
| ②   | **物理核數 ≥ `2 + N`**（多 DP 用官方公式）                    | vLLM 官方：CPU 不足會 `significantly degrade throughput and latency`                                                                                                            |
| ③   | **自建映象顯式加入 `10.3` arch**                              | 官方映象的 `TORCH_CUDA_ARCH_LIST` 不含它                                                                                                                                        |
| ④   | **`--disaggregation-decode-extra-slots` 顯式設定**（若配 PD） | 不設則 32 請求以上預設歸零                                                                                                                                                      |
| ⑤   | **跨實例共享 KV 時統一 `PYTHONHASHSEED`**                     | vLLM 官方：否則同樣內容算出不同檔名                                                                                                                                           |
| ⑥   | **精度驗收繫結 kernel backend 版本**                          | 同一份 NVFP4 權重換 backend 差約 1 分 GSM8K                                                                                                                                     |
| ⑦   | **啟動後確認 `available_gpu_mem` 落在 5–8 GB**                | SGLang 官方判據                                                                                                                                                                 |
| ⑧   | **長上下文任務的忠實度迴歸**                                  | 獨立論文：INT4 KV 下 `over 90% of faithfulness changes are negative, i.e., accuracy metrics are blind to this regression`                                                       |

**另外兩條來自 cookbook 的提醒**：

- **B300 1×8 上只有 `Unified` 的 Low-Latency 與 Balanced 兩格是 Verified**，其餘全部標 `Final Verification In Progress`：「treat those as starting points to verify」
- **大規模預設沒有一個在最終權重上跑過完整 serving round**：`the constants derive from measured single- and dual-node rounds plus a 64-GPU sweep. Validate throughput and accuracy on your workload before committing a fleet.`

---

## 附：三條收口判斷

1. **KV 量化只到 FP8。** `fp8_e4m3` 是 SGLang 官方明寫的推薦值；FP4 KV 官方標為實驗性，且 aime25 上有 0.75 → 0.35 的實測反例。
2. **MLA 模型上用 DP，不用 TP。** 兩家官方都寫明 TP > 1 時 MLA KV 被複制；SGLang 的 Deep PP 實測差距達 2.75 倍。
3. **第一槓杆是模型選型。** MLA 與 Qwen3-235B 的 GQA 在同精度（BF16）下 per-token KV 差約 2.8 倍（68.6 KB vs 188 KB）；若 MLA 按 FP8 打包（約 40 KB）計，差距拉大到近 5 倍——量級大於任何量化手段。

---

## 相關閱讀

- [KV Cache 技術體系](../kv_cache/README.md)——本文只講 B300 上的配置實踐，壓縮、淘汰、解除安裝的機制原理見該目錄
- [顯存估算](../memory_calc/README.md)——容量測算的方法與指令碼
- [vLLM 助力 DeepSeek 吞吐量飆升 5 倍](../vllm/hardware_optimization/deepseek_blackwell_wide_ep.md)——WideEP、NVFP4/FP8 與 Weight Offloading v2 的原理拆解，本文 §1.5 的並行策略是它在部署側的另一面
- [把 KV Cache 壓縮推到極限：DeepSeek-V4.1-Flash 技術報告精讀](../kv_cache/07_kv_compression/06-deepseek-v41-flash.md)——模型架構側的 KV 壓縮（CSA2、FP4 main KV），與本文的引擎側實踐互補
- [NVIDIA GB300 NVL72 架構解析](../../01_hardware_architecture/superchips/nvidia_gb300.md)——本文用到的顯存口徑在那一篇有完整的拓撲與頻寬背景
- [核心推理最佳化技術深度解析](../reference_design/03-核心推理优化技术深度解析.md)——KV Cache、Continuous Batching、量化等技術的原理層梳理
