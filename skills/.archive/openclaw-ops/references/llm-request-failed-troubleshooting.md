# LLM Request Failed 完整排查指南

## 错误分类

| 错误信息 | 根因 | 修复优先级 |
|----------|------|-----------|
| `LLM request failed` | 会话写锁卡死 | ⭐⭐⭐ 最常见 |
| `Request timed out before response` | Agent整体超时 | ⭐⭐ |
| `model idle timeout` | API首事件超时 | ⭐ |

## 排查流程

```bash
# 1. 查看最近错误
journalctl --user -u openclaw-gateway.service --since '10 minutes ago' --no-pager | grep -iE '(error|fail|timeout|stuck)'

# 2. 检查会话锁
find /home/ubuntu/.openclaw -name '*.lock' -ls

# 3. 检查会话文件数量
ls -la /home/ubuntu/.openclaw/agents/main/sessions/

# 4. 检查内存使用
free -h
ps aux --sort=-%mem | head -5
```

## 修复命令速查

### 会话写锁卡死
```bash
systemctl --user stop openclaw-gateway.service
rm -rf /home/ubuntu/.openclaw/agents/main/sessions/*
rm -rf /home/ubuntu/.openclaw/sessions/*
find /home/ubuntu/.openclaw -name '*.lock' -delete
systemctl --user start openclaw-gateway.service
```

### Agent整体超时
```bash
# 调整配置
python3 -c "
import json
with open('/home/ubuntu/.openclaw/openclaw.json', 'r') as f:
    config = json.load(f)
config['agents']['defaults']['timeoutSeconds'] = 120
config['models']['providers']['xiaomicoding']['timeoutSeconds'] = 60
with open('/home/ubuntu/.openclaw/openclaw.json', 'w') as f:
    json.dump(config, f, indent=2)
"
systemctl --user restart openclaw-gateway.service
```

### 沙箱无限循环
在 AGENTS.md 末尾添加：
```
## 防卡死规则
1. 遇到 Path escapes sandbox root 错误 → 立即停止，不重试
2. 遇到 Memory flush writes restricted 错误 → 立即停止
3. 工具调用失败最多重试 1次，连续失败 2次停止
```

## 预防措施

### 自动清理 Cron
```bash
# 每小时清理
0 * * * * rm -f /home/ubuntu/.openclaw/agents/*/sessions/*.lock 2>/dev/null; find /home/ubuntu/.openclaw/agents/*/sessions/ -name "*.jsonl" -mmin +120 -delete 2>/dev/null
```

### 推荐配置
```json
{
  "agents.defaults.timeoutSeconds": 120,
  "agents.defaults.compaction.reserveTokensFloor": 25000,
  "agents.defaults.compaction.keepRecentTokens": 30000,
  "models.providers.xiaomicoding.timeoutSeconds": 60
}
```
