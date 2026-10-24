# 大模型 vs LightGBM：同期开奖事前配对验证

只计入**已经开奖**的期号；尚未开奖的下一期预测不算漏报。
缺失事前封存文件算一次系统覆盖失败，不允许事后补成预测。
真实开奖号码和预测的三个数字不会出现在此报告中。

## 预测覆盖率

监测期号从 **2026274** 开始。
已开奖期数：**10**；其中有事前封存：**9**；已评分：**9**。
预测覆盖率：**9/10**（90.00%）
评分覆盖率：**9/10**（90.00%）
漏做事前预测：2026277
已有事前预测但尚未评分：无

## 同一期模型直接比较（仅描述，不做提前显著性检验）

方案从 **2026284** 开始，每组最多累计最早的 **200** 次双方都有合法预测且已开奖的期号。
模型超时/跳过/没有出现在封存记录中时，本期不进入该模型对的分母。

| 模型 A | 模型 B | 同期样本进度 | 仅 A 命中 | 仅 B 命中 | 都命中 | 都未命中 | A－B命中率差 |
|---|---|---:|---:|---:|---:|---:|---:|
| opencode/big-pickle | lightgbm | 0/200 | 0 | 0 | 0 | 0 | — |
| opencode/cat-jam-free | lightgbm | 0/200 | 0 | 0 | 0 | 0 | — |
| opencode/longcat-2.5-preview-free | lightgbm | 0/200 | 0 | 0 | 0 | 0 | — |
| opencode/mimo-v2.6-flash-free | lightgbm | 0/200 | 0 | 0 | 0 | 0 | — |
| opencode/muse-spark-1.3-contributor-free | lightgbm | 0/200 | 0 | 0 | 0 | 0 | — |
| opencode/nemotron-3-ultra-free | lightgbm | 0/200 | 0 | 0 | 0 | 0 | — |
| opencode/nemotron-3.5-lightning-free | lightgbm | 0/200 | 0 | 0 | 0 | 0 | — |
| opencode/deepseek-v4.1-flash-free | lightgbm | 0/200 | 0 | 0 | 0 | 0 | — |
| opencode/step-5-preview-free | lightgbm | 0/200 | 0 | 0 | 0 | 0 | — |
| opencode-consensus | lightgbm | 0/200 | 0 | 0 | 0 | 0 | — |
| ml-opencode-hybrid | lightgbm | 0/200 | 0 | 0 | 0 | 0 | — |

**重要：** 配对是在此前探索研究之后选定的，即使达到200次，也不能仅凭这张表视为确认性证据。
本报告不会计算中途 p 值，不替代原有17模型的200期预注册研究，也不会自动调整生产模型。
