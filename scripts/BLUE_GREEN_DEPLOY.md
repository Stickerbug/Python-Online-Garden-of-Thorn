# GTN 蓝绿 / 静默更新操作流程

目标：旧对局留在旧进程完成，新玩家和新对局进入新进程。

## 前提

- 正式服当前服务：`gtn-release.service`
- 当前端口：`127.0.0.1:5000`
- 新实例建议端口：`127.0.0.1:5002`
- 数据库仍共用 `/var/lib/gtn/gtn.sqlite3`
- 不要同时开多个写入数据库的长期重型后台清理任务。临时新实例建议设置 `GTN_DB_MAINTENANCE_ENABLED=0`。
- Phelren 配置统一从 `/etc/gtn/ai.env` 读取；蓝绿实例共享 `/opt/gtn-ai-runtime` 的只读推理包和 `/var/lib/gtn-ai` 的诊断数据，不要把它们复制进发布目录。

## 1. 准备新目录

```bash
cd /opt/gtn-release
scripts/blue_green_prepare.sh /opt/gtn-release /opt/gtn-next 5002 release
```

## 2. 启动新实例

按脚本输出创建或修改一个临时 systemd service，例如：

```bash
cp /opt/gtn-next/scripts/gtn-blue-green.service.template /etc/systemd/system/gtn-release-next.service
systemctl daemon-reload
systemctl start gtn-release-next
```

先在开发机的 `GTN-AI` 仓库生成仅含在线推理模块和最终模型的运行包：

```bash
python tools/build_runtime_bundle.py \
  --checkpoint models/structured-v2-search-dagger-v2.epoch-06.pt
```

上传生成的 `dist/gtn-ai-runtime.tar.gz` 后，在服务器执行：

```bash
cd /opt/gtn-release
GTN_AI_RUNTIME_ARCHIVE=/root/gtn-ai-runtime.tar.gz \
  bash scripts/setup_gtn_ai.sh
```

服务器不克隆完整 `GTN-AI` 仓库，也不保存训练脚本、测试、数据集、缓存或历史检查点。
`GTN_AI_RUNTIME_ARCHIVE` 也可以是私有 Release/OSS 的 HTTPS 下载地址。正式服务若不是由本模板创建，给
`gtn-release.service` 增加以下 drop-in：

```ini
[Service]
EnvironmentFile=-/etc/gtn/ai.env
```

然后运行 `systemctl daemon-reload`。默认最多同时保留 5 局未结束的 Phelren 对局，模型只加载一次，重型
推理串行执行；诊断保留 14 天且总量上限 2 GiB。修改 `/etc/gtn/ai.env` 后需要重启游戏
服务才会生效。

检查：

```bash
/opt/gtn-next/scripts/blue_green_status.sh 5000 5002
curl -fsS http://127.0.0.1:5002/api/health/full
```

## 3. 切 Nginx 新流量

将正式域名反代从 `127.0.0.1:5000` 切到 `127.0.0.1:5002`。

```bash
scripts/blue_green_switch_nginx.sh 5002 /opt/gtn-next
nginx -t
systemctl reload nginx
```

此时：

- 新打开网页的玩家进入新实例。
- 已打开旧网页的玩家仍可能连着旧实例。
- 已经在旧对局中的玩家刷新页面时，前端会带 `gtn_route_port` cookie，Nginx 应按该 cookie 路由回旧实例。
- 回到大厅、再来一局、退出观战会清除该 cookie，之后进入当前 active 实例。

如果你的 Nginx 还没有 sticky map，请先把 `scripts/nginx-blue-green-gtn.conf.template` 的 `map $cookie_gtn_route_port $gtn_release_backend` 合并到正式站点配置。以后切换只改 map 里的 `default 127.0.0.1:端口;`。

## 4. 旧实例进入排空

在旧实例控制台执行：

```text
drain on
```

效果：

- 拒绝新登录、新邀请、新训练场、新教程、新再来一局。
- 允许旧对局断线玩家返回。
- 旧对局继续运行。

## 5. 等旧实例清空

查看：

```text
status
rooms
drain status
```

或者：

```bash
/opt/gtn-next/scripts/blue_green_status.sh 5000 5002
```

旧实例 `rooms=0` 后，可以停止旧服务。

如果新实例成为唯一正式实例，可以重新启用低频数据库维护任务：

```bash
# 修改新 service 环境为 GTN_DB_MAINTENANCE_ENABLED=1 后重启，或等下一次正常维护窗口处理。
```

## 6. 收尾

如果新实例稳定，可以将 `/opt/gtn-next` 提升为新的正式目录，或下次部署继续使用新的 next 目录。

注意不要直接删除 `/var/lib/gtn`。

## 回滚

如果新实例异常：

1. Nginx 切回 `127.0.0.1:5000`。
2. 旧实例控制台执行 `drain off`。
3. 停止新实例：

```bash
systemctl stop gtn-release-next
```
