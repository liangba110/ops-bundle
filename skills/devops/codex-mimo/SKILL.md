---
name: codex-mimo
description: Codex CLI + MiMo 配置与调度模式。所有代码任务由Codex执行，Hermes调度反馈。
tags: [codex, mimo, devops, dispatch]
triggers: [codex, 代码修复, 代码审查, 写代码, codex修复, 初始化数据库, 全面测试]
---

# Codex CLI + MiMo 配置与调度

## 调度模式（铁律）

**所有代码相关任务由 Codex 执行，Hermes 负责调度和反馈结果。** Hermes 不手写代码。

流程：
1. 诊断问题（Hermes做）
2. 构造清晰的 Codex prompt（包含目录、上下文、预期输出）
3. 执行 `codex exec` 并等待结果
4. 解析输出，向用户反馈关键信息（去噪，不贴原始日志）

## 配置文件
```toml
# ~/.codex/config.toml
model = "mimo-v2.5-pro"
model_provider = "mimo"
web_search = "disabled"

[model_providers.mimo]
name = "MiMo"
base_url = "https://token-plan-cn.xiaomimimo.com/v1"
wire_api = "responses"
env_key = "OPENAI_API_KEY"
```

## 环境变量
```bash
export OPENAI_BASE_URL="https://token-plan-cn.xiaomimimo.com/v1"
export OPENAI_API_KEY="tp-c2hcz66we5sd0xbpgeuqf0vjqvyq1ix2wsyvdpve7ktv2wj8"
```

## 使用
```bash
# 基本对话
codex exec -m mimo-v2.5-pro "你的问题"

# 代码审查/修复（需绕过沙箱）
codex exec -m mimo-v2.5-pro --dangerously-bypass-approvals-and-sandbox "任务描述"

# 全面测试（构造结构化prompt，要求输出表格）
codex exec -m mimo-v2.5-pro --dangerously-bypass-approvals-and-sandbox "
任务：全面测试xxx。
目录：/opt/ttdazi/ops/
对每个测试：记录是否成功、关键信息、失败原因。
最后输出完整测试报告表格。
"
```

## Prompt 构造要点
- 明确工作目录
- 给出数据库配置（MySQL root@localhost, 密码huizhiyun2026, 库名huizhiyun）
- 说明当前状态（哪些模块已初始化、哪些缺失）
- 要求结构化输出（表格）方便解析
- 如果是初始化任务，说明预期的表结构和验证方式

## 注意
- 必须设置web_search = "disabled"（MiMo不支持）
- 必须设置env_key（否则API Key不附带）
- 沙箱需用--dangerously-bypass-approvals-and-sandbox绕过
- 输出日志很长，只提取关键结果反馈给用户，不要贴原始日志

## 安全铁律

**重要数据清理前必须：**
1. 先备份到 `/data/disk/important_backup/` 目录
2. 经用户确认后才执行清理

brain.py 等运维脚本中的清理操作必须遵守此规则。

## 常见坑

| 坑 | 原因 | 修复 |
|---|---|---|
| HTTP Error 401: Unauthorized | 运维脚本用MIMO_API_KEY，但环境变量是OPENAI_API_KEY | 脚本中加fallback：`os.environ.get('MIMO_API_KEY', '') or os.environ.get('OPENAI_API_KEY', '')` |
| Codex输出很长但无有用信息 | MiMo返回大量debug日志 | 只提取最后的json/table结果，过滤opentelemetry日志 |
