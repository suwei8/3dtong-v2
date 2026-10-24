# 3dtong-v2 — 逐期事前预测与模型擂台

<!-- 3DTONG_LATEST_START -->
## 最新一期事前预测｜第 2026283 期

**验证集选定模型：frequency-30 → `801`**

- **预测时已知至：** 第 2026282 期
- **原始封存时间（北京时间）：** 2026-10-24 01:10:58
- **OpenCode 独立封存时间（北京时间）：** 2026-10-24 01:12:58

| 模型 | 三个候选数字 |
|---|---:|
| xgboost | **681** |
| lightgbm | **681** |
| catboost | **863** |
| ensemble | **681** |
| dtong-main10 | **025** |
| frequency-30（验证集选定） | **801** |
| random-control-v1 | **452** |
| opencode/big-pickle | **289** |
| opencode/mimo-v2.6-flash-free | **289** |
| opencode/nemotron-3.5-lightning-free | **289** |
| opencode-consensus | **892** |
| ml-opencode-hybrid | **892** |

[本期预测详情](predictions/live/history/2026283.md) · [最新预测页面](predictions/live/LATEST.md) · [往期全部记录](predictions/live/HISTORY.md) · [实战排行榜](reports/live-leaderboard.md)

说明：仅展示开奖前已封存的三个不同候选数字，不展示实际开奖号码。这不是开奖结果或中奖保证；模型尚无经过确认的预测优势。
<!-- 3DTONG_LATEST_END -->

在公开仓库保存固定的预测数据，不暴露私有历史 CSV。研究目的：3个不重复数字命中下一期开奖号任意1个数字。独立均匀随机模型的理论基准为 **65.7%**，任何模型都不能保证优于随机。

## 预测和开奖复盘

- [最新事前预测](predictions/live/LATEST.md) · [往期预测可读档案](predictions/live/HISTORY.md)（按期号查看所有模型号码和命中结果）· [逐期不可覆盖原始记录](predictions/live/runs/)。
- [实战排行榜](reports/live-leaderboard.md)：只统计事前封存之后公布的开奖号，不与历史回测混算。
- [历史遮蔽回测](reports/leaderboard.md)：2026264—2026273 共10期，属于回溯模拟，不是事前成绩。
- [定时预测 workflow](.github/workflows/daily-predict.yml)：每天北京时间 **00:30、06:20、12:20、17:20、19:50、20:20、20:40** 七次尝试；先检查目标期号、私有数据源的提交时间和北京时间21:10截止，再决定是否安装依赖或调用模型。源数据超过24小时未更新时跳过新预测。GitHub 定时调度仍可能延迟，不能保证每次按时执行。
- [开奖评分 workflow](.github/workflows/daily-evaluate.yml)：评分只发布命中与否，不提交私有原始开奖内容。

## OpenCode 免费模型参赛（替换 Cline）

完全移除 Cline 认证、CLI 依赖与参赛配置。使用官方 OpenCode 2.x `@opencode/cli` npm 包，在 GitHub Actions 临时 Linux runner 调用：

```bash
npm install -g --allow-scripts=@opencode/cli @opencode/cli@2.1.4
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
- opencode/deepseek-v4.1-flash-free（新增探索模型，待真实匿名实测）
- opencode/step-5-preview-free

**2026-10-24 兼容性修复：** OpenCode 官方于 2026-10-19 确认旧模型ID `opencode/space-bunny-free` 已退役，并指向 `opencode/minimax-m3.1-flash-free`（[上游问题说明](https://github.com/anomalyco/opencode/issues/57083)）。旧ID于10月19日退役；替代ID在10月23日也退出了免费目录，因此不再自动调用该免费端点。后续由新增的独立候选DeepSeek V4.1 Flash Free替补，**已封存的 `space-bunny-free` 历史成绩和17模型预注册协议均保持不变，不能将新模型伪装成旧模型的连续命中样本**。新ID为额外观察模型，不纳入旧版固定200期家族的显著性检验。它能否在GitHub Actions匿名环境成功调用，以最新的[合成数据实测报告](reports/opencode-availability.md)为准。

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
- OpenCode npm 安装最多等待120秒，安装/网络故障不阻断传统模型发布。凌晨、白天及傍晚都有重试触发；**已封存目标期号自动跳过后续安装、训练和OpenCode调用**，避免重复消耗额度。全部自动测试由独立CI执行，不再挤占正式预测的发布时限。
- 发布前后及 `git pull --rebase` 之后均检查北京时间21:10截止；超过截止拒绝推送新预测。GitHub定时触发是best-effort，不能保证准时运行，若全部延迟或上游无可靠数据，仍可能出现漏期，需要运营健康报告检测。

此降级策略是运行覆盖率保护，**不会提高任何算法的理论预测概率**；对已封存期号无追溯影响。


## 独立的历史滚动实验

[滚动回测、特征消融及严格隔离区说明](docs/ROLLING_RESEARCH.md)：使用6种特征组合、2种基线、逐期时间顺序评估和默认200期保留区。该研究模块**不会修改当前每日预测系统**。


- [独立历史滚动实验任务](.github/workflows/rolling-research.yml)：使用私有历史数据运行，不改动生产模型，仅发布[中文汇总报告](reports/experimental/rolling-ablation.md)。


- [模型跨时间稳定性研究](reports/experimental/rolling-stability.md)：同一份冻结历史120期，分6段统计命中与配对差距，保留最后200期，不用分段表现自动更新正式模型。


## 真实事前预测覆盖率与同期开奖配对研究

[实时覆盖率与模型配对中文报告](reports/live-paired.md) · [固定的未来配对协议](configs/live_pair_protocol.json)。从2026274期起报告已开奖期数、按时封存期数、漏期及评分覆盖率；从尚未封存的2026281期起，固定四种同期模型比较，每对仅在双方都产生有效事前预测且开奖结果已知时计入分母，最多先记录200期。调用失败不算未命中；不进行中途显著性检验，不影响原有17模型预注册研究和生产预测。


### 提升事前预测覆盖率（2026-10-21 起）

- 新增[纯标准库的快速预检查](src/pipeline/preflight.py)，不依赖 numpy、pip 或 npm。先判定“目标已封存”“当前北京时间已超过21:10”“上游CSV最后Git提交超24小时/时间异常”，仅当条件合格时安装模型依赖。
- 21:10后即使触发延迟任务，也不会把已知结果事后算作当期预测；如果目标期号已封存，则以正常跳过结束，不把重复任务误判为失败。
- 凌晨00:30提供**上一期开奖已更新后的次日期号**尽早预测机会，06:20、12:20、17:20及晚间三个时间点继续兜底。所有新预测仍受21:10最终发布检查约束。
- 可看[预测覆盖率中文报表](reports/live-paired.md)持续验证实际提升；已有`2026277`漏期不会补造。**新调度还需后续生产自动运行验证，CI通过不代表未来零漏期。**


## 采集数据事件触发（优先传统 ML）

公开执行器 `suwei8/pinble-actions` 的 `collect.yml` 在私有 `pinble-data/data/k3_full_history.csv` **真的变化且成功推送后**，使用 repository_dispatch 事件类型 `pinble_history_updated` 立即触发本仓 daily-predict。传输的只有新提交 SHA，接收端验证它属于私有源 Git 历史、确实改过指定 CSV，然后再调用既有防重复/新鲜度/21:10截止预检查。

新路径只运行 **XGBoost、LightGBM、CatBoost、ensemble、dtong-main10、frequency-30 与随机对照**，优先将这些预测封存。OpenCode 由后续独立任务运行，不能把慢模型超时变成 ML 漏报。**已发布的历史事前预测绝不修改。**

在公开执行器仓库 Actions Secrets 配置 `PREDICT_DISPATCH_TOKEN`：仅授本仓 `suwei8/3dtong-v2` Contents: Read and write 权限。此前已经配置的 DATA_REPO_TOKEN / PINBLE_DATA_TOKEN 保持原状。未设置新令牌时跨仓库实时链路不会生效，7次定时兜底继续运行。源码、工作流及报告均不需要、也不会写入令牌内容。


### OpenCode 独立封存和评分

首次事前预测只冻结传统 ML + 随机对照。之后 [optional OpenCode forecasts](.github/workflows/opencode-live.yml) 以独立作业、独立 Git 创建提交保存到 `predictions/live/opencode-runs/<期号>.json`，不会追溯修改传统 ML 的 `predictions/live/runs/`。如遇21:10截止或失败，则跳过或记录不可用，不反过来阻塞传统模型。

开奖后 [daily evaluate](.github/workflows/daily-evaluate.yml) 会先校验两个目录各自的单次封存 Git 历史，只在目标一致、原始封存时间一致且每个候选都合法时，将独立 OpenCode 投票**合并进评分，不修改原始预测**。中文往期页面会同时显示传统封存时间和额外OpenCode封存时间。

历史已有带 OpenCode 的事前封存记录原样保留；未来只有传统模型封存的期号才进入独立OpenCode流程。数据变更的事件触发功能仍需执行器仓库配置 PAT 才能实际生效。


### 跨仓库事件与封存延迟诊断

触发链路：`suwei8/pinble-actions` 的每日增量采集在 `data/k3_full_history.csv` 真正变动并推送成功后，经 `repository_dispatch` 调用本仓 [daily predict](.github/workflows/daily-predict.yml)。**2026-10-21北京时间22:37 已验证事件送达**，但已过21:10安全截止，正确跳过当前预测。次日00:30兜底定时再次检查下一期。

[运营状态报告](reports/STATUS.md)现额外展示：最近私有数据提交时间（只展示时间，不展示数据）、下一目标期传统模型与独立OpenCode封存生成时间、从最近数据源提交到传统模型预测生成的分钟数、生成到公开Git首次提交的秒数。**Git提交时间不等于远端实际push时间**；源数据在预测后再次更新时延迟显示“无法确认”，不把负数当成功。每个预测workflow的运行页面还会记录预检查决策 `already_frozen`、`past_beijing_cutoff`、`stale_or_future_source`、`eligible_pre_result`。由于GitHub调度并不保证准点，追求未来连续30期无漏报仍需实际观察。


### OpenCode 2.x 安装渠道修复（2026-10-24）

`opencode-ai` 的 npm latest 标签仍是 **v1.19.4**，而 OpenCode 2.x 改用 `@opencode/cli`。为复现 MiniMax M3.1 Flash Free 官方说明适用的客户端版本，三个 GitHub 工作流均固定安装 `@opencode/cli@2.1.4`，在调用前校验 major=2；允许该官方包安装 native binary 的 postinstall，其他安装脚本不放行。旧包会导致“模型退役与新目录不兼容”被错误归类为模型不可用。

[官方 OpenCode 2.x 安装说明](https://opencode.ai/v2/docs) · [单模型匿名调用冒烟测试](.github/workflows/opencode-smoke.yml) · [9模型合成数据可用性实测](reports/opencode-availability.md)。真实历史封存数据不会重写，旧17模型统计协议保留退役ID，新ID只作新增观察参赛。


### 2026-10-24 Space Bunny 免费端点最终诊断

GitHub Actions 真实 Linux 匿名CLI实测：`opencode-ai@1.19.4` 老包无法恢复旧模型；升级为官方 `@opencode/cli@2.1.4` 后，`opencode/minimax-m3.1-flash-free` 仍返回404。公开免费模型目录显示其在2026-10-23被下线（[免费目录变更记录](https://freetokens.fyi/channels/opencode-zen)），不应继续把它标为可用。已从**未来新预测**的活跃候选配置中移除旧Space Bunny和已失效的MiniMax免费端点；历史封存和原有17模型预注册协议不变。

`opencode/deepseek-v4.1-flash-free` 作为新一组**观察性参赛候选**加入，必须以[当前CI匿名合成请求](reports/opencode-availability.md)结果确定是否可用；不混入旧版固定200期正式统计。
