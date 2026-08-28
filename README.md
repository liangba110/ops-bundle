# 🛡️ Ops Bundle — 服务器运维自动化完整包

一键部署到任意Linux服务器，获得：
- **opsctl** — 22条CLI命令，一条完成常用运维操作
- **自治引擎** — 15条YAML规则，每60秒自动检测+修复
- **智能分析** — 5个特性：EWMA基线/异常检测/趋势预测/根因关联/自动调参
- **Autopilot** — 自动发现高频操作→生成新Python工具

## 快速开始

```bash
# 克隆
git clone https://github.com/liangba110/ops-bundle.git
cd ops-bundle

# 一键部署
bash deploy.sh
```

## 架构

```
Hermes(大脑) → opsctl(22命令) → 引擎(15规则) → 智能分析 → autopilot(自动开发)
```

## opsctl 命令（22条）

| 类别 | 命令 |
|---|---|
| 状态 | `status` `health` `disk` `service` `cron` `network` `port` `top` |
| 部署 | `deploy <project>` |
| 数据库 | `query --user/--order/--money/--tables` `db` `db size` `db optimize` |
| 日志 | `logs errors <svc>` `error-hunter` `db-health` |
| 自动 | `user-lookup <kw>` |
| 运维 | `backup` `backup clean` `ssl` `git` `search` `find` `read` `restart` |

## 自治引擎

```bash
python3 engine.py --status    # 查看状态
python3 engine.py             # 手动执行一次
sudo systemctl restart ops-engine  # 重启
```

### YAML规则（修改即生效）

```yaml
# rules/services.yaml 示例
- name: 后端存活检查
  check:
    type: http
    url: http://127.0.0.1:5002/api/health
  actions:
    - type: restart_systemd
      service: myapp
```

## 智能分析

```bash
python3 intelligence.py --analyze    # 综合报告
python3 intelligence.py --predict    # 磁盘预测
python3 intelligence.py --correlate  # 根因关联
```

## Autopilot

```bash
python3 autopilot.py --report     # 扫描操作模式+建议
python3 autopilot.py --generate <id>  # 生成新工具
python3 autopilot.py --install <id>   # 安装到opsctl
```

## 依赖

- Python 3.10+
- numpy, pymysql, pyyaml
- mysql client, openssl, curl, dig

## License

MIT
