---
name: ops-codex-fix
description: 运维问题诊断+Codex修复流程。检查出问题后用codex-mimo自动修复。
tags: [ops, codex, fix, devops]
triggers: [运维修复, 修脚本, fix script, codex修复]
---

# 运维 Codex 修复流程

## 原则
检查出问题 → 用 Codex 修复，不手写。（详见 `codex-mimo` skill 调度模式）

## 流程

### 1. 诊断（Hermes做）
```bash
# 检查cron任务状态
hermes cron list

# 检查脚本语法
cd /opt/ttdazi/ops && python3 -c "import ast; ast.parse(open('xxx.py').read())"

# 检查服务状态
systemctl status xxx

# 手动运行脚本看报错
python3 /opt/ttdazi/ops/xxx.py 2>&1
```

### 2. 用Codex修复（构造prompt，不手写代码）
```bash
export OPENAI_BASE_URL="https://token-plan-cn.xiaomimimo.com/v1"
export OPENAI_API_KEY="tp-c2hcz66we5sd0xbpgeuqf0vjqvyq1ix2wsyvdpve7ktv2wj8"

codex exec -m mimo-v2.5-pro --dangerously-bypass-approvals-and-sandbox \
  "在 /opt/ttdazi/ops/ 目录下修复xxx.py的问题：[具体问题描述]。使用subprocess调用mysql命令行，不用pymysql。参考config.py获取数据库配置。"
```

### 3. 验证（Hermes做）
```bash
python3 /opt/ttdazi/ops/xxx.py 2>&1
```

### 4. 反馈用户
- 提取关键结果，不贴原始日志
- 说明修复了什么、验证是否通过

## 约束
- 运维脚本用subprocess+mysql命令行，不用pymysql（PEP668限制）
- 数据库配置从 /opt/ttdazi/ops/config.py 读取
- 所有脚本输出中文

## 🔒 安全铁律（不可违反）

### 清理操作必须三步走
1. **备份** → 先把重要数据备份到 `/data/disk/important_backup/`（数据盘单独建重要文件目录）
2. **确认** → 把备份结果和清理方案发给用户，等用户说"确认"/"执行"才动
3. **执行** → 按确认的方案执行清理

**例外（可直接执行，无需确认）：**
- 纯信息查询（状态检查、日志读取）
- 读取文件/查看配置
- 用户明确说"直接做"/"不用确认"

### 数据盘路径
- 数据盘挂载：`/data/disk`（20G，16%使用率）
- 备份目录：`/data/disk/important_backup/`
- 系统盘：`/`（69G，53%使用率）
