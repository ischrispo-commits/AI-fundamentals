# vLLM + LWS：Kubernetes 上的多機多卡推理方案

隨著 `LLM` 推理的工程實踐不斷深入，現有推理框架在部署能力方面的不足日益顯現：例如難以跨節點統一管理多個 `Pod` 的生命周期、資源排程粒度過粗、缺乏分散式拓撲感知等問題。針對這些挑戰，`Kubernetes` 推出了一種新的控制器原語 —— `LeaderWorkerSet`（簡稱 **LWS**），用於支援“分散式啟動”“資源組排程”“拓撲感知”“組級原子恢復”等推理服務中的關鍵能力，成為包括 `vLLM`、`TensorRT-LLM` 在內的新一代大模型推理系統的重要執行支撐。

## 什麼是 LWS？

`LeaderWorkerSet`（LWS）是 `Kubernetes` 新引入的一個 `CRD`（`CustomResourceDefinition`，自定義資源類型），其設計目標是 **支持分布式 AI 作業的原生部署與管理**，在部署結構上強調以下特點：

- **分散式角色結構**：`LWS` 將一組邏輯相關的 `Pod` 分為一個 `Leader Pod` 和多個 `Worker Pod`。`Leader` 負責初始化任務、構建主控制流，`Worker` 負責協同工作。
- **統一生命週期管理**：`LWS` 保證一組 `Pod` 的建立、銷燬、狀態檢查以”組”為單位統一管理，解決了 `Deployment`、`StatefulSet` 等原生控制器在處理多角色任務時的能力不足。
- **拓撲感知能力**：透過對 `Node` 拓撲結構的感知（如 `GPU`、`NUMA`、`TPU` 拓撲等），`LWS` 能為推理場景中的”低延遲、強繫結”資源排程提供基礎。
- **狀態同步能力**：`Leader` 可透過註解等機制將服務發現、埠號、共享參數等元資訊同步給 `Worker`，降低叢集服務編排的複雜性。

簡言之，`LWS` 旨在提供一種 **更符合 AI 原生工作負載特點的分散式控制器語義**，填補現有原語在推理部署上的能力空白。

![Conceptual View](https://lws.sigs.k8s.io/images/concept.png)

### 與傳統控制器的對比

`Kubernetes` 中已有多種控制器原語，如 `Deployment`、`StatefulSet`、`Job`、`ReplicaSet` 等，它們在構建無狀態服務或狀態服務方面表現出色。然而，對於如 `vLLM`、`TensorRT-LLM` 這類 **異構資源強繫結 + 啟動順序依賴 + 多節點資源協同** 的工作負載，傳統原語存在如下不足：

| **控制器**                  | **適用場景**                | **不足**                           |
| --------------------------- | --------------------------- | ---------------------------------- |
| `Deployment` / `ReplicaSet` | 無狀態服務（如 Web 服務）   | 缺乏角色區分、拓撲感知             |
| `StatefulSet`               | 狀態服務（如資料庫）        | 排程粒度為單 Pod，跨節點通訊能力弱 |
| `Job` / `CronJob`           | 離線批處理任務              | 不支援長週期常駐服務               |
| `DaemonSet`                 | Node 級服務（如日志收集器） | 無法動態擴展，資源排程不可控       |

相比之下，**LeaderWorkerSet 是首個支援 Pod 間主從角色語義的控制器**，具有以下差異化能力：

1. **生命周期一致性**：`Leader` 與 `Worker` 被繫結為一個邏輯部署單元，狀態同步、重建過程均由控制器原子管理。
2. **拓撲表達能力**：`Worker` 可感知 `Leader` 所在節點資訊，實現“**同 NUMA**”、“**同 switch**”等低延遲協同。
3. **分布式配置能力**：透過註解或 `Downward API` 等方式傳遞 `Leader` 地址、端口、分散式參數，簡化排程邏輯。

## LWS 的核心優勢

### 1. 統一的生命週期管理

`LWS` 將 `Super Pod` 作為原子單元進行擴縮容和更新，確保組內狀態一致性。例如：

- 擴縮容時以組為單位增減資源池。
- 滾動更新以組為單位逐組替換，`maxUnavailable`/`maxSurge` 控制節奏，一個組只有 Leader 和全部 Worker 都 Ready 才算就緒。
- 故障時優先區域性恢復，必要時整組重建（`restartPolicy: RecreateGroupOnPodRestart`，組內任一 Pod 重啟即整組重建）。

### 2. 拓撲感知的排程

`LWS` 自身依賴 `Kubernetes` 原生的 `Pod Topology Spread Constraints`，配合廠商各自的拓撲註解使用（`LWS` 沒有內建廠商拓撲註解，不同環境用各自的擴展）：

```yaml
# Google TPU 叢集（GKE 注解）
annotations:
  cloud.google.com/gke-tpu-topology: "4x4x4"
```

支持 `NVLink` 域內排程、`TPU` 切片繫結等高階場景，降低跨節點通訊延遲。

### 3. 彈性伸縮與資源最佳化

與 `HPA` 深度集成，支援基於多維指標（請求佇列、`GPU` 利用率）的彈性伸縮。資源分配透過 `limits`/`requests` 精細化控制，結合 `NVIDIA MIG` 技術可將單 `GPU` 劃分為多個實例，提升利用率。

### 4. 安全與可觀測性

- **憑證管理**：透過 `Secrets` 儲存敏感資訊，避免明文暴露。
- **網路隔離**：使用 `NetworkPolicy` 限制 `Worker` 僅允許與 `Leader` 通信。
- **監控體系**：采集 `GPU` 利用率、`KV Cache` 使用率等關鍵指標。

## vLLM 場景下的能力支撐分析

`vLLM` 是一個專為大語言模型推理最佳化的高效能引擎，在實際部署中，它往往要求：

- 橫跨多個節點使用 GPU/TPU；
- `Worker` 需透過 `gRPC` 接入 `Leader` 完成分布式 `KV Cache` 管理；
- 推理參數（如 `max num tokens`）需由 `Leader` 向 `Worker` 廣播；
- 啟動與恢復需具備原子性，避免部分 `Worker` 卡死或重連失敗。

這些需求中，`LWS` 提供的組級排程與啟動順序控制能力、拓撲感知能力、配置動態傳遞能力，恰好能夠完整覆蓋，如下表所示：

| **能力需求** | **LWS 提供方式**                                 |
| ------------ | ------------------------------------------------ |
| 角色區分     | Leader / Worker 模板                             |
| 啟動順序     | Leader 先啟動，地址寫入註解，Worker 自動感知     |
| 參數廣播     | Leader 將 tokens、埠等寫入 CRD，被 Worker 讀取 |
| 拓撲排程     | Worker 可設定和 Leader 相同的 NUMA 區域          |
| 異常恢復     | 控制器統一重啟整個組，保證狀態一致性             |

## vLLM 與 LWS 的實戰部署

### 配置解析

以下是使用 `LeaderWorkerSet`（LWS）在 `Kubernetes` 上部署 `vLLM` 的配置示例：

```yaml
apiVersion: leaderworkerset.x-k8s.io/v1
kind: LeaderWorkerSet
metadata:
  name: vllm
spec:
  replicas: 2
  leaderWorkerTemplate:
    size: 2
    restartPolicy: RecreateGroupOnPodRestart
    leaderTemplate:
      metadata:
        labels:
          role: leader
      spec:
        containers:
          - name: vllm-leader
            image: docker.io/vllm/vllm-openai:latest
            env:
              - name: HUGGING_FACE_HUB_TOKEN
                value: <your-hf-token>
            command:
              - sh
              - -c
              - "bash /vllm-workspace/examples/online_serving/multi-node-serving.sh leader --ray_cluster_size=$(LWS_GROUP_SIZE);
                python3 -m vllm.entrypoints.openai.api_server --port 8080 --model meta-llama/Meta-Llama-3.1-405B-Instruct --tensor-parallel-size 8 --pipeline_parallel_size 2"
            resources:
              limits:
                nvidia.com/gpu: "8"
                memory: 1124Gi
                ephemeral-storage: 800Gi
              requests:
                ephemeral-storage: 800Gi
                cpu: 125
            ports:
              - containerPort: 8080
            readinessProbe:
              tcpSocket:
                port: 8080
              initialDelaySeconds: 15
              periodSeconds: 10
            volumeMounts:
              - mountPath: /dev/shm
                name: dshm
        volumes:
          - name: dshm
            emptyDir:
              medium: Memory
              sizeLimit: 15Gi
    workerTemplate:
      spec:
        containers:
          - name: vllm-worker
            image: docker.io/vllm/vllm-openai:latest
            command:
              - sh
              - -c
              - "bash /vllm-workspace/examples/online_serving/multi-node-serving.sh worker --ray_address=$(LWS_LEADER_ADDRESS)"
            resources:
              limits:
                nvidia.com/gpu: "8"
                memory: 1124Gi
                ephemeral-storage: 800Gi
              requests:
                ephemeral-storage: 800Gi
                cpu: 125
            env:
              - name: HUGGING_FACE_HUB_TOKEN
                value: <your-hf-token>
            volumeMounts:
              - mountPath: /dev/shm
                name: dshm
        volumes:
          - name: dshm
            emptyDir:
              medium: Memory
              sizeLimit: 15Gi
---
apiVersion: v1
kind: Service
metadata:
  name: vllm-leader
spec:
  ports:
    - name: http
      port: 8080
      protocol: TCP
      targetPort: 8080
  selector:
    leaderworkerset.sigs.k8s.io/name: vllm
    role: leader
  type: ClusterIP
```

> 詳細配置說明請參見 [vLLM 官方文件](https://docs.vllm.ai/en/latest/deployment/frameworks/lws.html)。

**關鍵配置說明**：

- **動態組規模傳遞**：透過註解機制，`$(LWS_GROUP_SIZE)` 動態注入組內 Pod 數量，確保資源分配的靈活性。
- **服務發現機制**：`Worker` Pod 透過註解 `leaderworkerset.x-k8s.io/leader-address` 自動獲取 `Leader` 的地址，實現高效的服務發現。

## 效能調優與部署實踐

`vLLM` 對推理效能高度敏感，部署時通常採用多機多卡結構（GPU/TPU），以實現模型並行和吞吐最佳化。以下是某企業在生產環境中的部署經驗總結：

- **模型規模**：使用 `Mixtral 8x7B`（約 46.7B 參數），AWQ 量化後模型大小約 `26GB`。
- **部署結構**：1 個 `Leader` + 3 個 `Worker`，每個 `Worker` 節點分配 2 塊 `GPU`，採用張量並行機制。
- **核心參數調優示例**：

  ```bash
  python3 -m vllm.entrypoints.openai.api_server \
    --model /models/mixtral \
    --dtype auto \
    --tensor-parallel-size 4 \
    --max-model-len 8192 \
    --gpu-memory-utilization 0.9 \
    --quantization awq \
    --enforce-eager \
    --max-num-batched-tokens 8192 \
    --max-num-seqs 256 \
    --disable-log-stats
  ```

- **調優要點說明**：
  - `--tensor-parallel-size`：結合多卡部署設定張量並行維度。
  - `--gpu-memory-utilization`：控制每張 `GPU` 的顯存使用上限，避免 `OOM`。
  - `--quantization`：使用 `awq` 量化以減小模型載入體積。
  - `--max-num-batched-tokens` 與 `--max-num-seqs`：控制批處理規模，提升吞吐性能。
  - `--enforce-eager`：跳過 CUDA Graph 構建，降低啟動延遲（以部分吞吐為代價）。

該配置可在保持高吞吐的同時，兼顧大模型的響應延遲需求。

## 未來趨勢與能力展望

`LWS` 已发布 v1.0，API 進入 v1（`leaderworkerset.x-k8s.io/v1`，與本文示例一致），其組級排程原語已被 `vLLM`、`llm-d` 等推理系統採納為多機編排的執行基座。在未來，以下方向可能成為演進重點：

- **更強的異構資源排程表達能力**：引入 `GPU` 型號、`TPU topology-aware` 等特徵排程；
- **與 Service Mesh 結合**：`Worker` 動態加入統一負載平衡服務；
- **與 HPA（水平自動擴展）協同**：根據負載自動調整 `Worker` 數量。

此外，LWS 的控制器機制也可能被擴展用於訓練作業、線上增量學習等更廣泛的場景中，成為 AI native workload 的基礎控制器抽象。

## 擴展閱讀

- [LWS 官方文件](https://lws.sigs.k8s.io)
- [Kubernetes 拓撲排程指南](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/)
- [vLLM 多節點部署實踐](https://www.cecg.io/blog/multinode-llm-serving/)
