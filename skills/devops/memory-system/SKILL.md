---
name: memory-system
description: Hermes双轨记忆系统管理
---

# 记忆系统管理

## 双轨记忆架构

| 层 | 容量 | 存储 | 用途 |
|---|---|---|---|
| Hermes记忆 | 4000字符 | ~/.hermes/memories/MEMORY.md | 高频核心，每轮注入 |
| workspace | 无限制 | ~/.hermes/workspace/*.md | 详细记录，按需读取 |

## Hermes记忆操作

```python
memory(action="add", content="新条目", target="memory")
memory(action="replace", content="新内容", old_text="旧内容", target="memory")
memory(action="remove", old_text="要删除的内容", target="memory")
```

## 容量管理
- memory_char_limit: 4000（config.yaml，从2200调大）
- user_char_limit: 2000（config.yaml，从1375调大）
- 满了→精简旧条目（缩短措辞）→腾空间→加新条目
- 详细内容放workspace，不要塞Hermes记忆
- **教训（2026-08-29）：** 容量2200时15条记忆就满了写不进去。调到4000+精简措辞后解决。精简方法：合并同类条目、用缩写、删重复。

## workspace操作

```bash
cat ~/.hermes/workspace/MEMORY.md
cat ~/.hermes/workspace/ERRORS.md
cd ~/.hermes/workspace && git add -A && git commit -m "更新" && git push b master
```
