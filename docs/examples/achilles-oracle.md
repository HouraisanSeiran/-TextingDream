# 阿喀琉斯占卜：独立四档示例

这是用户原创场景，不作为神话考据，也不安装进正式 StoryPackage 或 data。`tools.oracle_example.build_example()` 返回最小 `story` / `characters` 字典；验收时仅提交到测试临时根和临时 SQLite。

动作是“献贡向阿波罗询问”，贡品是有限资源，`costs.offering=1` 在正式结算路径真实扣除。预览不扣，失效凭据或重复执行不再次扣除。这里的“失败拒绝回答”是已献贡并掷骰后的结果，不是社交底线门槛的 `status=refused`。

| 档位 | 实际后果 |
|---|---|
| 大成功 critical | 获知脚后跟弱点；额外听到帕里斯愿意在收到决斗时间地点后合作射击，开启联系线索 |
| 成功 success | 获知脚后跟弱点 |
| 失败 failure | 拒绝回答，贡品已消耗 |
| 大失败 disaster | 女祭司称忒提斯回应“赤手空拳按顺序打上半身108穴” |

大成功只写 `paris_contact_lead` 联系线索，不提供击杀、自动射击或阿喀琉斯死亡效果；后续交付时间地点、取得合作和射击不在本最小示例实现范围。

误导通过 `information` 且 `confirmed=false` 进入玩家 `heard`，若指定 NPC 受众则进入 `beliefs`，不写 `facts`，不关联 `source_fact`，不覆盖作者知识。弱点在作者层保持事实；占卜成功才确认给玩家。大失败的公开文本只呈现女祭司的说法，不提前说明真假或揭示成功/大成功分支。预览与意图候选不包含任何未发生分支文本。

验收：`.venv\Scripts\python.exe -m unittest tests.test_checks_v2_four`。四条 HTTP 分支使用真实确定性骰面，不 mock 分档；各自在临时根创建新会话。边界、加值、天然覆盖开关、阈值校验、冻结规则、旧 revision 与贡品重复提交均单独断言。
