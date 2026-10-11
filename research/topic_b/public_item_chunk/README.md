# 公开金融 item＋chunk 数据构造

这些文件用于毕业论文的数据适配与审计，尚无模型实验结果。完整设计见[数据方案](../../../选题2_公开金融item与chunk_数据替代与组装方案.md)。

## 来源与许可

- **FinRank**：Sasan Mansouri、Daniel Saad、Mark Wahrenburg、Manu Weissel、Fabian Woebbeking，[论文](https://arxiv.org/abs/2608.07400)、[数据仓库](https://github.com/datanxt/FinRank)。固定提交`916dc27e77b90e294ea1b3a2cc5b0abcf07392d1`。发布许可为[CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)。本目录FinRank派生样例沿用该非商业许可、保留作者归属；改动包括中性ID、统一标题提取、来源绑定去重、BM25选池及排列。新增项标为未判断，未生成虚构金标。
- **FinQA**：Chen等，EMNLP 2021，[官方仓库及MIT许可](https://github.com/czyssrs/FinQA)。固定提交`0f16e2867befa6840783e58be38c9efb9229d742`，本轮仅下载`dataset/dev.json`。派生示例从原表格行与上下文构造item，答案和程序另存；原始财报权利与出处不因序列化改变。
- **FinDER**：[作者发布页](https://huggingface.co/datasets/Linq-AI-Research/FinDER)。本轮仅核对页面与目录元数据，未完成全量下载对齐。

原始缓存留在项目`.local/`，下载URL及SHA-256见`download_audit_20261012.json`。复建命令见[阶段成果汇总](../阶段成果汇总_20261012.md)。不执行任何下载数据中的代码。

## 文件使用边界

`examples/finrank_input_*.json`为未调用模型的原文构造输入；长文件需要先核验token预算和证据保留。`finrank_eval_only_*.json`包含标签状态与原答案，不可输入模型。`finrank_original_small_pool.json`同时带标签，仅供阅读。

新候选是否相关尚需补判；现有标签和来源也需质量审核。哈希不一致项已保留在审计记录，没有静默修复原数据。
