# 3dtong-v2｜预注册统计研究

固定评估方案：first-200-valid-prospective-issues-v1
纳入注册起点之后的已评分期数：**11**
检验起点期号：**2026275**；每个模型首次 **200** 次真实合法事前预测构成一个固定窗口。
理论随机命中概率：**65.7%**；
单侧精确二项检验；多重比较 Bonferroni 校正：**17 个模型**。

**未达到200次有效预测的模型不计算p值，也不宣称优于随机。**

| 已注册模型 | 固定窗口进度 | 命中率（窗口内） | Bonferroni p |
|---|---:|---:|---:|
| xgboost | 11/200 | 54.5% | 待满200次 |
| lightgbm | 11/200 | 72.7% | 待满200次 |
| catboost | 11/200 | 63.6% | 待满200次 |
| ensemble | 11/200 | 63.6% | 待满200次 |
| dtong-main10 | 11/200 | 72.7% | 待满200次 |
| frequency-30 | 11/200 | 72.7% | 待满200次 |
| opencode/big-pickle | 10/200 | 60.0% | 待满200次 |
| opencode/cat-jam-free | 1/200 | 100.0% | 待满200次 |
| opencode/longcat-2.5-preview-free | 5/200 | 80.0% | 待满200次 |
| opencode/mimo-v2.6-flash-free | 11/200 | 54.5% | 待满200次 |
| opencode/muse-spark-1.3-contributor-free | 2/200 | 100.0% | 待满200次 |
| opencode/nemotron-3-ultra-free | 6/200 | 83.3% | 待满200次 |
| opencode/nemotron-3.5-lightning-free | 7/200 | 71.4% | 待满200次 |
| opencode/space-bunny-free | 3/200 | 100.0% | 待满200次 |
| opencode/step-5-preview-free | 0/200 | — | 待满200次 |
| opencode-consensus | 11/200 | 63.6% | 待满200次 |
| ml-opencode-hybrid | 11/200 | 63.6% | 待满200次 |
| random-control-v1 | 11/200 | 72.7% | 待满200次 |

**注意：** 固定评估样本可能存在模型调用失败/遗漏而分布在不同期号；
这里的检验只针对理想独立随机模型，不构成模型之间两两优劣或收益性证明。
不同于持续更新的实战命中率，这个协议不会在前200次完成前不断试探显著性。
开奖码与私有训练数据不包含在本报告。
