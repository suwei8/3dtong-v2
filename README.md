# 3dtong-v2 — 逐期事前预测与模型擂台

在公开仓库保存固定的预测数据，不暴露私有历史 CSV。研究目的：3个不重复数字命中下一期开奖号任意1个数字。独立均匀随机模型的理论基准为 **65.7%**，任何模型都不能保证优于随机。

## 预测和开奖复盘

- [真正的事前预测](predictions/live/LATEST.md) 和 [逐期不可覆盖 JSON](predictions/live/runs/)。当前封存的 2026274 不会因为增加 LLM 参赛者而被修改。
- [实战排行榜](reports/live-leaderboard.md)：只统计事前封存之后公布的开奖号，不与历史回测混算。
- [历史遮蔽回测](reports/leaderboard.md)：2026264—2026273 共10期，属于回溯模拟，不是事前成绩。
- [定时预测 workflow](.github/workflows/daily-predict.yml)：每晚北京时间 19:50 与 20:20 两次尝试；21:10 之前需完成计算和发布（GitHub 调度不保证准点），私有 CSV 超过36小时没有更新时拒绝输出。
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
