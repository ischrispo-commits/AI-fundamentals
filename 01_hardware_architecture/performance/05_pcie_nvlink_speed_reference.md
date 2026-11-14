# PCIe & NVLink 頻寬速查表

> 涵蓋 PCIe 各代、NVLink 各代、主流 GPU 互連規格及 NVMe SSD 速度的快速參考。資料來源標註於各表下方。資料截至 2026-11；B300 與 NVLink 6.0 為廠商口徑，標於相應表格。

---

## 1. PCIe 各代頻寬

單向頻寬 = GT/s × 編碼效率 × Lane 數 ÷ 8。Gen3–5 使用 128b/130b 編碼 (效率 ≈ 98.5%)；Gen6/Gen7 使用 PAM-4 + FLIT 編碼 (效率 ≈ 94.5%) [1,2]。

| 版本     | 年份 | GT/s  | 編碼       | x1 單向    | x4 單向    | x8 單向    | x16 單向   | x16 雙向   |
| :------- | :--- | :---- | :--------- | :--------- | :--------- | :--------- | :--------- | :--------- |
| **Gen1** | 2003 | 2.5   | 8b/10b     | 0.25 GB/s  | 1.0 GB/s   | 2.0 GB/s   | 4.0 GB/s   | 8.0 GB/s   |
| **Gen2** | 2007 | 5.0   | 8b/10b     | 0.5 GB/s   | 2.0 GB/s   | 4.0 GB/s   | 8.0 GB/s   | 16 GB/s    |
| **Gen3** | 2010 | 8.0   | 128b/130b  | ~1.0 GB/s  | ~3.9 GB/s  | ~7.9 GB/s  | ~15.8 GB/s | ~31.5 GB/s |
| **Gen4** | 2017 | 16.0  | 128b/130b  | ~2.0 GB/s  | ~7.9 GB/s  | ~15.8 GB/s | ~31.5 GB/s | ~63 GB/s   |
| **Gen5** | 2019 | 32.0  | 128b/130b  | ~3.9 GB/s  | ~15.8 GB/s | ~31.5 GB/s | ~63 GB/s   | ~126 GB/s  |
| **Gen6** | 2022 | 64.0  | PAM-4/FLIT | ~7.6 GB/s  | ~30.3 GB/s | ~60.5 GB/s | ~121 GB/s  | ~242 GB/s  |
| **Gen7** | 2025 | 128.0 | PAM-4/FLIT | ~15.1 GB/s | ~60.5 GB/s | ~121 GB/s  | ~242 GB/s  | ~485 GB/s  |

> **來源**: [1] PCI-SIG 官方規範各代速率定義；[2] 本倉庫 `pcie/01_pcie_comprehensive_guide.md` 第 31–47 行。

---

## 2. NVLink 各代頻寬

NVLink 總雙向頻寬 = 單 link 速率 × 雙向 × link 數量 [3]。

| 代      | 年份 | 架構      | 代表 GPU  | 單 Link 速率 | Link 數 | 雙向總頻寬 | 關鍵技術             |
| :------ | :--- | :-------- | :-------- | :----------- | :------ | :--------- | :------------------- |
| **1.0** | 2016 | Pascal    | P100      | 20 GB/s      | 4       | 160 GB/s   | 首次引入 GPU 直連    |
| **2.0** | 2017 | Volta     | V100      | 25 GB/s      | 6       | 300 GB/s   | NVSwitch 1.0         |
| **3.0** | 2020 | Ampere    | A100      | 25 GB/s      | 12      | 600 GB/s   | 訊號對減半，鏈路翻倍 |
| **4.0** | 2022 | Hopper    | H100/H200 | 25 GB/s      | 18      | 900 GB/s   | SHARP 網內計算       |
| **5.0** | 2024 | Blackwell | B200/B300 | 50 GB/s      | 18      | 1.8 TB/s   | NVL72 機架級擴展     |
| **6.0** | 2026 | Rubin     | Vera      | —            | —       | 3.6 TB/s   | NVSwitch 6, RAS 增強 |

> NVLink 6.0 頻寬雙口徑：GTC 2025 宣傳口徑為單 GPU 3.6 TB/s、NVL72 域聚合 260 TB/s；NVIDIA 官網當前為單 GPU 3,000 GB/s、Vera Rubin NVL72 聚合 216 TB/s（2026-11 核對）。表中取 GTC 2025 口徑。
>
> **來源**: [3] 本倉庫 `nvlink/nvlink_intro.md` 第 57–61 行；[4] NVIDIA GB200 NVL4 Architecture Whitepaper。

---

## 3. 主流 GPU 互連與顯存規格

所有頻寬均為**雙向**總頻寬。HBM 頻寬為近存頻寬 (near-memory BW)，PCIe/NVLink 為片間頻寬 [3,4,5,6,7]。

| GPU          | 架構            | 顯存         | 顯存頻寬  | PCIe 上行 | NVLink | NVLink 總頻寬 | NVSwitch |
| :----------- | :-------------- | :----------- | :-------- | :-------- | :----- | :------------ | :------- |
| **P100**     | Pascal          | 16 GB HBM2   | 732 GB/s  | Gen3 x16  | 1.0    | 160 GB/s      | —        |
| **V100**     | Volta           | 32 GB HBM2   | 900 GB/s  | Gen3 x16  | 2.0    | 300 GB/s      | 1.0      |
| **A100**     | Ampere          | 80 GB HBM2e  | 2.0 TB/s  | Gen4 x16  | 3.0    | 600 GB/s      | 2.0      |
| **H100**     | Hopper          | 80 GB HBM3   | 3.35 TB/s | Gen5 x16  | 4.0    | 900 GB/s      | 3.0      |
| **H200**     | Hopper          | 141 GB HBM3e | 4.8 TB/s  | Gen5 x16  | 4.0    | 900 GB/s      | 3.0      |
| **B200**     | Blackwell       | 192 GB HBM3e | 8.0 TB/s  | Gen5 x16  | 5.0    | 1.8 TB/s      | 4.0      |
| **B300**     | Blackwell Ultra | 270 GB HBM3e | 8.0 TB/s  | Gen6 x16  | 5.0    | 1.8 TB/s      | 4.0      |
| **RTX 5090** | Blackwell       | 32 GB GDDR7  | 1.79 TB/s | Gen5 x16  | **—**  | —             | —        |
| **L40S**     | Ada Lovelace    | 48 GB GDDR6  | 864 GB/s  | Gen4 x16  | **—**  | —             | —        |

> [!NOTE]
> **消費級 GPU (GeForce RTX) 不支持 NVLink**。40 系（Ada Lovelace）起全面移除；30 系僅 RTX 3080/3090 保留接口（官方橋接器面向 3090）。僅資料中心 GPU (Tesla/Quadro/HGX) 提供 NVLink 支持 [3]。
>
> B300 資料為 **HGX B300 形態**，顯存頻寬為廠商口徑「up to 8 TB/s」。NVL72 SXM 變體為 279 GB HBM3e / 8.0 TB/s [10]。
>
> **注意 270 / 279 是「系統可用顯存」而非卡規格。** B300 的卡規格是 **288 GB HBM3e**（NVIDIA 官方部落格口徑）；系統形態下的可用值按 [MIG 產品頁](https://www.nvidia.com/en-us/technologies/multi-instance-gpu/)分檔：**HGX B300 = `1x 270 GB`，GB300 NVL72 = `1x 279 GB`**。該頁尾註標明這些為 `Preliminary specifications`，且 NVL72 形態比裸卡少約 6–9 GB 屬慣例（GB200 同樣 186 vs 192）。**讀規格表用 288，做容量規劃用 270/279。**
>
> **來源**: [5] NVIDIA H100 Data Sheet; [6] NVIDIA H200 Product Page; [7] 本倉庫 `superchips/nvidia_gb300.md`; [3] 本倉庫 `nvlink/nvlink_intro.md`; [10] NVIDIA Blackwell Ultra Datasheet; [11] NVIDIA MIG Product Page。

---

## 4. NVMe SSD 典型速度 (M.2/U.2, x4)

NVMe SSD 使用 PCIe x4 接口。理論值 = PCIe x4 單向頻寬；典型讀取 ≈ 理論值的 85–90% (扣除協議開銷) [1]。

| 代       | 接口      | x4 理論單向 | 典型順序讀   | 典型順序寫   | 代表型號                         |
| :------- | :-------- | :---------- | :----------- | :----------- | :------------------------------- |
| **Gen3** | M.2 / U.2 | ~3.9 GB/s   | ~3,500 MB/s  | ~3,200 MB/s  | Samsung 970 Pro, WD Black SN750  |
| **Gen4** | M.2 / U.2 | ~7.9 GB/s   | ~7,000 MB/s  | ~6,900 MB/s  | Samsung 990 Pro, WD Black SN850X |
| **Gen5** | M.2 / U.2 | ~15.8 GB/s  | ~14,000 MB/s | ~12,000 MB/s | Crucial T705, Samsung 9100 Pro   |

> **來源**: [1] PCI-SIG 各代速率; Samsung/Crucial/Western Digital 官方產品規格頁。

---

## 5. 典型場景頻寬瓶頸速查

| 場景                          | 瓶頸鍊路                  | 理論單向頻寬              | 備註                                    |
| :---------------------------- | :------------------------ | :------------------------ | :-------------------------------------- |
| GPU→GPU (PCIe P2P, 同 Switch) | PCIe Gen5 x16             | ~63 GB/s                  | PIX 拓撲，GPUDirect P2P 全速 [8]        |
| GPU→GPU (PCIe P2P, 經 RC)     | PCIe Gen5 x16 ÷ 2         | ~32 GB/s                  | PHB 拓撲，頻寬減半 (資料經 RC 往返) [8] |
| GPU→GPU (NVLink 4.0)          | NVLink 4.0                | 900 GB/s                  | H100/H200，18 links [3]                 |
| GPU→GPU (NVLink 5.0)          | NVLink 5.0                | 1.8 TB/s                  | B200/B300，18 links [3]                 |
| H2D / D2H (GPU↔CPU)           | PCIe Gen5 x16             | ~63 GB/s                  | 單方向上限 [1]                          |
| NVMe→GPU (傳統, Buffered)     | PCIe Gen4 x4 → DRAM → GPU | ~3.5 GB/s                 | 2 次 PCIe 穿越 + CPU memcpy [9]         |
| NVMe→GPU (傳統, O_DIRECT)     | PCIe Gen4 x4 → DRAM → GPU | ~7 GB/s                   | 2 次 PCIe 穿越，無 CPU memcpy [9]       |
| NVMe→GPU (GDS)                | PCIe P2P 直通             | ~7 GB/s (同 PCIe Gen4 x4) | 1 次 PCIe 穿越，同 Switch 最優 [9]      |
| NVMe→GPU (GDS, Gen5)          | PCIe P2P 直通             | ~14 GB/s                  | 1 次 PCIe 穿越，基於 Gen5 x4 NVMe [9]   |
| CPU↔GPU (NVLink-C2C, GH200)   | NVLink-C2C                | ~450 GB/s                 | GH200 單向（900 GB/s 雙向）[7]          |
| CPU↔GPU (NVLink-C2C, GB300)   | NVLink-C2C                | ~225 GB/s                 | 每鏈單向（雙鏈聚合 900 GB/s）[7]        |
| CPU↔CPU (GB300 Clinks)        | Clinks                    | ~150 GB/s                 | GB300 兩顆 Grace CPU 之間，單向 [7]     |

> **來源**: [8] 本倉庫 `gpudirect/02_gpudirect_p2p.md` 第 5.1 節；[9] 本倉庫 `gpudirect/01_gpudirect_technology.md` 第 3.1–3.4 節；[3] `nvlink/nvlink_intro.md`；[7] `superchips/nvidia_gb300.md`。

---

## 6. 速算公式

```text
PCIe 單向頻寬 (GB/s) = GT/s × 編碼效率 × Lane 數 ÷ 8

  Gen1/2 (8b/10b):    效率 = 8/10 = 0.80
  Gen3/4/5 (128b/130b): 效率 = 128/130 ≈ 0.985
  Gen6 (PAM-4 + FLIT):  效率 = 242/256 ≈ 0.945

NVLink 雙向總頻寬 = 單 Link 速率 × 2 (雙向) × Link 數

NVMe 典型讀取 = PCIe x4 理論單向 × ~0.85–0.90 (NVMe 協議開銷)
```

**示例**: Gen5 x16 單向 = 32 × 0.985 × 16 ÷ 8 = 63.0 GB/s

---

## 7. NVLink vs PCIe 頻寬對比 (x16)

| NVLink 代   | 總雙向頻寬 | 對比 PCIe (x16 雙向) | 倍數  |
| :---------- | :--------- | :------------------- | :---- |
| 1.0 (P100)  | 160 GB/s   | vs ~31.5 GB/s (Gen3) | 5.1×  |
| 2.0 (V100)  | 300 GB/s   | vs ~31.5 GB/s (Gen3) | 9.5×  |
| 3.0 (A100)  | 600 GB/s   | vs ~63 GB/s (Gen4)   | 9.5×  |
| 4.0 (H100)  | 900 GB/s   | vs ~126 GB/s (Gen5)  | 7.1×  |
| 5.0 (B200)  | 1.8 TB/s   | vs ~126 GB/s (Gen5)  | 14.3× |
| 6.0 (Rubin) | 3.6 TB/s   | vs ~242 GB/s (Gen6)  | 14.9× |

> 注：NVLink 1/2 對應 Gen3，NVLink 3 對應 Gen4，NVLink 4.0+ 對比最新 PCIe；對比基準為 PCIe x16 雙向頻寬，與第 1 節口徑一致。

---

## 參考資料

1. PCI-SIG Official Specifications — 各代速率定義 (https://pcisig.com)
2. 本倉庫 `pcie/01_pcie_comprehensive_guide.md` — PCIe 頻寬表與編碼說明
3. 本倉庫 `nvlink/nvlink_intro.md` — NVLink 各代頻寬表與技術演進
4. NVIDIA GB200 NVL4 Architecture Whitepaper (https://resources.nvidia.com)
5. NVIDIA H100 Tensor Core GPU Data Sheet (https://www.nvidia.com/en-us/data-center/h100/)
6. NVIDIA H200 Tensor Core GPU Product Page (https://www.nvidia.com/en-us/data-center/h200/)
7. 本倉庫 `superchips/nvidia_gb300.md` — GB200/GB300 規格對比
8. 本倉庫 `gpudirect/02_gpudirect_p2p.md` — GPU 拓撲與 P2P 性能
9. 本倉庫 `gpudirect/01_gpudirect_technology.md` — GDS 資料路徑與效能對比
10. NVIDIA Blackwell Ultra Datasheet — B300 GPU 規格 (https://resources.nvidia.com/en-us-blackwell-architecture/blackwell-ultra-datasheet)
11. [PCIe 頻寬實測](../../02_gpu_programming/04_profiling/02_pcie_bandwidth_measurement.md) — 零依賴 H2D/D2H 基准程序
12. [GPU 間資料傳輸方法實測](../../02_gpu_programming/04_profiling/09_gpu_transfer_methods.md) — 4 種方法 A100 實測對比
