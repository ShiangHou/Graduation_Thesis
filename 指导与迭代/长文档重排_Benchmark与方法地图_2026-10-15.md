# 长文档重排：Benchmark 与方法地图

检索日期：2026-10-15。范围：query + 候选长文档正文 → 文档相关性排序。不是单篇问答，也不是仅因候选数量多而形成的长输入。当前为开题调研，未运行复现实验，未确认创新点。阅读深度以任务定义、方法、相关实验和局限为主。

## Benchmark

| 数据集 | 用途与对象 | 使用边界 |
|---|---|---|
| MS MARCO Document / TREC DL Document | 英文网页文档排序；主效果验证。2019 官方即区分全库检索和 Top-100 重排 | 必须选择 document 版本；不同年份及 v1/v2 不能混用；文档长不等于必须读完整文档才能回答 |
| Robust04 / GOV2 | 新闻与政府网页文档；可研究分散证据聚合 | 经典长文档排序集合，不代表现代超长上下文；具体长度、许可和候选协议需单独核查 |
| MLDR，优先 zh/en | 13 语言长文档检索，可固定候选转为重排 | 问题由段落生成，文章作为正例；非自然搜索日志，非穷尽分级相关性标注。中文测试 800 query、语料 20 万篇 |
| MS MARCO FarRelevant | 位置诊断：相关片段从第 512 token 后开始 | 合成数据；连贯性及训练分布有局限；不能单独作为实际效果证据 |
| LongEmbed | 四个真实任务改造的检索子集及 Needle/Passkey 两个合成任务 | 原本评价 embedding 检索；用于重排需声明候选构造；不是生成答案的原始 QA 任务 |
| LoCoV1 | 12 项长上下文检索任务，补充泛化 | LongEmbed 对部分子集报告前部证据偏置；长文档高分未必证明长上下文能力 |

来源：[TREC 官方任务](https://github.com/microsoft/msmarco/blob/master/TREC-Deep-Learning-2019.md)、[NIST 数据](https://trec.nist.gov/data/deep2019.html)、[MLDR 数据卡](https://huggingface.co/datasets/Shitao/MLDR)、[FarRelevant 论文](https://arxiv.org/html/2207.01262)、[LongEmbed](https://arxiv.org/html/2404.12096)、[LoCo](https://arxiv.org/abs/2402.07440)、[PARADE](https://arxiv.org/abs/2008.09093)。

主效果可报告 nDCG@10，按相关性标注与任务补充 MRR/MAP；上游候选召回用于说明重排上限。不能只报告删除未召回正例后的结果而不说明条件化筛选。位置研究需补充位置分组或控制扰动，普通 benchmark 的总分不能自动归因于位置偏置。

## 已有问题与代表方法

| 已有问题 | 代表方法 | 方法要点 | 需要区分的边界 |
|---|---|---|---|
| 截断丢失后部证据 | FirstP 对照；MaxP；PARADE | 分段评分取最大值；或聚合各段与查询交互后的表示 | MaxP 是单块强信号假设，PARADE 可融合多个片段；并非所有任务复杂聚合都更好 |
| 全文包含大量无关内容 | KeyB；EviRerank | 先选 query 相关块，再构造紧凑输入供强模型评分 | 选择错误会限制下游可见证据，这是机制推论，不等于已证实的新研究空白 |
| 固定选块数量不能适应证据密度 | EviRerank | 根据局部分数动态停止，并加入全局摘要线索 | 已覆盖“自适应预算 + 全局补充”；不能简单复用作创新 |
| 证据位置偏置及去偏的性能权衡 | Positional Bias in Long-Document Ranking | FarRelevant 诊断、去偏训练、不同聚合架构比较 | 训练退化结果主要来自传统模型；不能直接外推所有 LLM |
| 通用摘要目标与排序目标不一致 | SumRank | 教师摘要 SFT，再用排序奖励进行 GRPO 对齐 | 已覆盖“摘要后重排”和“用排序指标训练摘要器”；不能只换底座 |
| 长输入推理昂贵，过早压缩损伤匹配 | LTC | 在 Transformer 中间层做 token 池化压缩 | 包括 passage/document 和 listwise 扩展，需拆开看结论 |

文献：

- [PARADE](https://arxiv.org/abs/2008.09093)：片段表示聚合；其结果区分分散信息需求与单段即可满足的需求。
- [KeyB](https://arxiv.org/abs/2111.09852)：文档内部块预排序和选择，早于现代 LLM 重排。
- [EviRerank v7](https://arxiv.org/html/2411.06254v7)：2026-10-14 版本；同一 arXiv 编号早期检索结果题为 KeyB2，不能当作两项完全独立工作。局部选择器、动态证据预算、抽取式全局提示，接入 pointwise/listwise 重排；在 DL19/22/23 document 与 MLDR-zh 上评估。
- [Positional Bias in Long-Document Ranking](https://arxiv.org/html/2207.01262)：重点看 §3.3、表2、§5；支持位置问题存在及去偏收益不一致，合成诊断不等价于真实全文。
- [SumRank v2](https://arxiv.org/html/2603.24204v2)：2026-09-10 预印本；训练面向 query 的摘要器，目标与最终列表排序对齐。其 TREC/BEIR 报告需继续核对具体数据配置，不能仅因标题称长文档就把所有实验视作超长文本验证。
- [LTC](https://arxiv.org/html/2605.20683)：SIGIR 2026；中间层压缩，研究效率及短文本训练向文档排序的迁移。
- [Compress-then-Rank](https://ojs.aaai.org/index.php/AAAI/article/view/40811)：AAAI 2026，压缩表示的列表重排近邻；本轮仅初筛，不据此下细节结论。

## 对开题的影响

当前不能仅以“长文档有噪声，所以选关键片段”“长文档太长，所以生成摘要”“固定长度不好，所以自适应选择”为创新点，均有直接近邻。

建议继续阅读的问题假设（不是已经证明的空白）：局部高相关块选择能否保留分散但互补的证据？抽取/摘要压缩是否遗漏否定、条件或例外而改变相关性判断？现有 LLM 去偏是否确有原分布性能退化？三者应分别查证，最后只选一项。

优先组合：TREC DL Document / MLDR 验证真实排序；FarRelevant 验证位置敏感性；如果选分散证据问题，再加 Robust04 或合适的 LongEmbed 子集。不要为堆数量同时采用所有 benchmark。
