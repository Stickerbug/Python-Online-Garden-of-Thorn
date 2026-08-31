# Python联机版工作区基线（2026-08-31）

> 用途：在当前未提交改动较多的情况下，为本轮计划标记起点，防止后续修改覆盖已完成的故事、Phelren、伤害预测、安全或部署工作。

## 1. Git 起点

- 仓库：`Python联机版`
- 分支：`main`
- HEAD：`1ca434bcea47`
- 记录时工作区：44 个已跟踪文件有改动，14 个未跟踪文件
- 已跟踪差异规模：6,697 行新增，553 行删除
- P0-02 收口时状态：45 个已跟踪改动 + 15 个未跟踪文件（包含本计划与基线文件），共 60 个路径；路径覆盖检查遗漏为 0
- 换行提示：多个文件当前为 LF，Windows Git 提示未来可能转 CRLF；本基线不使用换行重写文件。

## 2. 本轮计划直接产生的改动

### P0-01 公共 AI 入口暂时关闭

| 文件 | 本轮拥有的内容 | 注意 |
|---|---|---|
| `app.py` | `GTN_AI_PUBLIC_ENTRY_ENABLED`、`AI_TEMPORARILY_DISABLED_*`、首页模板参数、状态投影、start/rematch/队列服务端门禁、静态缓存版本后缀 | 该文件在本轮前已有大量故事、Phelren 和安全改动，只能按上述标识识别本轮 hunk |
| `templates/index.html` | `{% if ai_public_entry_enabled %}` 包裹的 Phelren 入口 | 其余 CSP/账号 UI 改动已存在 |
| `static/js/game.js` | 入口可用性同时检查 `data.public_entry_enabled` | 其余伤害预测、UI 和安全改动已存在 |
| `tests/test_ai_1v1_gate.py` | 默认关闭、模板不渲染、稳定错误码、可恢复开关测试 | 本文件也包含既有 AI 入口测试 |
| `tests/test_ai_local_session.py` | 既有公开 AI 正常流程测试显式打开新开关 | 不改动 Phelren 对局本身语义 |
| `docs/API.md` | 区分模型 `enabled`、公开入口 `public_entry_enabled` 和最终 `available` | 该文件在本轮前已有其他 API 文档改动 |
| `scripts/setup_gtn_ai.sh` | AI 环境文件默认写入 `GTN_AI_PUBLIC_ENTRY_ENABLED=0` | 不改模型加载与训练配置 |
| `docs/CHANGE_PLAN_2026-08-31.md` | 本轮执行计划、进度和决策真源 | 新文件 |
| `docs/WORKTREE_BASELINE_2026-08-31.md` | 本基线 | 新文件 |

## 3. 本轮开始前已存在的改动簇

下列分类用于保护边界，不表示已通过本轮最终验收。一个文件可能属于多个簇。

### A. 双人协作故事与单人内容共享

- 核心：`story_coop_combat.py`、`story_coop_content.py`、`story_coop_live.py`、`story_content.py`、`story_engine.py`、`db.py`、`app.py`
- 前端：`templates/story.html`、`static/js/story.js`、`static/css/story.css`
- 文档：`docs/MULTIPLAYER_STORY_MODE.md`
- 测试：`tests/test_story_coop_access.py`、`tests/test_story_coop_combat.py`、`tests/test_story_coop_combat_api.py`、`tests/test_story_coop_content.py`、`tests/test_story_coop_live.py`、`tests/test_story_coop_lobby_ui.py`、`tests/test_story_coop_opening.py`、`tests/test_story_coop_party_api.py`、`tests/test_story_coop_party_api_integration.py`、`tests/test_story_coop_persistence.py`、`tests/test_story_coop_progression.py`、`tests/test_story_presence.py`、`tests/test_story_redesign.py`

### B. PvP 装备指向、伤害链与预测一致性

- 实现：`game_engine.py`、`game_engine_2v2.py`、`static/js/game.js`
- 测试：`tests/test_client_prediction_rules.py`、`tests/test_damage_reduction_order.py`、`tests/test_damage_shield_parity.py`、`tests/test_plank_attack_source.py`、`tests/test_void_dlc_cards.py`

### C. 安全硬化、社区模组与字体子集

- 实现：`app.py`、`security.py`、`r2_mods.py`、`font_subsets.py`、`requirements.txt`、`static/css/style.css`、`static/js/admin.js`、`static/js/game.js`、`static/js/handling.js`、`templates/admin_fake.html`、`templates/adminpage.html`、`templates/beta_gate.html`、`templates/card_exporter.html`、`templates/feedback_handling.html`、`templates/index.html`、`templates/titleeditor.html`
- 文档：`docs/API.md`、`docs/SECURITY.md`
- 测试：`tests/test_community_font_security.py`、`tests/test_community_mod_dom_security.py`、`tests/test_community_mod_security.py`、`tests/test_network_security.py`、`tests/test_settings_persistence.py`

### D. 部署、日志与环境配置

- `scripts/nginx-blue-green-gtn.conf.template`
- `CHANGELOG.txt`
- `scripts/setup_gtn_ai.sh` 中除 P0-01 新增行外的内容

### E. Phelren 会话隔离、恢复与本地对局

- `app.py`、`tests/test_ai_local_session.py` 中除 P0-01 列出 hunk 外的已有改动

## 4. 后续操作规则

1. 不对上述文件执行 `git checkout --`、`git restore`、`git reset --hard` 或全文件覆盖。
2. 重叠文件只使用小 hunk 补丁，每次验证对应测试簇。
3. 每个 P0-P8 任务在计划文档中记录拥有文件/标识和测试证据。
4. 新的临时产物不放入仓库；未跟踪的正式源码和测试视为必须保护的工作成果。
5. 提交或部署前必须再次对照本基线与 `git status --short`，确认没有文件意外消失。

## 5. P0-01 已验证证据

- `python -m pytest -q -p no:cacheprovider tests/test_ai_1v1_gate.py tests/test_ai_local_session.py tests/test_network_security.py tests/test_api_documentation.py`：72 passed
- `node --check static/js/game.js`：通过
- 相关文件 `git diff --check`：通过（只有已知 LF/CRLF 提示）
- Windows 当前无 Bash 可执行文件，因此 `scripts/setup_gtn_ai.sh` 本轮未运行 `bash -n`；其改动仅为 heredoc 内新增一行环境变量。

## 6. P0-03 全量测试基线

- 日期：2026-08-31
- `python -m pytest -q -p no:cacheprovider`：1,132 passed，12 skipped，101 subtests passed，109.09s
- 警告：1 个 Eventlet deprecation warning，非本轮回归
- `node --check`：`static/js/game.js`、`static/js/story.js`、`static/js/admin.js`、`static/js/handling.js` 全部通过
- 全工作区 `git diff --check`：通过，仅输出现有 LF/CRLF 警告
