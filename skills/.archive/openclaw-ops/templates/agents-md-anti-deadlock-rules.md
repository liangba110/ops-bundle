# OpenClaw AGENTS.md 防卡死规则模板

在 AGENTS.md 末尾添加以下内容：

---

# 防卡死规则（必须遵守）

## 文件操作限制

1. **不要尝试读取/写入以下路径**（会被拒绝）：
   - /data/ops-engine/*
   - /var/www/*
   - /opt/*
   - /etc/*

2. **只能在 workspace 内操作**：
   - ~/.openclaw/workspace/
   - ~/.openclaw/workspace/.openclaw/tmp/

3. **如果遇到 Path escapes sandbox root 错误**：
   - **立即停止**，不要重试
   - 回复用户：「该操作需要服务器管理员权限，我无法执行」

4. **如果遇到 Memory flush writes are restricted 错误**：
   - **立即停止**，不要重试
   - 回复用户：「文件写入受限，请告诉我具体需求，我来指导你操作」

## 避免无限循环

- 每个工具调用失败后，最多重试 **1次**
- 连续失败 **2次**，立即停止并告知用户
- **永远不要**因为同一个错误反复尝试超过 2 次

## 超时预防

- 复杂任务拆分成多个简单步骤
- 每个步骤完成后给用户反馈
- 不要一次性执行超过 10 个工具调用
