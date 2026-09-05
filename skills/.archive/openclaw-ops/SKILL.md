---
name: openclaw-ops
description: openclaw 服务器部署与运维。覆盖：openclaw 安装、配置、升级、插件管理、API 对接、故障排查。
version: 1.0.0
author: hermes
---

# OpenClaw 运维 Skill

## 触发条件
- 用户提到 openclaw、claw、E 服务器
- 部署/配置/升级 openclaw

## 服务器信息

### E 服务器（主要）
- **地址**：185.239.224.191（东京，2核3.8G/40G）
- **系统**：Ubuntu，root 密钥 SSH，fail2ban
- **用户**：openclaw（降权用户，无 sudo）
- **UI 端口**：IP:18789 / oc3385
- **域名**：E 服务器开放（国际站），openclaw 是全新个人助理（业务记忆已清空）
- **数据库**：自建库 openclaw，密码见 /etc/openclaw-db-credentials
- **站点目录**：/var/www/openclaw-sites/ + 自建库 openclaw + php8.3

### B 服务器（反代服务器）
- **地址**：82.157.202.24
- **用户**：ubuntu（有sudo）
- **OpenClaw端口**：38598
- **模型配置**：xiaomicoding/mimo-v2.5（默认）+ deepseek/deepseek-v4-flash
- **进程**：systemd用户服务（`openclaw-gateway.service`），有sudo停服务的冲突历史
- **配置文件**：/home/ubuntu/.openclaw/openclaw.json
- **Agent配置**：/home/ubuntu/.openclaw/workspace/AGENTS.md

## 关键操作

### 部署
1. SSH 到 E 服务器（root@185.239.224.191，用 ~/.ssh/id_ed25519）
2. 确认 nvm/node 版本（v22+）
3. `pnpm install && pnpm build`（如果源码目录）
4. 配置 systemd 服务（openclaw 用户运行）
5. 配置 Caddy/Nginx 反代（如有域名）

### 升级
```bash
cd /path/to/openclaw
git pull
pnpm install && pnpm build
systemctl restart openclaw
```

### 安全
- 用户 openclaw 无 sudo（降权）
- 禁碰 /var/www/ttdazi（同途搭子站点）
- fail2ban 已启用（SSH 防暴力破解）
- E 服务器安全分流：恶意 UA/路径 → 反代 D(/__guard__)，curl 必须带浏览器 UA

### 常见问题
- **openclaw 连接失败**：检查 systemd 状态、端口监听、防火墙
- **数据库连接错误**：确认 /etc/openclaw-db-credentials 密码正确
- **升级后不生效**：清缓存 + rebuild
- **B服务器systemd无限重启**（已遇）：独立进程占用端口 + systemd服务同时启动 → 冲突 → 无限重启循环（restart counter可达2000+）。修复：`sudo systemctl stop openclaw.service && sudo systemctl disable openclaw.service`
- **会话上下文溢出修复**（2026-08-31已遇）：会话历史超模型限制（155K > 150K tokens），日志出现`Context overflow: prompt too large` + `auto-compaction failed: Already compacted`。修复步骤：
  1. 备份并清理会话文件：`mv sessions/<session-id>.jsonl sessions/<session-id>.jsonl.bak`
  2. 增加compaction缓冲区：编辑`openclaw.json` → `agents.defaults.compaction.reserveTokensFloor` 设为 35000
  3. 重启gateway：`systemctl --user restart openclaw-gateway.service`
  4. 验证：重新发消息，日志中不再出现`Context overflow`
  **注意**：清理会话只删对话记录，不影响长期记忆（MEMORY.md等文件）
- **会话卡在 active_reply_work**（已遇）：MiMo API返回200但回复发送卡住，日志显示 `stuck session: reason=active_reply_work`。修复：`systemctl --user restart openclaw-gateway.service`
- **模型超时（两种错误，根因不同）**（2026-08-31已遇）：
  - **错误1：`The model did not produce a response before the model idle timeout`**
    原因：SSE流已建立但模型120秒内未返回首个事件（first-event timeout）
    日志特征：`completions HTTP stream opened but did not deliver a first SSE event within 120000ms`
    修复：增加 `models.providers.<id>.timeoutSeconds`
  - **错误2：`Request timed out before a response was generated`**
    原因：agent整体运行超时（多次API调用+compaction+工具调用总时间过长）
    日志特征：`embedded run timeout: ... timeoutMs=300000`
    修复：增加 `agents.defaults.timeoutSeconds` + 优化compaction + 清理会话
  - **推荐配置（B服务器已验证）**：
    ```json
    {
      "agents.defaults.timeoutSeconds": 120,
      "agents.defaults.compaction.reserveTokensFloor": 25000,
      "agents.defaults.compaction.keepRecentTokens": 30000,
      "models.providers.xiaomicoding.timeoutSeconds": 60
    }
    ```
    **⚠️ 用户反馈 600 秒太长，调整为 120 秒（agent）+ 60 秒（API）**
  - **排查流程**：①查日志`journalctl --user -u openclaw-gateway.service --since '10 minutes ago'` → ②确认是哪种超时 → ③调整对应配置 → ④清理会话`rm sessions/*.jsonl` → ⑤重启gateway → ⑥验证`curl localhost:38598/health`
  - **⚠️ 坑：compaction字段验证**：`maxTurns` 不是有效compaction字段，写入会导致 gateway 启动失败（exit code 78/CONFIG）。有效字段仅 `reserveTokensFloor` 和 `keepRecentTokens`。
  - **注意**：清理会话只删对话记录，不影响长期记忆（MEMORY.md等文件）

- **LLM request failed（沙箱无限循环）**（2026-08-31已遇）：
  - **现象**：反复出现 `LLM request failed`，即使超时配置正确也会超时
  - **根因**：Agent 尝试读写沙箱外的文件（如 `/data/ops-engine/*`），被拒绝后**无限重试直到耗尽超时时间**
  - **日志特征**：
    - `read failed: Path escapes sandbox root (~/.openclaw/workspace)`
    - `write failed: Memory flush writes are restricted to memory/2026-08-31.md`
    - `embedded run timeout: ... timeoutMs=600000`（即使600秒也超时）
  - **修复方案**：在 AGENTS.md 末尾添加防卡死规则（见下方模板）
  - **⚠️ 坑：不要修改 sandbox 配置**：尝试 `tools.sandbox.enabled=false` 或删除 `agents.defaults.sandbox` 都会导致 exit code 78（CONFIG错误）。正确做法是**只修改 AGENTS.md 添加行为约束**。
  - **AGENTS.md 防卡死规则模板**：
    ```
    # 防卡死规则（必须遵守）
    ## 文件操作限制
    1. 不要尝试读取/写入以下路径（会被拒绝）：/data/ops-engine/*, /var/www/*, /opt/*, /etc/*
    2. 只能在 workspace 内操作：~/.openclaw/workspace/
    3. 遇到 Path escapes sandbox root 错误 → 立即停止，不重试，回复用户"需要管理员权限"
    4. 遇到 Memory flush writes are restricted 错误 → 立即停止，回复用户具体需求
    ## 避免无限循环
    - 每个工具调用失败后最多重试 1次
    - 连续失败 2次立即停止并告知用户
    ## 超时预防
    - 复杂任务拆分成多个简单步骤
    - 不要一次性执行超过 10 个工具调用
    ```

- **会话写锁卡死（常见根因）**（2026-08-31已遇）：
  - **现象**：即使超时配置正确，仍然反复超时或卡死
  - **根因**：会话写锁被长时间持有，超过系统限制（300秒）
  - **日志特征**：`[session-write-lock] releasing lock held for 311913ms (max=300000ms)`
  - **触发场景**：用户发送复杂任务 → Agent执行大量工具调用 → 写入会话文件被阻塞 → 锁持有超时
  - **修复步骤**：
    1. 停止服务：`systemctl --user stop openclaw-gateway.service`
    2. 清理会话和锁文件：`rm -rf /home/ubuntu/.openclaw/agents/main/sessions/* /home/ubuntu/.openclaw/sessions/*`
    3. 删除所有锁文件：`find /home/ubuntu/.openclaw -name '*.lock' -delete`
    4. 启动服务：`systemctl --user start openclaw-gateway.service`
    5. 验证：`curl -s http://localhost:38598/health`

- **自动清理机制（必须配置）**：
  ```bash
  # 每小时清理锁文件和超过2小时的会话
  0 * * * * rm -f /home/ubuntu/.openclaw/agents/*/sessions/*.lock 2>/dev/null; find /home/ubuntu/.openclaw/agents/*/sessions/ -name "*.jsonl" -mmin +120 -delete 2>/dev/null
  ```

- **中文回复要求**：所有cron任务和定时推送必须用中文，在prompt末尾加"重要：所有回复必须使用中文，不要用英文。"

### B服务器OpenClaw配置
- 任务执行流程：在AGENTS.md中配置"先制定方案，确认后执行"规则（2026-08-31生效）
- AGENTS.md追加内容：任务接收→制定方案（目标/步骤/预期/风险）→等用户确认→执行→汇报结果
- 例外：纯信息查询、读取状态、用户说"直接做"可跳过确认
- **防卡死规则**（2026-08-31添加）：禁止Agent反复重试沙箱拒绝的操作，遇到Path escapes或Memory flush restricted错误立即停止（详见"LLM request failed"条目中的模板）
- **配置路径**：/home/ubuntu/.openclaw/workspace/AGENTS.md
- **验证**：`curl -s http://localhost:38598/health` → `{"ok":true,"status":"live"}`

### 参考文件
- `references/llm-request-failed-troubleshooting.md` — LLM request failed 完整排查指南
- `templates/agents-md-anti-deadlock-rules.md` — AGENTS.md 防卡死规则模板

## 注意事项
- E 服务器是海外，curl 测试必须带浏览器 UA（否则被安全分流转 D 旧版）
- openclaw 是全新个人助理，业务记忆已清空
- 可自建站 /var/www/openclaw-sites/，但禁碰 /var/www/ttdazi
