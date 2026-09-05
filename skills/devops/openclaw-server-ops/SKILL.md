---
name: openclaw-server-ops
description: OpenClaw 服务器部署与运维（Linux）。覆盖：全新安装（nvm/node/pnpm/playwright/systemd）、Gateway 服务管理、远程 Control UI 暴露、LLM provider 配置、版本升级（含迁移锁/StartLimitBurst 坑）、记忆体系搭建（MEMORY.md/技能/ClawHub 安装）、渠道配置。触发：任何"装 openclaw、openclaw 升级、openclaw 失忆、openclaw 远程访问、配 openclaw 模型/渠道/技能"类任务。用户环境：Server B(腾讯云) 与 Server E(东京 185.239.224.191) 各跑一个 openclaw 实例。
---

# OpenClaw 服务器部署与运维

## 架构速览

- 程序：pnpm 或 npm 全局安装；**2026.7.1-2 起官方 update 会装到 npm 全局**（`/root/.nvm/versions/node/v22.23.2/lib/node_modules/openclaw`），systemd 服务文件由 update 自动重写指向新路径
- Gateway：systemd **user 级**服务（`openclaw daemon install` 生成 `~/.config/systemd/user/openclaw-gateway.service`），管理命令带 `XDG_RUNTIME_DIR=/run/user/0`
- 数据目录：`~/.openclaw/`（openclaw.json 配置/token、agents/、workspace/ 记忆、sessions/ 会话日志）
- pnpm 11 全局布局：`~/.local/share/pnpm/global/v11/<hash>/node_modules/openclaw/`（旧版 pnpm 是 `global/5/.pnpm/`）

## 安装（全新服务器）

```bash
# 1. nvm + Node 22（openclaw 要求 node >=22.22.3）
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
export NVM_DIR=$HOME/.nvm; . $HOME/.nvm/nvm.sh; nvm install 22; nvm alias default 22

# 2. pnpm + openclaw
npm i -g pnpm; pnpm setup && source ~/.bashrc   # pnpm bin 不在 PATH 会报错
pnpm add -g openclaw@2026.7.1    # 与已有实例同版本

# 3. Chromium（openclaw 浏览器自动化）—— 用 openclaw 自带脚本或 playwright-core CLI
#    直接跑官方脚本（依赖齐全时）：
#    node <openclaw路径>/scripts/ensure-playwright-chromium.mjs
#    依赖没链接时（pnpm 11 常见）：找到 playwright-core 的 cli.js 再 install
CLI=$(find ~/.local/share/pnpm/store -path '*playwright-core*/cli.js' | head -1)
node $CLI install chromium && node $CLI install-deps chromium
#    产物：~/.cache/ms-playwright/chromium-1228 + headless_shell + ffmpeg

# 4. systemd 服务 + 开机自启（linger 必须，否则重启后 user 服务不启动）
openclaw daemon install        # 自动生成 token + gateway.mode=local
loginctl enable-linger root    # 关键！否则重启后 gateway 不自动拉起
export XDG_RUNTIME_DIR=/run/user/0
systemctl --user start openclaw-gateway
```

## 远程 Control UI（网页访问）

gateway 端口自带 Control UI 网页。远程访问配置（openclaw.json gateway 段）：

```bash
openclaw config set gateway.bind lan
openclaw config set gateway.port 18789
openclaw config set gateway.controlUi.basePath /<随机串>          # 防扫描
openclaw config set gateway.controlUi.allowedOrigins '["http://IP:port"]'
openclaw config set gateway.controlUi.allowInsecureAuth true
openclaw config set gateway.controlUi.dangerouslyDisableDeviceAuth true
systemctl --user restart openclaw-gateway
```

访问：`http://IP:port/basePath` → 输入 openclaw.json 里的 `gateway.auth.token` → Connect。
⚠️ 默认绑 127.0.0.1；`bind lan` 才对外暴露（裸 http + token，评估风险）。

## LLM Provider 配置（DeepSeek 实测）

```bash
# 1. 认证（stdin 管道，非交互）
echo 'sk-xxx' | openclaw models auth paste-api-key --provider deepseek

# 2. 自定义模型表（必须！否则报 "Unknown model: deepseek/deepseek-v4-flash"）
#    openclaw 内置目录不认识 v4-flash/v4-pro，需按 openai-completions 协议注册：
#    ⚠️ 每条必须带 maxTokens（不配则默认输出上限很小，写长文被截断报错，见坑速查"写长文失败"）
openclaw config set models.providers.deepseek.baseUrl https://api.deepseek.com/v1
openclaw config set models.providers.deepseek.api openai-completions
openclaw config set models.providers.deepseek.models '[{"id":"deepseek-v4-flash","name":"DeepSeek V4 Flash","maxTokens":8192},{"id":"deepseek-v4-pro","name":"DeepSeek V4 Pro","maxTokens":8192}]'
openclaw config set agents.defaults.model.primary deepseek/deepseek-v4-flash
```

实测命令：`timeout 90 openclaw agent --local --agent main -m '你好'`（必须带 `--agent` 否则报 session 选择错误）。

## 上下文自动压缩（长会话防退化，2026-08 实测）

**根因**：自定义模型条目不声明 `contextTokens` 时，openclaw 按 `resolveMemoryFlushContextWindowTokens() ?? 2e5` 回退 **200K** 计算压缩阈值——deepseek-v4-flash 实际窗口 128K，会话堆到 130K 才到阈值，模型早已退化（只输出文字不发 tool_calls）。**必须显式声明真实窗口 + 配 compaction**。

```bash
# openclaw.json 里（手改 JSON 比 config set 方便；改前 cp 备份）
"models": { "providers": { "deepseek": { "models": [
  {"id": "deepseek-v4-flash", "name": "DeepSeek V4 Flash",
   "maxTokens": 8192, "contextTokens": 131072}   # 128K 真实窗口
] } } },
"agents": { "defaults": { "compaction": {
  "mode": "default",
  "reserveTokens": 20000,          # 压缩后预留回复+工具输出空间
  "keepRecentTokens": 32000,       # 压缩后保留最近对话
  "reserveTokensFloor": 20000,     # 最小预留下限（防过度压缩）
  "recentTurnsPreserve": 3         # 最近 3 轮原文保留
} } }
```

- 配置字段确认：模型条目支持 `contextTokens`/`contextWindow`（`context-_zWLdTOu.js` 的 `resolveConfiguredProviderContextTokens` 读 `models.providers.<p>.models[].contextTokens`）；`agents.defaults.compaction.*` 见 schema（mode/reserveTokens/keepRecentTokens/reserveTokensFloor/recentTurnsPreserve/qualityGuard 等）
- 效果：会话到 ~111K（131072−20000）自动压缩历史，模型长期在舒适区
- 注意：压缩只对**后续新对话**生效，已撑爆的旧会话仍建议 New Chat
- **MiMo 模型同样适用**：xiaomicoding provider 的 mimo-v2.5-pro 等模型需同样声明 contextTokens=131072，否则同样会溢出
- **已溢出会话的恢复步骤**（compaction 失败 `Already compacted recently` 时）：
  ```bash
  # 1. 备份并清理卡住的会话
  SESSION_DIR=~/.openclaw/agents/main/sessions
  ls -lt $SESSION_DIR/*.jsonl | head -1          # 找到最大的会话文件
  mv $SESSION_DIR/<session-id>.jsonl $SESSION_DIR/<session-id>.jsonl.bak
  mv $SESSION_DIR/<session-id>.trajectory.jsonl $SESSION_DIR/<session-id>.trajectory.jsonl.bak

  # 2. 更新 compaction 配置（确保 contextTokens 已声明）
  # 见上方 openclaw.json 配置示例

  # 3. 重启 gateway
  systemctl --user restart openclaw-gateway
  ```
  验证：`journalctl --user -u openclaw-gateway -n 20` 看到 `Gateway resumed` + 无 `stuck session` 即恢复
- 验证：重启后 `journalctl --user -u openclaw-gateway | grep reload` 应见 `config change detected; evaluating reload (agents.defaults.compaction, models.providers.deepseek.models)`；再 `openclaw agent --agent main -m '回复：配置生效'` 实测

## 升级流程（含两个坑）

```bash
export XDG_RUNTIME_DIR=/run/user/0
systemctl --user stop openclaw-gateway     # 必须先停（gateway 进程树内拒绝自重启）
openclaw update
systemctl --user start openclaw-gateway
```

- **坑① 迁移锁**：update 后首次启动若被中断，报 "startup migrations are already running... retry after <时间>"——锁过期自动恢复，无残留进程时等过期即可
- **坑② StartLimitBurst**：连续失败 5 次（60s 内）systemd 停止重试 → `systemctl --user reset-failed openclaw-gateway` 后手动 start
- **CLI 版本不一致**：update 装 npm 全局，pnpm 旧版 CLI 仍在前 → `pnpm remove -g openclaw` 清理，`which openclaw` 应指向 nvm bin
- 升级后验证：`openclaw --version`、`systemctl --user status`、`curl 127.0.0.1:port/health`

## 记忆体系（解决"重启失忆"）

openclaw **不会自动写记忆**。失忆根源排查顺序：`MEMORY.md` 不存在 → `BOOTSTRAP.md` 残留（每次启动走"刚出生"）→ 记忆目录空 → session-logs 技能未启用。

```bash
# 1. 初始化长期记忆
tee ~/.openclaw/workspace/MEMORY.md   # 声明式事实：用户/环境/铁律/偏好，精简
mkdir -p ~/.openclaw/workspace/memory/daily    # 每日记忆 YYYY-MM-DD.md
rm -f ~/.openclaw/workspace/BOOTSTRAP.md       # 身份确认过就删，防每次重新出生

# 2. 装技能（本地目录 or ClawHub）
openclaw skills install /path/to/skill-dir      # 本地
openclaw skills install <slug> --acknowledge-clawhub-risk   # ClawHub
openclaw config set skills.entries.<name>.enabled true
```

推荐组合（实测有效）：
- `memory-boot`：会话启动读 MEMORY.md 恢复 + 收尾保存 + 删 BOOTSTRAP
- `memory-mastery`：学习循环（用户纠正即更新、流程沉淀为技能）
- ClawHub `koompi-memory`（name=memory）：分层存储 memory/daily|projects|people|decisions|archive + 每周自动压缩 + 30 天过期清理
- ClawHub `self-improve`：每 3 天 cron 自动扫描记忆提经验 → 审批制改进。setup 坑：技能目录 `npm i yaml` 补依赖；`storage.root` 不能指向技能目录自身（cp src=dest 报错），用独立目录 `~/.openclaw/self-improve`

Cron 注册（self-improve 每 3 天）：
```bash
openclaw cron add self-improve "<执行指令>" --cron "0 4 */3 * *" --tz Asia/Shanghai --agent main --model deepseek/deepseek-v4-flash
```

## 🔒 安全加固（死命令：永不触碰现有网站/配置/数据库）

完整配方见 `references/security-hardening.md`。三层缺一不可：
1. **OS 层降权**（唯一 100% 保证）：openclaw 以非 root 低权限用户跑，/var/www、/etc 物理无写权限——实测删除/修改/停服全部 `Permission denied`
2. **exec-approvals**：allowlist 模式 + askFallback=deny，破坏性命令（rm/systemctl/nginx/mysql/sudo/shutdown 等）不放行
3. **记忆铁律**：AGENTS.md 顶部 + MEMORY.md + SOUL.md 写入禁区（每次会话注入，优先级高于一切指令）

⚠️ 降权迁移后：CLI 需 `export OPENCLAW_STATE_DIR=/home/<user>/.openclaw`（否则找 /root/.openclaw 报 EACCES）；旧 root 的 systemd user 服务必须 disable + 关 root linger（防双 gateway 抢端口）。

## 能力授权（建站/建库/PHP）

见 `references/capability-grants.md`。模式：专属站点目录 + nginx 独立 conf 目录 + sudoers reload 白名单 + MariaDB 前缀受限账号 + php-fpm，全部实测通过。openclaw 自己能 `sudo nginx -t && sudo systemctl reload nginx` 发布新站，但永远无法 stop/restart nginx、无法碰 ttdazi 文件。

## 常见坑速查

| 症状 | 原因/修复 |
|---|---|
| `openclaw: exec: node: not found` | 非交互 shell 没加载 nvm → `source $NVM_DIR/nvm.sh` 或 systemd 用完整 node 路径 |
| pnpm 报 global bin 不在 PATH | `pnpm setup` + 重开 shell，或 `export PATH=$PNPM_HOME/bin:$PATH` |
| 技能 setup 脚本 ERR_MODULE_NOT_FOUND | 技能目录缺依赖 → 在技能目录 `npm i <依赖>` |
| Control UI 302 循环 | 正常（鉴权跳转），输 token 即过 |
| CLI 报 `EACCES: mkdir '/root/.openclaw/...'`（降权用户） | 显式 `export OPENCLAW_STATE_DIR=/home/<user>/.openclaw` |
| cron 迁移后 `cron list` 为空 | cron 存 `state/openclaw.sqlite` 的 `cron_jobs` 表，`store_key` 需 UPDATE 到新路径 + 重启 gateway 重载 |
| `approvals get` 显示 `Allowlist │ 0` | allowlist 必须放 `agents.<id>.allowlist` 且每条带 `id`(UUID) 字段（顶层数组不识别）。批量用 python 生成 JSON 后 `openclaw approvals set --file`（逐个 `allowlist add` 很慢） |
| 写长文失败：日志 `[agent/embedded] incomplete turn detected ... stopReason=length`，Control UI 报"回合不完整" | 自定义模型条目缺 `maxTokens`，openclaw 用很小的默认输出上限 → 输出被截断。诊断顺序：gateway health 正常 + 模型请求全 200 但用户报写不了 → `journalctl --user -u openclaw-gateway | grep stopReason` 看是否全 length。修复：openclaw.json 的 `models.providers.<p>.models[]` 每条补 `"maxTokens": 8192`（deepseek 实测上限 8K），改前 cp 备份，重启 gateway 后实测长文验证 |
| 重启 gateway 后立刻 `curl 127.0.0.1:port/health` 报 exit 7 | 正常：gateway 冷启动约需 10s 才绑端口，sleep 后再验（服务 active 但端口未监听 = 启动中，非故障） |
| 记忆/技能数据在 root 家目录（迁移前） | rsync 到新用户 + chown；openclaw.json 里 auth token、DeepSeek auth profile、skills entries 全在数据目录内一起迁 |
| 远程改 openclaw.json/exec-approvals.json：`ssh root@E 'python3 <<EOF ... EOF'` 报 `SyntaxError` / `bash: syntax error near unexpected token` | ssh 命令串里嵌 python heredoc + 中文/引号必崩（多层引号转义）。可靠路径：`scp` 拉到本地 → `patch`/`write_file` 改 → `scp` 传回 → 服务器上 `chown openclaw:openclaw` + `node --check`（root 无 node，用 `su -s /bin/bash openclaw -c "export PATH=/home/openclaw/.nvm/.../bin:\$PATH; node --check ..."`） |
| Control UI 里 agent 只说\\\\\\\"现在执行/现在写入\\\\\\\"却不调用任何工具（无 tool_calls，纯文本回复） | 会话上下文膨胀接近上限 → 模型退化（实测 cacheRead 130K tokens 时 deepseek-v4-flash 不再发 tool_calls）。诊断：① gateway health 正常、模型请求 200 排除配置问题 ② 看 `agents/main/sessions/<id>.jsonl` 最后几条 assistant 消息——只有 text、无 toolCall ③ 看 trajectory.jsonl `model.completed.usage.cacheRead` >10 万 = 撑爆 ④ CLI 直测工具链路：`openclaw agent --agent main -m \\\"用工具读取 <路径>\\\"`（链路正常则问题在会话侧）。临时修复：Control UI **New Chat 新开会话**。根治：给自定义模型声明真实 `contextTokens` + 配 compaction 自动压缩（见下方「上下文自动压缩」章节），否则旧会话照旧退化 |
| 不回消息、health 正常但无响应 | **双进程冲突**：独立 gateway 进程（手动启动或 pnpm 启动）+ systemd 服务同时运行，抢同一个端口。systemd 每次启动失败（exit 78: "gateway already running"），无限重启循环（restart counter 可达几千次）。诊断：`journalctl --user -u openclaw-gateway \| grep "already running"` 或 `ss -tlnp \| grep <port>` 看到两个进程。修复：`systemctl --user stop openclaw-gateway` + `kill <独立进程pid>`，然后只保留一种启动方式。**永远不要同时用两种方式启动 gateway**。⚠️ 降权迁移后旧 root 的 systemd user 服务必须 disable + 关 root linger（防双 gateway 抢端口） |
| 会话卡住（stuck session） | 日志出现 `stuck session recovery outcome: status=skipped`，gateway 进程正常但不处理新消息。修复：重启 gateway `systemctl --user restart openclaw-gateway`。 |
| 会话写锁卡死 | 日志 `releasing lock held for 311913ms (max=300000ms)`。修复：stop → rm sessions/*.jsonl + *.lock → start |
| 会话文件过大导致内存紧张 | `ls -lh ~/.openclaw/agents/*/sessions/*.trajectory.jsonl` 发现 >10MB 文件。根因：未声明 `contextTokens` 导致会话无限膨胀。修复：① 备份大会话 `mkdir backup_$(date +%Y%m%d) && mv *.jsonl backup/` ② 为模型声明 `contextTokens: 131072` + 配 compaction ③ 重启 gateway。验证：`free -h` 确认可用内存回升 |
| 模型超时（两种） | ① first-event timeout (SSE 120s 无事件) → 增 `models.providers.<id>.timeoutSeconds`；② agent 整体超时 (300s) → 增 `agents.defaults.timeoutSeconds` + 清理会话 |
| LLM request failed（沙箱无限循环） | Agent 读写沙箱外文件被拒后无限重试。修复：AGENTS.md 添加防卡死规则（遇 Path escapes 立即停止，最多重试1次） |
| `maxTurns` 写入 compaction 致 gateway 启动失败 | `maxTurns` 不是有效字段。有效：`reserveTokensFloor`、`keepRecentTokens` |

## 现有实例参考

| 实例 | 服务器 | 运行用户 | Gateway 端口 | 数据目录 |
|---|---|---|---|---|
| B | 82.157.202.24（腾讯云） | ubuntu | 38598（0.0.0.0） | /home/ubuntu/.openclaw |
| E | 185.239.224.191（东京） | openclaw（降权） | 18789（127.0.0.1） | /home/openclaw/.openclaw |

B 模型：xiaomicoding/mimo-v2.5（默认）+ deepseek/deepseek-v4-flash。推荐 compaction：`timeoutSeconds: 120`、`reserveTokensFloor: 25000`、`keepRecentTokens: 30000`。

### 自动清理机制
```bash
0 * * * * rm -f /home/ubuntu/.openclaw/agents/*/sessions/*.lock 2>/dev/null; find /home/ubuntu/.openclaw/agents/*/sessions/ -name "*.jsonl" -mmin +120 -delete 2>/dev/null
```

### AGENTS.md 防卡死规则
Agent 尝试读写沙箱外文件被拒后无限重试 → 在 AGENTS.md 添加：遇 `Path escapes sandbox root` 立即停止不重试；每个工具调用失败最多重试1次；连续失败2次立即停止。详见 `references/`。

## AGENTS.md 配置（系统提示 + 行为规则）

AGENTS.md 是 openclaw 的**系统提示文件**，每次会话自动注入，优先级最高。

### ⚠️ 铁律：不要在 openclaw.json 里加 systemPrompt

`agents.defaults.systemPrompt` 字段**不存在/无效**，会导致 gateway 启动失败：
```
Gateway failed to start: Invalid config at openclaw.json:
agents.defaults: Invalid input
```
**所有系统提示必须写在 AGENTS.md 里。**

### 添加方式（远程服务器）
```bash
python3 /opt/ttdazi/ops/remote_ops.py exec 'python3 << '\''PYEOF'\''
with open("/home/ubuntu/.openclaw/workspace/AGENTS.md") as f:
    content = f.read()
# 在文件开头插入（最高优先级）
content = "你的规则内容\n\n---\n\n" + content
with open("/home/ubuntu/.openclaw/workspace/AGENTS.md", "w") as f:
    f.write(content)
PYEOF' B
```

### 任务执行流程配置

用户要求 openclaw 接收任务时先制定方案，确认后再执行：

```markdown
## 任务执行流程

**所有任务必须先制定方案，用户确认后才可执行。**

### 流程
1. 接收任务 → 分析需求
2. 制定方案 → 输出任务目标、执行步骤、预期结果、可能风险
3. 等待确认 → 用户说确认/执行/同意后才动
4. 执行任务 → 按方案逐步执行
5. 汇报结果 → 执行完成后反馈

### 例外（可直接执行）
- 纯信息查询（天气、时间、计算）
- 读取文件/状态检查
- 用户明确说直接做/不用确认
```

### 强制中文输出配置

MiMo 模型的内部推理是英文，会泄漏到回复中。在 AGENTS.md **文件开头**添加（最高优先级）：

```markdown
# 🚨 最高铁律（每次会话必须遵守）

**你是一个中文AI助手。绝对禁止输出任何英文内容。**

## 强制规则（违反=严重错误）

1. **所有回复必须100%中文**
2. **禁止显示任何英文**（包括思考过程、推理过程、内部想法）
3. **禁止出现以下英文内容**：
   - "The user said..." → 不要出现
   - "Actually..." → 不要出现
   - "Let me..." → 不要出现
   - "OK" → 用"好的"
   - "Yes/No" → 用"是/否"
4. **技术术语用中文**：服务器、数据库、端口、配置
5. **代码和命令保持原样**（不翻译代码本身）

## 回复格式

✅ 正确示例：
- "好的，我来帮你检查服务器状态"
- "数据库连接正常，端口3306监听中"

❌ 错误示例（禁止出现）：
- "OK, let me check" ❌
- "The user said '好的'..." ❌
```

**关键点：必须放在文件开头（`#` 标题之前），否则优先级不够。**

## 参考

- `references/e-server-setup.md` — Server E 实际实例参数（端口/basePath/服务名/已装技能/降权用户/能力授权）
- `references/security-hardening.md` — 安全加固完整配方（降权迁移 + exec-approvals + sudoers 白名单 + 记忆铁律）
- `references/capability-grants.md` — 授权 openclaw 建站/建库/跑 PHP 的隔离模式与边界验证清单
- `references/e-tools-blog-publishing.md` — E 上 TOOLS 工具箱站（tools.ttdazi.xyz:8099）文章发布工作流：模板结构/素材命名/发布步骤/验证清单
