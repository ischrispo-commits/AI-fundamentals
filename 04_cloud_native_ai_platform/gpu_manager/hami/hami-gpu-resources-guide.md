# HAMi GPU 資源管理完整指南

本指南面向對 HAMi 有一定了解的技術人員，提供從基礎概念到高階特性的全方位技術說明。

---

## 1. 概述

本文件是 HAMi GPU 資源管理的完整技術指南，涵蓋以下核心內容：

- **資源類型管理**: 詳細介紹 NVIDIA GPU 的四種核心資源類型（`nvidia.com/gpu`、`nvidia.com/gpucores`、`nvidia.com/gpumem`、`nvidia.com/gpumem-percentage`）的定義、特性和使用方法
- **算力分配機制**: 深入解析基於反饋控制的令牌桶演算法實現原理、分配流程和效能影響
- **高階特性**: 包括多種排程策略（binpack、spread、topology-aware 等）、裝置選擇、NUMA 繫結、拓撲感知、MIG 支持、執行時模式選擇等
- **配置管理**: 全局配置、節點級配置和 Pod 級配置的詳細說明
- **故障排查與最佳實踐**: 常見問題診斷、效能最佳化建議、監控告警配置、版本升級指導
- **多廠商支援**: 統一管理 NVIDIA、寒武紀、海光、天數智芯、摩爾執行緒、華為昇騰、沐曦等 7 種廠商的 AI 加速裝置
- **監控與可觀測性**: Prometheus 指標、效能監控、資源使用率跟蹤等

> **注意**: 文件中預設程式碼都是指向 `HAMi` 專案。

### 1.1 獨佔 vs 共享場景

- **獨佔模式 (Exclusive)**

  - **定義**：一個 Pod 獨佔一張或多張物理 GPU 卡。
  - **適用場景**：大型模型訓練（LLM Pretraining/SFT）、高效能運算（HPC）、對延遲極其敏感的推理任務。
  - **優勢**：效能無損耗，無資源爭搶，故障完全隔離。
  - **配置特徵**：申請資源量等於物理卡總量（如 100% 算力 + 100% 顯存）。

- **共享模式 (Sharing/Fractional)**
  - **定義**：多個 Pod 共享同一張物理 GPU 卡，每個 Pod 佔用一部分顯存和算力。
  - **適用場景**：輕量級推理服務、開發/除錯環境（Jupyter Notebook）、小模型微調、CI/CD 流水線。
  - **優勢**：極大提升 GPU 利用率，降低成本，支援靈活的資源配置。
  - **配置特徵**：申請資源量小於物理卡總量。

### 1.2 NVIDIA 共享模式深度對比

針對 NVIDIA GPU，HAMi 提供了三種主要的共享模式。請根據下表選擇最適合的方案：

| **特性**     | **HAMi-core 模式 (預設)**                                           | **MIG 模式 (Multi-Instance GPU)**                           | **MPS 模式 (Multi-Process Service)**                               |
| :----------- | :------------------------------------------------------------------ | :---------------------------------------------------------- | :----------------------------------------------------------------- |
| **隔離級別** | 軟體級 (顯存硬隔離 + 算力時間片限制)                                | 硬體級 (物理隔離的計算單元與顯存)                           | 行程級 (共享 CUDA Context)                                         |
| **硬件要求** | 所有 NVIDIA GPU                                                     | 僅限 Ampere (A100/A30) 及 Hopper (H100/H800) 架構           | 所有 NVIDIA GPU                                                    |
| **顯存隔離** | 安全 (劫持 CUDA API 實現)                                           | 非常安全 (物理分割槽)                                         | 地址空間 Volta+ 起已隔離；顯存容量不隔離                            |
| **算力隔離** | 較好 (基於反饋控制的令牌桶演算法)                                     | 極好 (物理計算單元隔離)                                     | 一般 (共享計算資源，提高併發度)                                    |
| **故障影響** | 單個任務崩潰通常不影響其他任務，但嚴重錯誤可能導致 XID 錯誤影響整卡 | 故障完全隔離                                                | 某個行程崩潰可能導致 MPS Server 重置，影響共享該 Server 的所有行程 |
| **適用場景** | 通用場景，需要靈活切分顯存（如 1GB, 1.5GB）                         | 對隔離性要求極高（多租戶），且接受固定切分規格（如 1g.5gb） | 小算力高併發任務，希望能最大化吞吐量                               |
| **啟用方式** | 預設 (或 `nvidia.com/vgpu-mode: "hami-core"`)                       | `nvidia.com/vgpu-mode: "mig"`                               | `nvidia.com/vgpu-mode: "mps"`                                      |

**模式詳解：**

1. **HAMi-core 模式**：

   - 這是 HAMi 的核心能力，透過攔截 CUDA 呼叫實現。
   - **優點**：切分粒度極其靈活（可以申請 1MB 顯存），支援超賣（如果未開啟嚴格限制），基於反饋控制的令牌桶演算法實現精確的算力限制。
   - **缺點**：算力限制基於時間片，可能有微小的上下文切換開銷。

2. **MIG 模式**：

   - 利用 NVIDIA GPU 的硬體特性將 GPU 物理切分為多個實例。
   - **優點**：提供 QoS 保證的硬體隔離，互不干擾。
   - **缺點**：切分規格固定（如 A100 只能切分為 7 個實例），不夠靈活；不支援舊型號 GPU。

3. **MPS 模式**：
   - NVIDIA 官方提供的多行程服務。
   - **優點**：減少了多個 CUDA Context 切換的開銷，顯著提升小任務併發時的吞吐量；Volta+ 架構下各客戶端地址空間已隔離，但顯存容量預設不隔離（一個行程超用會擠佔整卡共享池）。
   - **缺點**：故障隔離性較差（"一損俱損"風險），某個行程崩潰可能導致 MPS Server 重置，影響共享該 Server 的所有行程。

### 1.3 多廠商異構支援概覽

HAMi 不僅支援 NVIDIA GPU，還透過統一的介面支援多種異構算力裝置。詳細的配置管理方法請參見第 4 章。

- **華為昇騰 (Ascend)**：支持 910A、910B (B2/B3/B4)、310P 系列 NPU 切分與共享。
- **寒武紀 (Cambricon)**：支持思元系列 MLU 加速卡。
- **海光 (Hygon)**：支持深算系列 DCU 加速卡。
- **天數智芯 (Iluvatar)**：支持 CoreX 系列 GPU。
- **摩爾執行緒 (Moore Threads)**：支持 MTT 系列 GPU。
- **沐曦 (MetaX)**：支持 MetaX 系列 GPU。

---

## 2. 資源配置實戰

本章詳細講解 HAMi GPU 資源管理的具體配置方法，涵蓋從基礎資源參數到高階場景化配置的完整實踐指南。

### 2.1 核心資源參數詳解

在 Pod 的 YAML 中，透過 `resources.limits` 申請資源。以下是所有支持的 NVIDIA 資源類型：

| **資源名稱**                   | **描述**             | **取值範圍** | **版本要求** | **備註/衝突處理**                                                 |
| :----------------------------- | :------------------- | :----------- | :----------- | :---------------------------------------------------------------- |
| `nvidia.com/gpu`               | 申請的 **vGPU** 數量 | 正整數       | 所有版本     | **必填**。用於觸發排程。                                          |
| `nvidia.com/gpumem`            | 申請的顯存大小 (MB)  | 正整數       | 所有版本     | **顯存硬限制**。若與 `gpumem-percentage` 同時存在，優先使用此值。 |
| `nvidia.com/gpumem-percentage` | 申請的顯存百分比 (%) | 0-100        | v1.0.1.4+    | 動態適應不同顯存大小的卡。**注意：MIG 模式不支持百分比配置**。    |
| `nvidia.com/gpucores`          | 申請的算力百分比 (%) | 0-100        | v1.0.1.3+    | 限制該容器最多使用多少比例的算力。                                |

> **注意**：`nvidia.com/gpu` 在 Pod 申請時代表“需要的 vGPU 實例數”，而在節點 Capacity 中通常代表“vGPU 的總配額”（取決於配置）。

### 2.2 場景化配置模板

#### 2.2.1 獨佔使用 (Exclusive)

希望完全佔用一張卡，不與其他任務共享。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: exclusive-gpu-pod
spec:
  containers:
    - name: cuda-container
      image: nvidia/cuda:11.0-base
      resources:
        limits:
          nvidia.com/gpu: 1 # 申請 1 個 vGPU
          nvidia.com/gpumem-percentage: 100 # 占用 100% 顯存
          nvidia.com/gpucores: 100 # 占用 100% 算力
```

#### 2.2.2 HAMi-core 共享模式 (Sharing)

一個輕量級推理服務，需要 4GB 顯存和 20% 的算力。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: shared-gpu-pod
  annotations:
    nvidia.com/vgpu-mode: "hami-core" # 顯式指定模式（預設可省略）
spec:
  containers:
    - name: inference-container
      image: pytorch/pytorch:1.9.0-cuda11.1-cudnn8-runtime
      resources:
        limits:
          nvidia.com/gpu: 1
          nvidia.com/gpumem: 4096 # 4096 MB 顯存
          nvidia.com/gpucores: 20 # 20% 算力
```

#### 2.2.3 MIG 模式 (MIG)

申請一個 A100 的 MIG 實例。**注意：MIG 模式必須使用固定規格的顯存配置，不支持百分比配置**。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: mig-pod
  annotations:
    nvidia.com/vgpu-mode: "mig" # 指定使用 MIG 模式
spec:
  containers:
    - name: mig-container
      image: nvidia/cuda:11.0-base
      resources:
        limits:
          nvidia.com/gpu: 1
          nvidia.com/gpumem: 20480 # 必須使用MIG固定規格的顯存大小 (對應 A100 3g.20gb 規格)
```

#### 2.2.4 MPS 模式 (MPS)

適用於小算力高併發任務，希望最大化吞吐量的場景。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: mps-pod
  annotations:
    nvidia.com/vgpu-mode: "mps" # 指定使用 MPS 模式
spec:
  containers:
    - name: mps-container
      image: nvidia/cuda:11.0-base
      resources:
        limits:
          nvidia.com/gpu: 1
          nvidia.com/gpumem: 4096 # 申請 4GB 顯存
          nvidia.com/gpucores: 25 # 申請 25% 算力
```

### 2.3 配置層級管理

HAMi 的配置生效優先順序遵循：**Pod Annotation > Node Annotation > Global ConfigMap**。詳細的配置管理方法請參見第 4 章。

#### 2.3.1 全局配置 (ConfigMap)

透過 `hami-scheduler-device` ConfigMap 管理（`device-config.yaml` 字段）：

| **字段名**                | **預設值** | **描述**                                      |
| :------------------------ | :--------- | :-------------------------------------------- |
| `deviceMemoryScaling`     | `1`        | 顯存超賣比例。>1 表示開啟超賣（實驗性）。     |
| `deviceSplitCount`        | `10`       | 單個 GPU 可同時承載的最大容器數（併發度）。   |
| `defaultMemory`           | `0`        | Pod 未指定顯存時的預設值（0 表示 100%）。     |
| `defaultCores`            | `0`        | Pod 未指定核心時的預設百分比（0 表示 100%）。 |
| `defaultGPUNum`           | `1`        | Pod 未指定 `nvidia.com/gpu` 時的預設數量。    |
| `strictMemoryEnforcement` | `false`    | 是否嚴格限制顯存使用（防止超賣場景下的 OOM）  |

**ConfigMap 配置示例**：

```yaml
# device-config.yaml
deviceMemoryScaling: 1.0
deviceSplitCount: 10
defaultMemory: 0
defaultCores: 0
defaultGPUNum: 1
strictMemoryEnforcement: false
```

#### 2.3.2 節點級配置

節點級配置允許管理員針對特定節點設定排程策略和資源管理規則。

- **啟用 GPU 排程**：為節點新增標籤啟用 HAMi 排程

  ```bash
  kubectl label nodes node1 gpu=on
  ```

- **節點排程策略**：設定節點級別的排程偏好

  ```bash
  # binpack: 儘量將任務集中到已使用的節點，減少碎片
  kubectl annotate node node1 hami.io/node-scheduler-policy=binpack

  # spread: 儘量將任務均勻分佈到不同節點
  kubectl annotate node node1 hami.io/node-scheduler-policy=spread
  ```

- **裝置選擇策略**：限制節點上可使用的裝置類型

  ```bash
  kubectl annotate node node1 nvidia.com/use-gputype="Tesla V100-PCIE-32GB"
  ```

#### 2.3.3 Pod 級配置

Pod 級配置允許開發者在應用層面指定排程和資源使用策略。

- **GPU 排程策略**：強制指定 Pod 的排程行為

  ```yaml
  apiVersion: v1
  kind: Pod
  metadata:
    name: example-pod
    annotations:
      hami.io/gpu-scheduler-policy: "spread" # 或 "binpack"
  spec:
    # ...
  ```

- **裝置類型偏好**：指定 Pod 需要的特定裝置型號

  ```yaml
  annotations:
    nvidia.com/use-gputype: "Tesla V100-PCIE-32GB"
  ```

- **GPU 模式選擇**：顯式指定使用的 vGPU 模式

  ```yaml
  annotations:
    nvidia.com/vgpu-mode: "hami-core" # 或 "mig", "mps"
  ```

---

## 3. 核心資源類型深度解析

### 3.1 nvidia.com/gpu

#### 3.1.1 定義

`nvidia.com/gpu` 是用於宣告 Pod 所需物理 GPU 數量的資源類型。

#### 3.1.2 特性

- **必需性**: 必需的資源宣告，用於觸發 GPU 排程
- **取值範圍**: 正整數（1, 2, 3...）
- **用途**: 指定 Pod 需要多少個物理 GPU 裝置
- **排程作用**: HAMi 排程器根據此值進行 GPU 裝置分配

#### 3.1.3 程式碼實現

**1. 資源請求解析**：

在 `pkg/device/nvidia/device.go` 的 `GenerateResourceRequests` 函式中：

```go
// GenerateResourceRequests 解析容器資源請求，生成裝置請求結構體
// 參數: ctr - 容器物件，包含資源限制和請求
// 返回值: device.ContainerDeviceRequest - 裝置請求結構體
func (dev *NvidiaGPUDevices) GenerateResourceRequests(ctr *corev1.Container) device.ContainerDeviceRequest {
    // 獲取 nvidia.com/gpu 的值，優先從 Limits 獲取，其次從 Requests 獲取
    v, ok := ctr.Resources.Limits[resourceName]
    if !ok {
        v, ok = ctr.Resources.Requests[resourceName]
    }
    if ok {
        if n, ok := v.AsInt64(); ok {
            return device.ContainerDeviceRequest{
                Nums: int32(n),      // 請求的 GPU 數量
                Type: resourceName,   // 資源類型
                // ... 其他字段
            }
        }
    }
    // 如果沒有找到資源請求，返回空結構體
    return device.ContainerDeviceRequest{}
}
```

**2. 排程分配**：

在 `Fit` 函式中，排程器會尋找滿足數量要求的裝置：

```go
// pkg/device/nvidia/device.go
// Fit 函式檢查裝置列表是否滿足容器裝置請求
// 參數: devices - 裝置使用情況列表, request - 容器裝置請求, pod - Pod物件, nodeInfo - 節點資訊, allocated - 已分配裝置
// 返回值: bool - 是否滿足請求, map[string]device.ContainerDevices - 分配的裝置對映, string - 失敗原因
func (nv *NvidiaGPUDevices) Fit(devices []*device.DeviceUsage, request device.ContainerDeviceRequest, pod *corev1.Pod, nodeInfo *device.NodeInfo, allocated *device.PodDevices) (bool, map[string]device.ContainerDevices, string) {
    // ...
    // 檢查是否需要拓撲感知排程策略
    needTopology := util.GetGPUSchedulerPolicyByPod(device.GPUSchedulerPolicy, pod) == util.GPUSchedulerPolicyTopology.String()
    // 從後向前遍歷裝置列表（最佳化分配策略）
    for i := len(devices) - 1; i >= 0; i-- {
        dev := devices[i]
        // ... 檢查健康狀態 / 裝置類型 / UUID / 顯存 / 核心等 ...

        tmpDevs[request.Type] = append(tmpDevs[request.Type], device.ContainerDevice{
            UUID:      dev.ID,
            Usedmem:   memreq,
            Usedcores: request.Coresreq,
        })

        // 非 topology-aware 策略：滿足數量後立即返回
        if !needTopology {
            request.Nums--
            if request.Nums == 0 {
                return true, tmpDevs, ""
            }
        }
    }
    // topology-aware 策略：在候選集上做組合選擇後返回
    // ...
}
```

### 3.2 nvidia.com/gpucores

#### 3.2.1 定義

`nvidia.com/gpucores` 是用於指定每個物理 GPU 分配給 Pod 的計算核心百分比的資源類型。

#### 3.2.2 特性

- **必需性**: 可選的資源宣告
- **取值範圍**: 0-100 的整數，表示百分比
- **預設值**: 由 `device-config.yaml` 中 `defaultCores` 配置項決定（來源：`charts/hami/templates/scheduler/device-configmap.yaml`）
- **限制類型**: 從 v1.0.1.3 版本開始在容器內部限制 GPU 利用率（來源：`HAMi/CHANGELOG.md` 中 `v1.0.1.3` 說明）
- **共享支持**: 支援多個 Pod 共享同一個物理 GPU 的不同算力份額

#### 3.2.3 配置選項

- `defaultCores`: 預設核心分配百分比（`device-config.yaml`）
- `devicePlugin.disablecorelimit`: 是否禁用核心限制（Helm Chart values，最終作為 `hami-device-plugin` 的 `--disable-core-limit` 參數）
- `GPU_CORE_UTILIZATION_POLICY`: 容器環境變數，控制核心利用率策略

#### 3.2.4 算力分配機制

##### 3.2.4.1 核心概念

- **總量(Totalcore)**: 每個 GPU 裝置的總計算核心數，通常為 100（代表 100% 的 GPU 計算能力）
- **已分配(Usedcores)**: 當前已經分配給 Pod/容器的 GPU 核心數總和
- **算力**: 指 GPU 的計算核心資源，以百分比形式表示

##### 3.2.4.2 資料結構

在 `pkg/device/devices.go` 中的 `DeviceUsage` 結構體定義：

```go
type DeviceUsage struct {
    ID          string
    Index       uint
    Used        int32   // 使用該裝置的容器數量
    Count       int32   // 裝置可支援的最大容器數量
    Usedmem     int32   // 已使用記憶體
    Totalmem    int32   // 總記憶體
    Totalcore   int32   // 總核心數（通常為100）
    Usedcores   int32   // 已使用核心數
    Mode        string  // 裝置模式（如MIG模式）
    Numa        int     // NUMA 節點編號
    Type        string  // GPU 型號
    Health      bool    // 裝置健康狀態
    // ... 其他字段
}
```

##### 3.2.4.3 分配流程

1. **資源宣告**: Pod 透過 `nvidia.com/gpucores` 宣告所需的 GPU 核心百分比
2. **分配檢查**: 在 `Fit` 函式中檢查可用資源

   ```go
   if dev.Totalcore-dev.Usedcores < k.Coresreq {
       // 核心資源不足
       continue
   }
   ```

3. **使用更新**: 在 `AddResourceUsage` 函式中更新已分配核心數

```go
// 更新裝置的已使用核心數：累加容器的核心使用量
n.Usedcores += ctr.Usedcores
```

##### 3.2.4.4 實際示例

- **100/100**: GPU 被完全獨佔使用
- **50/100**: GPU 的 50% 算力已分配，還剩 50% 可用
- **80/100**: GPU 的 80% 算力已分配，還剩 20% 可用

##### 3.2.4.5 效能影響分析

`nvidia.com/gpucores` 表示 Pod 在排程與執行期可用的計算份額上限，但效能表現通常不滿足嚴格的線性關係，主要受以下因素影響：

- 算子形態與併發（Kernel 粒度、Launch 頻率、CPU 側開銷）
- 顯存頻寬與訪存模式（訓練/推理差異明顯）
- 多租共享時的競爭（上下文切換、其他任務負載波動）

因此，建議在目標 GPU 型號與目標框架上做基準測試，使用 `HostCoreUtilization` 與容器級 `Device_utilization_desc_of_container` 指標對比評估資源配置是否合理。

#### 3.2.5 程式碼實現

**1. 資源請求解析**：

在 `pkg/device/nvidia/device.go` 中解析核心需求：

```go
// pkg/device/nvidia/device.go

// 設定預設核心數為配置的預設值
corenum := dev.config.DefaultCores
// 優先從 Limits 獲取 nvidia.com/gpucores 的值
core, ok := ctr.Resources.Limits[resourceCores]
if !ok {
    // 如果 Limits 中沒有，則從 Requests 獲取
    core, ok = ctr.Resources.Requests[resourceCores]
}
if ok {
    // 將資源值轉換為 int64
    corenums, ok := core.AsInt64()
    if ok {
        // 更新核心數為請求的值
        corenum = int32(corenums)
    }
}
```

**2. 排程分配**：

在 `Fit` 函式中，檢查裝置剩餘算力是否滿足請求：

```go
// pkg/device/nvidia/device.go

// 檢查裝置剩餘核心數是否足夠：總核心數 - 已使用核心數 >= 請求核心數
if dev.Totalcore-dev.Usedcores < k.Coresreq {
    // 核心資源不足，記錄原因並繼續檢查其他裝置
    reason[common.CardInsufficientCore]++
    continue
}
```

**3. 限制執行 (Enforcement)**：

核心利用率限制主要在 `HAMi-core` 專案中實現，采用了**基於反饋控制的令牌桶演算法**。

**算法原理**：

1. **令牌桶 (Token Bucket)**：使用全域性變數 `g_cur_cuda_cores` 作為令牌桶，代表當前允許使用的計算配額。該變數**初始化為 0**，後續由監控執行緒動態調整。
2. **消費 (Consume)**：當 CUDA Kernel 啟動時，計算其所需的計算量（Grid × Block），並從令牌桶中扣除相應數量的令牌。如果桶中令牌不足（小於 0），則掛起當前執行緒等待，直到令牌回補。
3. **反饋調節 (Feedback Loop)**：後台監控執行緒定期檢查 GPU 實際利用率。如果實際利用率低於使用者設定的限制（`nvidia.com/gpucores`），則向桶中注入令牌；如果超過限制，則減少令牌，從而動態穩定 GPU 利用率。

> **注**：GPU 實際利用率是透過 NVML API `nvmlDeviceGetProcessUtilization` 獲取的 **SM 利用率 (smUtil)**，統計了當前容器內所有行程的利用率之和。（來源：`HAMi-core/src/multiprocess/multiprocess_utilization_watcher.c` 呼叫 `nvmlDeviceGetProcessUtilization` 並累加 `smUtil`）
>
> **關於監控指標**：
>
> 1. **指標對應關係**：該指標在 **DCGM Exporter** 中**沒有直接對應的容器級指標**。預設的 `DCGM_FI_DEV_GPU_UTIL` 僅反映整卡物理利用率。
> 2. **指標準確性說明**：標準的 GPU 利用率（如 `nvidia-smi`）通常是**基於時間（Temporal）**的度量，即“在過去取樣週期內，GPU 是否有 Kernel 在執行”。（來源：NVML `nvmlDeviceGetProcessUtilization` 與 `nvmlProcessUtilizationSample_t.smUtil` 欄位定義，見 `HAMi-core/src/include/nvml-subset.h`）
>    - 這意味著：即使只有一個 Kernel 在單個 SM 上執行，利用率也可能顯示為 100%。
>    - 因此，該指標更適合衡量 **“GPU 是否繁忙”**（`Time Slicing`），而非 **“GPU 計算能力是否飽和”**（`Compute Saturation`/`SM Efficiency`）。
> 3. **HAMi 的做法**：HAMi 的核心限制本質上是**時間片排程（Time Slicing）**，因此依賴這種基於時間的利用率指標是符合其設計預期的。如果需要監控容器級別的核心利用率，建議使用 HAMi 自帶的監控元件（`vGPU Monitor`）。

**程式碼實現細節**：

**1. Kernel 啟動攔截與令牌消費**：

在 `HAMi-core/src/cuda/memory.c` 中，攔截了 `cuLaunchKernel` 等函式：

```c
// HAMi-core/src/cuda/memory.c

// cuLaunchKernel - CUDA Kernel 啟動函式攔截實現
// 參數: f - CUDA 函式控制代碼, gridDimX/Y/Z - Grid 維度, blockDimX/Y/Z - Block 維度
//       sharedMemBytes - 共享記憶體大小, hStream - CUDA 流, kernelParams - 核心參數, extra - 額外參數
// 返回值: CUresult - CUDA 操作結果
CUresult cuLaunchKernel ( CUfunction f, unsigned int  gridDimX, unsigned int  gridDimY, unsigned int  gridDimZ, unsigned int  blockDimX, unsigned int  blockDimY, unsigned int  blockDimZ, unsigned int  sharedMemBytes, CUstream hStream, void** kernelParams, void** extra ){
    ENSURE_RUNNING();  // 確保執行時環境正常
    pre_launch_kernel();  // Kernel 啟動前預處理
    if (pidfound==1){  // 檢查是否為需要限制的行程
        // 呼叫速率限制器，計算 Kernel 的總計算量（Grid 大小 × Block 大小）
        rate_limiter(gridDimX * gridDimY * gridDimZ,
                   blockDimX * blockDimY * blockDimZ);
    }
    // 呼叫原始的 CUDA Kernel 啟動函式
    CUresult res = CUDA_OVERRIDE_CALL(cuda_library_entry,cuLaunchKernel,f,gridDimX,gridDimY,gridDimZ,blockDimX,blockDimY,blockDimZ,sharedMemBytes,hStream,kernelParams,extra);
    return res;  // 返回操作結果
}
```

**2. 速率限制邏輯**：

在 `HAMi-core/src/multiprocess/multiprocess_utilization_watcher.c` 中實現 `rate_limiter`，根據當前的利用率情況決定是否延遲 Kernel 的提交：

```c
// HAMi-core/src/multiprocess/multiprocess_utilization_watcher.c

// rate_limiter - 速率限制器函式，控制 CUDA Kernel 的提交速率
// 參數: grids - Grid 維度乘積, blocks - Block 維度乘積
// 返回值: void
void rate_limiter(int grids, int blocks) {
  long before_cuda_cores = 0;  // 限制前的核心數
  long after_cuda_cores = 0;   // 限制後的核心數
  long kernel_size = grids;    // Kernel 計算量（Grid 大小）

  // 等待初始化完成，確保監控系統已就緒
  while (get_recent_kernel()<0) {
    sleep(1);  // 每秒檢查一次
  }
  set_recent_kernel(2);  // 設定最近 Kernel 狀態

  // 檢查是否需要限制：如果限制為100%（無限制）或0%（禁用限制），則直接返回
  if ((get_current_device_sm_limit(0)>=100) || (get_current_device_sm_limit(0)==0))
      return;
  // 檢查利用率開關是否開啟
  if (get_utilization_switch()==0)
      return;

  // 核心限制邏輯 - 使用 CAS（Compare And Swap）原子操作
  do {
CHECK:
      before_cuda_cores = g_cur_cuda_cores;  // 獲取當前可用核心數
      if (before_cuda_cores < 0) {
        // 如果當前核心數不足，則睡眠等待令牌回補
        nanosleep(&g_cycle, NULL);  // 使用納秒級睡眠
        goto CHECK;  // 重新檢查
      }
      after_cuda_cores = before_cuda_cores - kernel_size;  // 計算扣除後的核心數
  } while (!CAS(&g_cur_cuda_cores, before_cuda_cores, after_cuda_cores));  // 原子更新
}
```

**3. 利用率監控與調節**：

後台執行緒 `utilization_watcher` 負責監控實際 GPU 利用率並動態調整可用 Token (`g_cur_cuda_cores`)：

```c
// HAMi-core/src/multiprocess/multiprocess_utilization_watcher.c

void* utilization_watcher() {
    // ... 初始化 ...
    int upper_limit = get_current_device_sm_limit(0);

    while (1){
        nanosleep(&g_wait, NULL);
        // ... 獲取當前利用率 userutil ...

        // 動態調整可用核心數
        if ((userutil[0]<=100) && (userutil[0]>=0)){
          share = delta(upper_limit, userutil[0], share);
          change_token(share);
        }
    }
}
```

### 3.3 nvidia.com/gpumem

#### 3.3.1 定義

`nvidia.com/gpumem` 是用於指定 Pod 所需 GPU 記憶體大小的資源類型，以 MB 為單位。

#### 3.3.2 特性

- **必需性**: 可選的資源宣告
- **取值範圍**: 正整數，單位為 MB
- **用途**: 精確指定 Pod 需要的 GPU 記憶體量
- **互斥建議**: 建議不要與 `nvidia.com/gpumem-percentage` 同時設定；如同時設定，`gpumem` 優先生效（來源：`pkg/device/nvidia/device.go` 的 `Fit` 實現）
- **記憶體隔離**: 提供硬隔離保證，確保容器不會超出分配的記憶體邊界

#### 3.3.3 程式碼實現

**1. 資源請求解析**：

在 `GenerateResourceRequests` 函式中處理記憶體資源請求：

```go
// pkg/device/nvidia/device.go

// 獲取 nvidia.com/gpumem 的值
mem, ok := ctr.Resources.Limits[resourceMem]
if !ok {
    mem, ok = ctr.Resources.Requests[resourceMem]
}
if ok {
    memnums, ok := mem.AsInt64()
    if ok {
        memnum = int(memnums)
    }
}
```

**2. 排程分配**：

在 `Fit` 函式中，檢查裝置剩餘顯存是否滿足請求：

```go
// pkg/device/nvidia/device.go

// 檢查裝置總顯存減去已用顯存是否小於請求顯存
if dev.Totalmem-dev.Usedmem < memreq {
    reason[common.CardInsufficientMemory]++
    klog.V(5).InfoS(common.CardInsufficientMemory, ...)
    continue
}
```

### 3.4 nvidia.com/gpumem-percentage

#### 3.4.1 定義

`nvidia.com/gpumem-percentage` 是用於指定 Pod 所需 GPU 記憶體百分比的資源類型，在 v1.0.1.4 版本中引入。（來源：`HAMi/CHANGELOG.md` 中 `v1.0.1.4` 說明）

#### 3.4.2 特性

- **必需性**: 可選的資源宣告
- **取值範圍**: 0-100 的整數，表示百分比
- **用途**: 以百分比形式分配 GPU 記憶體
- **互斥建議**: 建議不要與 `nvidia.com/gpumem` 同時設定；如同時設定，`gpumem` 優先生效（來源：`pkg/device/nvidia/device.go` 的 `Fit` 實現）
- **獨佔支援**: 設定為 100 時配合 `nvidia.com/gpucores: 100` 可實現 GPU 獨佔

#### 3.4.3 使用示例

```yaml
resources:
  limits:
    nvidia.com/gpu: 1
    nvidia.com/gpumem-percentage: 50 # 分配 50% 的 GPU 記憶體
    nvidia.com/gpucores: 50 # 分配 50% 的 GPU 算力
```

#### 3.4.4 程式碼分析

**1. 資源請求解析**：

在 `pkg/device/nvidia/device.go` 的 `GenerateResourceRequests` 函式中，HAMi 會解析 `gpumem-percentage` 並將其轉換為內部請求結構。

- **讀取配置與優先順序處理**：程式碼首先嚐試讀取絕對記憶體值 (`gpumem`)，然後讀取百分比值 (`gpumem-percentage`)。
- **預設行為**：如果兩者都未設定，且未配置全域性預設記憶體值，則預設設定為 100% 記憶體。

```go
// pkg/device/nvidia/device.go

func (dev *NvidiaGPUDevices) GenerateResourceRequests(ctr *corev1.Container) device.ContainerDeviceRequest {
    // ... (省略部分程式碼)

    // 讀取 nvidia.com/gpumem-percentage
    mempnum := int32(101) // 101 為未設定的標記值
    mem, ok := ctr.Resources.Limits[resourceMemPercentage]
    if !ok {
        mem, ok = ctr.Resources.Requests[resourceMemPercentage]
    }
    if ok {
        mempnums, ok := mem.AsInt64()
        if ok {
            mempnum = int32(mempnums)
        }
    }

    // 預設邏輯：如果未設定百分比且未設定絕對記憶體，則根據配置決定預設行為
    if mempnum == 101 && memnum == 0 {
        if dev.config.DefaultMemory != 0 {
            memnum = int(dev.config.DefaultMemory)
        } else {
            mempnum = 100 // 預設為 100%
        }
    }

    // 返回標準化的裝置請求結構
    return device.ContainerDeviceRequest{
        // ...
        Memreq:           int32(memnum),  // 絕對記憶體值
        MemPercentagereq: int32(mempnum), // 百分比值
        // ...
    }
}
```

**2. 排程與分配邏輯**：

在 `pkg/device/nvidia/device.go` 的 `Fit` 函式中，排程器會根據裝置的總顯存將百分比轉換為實際的顯存大小進行校驗。

- **動態轉換**：百分比值 (`MemPercentagereq`) 會根據當前遍歷到的裝置的總顯存 (`dev.Totalmem`) 動態計算為絕對值 (`memreq`)。
- **互斥邏輯**：程式碼明確了 `Memreq` (來自 `gpumem`) 的優先順序高於 `MemPercentagereq`。如果 `Memreq > 0`，則直接使用絕對值，忽略百分比設定。

```go
// pkg/device/nvidia/device.go

func (nv *NvidiaGPUDevices) Fit(devices []*device.DeviceUsage, request device.ContainerDeviceRequest, pod *corev1.Pod, nodeInfo *device.NodeInfo, allocated *device.PodDevices) (bool, map[string]device.ContainerDevices, string) {
    // ...
    k := request
    for i := len(devices) - 1; i >= 0; i-- {
        dev := devices[i]

        // ...

        memreq := int32(0)
        // 優先順序 1: 如果設定了絕對記憶體值 (gpumem)，直接使用
        if k.Memreq > 0 {
            memreq = k.Memreq
        }
        // 優先順序 2: 如果未設定絕對值且設定了百分比，則根據裝置總顯存計算
        if k.MemPercentagereq != 101 && k.Memreq == 0 {
            // 計算公式: 裝置總顯存 * 百分比 / 100
            memreq = dev.Totalmem * k.MemPercentagereq / 100
        }

        // 檢查配額與剩餘顯存
        if dev.Totalmem-dev.Usedmem < memreq {
            // 顯存不足，記錄原因並跳過該裝置
            reason[common.CardInsufficientMemory]++
            continue
        }

        // ...
    }
}
```

---

## 4. 配置管理

HAMi 提供了多層次的配置管理機制，支援從全域性到 Pod 級別的精細控制。配置遵循層級優先順序：Pod 注解 > 節點註解 > 全局配置。這種設計允許管理員在叢集級別設定預設策略，同時在需要時進行細粒度的個性化配置。

### 4.1 全局配置

透過 `hami-scheduler-device` ConfigMap 管理排程器的裝置配置（Helm Chart 預設渲染為 `<release>-scheduler-device`，來源：`charts/hami/templates/scheduler/device-configmap.yaml`）：

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: hami-scheduler-device # 示例名稱，實際取決於 Helm Release 名稱
data:
  device-config.yaml: |-
    nvidia:
      # GPU 裝置記憶體虛擬化縮放比例，支持超分配（實驗性功能）
      # 取值範圍：大於 0 的浮點數，預設值：1
      # 當設定為大於 1 時，可實現 GPU 記憶體的虛擬化超分配
      deviceMemoryScaling: 1

      # 單個 GPU 裝置可同時分配的最大任務數量
      # 取值範圍：正整數，預設值：10
      # 控制 GPU 資源共享的併發度，影響排程器的分配策略
      deviceSplitCount: 10

      # Pod 未指定 GPU 記憶體時的預設記憶體分配量（單位：MB）
      # 取值範圍：非負整數，預設值：0
      # 0 表示使用 GPU 的 100% 記憶體，非 0 值表示具體的記憶體分配量
      defaultMemory: 0

      # Pod 未指定 GPU 核心時的預設核心分配百分比
      # 取值範圍：0-100 的整數，預設值：0
      # 0 表示可適配任何有足夠記憶體的 GPU，100 表示獨佔整個 GPU
      defaultCores: 0

      # Pod 未指定 nvidia.com/gpu 時的預設 GPU 數量
      # 取值範圍：正整數，預設值：1
      # 當 Pod 指定了 gpumem、gpumem-percentage 或 gpucores 時自動補齊此預設值
      defaultGPUNum: 1
```

`nvidia.disablecorelimit` 由 `hami-device-plugin` 的啟動參數 `--disable-core-limit` 控制（來源：`charts/hami/templates/device-plugin/daemonsetnvidia.yaml`），不屬於 `device-config.yaml` 的字段。

### 4.2 節點級配置

透過節點註解進行排程策略配置。詳細的排程策略說明請參見第 5.1 節。

```yaml
apiVersion: v1
kind: Node
metadata:
  annotations:
    hami.io/node-scheduler-policy: "binpack" # 節點排程策略
    hami.io/gpu-scheduler-policy: "spread" # GPU排程策略
```

### 4.3 Pod 級配置

透過 Pod 註解進行精細控制：

```yaml
apiVersion: v1
kind: Pod
metadata:
  annotations:
    nvidia.com/use-gputype: "GeForce-RTX-3080" # 指定GPU類型
    nvidia.com/use-gpuuuid: "GPU-12345678" # 指定GPU UUID
    # nvidia.com/vgpu-mode: "mig" # 可選值: "mig", "mps", "hami-core"，不設定表示預設共享
spec:
  containers:
    - name: gpu-container
      env:
        - name: GPU_CORE_UTILIZATION_POLICY
          value: "default" # 核心利用率策略
```

---

## 5. 高階特性

本章詳細介紹 HAMi 的高階功能特性，包括排程策略、裝置選擇、NUMA 繫結、MIG 支持、執行時模式選擇和監控能力。這些特性為生產環境提供了靈活的配置選項和精細的控制能力。

### 5.1 排程策略

HAMi 支援多種 GPU 排程策略，可透過註解進行配置：

#### 5.1.1 節點級排程策略

```yaml
apiVersion: v1
kind: Node
metadata:
  annotations:
    hami.io/node-scheduler-policy: "binpack" # 緊湊分配策略
    # 可選值: "binpack", "spread"
```

#### 5.1.2 GPU 級排程策略

```yaml
apiVersion: v1
kind: Pod
metadata:
  annotations:
    hami.io/gpu-scheduler-policy: "spread" # GPU 分散策略
    # 可選值: "binpack", "spread", "topology-aware"
spec:
  # Pod 規格定義
```

#### 5.1.3 排程策略說明

| **策略名稱**     | **作用範圍**  | **效果描述**                               |
| ---------------- | ------------- | ------------------------------------------ |
| `binpack`        | 節點級/GPU 級 | 優先使用已有負載的資源，提高資源利用率     |
| `spread`         | 節點級/GPU 級 | 分散分配，提高可用性和負載均衡             |
| `topology-aware` | GPU 級        | 優先選擇拓撲更優（例如同一 NUMA 域）的 GPU |

策略名稱來源：`pkg/util/types.go` 中 `NodeSchedulerPolicy*` 與 `GPUSchedulerPolicy*` 常量定義。

### 5.2 GPU 類型和裝置選擇

#### 5.2.1 指定 GPU 類型

```yaml
apiVersion: v1
kind: Pod
metadata:
  annotations:
    nvidia.com/use-gputype: "GeForce-RTX-3080,Tesla-V100" # 指定可用GPU類型
    nvidia.com/nouse-gputype: "GeForce-GTX-1080" # 排除特定GPU類型
spec:
  containers:
    - name: gpu-container
      resources:
        limits:
          nvidia.com/gpu: 1
```

#### 5.2.2 指定 GPU UUID

```yaml
apiVersion: v1
kind: Pod
metadata:
  annotations:
    nvidia.com/use-gpuuuid: "GPU-12345678-1234-1234-1234-123456789012" # 指定GPU UUID
    nvidia.com/nouse-gpuuuid: "GPU-87654321-4321-4321-4321-210987654321" # 排除特定GPU UUID
spec:
  # Pod 規格定義
```

### 5.3 NUMA 繫結和拓撲感知

#### 5.3.1 NUMA 繫結

```yaml
apiVersion: v1
kind: Pod
metadata:
  annotations:
    nvidia.com/numa-bind: "true" # 啟用 NUMA 繫結
spec:
  containers:
    - name: gpu-container
      resources:
        limits:
          nvidia.com/gpu: 2 # 多 GPU 時會優先選擇同一 NUMA 域的 GPU
```

#### 5.3.2 拓撲感知排程

HAMi 支援基於 GPU 拓撲的智慧排程，在多 GPU 分配時會考慮：

- **NVLink 連線**: 優先分配有 NVLink 連線的 GPU 組合
- **PCIe 拓撲**: 考慮 PCIe 匯流排的頻寬和延遲
- **NUMA 域**: 優先在同一 NUMA 域內分配 GPU

### 5.4 MIG 支持

#### 5.4.1 靜態 MIG 配置

HAMi 支持 NVIDIA MIG (Multi-Instance GPU) 技術：

```yaml
apiVersion: v1
kind: Pod
metadata:
  annotations:
    nvidia.com/vgpu-mode: "mig" # 指定使用 MIG 模式
spec:
  containers:
    - name: mig-container
      resources:
        limits:
          nvidia.com/gpu: 1
          nvidia.com/gpumem: 5000 # MIG 實例記憶體大小
```

#### 5.4.2 動態 MIG 支持

HAMi 支援透過 `mig-parted` 進行動態 MIG 實例管理。（來源：`HAMi/docs/dynamic-mig-support_cn.md`）

- **自動切分與選擇**: `hami-device-plugin` 會基於 device-config 中的 MIG template 選擇並建立可用實例
- **動態調整**: 在任務排程與資源回收過程中按需調整 MIG template
- **統一 API**: 任務仍使用 `nvidia.com/gpu` 與 `nvidia.com/gpumem` 宣告資源；可選透過 `nvidia.com/vgpu-mode: "mig"` 將任務限定在 MIG 節點

啟用方式與前置條件來源：`HAMi/docs/dynamic-mig-support_cn.md` 的 “Enabling Dynamic-mig Support” 小節。

### 5.5 執行時模式選擇

#### 5.5.1 vGPU 模式配置

```yaml
apiVersion: v1
kind: Pod
metadata:
  annotations:
    # nvidia.com/vgpu-mode: "mig" # 可選值: "mig", "mps", "hami-core"，不設定表示預設共享
spec:
  containers:
    - name: gpu-container
      env:
        - name: GPU_CORE_UTILIZATION_POLICY
          value: "default" # 核心利用率策略
          # 可選值: "default", "force", "disable"
```

#### 5.5.2 執行時類配置

```yaml
apiVersion: v1
kind: Pod
spec:
  runtimeClassName: "nvidia" # 指定執行時類
  containers:
    - name: gpu-container
      resources:
        limits:
          nvidia.com/gpu: 1
```

#### 5.5.3 MPS 模式說明

MPS（Multi-Process Service）是 NVIDIA 提供的一種 GPU 共享機制，用於在多行程 CUDA 負載（例如 MPI 場景）下提升併發利用率。（來源：NVIDIA MPS 文件：<https://docs.nvidia.com/deploy/mps/index.html>）

HAMi 對 MPS 的處理可以拆為兩層：

第一層是“排程約束”。HAMi 透過 Pod 注解 `nvidia.com/vgpu-mode: "mps"` 將任務約束到 `Mode` 匹配的裝置/節點上（來源：`pkg/device/nvidia/device.go` 中 `AllocateMode` / `MpsMode` 常量與 `checkType()` 的模式過濾邏輯）。

第二層是“執行時能力”。當裝置外掛側選擇 MPS Sharing Strategy 時，啟動參數會拒絕 `--mig-strategy=mixed`，並要求顯式指定 `--mps-root`（來源：`cmd/device-plugin/nvidia/main.go` 的 `validateFlags()`）。但需要注意：本倉庫內 `pkg/device-plugin/nvidiadevice/nvinternal/plugin/mps.go` 的 MPS 相關邏輯為佔位實現（`getMPSOptions()` / `waitForDaemon()` / `updateReponse()` 均為空操作），因此 `nvidia.com/vgpu-mode: "mps"` 目前不應被理解為“HAMi 會自動完成 MPS control daemon 的部署、啟動與環境注入”。（來源：`pkg/device-plugin/nvidiadevice/nvinternal/plugin/mps.go`）

下面給出 Pod 側的宣告方式示例（資源宣告與共享模式一致，差異在於 `vgpu-mode` 約束）：

```yaml
apiVersion: v1
kind: Pod
metadata:
  annotations:
    nvidia.com/vgpu-mode: "mps" # 約束排程到 MPS 模式節點（若節點側已啟用對應模式）
spec:
  containers:
    - name: mps-container
      resources:
        limits:
          nvidia.com/gpu: 1 # 申請 1 張物理 GPU
          nvidia.com/gpucores: 50 # 可選：限制算力占比（0-100）
          nvidia.com/gpumem: 4096 # 可選：限制顯存（MB）
```

可觀測性方面，排程器監控端暴露的 `nodeGPUMigInstance` 指標描述中預留了 MPS 值語義（`0` 表示 hami-core，`1` 表示 mig，`2` 表示 mps）（來源：`cmd/scheduler/metrics.go` 的指標定義）。

### 5.6 監控和可觀測性

#### 5.6.1 資源使用率監控

HAMi 提供多層次的 GPU 使用率監控：

- **節點級監控**: 透過 `HostCoreUtilization` 指標監控整個 GPU 卡的利用率
- **容器級監控**: 透過 `Device_utilization_desc_of_container` 指標監控容器維度的 SM 利用率（來源：`cmd/vGPUmonitor/metrics.go` 中 `DeviceSmUtil` 上報邏輯）
- **記憶體監控**: 透過 `vGPU_device_memory_usage_in_bytes` / `vGPU_device_memory_limit_in_bytes` 指標監控 vGPU 記憶體使用與限制

#### 5.6.2 Prometheus 指標

```yaml
# 主要監控指標
- HostGPUMemoryUsage: GPU 裝置記憶體已用量（bytes）
- HostCoreUtilization: GPU 核心利用率（0-100）
- vGPU_device_memory_usage_in_bytes: vGPU 裝置記憶體使用量（bytes）
- vGPU_device_memory_limit_in_bytes: vGPU 裝置記憶體限制（bytes）
- Device_utilization_desc_of_container: 容器維度 SM 利用率（0-100）
```

指標名稱與標籤來源：`cmd/vGPUmonitor/metrics.go` 中 Prometheus 指標定義。

---

## 6. 故障排查和最佳實踐

本章提供 HAMi GPU 資源管理的故障排查指南和效能最佳化最佳實踐。內容包括常見問題診斷方法、效能最佳化建議以及生產環境中的配置經驗。透過本章內容，您可以快速定位和解決 GPU 資源相關的各類問題。

### 6.1 常見問題診斷

#### 6.1.1 資源分配失敗

**問題現象**: Pod 一直處於 Pending 狀態，事件顯示 GPU 資源不足

**排查步驟**:

```bash
# 1. 檢查節點 GPU 資源狀態
kubectl describe node <node-name> | grep nvidia.com

# 2. 查看 HAMi 排程器日誌
kubectl logs -n kube-system deployment/hami-scheduler

# 3. 檢查裝置外掛狀態
kubectl get pods -n kube-system | grep hami-device-plugin
```

**常見原因**:

- GPU 記憶體碎片化：多個小任務佔用導致無法分配大記憶體需求
- 算力超分配：`gpucores` 總和超過 100%
- 裝置類型不匹配：指定的 GPU 類型在節點上不存在

#### 6.1.2 效能隔離問題

**問題現象**: 容器 GPU 利用率超出預期，影響其他容器

**解決方案**:

```yaml
# 啟用嚴格的核心利用率限制
apiVersion: v1
kind: Pod
metadata:
  annotations:
    nvidia.com/vgpu-mode: "hami-core"
spec:
  containers:
    - name: gpu-container
      env:
        - name: GPU_CORE_UTILIZATION_POLICY
          value: "force" # 強制執行利用率限制
```

#### 6.1.3 記憶體超限問題

**問題現象**: 容器因 GPU 記憶體不足被終止

**排查方法**:

```bash
# 查看容器 GPU 記憶體使用情況
kubectl exec <pod-name> -- nvidia-smi

# 檢查HAMi監控指標
curl http://<node-ip>:9394/metrics | grep vGPU_device_memory
```

### 6.2 效能最佳化建議

#### 6.2.1 資源配置最佳化

**記憶體分配策略**:

```yaml
# 推薦：使用固定記憶體分配，避免碎片化
nvidia.com/gpumem: 4000 # 而非 nvidia.com/gpumem-percentage: 50

# 大記憶體任務：優先使用獨佔模式
nvidia.com/gpu: 1
nvidia.com/gpucores: 100
nvidia.com/gpumem-percentage: 100
```

**算力分配策略**:

```yaml
# 計算密集型任務：分配足夠的核心資源
nvidia.com/gpucores: 80

# 推理任務：可以使用較少的核心資源
nvidia.com/gpucores: 25
```

#### 6.2.2 排程策略最佳化

```yaml
# 高效能運算場景：使用 NUMA 繫結
apiVersion: v1
kind: Pod
metadata:
  annotations:
    nvidia.com/numa-bind: "true"
    hami.io/gpu-scheduler-policy: "topology-aware"

# 高可用場景：使用分散策略
apiVersion: v1
kind: Pod
metadata:
  annotations:
    hami.io/gpu-scheduler-policy: "spread"
```

---

## 7. 多廠商 GPU 支持

除了 NVIDIA GPU 外，HAMi 還支援多種其他廠商的 GPU 和 AI 加速裝置：

### 7.1 支援的裝置類型

| **廠商** | **裝置類型** | **資源名稱**                                                                                 | **特性支持**                     |
| -------- | ------------ | -------------------------------------------------------------------------------------------- | -------------------------------- |
| NVIDIA   | GPU          | `nvidia.com/gpu`, `nvidia.com/gpucores`, `nvidia.com/gpumem`, `nvidia.com/gpumem-percentage` | 完整虛擬化、MIG、監控            |
| 寒武紀   | MLU          | `cambricon.com/mlu`, `cambricon.com/mlu.smlu.vmemory`, `cambricon.com/mlu.smlu.vcore`        | 裝置共享、記憶體限制、核心限制     |
| 海光     | DCU          | `hygon.com/dcunum`, `hygon.com/dcumem`, `hygon.com/dcucores`                                 | 裝置虛擬化、資源隔離             |
| 天數智芯 | GPU          | `iluvatar.ai/vcuda-core`, `iluvatar.ai/vcuda-memory`                                         | 100 單元粒度切分                 |
| 摩爾執行緒 | GPU          | `mthreads.com/vgpu`, `mthreads.com/sgpu-memory`                                              | 裝置共享、MT-CloudNative Toolkit |
| 華為昇騰 | NPU          | `huawei.com/Ascend910A`, `huawei.com/Ascend910A-memory`                                      | 模板化虛擬化、AI 核心控制        |
| 沐曦     | GPU          | `metax-tech.com/gpu`                                                                         | 裝置複用、拓撲感知               |

### 7.2 通用資源宣告模式

HAMi 為不同廠商的裝置提供了統一的資源宣告模式：

#### 7.2.1 基礎裝置分配

```yaml
apiVersion: v1
kind: Pod
spec:
  containers:
    - name: ai-workload
      resources:
        limits:
          # NVIDIA GPU
          nvidia.com/gpu: 1
          nvidia.com/gpumem: 4000

          # 寒武紀 MLU
          # cambricon.com/mlu: 1

          # 海光 DCU
          # hygon.com/dcunum: 1

          # 天數智芯 GPU
          # iluvatar.ai/vcuda-core: 50
          # iluvatar.ai/vcuda-memory: 8000

          # 華為昇騰 NPU
          # huawei.com/Ascend910A: 1
          # huawei.com/Ascend910A-memory: 16000
```

#### 7.2.2 廠商特定配置

不同廠商的裝置可能需要特定的配置和依賴：

**天數智芯 GPU**:

```bash
# 需要部署 gpu-manager
helm install hami hami-charts/hami \
  --set iluvatarResourceMem=iluvatar.ai/vcuda-memory \
  --set iluvatarResourceCore=iluvatar.ai/vcuda-core
```

**摩爾執行緒 GPU**:

```bash
# 需要部署 MT-CloudNative Toolkit
# 聯絡廠商獲取相關元件
```

**華為昇騰 NPU**:

```yaml
# 支援模板化虛擬化
apiVersion: v1
kind: Pod
metadata:
  annotations:
    huawei.com/npu-template: "1c8g" # 1核心8GB模板
spec:
  containers:
    - name: npu-container
      resources:
        limits:
          huawei.com/Ascend910A: 1
```

### 7.3 裝置粒度和虛擬化策略

不同廠商的裝置採用不同的虛擬化粒度：

- **NVIDIA GPU**: 基於記憶體和核心百分比的靈活切分
- **天數智芯 GPU**: 100 單元粒度切分
- **華為昇騰 NPU**: 基於預定義模板的虛擬化
- **其他廠商**: 根據硬體特性採用相應的虛擬化策略

### 7.4 監控和可觀測性

HAMi 為不同廠商的裝置提供統一的監控介面：

```yaml
# 通用監控指標
- device_memory_usage_bytes: 裝置記憶體使用量
- device_memory_limit_bytes: 裝置記憶體限制
- device_utilization_percent: 裝置利用率
- device_core_usage: 裝置核心使用情況
```

---
