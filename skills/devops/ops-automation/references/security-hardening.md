# Security Hardening — ops系统安全加固

## 2026-08-29 完成的6项修复

### 1. 路径环境变量化

**问题：** 所有脚本硬编码 `/opt/ttdazi/ops`
**修复：** `config.py` 从 `.env` 读取路径

```python
# config.py
PROJECT_DIR = Path(os.environ.get('PROJECT_DIR', '/opt/ttdazi'))
OPS_DIR = Path(os.environ.get('OPS_DIR', '/opt/ttdazi/ops'))
```

### 2. 密码外部化

**问题：** MySQL密码 `huizhiyun2026` 直接写在代码里
**修复：** 移到 `.env`（权限600）

```env
MYSQL_PASSWORD=huizhiyun2026
MIMO_API_KEY=tp-c2hcz66we5sd0xbpgeuqf0vjqvyq1ix2wsyvdpve7ktv2wj8
```

权限：`chmod 600 /opt/ttdazi/ops/.env`

### 3. SQL注入防护

**问题：** `cmd_query` 直接拼接用户输入到SQL
**修复：** 添加危险操作拦截

```python
dangerous = ['DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'UPDATE', 'INSERT', 'GRANT', 'REVOKE']
for d in dangerous:
    if d in sql.upper():
        return {'status':'error','message':f'禁止执行: {d}操作'}
```

用户输入清洗：
```python
import re
kw = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff_\-\\s]", "", kw)
```

### 4. LLM自动执行白名单

**问题：** `action_llm_decide` 会执行LLM建议的任何命令
**修复：** 只允许白名单内的安全命令

```python
SAFE_COMMANDS = ['systemctl', 'mysql', 'nginx', 'df', 'free', 'top', 'ps', 'ss', 'curl']
if cmd and any(cmd.startswith(s) for s in SAFE_COMMANDS):
    if 'rm -rf' not in cmd and 'DROP' not in cmd.upper():
        run_cmd(cmd, timeout=30)
```

### 5. block_ip白名单

**问题：** 直接 `iptables -A INPUT` 可能封掉正常IP
**修复：** 添加白名单保护

```python
WHITELIST = ['127.0.0.1', '::1', '42.193.113.230', '82.157.202.24', 
             '165.154.224.225', '185.239.224.191']
if ip in WHITELIST:
    continue  # 跳过白名单IP
```

### 6. 回滚机制

**问题：** 清理文件、优化数据库等操作不可逆
**修复：** Git快照+安全回滚

```python
def git_snapshot():
    """每次修改前自动commit"""
    run(f"cd {PROJECT_DIR} && git add -A && git commit -m '快照' --allow-empty")

def git_rollback():
    """回滚前检查是否有快照"""
    out, _ = run(f"cd {PROJECT_DIR} && git log --oneline -5 | grep '快照'")
    if not out:
        return False  # 无快照可回滚
    run(f"cd {PROJECT_DIR} && git reset --hard HEAD~1")
```

## 部署检查清单

- [ ] `.env` 文件存在且权限为600
- [ ] `config.py` 能正确读取 `.env`
- [ ] `opsctl.py` SQL注入防护已启用
- [ ] `engine.py` LLM白名单已配置
- [ ] `engine.py` block_ip白名单已配置
- [ ] `dev_agent.py` 回滚机制已启用
