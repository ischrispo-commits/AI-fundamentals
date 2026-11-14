# 混合專家系統（MoE）圖解指南

> 原文：`https://newsletter.maartengrootendorst.com/p/a-visual-guide-to-mixture-of-experts`<br/>
> 作者：`Maarten Grootendorst`

在追蹤最新發布的大型語言模型時，你會發現許多模型的標題中都標註著「MoE」。這個「MoE」究竟代表什麼？為何能成為眾多 LLM 的架構首選？

本圖解指南將透過 50+ 組視覺化圖，帶你深入探索這一核心元件——混合專家系統（Mixture of Experts）。

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F50a9eba8-8490-4959-8cda-f0855af65d67_1360x972.png)

本文將系統解析 MoE 架構的兩大核心模組：專家系統與路由分配器。

> 作者還著有《**大型語言模型實戰指南**》（程式碼在 [GitHub](https://github.com/HandsOnLLM/Hands-On-Large-Language-Models) 開源）。

混合專家系統（Mixture of Experts，MoE）是一種透過協同多個差異化子模型（即「專家單元」）來提升大型語言模型效能的技術正規化。

MoE 架構包含兩大核心元件：

* 專家叢集——每個前饋神經網路層配置了可動態排程的多組專家單元集合這些專家單元本質上仍保持前饋神經網路的結構特性；
* 路由分配器（門控網路）——負責確定文字標記的專家排程路徑。

在集成`MoE`的大型語言模型各層級中，均部署了（具有領域特化能力的）專家單元：

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F7931367a-a4a0-47ac-b363-62907cd6291c_1460x356.png)

需要明確的是，這裡所說的“專家單元”並非專攻“心理學”或“生物學”等特定領域。其學習能力主要侷限於詞彙層面的語法資訊：

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fc6a81780-27c8-45f8-bccc-cc8f1ce3e943_1460x252.png)

更準確地說，這些專家系統的核心能力體現在處理**特定語境中的文字標記**。

路由決策層（門控網路）會為當前輸入層動態選擇最優的專家叢集：

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fb6a623a4-fdbc-4abf-883b-3c2679b4ad4d_1460x640.png)

每個專家單元並**非完整**的語言大模型，而是大模型架構中的**子模組元件**。

要深入理解專家系統的**表徵機制**和**工作原理**，我們首先需要剖析`MoE`技術旨在替代的核心結構——密集連線層。

混合專家系統的底層基礎源於語言大模型中的前饋神經網路（`FFNN`）模組。

值得注意的是，在標準的僅解碼器架構`Transformer`中，`FFNN`應用在層標準化處理之後：

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fd4729d2a-a51a-4224-93fe-c5674b9b38eb_1460x800.png)

前饋神經網路能夠利用注意力機制生成的上下文資訊，透過深度轉換捕捉資料中更復雜的關聯模式。

但前饋神經網路的參數量會呈現指數級增長趨勢。為了學習這些複雜的關係，模型通常會對接收的輸入資訊進行擴展處理：

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F091ec102-45f0-4456-9e0a-7218a49e01df_1460x732.png)

傳統`Transformer`中的前饋神經網路被稱為**稠密模型**，因為所有模型參數（包括**權重**和**偏置項**）都會被激活。所有輸入資訊都會被完整保留並參與輸出結果的計算。

仔細分析稠密模型可以發現，輸入資訊會在不同程度上激活所有參數：

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F101e8ddc-9aa7-4e24-92fc-78d25da73399_880x656.png)

與之形成對比的是**稀疏模型**，這類模型僅**激活部分參數**，其原理與混合專家系統密切相關。

具體實現上，可將稠密模型拆分為多個專家單元，經重新訓練後，每次推理僅激活部分專家叢集：

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fcc4eeaf8-166b-419f-896c-463498af5692_880x656.png)

核心原理在於：每個專家單元在訓練過程中會習得不同的資訊特徵；執行推理時，僅呼叫與當前任務最相關的專家。

當處理具體問題時，可選取最適合當前任務的專家單元：

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fce63e5cc-9b82-45b4-b3dc-9db0cac47da3_880x748.png)

如前所述，專家叢集學習的資訊粒度比整個領域更細緻[1](https://newsletter.maartengrootendorst.com/p/a-visual-guide-to-mixture-of-experts#footnote-1-148217245) ，因此將其統稱為'專家'有時可能不夠準確。

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F04123f9e-b798-4712-bcfb-70a26438f3b9_2240x1588.png)

`ST-MoE`論文中編碼器模型的專家單元展現出顯著的專業化特性。

然而在解碼器模型中，專家叢集的專業化特徵表現相對模糊。但這並不代表所有專家單元都具備相同效能。

[Mixtral 8x7B論文](https://arxiv.org/pdf/2401.04088) 提供了典型范例，論文中每個文字標記均按首選專家單元進行顏色編碼。

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fd03e32b4-5830-4d98-8514-0c1a28127ed9_1028x420.png)

視覺化分析同時揭示，專家系統更多聚焦**語法結構**而非特定領域特徵。

因此，雖然解碼器專家單元未顯現明確專業方向，但其對特定類型標記的處理仍保持穩定模式。

儘管將專家單元視為分割後的稠密模型隱藏層有助於直觀理解，但實際上它們通常是完整的前饋神經網路結構：

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fe51561eb-f3d6-45ca-a2f8-c71abfa7c2a9_880x748.png)

鑑於多數大型語言模型配置多個解碼器模組，文字生成需經歷多層級聯的專家系統處理流程：

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F89b1caad-5201-43fe-b7de-04ebe877eb2d_1196x836.png)

不同文字標記選擇的專家單元存在差異，最終形成多樣化的'處理路徑'：

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fcde4794d-8b3e-454d-9a1c-88c1999fdd45_1372x932.png)

若重構解碼器模組的視覺化模型，當前應呈現多個獨立的前饋神經網路（每個對應一個專家單元）：

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fb97a8ac7-db97-497f-866d-10400729d51e_1248x764.png)

當前解碼器模組整合了多個前饋神經網路（每個作為獨立的'專家單元'），可在推理過程中靈活呼叫。

在構建專家叢集后，模型如何智慧選擇適用的專家系統？

專家層前端配置的路由分配器（亦稱門控網路），經訓練為每個文字標記匹配合適的專家單元。

路由分配器本身是一個前饋神經網路，基於輸入特徵動態選擇專家單元，透過機率輸出實現匹配：

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Facc49abf-bc55-45fd-9697-99c9434087d0_864x916.png)

專家層將選定專家單元的輸出結果與門控值（選擇機率）進行加權後輸出。

路由分配器與專家叢集（僅部分激活）共同組成**混合專家架構層**：

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fa6fcabc6-78cd-477f-ac4e-2260cb06e230_1160x688.png)

混合專家架構層提供兩種形態：_**稀疏型**_ 與 _**密集型**_ 專家系統組合方案。

兩者雖均採用路由分配機制，但稀疏混合架構僅激活少數專家單元，而密集型架構則全量呼叫並實施差異化權重分配。

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F46aadf17-3afe-4c98-b57c-83b7b38918b2_1004x720.png)

例如，給定一組文字標記時，密集型 MoE 的路由方式是把標記交給全部專家單元、按門控權重加權聚合；稀疏 MoE 則只選取少量專家單元參與計算。

在當前大型語言模型的技術現狀中，所提及的`MoE`通常特指稀疏混合專家架構，這種設計允許系統僅呼叫部分專家單元進行運算。這種架構顯著降低了計算成本，這對大型語言模型的執行效率具有關鍵意義。

門控網路是混合專家架構的核心元件：它既主導推理過程中的專家選擇，也在訓練流程中起關鍵調控作用。

在最基礎的數學表達中，輸入向量(_**x**_)將與路由權重矩陣(_**W**_)進行矩陣乘法運算：

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F58234ce0-bf96-49ab-b414-674a710a1c3c_1164x368.png)

隨後透過**SoftMax函式**對輸出值進行處理，生成針對各專家單元的機率分佈函式**G**(_**x**_)：

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fb888a32f-acef-4fff-9d4b-cc70e148a8f2_1164x384.png)

路由分配器基於該機率分佈，為每個輸入選擇最適配的專家單元進行處理。

最終系統將每個路由通道的輸出結果與對應專家單元的計算輸出相乘，並進行聚合求和操作。

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fe6e46ea4-dbd4-4cc4-aa2b-2c5474917f31_1164x464.png)

讓我們將各模組整合，完整解析輸入資料在路由決策層與專家叢集間的流動路徑：

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fd5d24a0b-2d78-4c69-b6fe-d75ba34bdd0c_2080x2240.png)

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F3d1122aa-7248-47d0-8e01-caa941ce0aa9_2080x2240.png)

然而，這種簡單的函式設計往往導致路由決策層持續選擇同一專家單元，因為部分專家單元可能具有更快的參數更新速度：

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F9233733c-c152-428a-ae99-1ed185fc3d50_1164x660.png)

這不僅會造成專家選擇分佈失衡，部分專家甚至可能完全無法獲得有效訓練，最終導致訓練流程與推理過程的雙重問題。

我們的最佳化目標是確保各專家單元在訓練和推理階段保持均衡激活狀態，該機制被稱為**負載均衡**。本質上，這種設計旨在防止模型對固定專家單元產生路徑依賴式的過擬合。

要實現專家單元的重要性均衡，必須重點最佳化路由分配器——這個決定專家選擇時序的核心控制元件。

實現路由層負載均衡的有效方法之一是採用[KeepTopK](https://arxiv.org/pdf/1701.06538) [2](https://newsletter.maartengrootendorst.com/p/a-visual-guide-to-mixture-of-experts#footnote-2-148217245) 擴展機制。透過注入可訓練的高斯噪聲參數，系統能夠打破專家選擇的固化模式：

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F1b95b020-ae34-40f0-a5c4-9542343beea9_1164x412.png)

隨後，除需要激活的前`k`個專家單元（例如2個）外，其餘專家單元的權重將被設定為 **-∞**:

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F66bea40e-3fb0-4937-88d5-2852af456cf3_1164x488.png)

透過將對應權重設為 **-∞**，這些權重經 `SoftMax` 函式處理後得到的機率值將為 **0**：

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F687d2279-1d8b-4af1-b55e-55d618ee877f_1164x496.png)

儘管存在諸多優質替代方案，`KeepTopK`策略仍是當前多數大型語言模型採用的核心路由機制。需注意，KeepTopK策略可不依賴額外噪聲獨立運作。

`KeepTopK`策略透過為每個文字標記選擇特定專家單元實現定向處理。該方法稱為_標記擇路_[3](https://newsletter.maartengrootendorst.com/p/a-visual-guide-to-mixture-of-experts#footnote-3-148217245) ，支援將文字標記路由至單一專家（ _Top-1路由_ ）：

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fdf7a9988-d4c8-4b1b-a968-073a6b3bfc6a_1004x648.png)

或同時分配給多個專家單元（top-k路由）：

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fb3f283f1-c359-4baf-8d01-8ebb2a90665f_1004x720.png)

關鍵優勢在於可實現專家系統貢獻度的動態加權與有機融合。

為確保訓練過程中專家叢集的均衡呼叫，網路在常規損失函式外特別引入了輔助損失（亦稱 _負載均衡損失_ ）。

該約束條件強制要求所有專家單元必須保持同等的重要性權重。

該輔助損失函式的第一部分計算方式為：對整批資料中各專家單元的路由分配值進行求和。

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff3624da0-3137-42ba-95e8-88fcbddb5f9f_1108x288.png)

由此可獲得各專家單元的 _重要性評分_，該指標反映了不考慮輸入層時專家單元被選中的機率分佈。

基於此可計算 _變異係數_ (**CV**)，用於量化不同專家單元間重要性評分的離散程度。

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F94def8dc-2a65-4a02-855f-219f0df2a119_916x128.png)

舉例說明，當專家單元間重要性評分差異顯著時，**CV**值將呈現較高水平：

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fab71b90c-ba29-42a9-944b-3dee52fc5c32_916x372.png)

反之，若所有專家單元重要性評分趨近一致，**CV**值則處於較低區間（這正是預期的最佳化目標）：

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fc5cb91ac-4aab-4eb5-80bf-84e2bd4dc576_916x324.png)

透過引入**CV**指標，我們可以在訓練流程中動態調整 _輔助損失函式_，使其以最小化**CV**值為最佳化方向（從而實現各專家單元的重要性權重均衡化）：

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff4aac801-af89-44e7-aaea-c57a55ff282c_916x312.png)

最終，該輔助損失函式將作為獨立的最佳化目標項整合到整體訓練流程中。

不平衡現象不僅存在於被選中的專家叢集中，也體現在分配到各專家的文字標記分佈上。

例如，若輸入層的文字標記被不成比例地分配給某個專家單元，則可能導致該專家訓練不足：

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F749eac8e-36e5-450f-a6fc-fbe48b7a1312_1004x484.png)

在此場景下，關鍵不僅在於選用哪些專家系統，更在於其被呼叫的**強度**。

該問題的解決方案是設定 _專家容量_ [4](https://newsletter.maartengrootendorst.com/p/a-visual-guide-to-mixture-of-experts#footnote-4-148217245) ，即限制單個專家單元可處理的文字標記數量。當專家達到容量上限時，溢位的文字標記將自動路由至下一順位專家：

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fdf67563f-755a-47a7-bebc-c1ac81a01f8f_1004x568.png)

若所有專家單元均達到容量上限，未處理的文字標記將繞過專家層直接傳遞至後續網路層。該機制被稱為 _**標記溢位現象**_。

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fe92ce4c5-affa-454d-8fd2-4debf9a08ce2_1004x544.png)

`Switch Transformer`[5](https://newsletter.maartengrootendorst.com/p/a-visual-guide-to-mixture-of-experts#footnote-5-148217245) 作為首個基於`Transformer`架構的`MoE`模型，成功解決了訓練穩定性問題（如負載均衡）。該模型在提升訓練穩定性的同時，顯著簡化了系統架構和訓練流程。

`Switch Transformer`是基於`T5`模型（編碼器-解碼器架構）改進的模型，透過用交換層替代傳統的前饋神經網路層。該交換層採用稀疏混合專家架構（`Sparse MoE`），基於`Top-1`路由選擇機制為每個文字標記分配唯一專家單元。

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F024d1788-9007-4953-9bf7-883da0db7f8d_1160x688.png)

路由分配器採用直接計算方法確定專家選擇：將輸入資料與專家權重矩陣相乘後，透過`SoftMax`函式處理得到路由決策（與前期處理方法保持一致）。

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff0758a7f-e26b-44b9-9d75-80ac6caa9802_1104x384.png)

這種`Top-1`路由選擇架構的設計假設是：路由分配器僅需呼叫單一專家單元即可完成輸入資料的有效路由學習。這與我們先前討論的`top-k`路由機制形成理論對比——後者認為需要透過多個專家叢集的協同工作才能實現最佳路由行為學習。

容量因子作為核心參數，直接決定單個專家單元可處理的文字標記最大數量。`Switch Transformer`透過創新性地引入**容量因子**這一關鍵參數，實現了對專家系統處理能力的動態調控與最佳化擴展。

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F22715139-3955-4e00-bed7-c45cffa52744_964x128.png)

專家系統容量的構成要素包含以下簡明維度：

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff4b399c6-723b-4de6-94ca-7020cd1bb181_908x380.png)

當容量因子數值增大時，每個專家單元可處理的文字標記數量將獲得線性提升。

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F7fd2aea0-fddf-4a43-ac79-7c5e5194c115_1240x472.png)

然而，若容量因子設定過大，會導致計算資源浪費。相反，若容量因子過小，模型效能將因 _標記溢位現象_ 而降低。

為進一步防範標記丟失問題，研究團隊採用了簡化版的輔助損失函式。

相較於計算變異係數，該簡化損失函式透過權衡專家單元的標記分配比例與其路由機率佔比來實現最佳化：

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F608da44a-7510-4ab6-97c9-e8ab212a567d_836x388.png)

由於目標是在**N**個專家單元間實現標記的均勻路由分配，因此需要確保向量**P**和**f**的取值均為**1/N**。

超參數**α**可用於在訓練過程中精確調節該損失函式的影響權重。參數值過高會壓制主損失函式，過低則對負載均衡作用甚微。

混合專家技術並非語言模型專屬的解決方案。基於`Transformer`架構的視覺模型（如`ViT`）天然具備整合混合專家系統的可能性。

簡而言之，`ViT`（視覺`Transformer`）是一種將影象分割為影象分塊進行處理的架構，其處理邏輯與文字標記高度相似。[6](https://newsletter.maartengrootendorst.com/p/a-visual-guide-to-mixture-of-experts#footnote-6-148217245)

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F11b64fce-4069-4c73-995d-c3059fda0dcc_1300x828.png)

這些影象分塊（或文字標記）在輸入標準編碼器前，會被轉換為附帶位置編碼的嵌入表示。

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fc0b2ea60-238b-446a-ab59-503efb6ca061_1228x1232.png)

當這些分塊進入編碼器時，其處理方式與文字標記類似，這種設計使得架構能夠完美適配混合專家系統。

視覺混合專家架構（`V-MoE`）是影象領域首批成功應用混合專家技術的模型之一[7](https://newsletter.maartengrootendorst.com/p/a-visual-guide-to-mixture-of-experts#footnote-7-148217245) ，其在`ViT`架構基礎上，將編碼層的稠密前饋網路替換為稀疏混合專家系統。

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F10e9721d-4b3f-4062-ad72-97ffd1049077_1160x944.png)

這使得原本規模較小的`ViT`模型，透過擴展專家叢集實現了參數量的顯著提升。

考慮到影象通常包含大量分塊，為緩解硬體限制，每個專家單元都預設了較小的處理容量。但容量過低容易導致分塊被丟棄（類似 _標記溢位_ 問題）。

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F219141c9-51ff-4d85-9f8a-c705c6e9ece4_1720x744.png)

為維持低容量配置，網路透過優先順序機制——先處理高重要性評分分塊，使得溢位分塊通常具有較低語義重要性。這種方法被稱作批次 _優先順序路由_ 機制。

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fa0ef5323-4b4c-4ee7-8a53-51fbe4213283_1720x772.png)

因此，即使文字標記的比例降低，我們仍能確保重要影象分塊被正確路由。

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F65f972b9-640b-4a76-b77d-2d2ef1b40609_1736x420.png)

優先順序路由機制透過聚焦最關鍵的分塊，可顯著減少需要處理的影象分塊數量。

在`V-MoE`架構中，優先順序評分器能有效區分影象分塊的重要性差異。但每個專家單元僅處理被分配的分塊，導致未處理圖塊的資訊丟失。

`Soft-MoE`透過混合圖塊的方式，實現了從離散分配到柔性分配的轉變（適用於圖塊和文字標記）。[8](https://newsletter.maartengrootendorst.com/p/a-visual-guide-to-mixture-of-experts#footnote-8-148217245)

首先將輸入特徵 **x**（即圖塊嵌入表示）與可訓練參數矩陣Φ進行矩陣相乘。由此生成 _路由決策資訊_，該資訊量化了特定文字標記與各專家單元的相關性強度。

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F644c0c1c-24d3-491b-a9a2-fdd9658ad589_1032x516.png)

透過對路由資訊矩陣按列執行`SoftMax`運算，我們動態更新每個圖塊的嵌入表示。

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F6c3187d8-5bf2-4c73-8c22-547107fe1152_1032x456.png)

更新後的圖塊嵌入表示本質上是所有圖塊嵌入表示的加權平均結果。

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F7cfeb30a-1b04-4b9a-8f5a-d3c5d47e6499_1376x400.png)

從視覺角度觀察，所有圖塊呈現出混合交融的狀態。這些整合後的圖塊資料將被並行傳輸至各專家單元進行處理。輸出結果生成後，需再次與路由決策矩陣進行乘積運算。

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F86020d75-c881-4418-82a6-a228f091abe8_808x844.png)

路由決策機制在文字標記層級調控輸入資料，並在專家系統層級調控輸出結果。

由此我們得到經過處理的**柔性**圖塊/文字標記，而非原始的離散輸入形式。

`MoE`架構的獨特價值主要體現在其創新的計算資源配置策略。由於在任意時刻僅呼叫部分專家叢集，實際可呼叫的模型參數規模遠超即時使用需求。

雖然`MoE`需要載入全部參數（稀疏化參數），但推理過程僅激活部分專家單元（激活參數），顯著降低實際計算開銷。

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fe1fd47bb-9ced-42e4-8f6c-536f7a65fbf7_1376x1252.png)

簡而言之，儘管需要將完整模型（包含所有專家單元）載入至裝置（稀疏化參數），但實際推理過程僅需呼叫部分參數子集（激活參數）。 混合專家模型需要更多顯存來載入全部專家叢集，但在推理過程中運算效率更高。

我們以`Mixtral 8x7B`模型為例，具體解析稀疏參數與激活參數的量化對比。[9](https://newsletter.maartengrootendorst.com/p/a-visual-guide-to-mixture-of-experts#footnote-9-148217245)

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fcc3d48d5-8afc-4477-af98-5817b1a145ae_1376x988.png)

此處可見每個專家單元的參數規模為**5.6B**而非`7B`（儘管包含`8`個專家單元）。

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F1dfd20b4-d3b7-433b-8072-2e67fc70afaa_1376x544.png)

模型需要 _載入_ **8×5.6B（46.7B）**參數（含全部共享參數），但實際推理每 token 僅激活約 **12.9B** 參數（Mixtral 論文口徑：含注意力等每層共享部分，並非「2 個專家 FFN」的 2×5.6B = 11.2B）。

當前幾乎所有主流模型家族都包含至少一個 MoE 變體——這項技術已成為行業標準配置。

想繼續深入研究，以下資源值得參考：

* [這篇](https://arxiv.org/pdf/2209.01667) 與[這篇](https://arxiv.org/pdf/2407.06204) 論文詳盡闡述了混合專家系統領域的最新突破。

* 關於[專家選擇路由機制](https://arxiv.org/pdf/2202.09368) 的研究論文已在學術界引起廣泛討論。

* [這篇優質部落格](https://cameronrwolfe.substack.com/p/conditional-computation-the-birth) 深入剖析了多篇關鍵論文及其研究成果。

* 同類[技術解析部落格](https://brunomaga.github.io/Mixture-of-Experts) 則完整呈現了混合專家系統的演進歷程。
