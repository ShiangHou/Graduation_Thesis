"""Build an editable XMind workbook and matching reading index; standard library only.

Run from any directory. Does not download papers or run model experiments.
XMind JSON fields follow xmindltd/xmind-sdk-js src/common/model.ts and core/note.ts.
"""
from pathlib import Path
import collections
import hashlib
import html
import json
import uuid
import zipfile
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OLD = json.loads((HERE.parent / 'literature_registry_20261011.json').read_text())

# id | short title | publication/version | URL | depth | checked sections | contribution | transfer and limit
ROWS = '''
N01|How do Language Models Bind Entities in Context?|ICLR 2024；所读作者版本2310.17191v1|https://arxiv.org/html/2310.17191v1|M|§2–3、引言与局限|通过激活干预研究实体与属性的绑定ID，给出可解释的上下文绑定机制。|为公司—指标—期间串绑提供机制假设；合成任务结果不等于金融API模型的病因证明。
N02|Retrieval Head Mechanistically Explains Long-Context Factuality|ICLR 2025；所读作者版本2404.15574v1|https://arxiv.org/html/2404.15574v1|M|§2–4|识别复制上下文信息的注意力头；屏蔽检索头比随机屏蔽更损害提取任务。|可用开源小模型做辅助干预；注意力图相关性本身不足以证明因果，闭源API不能直接复现。
N03|NoLiMa: Long-Context Evaluation Beyond Literal Matching|ICML 2025；所读2502.05167v1|https://arxiv.org/html/2502.05167v1|M|§1、§3、实验分析概述|降低问题与证据的字面重合，考察长上下文关联检索；字面相似干扰会误导。|比较同关键词异期间与改写同义证据；不是金融排序基准，不能移植原分数当NDCG。
N04|The Power of Noise: Redefining Retrieval for RAG Systems|2024作者版本2401.14887v1|https://arxiv.org/html/2401.14887v1|M|随机/相关干扰实验及讨论|相关却无答案的干扰与随机噪声影响不同；部分设置加入随机文档反而有益。|必须分层控制干扰种类；反对把所有加长都解释成单调退化，不能据此建议普遍填满随机文本。
N05|Sufficient Context: A New Lens on Retrieval Augmented Generation Systems|ICLR 2025；所读2411.06037v1|https://arxiv.org/html/2411.06037v1|M|§3定义、标注与AutoRater设置|区分输入是否含足够作答信息与模型能否正确作答，设计充分性标注。|理由支持、查询相关、证据充分是三个标签；缺证据组单独测拒绝无依据断言，不能混入充分组解释长度效应。
N06|LongCite: Enabling LLMs to Generate Fine-grained Citations in Long-Context QA|Findings ACL 2025；所读2409.02897v1|https://arxiv.org/html/2409.02897v1|M|§2–3、表3|CoF自动构造句级引用SFT数据；比较带引用与不带引用的问答正确性。|联合输出可能有额外负担，但训练后可以改善；本题需实测排序与理由联合任务，不能预设一定更差。
N07|FRONT: Learning Fine-Grained Grounded Citations for Attributed Large Language Models|Findings ACL 2024|https://aclanthology.org/2024.findings-acl.838/|M|作者HTML2408.04568v1 §3、表1|先抽引用片段再生成回答的SFT，随后用一致/不一致回答做DPO。|直接近邻：证据先行加DPO已经存在；我们的差异须由金融绑定、扩容干扰及排序约束实验证明。
N08|SelfCite: Self-Supervised Alignment for Context Attribution in Large Language Models|ICML 2025|https://arxiv.org/html/2502.09604v1|M|§2、§4.1–4.6|删除/保留引用上下文构造自监督信号，用BoN与SimPO改善引用；分析长度捷径和随机扰动失效。|证据干预奖励已有；借鉴长度匹配与真实错误偏好。模型概率依赖不等于文本蕴含，更不等于金融事实真实。
N09|ContextCite: Attributing Model Generation to Context|NeurIPS 2024|https://arxiv.org/html/2409.00729v1|M|§1–3方法定义及应用概述|通过上下文消融拟合代理模型，估计哪些来源影响某条生成陈述。|用于区分贡献性归因与支持性引用；额外前向成本高，归因到错误证据仍可能是不正确理由。
N10|LongReward: Improving Long-context Large Language Models with AI Feedback|ACL 2025；所读2410.21252v1|https://arxiv.org/html/2410.21252v1|M|§3.2–4.1|分别评价帮助性、逻辑性、忠实性、完整性，构造偏好并以DPO及CE正则训练。|多维奖励已存在；可迁移局部检查和覆盖约束，原32张H800配置不能作为单卡24GB可行性证据。
N11|RHIO: Improving Contextual Faithfulness of Large Language Models via Retrieval Heads-Induced Optimization|2025作者版本2501.13573v1|https://arxiv.org/html/2501.13573v1|M|§2–6|屏蔽检索头生成模型内生错误；正负控制符联合监督，配合对比解码。|提供真实分布负例构造路线；不是DPO或GRPO，需访问内部头且额外解码有成本。
N12|RAGChecker: A Fine-grained Framework for Diagnosing Retrieval-Augmented Generation|2024作者版本2408.08067v1|https://arxiv.org/html/2408.08067v1|M|诊断指标、§4.3–4.4|拆分检索覆盖、上下文利用、相关/无关噪声敏感及无依据生成；增加上下文可同时提高覆盖与噪声。|理由来自池中另一条目应单独查归属，不能只检查全池支持；原框架是RAG诊断，不是列表重排。
N13|RefChecker: Reference-based Fine-grained Hallucination Checker and Benchmark for Large Language Models|2024作者版本2405.14486v1|https://arxiv.org/html/2405.14486v1|M|三元组检查、附录A/B错误分析|将回答拆为声明三元组，判定支持、中立或矛盾；考察核验器依赖内部知识。|迁移到带主体、期间、单位的原子声明；抽取器也可能丢限定条件，必须人工校准。
N14|The FACTS Grounding Leaderboard|2025作者版本2501.03200|https://arxiv.org/abs/2501.03200|A|摘要与评测流程说明|长文条件生成先检查是否完成请求，再判是否完全有依据，汇总多评审结果。|同时测任务完成与理由可靠，防止少输出获得虚高精度；不是金融重排金标。
N15|Towards Long Context Hallucination Detection|Findings NAACL 2025|https://aclanthology.org/2025.findings-naacl.436/|M|论文§1–4、数据统计|在BookSum上合成无依据/矛盾错误；分块编码及聚合使小编码器处理长上下文核验。|核验器也需要长文能力；生成器与核验器分开评估，书籍合成错误需做金融域校准。
N16|Making Retrieval-Augmented Language Models Robust to Irrelevant Context|ICLR 2024；所读2310.01558v1|https://arxiv.org/html/2310.01558v1|M|§2–3|使用NLI判断证据相关并构造不同检索质量的训练混合；少量参数高效微调改善抗干扰问答。|普通混合干扰SFT必须作为基线；无上下文也正确的回答不自动满足本题仅依据输入的约束。
N17|SFR-RAG: Towards Contextually Faithful LLMs|2024作者版本2409.09916v1|https://arxiv.org/html/2409.09916v1|M|§1–2训练概述|围绕相关/干扰、冲突、引用、不可回答等情况设计RAG训练与评测。|金融后训练需包含缺证据和冲突；概述不足以完整复现原训练数据，9B长文不直接适配24GB。
N18|Training Language Models to Generate Text with Citations via Fine-grained Rewards|2024作者版本2402.04315v1|https://arxiv.org/html/2402.04315v1|M|§2、§4与错误分析|将正确性、引用召回及精确度信号用于拒绝采样和PPO，比较细粒度与整体奖励。|直接排除“忠实性加覆盖reward本身全新”的表述；原输入少量文档，不研究250项排序。
N19|ReClaim: Ground Every Sentence|Findings NAACL 2025；所读2407.01796v1|https://arxiv.org/html/2407.01796v1|M|§3方法、训练设置、表3–4|交替产生引用与声明，可拆为ReferModel和ClaimModel并约束引用解码。|局部证据生成/验证是强基线；出处字符串正确不保证陈述语义支持，也没有排名任务。
N20|Hierarchical Reranking for Scalable Financial RAG System|2026预印本2607.27523v1|https://arxiv.org/html/2607.27523v1|M|§3–6、表2–3|金融任务中两阶段重排、表格规范化及长上下文切分融合；上下文管理收益较小。|金融管线近邻；64k阈值非普适，文中统计稳定措辞不能替代显著性证据，不是逐item理由评测。
N21|TAT-QA: A Question Answering Benchmark on a Hybrid of Tabular and Textual Content in Finance|ACL 2021|https://aclanthology.org/2021.acl-long.254/|A|摘要与作者数据说明|金融表格与正文混合问答，提供数值推导和尺度，TAGOP先抽取再运算。|可扩展指标/单位诊断；问答答案不能直接转为全候选相关性等级，当前不增加为必做主数据。
N22|MultiHiertt: Numerical Reasoning over Multi Hierarchical Tabular and Textual Data|ACL 2022|https://aclanthology.org/2022.acl-long.454/|A|摘要、引言与示例|多层表头、多表和长正文问答，标注支持事实及推理；漏读表头可选错数值。|补充实体/层级/期间绑定视角；表格展开必须保留层级，当前仅列扩展资源。
N23|FinRank: An Evidence-Grounded Benchmark for Financial Question Answering and Retrieval over SEC Filings|2026预印本2608.07400|https://arxiv.org/abs/2608.07400|M,D|此前论文/数据核验；本轮摘要复核|提供公开金融问题、来源限定的支持证据及跨公司/期间困难负例。|最接近主数据；原池小、逐项理由待标，扩容未判断项不能当0；已下载不等于标签无误。
N24|FinQA: A Dataset of Numerical Reasoning over Financial Data|EMNLP 2021|https://aclanthology.org/2021.emnlp-main.300/|M,D|此前论文与已下载dev字段核验|财报表格/正文、金融问题、支持证据和程序，为数值推理提供监督。|可抽实体/指标item配原文chunk做可控诊断；答案和程序仅放评测侧；不是FiQA。
N25|FinDER: Financial Dataset for Question Answering and Evaluating Retrieval-Augmented Generation|2025作者版本2504.15800|https://arxiv.org/abs/2504.15800|A,C|此前摘要、数据卡与目录元数据|提供公开金融问题、参考证据与回答，并发布报告资源。|作为扩展/替代；本地未完成Parquet与报告全量对齐，不声称现成完整长池qrels。
N26|FinDVer: Explainable Claim Verification over Long and Hybrid-Content Financial Documents|EMNLP 2024；2411.05764v1|https://arxiv.org/html/2411.05764v1|M,D|此前§5.2–5.5和JSON核验|研究金融声明核验、证据与解释；部分设置完整上下文/推理有益。|金融事实核验辅助集；不是排序金标，同报告变体必须防泄漏，解释字段并非全部完整。
N27|PHANTOM: A Benchmark for Hallucination Detection in Financial Long-Context QA|NeurIPS 2025 Datasets and Benchmarks|https://papers.nips.cc/paper_files/paper/2025/hash/b8badadce3f482ba340ff870f4894441-Abstract-Datasets_and_Benchmarks_Track.html|M|此前§3、§5数据与检测器训练|金融披露长上下文幻觉检测，控制长度和证据位置，并训练小模型检测器。|金融直接证据但目标是检测；连续文档加长不等于独立item数增加，不提供重排NDCG金标。
N28|FinLongDocQA / Document-Level Numerical Reasoning across Single and Multiple Tables in Financial Reports|2026预印本2604.03664|https://arxiv.org/abs/2604.03664|A,C|此前摘要、作者仓库说明；本轮题名核对|长财报中的证据定位与数值问答，关联来源和可执行推理。|长文档金融资源补充；未下载全量，不因包含出处就称为列表重排基准。
N29|Same Task, More Tokens: the Impact of Input Length on the Reasoning Performance of Large Language Models|ACL 2024|https://aclanthology.org/2024.acl-long.818/|M|此前输入长度控制实验|保持任务核心信息，考察输入加长下推理变化。|迁移固定证据加长实验；不能把字符数当token数，模型与任务效应须独立报告。
N30|Context Length Alone Hurts LLM Performance Despite Perfect Retrieval|Findings EMNLP 2025|https://aclanthology.org/2025.findings-emnlp.1264/|M|此前§3–5|控制正确证据获取后，研究上下文长度仍可能导致的推理退化。|补做oracle证据与原始长池组；检索成功不保证理由关系正确，结果不是所有模型必然规律。
N31|Mixing Mechanisms: How Language Models Retrieve Bound Entities In-Context|2025预印本2510.06182v1|https://arxiv.org/html/2510.06182v1|M|此前§3、附录D|用干预分析位置/词汇等实体绑定机制，固定长度考察实体数的影响。|支持N与L分离；本题先做行为干预，微观机制实验列可选，勿直接把API错理由归因于某个头。
N32|RAFT: Adapting Language Model to Domain Specific RAG|2024作者版本2403.10131v1|https://arxiv.org/html/2403.10131v1|M|此前§3、§5|相关证据与干扰混合的域内问答SFT，并利用解释/引用监督。|必须比较RAFT式普通抗干扰训练；其缺oracle仍作答设计不适合原样移植为证据不足拒断言。
N33|Large Language Models Can Be Easily Distracted by Irrelevant Context|2023作者版本2302.00093v3|https://arxiv.org/html/2302.00093v3|M|此前干扰实验与结论|在算术题中加入不改变答案的无关内容，研究性能变化与提示缓解。|提供答案保持扰动范式；不是金融、也不证明理由生成导致错误。
N34|Context-faithful Prompting for Large Language Models|Findings EMNLP 2023|https://arxiv.org/abs/2303.11315|A|本轮摘要与版本信息|意见式提示、反事实示例改善上下文忠实性，涉及知识冲突和拒答。|作为低成本提示基线；不能预设必须后训练，需检查金融真实错误是否仍存在。
N35|When Financial Fine-tuning Fails: A Three-Level Detectability Analysis of Numerical Hallucination in Domain-Adapted Language Models|2026；本综述依据arXiv版本，另检出Neurocomputing出版页|https://arxiv.org/abs/2609.04806|M|此前方法核对；本轮摘要与出版线索|在特定金融摘要微调设置观察无依据数字/定量表述增加，讨论模板注入。|后训练须测数字克制和缺证据组；小规模特定设置不能推论所有金融微调必然有害。
'''

entries = []
for line in ROWS.strip().splitlines():
    pid, title, status, url, depth, sections, method, limit = line.split('|')
    entries.append(dict(id=pid, title_and_status=title+'，'+status, short_title=title,
                        primary_url=url, reading=depth.split(','), checked_sections=sections,
                        method_and_scale=method, scope_and_limitation=limit,
                        batch='20261012整合补充', checked_at='2026-10-12'))
old_entries = [dict(e, batch='20261011沿用，未在本轮全部重读') for e in OLD['entries']]
papers = {e['id']:e for e in old_entries+entries}

# question, direction, synthesis, identifiers, concrete next experiment
GROUPS = [
('RQ1 为什么失效', '1.1 长度与证据位置', '可接受长输入≠可靠利用；区分位置效应与获取证据后的推理退化。', 'P63 P64 N29 N30 N03', '固定核心证据，控制token长度；证据置前/中/后，设置oracle证据组。'),
('RQ1 为什么失效', '1.2 独立实体数与属性绑定', '长池还增加需要区分的实体和关系，不能只以token长度解释。', 'N01 N31 N02 N11', '固定总token数改变独立实体数；追踪错误理由是否来自同池另一个item。'),
('RQ1 为什么失效', '1.3 相似干扰、知识冲突与充分性', '语义相似但不支持，比随机噪声更值得单独研究；更多上下文也可能改善覆盖。', 'N04 N05 N12 N16 N33 N34', '随机/同公司异期/同指标异主体分别扩容；充分与缺证据分别统计。'),
('RQ1 为什么失效', '1.4 金融语义中的多重约束', '金融证据需同时匹配主体、期间、指标、口径、单位与出处。', 'P29 N23 N24 N21 N22 N28', '同数值异含义、申报年≠财务期、发行主体≠被描述实体；与同模板非金融组对照。'),
('RQ1 为什么失效', '1.5 排序位置偏差与比较不一致', '输入顺序会影响排名，比较可非传递；集合稳定不等于解释可靠。', 'P10 P11 P12 P13 P14 P17 P18 P65', '同池多排列，报告排序方差与理由错误；不要把新增真相关项导致的合理变化算失稳。'),
('RQ1 为什么失效', '1.6 联合任务与后训练分布', '排序+理由同时生成的额外负担是待检验假设；引用训练也能带来收益。', 'N06 P30 P35 P38 N26 N35', '只排序、固定排名只解释、联合、先排后解释；匹配输出长度与预算。'),
('RQ2 出现什么及如何衡量', '2.1 无依据与矛盾声明', '原子声明检查；将支持、矛盾、证据不足分开。', 'P53 P54 P79 N13 N15 N27 N35', '规则校验数值/单位，独立核验器加双人抽查；报告各错误类与宏平均。'),
('RQ2 出现什么及如何衡量', '2.2 出处错配与item归属错误', '全池能找到同一句话，仍可能归错item；合法引用ID不保证支持。', 'P52 N06 N07 N12 N23 N26', '给定原子声明，只按指定item及其出处核验，再查全池定位串绑源。'),
('RQ2 出现什么及如何衡量', '2.3 支持性≠贡献性≠内部推理忠实', '外部证据支持可以评测；生成解释不自动等于模型真实决策过程。', 'P49 P50 P51 P56 P57 P71 N09 N08', '正文以证据一致性为目标；删证据或替换主体测试敏感性，避免声称证明内部CoT。'),
('RQ2 出现什么及如何衡量', '2.4 排序质量与集合/次序稳定', '必须用相关性qrels测质量，再用配对扰动测稳定；不以两次重合率代替正确性。', 'P01 P11 P17 P27 P69 N23', 'NDCG@20、Evidence Recall@20、同池Top20重合及共同项顺序一致；未判断项保留unknown。'),
('RQ2 出现什么及如何衡量', '2.5 覆盖、弃答与格式错误', '空理由、少推、重复、池外ID、截断属于不同失效，不能混成一个幻觉率。', 'P27 P55 N05 N14', '完整K、合法ID、理由覆盖和无错列表比例；拒断言正确性单列，finish_reason单列。'),
('RQ2 出现什么及如何衡量', '2.6 金融公开数据能提供什么', '优先公开披露item+chunk；QA和检测数据需改造，不能冒充现成长池排序金标。', 'N23 N24 N25 N26 N27 N28 N21 N22', 'FinRank主数据候选质量审计；FinQA绑定诊断；其他数据作为按需扩展。'),
('RQ3 如何缓解与后训练', '3.1 小组排序与候选管理', '滑窗、pairwise、setwise、树/锦标赛解决单次比较规模，但可能损失召回。', 'P01 P02 P03 P04 P05 P08 P09 P15 P27 N20', '统一首检候选与预算，记录进入Top20前的漏召回、调用与token总量。'),
('RQ3 如何缓解与后训练', '3.2 金融卡片与规则约束', '结构字段匹配、证据卡和元数据过滤是直接近邻，必须作为强基线。', 'P29 N20', '真实可抽字段与oracle字段分开；卡片保留出处回指，核查压缩是否丢表头/否定。'),
('RQ3 如何缓解与后训练', '3.3 分离排序、取证与理由生成', '先定位证据，再生成或核验理由；局部读取可减少跨item污染。', 'N07 N19 N06 P33 P34 P38 P78', '冻结同一排名比较全池解释和局部解释；再测端到端质量，防止任务更简单造成虚假增益。'),
('RQ3 如何缓解与后训练', '3.4 排序蒸馏与证据SFT', '排序蒸馏、解释监督和抗干扰SFT均已有；数据构造比换训练名更关键。', 'P06 P07 P30 P31 P32 N32 N16 N17 N06', '普通SFT、普通难负例SFT、金融绑定难负例SFT；同训练量、同底座、同格式。'),
('RQ3 如何缓解与后训练', '3.5 偏好优化与反事实证据', 'DPO/SimPO可学习正确和错误理由差异，但要防长度偏好与合成错误失真。', 'N07 N08 N09 N10 P45 P19 P47', '同输入、同排名、近等长理由偏好；实体/期间替换与自然模型错误各自消融。'),
('RQ3 如何缓解与后训练', '3.6 RL与细粒度奖励', '排序GRPO与引用PPO已有；单一NDCG奖励不覆盖理由归属，单一支持率会鼓励少说。', 'P20 P35 P36 P37 P46 P48 N18 P60 P61 P62', '先验证奖励与人工一致，再比较SFT/DPO/可选GRPO；保持排名和覆盖门槛。'),
('RQ3 如何缓解与后训练', '3.7 稳定性训练及推理聚合', '多排列聚合与顺序一致训练已有；一致可能只是稳定地错误。', 'P10 P11 P17 P19 P58', '监督真实相关性并跨扰动一致；不能要求新增更相关证据时仍保持旧排名。'),
('RQ3 如何缓解与后训练', '3.8 核验器、拒断言与机制干预', '检测器或规则可直接清除部分错误；内部检索头路线需要可访问模型。', 'P55 P79 N15 N27 N11 N02 N34', '程序回填/局部检查先做；若已解决则不强行RL，剩余语义错误才值得后训练。'),
]

aliases = {'P01':'RankGPT','P02':'PRP','P03':'Setwise','P04':'PRP-Graph','P05':'ListT5','P06':'RankZephyr','P07':'FIRST','P08':'TourRank','P09':'BracketRank','P10':'PSC','P11':'BSC','P12':'Preferential Ranking Inconsistency','P13':'CapCal','P14':'Beyond Sampling / Self-Sorting','P15':'Whole-Pool Setwise','P17':'InvariRank','P18':'Debias First','P19':'OC-SFT','P20':'TSSetRank','P27':'CompRank','P29':'FinCARDS','P30':'ExaRanker','P31':'ExaRanker Open Models','P32':'Rank1','P33':'JudgeRank','P34':'DeAR','P35':'REA-RANK','P36':'Rank-R1','P37':'ERank','P38':'Explain-then-Rank','P45':'PEX','P46':'RationaleRM','P47':'Training for Self-Explanation Faithfulness','P48':'FaithLens','P49':'ERASER','P50':'Faithfulness Tests for NLE','P51':'Walk the Talk','P52':'ALCE','P53':'FActScore','P54':'RAGTruth','P55':'Attribute or Abstain','P56':"LMs Don't Always Say What They Think",'P57':'CoT in the Wild','P58':'StableRAG','P60':'RRPO','P61':'SRPO','P62':'PA-GRPO','P63':'Lost in the Middle','P64':'RULER','P65':'Positional Bias in Long-Document Ranking','P69':'How Good Are Rerankers?','P71':'Survey of Faithful Model Explanation','P78':'Rerank Before You Reason','P79':'MiniCheck'}
for e in papers.values():
    e.setdefault('short_title', aliases.get(e['id'], e['title_and_status'].split('，')[0]))
    e['directions'] = [g[1] for g in GROUPS if e['id'] in g[3].split()]

def ident(label):
    return uuid.uuid5(uuid.NAMESPACE_URL, 'thesis-literature-20261012:'+label).hex

def node(title, children=None, note=None, url=None, key=None, collapsed=False):
    n = {'id':ident(key or title), 'class':'topic', 'title':title, 'customWidth':320}
    if children: n['children'] = {'attached':children}
    if note:
        n['notes'] = {'plain':{'content':note}, 'html':{'content':{'paragraphs':[{'spans':[{'text':note}]}]}}}
    if url: n['href'] = url
    if collapsed and children: n['branch'] = 'folded'
    return n

def paper_node(pid, branch):
    p = papers[pid]
    note = '\n'.join([p['title_and_status'], '一次来源：'+p['primary_url'],
                     '核对深度：'+','.join(p['reading']), '阅读范围：'+p.get('checked_sections', '见20261011阅读矩阵'),
                     '做了什么：'+p['method_and_scale'], '迁移与边界：'+p['scope_and_limitation'], '来源批次：'+p['batch']])
    return node(f"[{pid}] {p['short_title']}", [
        node('做了什么｜'+p['method_and_scale'], key=branch+pid+'method'),
        node('迁移与边界｜'+p['scope_and_limitation'], key=branch+pid+'limit')],
        note, p['primary_url'], key=branch+pid, collapsed=True)

def sheet(title, children, note=None):
    root = node(title, children, note, key='root'+title)
    root['structureClass'] = 'org.xmind.ui.logic.right'
    return {'id':ident('sheet'+title), 'class':'sheet', 'title':title, 'rootTopic':root}

selected = sorted({pid for g in GROUPS for pid in g[3].split()})
overview = [node(q, [node(g[1]+'｜'+g[2], key='overview'+g[1]) for g in GROUPS if g[0]==q]) for q in dict.fromkeys(g[0] for g in GROUPS)]
overview += [node('当前题目与边界', [node(t) for t in [
    '金融信息条目长候选池重排：理由证据一致性分析与后训练优化',
    '输入：公开query + item/主体/出处 + chunk；输出：TopK + 可验证理由',
    '排序质量、理由支持、条目归属、有效覆盖、成本同时评测',
    '基金业务是动机；现阶段不声称复现企业基金任务',
    '假设：相似干扰下的绑定错误；尚无本项目模型实验结论']]),
    node('如何读图', [node(f'总索引115项；三个问题导图精选{len(selected)}项，跨分支重复引用不重复计数'),
                    node('M：方法/相关实验或分析核对；A：摘要/元数据；C：作者资源说明；D：数据解析'),
                    node('论文节点展开看方法和边界；点击链接看一次来源，备注列阅读范围'),
                    node('原80项沿用，补充35项含此前金融专题成果；并非本轮通读115篇全文')])]
workbook = [sheet('00 总览与阅读说明', overview)]
for q in dict.fromkeys(g[0] for g in GROUPS):
    branches=[]
    for _, name, synthesis, ids, experiment in [g for g in GROUPS if g[0]==q]:
        branches.append(node(name, [node('方向结论｜'+synthesis, key=name+'synthesis'),
                                  node('本题实验｜'+experiment, key=name+'experiment')]+
                             [paper_node(pid,name) for pid in ids.split()], key=name))
    workbook.append(sheet(q,branches))

transfer = [
('A 归因贡献', ['从“长度”拆成N、L、主体数、相似干扰、位置与联合任务',
                '三种条件：固定N变L；近固定L变N；固定证据增困难负例',
                '同模板金融/非金融只是域敏感性诊断，不等于证明金融独有机制',
                '近邻：N01/N03/N29/N30/N31、P29；行为干预优先，检索头可选']),
('B 评测贡献', ['为公开FinRank/FinQA构造出处可追溯的item+chunk长池',
                '原子声明→绑定item→局部证据→支持/矛盾/不足→串绑来源',
                '质量：NDCG/Evidence Recall；可靠：支持率/错绑率/覆盖/无错列表率',
                '近邻：N12/N13/N23/N27、P52；先解决扩容标签与来源质量']),
('C 方法候选：绑定感知偏好训练', ['起点：短窗小模型，明确主体/期间/指标/单位/出处',
                'SFT格式与证据监督→近等长自然错误/受控错绑偏好→DPO',
                '正确排名而理由错的偏好对，尽量保持排名不变以隔离理由训练',
                '近邻：FRONT/SelfCite/LongReward/FinCARDS；不是新发明DPO或引用奖励',
                'GRPO作为可选，不以单卡24GB承诺250项单次长上下文训练']),
('D 必须击败的简单方案', ['元数据过滤＋出处规则；只用chunk；只用item',
                '同一排名下局部证据解释；程序回填可直接判定的理由',
                '普通SFT、普通困难负例SFT、通用引用DPO',
                '同输入信息、模型、训练量、输出覆盖和总预算；简单方案解决即收窄贡献']),
('E 实验优先次序', ['E0 数据审计与去泄漏；扩容新候选unknown需补判',
                'E1 20–30题试验确认现象；这不是正式显著性证据',
                'E2 配对归因与完整错误标注；E3 SFT/DPO及消融',
                'E4 公司/报告/期间隔离测试及候选规模外推',
                '按query或报告bootstrap；同题多个排列不能当独立样本']),
('F 尚未证明与失败出口', ['没有证据证明所有金融长池一定比其他域更容易幻觉',
                '没有完整扩容qrels、模型效果或训练结果',
                '若只格式错，做约束生成；若全靠元数据解决，不包装成RL创新',
                '若仅能做短窗，应报告系统级长池，而非模型原生长上下文改进'])]
workbook.append(sheet('04 创新边界与实验落点', [node(t,[node(s,key=t+str(i)) for i,s in enumerate(xs)]) for t,xs in transfer]))

archive = [e for e in old_entries if e['id'] not in selected]
workbook.append(sheet('05 外围文献与检索边界', [
    node('保留但非核心必读', [paper_node(e['id'],'archive') for e in archive], collapsed=True),
    node('检索方式', [node('长上下文/实体绑定/相似干扰；金融证据/财报/重排；引用/幻觉评测；SFT/DPO/SimPO/PPO/GRPO'),
                       node('前向主题搜索 + 近邻论文参考文献追踪；优先作者论文、ACL、PMLR、NeurIPS、OpenReview及作者仓库'),
                       node('工作级去重：预印本与会议版不重复计；本批次是范围综述，不声称穷尽全部文献')]),
    node('重点复现阅读顺序', [node('FinCARDS/FinRank → LongCite/FRONT → SelfCite/细粒度引用PPO → 绑定机制/长度控制 → RAGChecker/PHANTOM')])]))

def dump(path, obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')

counts=collections.Counter('M' if 'M' in p['reading'] else 'A' for p in papers.values())
registry = {'checked_at':'2026-10-12', 'count':len(papers), 'selected_unique':len(selected),
            'supplemental_count':len(entries), 'reading_count':dict(counts),
            'reading_definitions':OLD['reading_definitions'],
            'scope':'原80项沿用；补充35项包含此前金融专题与本轮新阅读。不表示本轮逐篇重新全文核对。',
            'model_experiments_run':False, 'entries':list(papers.values())}
dump(HERE/'literature_registry_20261012.json',registry)
dump(HERE/'mindmap_content.json',workbook)

target=ROOT/'选题2_三问文献综述与研究路线.xmind'
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
    for fn,obj in [('content.json',workbook),('metadata.json',{'creator':{'name':'Research literature map'},'activeSheetId':workbook[0]['id']}),
                   ('manifest.json',{'file-entries':{'content.json':{},'metadata.json':{}}})]:
        z.writestr(fn,json.dumps(obj,ensure_ascii=False))

# Outline fallback preserves notes and links even without the desktop application.
opml=ET.Element('opml',version='2.0')
ET.SubElement(ET.SubElement(opml,'head'),'title').text='金融item+chunk长池重排：三问文献综述'
body=ET.SubElement(opml,'body')
def outline(parent,n):
    attrs={'text':n['title']}
    if 'href' in n: attrs.update(type='link',url=n['href'])
    if 'notes' in n: attrs['_note']=n['notes']['plain']['content']
    item=ET.SubElement(parent,'outline',attrs)
    for c in n.get('children',{}).get('attached',[]): outline(item,c)
for s in workbook: outline(body,s['rootTopic'])
ET.indent(opml)
ET.ElementTree(opml).write(HERE/'三问文献导图.opml',encoding='utf-8',xml_declaration=True)

matrix=['# 三问文献阅读索引（2026-10-12）','',
        f'工作级去重共{len(papers)}项，其中原索引80项、补充35项；核心三问导图精选{len(selected)}项。核对层级统计：'+str(dict(counts))+'。',
        '本轮不是115篇重新通读。原P01—P80保留之前核对记录，N01—N35区分本轮阅读与此前专题成果；M也仅表示关键方法/相关分析核对，不代表全文附录通读或复现。','',
        '## 新纳入统一索引的35项','']
for e in entries:
    matrix += [f"### {e['id']} {e['short_title']}",'',f"- 版本/出处：[{e['title_and_status']}]({e['primary_url']})。",
               '- 核对：'+','.join(e['reading'])+'；'+e['checked_sections']+'。',
               '- 做了什么：'+e['method_and_scale'], '- 本题迁移与边界：'+e['scope_and_limitation'],
               '- 导图方向：'+'；'.join(e['directions']),'']
matrix+=['## 原80项：沿用记录与新方向映射','','| 编号/论文 | 原核对层级 | 做了什么 | 边界/启发 | 本轮方向 |','|---|---|---|---|---|']
for e in old_entries:
    p=papers[e['id']]
    vals=[f"[{p['id']} {p['title_and_status']}]({p['primary_url']})",','.join(p['reading']),p['method_and_scale'],p['scope_and_limitation'],'；'.join(p['directions']) or '外围资料']
    matrix.append('| '+' | '.join(x.replace('|','／') for x in vals)+' |')
(HERE/'三问文献阅读索引_20261012.md').write_text('\n'.join(matrix)+'\n')

def webtree(n,level=0):
    t=html.escape(n['title'])
    url=n.get('href')
    if url:t+=f' <a target="_blank" rel="noopener" href="{html.escape(url)}">原文 ↗</a>'
    children=n.get('children',{}).get('attached',[])
    note=n.get('notes',{}).get('plain',{}).get('content','')
    if children:
        return '<details'+(' open' if level<2 else '')+'><summary>'+t+'</summary><div>'+(''.join(webtree(c,level+1) for c in children))+(f'<pre>{html.escape(note)}</pre>' if note else '')+'</div></details>'
    return '<p>'+t+'</p>'
page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>金融长池重排｜三问文献地图</title><style>
body{margin:0;background:#f4f6f9;color:#172c42;font:16px/1.8 system-ui,"PingFang SC",sans-serif}main{max-width:1180px;margin:auto;padding:40px 28px}h1{font-size:30px;margin-bottom:10px}header{border-bottom:3px solid #167580;padding-bottom:22px;margin-bottom:28px}details{margin:10px 0;background:white;border:1px solid #dbe4eb;border-radius:10px}summary{cursor:pointer;padding:12px 16px;font-weight:650}details>div{padding:0 16px 12px 26px;border-left:3px solid #d9e9eb;margin-left:18px}p{margin:7px 0}a{color:#067785;font-size:13px}pre{white-space:pre-wrap;font:13px/1.8 system-ui;background:#f5f7f8;padding:14px;border-radius:8px;color:#526270}small{color:#566776}button{background:#126c79;color:white;border:0;padding:9px 18px;border-radius:6px;margin-right:10px;cursor:pointer}section{margin:28px 0}nav a{margin-right:18px;font-size:15px}input{padding:10px;border:1px solid #bbb;border-radius:6px;width:300px;max-width:85%}.hint{color:#526270}.hit{outline:2px solid #dd9c40}</style><main><header><small>毕业论文选题 2 · 文献地图 · 2026-10-12</small><h1>金融 item＋chunk 长候选池重排</h1><p>为什么失效 → 出现什么、如何衡量 → 如何缓解与后训练</p><p class="hint">115项工作索引；论文节点可展开查看方法、适用边界与一次来源。M/A是阅读深度，不是实验结果。</p><button onclick="document.querySelectorAll('details').forEach(x=>x.open=true)">全部展开</button><button onclick="document.querySelectorAll('details').forEach(x=>x.open=false)">全部折叠</button><input placeholder="查找标题，例如 SelfCite" oninput="search(this.value)"></header>'''
page+='<nav>'+''.join(f'<a href="#s{i}">{html.escape(s["title"])}</a>' for i,s in enumerate(workbook))+'</nav>'
page+=''.join(f'<section id="s{i}">'+webtree(s['rootTopic'])+'</section>' for i,s in enumerate(workbook))
page+='''<script>function search(q){document.querySelectorAll('summary').forEach(s=>{let ok=q&&s.textContent.toLowerCase().includes(q.toLowerCase());s.classList.toggle('hit',!!ok);if(ok){let p=s.parentElement;while(p){if(p.tagName==='DETAILS')p.open=true;p=p.parentElement}}})}</script></main></html>'''
(HERE/'三问文献地图_浏览版.html').write_text(page)

# Structural validation: IDs, links, archive CRC, all papers and RQ coverage.
nodes=[]
def collect(n):
    nodes.append(n)
    for c in n.get('children',{}).get('attached',[]):collect(c)
for s in workbook:collect(s['rootTopic'])
assert len({n['id'] for n in nodes})==len(nodes)
assert len(papers)==115 and len(entries)==35
assert all(pid in papers for g in GROUPS for pid in g[3].split())
assert {p['primary_url'] for p in papers.values()} <= {n['href'] for n in nodes if 'href' in n}
with zipfile.ZipFile(target) as z:
    assert z.testzip() is None
    assert json.loads(z.read('content.json'))==workbook
ET.parse(HERE/'三问文献导图.opml')
audit={'date':'2026-10-12','file':target.name,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
       'sheet_count':len(workbook),'topic_count':len(nodes),'unique_papers':len(papers),'core_papers':len(selected),
       'direction_count':len(GROUPS),'reading_count':dict(counts),
       'checks':['ZIP CRC','JSON parse and round-trip','unique topic IDs','paper links complete','OPML XML parse'],
       'native_xmind_open_verified':False,'note':'未检测到本机XMind；已验证文件结构，未声称完成客户端打开测试。'}
dump(HERE/'artifact_validation.json',audit)
print(json.dumps(audit,ensure_ascii=False,indent=2))
