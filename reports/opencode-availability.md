# OpenCode 匿名免费模型可用性实测

时间（UTC）：2026-10-24T07:06:12.363715+00:00
测试环境：GitHub Actions 全新 Ubuntu runner；**未设置任何 OpenCode 登录凭证**。
以下仅表示当次合成数据请求能否成功，并非预测能力、长期免费承诺或实际开奖号码。

| 免费模型 | 可用状态 | 备注 |
|---|---|---|
| opencode/big-pickle | 可调用 | JSON校验通过 |
| opencode/cat-jam-free | 跳过/失败 | CLI exit nonzero; inspect model availability |
| opencode/longcat-2.5-preview-free | 跳过/失败 | CLI exit nonzero; inspect model availability |
| opencode/mimo-v2.6-flash-free | 可调用 | JSON校验通过 |
| opencode/muse-spark-1.3-contributor-free | 跳过/失败 | CLI exit nonzero; inspect model availability |
| opencode/nemotron-3-ultra-free | 可调用 | JSON校验通过 |
| opencode/nemotron-3.5-lightning-free | 可调用 | JSON校验通过 |
| opencode/minimax-m3.1-flash-free | 跳过/失败 | CLI exit nonzero; inspect model availability |
| opencode/step-5-preview-free | 跳过/失败 | CLI exit nonzero; inspect model availability |

## 合成数据上的 OpenCode 多模型集成（不计入成绩）

以下只测试 OpenCode → 投票算法的实际调用链。ML 参考概率为人为设置的均匀 10 维向量，不使用历史开奖和真实模型训练。

| 组合算法 | 状态 | 合成测试数字 | 参与模型数 |
|---|---|---|---:|
| opencode-consensus | ok | 493 | 4 |
| ml-opencode-hybrid | ok | 493 | 4 |

实际预测仅允许成功的合法模型输出加入当期封存结果。
若免费模型配额、匿名访问权限或名字变动，下次运行可能不同。
