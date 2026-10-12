# 2 人爬塔重写计划：单人引擎 + 席位作用域（最小改动集）

状态：**进行中，已暂停**（2026-10-12 起）。分支 `coop-engine-rewrite`，进度见文末。

## 背景

现有 v10 平行合作引擎（story_coop.py / story_coop_live.py / story_coop_combat.py /
story_coop_content.py 的白名单执行器）被判定不合格：
- 界面是对话框+文字日志，远差于单人界面；
- 平行小引擎永远追不平单人内容（卡牌效果白名单 8 种 vs 单人引擎数十种，
  轨道/召唤/装备/脚本敌人全部缺失）。

用户决策（2026-10-11/12）：**重写 2 人爬塔引擎 = 在单人引擎 story_engine.py 上做
部分更改（席位作用域）**，让合作模式天然继承全部内容与单人界面，只是旁边显示队友。

## 架构

单人引擎内部读写方式不变（`combat['shield']`、`combat['hand']` 等扁平键直接用），
新增席位作用域：
- `state['players'][seat]`（单人恒 1 席），`state['player']` = 当前挂载席运行时别名；
- `combat['seat_states'][seat]` 持有每席战斗数据；`_mount_seat/_seat_scope/
  _sync_mounted_seat` 挂载为顶层扁平键——结算谁的 action 就先挂载谁；
- 共享治理键反向白名单 `SHARED_COMBAT_KEYS`（round/turn/enemies/投影等），
  其余键全部跟席位走，新增玩家侧键零登记；
- 存量 v9 惰性迁移（`_normalize_legacy_story_state` 无条件从扁平键重建挂载席），
  不跳 schema 版本，线上旅程零影响。

## 引擎改动清单（约 20 个节点）

1. ✅ 持久层 players 列表 + 惰性迁移 + 挂载机制 + `_start_combat` 两遍席位化
   （第一遍各席扁平初始化 → 共享敌人入场 → 第二遍各席遗物/抽牌，事件顺序与单人一致）。
2. ⬜ 伤害管线 victim_seat：`_player_physical_hit/_player_damage/_player_raw_damage/
   _player_magic_shield` 加可选受击席参数（默认=挂载席，单人零改动）；敌方结算按意图目标传入。
3. ⬜ 回合治理：`_end_turn` → ready 栅栏（`combat['ready_seats']`，全员 ready 才
   `_enemy_turn`；单人 1 席即原行为）；回合结束弃牌/装备/轨道对每席逐席挂载执行。
4. ⬜ 敌人意图：`target_seat`（回合开始具名 RNG 锁定、倒地顺位重指）与 `attack_all`
   （逐席调用伤害管线）。
5. ⬜ 死亡/胜负：全席倒地才判负；胜利时倒地席复活 20% 最大生命。
6. ⬜ 待选交互 per-seat（`pending_card_choice` 等键带席）。
7. ⬜ 投影 per-seat（`_refresh_combat_projections` 按 viewer 席位）。
8. ⬜ 事件 actor/target 席位化（presentation 原样保留 → 合作动画免费继承）。
9. ⬜ RNG namespace 需要处带 seat 上下文（seat 0 命名与单人完全一致）。

单人回归红线：每步全量单人套件保持基线（17 既有失败 / 806 通过，2026-10-12 基线）。

## 后续阶段

- **story_coop_engine.py 编排薄层**（取代 v10）：复用 party/runs DB 与 REST、地图投票
  具名 RNG、per-seat 赐福/奖励/商店/休息、阶段屏障；同时英雄回合（挂载→apply→卸载）+
  ready per-seat；敌人双人系数（3/2 起步可配）。
- **前端**：服务端按 viewer 席位投影（形状=单人 state）→ 现有单人渲染管线零适配直用；
  新增队友面板/意图目标徽标/准备按钮/投票覆盖层/队友动画标识；退役
  `#story-coop-combat-dialog` 与 `renderStoryCoopCombat*`。
- **之后**：大厅各席选角色（party_members 加 character_id，起始状态×席位，几乎免费）、
  Socket.IO 推送 + presence、3-4 人扩展。

## 主要风险与对策

- 挂载纪律（漏挂/漏卸写错席）→ 上下文管理器强制成对 + 双席单测逐路径断言；
- 敌人逐席结算顺序 → 固定席位序、事件流可复现；
- 单人回归 → 全量套件红线（每步对照基线）；
- 入库 JSON 会重复保存挂载席数据（扁平+seat_states 同值）——已试过入库剥离
  `player` 键但读取路径在 normalize 前依赖它，11 个测试炸；已回退，重复暂接受，
  优化方向=读取路径统一先 normalize。

## 进度

- eaaee12（2026-10-12，rebase 后）：第 1 步席位化基础，单人 809 项零回归（基线随 main 更新为 14 既有失败/809 通过）。
- 第 2/3 步（2026-10-12）：victim_seat 伤害包装（物理/原始/完整三管线，挂载作用域递归）、ready 栅栏（ready_seats + combat_seat_ready 事件、cancel_ready 撤回、就绪席 SEAT_ALREADY_READY 封锁出牌）、敌方逐席受害席（每敌人每轮具名 RNG 锁定 coop_enemy_target:{combat}:{round}:{enemy}，效果结算后清理 _victim_seat）、单席倒地不判负（seat_downed 事件）、胜利复活 20%（seat_revived 事件）。双席测试 test_coop_engine_seats.py 7 项全过。
- 下一步：第 4 步（pending per-seat + 投影 per-seat + 事件席位化）→ 双席回合结束逐席处理（当前全员就绪后只结算挂载席的回合结束，弃牌/重抽需逐席循环）→ 编排层。
