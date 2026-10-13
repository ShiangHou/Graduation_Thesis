# 选题 A：文献、实验资源与开题评估

完成日期：2026-10-10。基于最新项目 `c4f6de9` 的选题继续研究；保留原有两份选题文档，本文档包给出更新后的判断。

**主入口：[论文完整研究与撰写方案](论文完整研究与撰写方案.md)。** 这份单文件方案明确了调研后的题目、问题与创新点，完整包含文献综述、方法与训练目标、数据与实验、资源预算、预期效果、七章写作提纲和进度安排。后续实施与写作优先以该文件为准。

以下为支撑主方案的专项附件：

1. [开题可行性研究报告](开题可行性研究报告.md)：结论、近邻冲突、建议改题、无人工标注方案、开题条件。
2. [文献综述与创新性矩阵](文献综述与创新性矩阵.md)：35 项文献、阅读深度、官方链接和创新边界。
3. [实验方案与论文撰写流程](实验方案与论文撰写流程.md)：实际数据拆分、基线、指标、资源估算、两周预实验和 12/24 周论文计划。

核心判断：原来的宽题与 GBFR、VeriFin 等工作重合较多；建议收窄为“面向金融数值问答的证据绑定不确定性感知选择性回答方法研究”，经过预实验再锁定。当前没有新方法性能结果。

## 已运行的核验

- 38 个主资源文件、13 个 GBFR 文件固定来源并保存 SHA-256；大文件保存在被忽略的 `.local/topic_a/`。
- FinQA 8,281 条 gold 程序全部通过官方执行器回算。
- TAT-QA 16,546 条 gold 答案通过官方 EM/F1/scale 自检。
- 统计证据字段、题型、报告／表格划分交集、FinanceReasoning 母数据来源。
- GBFR 公开文件计数、反事实类型与母题文本连接核验。
- 生成包含 19,466 个训练样本 ID 的分阶段划分清单，组之间互斥；官方 dev/test 另保留。
- 重新表达 VeriFin 公开计数的回答覆盖率与决定覆盖率。只是计数换算，未重新运行其模型。

## 复现数据审计

从项目根目录执行；无需 API key。下载需要网络，标准库脚本不执行下载文件。`cached_path` 是本机可选缓存提示：不存在时会从固定公开 URL 下载。

```bash
python3 research/topic_a/fetch_sources.py --files research/topic_a/data_sources.json
python3 research/topic_a/fetch_sources.py --files research/topic_a/gbfr_sources.json
python3 -m venv .local/audit-venv
.local/audit-venv/bin/python -m pip install numpy pandas scipy sympy tqdm
.local/audit-venv/bin/python research/topic_a/audit_resources.py
.local/audit-venv/bin/python research/topic_a/audit_gbfr.py
.local/audit-venv/bin/python research/topic_a/make_splits.py
```

本次实际使用 `.local/metrics-venv/bin/python`。运行时版本记录见 [audit_environment.json](audit_environment.json)。以上安装命令是复现说明，未来严格重现应按记录固定依赖。官方 TAT-QA 代码在 Python 3.14 报正则转义 SyntaxWarning，但本轮评测成功；未修改上游评分逻辑。

`audit_resources.py` 会导入已查看的官方 FinQA/TAT-QA 评测代码，执行 gold 自检；不执行模型生成的任意 Python，不训练模型。FinQA 的 `eval_program` 是操作白名单；TAT-QA 需要 scipy 的线性匹配函数。

## 结果与证据文件

| 文件 | 内容 |
|---|---|
| [resource_audit.json](resource_audit.json) | 主资源计数、官方自检、来源重叠、公开计数换算 |
| [gbfr_audit.json](gbfr_audit.json) | GBFR 数据实际规模及 hash、母题文本匹配 |
| [split_summary.json](split_summary.json) | 各阶段样本与 group 计数 |
| [split_manifest.json](split_manifest.json) | 具体样本 ID、group、阶段与题型；不含原文与答案 |
| [data_sources_manifest.json](data_sources_manifest.json) | 主资源固定 URL、hash、状态 |
| [gbfr_sources_manifest.json](gbfr_sources_manifest.json) | GBFR 固定 URL、hash、状态 |
| [repository_inventory.json](repository_inventory.json) | 已取得的仓库版本和文件清单 |
| [repository_refresh_attempt.json](repository_refresh_attempt.json) | 元数据 API rate limit 的原始失败记录；不是仓库不存在的证据 |

## 未执行事项

尚未下载模型权重、运行候选答案生成、训练新方法、调用付费 LLM API、验证 NVIDIA GPU 显存与吞吐、取得独立人工标注。没有绕过 gated 数据访问条款，也没有将许可 pending 的派生数据重新发布。

这份材料可用于准备开题，但算法性能、正式学校要求和导师认可仍需补齐，不能把 gold 自检数值写进论文主性能表。
