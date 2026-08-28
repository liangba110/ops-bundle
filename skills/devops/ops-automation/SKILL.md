---
name: ops-automation
description: 服务器运维自动化工具集 — opsctl CLI + Ops自治引擎 + 智能分析。触发：任何服务器运维操作（查状态/部署/查数据/看日志/备份/SSL/重启/搜索代码）。
---

# Ops 自动化运维

## 架构

```
Hermes(大脑) → opsctl(快捷操作) → 引擎(自动守护) → 智能分析(自学习)
```

# ops-automation + websearch

## Web搜索（无需web_search工具）

```bash
# GitHub仓库搜索
python3 /opt/ttdazi/ops/websearch.py github "python server monitor"

# GitHub代码搜索
python3 /opt/ttdazi/ops/websearch.py code "anomaly detection python"

# PyPI包搜索
python3 /opt/ttdazi/ops/websearch.py pypi "process manager"

# 综合搜索
python3 /opt/ttdazi/ops/websearch.py all "python ops automation"
```

## opsctl 命令速查（22条）

```bash
OPS="python3 /opt/ttdazi/ops/opsctl.py"

# ── 状态(8) ──
$OPS status                    # 全站状态总览
$OPS health                    # 健康检查(12项)
$OPS disk                      # 磁盘分析
$OPS service                   # 服务列表(6个)
$OPS cron                      # 定时任务列表
$OPS network                   # DNS+连通性
$OPS port                      # 端口占用
$OPS top 10                    # CPU Top进程

# ── 部署(1) ──
$OPS deploy ttdazi|ttdazi-backend|pay|aiweb

# ── 数据库(4) ──
$OPS query --user/--order/--money/--tables/--users-count
$OPS db / db size / db optimize

# ── 日志+安全(3) ──
$OPS logs errors ttdazi        # 错误扫描
$OPS error-hunter              # 全日志错误猎手
$OPS db-health                 # 数据库深度健康

# ── 自动扩展(2) ──
$OPS user-lookup <关键词>      # 用户完整画像

# ── 运维(4) ──
$OPS backup / backup clean / ssl / git
$OPS search/find/read/restart
```

## Autopilot（自动开发引擎）

Hermes调用此工具自动发现高频操作→生成新Python工具→扩展opsctl：

```bash
# 扫描操作模式
python3 /opt/ttdazi/ops/autopilot.py --report

# 生成新工具
python3 /opt/ttdazi/ops/autopilot.py --generate <tool_id>

# 安装到opsctl
python3 /opt/ttdazi/ops/autopilot.py --install <tool_id>
```

可用的自动工具模板：user_lookup, quick_deploy, error_hunter, db_health, backup_report, service_health, domain_check

## Ops 自治引擎

常驻systemd，每60秒扫描15条YAML规则，自动检测+自动修复。

```bash
# 查看引擎状态
python3 /opt/ttdazi/ops/engine.py --status

# 手动执行一次
python3 /opt/ttdazi/ops/engine.py

# 重启引擎
sudo systemctl restart ops-engine

# 查看升级队列（引擎处理不了需要Hermes介入的）
cat /opt/ttdazi/ops/state/escalation.json
```

### 规则文件（修改即生效，无需重启）

```
/opt/ttdazi/ops/rules/
├── services.yaml      # 服务守护（5个服务）
├── security.yaml      # 安全（SSH爆破/恶意进程/磁盘）
├── ssl.yaml           # SSL证书到期
├── database.yaml      # 数据库（连接数/碎片）
├── finance.yaml       # 资金异常
└── intelligence.yaml  # EWMA智能异常
```

## 智能分析

```bash
# 综合报告（基线+异常+预测+关联）
python3 /opt/ttdazi/ops/intelligence.py --analyze

# 磁盘趋势预测
python3 /opt/ttdazi/ops/intelligence.py --predict

# 根因关联
python3 /opt/ttdazi/ops/intelligence.py --correlate

# 采集数据（cron每5分钟自动跑）
python3 /opt/ttdazi/ops/intelligence.py --collect
```

## 标准工作流

### 用户问"平台怎样"
```bash
python3 /opt/ttdazi/ops/opsctl.py status
python3 /opt/ttdazi/ops/opsctl.py health
```

### 改代码后部署
```bash
python3 /opt/ttdazi/ops/opsctl.py deploy ttdazi
```

### 查业务数据
```bash
python3 /opt/ttdazi/ops/opsctl.py query --user <关键词>
python3 /opt/ttdazi/ops/opsctl.py query --order <状态>
```

### 排查问题
```bash
python3 /opt/ttdazi/ops/opsctl.py logs errors ttdazi
python3 /opt/ttdazi/ops/opsctl.py search "关键词"
```

### 处理引擎升级
```bash
cat /opt/ttdazi/ops/state/escalation.json  # 看升级原因
# 根据原因执行修复
python3 /opt/ttdazi/ops/opsctl.py restart <服务>
```

## 跨服务器部署

```bash
# A→B 部署
cd /opt/ttdazi && tar czf /tmp/ops-bundle.tar.gz --exclude='__pycache__' --exclude='*.pyc' --exclude='data/metrics.db' ops/
scp /tmp/ops-bundle.tar.gz ubuntu@82.157.202.24:/tmp/
ssh ubuntu@82.157.202.24 "cd /opt/ttdazi && sudo tar xzf /tmp/ops-bundle.tar.gz && bash ops/deploy.sh"
```

GitHub仓库: `git@github.com:liangba110/ops-bundle.git`

## 开发陷阱

1. **pymysql DictCursor信息表大写** — information_schema查询返回`TABLE_NAME`不是`table_name`，必须用alias: `SELECT TABLE_NAME as tname`
2. **表字段名差异** — money_log用`relate_id`不是`order_id`，withdraw用`companion_id`不是`user_id`，app_order用`create_time`不是`created_at`。写SQL前先`DESCRIBE table`
3. **CHECKERS字典顺序** — Python中`dict[key] = func`必须在func定义之后。把赋值放在`if __name__`之前、函数定义之后
4. **文件反复patch会损坏** — 多次patch同一个文件容易破坏结构。超过3次patch时直接`write_file`重写整个文件
5. **opsctl日志记录** — 每次opsctl调用自动记录到`logs/ops_YYYY-MM-DD.jsonl`，供autopilot分析高频模式
