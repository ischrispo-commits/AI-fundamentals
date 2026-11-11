# InfiniBand 網路理論與實踐

> 作者：Grissom
> Version：1.3
> Updated Date：2026/11/5

## 術語定義

在深入了解 InfiniBand 技術之前，我們先列舉一些關鍵術語：

| **術語**  | **英文全稱**                        | **中文含義**        | **說明**                              |
| --------- | ----------------------------------- | ------------------- | ------------------------------------- |
| **IB**    | InfiniBand                          | 無限頻寬            | 高效能運算網路架構標準                |
| **RDMA**  | Remote Direct Memory Access         | 遠端直接記憶體訪問    | 繞過 CPU 直接訪問遠端記憶體的技術       |
| **HCA**   | Host Channel Adapter                | 主機通道介面卡      | InfiniBand 網卡的正式名稱             |
| **SM**    | Subnet Manager                      | 子網管理器          | 管理 IB 子網拓撲和路由的軟體          |
| **QP**    | Queue Pair                          | 佇列對              | IB 通訊的基本單元，包含傳送和接收佇列 |
| **VL**    | Virtual Lane                        | 虛擬通道            | 在物理鏈路上建立的邏輯通道            |
| **SL**    | Service Level                       | 服務級別            | 用於 QoS 和路由的流量分類             |
| **P_Key** | Partition Key                       | 分割槽金鑰            | 用於網路分割槽和安全隔離                |
| **LID**   | Local Identifier                    | 本地識別符號          | 子網內裝置的唯一地址                  |
| **GUID**  | Globally Unique Identifier          | 全域性唯一識別符號      | 裝置的全球唯一標識                    |
| **MTU**   | Maximum Transmission Unit           | 最大傳輸單元        | 單次傳輸的最大資料包大小              |
| **FEC**   | Forward Error Correction            | 前向糾錯            | 自動檢測和糾正傳輸錯誤的技術          |
| **RoCE**  | RDMA over Converged Ethernet        | 融合乙太網上的 RDMA | 在乙太網上實現 RDMA 的技術            |
| **OFED**  | OpenFabrics Enterprise Distribution | 開放架構企業發行版  | InfiniBand 和 RDMA 的開源軟體棧       |

---

## 目錄

- [InfiniBand 網路理論與實踐](#infiniband-網路理論與實踐)
  - [術語定義](#術語定義)
  - [目錄](#目錄)
  - [1. InfiniBand 原理](#1-infiniband-原理)
    - [1.1 InfiniBand 概述](#11-infiniband-概述)
    - [1.2 核心技術特性](#12-核心技術特性)
      - [1.2.1 效能指標](#121-效能指標)
      - [1.2.2 頻寬演進歷史](#122-頻寬演進歷史)
    - [1.3 架構原理](#13-架構原理)
      - [1.3.1 InfiniBand 分層協議模型](#131-infiniband-分層協議模型)
      - [1.3.2 RDMA 技術](#132-rdma-技術)
      - [1.3.3 虛擬通道 (Virtual Lanes)](#133-虛擬通道-virtual-lanes)
    - [1.4 網路拓撲](#14-網路拓撲)
      - [1.4.1 支援的拓撲結構](#141-支援的拓撲結構)
      - [1.4.2 子網管理](#142-子網管理)
    - [1.5 高可用與容錯機制](#15-高可用與容錯機制)
      - [1.5.1 自適應路由 (Adaptive Routing)](#151-自適應路由-adaptive-routing)
      - [1.5.2 冗餘路徑設計 (Redundant Paths)](#152-冗餘路徑設計-redundant-paths)
      - [1.5.3 虛擬通道容錯機制](#153-虛擬通道容錯機制)
      - [1.5.4 硬體級別容錯](#154-硬體級別容錯)
      - [1.5.5 網路級別高可用性](#155-網路級別高可用性)
      - [1.5.6 效能指標與 SLA](#156-效能指標與-sla)
    - [1.6 本章小結](#16-本章小結)
  - [2. InfiniBand 網卡](#2-infiniband-網卡)
    - [2.1 主要廠商和產品](#21-主要廠商和產品)
      - [2.1.1 NVIDIA (原 Mellanox)](#211-nvidia-原-mellanox)
      - [2.1.2 Cornelis Networks (原 Intel OPA)](#212-cornelis-networks-原-intel-opa)
      - [2.1.3 其他廠商](#213-其他廠商)
    - [2.2 網卡架構](#22-網卡架構)
      - [2.2.1 硬體元件](#221-硬體元件)
      - [2.2.2 軟體棧](#222-軟體棧)
    - [2.3 VPI 技術](#23-vpi-技術)
      - [2.3.1 Virtual Protocol Interconnect](#231-virtual-protocol-interconnect)
      - [2.3.2 協議切換](#232-協議切換)
    - [2.4 性能特性](#24-性能特性)
      - [2.4.1 延遲最佳化](#241-延遲最佳化)
      - [2.4.2 頻寬最佳化](#242-頻寬最佳化)
  - [3. InfiniBand 網卡配置](#3-infiniband-網卡配置)
    - [3.1 驅動程式安裝](#31-驅動程式安裝)
      - [3.1.1 Ubuntu/Debian 系統](#311-ubuntudebian-系統)
      - [3.1.2 CentOS/RHEL 系統](#312-centosrhel-系統)
    - [3.2 網路介面配置](#32-網路介面配置)
      - [3.2.1 IPoIB 配置](#321-ipoib-配置)
      - [3.2.2 RoCE 配置](#322-roce-配置)
    - [3.3 效能最佳化配置](#33-效能最佳化配置)
      - [3.3.1 系統參數最佳化](#331-系統參數最佳化)
      - [3.3.2 CPU 親和性配置](#332-cpu-親和性配置)
      - [3.3.3 記憶體大頁配置](#333-記憶體大頁配置)
    - [3.4 安全配置](#34-安全配置)
      - [3.4.1 防火牆配置](#341-防火牆配置)
      - [3.4.2 訪問控制](#342-訪問控制)
  - [4. InfiniBand 網卡相關命令](#4-infiniband-網卡相關命令)
    - [4.1 基礎診斷命令](#41-基礎診斷命令)
      - [4.1.1 裝置發現和狀態查詢](#411-裝置發現和狀態查詢)
      - [4.1.2 網路拓撲發現](#412-網路拓撲發現)
      - [4.1.3 連通性測試](#413-連通性測試)
    - [4.2 效能監控命令](#42-效能監控命令)
      - [4.2.1 效能計數器](#421-效能計數器)
      - [4.2.2 錯誤檢查](#422-錯誤檢查)
      - [4.2.3 鏈路狀態和效能分析](#423-鏈路狀態和效能分析)
    - [4.3 配置管理命令](#43-配置管理命令)
      - [4.3.1 子網管理](#431-子網管理)
      - [4.3.2 虛擬化配置](#432-虛擬化配置)
      - [4.3.3 固件管理](#433-固件管理)
    - [4.4 效能測試工具詳解](#44-效能測試工具詳解)
      - [4.4.1 頻寬測試 (ib_write_bw)](#441-頻寬測試-ib_write_bw)
      - [4.4.2 延遲測試 (ib_send_lat)](#442-延遲測試-ib_send_lat)
      - [4.4.3 RDMA 效能測試](#443-rdma-效能測試)
      - [4.4.4 多連線併發測試](#444-多連線併發測試)
      - [4.4.5 效能基準和調優建議](#445-效能基準和調優建議)
    - [4.5 故障排查命令](#45-故障排查命令)
      - [4.5.1 診斷指令碼](#451-診斷指令碼)
      - [4.5.2 日志分析](#452-日志分析)
  - [5. GPU 場景下 InfiniBand 網卡檢查和測試](#5-gpu-場景下-infiniband-網卡檢查和測試)
    - [5.1 GPU 與 InfiniBand 集成原理](#51-gpu-與-infiniband-集成原理)
      - [5.1.1 GPUDirect RDMA 核心技術](#511-gpudirect-rdma-核心技術)
      - [5.1.2 系統架構要求](#512-系統架構要求)
    - [5.2 環境檢查與配置](#52-環境檢查與配置)
      - [5.2.1 關鍵檢查命令](#521-關鍵檢查命令)
      - [5.2.2 NCCL 環境配置要點](#522-nccl-環境配置要點)
      - [5.2.3 快速環境檢查](#523-快速環境檢查)
    - [5.3 效能測試方法](#53-效能測試方法)
      - [5.3.1 基礎 IB 效能測試](#531-基礎-ib-效能測試)
      - [5.3.2 NCCL 集合通訊測試](#532-nccl-集合通訊測試)
      - [5.3.3 自定義效能測試核心](#533-自定義效能測試核心)
    - [5.4 故障排查要點](#54-故障排查要點)
      - [5.4.1 常見問題診斷](#541-常見問題診斷)
      - [5.4.2 效能最佳化關鍵點](#542-效能最佳化關鍵點)
    - [5.5 監控要點](#55-監控要點)
      - [5.5.1 關鍵監控指標](#551-關鍵監控指標)
      - [5.5.2 健康檢查要點](#552-健康檢查要點)
  - [6. 總結](#6-總結)
    - [6.1 關鍵要點](#61-關鍵要點)
    - [6.2 最佳實踐建議](#62-最佳實踐建議)
  - [7. 推薦參考資料](#7-推薦參考資料)
    - [7.1 官方文件和標準](#71-官方文件和標準)
    - [7.2 開源社群資源](#72-開源社群資源)
    - [7.3 技術白皮書和研究論文](#73-技術白皮書和研究論文)
    - [7.4 實用工具和指令碼](#74-實用工具和指令碼)
    - [7.5 培訓和認證](#75-培訓和認證)
    - [7.6 社群支援](#76-社群支援)
  - [8. 參考文獻](#8-參考文獻)

---

## 1. InfiniBand 原理

### 1.1 InfiniBand 概述

`InfiniBand` (IB) 是一種高效能、低延遲的網路互連技術，專為高效能運算 (HPC)、資料中心和企業級應用設計。`InfiniBand` 架構由 `InfiniBand Trade Association` (IBTA) 標準化，提供了比傳統乙太網更優越的效能特性 [1]。

### 1.2 核心技術特性

#### 1.2.1 效能指標

根據 `IBTA` 規範，`InfiniBand` 提供以下核心性能特性：

- **高頻寬**: 支援從 8 Gbps (SDR) 到 775 Gbps (XDR) 的資料傳輸速率（有效頻寬）
- **超低延遲**: _端到端延遲_ 通常為 1.6-3 微秒 [2]，在理想實驗室環境下可低至 0.5 微秒
- **高可靠性**: 硬體級別的錯誤檢測和糾正機制，BER < 10⁻¹⁵
- **可擴展性**: 支援數萬個節點的大規模叢集部署

**關鍵延遲概念說明**:

**端到端延遲：**

> **端到端延遲**是指從應用程式發起資料傳輸請求到接收方應用程式收到資料的完整時間 ，包含了整個資料傳輸路徑上的所有延遲元件。**端到端延遲的組成部分** ：
>
> - 應用層處理時間 ：應用程式準備和處理資料的時間
> - 作業系統開銷 ：系統呼叫、核心處理時間
> - 介面卡延遲 ：網路介面卡的硬體處理時間
> - 傳輸延遲 ：資料在網路介質中的傳播時間
> - 交換機延遲 ：資料包在交換機中的處理和轉發時間
> - 接收端處理 ：接收方的解包和應用層處理時間

**介面卡延遲：**

> **介面卡延遲**是指網路介面卡（HCA - Host Channel Adapter） 硬件本身 的處理延遲，這是端到端延遲的一個重要組成部分。**介面卡延遲包括** ：
>
> - 資料包封裝/解封裝時間
> - 硬體佇列處理時間
> - RDMA 引擎處理時間
> - PCIe 匯流排傳輸時間
> - 內部緩衝和排程延遲

#### 1.2.2 頻寬演進歷史

| 標準 | 單通道速率    | x4 鏈路速率  | 有效頻寬 (x4) | 介面卡延遲 | 发布年份 | 編碼效率        |
| ---- | ------------- | ------------ | ------------- | ---------- | -------- | --------------- |
| SDR  | 2.5 Gbps      | 10 Gbps      | 8 Gbps        | 5 μs       | 2003     | 8b/10b          |
| DDR  | 5 Gbps        | 20 Gbps      | 16 Gbps       | 2.5 μs     | 2005     | 8b/10b          |
| QDR  | 10 Gbps       | 40 Gbps      | 32 Gbps       | 1.3 μs     | 2008     | 8b/10b          |
| FDR  | 14.0625 Gbps  | 56.25 Gbps   | 54.54 Gbps    | 0.7 μs     | 2011     | 64b/66b         |
| EDR  | 25.78125 Gbps | 103.125 Gbps | 100 Gbps      | < 0.5 μs   | 2014     | 64b/66b         |
| HDR  | 53.125 Gbps   | 212.5 Gbps   | 200 Gbps      | < 0.6 μs   | 2017     | 64b/66b (PAM-4) |
| NDR  | 106.25 Gbps   | 425 Gbps     | 400 Gbps      | < 0.6 μs   | 2020     | 64b/66b (PAM-4) |
| XDR  | 200 Gbps      | 800 Gbps     | 775.76 Gbps   | < 0.6 μs   | 2023     | 64b/66b (PAM-4) |

**有效頻寬計算公式**:

```text
實際頻寬 = 單通道速率 × 通道數 × 編碼效率

計算示例:
- NDR x4：106.25 Gbps × 4 × 96.97% ≈ 400 Gbps
- XDR x4：200 Gbps × 4 × 96.97% ≈ 775.76 Gbps
```

**說明**:

- **單通道速率**: 每個物理通道的原始資料速率
- **x4 鏈路**: InfiniBand 標準鏈路配置，使用 4 個物理通道
- **有效頻寬**: 扣除編碼開銷後的實際可用頻寬
- **HDR/NDR 行口徑**: 表中 HDR 200 Gbps / NDR 400 Gbps 為含 RS-FEC 前向糾錯開銷後的官方有效頻寬；上面的公式只體現 64b/66b 編碼效率（不含 RS-FEC），因此對 HDR/NDR 會算出偏高的數值（如 NDR：425 × 96.97% ≈ 412 Gbps ≠ 400 Gbps），對 XDR 則恰好吻合（800 × 96.97% ≈ 775.76 Gbps）
- **介面卡延遲**: 網路介面卡的硬體處理延遲，不包括傳輸延遲和應用層處理時間
- **編碼效率**: 8b/10b 編碼效率為 80%，64b/66b 編碼效率為 96.97%
- **PAM-4**: Pulse Amplitude Modulation 4-level，四電平脈衝幅度調製
- **NDR 发布**: 2020 年規範釋出，2021 年商用化
- **XDR 狀態**: 2023 年 10 月規範釋出 [3]，支持 800Gb/s 端口速度和 1.6Tb/s 交換機間連線，產品已於 2024 年下半年開始部署

_資料來源: `IBTA` 官方規範 [4] 和 `Wikipedia InfiniBand` 規格表 [5]_

### 1.3 架構原理

#### 1.3.1 InfiniBand 分層協議模型

根據 `IBTA` 架構規範，`InfiniBand` 採用四層分層架構設計，每層負責特定的網路功能：

**協議棧概覽**:

```text
┌─────────────────────────────────────┐
│        應用層 (Applications)         │
├─────────────────────────────────────┤
│      傳輸層 (Transport Layer)        │  ← QP管理、RDMA操作
├─────────────────────────────────────┤
│       網路層 (Network Layer)         │  ← 路由、子網管理
├─────────────────────────────────────┤
│        鏈路層 (Link Layer)           │  ← 流控、虛擬通道
├─────────────────────────────────────┤
│       物理層 (Physical Layer)        │  ← 訊號傳輸、編碼
└─────────────────────────────────────┘
```

**各層詳細功能**:

1. **物理層 (Physical Layer)**
   - **訊號傳輸**: 負責電氣訊號的編碼、調製和傳輸
   - **連線介質**: 支援銅纜 (DAC/AOC) 和光纖 (SR4/LR4) 連線
   - **鏈路訓練**: 自動協商速率、FEC (Forward Error Correction) 和通道參數
   - **錯誤檢測**: 硬體級別的 BER (Bit Error Rate) 監控和糾正

2. **鏈路層 (Link Layer)**
   - **可靠傳輸**: 基於 ACK/NAK 機制的資料包確認和重傳
   - **流量控制**: 基於信用 (Credit) 的端到端流控機制
   - **虛擬通道**: 支持最多 16 個 VL (Virtual Lanes) 實現 QoS 隔離
   - **擁塞管理**: 硬體級別的擁塞控制和避免機制

3. **網路層 (Network Layer)**
   - **路由功能**: 基於 LID (Local Identifier) 的包轉發
   - **子網管理**: 透過 SMP (Subnet Management Packets) 進行拓撲發現
   - **分割槽管理**: 基於 P_Key (Partition Key) 的網路隔離
   - **服務級別**: SL (Service Level) 到 VL 的映射管理

4. **傳輸層 (Transport Layer)**
   - **佇列對管理**: QP (Queue Pairs) 的建立、連線和銷燬
   - **RDMA 操作**: 支持 Send/Receive、Read、Write、Atomic 操作
   - **消息排序**: 保證同一 QP 內訊息的有序傳輸
   - **錯誤恢復**: 傳輸級別的超時和重傳機制

#### 1.3.2 RDMA 技術

`Remote Direct Memory Access` (RDMA) 是一種高效能網路通訊技術，實現了應用程式間的直接記憶體訪問。RDMA 可以基於不同的網路架構實現：

**RDMA 實現方式**:

- **InfiniBand RDMA**: InfiniBand 網路原生支援 RDMA，提供最佳效能和最低延遲
- **RoCE (RDMA over Converged Ethernet)**: 在乙太網基礎設施上實現 RDMA
  - **RoCE v1**: 基於乙太網 Layer 2 (Ethertype 0x8915)，限制在單一廣播域，不可路由 [6]
  - **RoCE v2**: 基於 UDP/IP，支援跨子網路由，應用更廣泛 [6]
- **iWARP**: 基於 TCP/IP 的 RDMA 實現

在 InfiniBand 網路中，RDMA 是核心特性，具有以下優勢：

**核心特性**:

- **零複製傳輸 (Zero Copy)**: 資料直接在應用程式記憶體間傳輸，無需核心緩衝區複製
- **核心旁路 (Kernel Bypass)**: 繞過作業系統核心，減少上下文切換開銷
- **硬體解除安裝 (Hardware Offload)**: 網路協議處理由硬體完成，釋放 CPU 資源
- **使用者空間操作**: 應用程式可直接操作網路硬體，無需系統呼叫

**RDMA 操作類型**:

1. **Send/Receive**: 雙邊操作，需要接收方預先準備接收緩衝區
2. **RDMA Read**: 單邊操作，直接讀取遠端記憶體內容
3. **RDMA Write**: 單邊操作，直接寫入遠端記憶體
4. **Atomic Operations**: 原子操作，支持 Compare-and-Swap、Fetch-and-Add 等

**效能優勢** (基於 InfiniBand RDMA):

- **超低延遲**: InfiniBand RDMA 理想條件下可達 1.6 μs [1]，生產環境典型延遲為 1.6-3 μs
- **高頻寬利用率**: 可達到理論頻寬的 95% 以上
- **低 CPU 開銷**: CPU 利用率通常低於 5%

**RDMA 技術對比**:

| 實現方式            | 典型延遲     | 頻寬利用率 | 部署複雜度 | 基礎設施要求 | 資料來源  |
| ------------------- | ------------ | ---------- | ---------- | ------------ | --------- |
| **InfiniBand RDMA** | 1.6-3 μs [2] | > 95%      | 中等       | 專用 IB 網路 | FS.com    |
| **RoCE v2**         | 1.3-6 μs [6] | 85-90%     | 複雜       | 無損乙太網   | Wikipedia |
| **iWARP**           | 3-15 μs [6]  | 70-85%     | 簡單       | 標準乙太網   | Wikipedia |

**延遲對比說明**:

- **交換機延遲**: InfiniBand 交換機埠延遲約 100ns，乙太網交換機約 230ns [6]
- **最佳性能**: RoCE HCA 最低延遲可達 1.3μs，而 iWARP 最低約 3μs (2011 年資料) [6]
- **實際應用**: InfiniBand 在理想條件下可達 1.6μs，生產環境通常為 1.6-3μs [2]

**與乙太網和 RoCE 的詳細對比**:

| 特性             | InfiniBand     | 乙太網       | RoCE v2     |
| ---------------- | -------------- | ------------ | ----------- |
| **端到端延遲**   | 1.6-3 μs [2]   | 20-80 μs [7] | 5-6 μs [2]  |
| **CPU 開銷**     | < 5%           | 15-30%       | 5-10%       |
| **頻寬利用率**   | > 95%          | 60-80%       | 85-90%      |
| **錯誤率 (BER)** | < 10⁻¹⁵        | 10⁻¹²        | 10⁻¹³       |
| **流量控制**     | 硬體級信用機制 | 軟體實現     | PFC + ECN   |
| **RDMA 支持**    | 原生支持       | 不支持       | 原生支持    |
| **網路管理**     | 集中式 SM      | 分布式       | 分布式      |
| **路由能力**     | 子網內/跨子網  | 全路由       | 全路由 (v2) |
| **部署複雜度**   | 中等           | 簡單         | 複雜        |
| **基礎設施成本** | 高             | 低           | 中等        |

**技術註釋**:

1. **InfiniBand 延遲特性**: 根據最新技術資料，InfiniBand 在理想條件下可達 1.6μs，生產環境典型值為 1.6-3μs [2]
2. **RoCE v2 延遲特性**: 生產環境典型延遲為 5-6μs，理想條件下最低可達 1.3μs [2,6]
3. **延遲差異原因**: InfiniBand 交換機延遲約 100ns，乙太網交換機約 230ns [6]
4. **RDMA 技術優勢**: 透過硬體解除安裝顯著降低 CPU 開銷
5. **PFC+ECN**: Priority Flow Control + Explicit Congestion Notification，RoCE v2 的無損網路配置
6. **乙太網延遲**: 範圍為 20-80μs [7]，具體取決於網路配置和負載
7. **基礎設施複用**: RoCE v2 可複用現有乙太網基礎設施，但需要無損網路配置

**RoCE (RDMA over Converged Ethernet) 特點**:

- **技術優勢**:
  - 利用現有乙太網基礎設施，降低部署成本
  - 支援標準乙太網管理工具和協議
  - 與傳統網路裝置相容性好
- **技術挑戰**:
  - 需要配置無損乙太網 (PFC/ECN)
  - 網路調優複雜度較高
  - 效能略低於專用 InfiniBand 網路

#### 1.3.3 虛擬通道 (Virtual Lanes)

InfiniBand 的虛擬通道 (`Virtual Lanes`, VL) 是一種在單一物理鏈路上建立多個邏輯通道的技術，類似於乙太網中的 VLAN 概念，但在實現機制和應用場景上有顯著差異。

**基本概念與 VLAN 類比**:

InfiniBand 支援多達 **16** 個虛擬通道 (VL0-VL15)，其中：

- **VL15**: 專用於子網管理流量，不可用於資料傳輸
- **VL0-VL14**: 可用於資料流量，支援靈活配置

| 特性對比     | InfiniBand VL         | 乙太網 VLAN           |
| ------------ | --------------------- | --------------------- |
| **隔離層次** | 物理鏈路層            | 資料鏈路層            |
| **數量限制** | 最多 16 個 (VL0-VL15) | 最多 4094 個 (1-4094) |
| **標識方式** | VL 字段 (4 bits)      | VLAN Tag (12 bits)    |
| **流量控制** | 每 VL 獨立的信用機制  | 共享物理埠頻寬      |
| **服務品質** | 硬體級 QoS 保證       | 軟體 QoS 實現         |
| **死鎖避免** | 原生支持              | 需要額外協議          |

**技術實現機制**:

1. **硬體級隔離**

   ```text
   物理鏈路
   ├── VL0: 高優先順序流量 (40% 頻寬)
   ├── VL1: 中優先順序流量 (30% 頻寬)
   ├── VL2: 低優先順序流量 (20% 頻寬)
   ├── VL3: 管理流量 (5% 頻寬)
   └── VL15: 子網管理 (5% 頻寬，專用)
   ```

2. **信用流控機制**
   - 每個 VL 維護獨立的傳送/接收信用計數器
   - 傳送方必須獲得接收方信用才能傳送資料
   - 避免了傳統乙太網的丟包重傳機制

3. **服務級別對映 (SL to VL Mapping)**

   ```text
   # 配置示例：將不同服務級別對映到虛擬通道
   SL0 -> VL0  # 最高優先順序 (AI訓練流量)
   SL1 -> VL1  # 高優先順序 (儲存流量)
   SL2 -> VL2  # 中優先順序 (管理流量)
   SL3 -> VL3  # 低優先順序 (監控流量)
   ```

**核心功能詳解**:

1. **服務品質保證 (QoS)**
   - **頻寬分配**: 每個 VL 可配置最小/最大頻寬保證
   - **優先順序排程**: 支援嚴格優先順序 (SP) 和加權公平佇列 (WFQ)
   - **延遲控制**: 高優先順序 VL 獲得更低的排隊延遲

   **配置示例**:

   ```text
   # OpenSM 配置文件（opensm.conf）QoS 相關鍵示例
   # 鍵名以 opensm.conf(5) 為準（opensm 原始碼 osm_subnet.c 的選項表）：
   # qos_high_limit / qos_vlarb_high / qos_vlarb_low / qos_sl2vl，
   # 另有按裝置類型細分的 qos_ca_* / qos_sw0_* / qos_swe_* / qos_rtr_* 變體
   qos_high_limit  0             # VL high priority 門限
   qos_vlarb_high  0:40,1:30     # VL 仲裁表 high 段（VL:權重 對）
   qos_vlarb_low   0:20,1:10     # VL 仲裁表 low 段
   qos_sl2vl       0,1,2,3       # SL 到 VL 映射表（逐 SL 給出目標 VL）
   ```

2. **死鎖避免機制**
   - **Turn Model**: 透過限制路由轉向避免迴圈依賴
   - **VL 分層**: 不同 VL 形成有向無環圖 (DAG)
   - **Escape VL**: VL0 通常作為逃逸通道，保證無死鎖路由

   **死鎖避免示例**:

   ```text
   網路拓撲: A ↔ B ↔ C ↔ A (環形)

   傳統路由: 可能形成死鎖
   A→B→C→A (所有流量使用同一VL)

   VL 分層路由: 避免死鎖
   A→B: 使用 VL0
   B→C: 使用 VL1
   C→A: 使用 VL0 (降級到逃逸VL)
   ```

3. **頻寬管理與分配**
   - **靜態分配**: 預先配置每個 VL 的頻寬份額
   - **動態調整**: 根據實際流量需求動態調整頻寬
   - **突發處理**: 允許 VL 臨時使用其他 VL 的空閒頻寬

   **頻寬分配策略**:

   ```text
   # 典型 AI 叢集 VL 配置
   VL0: 60% - AI 訓練通訊 (AllReduce, AllGather)
   VL1: 20% - 儲存 I/O 流量
   VL2: 10% - 管理和監控流量
   VL3: 5%  - 備用/突发流量
   VL15: 5% - 子網管理 (固定)
   ```

**實際應用場景**:

1. **AI 訓練叢集最佳化**

   ```text
   # NCCL 通信模式 VL 映射
   VL0: AllReduce 操作 (最高優先順序)
   VL1: Parameter Server 通信
   VL2: 資料載入和檢查點
   VL3: 監控和日誌傳輸
   ```

2. **多租戶環境隔離**

   ```text
   # 租戶流量隔離
   VL0: 租戶 A (GPU 叢集)
   VL1: 租戶 B (CPU 叢集)
   VL2: 租戶 C (儲存叢集)
   VL3: 共享服務 (監控、日志)
   ```

3. **混合工作負載管理**

   ```text
   # 工作負載類型分離
   VL0: 實時推理服務 (低延遲要求)
   VL1: 批次訓練任務 (高吞吐要求)
   VL2: 資料預處理 (中等優先順序)
   VL3: 備份和歸檔 (最低優先順序)
   ```

**效能優勢**:

- **延遲隔離**: 高優先順序流量不受低優先順序流量影響
- **頻寬保證**: 關鍵應用獲得最小頻寬保證
- **無丟包傳輸**: 信用流控機制確保無緩衝區溢位
- **硬件加速**: 所有 VL 處理在硬體層面完成，CPU 開銷極低

**配置和管理**:

```bash
# 檢視當前 VL 配置
ibstat                       # 檢視裝置與埠狀態（ibstat 僅支援 -l/-s/-p/-h/-V，沒有 -v 選項）
perfquery -a                 # 查詢子網內所有埠的 PM 效能計數器（按埠計數，不分 VL）

# OpenSM VL 配置
opensm -c /etc/opensm/opensm.conf  # 使用自定義 VL 配置

# 應用層 VL 選擇
ibv_modify_qp(..., IBV_QP_PATH_MIG_STATE, ...)  # 設定 QP 的 VL
```

透過虛擬通道技術，InfiniBand 在單一物理鏈路上實現了類似 VLAN 的邏輯隔離，但提供了更強的效能保證和更低的延遲，特別適合對網路效能要求極高的 HPC 和 AI 應用場景。

### 1.4 網路拓撲

#### 1.4.1 支援的拓撲結構

InfiniBand 支援多種網路拓撲結構，每種拓撲都有其特定的應用場景和效能特點：

1. **點對點連線 (Point-to-Point)**
   - **特點**: 直接連線兩個裝置，無需交換機
   - **應用場景**: 小規模雙節點配置、儲存直連
   - **性能**: 延遲最低 (< 1μs)，但擴展性有限
   - **成本**: 最低，適合簡單應用

2. **交換機網路 (Switched Network)**
   - **特點**: 透過交換機連線多個裝置
   - **拓撲類型**: 支持星型、環型等基礎拓撲
   - **應用場景**: 中小規模叢集 (< 100 節點)
   - **擴展性**: 受交換機埠數限制

3. **Fat Tree 拓撲**
   - **特點**: 高頻寬、無阻塞的樹形結構
   - **應用場景**: 大規模 HPC 叢集、AI 訓練叢集
   - **效能優勢**:
     - **1:1 Over-subscription**: 上行頻寬等於下行頻寬，無阻塞，適合通訊密集型應用
     - **2:1 Over-subscription**: 上行頻寬為下行頻寬的一半，常見配置，價效比高
     - **3:1 Over-subscription**: 上行頻寬為下行頻寬的三分之一，經濟型配置

   **典型 Fat Tree 配置示例**:

   ```text
   Spine 層 (核心交換機)
        ├── Leaf 交換機 1 ── 伺服器 1-24
        ├── Leaf 交換機 2 ── 伺服器 25-48
        └── Leaf 交換機 3 ── 伺服器 49-72

   配置參數:
   - 36 端口 Leaf + 36 端口 Spine
   - Over-subscription: 2:1 (12 上行端口 vs 24 下行端口)
   ```

4. **Torus/Mesh 拓撲**
   - **特點**: 多維網格拓撲，常用於超級計算機
   - **拓撲類型**:
     - **2D Torus**: 每個節點連線 4 個鄰居，適合中等規模叢集
     - **3D Torus**: 每個節點連線 6 個鄰居，適合大規模超算
     - **高維 Torus**: 支援更高維度，進一步提升連線性
   - **技術優勢**:
     - 提供多條等長路徑，負載均衡效果好
     - 具備良好的容錯性和可擴展性
     - 網路直徑小，平均跳數低
   - **應用場景**: 超級計算機、大規模科學計算叢集

**拓撲選擇指南**:

| 拓撲類型       | 節點規模 | 成本 | 延遲 | 頻寬 | 容錯性 | 適用場景           |
| -------------- | -------- | ---- | ---- | ---- | ------ | ------------------ |
| **點對點**     | 2        | 最低 | 最低 | 高   | 低     | 儲存直連、簡單應用 |
| **交換機網路** | < 100    | 低   | 低   | 中   | 中     | 中小規模叢集       |
| **Fat Tree**   | 100-10K  | 中   | 中   | 最高 | 高     | HPC、AI 訓練       |
| **Torus**      | 1K-100K  | 高   | 中   | 高   | 最高   | 超級計算機         |

#### 1.4.2 子網管理

InfiniBand 網路採用集中式管理模式，需要子網管理器 (Subnet Manager, SM) 的原因包括：

1. **網路複雜性管理**:
   - InfiniBand 網路通常包含數百到數萬個節點
   - 複雜的拓撲結構 (Fat Tree、Torus 等) 需要統一協調
   - 動態網路變化 (節點上下線、鏈路故障) 需要實時響應

2. **地址分配與管理**:
   - **LID (Local Identifier) 分配**: 每個埠需要唯一的 16 位本地識別符號
   - **GUID (Global Unique Identifier) 管理**: 64 位全域性唯一識別符號的註冊和維護
   - **地址冲突避免**: 確保網路中不存在重複的地址分配

3. **路由表計算與分發**:
   - **最優路徑計算**: 基於網路拓撲計算最短路徑或負載均衡路徑
   - **路由表分发**: 將計算結果分發到所有交換機的轉發表
   - **多路徑支援**: 配置 ECMP (Equal Cost Multi-Path) 實現負載均衡

4. **網路分割槽與安全**:
   - **P_Key (Partition Key) 管理**: 實現網路邏輯分割槽和訪問控制
   - **安全隔離**: 不同分割槽間的流量完全隔離，類似 VLAN 概念
   - **許可權控制**: 控制節點間的通訊許可權

5. **服務品質保證**:
   - **虛擬通道對映**: 配置 SL (Service Level) 到 VL (Virtual Lane) 的映射
   - **QoS 策略**: 實現不同優先順序流量的差異化服務
   - **頻寬分配**: 為不同應用分配專用的網路資源

6. **故障檢測與恢復**:
   - **鏈路狀態監控**: 實時監控所有鏈路的健康狀態
   - **故障自動恢復**: 檢測到故障時自動重新計算路由
   - **網路重構**: 在拓撲變化時快速重新配置網路

**與乙太網的對比**:

| 特性           | InfiniBand (集中式 SM) | 乙太網 (分布式)       |
| -------------- | ---------------------- | --------------------- |
| **管理模式**   | 集中式子網管理器       | 分散式自學習          |
| **地址分配**   | SM 統一分配 LID        | DHCP 或靜態配置       |
| **路由計算**   | SM 全域性最優計算        | 分散式生成樹/OSPF     |
| **故障恢復**   | 快速重新計算 (秒級)    | 收斂時間較長 (分鐘級) |
| **QoS 配置**   | 集中式策略管理         | 分布式配置            |
| **網路可見性** | 全域性拓撲檢視           | 區域性檢視              |

InfiniBand 網路需要子網管理器 (Subnet Manager, SM) 進行集中管理，OpenSM 是最常用的開源實現：

**核心功能**:

- **拓撲發現**: 自動發現網路中的所有節點和鏈路
- **LID 分配**: 為每個埠分配唯一的 Local Identifier
- **路由計算**: 計算最優路徑並配置轉發表
- **P_Key 管理**: 配置分割槽金鑰實現網路隔離
- **VL 映射**: 配置服務級別到虛擬通道的對映
- **故障處理**: 檢測鏈路故障並重新計算路由

**OpenSM 部署模式**:

1. **單 SM 模式**

   ```bash
   # 啟動主 SM（-g 指定繫結的本地埠 GUID；注意 -D 是日志/除錯標誌位，不是綁 GUID）
   sudo opensm -g 0x2c903000a0b1c
   ```

2. **主備 SM 模式 (Master/Standby)**

   ```bash
   # 主 SM (優先順序 15)
   sudo opensm -p 15 -g 0x2c903000a0b1c

   # 備 SM (優先順序 10)
   sudo opensm -p 10 -g 0x2c903000a0b1d
   ```

3. **多 SM 高可用模式**
   - 支援多個 SM 同時執行
   - 自動選舉機制確定 Master SM
   - 故障時自動切換，RTO < 30 秒

**SM Failover 機制**:

- **心跳檢測**: SM 之間定期交換心跳訊息
- **優先順序選舉**: 基於配置優先順序選擇 Master SM
- **狀態同步**: Standby SM 保持網路狀態同步
- **快速切換**: 故障檢測後 10-30 秒內完成切換

### 1.5 高可用與容錯機制

`InfiniBand` 網路提供多種容錯機制確保高可用性，這些機制是 `InfiniBand` 在關鍵任務環境中廣泛應用的重要基礎：

#### 1.5.1 自適應路由 (Adaptive Routing)

**技術原理**:

自適應路由是 `InfiniBand` 網路的核心特性之一，透過硬體級別的智慧路由選擇實現最優效能：

- **動態負載均衡**:
  - 實時監控所有可用路徑的負載狀態
  - 根據佇列深度、鏈路利用率自動選擇最優路徑
  - 支援包級別的負載分散，避免單一路徑過載
  - 典型負載均衡效果可提升 15-30% 的整體吞吐量

- **擁塞避免**:
  - 硬體級別的擁塞檢測機制，檢測延遲 < 1μs
  - 檢測到擁塞時自動切換到備用路徑
  - 支援基於信用的流控機制，避免緩衝區溢位
  - 擁塞恢復時間通常 < 10μs

- **故障繞行**:
  - 鏈路故障檢測時間 < 100ms
  - 自動重新路由流量到健康路徑
  - 支援預計算備用路徑，切換時間 < 1ms
  - 故障恢復後自動回切到最優路徑

**自適應路由演算法**:

1. **DFSSSP (Distributed Fat-tree Shortest-Spanning-tree Protocol)**:
   - 專為 Fat Tree 拓撲最佳化
   - 支援多路徑負載均衡
   - 自動避免網路死鎖

2. **LASH (Layered Shortest Path)**:
   - 基於虛擬層的路由演算法
   - 適用於任意拓撲結構
   - 提供死鎖避免保證

3. **DOR (Dimension Order Routing)**:
   - 適用於 Torus 拓撲
   - 確定性路由，延遲可預測
   - 簡單高效的實現

**配置示例**:

```bash
# 啟用自適應路由 (OpenSM)
# -R 選擇路由引擎（ftree = fat tree 最佳化路由）；-Q 無參數，含義是啟用 QoS 配置；
# -P 接的是分割槽配置檔案路徑，不是分割槽號——不要寫 -P 0x0001 這類值
sudo opensm -R ftree -Q

# 獲取埠連線報告 (顯示 LID、埠號、GUID、鏈路寬度、速度等信息)
sudo ibnetdiscover -p | grep -E "Switch|CA"

# 監控路徑利用率
sudo ibqueryerrors -k -c -d
```

#### 1.5.2 冗餘路徑設計 (Redundant Paths)

**多路徑架構**:

- **Fat Tree 拓撲優勢**:
  - 提供 2^k 條等價路徑 (k 為 Fat Tree 參數)
  - 上行和下行頻寬完全對稱
  - 任意兩節點間至少有 4 條獨立路徑

- **鏈路聚合 (Link Aggregation)**:
  - 支持 2-8 條物理鏈路聚合
  - 聚合頻寬可達單鏈路的 N 倍
  - 單鏈路故障時自動負載重分配
  - 聚合鏈路的可用性達到 99.99%+

- **故障隔離機制**:
  - 單點故障影響範圍 < 總網路的 1%
  - 支援熱插拔，維護時無需停機
  - 故障節點自動隔離，不影響其他通訊

**冗餘設計最佳實踐**:

```bash
# 配置鏈路聚合
sudo mlxconfig -d /dev/mst/mt4119_pciconf0 set LINK_TYPE_P1=IB
sudo mlxconfig -d /dev/mst/mt4119_pciconf0 set LINK_TYPE_P2=IB

# 驗證多路徑配置
sudo iblinkinfo | grep -E "Width|Speed"

# 監控鏈路狀態
sudo ibstatus
```

#### 1.5.3 虛擬通道容錯機制

**死鎖避免技術**:

- **VL 分配策略**:
  - 不同方向的流量使用不同 VL
  - 上行流量使用 VL0，下行流量使用 VL1
  - 東西向流量使用 VL2-VL3
  - 管理流量專用 VL15

- **優先順序保證**:
  - 關鍵應用 (如 MPI) 使用高優先順序 VL
  - 儲存流量使用中等優先順序 VL
  - 管理流量使用最高優先順序 VL15
  - 支持 16 個服務級別 (SL0-SL15，SL 字段 4 bits)，經 SL→VL 映射落到 16 個 VL 上（見 §1.3.3）

- **流量隔離**:
  - 不同租戶使用獨立的 VL
  - 應用間流量完全隔離
  - 支援基於 P_Key 的分割槽隔離

**VL 配置示例**:

```bash
# VL 數量與 SL2VL/VL 仲裁映射不在命令行上配，統一走 opensm.conf：
# qos_sl2vl（SL→VL 映射表）、qos_vlarb_high / qos_vlarb_low（VL 仲裁表）、
# qos_high_limit（high priority 門限）等 qos_* 鍵；改完重啟 opensm 生效
sudo nano /etc/opensm/opensm.conf

# -Q 無參數（啟用 QoS 配置）；-V 也無參數（日誌級別直接開到 0xFF 全開）
sudo opensm -Q -V

# 查看 VL 仲裁配置
sudo saquery -g | grep VLArb
```

#### 1.5.4 硬體級別容錯

**前向糾錯 (FEC)**:

- **Reed-Solomon FEC**:
  - 支援單位元和多位元錯誤糾正
  - 糾錯能力: 檢測 3 位錯誤，糾正 1 位錯誤
  - 對效能影響 < 1%
  - 誤位元速率改善 10^3 - 10^4 倍

- **LDPC (Low-Density Parity-Check)**:
  - 用於高速鏈路 (HDR/NDR)
  - 更強的糾錯能力
  - 適應性編碼，根據通道品質調整

**重傳機制**:

- **鏈路層重傳**:
  - 自動檢測丟包並重傳
  - 重傳延遲 < 10μs
  - 支援選擇性重傳 (SACK)
  - 重傳成功率 > 99.9%

- **端到端重傳**:
  - 傳輸層的可靠性保證
  - 超時重傳機制
  - 擁塞控制整合

**訊號完整性監控**:

- **眼圖監控**:
  - 實時監控訊號品質
  - 自動調整均衡器參數
  - 預測性維護告警

- **BER 監控**:
  - 實時誤位元速率統計
  - 閾值告警機制
  - 歷史趨勢分析

```bash
# 監控 FEC 狀態
sudo mlxlink -d /dev/mst/mt4119_pciconf0 -p 1 --fec

# 檢視誤位元速率統計
sudo mlxlink -d /dev/mst/mt4119_pciconf0 -p 1 --ber

# 監控訊號品質
sudo mlxlink -d /dev/mst/mt4119_pciconf0 -p 1 --eye
```

#### 1.5.5 網路級別高可用性

**子網管理器高可用**:

- **主備模式**:
  - 主 SM 故障時備 SM 自動接管
  - 切換時間 < 30 秒
  - 狀態同步確保無縫切換

- **多 SM 協調**:
  - 支援多個 SM 同時執行
  - 基於優先順序的選舉機制
  - 分散式狀態管理

**網路分割槽容錯**:

- **P_Key 隔離**:
  - 不同分割槽完全隔離
  - 單分割槽故障不影響其他分割槽
  - 支援動態分割槽重配置

- **跨子網通訊**:
  - 支援多子網架構
  - 子網間路由器提供連線
  - 單子網故障時其他子網正常執行

#### 1.5.6 效能指標與 SLA

> 注：本節列出的可用性、MTBF/MTTR、故障檢測/恢復、延遲抖動、丟包率與負載均衡效率均為**工程經驗值**（容量規劃與運維基準參考口徑），不是 IBTA 規範值，也不是廠商質保數字；SLA 以具體採購合同與裝置規格書為準。

**可用性指標**:

- **網路可用性**: 99.99% (年停機時間 < 53 分钟)
- **MTBF (平均故障間隔)**: > 100,000 小時
- **MTTR (平均修復時間)**: < 30 分钟
- **故障檢測時間**: < 100ms
- **故障恢復時間**: < 1 秒

**效能保證**:

- **延遲抖動**: < 100ns (99.9% 分位數)
- **丟包率**: < 10^-12 (無損網路)
- **頻寬利用率**: > 95% (正常負載下)
- **負載均衡效率**: > 90%

**監控與告警**:

```bash
# 網路健康檢查指令碼
#!/bin/bash
# 檢查鏈路狀態
ibstatus | grep -E "State|Rate"

# 檢查錯誤計數
ibqueryerrors -k -c

# 檢查 SM 狀態
sminfo | grep -E "Priority|State"

# 效能測試
ib_write_bw -d mlx5_0 -i 1 -s 1048576
```

這種多層次的容錯機制確保了 `InfiniBand` 網路在大規模 `HPC` 和 `AI` 叢集中的高可靠性，是其在關鍵任務環境中廣泛應用的重要基礎。

### 1.6 本章小結

本章全面介紹了 `InfiniBand` 網路的核心原理和技術特性：

**核心技術優勢**:

- **超高性能**: 支持 `775 Gbps` 頻寬，`1.6-3μs` 超低延遲
- **先進架構**: 四層協議棧設計，硬體級 `RDMA` 支持
- **智能管理**: 集中式子網管理，自適應路由最佳化
- **高可靠性**: 多層次容錯機制，`99.99%` 可用性保證

**關鍵技術特性**:

1. **分層協議模型**: 物理層、鏈路層、網路層、傳輸層各司其職
2. **RDMA 技術**: 零複製、核心旁路、硬體解除安裝的高效通訊
3. **虛擬通道**: `16` 個 VL 提供 QoS 保證和死鎖避免
4. **網路拓撲**: 支援點對點、Fat Tree、Torus 等多種拓撲
5. **容錯機制**: 自適應路由、冗餘路徑、硬體級糾錯

**應用價值**:

- 為 `HPC` 和 `AI` 叢集提供高效能網路基礎設施
- 支援大規模平行計算和深度學習訓練
- 確保關鍵任務應用的高可用性和可靠性

---

## 2. InfiniBand 網卡

### 2.1 主要廠商和產品

#### 2.1.1 NVIDIA (原 Mellanox)

NVIDIA 是 InfiniBand 市場的領導者，在 2025 年繼續保持主導地位。根據第三方市場資料，NVIDIA 在 InfiniBand 網路裝置市場佔據主導地位，其 InfiniBand 產品銷售額在 2025 財年第一季度（2024 年 2-4 月）達 27.1 億美元，佔其網路業務收入的 85.5% [8]（第三方估算口徑，非 NVIDIA 財報直接披露；數字隨季度更新，引用前請以 NVIDIA 最新 10-Q 複核）：

**ConnectX 系列**:

- **ConnectX-3**: 支持 QDR (40 Gbps)，ConnectX-3 Pro 支持 FDR (56 Gbps)
- **ConnectX-4**: 支持 EDR (100 Gbps)
- **ConnectX-5**: 支持 EDR，增強的 RDMA 功能
- **ConnectX-6**: 支持 HDR (200 Gbps)
- **ConnectX-7**: 支持 NDR (400 Gbps)
- **ConnectX-8**: 支持 XDR (800 Gbps)，配備 NVIDIA In-Network Computing 加速引擎，專為萬億參數級 AI 工廠和科學計算工作負載設計 (已開始出貨) [9]

**BlueField DPU 系列**:

- 集成 ARM 處理器的資料處理單元
- 支援網路、儲存和安全解除安裝
- 適用於雲原生和邊緣計算場景

#### 2.1.2 Cornelis Networks (原 Intel OPA)

Intel 已將其 Omni-Path 業務剝離給 Cornelis Networks，後者繼續開發高效能互連技術：

- **Cornelis Omni-Path**: 100 Gbps 互連解決方案，作為 InfiniBand 的高價效比替代方案
- **CN5000**: 下一代 400 Gbps 互連產品

#### 2.1.3 其他廠商

- **Cisco**: 主要提供乙太網和 RoCE 解決方案
- **Chelsio**: 專注於 iWARP 和 RoCE 解決方案

### 2.2 網卡架構

#### 2.2.1 硬體元件

1. **Host Channel Adapter (HCA)**
   - InfiniBand 網卡的核心元件
   - 負責協議處理和 RDMA 操作
   - 包含佇列對 (Queue Pairs) 管理

2. **PCIe 接口**
   - 連線主機系統的標準介面
   - 支持 PCIe 3.0/4.0/5.0
   - 通常使用 x8 或 x16 通道

3. **記憶體控制器**
   - 管理板載記憶體和快取
   - 支援記憶體註冊和保護
   - 提供 DMA 引擎功能

#### 2.2.2 軟體棧

1. **固件 (Firmware)**
   - 低階別的硬體控制
   - 協議棧實現
   - 效能最佳化和錯誤處理

2. **驅動程式**
   - 核心空間驅動
   - 使用者空間庫 (libibverbs)
   - 管理工具和實用程式

### 2.3 VPI 技術

#### 2.3.1 Virtual Protocol Interconnect

VPI 技術允許單一網卡支援多種協議：

- **InfiniBand**: 原生 IB 協議
- **Ethernet**: 標準乙太網協議
- **RoCE**: RDMA over Converged Ethernet

#### 2.3.2 協議切換

VPI 網卡可以根據網路環境動態切換協議：

```bash
# 檢視當前協議
ibv_devinfo | grep link_layer

# 注意：/sys/class/infiniband/mlx5_0/ports/1/link_layer 是隻讀屬性，
# 只反映固件/驅動當前的選擇，不能 echo 寫入，改它切換不了協議

# 協議切換隻有 mlxconfig 一條路（寫韌體配置 + 過載驅動/重啟生效）
mlxconfig -d /dev/mst/mt412* set LINK_TYPE_P1=ETH
mlxconfig -d /dev/mst/mt412* set LINK_TYPE_P2=ETH

# 切換回 InfiniBand 模式
mlxconfig -d /dev/mst/mt412* set LINK_TYPE_P1=IB
```

### 2.4 性能特性

#### 2.4.1 延遲最佳化

- **硬體時間戳**: 精確的延遲測量
- **零複製 DMA**: 減少記憶體複製開銷
- **中斷合併**: 最佳化中斷處理

#### 2.4.2 頻寬最佳化

- **多佇列支援**: 並行處理多個連線
- **自適應路由**: 動態負載均衡
- **擁塞控制**: 硬體級別的流量管理

---

## 3. InfiniBand 網卡配置

### 3.1 驅動程式安裝

#### 3.1.1 Ubuntu/Debian 系統

**方法一: 使用官方軟體源:**

```bash
# 更新軟體包列表
sudo apt update

# 安裝基礎 InfiniBand 支持
sudo apt install -y infiniband-diags ibverbs-utils
sudo apt install -y libmlx5-1 libmlx4-1
sudo apt install -y libibverbs-dev librdmacm-dev

# 安裝效能測試工具
sudo apt install -y perftest
```

**方法二: 安裝 NVIDIA MLNX_OFED:**

```bash
# 下載 MLNX_OFED (以 Ubuntu 22.04 為例，請訪問官網獲取最新版本)
# 24.10-0.7.0.0 是 24.10 系列的正式 GA 版本（2024 年 11 月发布），下載 URL 已驗證可達（2026-11-05 複核）
wget https://www.mellanox.com/downloads/ofed/MLNX_OFED-24.10-0.7.0.0/MLNX_OFED_LINUX-24.10-0.7.0.0-ubuntu22.04-x86_64.tgz

# 解壓安裝包
tar -xzf MLNX_OFED_LINUX-24.10-0.7.0.0-ubuntu22.04-x86_64.tgz
cd MLNX_OFED_LINUX-24.10-0.7.0.0-ubuntu22.04-x86_64

# 安裝所有元件
sudo ./mlnxofedinstall --all

# 重啟系統使驅動生效
sudo reboot
```

#### 3.1.2 CentOS/RHEL 系統

```bash
# 安裝基礎軟體包
sudo yum install -y infiniband-diags libibverbs-utils
sudo yum install -y perftest rdma-core

# 或使用 dnf (較新版本)
sudo dnf install -y infiniband-diags libibverbs-utils
sudo dnf install -y perftest rdma-core
```

### 3.2 網路介面配置

#### 3.2.1 IPoIB 配置

**使用 Netplan (Ubuntu 18.04+):**

```yaml
# /etc/netplan/01-ib-config.yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    ib0:
      addresses:
        - 192.168.100.10/24
      routes:
        - to: default
          via: 192.168.100.1
      nameservers:
        addresses:
          - 8.8.8.8
          - 8.8.4.4
      mtu: 2044 # IPoIB 資料包模式標準 MTU (IB MTU 2048 減 4 位元組 IPoIB 頭)
      # 注意: IPoIB 連線模式下 MTU 可達 65520 位元組
      optional: true
```

```bash
# 應用配置
sudo netplan apply

# 驗證配置
ip addr show ib0
ping -I ib0 192.168.100.1
```

**傳統網路配置:**

```bash
# 手動配置 IB 接口
sudo ip link set ib0 up
sudo ip addr add 192.168.100.10/24 dev ib0
sudo ip link set ib0 mtu 2044  # 資料包模式標準 MTU

# 注意: IPoIB 連線模式下 MTU 可達 65520 位元組，但需要特殊配置
# sudo modprobe ib_ipoib send_queue_size=128 recv_queue_size=512

# 添加路由
sudo ip route add 192.168.100.0/24 dev ib0
```

#### 3.2.2 RoCE 配置

當網卡工作在乙太網模式時，需要配置 RoCE：

```bash
# 檢查 Link Layer 類型
ibv_devinfo | grep link_layer

# RoCE v2 判定：由驅動按埠 netdev 類型自動完成（gid_attrs/types 是隻讀的 sysfs 列舉數字，
# RoCE v2 對應值 2），不要 echo 寫入，也不需要手工配置

# 無損網路配置（PFC + ECN，對應 §1.3.2 技術註釋 5）：
# PFC 用 mlnx_qos 配 802.1Qbb 優先順序流控（示例對第 4、5 優先順序開 PFC），並設定優先順序信任模式
sudo mlnx_qos -i eth0 --trust dscp --pfc 0,0,0,0,1,1,0,0
# ECN 由交換機側擁塞標記 + 網卡側響應配合完成
# 注意：ethtool -A rx on tx on 是 802.3x 全局 pause，不是 PFC；RoCE 無損配置不使用它

# 設定 Jumbo Frame
sudo ip link set eth0 mtu 9000
```

### 3.3 效能最佳化配置

#### 3.3.1 系統參數最佳化

**網路緩衝區最佳化 (僅適用於 IPoIB 場景)：**

> **重要說明**: 以下網路核心參數最佳化僅適用於 IP over InfiniBand (IPoIB) 場景。如果 GPU 直接使用 InfiniBand 網路進行 RDMA 通信，則無需修改這些參數，因為 RDMA 繞過了核心網路棧。

```bash
# 網路緩衝區最佳化 (僅在使用 IPoIB 時配置)
echo 'net.core.rmem_max = 134217728' | sudo tee -a /etc/sysctl.conf
echo 'net.core.wmem_max = 134217728' | sudo tee -a /etc/sysctl.conf
echo 'net.core.rmem_default = 67108864' | sudo tee -a /etc/sysctl.conf
echo 'net.core.wmem_default = 67108864' | sudo tee -a /etc/sysctl.conf

# TCP 參數最佳化 (僅在使用 IPoIB 時配置)
echo 'net.ipv4.tcp_rmem = 4096 87380 134217728' | sudo tee -a /etc/sysctl.conf
echo 'net.ipv4.tcp_wmem = 4096 65536 134217728' | sudo tee -a /etc/sysctl.conf

# 應用配置
sudo sysctl -p
```

**適用場景判斷**:

- ✅ **需要配置**: 使用 IPoIB 網路介面進行 TCP/IP 通信
- ❌ **無需配置**: GPU 直接使用 InfiniBand 進行 RDMA 通信
- ❌ **無需配置**: 使用 UCX、OpenMPI 等直接訪問 InfiniBand 的應用

#### 3.3.2 CPU 親和性配置

```bash
# 檢視網卡的 NUMA 節點
cat /sys/class/infiniband/mlx5_0/device/numa_node

# 設定中斷親和性
echo 2 | sudo tee /proc/irq/24/smp_affinity

# 繫結應用程式到特定 CPU
numactl --cpunodebind=0 --membind=0 your_application
```

#### 3.3.3 記憶體大頁配置

```bash
# 配置大頁記憶體
echo 1024 | sudo tee /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages

# 永久配置
echo 'vm.nr_hugepages = 1024' | sudo tee -a /etc/sysctl.conf

# 掛載大頁檔案系統
sudo mkdir -p /mnt/huge
sudo mount -t hugetlbfs nodev /mnt/huge
```

### 3.4 安全配置

#### 3.4.1 防火牆配置

> **注意**: InfiniBand 子網管理 (SM) 和原生 RDMA 通訊通常不經過 IP 防火牆 (如 ufw/iptables)。以下配置主要適用於 IPoIB、RoCEv2 以及使用 TCP/IP 輔助連線的工具。

```bash
# 允許 IPoIB 接口的所有流量
sudo ufw allow in on ib0
sudo ufw allow out on ib0

# 允許 RoCEv2 (UDP 4791)
sudo ufw allow 4791/udp

# 允許 ib_write_bw 等測試工具的預設埠 (TCP 18515)
sudo ufw allow 18515/tcp
```

#### 3.4.2 訪問控制

```bash
# 配置 IB 分割槽
echo "0x8001" | sudo tee /sys/class/infiniband/mlx5_0/ports/1/pkeys/1

# 設定裝置許可權
sudo chown root:rdma /dev/infiniband/*
sudo chmod 660 /dev/infiniband/*
```

---

## 4. InfiniBand 網卡相關命令

### 4.1 基礎診斷命令

#### 4.1.1 裝置發現和狀態查詢

```bash
# 列出所有 IB 裝置
ibv_devices

# 顯示裝置詳細資訊
ibv_devinfo

# 顯示裝置狀態摘要
ibstat

# 檢視特定裝置資訊
ibv_devinfo -d mlx5_0

# 顯示埠狀態
ibportstate
```

**示例輸出解析**:

```bash
$ ibstat
CA 'mlx5_0'
    CA type: MT4129
    Number of ports: 1
    Firmware version: 28.39.5050
    Hardware version: 0
    Node GUID: 0xa088c20300863a34
    System image GUID: 0xa088c20300863a34
    Port 1:
        State: Active
        Physical state: LinkUp
        Rate: 200
        Base lid: 113
        LMC: 0
        SM lid: 92
        Capability mask: 0x2651e848
        Port GUID: 0xa088c20300863a34
        Link layer: InfiniBand
```

#### 4.1.2 網路拓撲發現

```bash
# 發現網路拓撲
ibnetdiscover

# 獲取埠連線報告 (顯示 LID、埠號、GUID、鏈路寬度、速度等信息)
ibnetdiscover -p

# 顯示所有節點
ibnodes

# 顯示所有交換機
ibswitches

# 顯示路由表
ibroute
```

#### 4.1.3 連通性測試

```bash
# 連通性測試（ibping 分兩端）：
#   目標機（服務端）先跑:  ibping -S
#   本機（客戶端）按 LID 打: ibping -L <dest_lid>   （或按端口 GUID: ibping -G <port_guid>）
#   注意 -S/--Server 是服務端模式，不是源地址；rdma-core 版 ibping 沒有 -D 選項
ibping -L <dest_lid>

# 路徑追蹤
ibtracert <source_lid> <dest_lid>

# 檢查埠連線
ibportstate <ca_name> <port_num>
```

### 4.2 效能監控命令

#### 4.2.1 效能計數器

```bash
# 查詢效能計數器
perfquery

# 查詢所有埠的計數器
perfquery -a

# 查詢特定裝置的計數器
perfquery -G <port_guid>

# 重置計數器
perfquery -R

# 持續監控計數器變化
watch -n 1 'perfquery -a'
```

**關鍵效能計數器說明**:

| 計數器                   | 含義         | 正常值   |
| ------------------------ | ------------ | -------- |
| PortXmitData             | 傳送資料量   | 持續增長 |
| PortRcvData              | 接收資料量   | 持續增長 |
| PortXmitPkts             | 傳送包數     | 持續增長 |
| PortRcvPkts              | 接收包數     | 持續增長 |
| SymbolErrorCounter       | 符號錯誤     | 應為 0   |
| LinkErrorRecoveryCounter | 鏈路錯誤恢復 | 應為 0   |
| LinkDownedCounter        | 鏈路斷開次數 | 應為 0   |
| PortRcvErrors            | 接收錯誤     | 應為 0   |
| PortXmitDiscards         | 傳送丟棄     | 應為 0   |

#### 4.2.2 錯誤檢查

```bash
# 檢查網路錯誤
ibcheckerrors

# 查詢錯誤計數器
ibqueryerrors.pl

# 檢查節點錯誤
ibcheckerrs

# 檢查埠錯誤
ibcheckport
```

#### 4.2.3 鏈路狀態和效能分析

**mlxlink 工具詳解：**

mlxlink 是 NVIDIA 提供的高階鏈路分析工具，可以詳細檢視鏈路狀態和效能參數：

```bash
# 檢視鏈路基本資訊
mlxlink -d /dev/mst/mt4125_pciconf0 -p 1

# 檢視鏈路效能計數器
mlxlink -d /dev/mst/mt4125_pciconf0 -p 1 -c

# 檢視鏈路錯誤統計
mlxlink -d /dev/mst/mt4125_pciconf0 -p 1 --show_errors

# 重置效能計數器
mlxlink -d /dev/mst/mt4125_pciconf0 -p 1 --pc
```

**mlxlink 輸出欄位解釋**:

| 字段                       | 含義             | 正常值        | 說明            |
| -------------------------- | ---------------- | ------------- | --------------- |
| **Enabled Link Speed**     | 協商後的鏈路速率 | HDR/EDR/FDR   | 實際工作速率    |
| **Enabled Link Width**     | 協商後的鏈路寬度 | 4x            | 通常為 4 通道   |
| **FEC Mode**               | 前向糾錯模式     | RS-FEC/FC-FEC | HDR 推薦 RS-FEC |
| **PLR (Packet Loss Rate)** | 包丟失率         | < 10^-12      | 越低越好        |
| **BER (Bit Error Rate)**   | 誤位元速率           | < 10^-15      | 硬體品質指標    |
| **Temperature**            | 模組溫度         | < 70°C        | 過熱會影響效能  |
| **RX Power**               | 接收光功率       | -1 ~ -10 dBm  | 光模組訊號強度  |
| **TX Power**               | 发送光功率       | -1 ~ -5 dBm   | 傳送端訊號強度  |

**示例輸出分析**:

```bash
$ mlxlink -d /dev/mst/mt4125_pciconf0 -p 1

Operational Info
----------------
State                        : Active
Physical state               : LinkUp
Speed                        : HDR (200Gb/s)
Width                        : 4x
FEC                          : RS-FEC (544,514)
Loopback Mode               : No Loopback
Auto Negotiation            : ON

Physical Counters
-----------------
Symbol errors               : 0
Link error recovery         : 0
Link downed                 : 0
Rcv errors                  : 0
Rcv remote physical errors  : 0
Rcv switch relay errors     : 0
Xmit discards              : 0
Xmit constraint errors     : 0
Rcv constraint errors      : 0
Link integrity errors      : 0
Buffer overrun errors      : 0
VL15 dropped               : 0

Temperature Info
----------------
Temperature                 : 45 C
Temperature Threshold       : 75 C
Temperature Warning         : No

Cable Info
----------
Cable Type                  : Passive Copper
Cable Length                : 3 m
Cable Part Number           : MCP1600-H003
Cable Vendor                : Mellanox
```

**效能分析要點**:

1. **錯誤計數器全部為 0**: 表示鏈路品質良好
2. **溫度在正常範圍**: 避免過熱導致的效能下降
3. **FEC 模式正確**: HDR 使用 RS-FEC，EDR 使用 FC-FEC
4. **鏈路狀態為 Active**: 表示鏈路正常工作

### 4.3 配置管理命令

#### 4.3.1 子網管理

```bash
# 啟動子網管理器
sudo opensm

# 檢視子網管理器狀態
sudo systemctl status opensm

# 配置子網管理器
sudo nano /etc/opensm/opensm.conf

# 指定路由演算法啟動（-R 選擇 routing engine，如 ftree/up-dn；不是"重新掃描"）
sudo opensm -R ftree
# 拓撲變化由 SM 周期性 sweep 自動捕捉（opensm.conf 的 sweep_interval，預設 10 秒），
# 不存在也不需要"手動 rescan"命令
```

#### 4.3.2 虛擬化配置

```bash
# 啟用 SR-IOV
echo 8 | sudo tee /sys/class/net/ib0/device/sriov_numvfs

# 檢視虛擬功能
lspci | grep -i virtual

# 配置虛擬功能
ibdev2netdev -v
```

#### 4.3.3 固件管理

```bash
# 查看固件版本
ibv_devinfo | grep fw_ver

# 使用 mstflint 更新固件
mstflint -d /dev/mst/mt4129_pciconf0 q

# 燒錄新韌體 (謹慎操作)
mstflint -d /dev/mst/mt4129_pciconf0 -i fw_image.bin burn
```

### 4.4 效能測試工具詳解

#### 4.4.1 頻寬測試 (ib_write_bw)

**基本用法**:

```bash
# 服務端
ib_write_bw

# 客戶端
ib_write_bw <server_ip>
```

**高階參數配置**:

```bash
# 完整的效能測試命令
ib_write_bw -d mlx5_0 -i 1 -s 65536 -n 10000 -D 10 \
  --cpu_util --report_gbits --run_infinitely

# 參數說明:
# -d mlx5_0        : 指定 IB 裝置
# -i 1             : 使用端口 1
# -s 65536         : 消息大小 64KB
# -n 10000         : 測試迭代次數
# -D 10            : 測試持續時間 10 秒
# --cpu_util       : 顯示 CPU 使用率
# --report_gbits   : 以 Gbps 顯示結果
# --run_infinitely : 持續執行直到手動停止
```

**NUMA 繫結和 CPU 親和性**:

```bash
# 繫結到特定 NUMA 節點和 CPU 核心
numactl --cpunodebind=0 --membind=0 \
  taskset -c 0-15 ib_write_bw -d mlx5_0 -s 1048576

# 查看 NUMA 拓撲
numactl --hardware
lscpu | grep NUMA

# 查看 IB 裝置的 NUMA 親和性
cat /sys/class/infiniband/mlx5_0/device/numa_node
```

**不同訊息大小的效能測試**:

```bash
# 小訊息測試 (延遲敏感)
for size in 64 256 1024 4096; do
  echo "Testing message size: $size bytes"
  ib_write_bw -s $size -n 100000
done

# 大訊息測試 (頻寬敏感)
for size in 65536 262144 1048576 4194304; do
  echo "Testing message size: $size bytes"
  ib_write_bw -s $size -n 10000
done

# 注意: 訊息大小超過 4KB 時需要註冊記憶體區域
# 使用 ibv_reg_mr() 函式進行記憶體註冊以獲得最佳效能
```

#### 4.4.2 延遲測試 (ib_send_lat)

**基本延遲測試**:

```bash
# 服務端
ib_send_lat

# 客戶端
ib_send_lat <server_ip>
```

**高精度延遲測試**:

```bash
# 使用硬體時間戳的高精度測試
ib_send_lat -d mlx5_0 -i 1 -s 64 -n 100000 \
  -e --cpu_util

# 參數說明:
# -s 64        : 64 位元組小訊息
# -n 100000    : 大量迭代確保統計準確性
# -e           : 事件驅動模式（等完成事件，替代輪詢；perftest 沒有 --use_event 這個長選項）
# --cpu_util   : 監控 CPU 使用率
```

**延遲分佈分析**:

```bash
# 生成延遲分佈資料（-H/--report-histogram 列印全部樣本，格式：序號, 延遲[usec]；
# --output 只接受 bandwidth/message_rate/latency，沒有 histogram 取值）
ib_send_lat -s 64 -n 1000000 -H > latency_hist.txt

# 分析結果（檔案末兩行是表頭 + 彙總行，含 t_min/t_avg/t_stdev 與 99%/99.9% 分位）
echo "延遲彙總:"
tail -n 2 latency_hist.txt
echo "延遲樣本分佈（前 5 個取樣點）:"
grep -E "^[0-9]+, " latency_hist.txt | head -5
```

#### 4.4.3 RDMA 效能測試

**RDMA Read 測試**:

```bash
# 測試 RDMA Read 頻寬
ib_read_bw -d mlx5_0 -s 1048576 -n 10000

# 測試 RDMA Read 延遲
ib_read_lat -d mlx5_0 -s 64 -n 100000
```

**RDMA Write 測試**:

```bash
# 測試 RDMA Write 頻寬
ib_write_bw -d mlx5_0 -s 1048576 -n 10000

# 測試 RDMA Write 延遲
ib_write_lat -d mlx5_0 -s 64 -n 100000
```

**原子操作測試**:

```bash
# 測試原子操作延遲
ib_atomic_lat -d mlx5_0 -n 100000

# 測試原子操作頻寬
ib_atomic_bw -d mlx5_0 -n 10000
```

#### 4.4.4 多連線併發測試

**多佇列對測試**:

```bash
# 測試多個佇列對的聚合頻寬
ib_write_bw -d mlx5_0 -q 8 -s 65536 -n 10000

# 參數說明:
# -q 8 : 使用 8 個佇列對
```

**多行程併發測試**:

```bash
#!/bin/bash
# 啟動多個併發測試行程
for i in {1..4}; do
  ib_write_bw -p $((18515+i)) -d mlx5_0 &
done
wait
```

#### 4.4.5 效能基準和調優建議

**典型性能基准** (ConnectX-7 HDR):

| 測試類型            | 消息大小 | 期望性能   | 調優要點             |
| ------------------- | -------- | ---------- | -------------------- |
| **RDMA Write 頻寬** | 1MB      | > 190 Gbps | 大消息，多佇列       |
| **RDMA Write 延遲** | 64B      | < 0.6 μs   | CPU 親和性，中斷繫結 |
| **Send/Recv 頻寬**  | 64KB     | > 180 Gbps | 適中訊息大小         |
| **Send/Recv 延遲**  | 64B      | < 0.8 μs   | 事件驅動模式         |
| **原子操作延遲**    | 8B       | < 0.9 μs   | 硬件原子支持         |

> 注：表中延遲為網卡硬體口徑（adapter latency，訊息不離開網卡）。perftest 實測是端到埠徑（含軟體棧、PCIe 往返），64B 消息一般在 1.x μs 量級。對比數字前先確認口徑一致。

**效能調優檢查清單**:

1. **NUMA 繫結**: 確保行程和記憶體在同一 NUMA 節點
2. **CPU 親和性**: 繫結到專用 CPU 核心
3. **中斷繫結**: IB 中斷繫結到測試行程相同的 CPU
4. **記憶體鎖定**: 使用 `mlockall()` 鎖定記憶體頁
5. **佇列深度**: 根據應用特性調整 QP 深度
6. **消息大小**: 選擇適合應用的最優訊息大小

**PCIe 瓶頸說明**:

```plaintext
PCIe 5.0 x16 頻寬 ≈ 64 GB/s → 可支撐單埠 NDR 400Gbps (50 GB/s)，雙埠會受限
PCIe 4.0 x16 ≈ 32 GB/s → 單口 HDR (25 GB/s) 尚可，雙口 HDR 吃緊；NDR 單口已不夠
（ConnectX-7 本身是 PCIe 5.0 裝置，主機插槽也要 PCIe 5.0 才能跑滿）

PCIe 版本對比 (x16 通道理論單向頻寬):
- PCIe 3.0 x16: ~16 GB/s (支持 EDR 100Gbps)
- PCIe 4.0 x16: ~32 GB/s (支持 HDR 200Gbps)
- PCIe 5.0 x16: ~64 GB/s (支持 NDR 400Gbps)
- PCIe 6.0 x16: ~128 GB/s (支持 XDR 800Gbps / NDR 400Gbps 雙口)
- PCIe 7.0 x16: ~256 GB/s (2025 年 6 月規範已釋出) [10]
```

**效能問題診斷**:

```bash
# 檢查 CPU 頻率縮放
cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# 檢查中斷分佈
cat /proc/interrupts | grep mlx

# 檢查記憶體頻寬
stream_benchmark

# 檢查 PCIe 頻寬
lspci -vv | grep -A 10 "Mellanox"
```

### 4.5 故障排查命令

#### 4.5.1 診斷指令碼

```bash
#!/bin/bash
# ib_quick_check.sh - 快速 IB 健康檢查

echo "=== InfiniBand 快速健康檢查 ==="

# 檢查裝置
echo "1. IB 裝置檢查:"
ibv_devices

# 檢查狀態
echo -e "\n2. 埠狀態檢查:"
ibstat | grep -E "(State|Physical state|Rate)"

# 檢查錯誤
echo -e "\n3. 錯誤計數器檢查:"
perfquery -a | grep -E "(Error|Discard)" | head -10

# 檢查連通性
echo -e "\n4. 網路拓撲檢查:"
ibnodes | wc -l
echo "發現 $(ibnodes | wc -l) 個網路節點"
# 獲取埠連線報告
echo "埠連線數: $(ibnetdiscover -p | wc -l)"

echo -e "\n=== 檢查完成 ==="
```

#### 4.5.2 日志分析

```bash
# 檢視系統日誌中的 IB 相關資訊
sudo dmesg | grep -i infiniband

# 檢視核心模組日誌
sudo journalctl -k | grep mlx5

# 查看 OFED 日志
sudo cat /var/log/messages | grep -i ofed
```

---

## 5. GPU 場景下 InfiniBand 網卡檢查和測試

### 5.1 GPU 與 InfiniBand 集成原理

#### 5.1.1 GPUDirect RDMA 核心技術

GPUDirect RDMA 是 GPU 與 InfiniBand 高效整合的關鍵技術：

**技術原理**：

- **零複製傳輸**：GPU 記憶體直接與遠端 GPU 記憶體通訊，繞過 CPU 記憶體
- **DMA 引擎**：利用 GPU 和 IB 網卡的 DMA 引擎實現非同步資料傳輸
- **記憶體對映**：透過 PCIe BAR 空間將 GPU 記憶體對映到 IB 網卡地址空間

**效能優勢**：

- 延遲降低：消除 CPU 記憶體複製開銷，延遲可降低 50% 以上
- 頻寬提升：充分利用 PCIe 和 IB 頻寬，理論頻寬接近硬體極限
- CPU 解除安裝：釋放 CPU 資源用於計算任務

#### 5.1.2 系統架構要求

**硬件要求**：

- NVIDIA GPU：Kepler 架構及以上，支持 GPUDirect
- InfiniBand 網卡：Mellanox ConnectX-3 及以上
- PCIe 匯流排：PCIe 3.0 x16 或更高，確保充足頻寬
- NUMA 拓撲：GPU 與 IB 網卡位於同一 NUMA 節點

**軟體棧**：

- CUDA 驅動：支持 GPUDirect 的版本
- NVIDIA 驅動自帶的 `nvidia-peermem` 模組（記憶體註冊入口在 GPU 驅動側；MLNX_OFED 提供的是核心 RDMA 基礎設施，早期 `nv_peer_mem` 隨 OFED 分发，現已由 NVIDIA 驅動內建模組取代）
- NCCL：GPU 叢集通訊庫
- 應用框架：PyTorch、TensorFlow 等

### 5.2 環境檢查與配置

#### 5.2.1 關鍵檢查命令

```bash
# 1. GPU 裝置和拓撲檢查
nvidia-smi topo -m                    # 查看 GPU-IB 拓撲關係
nvidia-smi --query-gpu=name,driver_version --format=csv

# 2. InfiniBand 裝置檢查
ibv_devices                           # 列出 IB 裝置
ibstat                               # 查看 IB 埠狀態

# 3. GPUDirect RDMA 支援檢查
cat /proc/driver/nvidia/gpus/*/information | grep -i rdma
lsmod | grep nvidia_peermem          # 檢查 peermem 模組

# 4. NCCL 功能驗證
python3 -c "import torch; print(torch.cuda.nccl.version())"
```

#### 5.2.2 NCCL 環境配置要點

```bash
# 核心配置：啟用 InfiniBand 和 GPUDirect
export NCCL_IB_DISABLE=0             # 啟用 InfiniBand
export NCCL_NET_GDR_LEVEL=2          # GDR 的 GPU-NIC 距離上限，2 = PXB（GDR 預設已啟用；推薦寫 "PXB"）
export NCCL_IB_HCA=mlx5_0            # 指定 IB 裝置

# 除錯配置：問題排查時使用
export NCCL_DEBUG=INFO               # 啟用除錯資訊
export NCCL_DEBUG_SUBSYS=INIT,NET    # 網路子系統除錯

# 效能最佳化配置
export NCCL_IB_TIMEOUT=22            # IB 超時設定
export NCCL_IB_RETRY_CNT=7           # 重試次數
export NCCL_IB_GID_INDEX=0           # GID 索引（原生 IB）
```

#### 5.2.3 快速環境檢查

```bash
# 簡化的環境檢查指令碼核心邏輯
check_gpu_ib_env() {
    # GPU 檢查
    nvidia-smi -L | wc -l

    # IB 裝置檢查
    ibv_devices | wc -l

    # GPUDirect 支援檢查
    grep -q "RDMA" /proc/driver/nvidia/gpus/*/information 2>/dev/null

    # NCCL 可用性檢查
    python3 -c "import torch; torch.cuda.nccl.version()" 2>/dev/null
}
```

### 5.3 效能測試方法

#### 5.3.1 基礎 IB 效能測試

```bash
# 頻寬測試（關鍵參數）
ib_send_bw -d mlx5_0 -i 1 -s 1048576    # 1MB 消息大小
ib_send_bw -d mlx5_0 -i 1 -s 4194304    # 4MB 消息大小

# 延遲測試
ib_send_lat -d mlx5_0 -i 1 -s 8         # 小訊息延遲

# RDMA 操作測試
ib_read_bw -d mlx5_0 <server_ip>        # RDMA Read
ib_write_bw -d mlx5_0 <server_ip>       # RDMA Write
```

#### 5.3.2 NCCL 集合通訊測試

```bash
# 使用 NCCL Tests 進行標準測試
git clone https://github.com/NVIDIA/nccl-tests.git
cd nccl-tests && make

# AllReduce 效能測試（關鍵操作）
./build/all_reduce_perf -b 1K -e 1G -f 2 -g 4

# 多節點測試
mpirun -np 8 -H node1:4,node2:4 \
    ./build/all_reduce_perf -b 1M -e 128M -f 2
```

#### 5.3.3 自定義效能測試核心

```python
# NCCL 效能測試的關鍵程式碼片段
import torch
import torch.distributed as dist
import time

def benchmark_allreduce(tensor_size_mb, iterations=100):
    rank = dist.get_rank()
    device = torch.device(f"cuda:{rank}")

    # 建立測試張量
    elements = tensor_size_mb * 1024 * 1024 // 4
    tensor = torch.ones(elements, device=device, dtype=torch.float32)

    # 預熱
    for _ in range(10):
        dist.all_reduce(tensor)
        torch.cuda.synchronize()

    # 效能測試
    torch.cuda.synchronize()
    start_time = time.time()

    for _ in range(iterations):
        dist.all_reduce(tensor)

    torch.cuda.synchronize()
    end_time = time.time()

    # 計算效能指標
    avg_time = (end_time - start_time) / iterations * 1000  # ms
    bandwidth = tensor_size_mb * 8 / (avg_time / 1000)     # Gbps

    if rank == 0:
        print(f"Size: {tensor_size_mb}MB, Latency: {avg_time:.2f}ms, Bandwidth: {bandwidth:.2f}Gbps")

# 執行測試
# torchrun --nproc_per_node=4 test_script.py
```

### 5.4 故障排查要點

#### 5.4.1 常見問題診斷

**NCCL 無法使用 InfiniBand**：

```bash
# 檢查步驟
env | grep NCCL                      # 環境變數配置
ibstat                              # IB 裝置狀態
dmesg | grep -i infiniband          # 核心日誌
```

**GPUDirect RDMA 不工作**：

```bash
# 關鍵檢查點
lsmod | grep nvidia_peermem         # peermem 模組
nvidia-smi topo -m                  # GPU-IB 拓撲
cat /sys/class/infiniband/*/device/numa_node  # NUMA 節點
```

**效能不達預期**：

```bash
# 性能分析
nvidia-smi topo -m                  # 檢查 PCIe 連線
numactl --hardware                  # NUMA 拓撲
cat /proc/cpuinfo | grep MHz        # CPU 頻率
```

#### 5.4.2 效能最佳化關鍵點

1. **硬體最佳化**：
   - GPU 與 IB 網卡 NUMA 親和性
   - PCIe 頻寬充足性（x16 通道）
   - CPU 效能模式設定

2. **軟體最佳化**：
   - NCCL 環境變數調優
   - 大頁記憶體啟用
   - 中斷親和性設定

3. **網路最佳化**：
   - 專用 IB 網路
   - 合適的 MTU 設定
   - 流量控制配置

### 5.5 監控要點

#### 5.5.1 關鍵監控指標

```bash
# GPU 狀態監控
nvidia-smi --query-gpu=utilization.gpu,memory.used,temperature.gpu --format=csv

# IB 效能計數器
perfquery -a | grep -E "(PortXmitData|PortRcvData|PortXmitPkts|PortRcvPkts)"

# 錯誤計數器
perfquery -a | grep -E "Error|Discard" | grep -v ": 0"
```

#### 5.5.2 健康檢查要點

```bash
# 每日檢查核心專案
nvidia-smi --query-gpu=ecc.errors.corrected.total,ecc.errors.uncorrected.total --format=csv
ibstat | grep -E "State.*Active"
perfquery -a | grep -E "Error|Discard" | grep -v ": 0"
```

**監控告警閾值**：

- GPU 溫度 > 80°C
- GPU 記憶體使用率 > 90%
- IB 錯誤計數器增長
- NCCL 通訊延遲異常

---

## 6. 總結

高效能運算和 AI 訓練叢集的節點間通訊，大多跑在 InfiniBand 上。本文件從 InfiniBand 的基本原理出发，詳細介紹了網卡選型、配置方法、常用命令，以及在 GPU 場景下的特殊應用。

### 6.1 關鍵要點

1. **技術理解**: InfiniBand 提供了比傳統乙太網更優越的效能特性，特別是在延遲和 CPU 開銷方面
2. **硬體選擇**: NVIDIA ConnectX 系列是目前市場主流，支持 VPI 技術可以靈活適應不同網路環境
3. **配置最佳化**: 驅動安裝、網路配置、效能調優三步都做到位，才能跑出接近硬體指標的效能
4. **GPU 集成**: GPUDirect RDMA 和 NCCL 的正確配置是 AI 訓練叢集的關鍵
5. **監控維護**: 定期的健康檢查和效能監控有助於及早發現和解決問題

### 6.2 最佳實踐建議

- 在部署前進行充分的硬體相容性測試
- 使用官方推薦的驅動版本和配置參數
- 建立完善的監控和告警機制
- 定期進行效能基準測試
- 保持軟體棧的及時更新

透過遵循本文件的指導，可以有效地部署和維護高效能的 InfiniBand 網路環境，為 HPC 和 AI 應用提供強有力的網路基礎設施支援。

---

## 7. 推薦參考資料

### 7.1 官方文件和標準

**InfiniBand Trade Association (IBTA)：**

- 官方網站: <https://www.infinibandta.org>
- InfiniBand Architecture Specification: 權威的 IB 架構規範
- InfiniBand Roadmap: IB 技術發展路線圖

**NVIDIA Networking Documentation：**

- 官方文件: <https://docs.nvidia.com/networking/>
- Mellanox OFED User Manual: OFED 驅動使用指南
- Performance Tuning Guide: 效能調優最佳實踐
- Troubleshooting Guide: 故障排查指南

### 7.2 開源社群資源

**OpenFabrics Alliance：**

- 官方網站: <https://www.openfabrics.org>
- OFED 軟體棧: 開源 InfiniBand 和 RDMA 軟體
- 社群郵件列表: 技術討論和問題解答

**Linux RDMA Subsystem：**

- 核心文件: <https://www.kernel.org/doc/Documentation/infiniband/>
- RDMA Core Library: 使用者空間 RDMA 庫
- Perftest 工具集: 效能測試工具原始碼

### 7.3 技術白皮書和研究論文

**NVIDIA 技術白皮書：**

- "InfiniBand vs. Ethernet for HPC and AI"
- "RDMA Programming Guide"
- "Network Performance Optimization"

**學術研究：**

- "High Performance Computing with InfiniBand"
- "RDMA-based Distributed Systems"
- "Network Topology Design for Large-scale Clusters"

### 7.4 實用工具和指令碼

**效能測試工具：**

- Perftest: <https://github.com/linux-rdma/perftest>
- OSU Micro-Benchmarks: <http://mvapich.cse.ohio-state.edu/benchmarks/>
- Intel MPI Benchmarks: <https://github.com/intel/mpi-benchmarks>

**監控和診斷工具：**

- Mellanox UFM: 統一架構管理平台
- OpenSM: 開源子網管理器
- ibutils: IB 網路診斷工具集

### 7.5 培訓和認證

**NVIDIA 認證課程：**

- NVIDIA Certified Systems Administrator (NCSA)
- InfiniBand Network Administration
- High Performance Computing Fundamentals

**線上學習資源：**

- NVIDIA Developer Portal: 開發者資源和教程
- OpenFabrics Workshops: 年度技術研討會
- HPC University: 高效能運算線上課程

### 7.6 社群支援

**技術論壇：**

- NVIDIA Developer Forums: <https://forums.developer.nvidia.com>
- OpenFabrics Mailing Lists: 技術討論郵件列表
- Reddit HPC Community: r/HPC 社群討論

**商業支援：**

- NVIDIA Enterprise Support: 企業級技術支援
- 系統整合商服務: 專業的 IB 網路部署服務
- 第三方諮詢服務: 獨立的 HPC 網路諮詢

---

## 8. 參考文獻

1. IBTA. "Celebrating 25 Years of the InfiniBand Trade Association." InfiniBand Trade Association. Accessed: Dec. 7, 2025. [Online]. Available: https://www.infinibandta.org/celebrating-25-years-of-the-infiniband-trade-association/
2. FS.com. "InfiniBand vs RoCE v2: What's the Best Fit for Your AI Data Center." FS.com. Accessed: Dec. 7, 2025. [Online]. Available: https://www.fs.com/blog/infiniband-vs-roce-v2-whats-the-best-fit-for-your-ai-data-center-25811.html
3. IBTA. "IBTA Unveils XDR InfiniBand Specification." InfiniBand Trade Association. Accessed: Dec. 7, 2025. [Online]. Available: https://www.infinibandta.org/ibta-unveils-xdr-infiniband-specification-to-enable-the-next-generation-of-ai-and-scientific-computing/
4. InfiniBand Trade Association. _InfiniBand Architecture Specification_. 2023. [Online]. Available: https://www.infinibandta.org/ibta-specification/
5. Wikipedia contributors. "InfiniBand." Wikipedia. Accessed: Dec. 7, 2025. [Online]. Available: https://en.wikipedia.org/wiki/InfiniBand
6. Wikipedia contributors. "RDMA over Converged Ethernet." Wikipedia. Accessed: Dec. 7, 2025. [Online]. Available: https://en.wikipedia.org/wiki/RDMA_over_Converged_Ethernet
7. Nebius. "What is InfiniBand." Nebius Blog. Accessed: Dec. 7, 2025. [Online]. Available: https://nebius.com/blog/posts/what-is-infiniband
8. Morgan, T.P. "NVIDIA's Enormous Financial Success Becomes Normal." The Next Platform. Accessed: Dec. 7, 2025. [Online]. Available: https://www.nextplatform.com/2024/05/23/nvidias-enormous-financial-success-becomes-normal/
9. NVIDIA. "NVIDIA InfiniBand Adapters." NVIDIA. Accessed: Dec. 7, 2025. [Online]. Available: https://www.nvidia.com/en-us/networking/infiniband-adapters/
10. Wikipedia contributors. "PCI Express." Wikipedia. Accessed: Dec. 7, 2025. [Online]. Available: https://en.wikipedia.org/wiki/PCI_Express

---
