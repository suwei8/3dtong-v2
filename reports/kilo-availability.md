# Kilo 匿名免费模型可用性实测

时间（UTC）：2026-11-08T18:19:27.970783+00:00
测试环境：GitHub Actions 全新 Ubuntu runner；**未设置任何 Kilo 登录凭证**。
以下仅表示当次合成数据请求能否成功，并非预测能力、长期免费承诺或实际开奖号码。

| 免费模型 | 可用状态 | 备注 |
|---|---|---|
| kilo/cohere/north-mini-code:free | 可调用 | JSON校验通过 |
| kilo/dots-studio/dots-3-note-preview:free | 可调用 | JSON校验通过 |
| kilo/kilo-auto/free | 可调用 | JSON校验通过 |
| kilo/liquid/lfm-3-1.7b:free | 可调用 | JSON校验通过 |
| kilo/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free | 可调用 | JSON校验通过 |
| kilo/nvidia/nemotron-3-ultra-550b-a55b:free | 可调用 | JSON校验通过 |
| kilo/nvidia/nemotron-3.5-lightning:free | 跳过/失败 | TimeoutExpired |
| kilo/nvidia/nemotron-3.5-super-vl:free | 可调用 | JSON校验通过 |
| kilo/openrouter/free | 可调用 | JSON校验通过 |
| kilo/reflection/beam-free | 跳过/失败 | TimeoutExpired |

## 合成数据上的 Kilo 多模型集成（不计入成绩）

以下只测试 Kilo → 投票算法的实际调用链。ML 参考概率为人为设置的均匀 10 维向量，不使用历史开奖和真实模型训练。

| 组合算法 | 状态 | 合成测试数字 | 参与模型数 |
|---|---|---|---:|
| kilo-consensus | ok | 134 | 8 |
| ml-kilo-hybrid | ok | 134 | 8 |

实际预测仅允许成功的合法模型输出加入当期封存结果。
若免费模型配额、匿名访问权限或名字变动，下次运行可能不同。
