# OpenCode 匿名免费模型可用性实测

时间（UTC）：2026-10-15T04:32:08.735844+00:00
测试环境：GitHub Actions 全新 Ubuntu runner；**未设置任何 OpenCode 登录凭证**。
以下仅表示当次合成数据请求能否成功，并非预测能力、长期免费承诺或实际开奖号码。

| 免费模型 | 可用状态 | 备注 |
|---|---|---|
| opencode/big-pickle | 可调用 | JSON校验通过 |
| opencode/cat-jam-free | 跳过/失败 | TimeoutExpired |
| opencode/longcat-2.5-preview-free | 可调用 | JSON校验通过 |
| opencode/mimo-v2.6-flash-free | 可调用 | JSON校验通过 |
| opencode/muse-spark-1.3-contributor-free | 可调用 | JSON校验通过 |
| opencode/nemotron-3-ultra-free | 可调用 | JSON校验通过 |
| opencode/nemotron-3.5-lightning-free | 可调用 | JSON校验通过 |
| opencode/space-bunny-free | 可调用 | JSON校验通过 |
| opencode/step-5-preview-free | 可调用 | JSON校验通过 |

实际预测仅允许成功的合法模型输出加入当期封存结果。
若免费模型配额、匿名访问权限或名字变动，下次运行可能不同。
