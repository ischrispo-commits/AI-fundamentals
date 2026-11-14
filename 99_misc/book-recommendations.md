# 從晶片到 Agent：AI 基礎設施的閱讀地圖 ——「AI 原力注入」好書推薦合集

> **元信息**：整理於 2026-08 | 素材來自公眾號「AI 原力注入」好書推薦專輯（2023-11 至今 49 篇）| 章節體系對應 [AI Fundamentals](https://github.com/ForceInjection/AI-fundamentals) 知識倉庫

## 引子：為什麼需要一份「按層組織」的書單

AI 基礎設施是一條從矽片到智能體的長鏈路：GPU 晶片設計、PCIe/NVLink 互連、叢集網路與運維、雲原生排程、CUDA 程式設計、大模型訓練、推理引擎、Agent 工程、RAG 檢索……任何一個環節的知識缺口，都會在真正的生產實踐中暴露。

過去兩年多，我們公眾號陸續推薦了四十餘本好書，覆蓋了這條鏈路上的絕大多數環節。但單篇推薦解決的是「某本書值不值得讀」，解決不了「按什麼順序讀」。這篇合集把推薦過的書重新按**技術棧層級**組織成一張閱讀地圖——每一層推薦的書，就是進入該層的第一塊敲門磚。章節順序與 [AI Fundamentals](https://github.com/ForceInjection/AI-fundamentals) 倉庫目錄一一對應（硬件 → 互連 → 叢集 → 云原生 → 程式設計 → 應用 → 理論 → 訓練 → 推理 → 智能體 → 檢索 → 學習路徑 → 新范式），從底層到上層遞進；不按線性閱讀的讀者可直接跳到文末的「閱讀路徑建議」按目標裁剪。

選書標準有三條：**中文優先**（無中文版的經典單獨註明）；**理論與實戰搭配**（每一層至少保留一本「原理書」和一本「動手書」，書目不足的層以開源資源補位）；**經典與新書並重**（基礎層用時間檢驗過的經典，前沿層用 2025-2026 年的新書）。

---

## 一、硬體架構與互連技術

算力從哪來？答案是芯片。這一層決定的是「天花板」：SM 結構、Tensor Core、HBM 頻寬、PCIe/NVLink 拓撲，直接決定上層軟體能榨出多少效能。該層中文新書稀缺，推薦一本經受住時間檢驗的經典。

**《計算機體系結構：量化研究方法》（Hennessy & Patterson，機械工業出版社）**〔深度〕——計算機體系結構領域的經典之作，沉澱的量化分析方法論至今仍是評估任何新硬體（GPU、NPU、CXL 裝置）的思維框架。適合想真正讀懂硬體規格表、而不只是背參數的系統工程師。

> 該層技術迭代極快（NVLink 一年一代、CXL 3.0 Fabric），紙質書跟不上硬體節奏，體系化課程見第十二章 ZOMI 醬 AISystem，2026 年視角可配合 AI Fundamentals 倉庫的[硬體架構章節](https://github.com/ForceInjection/AI-fundamentals)。

## 二、AI 叢集運維與高效能通訊

單卡算力再高，跑大模型也要組網。這一層解決的是「機器買回來之後怎麼穩住」：GPU 狀態監控、網路健康、效能觀測。中文世界該層好書同樣稀少，以下三本分別從網路核心、系統效能和邊緣部署三個側面補位。

**《深入理解 Linux 網路》（張彥飛，電子工業出版社）**〔進階〕——從「網路包如何被接收和傳送、阻塞在內部如何發生、epoll 的底層工作原理、TCP 連線底層如何支援」等開發運維高頻問題切入，逐層拆解網路底層實現，帶讀者「修煉底層內功」、看清問題核心與背後的技術本質；全書是連線建立與收發包流程的概覽總結，貼近實戰。〔[公眾號原文](https://mp.weixin.qq.com/s?__biz=MzI0OTIzOTMzMA==&mid=2247486151&idx=1&sn=efadd6984666d7b5dbe17f849dda12a1&chksm=e995c88adee2419c41d5ddac4b88b65d88285cf04c7ecdcd1ca4698ef9aff343275eb69ada41)〕

**《BPF 之巔：洞悉 Linux 系統和應用效能》（Brendan Gregg，電子工業出版社）**〔深度〕——繼《效能之巔》之后，本書為讀者「開啟 Linux 核心大門」：從 BPF 起源到未來方向，完整覆蓋程式設計模型與 BCC、bpftrace 兩大前端框架；另一主線是系統與應用效能調優，講清 BPF 工具如何與 Linux 傳統效能工具互補，工具小巧精致、原始碼易讀，為核心開發之旅鋪平道路。〔[公眾號原文](https://mp.weixin.qq.com/s?__biz=MzI0OTIzOTMzMA==&mid=2247485127&idx=1&sn=1d9a0604ecd0d01c43b9d2235335dea7&chksm=e995c48adee24d9c8401e310b408bde8e09b8f1e373b51ac75d7d17c269ea6e41721b06985a)〕

**《邊緣雲部署與運營：系統性實現方法》（Larry Peterson 等，機械工業出版社）**〔進階〕——博主本人參與翻譯的引進書。a16z 合夥人 Martin Casado 在序言中點破「反云」趨勢：應用先遷上雲、如今又分散部署，大公司把工作負載遷回自有的最佳化基礎設施；正文以邊緣雲平台 Aether 為例，從架構設計到各子系統構建與運維細緻拆解，補齊被深埋進三大雲廠商的底層認知。〔[公眾號原文](https://mp.weixin.qq.com/s?__biz=MzI0OTIzOTMzMA==&mid=2247486092&idx=1&sn=4eb2aee4e90c5daa4c10fbd1793ff1ce&chksm=e995c8c1dee241d7165f71a8e43f7cd027b5046424a5c5075ff5ba16ff349e74c978e70f551f)〕

## 三、云原生 AI 基礎設施

AI 叢集跑在 Kubernetes 之上。這一層解決「算力資源怎麼編排」：容器、排程、儲存、資料庫。分散式系統的底層規律，是這一層所有工具的設計根源。

**《資料密集型應用系統設計》（Martin Kleppmann，中國電力出版社）**〔深度〕——全書分「資料系統基礎—分散式資料—衍生資料」三部分：從可靠性、儲存與檢索，到複製、分割槽、事務、一致性與共識，再到批處理與流處理，從宏觀層面講清各項技術的共性與差異、把底層原理拆解透徹——理解了原理，也就明白每項技術的誕生背景、要解決的問題與適用場景。〔[公眾號原文](https://mp.weixin.qq.com/s?__biz=MzI0OTIzOTMzMA==&mid=2247488960&idx=1&sn=92d650291882be60825766f75e3bc264&chksm=e995d78ddee25e9b06ff3fcc3990f6ea231b81019f514add32a978f5b53cf5aaa98a1032ddd9)〕

**《分散式系統應用設計（第二版）》（Brendan Burns，中國電力出版社）**〔入門〕——Kubernetes 共同創始人 Brendan Burns 的可複用設計模式手冊：單機層面講邊車、大使、介面卡模式（Istio 即邊車模式的典型應用），叢集層面覆蓋負載均衡、分片、分散聚集、FaaS 與所有權選舉；並以「演算法程式設計—物件導向—容器編排」三階段視角串起設計模式發展史。〔[公眾號原文](https://mp.weixin.qq.com/s?__biz=MzI0OTIzOTMzMA==&mid=2247488705&idx=1&sn=d832c8feb6b87a31f7e76089fbaf9f9e&chksm=e995d68cdee25f9a522bc2d367ad147b12e3edd70959618625dc6634a2ce28decb8fef728691)〕

**《自己動手寫 Docker》**〔進階〕——用 Golang 從零實現一個精簡容器執行時：從 run 命令起步，逐步打通 Namespace 隔離、cgroups 資源限制、rootfs 與 OverlayFS 映象分層、資料卷與 Bridge 容器網路，每步配教程與對應 GitHub 分支程式碼；原書第一版年代久遠，可結合作者部落格的新版教程學習〔[公眾號原文](https://mp.weixin.qq.com/s?__biz=MzI0OTIzOTMzMA==&mid=2247486086&idx=1&sn=f845a71f806d772568e7a262cbac69bd&chksm=e995c8cbdee241ddd755e5018560566b11a3b25120f67ea99e282d59078330942c8572c27cbe)〕。

**《雲原生資料庫：原理與實踐》（李飛飛、周烜等，電子工業出版社）**〔進階〕——阿里雲資料庫團隊撰寫（第一作者李飛飛），以 PolarDB 工程落地貫穿：從 B+ 樹、LSM-Tree 到 X-Engine 的儲存引擎演進，計算儲存分離與 Raft/Parallel Raft 高可用，再到 PolarDB-X 分散式事務與 HTAP 實踐，是一本「值得放在手邊常讀常新」的雲原生資料庫工具書。〔[公眾號原文](https://mp.weixin.qq.com/s?__biz=MzI0OTIzOTMzMA==&mid=2247489770&idx=1&sn=1e9b1f1d10907de0d5c0a0d25e902572&chksm=e995daa7dee253b14feec9ddc0280e5660de1060bbaf1bf317c5bd7499ed564224137c347ecc)〕

## 四、底層計算與異構程式設計

再往下一層是「親手寫算子」：CUDA 執行緒模型、共享記憶體、Tensor Core。這一層決定工程師能否真正榨乾 GPU。中文實戰書稀缺，從經典中選兩本互補的入門路徑。

**《CUDA C 程式設計權威指南》（John Cheng（程潤偉）、Max Grossman、Ty McKercher，機械工業出版社）**〔入門〕——英文原書 *Professional CUDA C Programming*，NVIDIA 工程師團隊撰寫的經典入門，執行緒/塊/網格模型、記憶體最佳化、原子操作循序漸進，配套程式碼可直接編譯執行，是 CUDA 從零到一的標準路徑。

**《大規模並行處理器程式設計（原書第 4 版）》（Kirk & Hwu，機械工業出版社）**〔進階〕——美國大學 GPU 程式設計標準教材（PMPP），從並行思維而非語法出發講 GPU 程式設計。第 4 版中譯 2025 年上市（第 3 版僅有英文影印版），按「中文優先」原則推薦中譯本；英文無障礙的讀者亦可直接讀原版。

> 動手環節可配合 AI Fundamentals 倉庫的 [CUDA-Learn-Notes](https://github.com/xlite-dev/CUDA-Learn-Notes)（200+ 個最佳化核心示例）與 [nano-vllm](https://github.com/ForceInjection/nano-vllm)（約 1400 行實現核心推理機制的迷你 vLLM）鞏固。

## 五、大語言模型應用開發與編排

從「會調 API」到「能交付應用」的中間地帶：提示工程、AI 程式設計工具、應用框架選型。這一層入門門檻最低、市面書最多，也是最容易踩「營銷書」坑的領域——以下兩本均經過公眾號實測推薦。

**《動手構建大模型》（Louis-François Bouchard & Louie Peters，人民郵電出版社）**〔入門〕——面向生產環境的端到端實踐指南，目標明確：幫開發者跨過 Demo 階段走向生產級系統。約 330 頁覆蓋 Prompting、RAG、微調、智能體、部署與評估全鏈路，配套 Colab 開箱即練，被一線工程師視作「反覆翻、隨手查」的實踐手冊；LlamaIndex CEO 稱其為「迄今構建 LLM 應用最全面的教材之一」。〔[公眾號原文](https://mp.weixin.qq.com/s?__biz=MzI0OTIzOTMzMA==&mid=2247491484&idx=1&sn=39d905c8b5b4c5f7e6a7d33ee985609e&chksm=e995ddd1dee254c7050b3ffab0b9f66ef032d6fc88b697024a90ca4b919ff24bfdc9f6391be4)〕

**《Cursor 與 MCP 快速入門：零基礎開發智能體應用》（黃桂釗，人民郵電出版社）**〔入門〕——30 多個親手實踐的案例貫穿全書，核心公式「一個清晰的創意 + 精准的需求描述 = 智能體生成可執行的應用」：從親子游戲、教學場景到招牌設計、小紅書文案等商業變現，再到 Sealos 云端部署全流程；並手把手講透 MCP 架構、自定義 Server 開發與阿里雲百鍊智能體整合。〔[公眾號原文](https://mp.weixin.qq.com/s?__biz=MzI0OTIzOTMzMA==&mid=2247490746&idx=1&sn=4eeca1838aad0cd4a8b7a87c19052331&chksm=e995def7dee257e133d0cd9d9471a0995319a66a5d54cc2f131f1c7b7ac1ea4d33ce1348df32)〕

## 六、機器學習基礎

AI 的基礎學科。這一層不直接產出功能，但決定工程師對模型行為的直覺：損失函式為什麼這樣設計、正則化在解決什麼、生成模型與判別模型的本質區別。

**《深度學習：基礎與概念》（Christopher Bishop，人民郵電出版社）**〔進階〕——大模型時代還需要啃深度學習教科書嗎？作者的答案是「理解本質，才能創造未來」。全書以機率論為基石，從單層網路講到 Transformer、擴散模型等前沿架構，辛頓、楊立昆、本吉奧三巨頭聯袂推薦，並提供與《模式識別與機器學習》銜接的閱讀建議。〔[公眾號原文](https://mp.weixin.qq.com/s?__biz=MzI0OTIzOTMzMA==&mid=2247489954&idx=1&sn=b270b5afddb8a59b3d68bd50a0046f9a&chksm=e995dbefdee252f915ecb4541fe402fa57c44d4d28654d35679b14f7f48425794047994447)〕

**《深度學習的數學工程：模型背後的數學原理》（Benoit Liquet 等，王斌譯，人民郵電出版社）**〔進階〕——源自澳洲名校暑期學校課程、美亞評分 5.0 的硬核著作：既非調包手冊也非純理論，以「工程視角」拆解深度學習背後的數學邏輯，從微積分、線性代數、機率論逐步構建到 Transformer 與圖神經網路，本科一年級數學基礎即可入門，小米 AI 實驗室主任王斌翻譯。〔[公眾號原文](https://mp.weixin.qq.com/s?__biz=MzI0OTIzOTMzMA==&mid=2247492552&idx=1&sn=c57ef7ad02c225ad90e2b3dd33dd7b84&chksm=e9962185dee1a893ea04f8daf6b1036aa9dd74be89b58f516f0130d5a4cf836085cde9faa3c2)〕

**《大模型技術 30 講》（Sebastian Raschka，葉文滔譯，人民郵電出版社）**〔入門〕——《Machine Learning Q and AI》的中譯本：30 個高頻問答覆蓋神經網路與深度學習、計算機視覺、NLP、生產與部署、預測效能與模型評測五個主題，180 餘頁短小精悍，適合查漏補缺的「問答詞典」。

**《統計學習方法》（李航，清華大學出版社）**〔進階〕——國內最經典的機器學習教材，感知機、SVM、HMM、CRF 的數學推導清晰嚴謹，是「知其所以然」的標準答案書。

**《機器學習》（周志華，清華大學出版社）**〔入門〕——「西瓜書」，用西瓜資料集講透機器學習全譜系，兼顧廣度與深度，適合與《統計學習方法》配合互為補充。

**《深度學習入門 5：生成模型》（齋藤康毅，人民郵電出版社）**〔入門〕——「魚書」系列第五部：前四部豆瓣評分均 9.0+、中文版狂賣 19 萬冊。全書以連貫故事分 10 步從正態分佈、EM 演算法講到 VAE 與擴散模型，用男女身高差解釋雙峰分佈、用猜謎遊戲類比 EM 算法，最後手把手實現簡化版 Stable Diffusion。〔[公眾號原文](https://mp.weixin.qq.com/s?__biz=MzI0OTIzOTMzMA==&mid=2247490193&idx=1&sn=60878aa47b9624e9b5d32e0537020b86&chksm=e995d8dcdee251cad3b905d26d767db4a1252ec8ff0c5fc58bf52cfdc2bf7ff3561366c82923)〕

**《精通特徵工程》（Alice Zheng & Amanda Casari，人民郵電出版社）**〔進階〕——「資料決定了模型的上限，演算法只是無限逼近這個上限」——本書正是這句話的完整註解：數值、類別、文本、時間序列四類資料的特徵構造、轉換與選擇方法全覆蓋，配程式碼示例與金融風控、電商推薦等實戰案例，並介紹 Featuretools 等自動化特徵工程工具。〔[公眾號原文](https://mp.weixin.qq.com/s?__biz=MzI0OTIzOTMzMA==&mid=2247489464&idx=1&sn=47671131ea315e2d46859ad077ae528d&chksm=e995d5f5dee25ce3ca0003fb097604eabc8970fa5de82d727524cb1e68c6025793c9f7e50bb0)〕

## 七、大語言模型理論與基礎

理解 Transformer 為何能「湧現」出語言能力。這一層是當前書市競爭最激烈的賽道，從 200 頁小冊子到千頁鉅著都有，按閱讀深度排序推薦。

**《How Large Language Models Work》（Stella Biderman 等）**〔入門〕——僅 200 頁的 LLM 入門小冊子：以清晰邏輯拆解大模型核心機制，覆蓋預訓練、微調、RAG、評估、對齊與可靠性設計等關鍵議題，提供可落地的技術路徑，內容緊貼前沿，適合想系統掌握 LLM 底層原理、為論文或專案構建堅實方法論的碩博生。〔[公眾號原文](https://mp.weixin.qq.com/s?__biz=MzI0OTIzOTMzMA==&mid=2247492451&idx=1&sn=141224caacec6e06f7ec4111dce89dff&chksm=e996212edee1a838e436c1eaeec2dfc67fa902e5f9bc3ec01041f060eb00c8862049686f28e4)〕

**《大語言模型》（Terrence Sejnowski，李夢佳譯，中信出版社）**〔入門〕——四院院士、玻爾茲曼機共同發明者謝諾夫斯基新作：以「AI 反向測試人類」現象切入，提出「反向圖靈測試」與「厄里斯魔鏡」假說，追問 LLM 是否真正理解語言，並給出幻覺是創造力體現、從「我思故我在」到「我演算故我在」等洞見，是技術書之外的思想書。

**《圖解大模型：生成式 AI 原理與實戰》（Jay Alammar & Maarten Grootendorst，李博傑譯，人民郵電出版社）**〔入門〕——圖解 Transformer 原作者的作品，300+ 全綵插圖覆蓋分詞、嵌入、Transformer、RAG、微調、多模態全鏈條，隨書附贈「圖解 DeepSeek-R1」彩蛋與 155 道面試題。入門體驗最好的中文圖文書。〔[公眾號原文](https://mp.weixin.qq.com/s?__biz=MzI0OTIzOTMzMA==&mid=2247490376&idx=1&sn=084c6a98a9921461d17cb16a943ad8e7&chksm=e995d905dee250132d46570b554ba8b557483d144183b6b07a1584e9a439d050501ff4ba871)〕

**《大模型基礎》（浙江大學 ZJU-LLMs 團隊，開源書籍）**〔進階〕——開源書籍的標杆：傳統語言模型、架構演化、Prompt 工程、參數高效微調、模型編輯、RAG 六章，月度更新緊跟論文前沿，附完整 PDF 免費下載。學生黨友好。

**《百面大模型》（包夢蛟、劉如日、朱儁達，人民郵電出版社）**〔進階〕——面向大模型求職熱點的實戰工具書：以「面試題 × 技術點 × 專案實戰」三位一體結構組織 100 道核心面試題，覆蓋預訓練、對齊（PPO/DPO）、RAG、智能體與推理加速等求職五大模組，每章配程式碼實戰與工程圖解。不是「背題集」，而是從「知道」到「能做」的成長路徑。〔[公眾號原文](https://mp.weixin.qq.com/s?__biz=MzI0OTIzOTMzMA==&mid=2247489907&idx=1&sn=7209048dad89e2fb90865ed778f111a8&chksm=e995db3edee25228d3b9233e7935f601622ac47e4d8a1008e80b19303f22e6da3969d586f307)〕

## 八、大模型訓練

把模型從隨機權重訓練到可用，是算力、資料、並行策略的三角工程。這一層書籍最少、門檻最高，兩本足以構建完整認知。

**《從零構建大模型》（Sebastian Raschka，人民郵電出版社）**〔進階〕——從零手寫一個 GPT 風格模型，填補「資料或過於抽象、或高度依賴框架封裝」的空白：從文字預處理、詞嵌入、注意力機制講到 Transformer 與 GPT 架構，完整走通預訓練、指令微調與部署，程式碼全部開源（含中文註釋版），自注意力實現僅 50 行，小資料集在個人電腦即可跑通。〔[公眾號原文](https://mp.weixin.qq.com/s?__biz=MzI0OTIzOTMzMA==&mid=2247489728&idx=1&sn=a62683e9c1d7b4f45c40128b15167edb&chksm=e995da8ddee2539b7d52a99491fc2b225fefdcdff987eaf54c9ba7149517aea21cd2ac277ea1)〕

**《大規模語言模型：從理論到實踐（第二版）》（張奇、桂韜、鄭銳、黃萱菁，電子工業出版社）**〔深度〕——復旦大學四位作者的系統性著作：第二版新增 50% 以上全新內容，涵蓋 MOE、多模態、智能體、RAG、效率最佳化、評估與應用開發等熱門方向，構建「理論基礎 → 資料處理 → 模型訓練 → 應用部署」的完整技術閉環，官方主頁提供免費預覽版電子書。〔[公眾號原文](https://mp.weixin.qq.com/s?__biz=MzI0OTIzOTMzMA==&mid=2247489809&idx=1&sn=799e43b526c75d90ed9297d910395b14&chksm=e995db5cdee2524af696f4414017d64e1f12c784fb71039a3bd582a87cd67146815e94292c8f)〕

## 九、大模型推理

推理是 AI 基礎設施的「最后一公里」：KV Cache、批處理、投機解碼、PD 分離，直接決定每 token 成本。中文專著極少，這本 2026 年新書是稀缺的實戰型補充。

**《vLLM 與 SGLang：大模型高效推理雙引擎實戰》（李明飛，電子工業出版社）**〔進階〕——對比兩大推理引擎：vLLM 走「通用極致效能」路線，SGLang 走「場景深度最佳化」路線，拆透 PagedAttention 與 RadixAttention 的快取哲學；7 個生產級專案覆蓋 90% 以上落地需求，附三維度選型決策矩陣。〔[公眾號原文](https://mp.weixin.qq.com/s?__biz=MzI0OTIzOTMzMA==&mid=2247492750&idx=1&sn=0dc47c03f65609d03fdd8b15cd10dad9&chksm=e99626c3dee1afd5138aa3d3d9676e2a32edd3dbc7d6f39d66b4d28ad6d6308b4d9e4773f641)〕

> 原理層面可配合 AI Fundamentals 倉庫的 KV Cache 技術體系、vLLM 模組分析等文章做原始碼級補充。

## 十、企業級 AI Agent 開發

從「模型」到「員工」：工具呼叫、記憶、規劃、多智能體協作。2025-2026 年中文 Agent 書集中爆發，按「工程深度」分層推薦。

**《Agent Skills 開發實戰：像搭積木一樣構建智能體》（代晶，人民郵電出版社）**〔進階〕——從 OpenClaw 登頂 GitHub Star 榜首講起：針對單體提示詞的痛點，拆解 Skills 檔案系統與漸進式披露機制，釐清 Skills（該怎麼做）與 MCP（能做什麼）的分工；電商經營報表、醫療病歷清洗兩個企業級案例貫穿始終。〔[公眾號原文](https://mp.weixin.qq.com/s?__biz=MzI0OTIzOTMzMA==&mid=2247492729&idx=1&sn=0c766381aec1dff4e9686e80231fcac1&chksm=e9962634dee1af22a679fc7829f4832a5cb1dfeda4d5e2561cef136e371c53ff37f439c6a8b2)〕

**《動手學大模型智能體》（溫睦寧、林江浩、張偉楠、俞勇，人民郵電出版社）**〔進階〕——上海交大團隊的 15 章教學實踐課程，分基礎（提示、評估）、架構（記憶、RAG、工具、規劃）、微調（指令微調、LoRA、強化微調）、前沿（多模態、多智能體、安全、協議）四篇，理論與示例程式碼並重，配套課件與線上課程，亦適合作高校輔助教材。〔[公眾號原文](https://mp.weixin.qq.com/s?__biz=MzI0OTIzOTMzMA==&mid=2247491444&idx=1&sn=25c4b9309d943b11993eaeec03467c37&chksm=e995dd39dee2542fd2a9871560b0bd033425a236f0f5db5f3501978349c1ea41efa03b58053c)〕

**《Agent 設計模式：圖解可複用智能體架構》（黃佳，人民郵電出版社）**〔深度〕——從 GoF 23 種經典設計模式到「概率性智能」時代的遷移：六大主軸（感知、記憶、推理、行動、反思、協作）× 21 個核心模式，並以 OpenClaw 架構實證；後記「熵的園丁」之喻道出真諦——工程師是培育可演化的生態，而非構建精密機器。〔[公眾號原文](https://mp.weixin.qq.com/s?__biz=MzI0OTIzOTMzMA==&mid=2247492016&idx=1&sn=e14d972a0f44fab98ee82f124325b88f&chksm=e99623fddee1aaeb2549a67f0ba7b16ec16e049fec4358e163fadf7e785d79a4c0f141c826c0)〕

**《AI 工程》（Chip Huyen，寶玉譯，人民郵電出版社·圖靈）**〔進階〕——O'Reilly 閱讀量最高的 AI 工程書；作者 Chip Huyen 曾任 NVIDIA NeMo 核心開發者，堅持「工具會很快過時，但基礎原理應該持續更長時間」，不堆程式碼、原理優先，覆蓋評估、幻覺、RAG、Agent 與成本安全。〔[公眾號原文](https://mp.weixin.qq.com/s?__biz=MzI0OTIzOTMzMA==&mid=2247491620&idx=1&sn=972420de7d680cc3c4604264a3e1e843&chksm=e9962269dee1ab7f57dacadb8c9358d8b3e2d0cb9c6c4837f6c9387d519cd7c44bde0e68a9b5)〕

**《MCP 開發從入門到實戰》（楊威理，人民郵電出版社）**〔入門〕——MCP 少有的中文系統教程，把 MCP 比作「AI 應用領域的 USB-C 接口」：從協議架構與核心元件，到 Claude 桌面應用配置、天氣預報伺服器開發與 Inspector 除錯，再到 Smithery 等生態實踐，8 章循序漸進。〔[公眾號原文](https://mp.weixin.qq.com/s?__biz=MzI0OTIzOTMzMA==&mid=2247490328&idx=1&sn=952d9f89ea833f4da554530f0ac25418&chksm=e995d955dee25043a88a355aed821e2828591e145b9050788c6cc9b141aa2715a80a8f895dba)〕

**《生成式 AI 開發揭秘：大模型詳解》（田雪松，機械工業出版社）**〔進階〕——全棧技術指南：「白話原理 + 程式碼復現」拆解 Transformer 與擴散模型，覆蓋 NLP、語音、視覺全模態、Agent、RAG；工程化最硬核——Scaling Laws 算力估算、消費級顯示卡 LoRA 微調、量化蒸餾、RLHF 評測。〔[公眾號原文](https://mp.weixin.qq.com/s?__biz=MzI0OTIzOTMzMA==&mid=2247491283&idx=1&sn=f2c25087edef5f0c2abe5b32532b38f3&chksm=e995dc9edee255888667600bb7c5249093222b04990138f47d34141065c66d768b2ad8ebdf33)〕

**《Generative AI in Action》（Amit Bahree，Manning）**〔進階〕——微軟首席專案經理 Amit Bahree 撰寫，美亞評分 4.6：三部分 13 章，從認知、提示工程/RAG/微調技術到架構、成本與負責任 AI 治理，以「智慧市場研報生成助手」案例貫穿全程，配套 GitHub 程式碼倉庫可執行。〔[公眾號原文](https://mp.weixin.qq.com/s?__biz=MzI0OTIzOTMzMA==&mid=2247491289&idx=1&sn=1340dc9f385bee1b42924e9789bb7a83&chksm=e995dc94dee2558247b5fcafc444603aedca361293ab68e267eb1b2aa8ea56a9701b8240ea5a)〕

**《這就是 OpenClaw：半小時玩轉小龍蝦》（劉江，人民郵電出版社）**〔入門〕——作者劉江是「大模型」術語定名人、智源研究院創始副院長；用 9 個案例（智能體 Felix 月入近 20 萬美元）講透「AI 從認知工具轉向執行主體」，以「喂糧食」「出門遛蝦」式類比降低門檻，30 分鐘零程式設計基礎即可上手，專章給出安全配置。〔[公眾號原文](https://mp.weixin.qq.com/s?__biz=MzI0OTIzOTMzMA==&mid=2247492383&idx=2&sn=952b87461c3ba47553d2865a2cb298a6&chksm=e9962152dee1a8440fddfafd2a595cdaaf34921f9a23ad7cd66c8308d30bbd7e4b60f74b20f2)〕

> 工具與協議層可配合 AI Fundamentals 倉庫的 MCP 深度解析、上下文工程、記憶系統架構等文章。

## 十一、檢索增強生成與文件智慧

RAG 解決「知識不進權重」的問題：讓模型在回答時引用外部知識庫。這一層從 2024 年起成為企業應用的主力形態。

**《大模型應用開發：RAG 實戰課》（黃佳，人民郵電出版社）**〔進階〕——從 0 到 1 構建可落地 RAG 系統的實戰指南：從資料分塊、向量檢索的「從零手搓」到許可權分層、溯源審計的工業級設計，覆蓋 GraphRAG、Agentic RAG、多模態 RAG 前沿范式，首創「RAG 架構決策樹」輔助技術選型。作者咖哥（黃佳）為新加坡科技研究局首席工程師，全書 132 張架構圖，獲宇樹科技創始人王興興力薦。〔[公眾號原文](https://mp.weixin.qq.com/s?__biz=MzI0OTIzOTMzMA==&mid=2247490027&idx=1&sn=8f3366e5b9d39212a7b1f2d517bc54ef&chksm=e995dba6dee252b029e3dd4902f69ab42b4e7a5b3917ee68afe65480c5e2d229490316d054f2)〕

**《大模型應用開發極簡入門：基於 GPT-4 和 ChatGPT（第 2 版）》（Olivier Caelen & Marie-Alice Blete，何文斯譯，人民郵電出版社）**〔入門〕——熱銷 2 萬冊的經典升級版：以 150 頁（第 1 版）至 300 頁（第 2 版）的精煉篇幅講透提示工程、微調、RAG 三大范式，配套新聞稿生成器、YouTube 影片摘要等 6 大場景，程式碼開源、可直接複用。第 2 版新增 RAG、智能體工作流與 DeepSeek 開發案例，由 Dify 產品經理何文斯翻譯，兼具學術嚴謹性與工業落地視角。〔[公眾號原文](https://mp.weixin.qq.com/s?__biz=MzI0OTIzOTMzMA==&mid=2247489547&idx=1&sn=408e0dc2223b5b288731ca570bf69547&chksm=e995da46dee253505bc87bbe7ae0b837de0ff07e9cc23e8515cff8a85c585f3bfa809d80be23)〕

## 十二、課程體系與學習路徑

單本書解決單點知識，體系化學習需要課程與路徑。這一層收錄體系化的免費課程資源。

**ZOMI 醬 AISystem（GitHub 開源課程）**〔進階〕——AI 系統全棧開源課程（https://github.com/chenzomi12/AISystem）：硬件基础、编译器技术、推理优化、框架设计四大模块，B 站配套影片。AI 基礎設施工程師的體系化免費教材，強烈建議通讀。

> 更多體系化資源可參考 AI Fundamentals 倉庫的[課程體系章節](https://github.com/ForceInjection/AI-fundamentals)：Trae 程式設計實戰課程、多智能體 AI 系統培訓材料、微軟 AI Agents for Beginners 課程等。

## 十三、AI Native 全棧實踐

Software 3.0：AI 程式設計助手成為「超級編譯器」，工程方法論全面重構。2026 年的關鍵詞是 Spec 驅動開發與 Harness 工程。

**《SDD 實戰：規範驅動開發之道》（黃佳，人民郵電出版社）**〔進階〕——國內較早的系統性 Spec-Driven Development 專著。針對 Vibe Coding「需求蒸发、上下文漂移、不可審查、不可復現、不可維護」五大致命問題，提出「規範先行」：工程師的核心產出是 proposal.md、design.md、tasks.md 三份規範文件，程式碼只是 AI 依據規範生成的衍生物，構成專案的「唯一真相來源」。全書以「智慧日報生成器」專案手把手演示六階段工作流。〔[公眾號原文](https://mp.weixin.qq.com/s?__biz=MzI0OTIzOTMzMA==&mid=2247492680&idx=1&sn=1925b1f9e8b1f4471a592723e3607af5&chksm=e9962605dee1af139ebcb569dbdcf0625350cff1d168bc43fe9c4a0064fe967ece91665a3966)〕

**《Codex 快速入門：Harness 工程落地》（袁從德、吳軍、陳文浩，人民郵電出版社）**〔進階〕——國內首批 Codex 系統專著。針對「AI 程式設計工具已經足夠強大，但很多團隊仍不知道怎樣穩定地用好它」的現實，講清從「AI 程式碼生成」到「AI 工程協作」的轉變，核心理念：讓 AI 看到正確的資訊，比寫出一條漂亮提示詞更重要。全書按「認知遷移→上下文工程→高頻實戰→團隊落地」四階段遞進，示例圍繞 emotional_chat 開源倉庫展開，兼顧 Cursor、Trae 等主流工具。〔[公眾號原文](https://mp.weixin.qq.com/s?__biz=MzI0OTIzOTMzMA==&mid=2247492640&idx=1&sn=638190bae25948789112a12d57193484&chksm=e996266ddee1af7bc2c5fdff42afde70ef6b424b40ecbbf3c788cabe89b4422882e0d0283e70)〕

**《軟體設計的哲學（第二版）》（John Ousterhout，人民郵電出版社）**〔進階〕——源自斯坦福 CS 190 課程的設計原則集：軟體設計的本質是對複雜性的管理，問題分解是程式設計師的首要設計任務。提出「模組應該是深的」、資訊隱藏、「透過定義來規避錯誤」、「先寫註釋」等原則與識別設計問題的危險訊號，均來自作者編寫約 25 萬行程式碼、參與建立多個作業系統的一線實踐。〔[公眾號原文](https://mp.weixin.qq.com/s?__biz=MzI0OTIzOTMzMA==&mid=2247488526&idx=2&sn=122af6bf418154afc4822372d3583171&chksm=e995d643dee25f55b0f7e053d5abb628b703bb577516c54945373bb4426bf529de77e8d9cf6c)〕

**《圖解 Skill：AI 提效實戰指南》（寶玉，人民郵電出版社）**〔入門〕——一本「用 skill 寫出來的 skill 書」：書中配圖全部由作者自己開發和迭代的 book-illustrator skill 生成，本身就是「用 skill 寫關於 skill 的書」的閉環。從 Skill 心智模型（第 1-2 章）、從零寫 Skill 全流程（第 3 章）、提示詞工程結合（第 4 章）到寫作工作流串聯（第 5 章）逐層進階，並給出漸進式披露三層的 token 預算量化標準（frontmatter 30-100 / 正文至 5,000 / 參考層無上限），是「從入門到精通」的完整路徑。〔[公眾號原文](https://mp.weixin.qq.com/s?__biz=MzI0OTIzOTMzMA==&mid=2247492518&idx=1&sn=b9bd39b8debeba878909fb8112c33070&chksm=e99621ebdee1a8fdf853da4fb1b9b0df6132550b2a8d3303c533e39c8af4a024e73f64fc907c)〕
## 選書標準的邊界說明

本合集的取捨基於三個原則，也意味著三個邊界：

1. **中文優先，經典原版註明**——絕大多數條目推薦中譯本；確無中文版的經典（如《Generative AI in Action》）才以原版形式推薦。
2. **理論書與實戰書搭配**——每一層至少一本「原理書」；純實戰書（如純工具教程）佔比刻意壓低，避免書單變成說明書堆砌。
3. **無書章節用開源資源補位**——硬件、叢集通訊等迭代極快的層級，紙質書天然滯後，以開源課程與倉庫文章替代，不硬湊書目。

## 說明

- 本合集素材來自公眾號「AI 原力注入」好書推薦專輯（[合集連結](https://mp.weixin.qq.com/mp/appmsgalbum?__biz=MzI0OTIzOTMzMA==&action=getalbum&album_id=3377874180926619650)）2023-11 至今的 49 篇文章，單本詳情可回看對應原文。
- 書目資訊（書名、作者、出版社、版本）依據公開渠道整理核實，個別條目的版本資訊以出版方為準。
- 章節體系與 [AI Fundamentals](https://github.com/ForceInjection/AI-fundamentals) 倉庫完全對應，倉庫內每章有原始碼級深度文章可作書目之外的延伸閱讀。

---

> **寫在最後**：這張地圖會隨公眾號持續更新——每當值得讀的新書出現，會按對應層級補充進去。你現在卡在哪一層？歡迎在評論區告訴我，也可以直接去 [AI Fundamentals](https://github.com/ForceInjection/AI-fundamentals) 倉庫按章節體系展開閱讀。
