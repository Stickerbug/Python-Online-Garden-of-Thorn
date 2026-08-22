# GTN API 接口与权限

> 审计日期：2026-08-15
> 代码基准：<code>app.py</code> 中的 Flask 与 Flask-SocketIO 路由

本文记录当前游戏本体会使用的接口。它是开发文档，不是对外承诺的第三方 API：字段与事件可能随游戏规则调整，未经明确许可不应使用脚本批量调用。

本文有意不记录管理密码、访问密钥、管理命令语法、服务器文件路径和敏感响应字段。管理接口只列权限与用途。

## 通用约定

- HTTP 基址为当前网页同源地址，正文通常使用 UTF-8 JSON。
- 登录状态保存在服务端会话中，由同源 Cookie 关联；当前没有面向第三方的 Bearer Token 或 API Key。
- 客户端应使用 <code>credentials: same-origin</code>，不要自行保存或转发会话 Cookie。
- 成功响应通常包含 <code>{"success": true}</code>；失败响应通常包含 <code>{"success": false, "error": "..."}</code>。
- 常见状态码：<code>400</code> 参数错误、<code>401</code> 未登录、<code>403</code> 权限不足、<code>404</code> 资源不存在、<code>409</code> 状态冲突、<code>429</code> 请求过快、<code>503</code> 数据库或服务暂不可用。
- 客户端提交的房间、玩家、牌、目标、费用和状态都不可信。最终合法性由服务器根据会话、房间、阶段、回合和当前状态重新判断。
- HTTP 与 Socket.IO 均按同源部署设计；没有开放跨域调用约定。

## 权限级别

| 标记 | 含义 |
| --- | --- |
| 公开 | 登录前即可读取，或属于注册、登录入口 |
| 可选账号 | 未登录可读取；登录后会附带自己的数据 |
| 账号 | 必须登录注册账号，游客不可用 |
| 玩家会话 | 必须先通过 Socket.IO 的 <code>login</code> 建立当前连接；部分模式允许游客 |
| 受限会话 | 使用独立的导出器、内测或管理会话，不等于普通账号登录 |
| Staff | 账号身份必须为 <code>staff</code> 或 <code>admin</code> |
| Admin | 管理会话或账号身份必须满足对应管理员检查 |
| 本机 | 仅应用主机的直连健康检查可用；经反向代理的外部请求不算本机 |

## 公开与基础接口

| 方法 | 路径 | 权限 | 用途与主要参数 |
| --- | --- | --- | --- |
| GET | <code>/api/healthz</code> | 公开 | 轻量存活检查；只应用于负载均衡与部署探针 |
| GET | <code>/api/changelog</code> | 公开 | 更新日志；查询参数 <code>limit</code> |
| GET | <code>/api/auth/me</code> | 公开 | 检查当前账号会话；未登录返回 <code>authenticated=false</code> |
| GET | <code>/api/leaderboard</code> | 可选账号 | 排行榜；<code>scope=season|total</code>、<code>min_games</code>、<code>limit</code>，登录后可附自己的名次 |
| GET | <code>/api/cards</code> | 公开 | 卡牌目录；可传 <code>disabled_mods</code>、<code>include_all_mods</code>、<code>mode</code> 及社区模组选择 |
| GET | <code>/api/opening-events</code> | 公开 | 配装倾向/开局事件目录；模组参数与卡牌目录一致 |
| GET | <code>/api/mods</code> | 公开 | 内置模组目录；<code>summary=1</code> 返回精简信息 |
| GET | <code>/api/community-mods</code> | 可选账号 | 社区模组目录；登录后仅增加当前账号的管理标记 |
| GET | <code>/api/mod-assets/&lt;asset_id&gt;</code> | 公开 | 读取已登记的模组图片资源 |
| POST | <code>/api/font-subsets/community</code> | 公开、限流 | 为已登记社区模组准备缺字字体子集；仅接受模组选择数据 |
| GET | <code>/api/hidden-features/status</code> | 公开 | 当前会话是否已解锁隐藏入口 |
| GET | <code>/api/ai-1v1/status</code> | 公开 | Phelren 测试入口是否启用、是否拥挤；只有登录账号会得到可用状态 |

公开读取只覆盖页面渲染所需资料，不包含账号私有数据、完整回放、服务器诊断或写入能力。

## 账号与身份

| 方法 | 路径 | 权限 | 主要请求字段 / 行为 |
| --- | --- | --- | --- |
| POST | <code>/api/auth/register</code> | 公开、限流 | <code>username</code>、<code>password</code>、<code>password_confirm</code> |
| POST | <code>/api/auth/login</code> | 公开、限流 | <code>username</code>、<code>password</code> |
| POST | <code>/api/auth/logout</code> | 当前会话 | 清除当前账号和记住登录状态 |
| POST | <code>/api/auth/change-password</code> | 账号 | <code>old_password</code>、<code>new_password</code>、<code>new_password_confirm</code>；成功后注销全部设备 |
| POST | <code>/api/auth/change-username</code> | 账号 | <code>username</code> 或 <code>new_username</code> |
| POST | <code>/api/auth/delete-account</code> | 账号 | 软注销当前账号 |
| POST | <code>/api/auth/skin</code> | 账号、限流 | 保存 <code>skin</code> |
| GET | <code>/api/auth/me</code> | 公开 | 返回当前会话的公开账号资料 |
| GET, POST | <code>/api/account/keybindings</code> | 账号 | 读取或保存 <code>keybindings</code>；保存可带 <code>expected_revision</code> 防止覆盖新版本 |

账号接口只允许操作当前会话对应的账号。玩家编号、用户名或请求体中的其他身份字段不能替代服务端会话。

## 荆露、成就、称号与商店

| 方法 | 路径 | 权限 | 用途 |
| --- | --- | --- | --- |
| GET | <code>/api/thorn-dew</code> | 账号 | 荆露中心、签到和任务进度 |
| POST | <code>/api/thorn-dew/checkin</code> | 账号 | 领取当日签到 |
| GET | <code>/api/achievements</code> | 账号 | 成就、里程碑、称号与荆露摘要；可传 <code>lang</code> |
| POST | <code>/api/titles/equip</code> | 账号 | 按顺序保存最多三个 <code>title_ids</code> |
| POST | <code>/api/titles/name-style</code> | 账号 | 从自己拥有的称号中选择 <code>title_id</code> 与 <code>segment_id</code> 作为昵称颜色 |
| GET | <code>/api/title-shop</code> | 账号 | 当日称号商店 |
| POST | <code>/api/title-shop/refresh</code> | 账号 | 消耗荆露主动刷新 |
| POST | <code>/api/title-shop/lock</code> | 账号 | 设置 <code>locked</code> |
| POST | <code>/api/title-shop/purchase</code> | 账号 | 购买当前 <code>set_id</code> 中的 <code>slot</code> |

价格、库存、拥有数量和奖励全部由服务器计算；客户端显示值不能作为结算依据。

## 故事模式

故事模式的所有数据接口都要求登录账号。<code>run_id</code> 也必须属于当前账号。

| 方法 | 路径 | 用途与主要参数 |
| --- | --- | --- |
| POST | <code>/api/story/presence</code> | 页面心跳；<code>client_id</code>、<code>activity</code> |
| POST | <code>/api/story/afk-check</code> | 回答挂机检测；<code>client_id</code>、<code>id</code>、<code>hold_ms</code> |
| GET | <code>/api/story/discoveries</code> | 当前账号的故事图鉴发现记录 |
| POST | <code>/api/story/discoveries/read</code> | 标记新发现已读 |
| GET | <code>/api/story/run</code> | 获取当前旅程 |
| POST | <code>/api/story/run</code> | 创建旅程 |
| GET | <code>/api/story/content</code> | 当前故事内容与版本 |
| POST | <code>/api/story/run/action</code> | 提交原子操作；<code>run_id</code>、<code>action_id</code>、<code>action_type</code>、<code>state_version</code>、<code>payload</code>、<code>client_id</code> |
| POST | <code>/api/story/run/abandon</code> | 放弃当前 <code>run_id</code> |
| GET | <code>/api/story/run/saves</code> | 列出 <code>run_id</code> 的手动存档 |
| POST | <code>/api/story/run/save</code> | 保存 <code>run_id</code> 与 <code>state_version</code> |
| POST | <code>/api/story/run/save/delete</code> | 删除 <code>save_id</code> |
| POST | <code>/api/story/run/load</code> | 读取 <code>save_id</code>；同时校验 <code>run_id</code> 与 <code>state_version</code> |
| POST | <code>/api/story/run/reset-map</code> | Staff 开发工具；普通账号得到 404 |

### 双人协作故事实验大厅

以下接口全部要求已登录的 Staff/Admin 账号；普通账号统一得到 404。响应均使用
<code>Cache-Control: private, no-store</code>。当前接口只开放队伍大厅、独立存档和
首版无界面的战斗协调内核，不代表完整协作旅程已经可玩。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | <code>/api/story/coop/bootstrap</code> | 获取实验功能版本、人数与规则摘要 |
| GET | <code>/api/story/coop/party</code> | 获取当前账号所在队伍、本人席位与活动旅程摘要 |
| POST | <code>/api/story/coop/party</code> | 创建双人队伍并返回一次性邀请码 |
| POST | <code>/api/story/coop/party/join</code> | 使用邀请码加入尚未开始的队伍 |
| POST | <code>/api/story/coop/party/invite</code> | 队长按 <code>party_revision</code> 轮换一次性邀请码 |
| POST | <code>/api/story/coop/party/leave</code> | 按 <code>party_revision</code> 离开或解散组队中的队伍 |
| POST | <code>/api/story/coop/party/start</code> | 队长在两席就绪后按 <code>party_revision</code> 创建独立 v10 旅程 |
| POST | <code>/api/story/coop/party/abandon</code> | 任一成员确认后按 <code>party_revision</code> 放弃活动旅程并解散队伍 |

<code>action_id</code> 用于幂等与重放保护，<code>state_version</code> 用于拒绝过期页面覆盖新状态。客户端不应跳过它们。

## 社交、私信、反馈与举报

以下接口均要求登录账号，并继续执行好友关系、封禁、禁言、长度和频率检查。

| 方法 | 路径 | 用途与主要参数 |
| --- | --- | --- |
| GET | <code>/api/social/friends</code> | 好友与申请；<code>mark_read</code> |
| GET | <code>/api/social/unread</code> | 社交、私信、反馈未读数 |
| POST | <code>/api/social/friends/add</code> | 按 <code>identifier</code> 申请好友 |
| POST | <code>/api/social/friends/respond</code> | <code>request_id</code>、<code>action</code> |
| POST | <code>/api/social/friends/remove</code> | 删除 <code>user_id</code> |
| POST | <code>/api/social/settings</code> | 保存社交与游客观战设置 |
| GET | <code>/api/social/dm/threads</code> | 私信会话列表；<code>limit</code> |
| GET | <code>/api/social/dm/messages</code> | <code>thread_id</code>、<code>limit</code>、<code>mark_read</code> |
| POST | <code>/api/social/dm/send</code> | <code>identifier</code> 或 <code>target_user_id</code>、<code>text</code> |
| GET | <code>/api/feedback/summary</code> | 反馈摘要与未读数 |
| GET | <code>/api/feedback/threads</code> | 反馈工单列表；<code>status</code>、<code>limit</code>；Staff 可使用受控的 <code>staff</code> 视图 |
| GET | <code>/api/feedback/messages</code> | <code>thread_id</code>、<code>limit</code>、<code>mark_read</code> |
| POST | <code>/api/feedback/send</code> | 新建或回复反馈；<code>thread_id</code>、<code>category</code>、<code>title</code>、<code>text</code>、<code>replay_id</code> |
| POST | <code>/api/feedback/status</code> | 更新自己有权处理的 <code>thread_id</code> 状态 |
| POST | <code>/api/report</code> | 举报玩家、消息或对局；<code>object_type</code>、<code>object_id</code>、<code>category</code>、<code>reason_text</code> |

举报证据由服务器按对象重新收集。请求体中的目标昵称和说明不能直接变成处罚依据。

## 回放

所有回放接口都要求登录。普通账号只能读取自己有权查看的回放；Staff/Admin 才能进入管理上下文。

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | <code>/api/replays</code> | 当前账号的回放列表；<code>limit</code>、<code>offset</code>、<code>mode</code>、<code>mod_source</code> |
| GET | <code>/api/replays/&lt;replay_ref&gt;</code> | 回放元数据与快照 |
| GET | <code>/api/replays/&lt;replay_ref&gt;/timeline</code> | 时间线；可使用 <code>offset</code>、<code>limit</code> 分页 |
| GET | <code>/api/replays/&lt;replay_ref&gt;/download</code> | 下载 <code>.gtnreplay</code>；执行归属检查与单账号/IP 限流 |

外部提交任意回放编号不会绕过 <code>replay_visible_to_user</code>。

## 社区模组

| 方法 | 路径 | 权限 | 用途 |
| --- | --- | --- | --- |
| GET | <code>/api/community-mods</code> | 可选账号 | 公开目录；不会向普通调用方返回上传者账号编号 |
| POST | <code>/api/community-mods/upload-url</code> | 账号、限流 | 为 <code>filename</code> 创建短期上传地址 |
| POST | <code>/api/community-mods/register</code> | 账号、限流 | 登记 <code>key</code>、<code>public_url</code>；可带 <code>replace_sha256</code> |
| DELETE | <code>/api/community-mods/&lt;sha256&gt;</code> | 账号、限流 | 仅上传者或有全局管理权的账号可删除 |
| POST | <code>/api/community-mods/validate-url</code> | 账号、限流 | 校验当前 R2 公开域名中的 <code>public_url</code> |
| POST | <code>/api/font-subsets/community</code> | 公开、限流 | 生成/读取已登记内容所需字体子集 |
| POST | <code>/api/mods/save</code> | Staff | 开发环境写入内置 Mod Spec v2；不能由普通账号或游客调用 |

远程校验只允许配置中的社区模组公开域名，并限制文件尺寸与连接时间；它不是任意 URL 代理。

## 受限工具会话

这些入口不使用普通账号权限，且不应被当作公共 API。

| 方法 | 路径 | 权限 / 用途 |
| --- | --- | --- |
| GET | <code>/api/card-exporter/me</code> | 查看卡牌导出器会话状态 |
| POST | <code>/api/card-exporter/login</code> | 独立访问密钥、失败限流 |
| POST | <code>/api/card-exporter/logout</code> | 清除导出器会话 |
| GET | <code>/api/card-exporter/cards</code> | 导出器会话；读取完整卡牌渲染资料 |
| POST | <code>/api/beta/login</code> | 内测实例访问密钥、失败限流 |
| POST | <code>/api/beta/logout</code> | 清除内测会话 |
| POST | <code>/api/hidden-features/unlock</code> | 隐藏入口访问密钥、失败限流 |
| GET | <code>/api/hidden-features/status</code> | 仅返回本会话解锁状态 |

文档与前端代码中都不应写入这些会话的明文密钥。

## Staff 与 Admin 接口

### 称号编辑器

<code>/api/title-editor/*</code> 要求登录 Staff/Admin 账号，并在写操作中校验编辑器 CSRF 令牌。

| 方法 | 路径 | 权限 |
| --- | --- | --- |
| GET | <code>/api/title-editor/workspace</code> | Staff/Admin，目录、草稿和历史 |
| POST | <code>/api/title-editor/preview</code> | Staff/Admin，解析预览，不发布 |
| POST, DELETE | <code>/api/title-editor/draft</code> | Staff/Admin，保存或放弃自己的草稿 |
| POST | <code>/api/title-editor/publish</code> | Admin，显式确认后发布 |
| POST | <code>/api/title-editor/rollback</code> | Admin，显式确认后回退 |

### 反馈处理台

以下路径全部由统一前置检查限制为 Staff/Admin。这里只记录能力，不公开处罚请求细节。

- <code>GET /api/feedback/handling/reports</code>
- <code>GET /api/feedback/handling/reports/&lt;report_id&gt;</code>
- <code>POST /api/feedback/handling/reports/&lt;report_id&gt;/resolve</code>
- <code>GET /api/feedback/handling/users</code>
- <code>GET /api/feedback/handling/users/&lt;user_id&gt;</code>
- <code>POST, PATCH /api/feedback/handling/users/&lt;user_id&gt;/ban</code>
- <code>GET /api/feedback/handling/matches</code>
- <code>GET /api/feedback/handling/moderation</code>
- <code>PATCH, DELETE /api/feedback/handling/warnings/&lt;warning_id&gt;</code>
- <code>GET, POST /api/feedback/handling/ip-bans</code>
- <code>PATCH, DELETE /api/feedback/handling/ip-bans/&lt;ip&gt;</code>

### Web 管理页

除登录与会话状态检查外，所有 <code>/api/admin/*</code> 路径都由统一前置检查限制为管理会话：

- 会话：<code>GET /api/admin/me</code>、<code>POST /api/admin/login</code>、<code>POST /api/admin/logout</code>
- 运行状态：<code>GET /api/admin/status</code>、<code>GET, POST /api/admin/drain</code>、<code>GET /api/admin/security/suspicious</code>
- 举报：<code>GET /api/admin/reports</code>、<code>GET /api/admin/reports/&lt;report_id&gt;</code>、<code>POST /api/admin/reports/&lt;report_id&gt;/resolve</code>
- 账号：<code>GET /api/admin/users</code>、<code>GET /api/admin/users/&lt;user_id&gt;</code>
- 统计：<code>GET /api/admin/draft-stats</code>、<code>GET /api/admin/opening-event-stats</code>、<code>POST /api/admin/draft-stats/rebuild-wins</code>
- 存储：<code>GET /api/admin/storage/summary</code>、<code>POST /api/admin/storage/cleanup-old</code>、<code>POST /api/admin/storage/cleanup-orphans</code>、<code>POST /api/admin/storage/vacuum</code>
- 社区文件：<code>GET /api/admin/community-mods/storage</code>、<code>POST /api/admin/community-mods/storage/delete</code>
- 命令：<code>POST /api/admin/command</code>、<code>GET /api/admin/complete</code>
- 对局维护：<code>GET /api/admin/ls</code>、<code>POST /api/admin/kick</code>、<code>POST /api/admin/broadcast</code>、<code>GET /api/admin/game-chat</code>、<code>POST /api/admin/game-chat/send</code>、<code>POST /api/admin/room/&lt;room_id&gt;/skip</code>、<code>POST /api/admin/room/&lt;room_id&gt;/endgame</code>、<code>POST /api/admin/room/&lt;room_id&gt;/draftfill</code>、<code>POST /api/admin/room/&lt;room_id&gt;/set</code>

### 独立管理终端

<code>/api/adminconsole/*</code> 使用独立管理会话；除登录和 <code>me</code> 外均由统一前置检查保护，命令写操作还要求 <code>X-Admin-Console-CSRF</code>。

- <code>GET /api/adminconsole/me</code>
- <code>POST /api/adminconsole/login</code>
- <code>POST /api/adminconsole/logout</code>
- <code>POST /api/adminconsole/command</code>
- <code>GET /api/adminconsole/complete</code>
- <code>GET /api/adminconsole/jobs/&lt;job_id&gt;</code>
- <code>POST /api/adminconsole/jobs/&lt;job_id&gt;/cancel</code>

### 详细健康诊断

<code>GET /api/health/full</code> 仅允许：

- 应用主机直接访问回环地址，且请求没有经过带 <code>X-Forwarded-For</code> 的反向代理；
- Staff/Admin 账号会话；
- Web 管理页或独立管理终端会话。

公网监控只应使用 <code>/api/healthz</code>。详细诊断含数据库、锁和待处理流程信息，不应公开。

## Socket.IO

Socket.IO 使用默认命名空间与 <code>/socket.io/</code> 传输路径。连接本身公开，但除握手和延迟检测外，事件必须匹配当前 SID 的玩家、观战或账号状态。普通账号 Cookie 不会让任意 SID 自动获得房间权限。

### 客户端发送事件

| 类别 | 事件 |
| --- | --- |
| 连接与同步 | <code>connect</code>、<code>disconnect</code>、<code>latency_ping</code>、<code>latency_report</code>、<code>request_pregame_state</code>、<code>request_game_state</code> |
| 登录与挂机 | <code>login</code>、<code>afk_activity</code>、<code>afk_check_response</code>、<code>skin_look</code> |
| 大厅与模式 | <code>set_mode</code>、<code>update_mod_settings</code>、<code>draft_reroll</code> |
| 1v1 邀请 | <code>invite</code>、<code>accept_invite</code>、<code>decline_invite</code> |
| 2v2 队伍 | <code>form_team</code>、<code>accept_team</code>、<code>decline_team</code>、<code>leave_team</code>、<code>invite_team</code>、<code>accept_team_match</code>、<code>decline_team_match</code> |
| 断线重连 | <code>reconnect_accept</code>、<code>reconnect_decline</code> |
| 聊天 | <code>chat</code>、<code>story_chat_join</code>、<code>story_chat_send</code> |
| 开局流程 | <code>draft_pick</code>、<code>select_opening_event</code>、<code>confirm_opening_reveal</code>、<code>reroll_opening_event</code>、<code>submit_event_sub_choice</code> |
| 正式对局 | <code>play_card</code>、<code>response</code>、<code>ally_consent_response</code>、<code>resolve_choice</code>、<code>v2_ui_response</code>、<code>use_trigger</code>、<code>end_turn</code> |
| 无限火力 | <code>urf_replace_card</code>、<code>urf_sell_equipment</code> |
| 投降与结算 | <code>surrender</code>、<code>surrender_consent_response</code>、<code>rematch</code>、<code>return_lobby</code> |
| 观战 | <code>spectate</code>、<code>leave_spectate</code>、<code>switch_spectate_perspective</code> |
| 单人训练 | <code>solo_start</code>、<code>solo_play_card</code>、<code>solo_response</code>、<code>solo_resolve_choice</code>、<code>solo_v2_ui_response</code>、<code>solo_use_trigger</code>、<code>solo_end_turn</code>、<code>solo_set_next_draw</code>、<code>solo_undo</code>、<code>solo_redo</code>、<code>solo_pause</code> |
| 新手教程 | <code>tutorial_start</code>、<code>tutorial_bot_action</code> |
| Phelren 测试 | <code>ai_1v1_start</code>、<code>ai_1v1_rematch</code>、<code>ai_1v1_mark_decision</code> |

客户端不应依赖某个事件“看起来能发送”来判断操作合法。比如 <code>play_card</code> 仍会检查玩家存活、当前回合、卡牌实例、费用、选择阶段、目标和等待中的反制。

### 主要服务端推送

服务端推送属于 UI 内部协议，字段不承诺稳定。当前事件包括：

- 状态：<code>lobby_update</code>、<code>state_update</code>、<code>solo_state</code>、<code>draft_state</code>、<code>game_phase</code>、<code>pregame_status_update</code>。
- 选择：<code>choice_request</code>、<code>response_request</code>、<code>v2_ui_request</code>、<code>ally_consent_request</code>。
- 邀请/队伍：<code>invite_received</code>、<code>invite_confirm_required</code>、<code>invite_gr_preview</code>、<code>team_invite</code>、<code>team_match_invite</code>、<code>team_match_confirm_required</code>、<code>team_formed</code>、<code>team_disbanded</code>。
- 断线/计时：<code>opponent_disconnected</code>、<code>opponent_reconnected</code>、<code>reconnect_available</code>、<code>reconnect_timeout</code>、<code>turn_timer_update</code>、<code>pregame_timer_update</code>。
- 聊天/通知：<code>chat</code>、<code>lobby_chat_history</code>、<code>dm_update</code>、<code>achievement_unlocked</code>、<code>account_warning</code>、<code>server_broadcast</code>。
- 观战/AI：<code>spectate_enter</code>、<code>spectate_leave</code>、<code>ai_1v1_status</code>、<code>ai_1v1_decision_marked</code>。
- 结果/错误：<code>login_ok</code>、<code>login_fail</code>、<code>action_rejected</code>、<code>server_error</code>、<code>kicked</code>、<code>account_session_replaced</code>。

## 安全维护清单

新增接口时至少确认：

1. 默认要求账号、Staff/Admin 或已建立的玩家 SID；只有页面启动必需的只读资料才匿名开放。
2. 写接口不接受客户端指定“代表哪个账号”；从服务端会话取当前用户。
3. 房间操作重新检查 SID、房间、玩家索引、阶段和动作序列。
4. URL 下载、导出、搜索、聊天、登录和高成本生成接口必须限流，并设置尺寸/时间上限。
5. 管理接口不只依赖前端隐藏；必须有服务端前置检查。高风险管理写操作还应有 CSRF 与显式确认。
6. 错误响应不回传密码、哈希、数据库路径、堆栈或不必要的内部标识。
7. 新增或删除 HTTP 路由、Socket 事件时同步更新本文。

## 待确认的接口建议

以下均未实现，添加前需要确认：

- <code>GET /api/meta</code>：只返回公开版本、支持语言、内容版本和能力开关，减少前端从多个接口拼装。
- <code>GET /api/account/export</code>：登录账号下载自己的可携带数据，不包含管理记录、他人消息或内部风控字段。
- <code>GET /api/account/sessions</code> 与 <code>POST /api/account/sessions/revoke</code>：查看并注销自己的其他登录设备。
- 开发环境专用的 OpenAPI/路由清单：仅本机或 Staff 可见，用于自动检查文档，不在正式公网开放。

若以后提供真正的第三方 API，建议单独使用 <code>/api/v1/</code>、独立令牌、权限范围、审计日志和版本兼容策略，不要直接承诺当前游戏内部接口。
