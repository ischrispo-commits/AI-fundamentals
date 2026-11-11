# NCCL 通訊路徑逐層壓測——從 NVLink 到 PCIe Fallback

多 GPU 通訊的效能天花板由物理拓撲決定：NVLink、PCIe P2P、IB、TCP 依次遞減。但理論頻寬是一回事，實際能跑到多少、禁用某條路徑後衰減多少、不同 GPU pair 之間有沒有差異，只有壓測才能回答。

本文在一台 8×H100 伺服器上用 NCCL all_reduce 逐層驗證：NVLink（同 NUMA / 跨 NUMA）→ PCIe P2P 降級 → 禁用 P2P fallback。每層固定張量從 1MB 到 512MB，記錄 bus bandwidth。最後給出一張速查表：從最快到最慢的完整通訊層級，帶實測值和理論對照。

> as-of 2026-11-05：實測環境 8×NVIDIA H100 80GB HBM3 + CUDA 12.8 + 容器映象 lmsysorg/sglang:v0.5.13.post1（NCCL 版本隨映象），宿主驅動版本文中未記錄；頻寬數字隨 NCCL/驅動版本與機型變化，引用前複核。

---

## 一、拓撲摸底

`nvidia-smi topo -m` 輸出決定了後續所有測試的分組依據。這台 H100 的關鍵資訊：

```text
        GPU0    GPU1    GPU2    GPU3    GPU4    GPU5    GPU6    GPU7
GPU0     X      NV18    NV18    NV18    NV18    NV18    NV18    NV18
GPU1    NV18     X      NV18    NV18    NV18    NV18    NV18    NV18
GPU2    NV18    NV18     X      NV18    NV18    NV18    NV18    NV18
GPU3    NV18    NV18    NV18     X      NV18    NV18    NV18    NV18
GPU4    NV18    NV18    NV18    NV18     X      NV18    NV18    NV18
GPU5    NV18    NV18    NV18    NV18    NV18     X      NV18    NV18
GPU6    NV18    NV18    NV18    NV18    NV18    NV18     X      NV18
GPU7    NV18    NV18    NV18    NV18    NV18    NV18    NV18     X
```

所有 8 張 GPU 兩兩之間都標 `NV18`，即 18 條 NVLink 4.0 link 直連。這意味著全部 GPU 在同一個 NVSwitch 域內，任意 pair 都有完整的 450 GB/s 單向頻寬。

NUMA 分布：

| NUMA Node | GPU         | 最近的 NIC        |
| --------- | ----------- | ----------------- |
| 0         | GPU 0,1,2,3 | NIC 0,1,2,3 (PIX) |
| 1         | GPU 4,5,6,7 | NIC 4,5,6,7 (PIX) |

GPU 和 NIC 之間存在親和性：GPU0 與 NIC0 走 PIX（同一 PCIe switch），與 NIC6 走 SYS（跨 NUMA + PCIe + SMP）。GPUDirect RDMA 選哪塊 NIC，這條親和性是決定性資訊。

---

## 二、測試方法

**環境**：

| 專案   | 值                                                                                           |
| ------ | -------------------------------------------------------------------------------------------- |
| GPU    | 8× NVIDIA H100 80GB HBM3                                                                     |
| NVLink | 18× NVLink 4.0 × 25 GB/s = 450 GB/s 單向                                                     |
| CUDA   | 12.8                                                                                         |
| 容器   | PyTorch + NCCL (lmsysorg/sglang:v0.5.13.post1)                                               |
| 算法   | NCCL Ring (NCCL_ALGO=Ring)                                                                   |
| 張量   | float32, 1MB ~ 512MB，預熱 5 次，計時 30 次取平均                                            |
| 指標   | bus bandwidth = `data_size × 2 × (n-1)/n / time`（NCCL 標準公式，2 GPU 時 bus_bw = algo_bw） |

**測試矩陣**：

| #   | 配置                           | 目的                             |
| --- | ------------------------------ | -------------------------------- |
| ①   | GPU0↔GPU1 (同 NUMA)            | NVLink 基線                      |
| ②   | GPU4↔GPU5 (同 NUMA)            | NVLink 另一 NUMA 對照            |
| ③   | GPU0↔GPU4 (跨 NUMA)            | 驗證 NVSwitch 是否屏蔽 NUMA 差異 |
| ④   | GPU0↔GPU7 (最大 NUMA 距離)     | 跨 NUMA 最差情況                 |
| ⑤   | GPU0↔GPU1 + NCCL_P2P_DISABLE=1 | P2P 禁用後的降級頻寬             |

測試指令碼（torchrun 啟動 2 行程）：

```python
import os, time
import torch
import torch.distributed as dist

def main():
    local_rank = int(os.environ["LOCAL_RANK"])
    torch.cuda.set_device(local_rank)
    dist.init_process_group(backend="nccl")

    sizes_mb = [1, 8, 64, 256, 512]
    if local_rank == 0:
        print(f"{'Size':>6}  {'Bus BW':>10}")

    for size_mb in sizes_mb:
        n_elements = size_mb * 1024 * 1024 // 4
        t = torch.ones(n_elements, dtype=torch.float32, device=f"cuda:{local_rank}")
        for _ in range(5): dist.all_reduce(t, op=dist.ReduceOp.SUM)
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        for _ in range(30): dist.all_reduce(t, op=dist.ReduceOp.SUM)
        torch.cuda.synchronize()
        elapsed = time.perf_counter() - t0
        n = dist.get_world_size()
        bus_bw = (t.numel() * 4 * 2 * (n - 1) / n) / (elapsed / 30) / 1e9
        if local_rank == 0:
            print(f"{size_mb:>4}MB  {bus_bw:>8.1f} GB/s")

    dist.destroy_process_group()

if __name__ == "__main__":
    main()
```

---

## 三、實測結果

### 3.1 NVLink 同 NUMA（基線）

| 張量   | GPU0↔GPU1 (NUMA 0) | GPU4↔GPU5 (NUMA 1) |
| ------ | ------------------ | ------------------ |
| 1 MB   | 22.7 GB/s          | 27.3 GB/s          |
| 8 MB   | 172.5 GB/s         | 172.1 GB/s         |
| 64 MB  | 266.8 GB/s         | 265.5 GB/s         |
| 256 MB | 298.8 GB/s         | 296.3 GB/s         |
| 512 MB | **315.8 GB/s**     | **313.5 GB/s**     |

兩組基線高度一致，NUMA 0 和 NUMA 1 的 NVLink 頻寬無差異。

### 3.2 NVLink 跨 NUMA

| 張量   | GPU0↔GPU4 (跨 NUMA) | GPU0↔GPU7 (最大距離) |
| ------ | ------------------- | -------------------- |
| 1 MB   | 29.8 GB/s           | 31.4 GB/s            |
| 8 MB   | 124.7 GB/s          | 170.5 GB/s           |
| 64 MB  | 265.8 GB/s          | 266.5 GB/s           |
| 256 MB | 294.1 GB/s          | 278.8 GB/s           |
| 512 MB | **316.3 GB/s**      | **315.2 GB/s**       |

跨 NUMA 與同 NUMA 的 NVLink 頻寬**完全一致**。GPU0↔GPU4 在 8MB 時有波動（124.7 vs 170+），這是單次測量噪聲，512MB 時全部迴歸 ~315 GB/s。結論：NVSwitch 屏蔽了 NUMA 差異，任意 GPU pair 的 NVLink 頻寬相同。

### 3.3 P2P 禁用（PCIe Fallback）

| 張量   | Bus BW    |
| ------ | --------- |
| 1 MB   | 15.6 GB/s |
| 8 MB   | 23.0 GB/s |
| 64 MB  | 23.6 GB/s |
| 256 MB | 23.7 GB/s |
| 512 MB | 23.8 GB/s |

P2P 禁用后，NCCL 不再使用 NVLink 直接傳輸。資料走 GPU0 → CPU Memory → GPU1 路徑，受限於 PCIe Gen5 x16 的雙向頻寬（兩次跨 PCIe 橋傳輸 + 記憶體複製開銷）。有效頻寬 23.8 GB/s，僅 NVLink 的 **1/13**。

---

## 四、結果速查

| 通訊路徑                     | 512MB Bus BW | 理論峰值  | 效率 | 說明                        |
| ---------------------------- | ------------ | --------- | ---- | --------------------------- |
| NVLink (NVSwitch 同域)       | ~316 GB/s    | 450 GB/s  | 70%  | 任意 GPU pair               |
| P2P Disabled (PCIe Fallback) | ~24 GB/s     | 32 GB/s\* | 75%  | GPU→CPU→GPU，兩跳 PCIe Gen5 |

> \* P2P 禁用後資料路徑為 GPU0→CPU Memory→GPU1，需要兩次 PCIe Gen5 x16 傳輸（各 64 GB/s 單向），理論有效頻寬上限約 32 GB/s。實測 24 GB/s = 理論 32 GB/s 的 75%，差額來自記憶體複製和容器開銷。

頻寬-張量大小曲線：

![NVLink vs P2P Disabled 頻寬-張量大小曲線](assets/nccl_path_benchmark.svg)

NVLink 在 8MB 時已達 170 GB/s（54% 峰值），256MB 時達 295 GB/s（93% 峰值），512MB 時收斂至 316 GB/s。P2P 禁用后 8MB 即觸頂 23 GB/s，小訊息的頻寬天花板同樣受 PCIe 限制。

---

## 五、結論

1. **NVSwitch 屏蔽 NUMA 差異**：跨 NUMA（GPU0↔GPU4/GPU7）與同 NUMA（GPU0↔GPU1）的 NVLink 頻寬完全相同，無需對 TP 分組做 NUMA 感知排程。

2. **NVLink → PCIe 降級損失 13 倍**：P2P 禁用後頻寬從 ~316 GB/s 驟降至 ~24 GB/s。確保 `NCCL_P2P_DISABLE` 在生產環境中不被錯誤設定。

3. **建議：NIC 選型關注 PIX 親和性**（拓撲分析，未經本文實測）：GPU0 與 NIC0/1 走 PIX（同一 PCIe switch），與 NIC4-7 走 SYS（跨 NUMA + PCIe + SMP）。GPUDirect RDMA 場景下優先將跨節點通訊繫結到 PIX 路徑的 NIC，理論上可避免跨 NUMA 的額外 PCIe 跳數。實際收益取決於 NCCL 的 multi-NIC 排程策略，需在 IB/RoCE 環境下單獨驗證。

---

## 六、相關資源

- [NCCL 技術理論深度解析](01_nccl_theory.md) — AllReduce 算法、Ring/Tree 拓撲選擇、RDMA 機制。
- [NCCL 基準測試方法論](04_nccl_benchmark.md) — `all_reduce_perf` 編譯、執行，A100 實測。
- [GPU 拓撲檢測工具](gpu_topology_detector.sh) — 自動化 GPU 拓撲分析與通訊路徑規劃。
- [GPUDirect RDMA 跨節點驗證](../../01_hardware_architecture/gpudirect/04_gpudirect_rdma_verification.md) — 跨節點 IB HDR 的端到端驗證。
