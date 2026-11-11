# GPU 驅動故障速查——nvidia-smi 不可用時的排查路徑

GPU 運維中最讓人焦慮的不是效能差，而是 `nvidia-smi` 本身報錯——"Unable to determine the device handle"、"No devices were found"、"NVIDIA-SMI has failed"。這些問題通常和驅動載入、核心模組、DKMS 編譯相關，不是 GPU 硬件故障，但排查路徑和 `nvidia-smi` 正常工作時的健康檢查完全不同。

本文按故障現象分類——每種現象給出一句話的根因和最可能的修復命令。

---

## 一、現象分類速查

| 現象                                                    | 最可能的根因                                                | 最快驗證                                            |
| ------------------------------------------------------- | ----------------------------------------------------------- | --------------------------------------------------- |
| `nvidia-smi` 報 "No devices were found"                 | 驅動未載入，或 GPU 被 nouveau 占用                          | `lsmod \| grep nvidia`；`lsmod \| grep nouveau`      |
| `nvidia-smi` 報 "Unable to determine the device handle" | GPU 處於故障態或 `/dev/nvidia*` 裝置項陳舊（fallen off the bus、驅動過載後最常見）；nouveau 佔用也會觸發（其典型表現是 "No devices were found"） | `dmesg \| grep -i "Xid\|fallen"`；`lspci -nnk \| grep -A3 NVIDIA` |
| `nvidia-smi` 卡住，無輸出                               | GPU 陷入不可恢復狀態             | `dmesg \| tail -30` 查 XID 錯誤                     |
| 驅動更新後 `nvidia-smi` 版本不匹配                      | DKMS 編譯失敗或未重啟            | `cat /proc/driver/nvidia/version` 對比 `nvidia-smi` |
| GPU 在 `lspci` 中可見但 `nvidia-smi` 看不到             | PCIe AER 錯誤導致 GPU 被隔離     | `dmesg \| grep -i "AER\|PCIe.*error"`               |

---

## 二、驅動未載入

```bash
# 檢查核心模組
lsmod | grep nvidia
# 應有: nvidia_uvm, nvidia_drm, nvidia_modeset, nvidia

# 手動載入
modprobe nvidia
modprobe nvidia_uvm

# 檢查載入失敗原因
dmesg | grep -i nvidia | tail -20
```

**常見原因**：

| 原因                                    | 修復                                                                                                                               |
| --------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| Secure Boot 阻止了未簽名的核心模組      | `mokutil --sb-state` 確認，在 BIOS 中禁用或簽名模組                                                                                |
| 核心升級後驅動未重新編譯                | `dkms status` 看 nvidia 模組狀態，手動 `dkms install nvidia/<ver>`                                                                 |
| `nouveau` 驅動佔用了 GPU（Ubuntu 預設） | `lsmod \| grep nouveau`，有則 `echo 'blacklist nouveau' > /etc/modprobe.d/blacklist-nouveau.conf && update-initramfs -u && reboot` |

---

## 三、驅動版本不匹配

驅動更新後最常見的坑：核心模組已載入新版本，但使用者態庫（`nvidia-smi`、`libcuda.so`）還是舊的。

```bash
# 對比核心模組版本 vs 使用者態版本
cat /proc/driver/nvidia/version | head -1
nvidia-smi | head -1

# 如果兩者不一致，重啟後一般就能解決。未重啟時：
# 1. 解除安裝舊模組 → 載入新模組
rmmod nvidia_uvm nvidia_drm nvidia_modeset nvidia
modprobe nvidia nvidia_uvm
```

**DKMS 編譯失敗**——更新核心或驅動後模組無法自動編譯：

```bash
dkms status                          # 查看所有 DKMS 模組狀態
dkms status | grep nvidia            # 只看 NVIDIA
# installed = 編譯成功, added = 未編譯, failed = 編譯失敗

# 手動重新編譯
dkms remove nvidia/<version> --all
dkms install nvidia/<version>
```

---

## 四、GPU 在 lspci 中可見但不可用

```bash
lspci -nnk | grep -A3 NVIDIA
# 檢查 "Kernel driver in use" 是否為 nvidia
# 如果是 "nouveau" → §二 黑名單步驟
# 如果是 "vfio-pci" → GPU 被透傳給虛擬機器，宿主機 nvidia-smi 不可用
# 如果是空或 "(none)" → 驅動未繫結該 GPU
```

**PCIe AER 錯誤導致 GPU 被隔離**——核心檢測到 PCIe 裝置多次錯誤後將其停用：

```bash
dmesg | grep -i "AER\|PCIe.*error\|corrected"
# 出現 "AER: Corrected error received" → 單次可忽略
# 出現 "AER: Uncorrected (Fatal) error" → GPU 可能已被隔離

# 重新掃描 PCIe 匯流排恢復（無需重啟）
echo 1 > /sys/bus/pci/devices/0000:XX:00.0/remove
echo 1 > /sys/bus/pci/rescan
```

---

## 五、nvidia-persistenced 問題

`nvidia-persistenced` 保持 GPU 驅動在核心中常駐。如果它掛了，空閒 GPU 會被驅動解除安裝，下一次訪問有 1-2s 冷啟動延遲——對延遲敏感的場景（如線上推理）影響顯著。

```bash
# 狀態檢查
systemctl status nvidia-persistenced

# 如果看到 "GPU 0000:XX:00.0 has fallen off the bus"
# → GPU 硬體脫離 PCIe 匯流排，不是 persistenced 的問題
# → 檢查電源、散熱、物理連線

# 恢復 persistenced（§四的情況排除後）
systemctl restart nvidia-persistenced

# 若只是持久化模式被關掉，重新開啟即可。注意 -pm 只切換驅動常駐，
# 不清理已退出行程的 context；要徹底清理用 GPU reset（-r，需無行程佔用）：
nvidia-smi -pm 1
```

---

## 六、舊 GPU（Kepler/Maxwell/Pascal/Volta）兼容性

Kepler（CC 3.x）早已移出主線；Maxwell（CC 5.x）、Pascal（CC 6.x）和 Volta（CC 7.0）自 CUDA 13.0 起也不再支持，驅動止於 R580 legacy 分支。如果 `nvidia-smi` 顯示 "Legacy Support" 或 CUDA 版本不兼容：

```bash
# 查詢 GPU 的計算能力
nvidia-smi --query-gpu=compute_cap --format=csv,noheader

# 截至 2026-11 的支援口徑（CUDA 13.0 起最低要求 CC 7.5）：
# Kepler (3.x)              → 早已移除，止步 CUDA 11.x，對應 legacy 驅動分支
# Maxwell (5.x) / Pascal (6.x) / Volta (7.0)
#                           → CUDA 13.0 已移除，止步 CUDA 12.x；驅動止於 R580 legacy 分支
# Turing (7.5) 及之后       → 當前 CUDA 13.x 仍支持
```

---

## 七、相關資源

- [nvidia-smi 場景速查](03_nvidia_smi_guide.md) — 驅動正常後的日常運維命令
- [GPU 叢集健康檢查](06_gpu_health_check.md) — L1/L2/L3 檢查流程
- [NVIDIA Driver Installation Quickstart](https://docs.nvidia.com/datacenter/tesla/driver-installation-guide/index.html)
- [NVIDIA GPU Deployment and Management Documentation](https://docs.nvidia.com/deploy/)
