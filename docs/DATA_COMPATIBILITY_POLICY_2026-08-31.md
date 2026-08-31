# Garden of Thorn 数据版本与兼容策略

> 版本：v1
> 冻结日期：2026-08-31
> 适用范围：单人故事、协作故事、手动故事存档、PvP 回放、花阶赛季数据
> 原则：旧数据不因新代码上线而被静默重写、重新解释或丢失。

## 1. 版本字段职责

| 字段 | 表达内容 | 变更条件 | 禁止事项 |
|---|---|---|---|
| `schema_version` | 状态 JSON 的结构契约 | 字段、类型或阶段联合发生不兼容变化 | 用同一个数字表达两种结构 |
| `content_version` | 卡牌、敌人、地图、事件和规则语义 | 任一会影响权威结算或存档解释的内容变化 | 只改代码、不换版本后继续解释旧状态 |
| `state_version` / `revision` | 单条运行记录的并发版本 | 每次成功提交动作后递增 | 当作内容版本或客户端自增 |
| `replay_version` | 回放容器内事件/帧结构 | 回放编码结构变化 | 用当前卡牌定义重算旧回放 |
| `season_id` | 一段独立排位统计期 | 新赛季开始 | 覆盖旧赛季结果或复用旧 ID |

内容 ID必须稳定且与显示名分离。工作簿重名、别名和翻译变化不得改变既有内容 ID。

## 2. 总体兼容决策

| 数据类型 | 当前版本 | 旧数据策略 | 可写条件 |
|---|---|---|---|
| 单人故事 | schema v9 / `story-redesign-9` | 不自动重置；原状态只读保留，用户明确结束后新建当前版本 | run 行、state JSON 与服务器当前 `content_version` 三者一致 |
| 单人手动存档 | 随 run 固定 | 只允许载入相同 run、相同内容版本的快照 | 当前 run 可写且快照内容版本完全相同 |
| 协作故事 | schema v10 / 带共享内容指纹的版本 | 冻结旧 validator；历史受支持版本可投影只读，动作只允许当前版本 | DB 行与 state 版本一致，且等于当前协作内容版本 |
| PvP 回放 | replay v2 / 下载 envelope v1 | 永不原地迁移；使用当时保存的卡牌/模组快照播放 | 回放创建时写一次，之后只读 |
| 花阶赛季 | `season_id` | 旧比赛、快照、奖励流水永久按原赛季保留 | 新结算只写当前新赛季和幂等业务 ID |

## 3. 单人故事

### 3.1 当前已封住的旧行为

此前 `app.py::_current_story_run` 在发现旧 `content_version` 时会：

1. 为同一 run 生成全新 seed/state；
2. 删除该 run 的动作账本；
3. 原地替换内容版本；
4. 保留仍指向同一 run 的旧手动存档。

这会同时造成旧进度丢失和旧快照跨版本回灌风险。现改为：

- GET 返回原 run，并附 `compatible=false` 与 `expected_content_version`；
- 不调用 `reset_story_run_map`，不删除动作，不改变 seed/state/version；
- 新动作、保存、读取返回 `409 STORY_CONTENT_VERSION_OLD`；
- 已成功落账动作的相同 `action_id` 重试仍按幂等规则返回成功；
- 前端只显示旧版本说明，不尝试用当前内容渲染旧状态；
- 玩家明确确认后才 abandon 旧 run，再创建当前版本新旅程。

旧 run 被 abandon 后仍留在数据库中供审计；玩家历史旅程列表 UI 不在 P0 范围内。

### 3.2 手动存档

- 快照 JSON 必须保留其 `content_version`。
- 创建快照前验证 run 行版本与当前 state 版本一致。
- 读取快照前同时验证 run 行、当前 state、快照 state 三者版本一致。
- 不允许把旧快照“升级”为当前版本后直接载入。
- 后续若新增 `story_manual_saves.content_version` 冗余列，只能作为索引/诊断字段；JSON 内版本仍是权威交叉检查项。

### 3.3 未来迁移要求

当前没有发布任何单人故事内容迁移。未来只有同时满足以下条件才可从只读改为可迁移：

1. 迁移函数按精确 `source_schema + source_content -> target_schema + target_content` 注册；
2. 输入 deepcopy，失败不得改原对象；
3. 迁移结果通过目标 validator，且 row/state 版本一致；
4. RNG seed、stream counter、牌实例 ID和已领取奖励不重抽、不重复发放；
5. 战斗中状态若不能证明等价，明确拒绝；
6. 使用代表性旧存档做 golden tests；
7. 数据库写入在单事务内完成，并保留 migration audit；
8. 不删除旧动作或手动存档，除非另有显式、可审计的归档步骤。

## 4. 协作故事

- schema v10 与单人 v9 分离，不能把单人 combat 对象直接包装为双席位 combat。
- `story_coop_live.validate_coop_live_state` 按持久化 `content_version` 路由冻结 validator；未知版本 fail closed。
- 当前共享内容版本包含 `COOP_CONTENT_FINGERPRINT` 前 12 位，内容目录变化会形成新版本，而不是重新解释旧 run。
- DB commit 要求 run 行、current state、next state 的 `content_version` 完全一致。
- HTTP 动作只允许 `COOP_STORY_CONTENT_VERSION`；旧版 run 可以经过对应旧 validator 和 viewer projection 读取，但不可继续动作。
- 已存在的 v9 -> v10 工具只允许非战斗、单席位迁移；不得自动用于生产双人旅程。
- 历史终局/失败快照即使成员已释放，也必须能通过原 action receipt 或历史读取路径复现最终结果；不得因新内容版本先套当前 validator。

## 5. PvP 回放

- `match_replays.replay_version` 与 blob 内 `version`共同标识回放结构；当前均为 v2。
- 回放写入时保存 `game_version`、`git_sha`、卡牌定义快照、社区模组 blob/hash 和原始动作/关键帧。
- 旧回放只读，禁止用新卡牌数值重新模拟并覆盖原 blob。
- 兼容播放优先使用已存关键帧、delta 和依赖快照；缺失依赖时展示可解释的降级状态，不猜测新规则。
- 对未来未知 `replay_version`：允许查看元数据和下载原始包；时间线解析应明确返回 unsupported，不应改写或删除。
- 保留策略和外部 blob 迁移只能改变存储位置，不得改变 replay SHA、版本和语义。
- 训练数据导出是派生产物，必须记录源 replay ID、replay version、导出 schema 和筛选原因；不得把训练缓存当作原始回放替代品。

## 6. 花阶赛季

- 旧赛季 `gr_match_results`、`gr_daily_snapshots`、`gr_season_activity_rewards` 和货币流水为只读历史证据。
- 本轮排位重做必须创建新的 `season_id`，不能复用现有月度 ID，也不能把旧赛季花阶分作为新排位的当前分数。
- 旧 `total_gr/season_gr` 可用于历史展示、关联账号的模糊最高分档和迁移审计，但不直接影响新赛季对局结算。
- 新赛季初始化值、定级方式和显示名称在 P5-04 冻结；迁移只新增快照/新赛季账户，不更新旧 `gr_match_results`。
- 赛季切换、活动奖励和结算使用唯一业务键；重复执行不得重复发奖或重复归档。
- 当前 `ensure_current_gr_season_for_conn` 会按既有公式把上季分转换到下季，属于 P5-04 必须替换的旧规则；在新排位上线前不能宣称已满足本策略。

## 7. 版本发布检查表

每次故事内容或排位赛季变更必须回答：

1. 这是 schema 变化、content 变化，还是仅展示变化？
2. 新版本常量是否唯一，旧常量含义是否保持不变？
3. DB 行和 JSON 内版本是否交叉校验？
4. 旧记录是继续可写、自动迁移、只读，还是明确拒绝？
5. 是否存在跨版本手动存档、动作重试、断线重连或终局 receipt？
6. RNG、奖励、货币、信誉和花阶分是否可能重复结算？
7. 回滚代码后，新版本数据会如何显示？
8. 是否有旧版 fixture、损坏状态、未知未来版本和并发测试？
9. 用户是否能在不丢数据的情况下明确结束旧 run 并开始新 run？
10. 更新日志是否说明兼容边界，而不是只写“更新内容”？

## 8. 本轮验证

- 新增单人旧版本不自动重置测试。
- 新增旧版本动作拒绝和 duplicate 重试测试。
- 新增 DB 提交跨内容版本拒绝测试，确认不落动作账本。
- 新增手动存档跨内容版本拒绝测试，确认 run 不变。
- 新增前端旧版本显式结束/新建契约测试。
- 协作历史版本、持久化与当前版本 action gate 继续由现有 coop 测试覆盖。
