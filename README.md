# 计算机技术与金融硕士毕业论文

用于管理选题报告、公开资料研究、实验方案及论文写作。

## 当前材料

- [硕士论文选题报告 Word版](reports/硕士论文选题报告.docx)
- [硕士论文选题报告 可编辑文本](reports/硕士论文选题报告.md)
- [研究依据与阅读记录](research/研究依据与阅读记录.md)
- [公开资源小样本核验](research/public_resource_probe.json)

报告包含基金相关性学习、多路证据重排序及可验证理由生成三个备选题目，按2026年10月底开题、约六个月研究、仅使用公开数据设计。

## 文档与资源脚本

`scripts/build_topic_report.py` 从Markdown生成Word报告，需要python-docx。

`scripts/probe_public_resources.py` 下载三份公开样本并核验结构，需要pypdf。原始下载保存到Git忽略的`.local/public_probe/`。

仓库只保存写作材料、自建代码及公开资源核验记录；原始网页和PDF缓存、密钥和私有数据不纳入版本管理。
