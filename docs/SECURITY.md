# GTN 网络安全运行契约

## 反向代理与客户端 IP

应用只在直连地址属于 `GTN_TRUSTED_PROXY_CIDRS` 时读取
`X-Forwarded-For`，默认信任一个环回代理跳数。Nginx 必须覆盖客户端
提交的转发头：

```nginx
proxy_set_header X-Forwarded-For $remote_addr;
```

不要使用 `$proxy_add_x_forwarded_for`，否则攻击者可以把伪造地址放进链首。
如果站点位于 CDN 后方，应先按 CDN 官方网段配置 Nginx `real_ip`，再让
`$remote_addr` 代表经验证的客户端；不要把任意公网段加入可信代理列表。

相关环境变量：

- `GTN_TRUSTED_PROXY_HOPS`：默认 `1`，不经过代理时设为 `0`。
- `GTN_TRUSTED_PROXY_CIDRS`：默认 `127.0.0.0/8,::1/128`。
- `GTN_TRUSTED_HOSTS`：生产环境建议显式列出允许的 Host（逗号分隔）。
- `GTN_HTTP_ALLOWED_ORIGINS`：确需跨域提交时才列出完整 Origin；默认只接受同源。

所有有副作用的 HTTP 方法会检查 `Sec-Fetch-Site`、`Origin` 或 `Referer`。
响应还会设置 CSP、禁止 MIME 嗅探、限制 iframe 来源，并在 HTTPS 下启用 HSTS。

## 必需凭据与 Cookie

生产环境应在受保护的环境文件中提供：

- `SECRET_KEY`
- `ADMIN_PASSWORD_HASH`
- `ADMIN_CONSOLE_PASSWORD_HASH`
- `BETA_ACCESS_KEY_HASH`

缺少这些值时，应用会生成仅本进程有效的随机值：已知源码默认密码不会
生效，但会话会在重启后失效，对应管理入口也无法登录。禁止把明文密码或
环境文件提交到仓库。

`GTN_SESSION_COOKIE_SECURE` 默认开启。只有明确使用本机 HTTP 开发服务器时
才可临时设为 `0`；生产 HTTPS 不得关闭。

旧管理面板会话同时受空闲时间和绝对时间限制，所有管理写请求都要求该会话
生成的 CSRF token。默认空闲 30 分钟、绝对 8 小时，可分别用
`ADMIN_IDLE_TIMEOUT_SECONDS`、`ADMIN_MAX_SESSION_SECONDS` 收紧。

## 限流层级

应用按服务器总量、客户端 IP、登录账号和具体高成本类别同时计数。所有
动态 HTTP 路由共享总预算，因此更换 URL 不能绕过保护；数据库重路径、
`/api/social/unread`、登录、Socket 连接及 Socket 全事件另有独立预算。

主要可调变量（单位均为每个 `GTN_HTTP_RATE_WINDOW_SECONDS`，默认 60 秒）：

- `GTN_HTTP_SERVER_LIMIT` / `GTN_HTTP_GLOBAL_IP_LIMIT` / `GTN_HTTP_GLOBAL_USER_LIMIT`
- `GTN_HTTP_DB_SERVER_LIMIT` / `GTN_HTTP_DB_IP_LIMIT` / `GTN_HTTP_DB_USER_LIMIT`
- `GTN_HTTP_UNREAD_SERVER_LIMIT` / `GTN_HTTP_UNREAD_IP_LIMIT` / `GTN_HTTP_UNREAD_USER_LIMIT`
- `GTN_SOCKET_TOTAL_SERVER_LIMIT` / `GTN_SOCKET_TOTAL_IP_LIMIT`
- `GTN_SOCKET_TOTAL_USER_LIMIT` / `GTN_SOCKET_TOTAL_SID_LIMIT`
- `GTN_SOCKET_CONNECT_SERVER_LIMIT`

应用的进程内限制不是边缘防火墙的替代品。生产 Nginx 还应启用仓库模板中
的 `limit_req_zone`、`limit_conn_zone`、请求体限制和读写超时。多实例部署时，
Nginx 共享区负责同一入口、跨应用实例之前的第一层保护。应用内令牌桶是
进程本地状态；若改成多主机或绕过同一 Nginx 入口，必须在入口层使用共享限流，
或另行接入 Redis 等共享后端。不要把每次限流计数写入游戏 SQLite，以免攻击流量
反向放大数据库锁争用。

## 社区模组与资源

社区上传 URL、对象 key、账号、有效期和文件大小由服务器签名绑定；登记、替换
和删除不能使用其他账号或索引中越界的对象 key。GTNMOD 会限制压缩前后大小、
条目数、单条目大小、扩展名和压缩比，并拒绝重定向及非配置 R2 源站 URL。

生产 R2 仍应为 `community/uploads/` 配置短期生命周期规则，清理拿到上传 URL
后未完成登记的孤立对象；应用层验证不能替代对象存储的配额和生命周期策略。
管理员可先用 `POST /api/admin/community-mods/storage/cleanup-uploads` 试算，再以
`dry_run=false`、`confirm=true` 清理超过安全等待期且未被索引引用的上传对象。
管理面板将试算与实际清理分成两个按钮；实际清理仍需浏览器二次确认。
字体子集生成要求登录，并同时按账号、IP 和服务器总量限流；单次字符数与缓存
文件数均有上限。

## 依赖更新

运行依赖使用精确版本锁定。升级前后执行：

```powershell
python -m pip_audit -r requirements.txt --progress-spinner off
python -m pytest -q -p no:cacheprovider tests/test_network_security.py tests/test_community_mod_security.py
```

不要只审计开发机的全局 Python 环境；应以本服务的 `requirements.txt` 为准。

## SQLite 与轮询

`journal_mode=WAL` 只在数据库初始化时设置，普通连接不重复协商 WAL。
`GTN_DB_BUSY_TIMEOUT_MS` 默认 1500 毫秒，防止锁争用让请求长时间堆积。

未读统计使用短期有界缓存，并在好友或私信状态变化时强制刷新。请求鉴权
使用只读用户快照，不应在每次轮询时执行赛季维护或提交事务。

## 运维观察

HTTP 限流返回 `429`、`Retry-After` 与 `Cache-Control: no-store`。遇到突发
429 时应先区分单 IP、账号、DB 类别和服务器总量，再调整阈值；不要直接
移除服务器总熔断。Nginx 与应用层都需要观察连接数、429、SQLite busy、
请求延迟和 Socket 拒绝数。
