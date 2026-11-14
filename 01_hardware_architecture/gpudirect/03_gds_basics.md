# GPU Direct Storage (GDS) 基礎

> GDS 是 GPUDirect 家族的儲存成員，允許 GPU 透過 PCIe 直接讀寫 NVMe 儲存，繞過 CPU 記憶體中轉。基於 RTX 5090 + CUDA 12.8 (GDS 1.13.1) 環境。

---

## 1. GPUDirect 家族全景

| 技術                  | 解決的問題      | 物理路徑               |
| --------------------- | --------------- | ---------------------- |
| **GPUDirect P2P**     | GPU↔GPU 直通    | PCIe / NVLink          |
| **GPUDirect RDMA**    | GPU↔網卡 直通   | PCIe + InfiniBand/RoCE |
| **GPUDirect Storage** | GPU↔NVMe 直通   | PCIe + NVMe            |
| **GPUDirect Video**   | GPU↔采集卡 直通 | PCIe                   |

GDS 是最晚加入的成員 (CUDA 11.4+)。它解決一個具體問題：訓練資料從 NVMe 載入到 GPU 時，傳統路徑是 `NVMe → CPU RAM → GPU`，GDS 是 `NVMe → GPU`，省掉 CPU 中轉。

```text
傳統:   NVMe ──PCIe──▶ CPU RAM ──PCIe──▶ GPU VRAM   (2 次 PCIe 傳輸)
GDS:    NVMe ──PCIe──────────▶ GPU VRAM              (1 次 PCIe 傳輸)
```

**為什麼這事重要？** 大模型訓練的 checkpoint 檔案動輒數百 GB。傳統路徑下，每個位元組都要：NVMe DMA → CPU 記憶體 → CPU memcpy → pinned buffer → GPU DMA。CPU 全程參與記憶體複製，而 GPU 的 PCIe 頻寬（~56 GB/s）可能被 CPU 記憶體頻寬（~100 GB/s DDR5）限制到一半。GDS 讓 NVMe 控制器直接透過 PCIe 把資料 DMA 到 GPU VRAM——GPU 的 GDDR7 控制器接收資料，不需要 CPU 側的中間人。不僅少了一次 PCIe 穿越，還釋放了 CPU 做更有意義的計算。

---

## 2. 前置條件

```bash
# 1. CUDA 11.4+
nvcc --version

# 2. GDS 包安裝
ls /usr/local/cuda/gds/README

# 3. cuFile 庫存在
ls /usr/local/cuda/targets/x86_64-linux/lib/libcufile.so*

# 4. NVMe 驅動器
lsblk | grep nvme
# 預期: 至少有一個 nvmeXnY 裝置

# 5. nvidia-fs.ko 核心模組
lsmod | grep nvidia_fs
# Legacy 模式 (pre-CUDA 12.8): 必須 + MOFED 補丁 NVMe 驅動
# Modern 模式 (CUDA 12.8+ + Linux ≥ 6.2): 可選，上游 pci_p2pdma 替代

# 6. 硬件/系統前提條件
# - ACS 旁路: PCIe Switch 下行埠關閉 ACS 轉發限制
# - IOMMU=pt: 核心啟動參數 iommu=pt (或 intel_iommu=pt / amd_iommu=pt)
# - O_DIRECT: 檔案開啟必須使用 O_DIRECT 標誌
```

### 2.1 本環境確認

```bash
ls /sys/block/ | grep nvme
# nvme0n1  nvme1n1  nvme2n1    ← 3 塊 NVMe 塊裝置

cat /usr/local/cuda/gds/README | head -1
# GDS Version: 1.13.1

ls /usr/local/cuda/targets/x86_64-linux/lib/libcufile.so*
# libcufile.so  libcufile_rdma.so  ← cuFile + RDMA 支持
```

> GDS 要求 NVMe 格式化為檔案系統並掛載（如 ext4/xfs + `mount`），僅作為塊裝置存在 (`/dev/nvme*`) 無法直接使用 `cuFileRead`。

---

## 3. cuFile API 基礎

GDS 透過 `libcufile` 暴露 API，核心流程：

```c
#include <cufile.h>

// 1. 開啟 NVMe 文件 (標準 POSIX open，需 O_DIRECT)
int fd = open("/mnt/nvme/data.bin", O_RDONLY | O_DIRECT);

// 2. 註冊檔案為 GPU 可直接訪問
CUfileDescr_t desc = {};
desc.type = CU_FILE_HANDLE_TYPE_OPAQUE_FD;
desc.cookie = (void*)(uintptr_t)fd;
CUfileHandle_t fh;
cuFileHandleRegister(&fh, &desc);

// 3. 註冊 GPU buffer
cuFileBufRegister(gpu_buffer, size, 0);

// 4. GPU 直接讀取 NVMe（非同步）
cuFileRead(fh, gpu_buffer, size, offset, 0);

// 5. 清理
cuFileBufDeregister(gpu_buffer);
cuFileHandleDeregister(fh);
close(fd);
```

編譯：

```bash
nvcc -I/usr/local/cuda/include \
     -L/usr/local/cuda/targets/x86_64-linux/lib \
     -lcufile \
     -o gds_read gds_read.cu
```

---

## 4. 效能對比：傳統 vs GDS

| 路徑             | PCIe 穿越次數 | 有效頻寬  | CPU 占用      |
| ---------------- | ------------- | --------- | ------------- |
| NVMe → CPU → GPU | 2             | ~½ 理論值 | 高 (memcpy)   |
| NVMe → GPU (GDS) | 1             | ~理論值   | 低 (DMA only) |

但由於 PCIe 頻寬共享（GPU 和 NVMe 通常在同一 PCIe root complex 下），實際加速取決於拓撲。如果 NVMe 和 GPU 連線到同一 PCIe switch 且支持 P2P，加速最明顯。

---

## 5. 常見限制

| 限制                   | 說明                                                                         |
| ---------------------- | ---------------------------------------------------------------------------- |
| **NVMe 必須直接掛載**  | 網路儲存 (NFS/Ceph) 不支持 GDS                                               |
| **檔案對齊**           | 偏移和大小需對齊到 4 KB                                                      |
| **nvidia-fs 核心模組** | Legacy (pre-CUDA 12.8) 必須 + MOFED 補丁 NVMe 驅動；Modern (CUDA 12.8+) 可選 |
| **消費級 GPU**         | 支持 GDS 但效能低於資料中心 GPU（BAR1 窗口限制）                             |
| **PCIe topology**      | GPU 和 NVMe 需在同一 PCIe 根匯流排段下且 P2P 可達                              |

---

## 6. 適用場景

| 場景                   | GDS 適用性  | 說明                        |
| ---------------------- | ----------- | --------------------------- |
| 大模型 checkpoint 載入 | ✅ 強推薦   | 數十 GB 檔案直接載入到 GPU  |
| 訓練資料流式讀取       | ✅ 推薦     | 繞過 CPU RAM 中轉           |
| KV Cache 磁碟解除安裝      | ✅ 適用     | 與 LMCache 等方案配合       |
| 小檔案隨機讀取         | ❌ 不適用   | 每次 open/register 開銷過大 |
| 已有 page cache 熱點   | ⚠️ 可能更慢 | 繞過 cache 反而增加延遲     |

---

## 7. 快速測試指令碼

```bash
cat > test_gds.sh << 'EOF'
#!/bin/bash
echo "=== GDS Environment Check ==="
echo "CUDA: $(nvcc --version 2>/dev/null | grep release)"
echo "GDS:  $(cat /usr/local/cuda/gds/README 2>/dev/null | head -1)"
echo "NVMe devices:"
lsblk 2>/dev/null | grep nvme || echo "  No NVMe found"
echo "libcufile:"
ls /usr/local/cuda/targets/x86_64-linux/lib/libcufile.so* 2>/dev/null || echo "  Not found"
echo "nvidia-fs module:"
lsmod 2>/dev/null | grep nvidia_fs || echo "  Not loaded (optional)"
EOF
chmod +x test_gds.sh
./test_gds.sh
```

---

## 參考

- [NVIDIA GPUDirect Storage Documentation](https://docs.nvidia.com/gpudirect-storage/)
- [cuFile API Reference](https://docs.nvidia.com/gpudirect-storage/api-reference-guide/)
- [GPUDirect RDMA 技術詳解](01_gpudirect_technology.md)
- [GPUDirect P2P 技術詳解](02_gpudirect_p2p.md)
- [PCIe P2PDMA 技術介紹](../pcie/02_p2pdma_technology.md)
- [GPU 記憶體管理 — GDS 原理與排查](../../02_gpu_programming/02_cuda/12_gpu_memory_management.md)（§5: GPUDirect Storage 的 DMA 鏈條與 cuFile err=5030 排查）
