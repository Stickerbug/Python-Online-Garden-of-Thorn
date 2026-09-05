# 2026-09-05 公开反馈中心（类 Mojira）设计与实施计划

> 状态：方案已实施完成（未部署）。本文同时作为执行记录与打勾依据。
>
> 范围：`Python联机版`（app.py、db.py、static/js、templates、docs、CHANGELOG.txt）。
>
> 本计划不自动部署；是否推送服务器由用户另行确认。

> 实施调整：数据层只把 7 张表及索引放在 `db.py`；公开反馈的增删查改、状态机、投票去重等业务逻辑新建在 `public_feedback.py`（与 `community_ops.py`、`account_integrity.py` 同构），避免 db.py 反向依赖 account_integrity。页面文案、API 与测试按本文执行。

## 1. 已确认的产品决策

| 项目 | 决定 |
| --- | --- |
| 新系统 | 从零新建公开反馈中心，不复用旧 feedback 私有工单的数据结构。 |
| 分区 | 公开中心分“漏洞”与“建议”两区；漏洞走 Mojira 式工单状态流，建议走投票式采纳流程。 |
| 游客 | 可浏览列表、查看漏洞全文、评论只显示前 3 条；不能提交、评论、投票、展开全部评论。 |
| 身份 | 评论/发布者一律按 user_id 实时显示当前昵称、皮肤、称号与角色；账号注销后显示固定“已注销玩家”和灰色头像。不做昵称快照。 |
| 旧系统 | 旧 feedback 入口收窄为管理员/申诉性质，仅保留“账号问题、举报/纠纷、对局申诉”；Bug、建议、其他分类不再提供新入口。旧数据保留在库里，玩家与 staff 常规列表均不显示旧 bug/suggestion 线程，仅管理控制台可审计。不迁移到新站。 |
| 投票 | 登录即可投票；无额外注册时长/对局门槛；probable、confirmed、appealed 关联均拦截并去重，suspected 不拦；作者本人及同组账号不能投票。 |
| 实时去重 | 投票计票与合并均在读取时按当前关联状态实时计算：同组多账号只算 1 票，作者所在组计 0 票；事后被识别为同组的旧票自动被去重，无需人工删票。 |
| 投票可见性 | 无论登录与否都不能查看投票人名单，只能看到票数和“自己是否已投”。 |
| 私密补充 | 每个公开问题有“仅作者与 Staff 可见”的补充区，供索要回放、账号等线索。另有仅 Staff 可见的内部备注。 |
| 内容安全 | 标题、正文、公开评论、私密补充均复用现有 `check_message_risk`/禁言/消毒管线；公开问题与评论可举报，复用 reports + moderation_actions 体系。 |
| 排序 | 默认按 staff 优先级 + 置顶 + 票数 + 最近更新；提供公开排序选项（最新/最近更新/票数）。 |
| 编辑删除 | 评论 5 分钟内作者可编辑/删除；超时或已有回复后只能由 staff 隐藏（保留审计）。问题主贴不可编辑，追加信息走私密补充。 |
| 通知 | 问题作者对状态变化、staff 私密回复有未读红点；staff 对新提交问题、新公开评论、新私密补充有未读红点。 |

## 2. 数据表结构

全部在 `db.py` 的建表迁移段新增。命名不与现有 `feedback_*`、`community_*` 冲突。

### 2.1 public_issues（公开问题/建议主表）

```sql
CREATE TABLE IF NOT EXISTS public_issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,                    -- 'bug' | 'suggestion'
    status TEXT NOT NULL,                  -- 见 2.8 状态机，代码层校验
    author_user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,                    -- 公开全文（游客可见）
    normalized_body TEXT,
    risk_level INTEGER DEFAULT 0,
    replay_id TEXT,                        -- 漏洞可关联回放 ID（可选）
    priority INTEGER NOT NULL DEFAULT 0,   -- staff：0 未分级，1 最高
    pinned INTEGER NOT NULL DEFAULT 0,
    sort_order REAL NOT NULL DEFAULT 0,    -- staff 手动微调顺序
    visible INTEGER NOT NULL DEFAULT 1,    -- 0 = staff 隐藏（审计保留）
    author_private_read_at TEXT,
    staff_private_read_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    status_changed_at TEXT,
    closed_at TEXT,
    FOREIGN KEY(author_user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_public_issues_kind_status ON public_issues(kind, status, updated_at);
CREATE INDEX IF NOT EXISTS idx_public_issues_author ON public_issues(author_user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_public_issues_staff_queue
    ON public_issues(kind, visible, pinned, priority, sort_order, created_at);
```

不把 users 设为 `ON DELETE CASCADE`；账号注销是软删除（`deleted_at`），历史内容保留并显示固定占位身份。

### 2.2 public_issue_comments（公开评论）

```sql
CREATE TABLE IF NOT EXISTS public_issue_comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    issue_id INTEGER NOT NULL,
    author_user_id INTEGER NOT NULL,
    body TEXT NOT NULL,
    normalized_body TEXT,
    risk_level INTEGER DEFAULT 0,
    hidden INTEGER DEFAULT 0,              -- 作者5分钟内删除或 staff 隐藏
    hidden_by_user_id INTEGER,
    hidden_at TEXT,
    created_at TEXT NOT NULL,
    edited_at TEXT,
    FOREIGN KEY(issue_id) REFERENCES public_issues(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_public_issue_comments_issue
    ON public_issue_comments(issue_id, created_at);
```

隐藏原文保留在库内供审计，接口不返回。

### 2.3 public_issue_votes（投票）

```sql
CREATE TABLE IF NOT EXISTS public_issue_votes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    issue_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,     -- 用户取消或 staff 作废时置 0
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    invalidated_by INTEGER,
    invalidated_at TEXT,
    UNIQUE(issue_id, user_id),
    FOREIGN KEY(issue_id) REFERENCES public_issues(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_public_issue_votes_issue ON public_issue_votes(issue_id, active);
CREATE INDEX IF NOT EXISTS idx_public_issue_votes_user ON public_issue_votes(user_id, created_at);
```

计票不直接 `COUNT(*)`，而是按 2.5 的实时关联去重。

### 2.4 public_issue_vote_events（投票审计）

```sql
CREATE TABLE IF NOT EXISTS public_issue_vote_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    issue_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    action TEXT NOT NULL,                  -- add | remove | invalidate | restore | blocked
    reason_code TEXT,                      -- author_group | linked_group | suspected_only | etc.
    actor_user_id INTEGER,
    created_at TEXT NOT NULL,
    FOREIGN KEY(issue_id) REFERENCES public_issues(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_public_issue_vote_events_user
    ON public_issue_vote_events(user_id, created_at);
```

被 probable/confirmed/appealed 拦截的尝试也记 `blocked`，方便 staff 复核误伤。

### 2.5 public_issue_private_messages（作者与 Staff 私密补充）

```sql
CREATE TABLE IF NOT EXISTS public_issue_private_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    issue_id INTEGER NOT NULL,
    sender_user_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    normalized_message TEXT,
    risk_level INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY(issue_id) REFERENCES public_issues(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_public_issue_private_issue
    ON public_issue_private_messages(issue_id, created_at);
```

可见范围：问题作者 + admin/staff。未读状态由 `public_issues.author_private_read_at / staff_private_read_at` 维护，沿用现有 feedback 的 staff/author read 模式。

### 2.6 public_issue_staff_notes（Staff 内部备注）

```sql
CREATE TABLE IF NOT EXISTS public_issue_staff_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    issue_id INTEGER NOT NULL,
    staff_user_id INTEGER NOT NULL,
    note TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(issue_id) REFERENCES public_issues(id) ON DELETE CASCADE
);
```

仅 admin/staff 可见，作者与游客均不可见。

### 2.7 public_issue_status_history（公开状态历史）

```sql
CREATE TABLE IF NOT EXISTS public_issue_status_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    issue_id INTEGER NOT NULL,
    actor_user_id INTEGER NOT NULL,
    from_status TEXT,
    to_status TEXT NOT NULL,
    reason TEXT,                           -- 展示给玩家的公开原因
    created_at TEXT NOT NULL,
    FOREIGN KEY(issue_id) REFERENCES public_issues(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_public_issue_status_history_issue
    ON public_issue_status_history(issue_id, id);
```

原因对外公开；staff 不想公开的内部判断写 staff_notes。

### 2.8 状态机

漏洞：

| 状态 | 含义 | 是否可继续投票 |
| --- | --- | --- |
| `new` | 待确认（新提交默认） | 是 |
| `needs_info` | 需补充信息 | 是 |
| `confirmed` | 已确认，进入按序修复队列 | 是 |
| `in_progress` | 修复中 | 是 |
| `fixed` | 已修复 | 否 |
| `duplicate` | 重复问题 | 否 |
| `unreproducible` | 无法复现 | 否 |
| `by_design` | 设计如此 | 否 |
| `invalid` | 不予处理/无效 | 否 |

建议：

| 状态 | 含义 | 是否可继续投票 |
| --- | --- | --- |
| `new` | 待审核 | 是 |
| `under_review` | 审核中 | 是 |
| `accepted` | 已采纳，进入规划 | 否 |
| `planned` | 已列入规划 | 否 |
| `rejected` | 已拒绝 | 否 |
| `duplicate` | 重复建议 | 否 |

状态流转只在服务端校验；任何状态变更都写 status_history。

## 3. 投票与账号关联算法

### 3.1 关系判定（拦截与去重共用）

两个账号视为“同一投票体”当且仅当满足任一条件：

- 同属一个 `account_link_groups` 且状态为 `confirmed`/`appealed`（`account_link_members` 中 active）；
- `account_link_decisions.state IN ('confirmed','appealed','probable')` 且当前未解除。

`suspected` 不构成投票拦截，也不参与去重。

### 3.2 写入时拦截

投票前检查：

1. 作者本人不能投自己的问题；
2. 当前账号与作者构成 3.1 关系 → 拒绝；
3. 当前账号与任一现存 active 投票账号构成 3.1 关系 → 拒绝；
4. 同账号已投且 active → 拒绝（前端表现为取消投票，接口走同一条 toggle）。

拒绝时记 `blocked` 审计事件，返回统一文案，不透露关联算法细节。

### 3.3 读取时实时去重

有效票数算法（每次详情/列表读取时计算）：

1. 取该问题全部 `active=1` 投票；
2. 剔除已注销账号（`users.deleted_at IS NOT NULL`）的票；
3. 对剩余投票人按 3.1 关系建并查集（连通分量，支持“A-B、B-C”传递）；
4. 若某分量包含作者本人，该分量整体计 0 票；
5. 有效票数 = 其余分量个数（每个分量 1 票）。

因为每次读取都按当前关联状态算，事后才被识别的同组旧票会自动合并，解除关联后按新状态重新计算。

### 3.4 取消与作废

- 登录用户可对自己 active 投票取消（`active=0`，记 `remove`）；
- staff 可经控制台对可疑票作废/恢复（记 `invalidate`/`restore`）；
- 被去重但从未被拦截的历史票不需要逐张删除，读取算法自动处理。

## 4. 页面结构与交互

### 4.1 入口

- 主页新增“反馈中心”链接（与公告/社区入口相邻），点击后以 `target="_blank"` 打开独立页面 `/feedback-center`，游客与登录账号都可浏览；
- 旧“反馈”按钮及其弹窗保留但语义收窄为“管理员/申诉”：分类只显示 账号问题、举报/纠纷、对局申诉；Bug、建议、其他选项从前端隐藏；
- 旧系统已存在的 bug/suggestion 线程在玩家列表与 staff“查看反馈”列表均不展示，管理控制台仍可查。

### 4.2 公开中心主视图

实现为独立 Flask 页面 `feedback_center.html` + 专用 `feedback_center.css/js`。视觉直接对照 Mojira `/browse/MC` 实时页面与计算样式：灰色 `#f4f5f7` 底、`#172b4d` 文字、浅灰 64px 顶栏、320px 左侧问题网格与右侧详情同屏显示；不依赖游戏 SPA 样式与 Socket.IO：

```
┌ 独立页顶栏 ──────────────────────────────┐
│ 品牌 + [漏洞] [建议] + 新建反馈 + 账号头像 │
├ 左侧筛选 ───────────┬─ 列表/详情切换 ─────┤
│ 项目说明、状态、排序  │ 列表行：标题、状态、  │
│                    │ 票数、作者、更新时间   │
└────────────────────┴ 点击后进入详情页：    │
                       正文、投票、评论、私密区、│
                       Staff 管理、状态历史     │
```

页面结构要点：

- 顶栏：未登录显示“去登录”（跳回游戏主页）；登录后显示头像、昵称与未读红点；
- 未登录：浏览与分页可用；发布、评论、投票入口隐藏或跳回登录；
- 登录：可发布、评论、投票；投票按钮显示“已投”状态，取消后票数实时刷新；
- 作者：正文不可改；可看“私密补充”并回复 staff；可看到自己的评论 5 分钟编辑/删除入口；
- staff：额外显示 状态流转、优先级、置顶、内部备注、隐藏评论/问题、举报处理跳转；
- 多语言：所有界面文案进页面自身词典（中/英/法/日）；正文与评论保留作者原始语言，不做机器翻译；
- 原 SPA 内嵌反馈中心 view 已停用并移除对应入口、CSS 与 JS，只保留 `/feedback-center` 一套界面。

## 5. 接口设计（摘要）

| 方法与路径 | 权限 | 作用 |
| --- | --- | --- |
| GET `/api/public-feedback/issues` | 公开 | 列表；kind/status/sort/page；返回票数与评论数（不含投票人） |
| GET `/api/public-feedback/issues/<id>` | 公开 | 详情；游客仅返回前 3 条评论；登录返回全部评论与 own_vote |
| POST `/api/public-feedback/issues` | 登录 | 发布漏洞/建议（kind/title/body/replay_id 可选） |
| POST `/api/public-feedback/issues/<id>/comments` | 登录 | 发表评论 |
| PATCH `/api/public-feedback/comments/<id>` | 作者/staff | 5 分钟内编辑；staff 可隐藏 |
| DELETE `/api/public-feedback/comments/<id>` | 作者/staff | 5 分钟内删除；staff 隐藏 |
| POST `/api/public-feedback/issues/<id>/vote` | 登录 | toggle 自己的投票 |
| GET/POST `/api/public-feedback/issues/<id>/private` | 作者/staff | 读取/发送私密补充 |
| GET/POST `/api/public-feedback/admin/issues/<id>/notes` | staff | 内部备注 |
| POST `/api/public-feedback/admin/issues/<id>/status` | staff | 状态流转（带公开 reason） |
| POST `/api/public-feedback/admin/issues/<id>/priority` | staff | 优先级/置顶/排序 |
| POST `/api/public-feedback/admin/issues/<id>/hide` | staff | 隐藏问题（审计保留） |
| POST `/api/public-feedback/admin/issues/<id>/votes/<uid>` | staff | 作废/恢复某账号票 |
| POST `/api/report` | 登录 | 举报问题/评论，复用现有 reports 表 |

CSRF 与中间件：公开 GET 不要求登录，也不能因跨站请求被误拦；新增路径加入现有 CSRF/权限白名单并单独测试。`feedback_handling_unauthorized` 等现有 staff 中间件不覆盖公开浏览接口。

## 6. 内容安全、限流与举报

- 标题（≤80）、正文（≤4000）、公开评论（≤1000）、私密补充（≤2000）按各自长度校验；
- 复用 `check_message_risk` 与现有 feedback 的处置语义：高风险拦截并禁言、mask/flag 清洗、normalized 文本入库；
- 复用现有 `rate_limiter`：发布 1 次/10 秒 + 每日上限、评论 1 次/5 秒、投票 toggle 1 次/2 秒；staff/chat_exempt 按现有豁免规则放宽；
- 举报写入现有 `reports`，`object_type` 用 `public_issue` / `public_issue_comment`，`object_id` 用对应 ID；举报处理页与 moderation_actions 扩展支持这两个对象类型。

## 7. 旧数据与迁移

- 不新建迁移任务：`feedback_threads`/`feedback_messages` 原样保留；
- 新增逻辑层过滤：常规玩家/管理员列表与 staff 查看列表不返回 `category IN ('bug','suggestion')` 的线程；
- 管理控制台新增按 category 审计旧数据的能力（只读）；
- 公开中心是全新表，不存在旧数据导入；
- 因新表只存 user_id，历史昵称不保存，符合“实时显示当前昵称/皮肤、注销显示固定占位”的决定。

## 8. 管理能力

### 8.1 UI

- staff 在公开中心详情页直接做状态、优先级、置顶、内部备注操作；
- 状态变更公开原因默认写入 status_history 并触发作者红点；
- 举报处理 iframe 能打开 `public_issue`/`public_issue_comment` 类型的举报详情并支持隐藏对象、处罚双方。

### 8.2 命令控制台

新增命令组（名称待实现时与现有命令不冲突，建议 `publicfeedback`）：

- `publicfeedback list <bug|suggestion> [状态] [数量]`
- `publicfeedback get <问题ID>`
- `publicfeedback status <问题ID> <目标状态> [公开原因]`
- `publicfeedback priority <问题ID> <0-5> [sort]`
- `publicfeedback note <问题ID> <备注>`
- `publicfeedback votes invalid|restore <问题ID> <账号ID> [原因]`
- `publicfeedback hide|unhide issue|comment <ID> [原因]`
- `publicfeedback audit <问题ID>`（投票事件与状态历史）

## 9. 分期实施顺序

### 第 1 期：数据层与关联去重

- [x] db.py：新增 2.1-2.7 全部表与索引，幂等迁移；
- [x] account_integrity.py：导出“账号间是否同一投票体”与“作者/投票人并查集”计算函数，疑似不拦截；
- [x] public_feedback.py：公开问题的增删查改、状态机校验、评论、投票、私密补充、内部备注、状态历史、未读计数基础函数；
- [x] 单元测试（tests/test_public_feedback.py 12 项）：建表幂等、状态机非法流转、probable/confirmed/appealed 拦截、suspected 放行、实时去重、作者组零票、注销账号票失效、评论窗口、私密权限、staff 作废票。

### 第 2 期：公开 API 与旧入口收窄

- [x] app.py：第 5 节接口全部实现；登录/游客权限、CSRF 白名单、限流、内容安全；
- [x] 旧 feedback 分类收窄：客户端与服务端都隐藏 bug/suggestion/other 新入口，常规列表过滤旧类型；
- [x] 服务端身份输出：作者/评论者实时昵称、皮肤、称号、角色；注销账号统一输出“已注销玩家”+灰色头像（多语言 UI 键）；
- [x] 接口测试：游客可见全文与前 3 条评论、登录全量评论、投票人不可见、own_vote 正确、红点计数。

### 第 3 期：前端页面

- [x] templates/CSS/game.js：主页入口改为新标签页；新增独立页面 `/feedback-center`，采用 Mojira 同款双栏工作台（左侧问题列表 + 右侧详情），含顶栏账号、搜索、筛选、排序、分页；
- [x] 列表与详情渲染：状态徽标、票数、评论数、作者身份、正文、回放预览、登录/游客差异；
- [x] 评论与私密补充交互：5 分钟编辑/删除、私密补充输入与未读；
- [x] staff 交互：状态、优先级、置顶、内部备注、隐藏操作；
- [x] UI 词典补充中/英/法/日文案；
- [x] 前端契约测试 + 浏览器抽查（独立页游客/登录顶栏、列表、详情、评论、私密区均正常，无 JS 报错）。

### 第 4 期：举报整合、控制台与收尾

- [x] 举报处理页支持 public_issue / public_issue_comment；
- [x] 命令控制台 `publicfeedback` 命令组及帮助文本；
- [x] 账号注销占位与灰头像（含删除历史显示）服务端输出验证；
- [x] 相关测试收尾：account_integrity、admin console、API、前端契约；
- [x] 按现有格式写 CHANGELOG.txt；
- [x] `git diff --check`、`py_compile`、`node --check` 与受影响的 pytest 分组通过（不跑无谓全量）；
- [ ] 等待用户明确“部署”后再推送服务器重启。

## 10. 风险与已知限制

- 关联识别依赖最近 30 天信号，新建小号在被识别为 probable 之前可能短暂投票；靠实时去重与 staff 作废兜底，不追求 100% 识别。
- probable 拦截可能误伤共享网络/合租场景，按既有申诉体系处理，不新增申诉界面。
- 公开中心正文无图片上传；需要图形证据的漏洞通过回放 ID 或私密补充文字描述。
- 昵称实时展示意味着改名会改变历史显示；这是已确认的行为，不是缺陷。
- 不迁移旧 bug/suggestion 线程；如未来需要导出，控制台只读审计即可支持。
