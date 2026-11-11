# GPU 裝置屬性查詢：寫 Kernel 前先查這張卡的並行上限

寫 CUDA 程式碼之前，你有兩個選擇：憑經驗設 Grid/Block 大小，或者先查一下這張卡到底有幾個 SM、每個 Block 最多放多少執行緒、共享記憶體多大。選前者可能出事：Kernel 在 A100 上跑得好好的，換到 T4 上直接 `cudaLaunch` 報錯，因為 T4 的 `maxThreadsPerBlock` 是 1024，你寫了 2048。

GPU 裝置查詢回答的是一個具體的問題：這段 Kernel 在這張卡上最多能怎麼並行。本文從 Runtime API 和 Driver API 兩條路徑切入，最後落到一張速查表，只列和 Kernel 設計直接相關的那幾個參數。

---

## 一、兩套 API：Runtime vs Driver

CUDA 提供了兩套查詢介面，側重不同：

| API 層      | 入口函式                    | 典型用途                                 |
| ----------- | --------------------------- | ---------------------------------------- |
| Runtime API | `cudaGetDeviceProperties()` | 應用開發首選，一行呼叫拿到所有屬性       |
| Driver API  | `cuDeviceGetAttribute()`    | 需要逐屬性查詢的場景（如中介軟體、框架層） |

Runtime API 返回一個 `cudaDeviceProp` 結構體，幾十個欄位一次性填好。Driver API 按需逐項查詢，更靈活但更繁瑣。兩者的資訊源相同（驅動層），不存在精度差異。

NVIDIA 官方示例中，`deviceQuery` 用 Runtime API，`deviceQueryDrv` 用 Driver API。原始碼在 [cuda-samples](https://github.com/NVIDIA/cuda-samples) 的 `Samples/1_Utilities/` 下。

---

## 二、Runtime API：一行拿到全部屬性

```cpp
#include <cuda_runtime.h>

int deviceCount;
cudaGetDeviceCount(&deviceCount);

for (int i = 0; i < deviceCount; i++) {
    cudaDeviceProp prop;
    cudaGetDeviceProperties(&prop, i);
    printf("Device %d: %s (CC %d.%d, %d SMs, %zu MB global mem)\n",
           i, prop.name, prop.major, prop.minor,
           prop.multiProcessorCount,
           prop.totalGlobalMem / (1024 * 1024));
}
```

編譯：

```bash
nvcc -o device_query device_query.cu
./device_query
```

以 Tesla T4 為例，關鍵輸出：

```text
Device 0: "Tesla T4"
  CUDA Capability:      7.5
  SMs:                  40
  CUDA Cores:           2560  (40 × 64)
  Global Memory:        14931 MB
  Max Threads/Block:    1024
  Max Threads/SM:       1024
  Shared Mem/Block:     48 KB
  Registers/Block:      65536
  Warp Size:            32
  Max Grid Dim:         (2147483647, 65535, 65535)
  Max Block Dim:        (1024, 1024, 64)
  Memory Bus Width:     256-bit
  ECC:                  Enabled
  Concurrent Kernels:   Yes
  Concurrent Copy+Exec: Yes (3 copy engines)
  P2P Access:           Yes (GPU0↔GPU1)
```

---

## 三、哪些參數直接影響 Kernel 設計？

不是每個欄位都需要關注。下面這 5 個決定了一段 Kernel 能否啟動、能啟動多大：

| 參數               | 字段                  | 含義                      | 踩坑場景                                                                                |
| ------------------ | --------------------- | ------------------------- | --------------------------------------------------------------------------------------- |
| **計算能力**       | `major`, `minor`      | 決定了哪些 CUDA 特性可用  | 編譯時 `-arch=sm_80` 的程式碼無法在 CC 7.5 上執行                                         |
| **SM 數量**        | `multiProcessorCount` | 多少個 SM 可並行          | 決定了 Grid 的並行度上限；SM 數太少的卡上小 Grid 利用率極低                             |
| **最大執行緒/Block** | `maxThreadsPerBlock`  | Block 維度的硬上限        | 寫了 2048 執行緒/Block，在 T4 (max 1024) 上直接 `cudaLaunch` 失敗                         |
| **共享記憶體/Block** | `sharedMemPerBlock`   | Block 內的高速 Scratchpad | 申請超過 48KB 的 `extern __shared__` 時會報錯（除非配置 `cudaFuncSetAttribute` 調上限） |
| **Warp Size**      | `warpSize`            | 硬體排程單位              | 所有 NVIDIA GPU 都是 32，但 Block Size 不整除 32 會浪費執行緒槽位                         |

其次重要的是決定能跑多快的參數：

| 參數                          | 含義                                                        |
| ----------------------------- | ----------------------------------------------------------- |
| `maxThreadsPerMultiProcessor` | SM 上同時駐留的執行緒數上限 → 決定 Occupancy                  |
| `regsPerBlock`                | Block 可用的暫存器數 → 每個執行緒用太多暫存器，Occupancy 暴跌 |
| `memPitch`                    | 2D 記憶體複製的最大行距                                       |
| `concurrentKernels`           | 是否支持多 Stream 並行執行                                  |
| `deviceOverlap`               | 是否支援計算與資料複製重疊                                  |

其餘參數（紋理維度、表面記憶體對齊等）屬於圖形/影象處理領域，CUDA 計算場景極少用到。

---

## 四、Driver API：按需逐屬性查詢

當不需要全部屬性、只查一兩個值時，Driver API 更高效：

```cpp
#include <cuda.h>

CUdevice device;
int smCount, maxThreadsPerBlock;
cuDeviceGet(&device, 0);
cuDeviceGetAttribute(&smCount, CU_DEVICE_ATTRIBUTE_MULTIPROCESSOR_COUNT, device);
cuDeviceGetAttribute(&maxThreadsPerBlock, CU_DEVICE_ATTRIBUTE_MAX_THREADS_PER_BLOCK, device);
printf("SM count: %d, Max threads/block: %d\n", smCount, maxThreadsPerBlock);
```

編譯時需連結 `-lcuda`：

```bash
nvcc -o device_query_drv device_query_drv.cu -lcuda
```

> Driver API 無需 CUDA Runtime 初始化，在載入 `libcuda.so` 後即可呼叫，適合需要在 `cudaSetDevice` 之前做硬體能力探測的場景（如框架層的裝置篩選）。

---

## 五、速查：從 Kernel 設計視角看裝置屬性

| 你要做的事                 | 查哪個屬性                                 | T4 示例值              |
| -------------------------- | ------------------------------------------ | ---------------------- |
| 確定 Block 最多放多少執行緒  | `maxThreadsPerBlock`                       | 1024                   |
| 確定 Grid 最多放多少 Block | `maxGridSize`                              | (2^31-1, 65535, 65535) |
| 估算最大 Occupancy         | `maxThreadsPerMultiProcessor` / `warpSize` | 32 warps/SM            |
| 靜態共享記憶體上限           | `sharedMemPerBlock`                        | 48 KB                  |
| 動態共享記憶體上限           | `sharedMemPerBlockOptin`                   | 64 KB                  |
| 選 `-arch` 編譯參數        | `major`, `minor`                           | `sm_75`                |
| 判斷是否支援 P2P           | `cudaDeviceCanAccessPeer`                  | —                      |
| 多 Stream 是否真並行       | `concurrentKernels`                        | Yes                    |
| 是否支持 Unified Memory    | `unifiedAddressing` + `managedMemory`      | Yes                    |

---

## 六、相關資源

- [cuda-samples/deviceQuery](https://github.com/NVIDIA/cuda-samples/tree/master/Samples/1_Utilities/deviceQuery)：Runtime API 完整示例
- [cuda-samples/deviceQueryDrv](https://github.com/NVIDIA/cuda-samples/tree/master/Samples/1_Utilities/deviceQueryDrv)：Driver API 完整示例
- [CUDA Runtime API 文件 - cudaGetDeviceProperties](https://docs.nvidia.com/cuda/cuda-runtime-api/structcudaDeviceProp.html)
- [CUDA Driver API 文件 - cuDeviceGetAttribute](https://docs.nvidia.com/cuda/cuda-driver-api/group__CUDA__DEVICE.html)
