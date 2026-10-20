# 3dtong-v2 — 逐期事前预测与模型擂台

在公开仓库保存固定的预测数据，不暴露私有历史 CSV。研究目的：3个不重复数字命中下一期开奖号任意1个数字。独立均匀随机模型的理论基准为 **65.7%**，任何模型都不能保证优于随机。

## 预测和开奖复盘

- [最新事前预测](predictions/live/LATEST.md) · [往期预测可读档案](predictions/live/HISTORY.md)（按期号查看所有模型号码和命中结果）· [逐期不可覆盖原始记录](predictions/live/runs/)。
- [实战排行榜](reports/live-leaderboard.md)：只统计事前封存之后公布的开奖号，不与历史回测混算。
- [历史遮蔽回测](reports/leaderboard.md)：2026264—2026273 共10期，属于回溯模拟，不是事前成绩。
- [定时预测 workflow](.github/workflows/daily-predict.yml)：每晚北京时间 19:50、20:20、20:40 三次尝试（后者为故障备用）；21:10 之前需完成计算和发布（GitHub 调度不保证准点），私有 CSV 超过36小时没有更新时拒绝输出。
- [开奖评分 workflow](.github/workflows/daily-evaluate.yml)：评分只发布命中与否，不提交私有原始开奖内容。

## OpenCode 免费模型参赛（替换 Cline）

完全移除 Cline 认证、CLI 依赖与参赛配置。使用官方 `opencode-ai` npm 包，在 GitHub Actions 临时 Linux runner 调用：

```bash
npm install -g opencode-ai
opencode run --model opencode/mimo-v2.6-flash-free --format json 'Return {"digits":[0,5,8]}'
```

[9 个候选模型配置](configs/opencode_models.json)：

- opencode/big-pickle
- opencode/cat-jam-free
- opencode/longcat-2.5-preview-free
- opencode/mimo-v2.6-flash-free
- opencode/muse-spark-1.3-contributor-free
- opencode/nemotron-3-ultra-free
- opencode/nemotron-3.5-lightning-free
- opencode/space-bunny-free
- opencode/step-5-preview-free

这个列表由用户提供，**不代表每个 ID 在任意时刻都能免登录使用**。GitHub CI 会实际检测，无网络、额度耗尽、模型下架、需要登录或格式错误时记录 `skipped`，不会伪造预测。每个模型只收到最近10/30/100期的聚合数字统计及遗漏间隔，不接触私有 CSV 或 GitHub Token。OpenCode 使用单独临时工作空间，其 `opencode.json` 将工具默认权限设为需确认（无人审批），将编辑、网络搜索和子任务等权限明确设为 `deny`，关闭对话分享；依然不能把进程隔离视为完善的系统沙盒。

只有成功生成**合法JSON、三个不重复整数（0—9）**的 OpenCode 候选才进入当期比赛，并在真正开奖后参与同一排行榜。没有历史训练验证的 LLM 不会被虚构一个冠军分数。

## 安装与本地验证

```bash
python -m pip install -r requirements.txt
python -m pytest -q tests/
python -m src.pipeline.live --history /path/to/private/k3_full_history.csv --opencode
python -m src.pipeline.evaluate_live --full-history /path/to/private/k3_full_history.csv
python -m src.pipeline.opencode_smoke --model opencode/mimo-v2.6-flash-free
```

唯一必要的 GitHub Actions Secret 为 `PINBLE_DATA_TOKEN`，允许读取私有 `suwei8/pinble-data`。OpenCode 匿名免费模型不用配置 Cline Key，也不读取用户账号认证。模型有效性以真实 Actions 运行日志为准。回溯实验和实战预测不会混算。简化规则 `dtong-main10` 不是已验证的原始16模块完整移植。

参考：[OpenCode CLI](https://dev.opencode.ai/docs/cli/) · [OpenCode 模型列表](https://dev.opencode.ai/v2/docs/console/models)。

## 自动运行健康监控

[运行健康报告](reports/STATUS.md) · [运行状态 JSON](reports/operations.json) · [历史事前成绩](reports/live-leaderboard.md)

北京时间 08:00 和 22:10 自动监测私有数据源更新、已开奖期号是否漏做事前预测、已开奖预测是否等待评分。数据超过36小时未更新，或出现确定的漏预测/漏评分时，工作流会在公开状态报告中说明问题并标为失败。只发布期号和状态，不发布私有历史开奖号码。注意：最新开奖之后下一期预测尚未生成，不等于当晚漏预测，不能凭期号推断开奖时间。


## OpenCode 多模型投票及混合集成（未来期号）

除原有九个 OpenCode 免费模型外，系统会尝试两个事前固定规则的派生模型：

- **opencode-consensus**：至少三家免费模型实际成功预测后，按数字得票数选出前三个；得票相同则依次用开奖前训练的传统 ML Ensemble 概率和数字大小打破平局。
- **ml-opencode-hybrid**：固定 50% 归一化 OpenCode 票数 + 50% 归一化 ML Ensemble 概率，选择权重最高的三个不同数字。

单模型成功次数不足三次时，两种派生方案均标记 skipped，不生成虚构票数。
每期冻结 JSON 同时记录参与模型、算法状态、固定权重及最终推荐数字。开奖后的排行榜分别记录有效预测次数、命中、失败调用和95% Wilson 置信区间。

已封存的 2026274 期不会被追溯增补 OpenCode 组合，也不会把历史遮蔽回测冒充真实事前表现。尚无任何科学证据证明这两种集成优于65.7%的独立均匀随机基准。


## 预注册随机对照与统计检验（从2026275期开始）

为了避免看见某个模型短期90%命中率就断言有预测优势，项目在未来期号冻结时增加 `random-control-v1`：
它只对「上期已开奖期号＋本期目标期号＋固定版本标签＋数字0—9」计算 SHA-256 排序，选择最靠前的三个不重复数字。
该算法可复现，不使用私有开奖号、未来数据、模型预测或随机账号状态。这个对照是**伪随机对照**，没有预测优势的假设。

- [已预先提交的研究协议](configs/research_protocol.json) ：固定考察17个候选模型；旧的2026274期结果不纳入新协议。
- [独立研究报告](reports/research.md) · [可读JSON](reports/research.json)：每个模型从2026275期起累计**最早的200次合法事前预测**；少于200次不计算显著性。
- 到第200次有效评分时才计算一次单侧精确二项检验，将P值按17个候选模型做 Bonferroni 校正，避免连续试探并减轻多重比较误判。
- OpenCode未能调用或未参赛的期号不算失败预测；控制组不参加模型优胜显著性检验。模型可用性的偏差仍应在分析中讨论。

**边界：** 65.7%来自独立均匀随机开奖假设；即使完整固定窗口达到统计阈值，也不意味着可投注获利，更不能证明模型间两两优劣。所有推断取决于真实事前封存与开奖源可靠性。历史回测和未来实验始终分开。

## 运行时预算与失败降级

- OpenCode 免费模型是**可选参赛者**：模型耗时总预算上限 240 秒，单模型仍受配置中的45秒超时限制。接近21:10时，必须再提前预留120秒给整理预测文件与Git提交。
- 尚未调用完的模型标记 `skipped`，**不伪造模型投票，也不把未调用算成预测失败**；ML、规则模型和随机对照组仍可形成正常有效的事前预测。
- OpenCode npm 安装最多等待120秒，安装/网络故障不阻断传统模型发布。19:50和20:20失败时，20:40安排一次备用尝试；已封存期号会跳过模型调用，避免重复消耗免费额度。
- 发布前后及 `git pull --rebase` 之后均检查北京时间21:10截止；超过截止拒绝推送新预测。GitHub定时触发是best-effort，不能保证准时运行，若全部延迟或上游无可靠数据，仍可能出现漏期，需要运营健康报告检测。

此降级策略是运行覆盖率保护，**不会提高任何算法的理论预测概率**；对已封存期号无追溯影响。


## 独立的历史滚动实验

[滚动回测、特征消融及严格隔离区说明](docs/ROLLING_RESEARCH.md)：使用6种特征组合、2种基线、逐期时间顺序评估和默认200期保留区。该研究模块**不会修改当前每日预测系统**。


- [独立历史滚动实验任务](.github/workflows/rolling-research.yml)：使用私有历史数据运行，不改动生产模型，仅发布[中文汇总报告](reports/experimental/rolling-ablation.md)。
