---
name: security-hardening
description: 服务器安全加固措施集 — 密码管理/SQL注入防护/LLM白名单/IP白名单/回滚/配置统一/softapi安全
---

# 安全加固

## softapi安全审计（2026-08-29，51项修复，11轮）

### 审计方法
1. 逐文件审查 → 分类（🔴严重/🟡中等/🟢小）
2. 优先修严重 → 验证 → 同步GitHub+生产
3. **铁律：修了必须同时更新 源码+运行目录+GitHub，三处一致**

### 四轮核心修复

| 轮次 | 修复项 |
|---|---|
| 1 | JWT密钥→.env / 回调HMAC验签 / 订单号加随机 / HTTP状态码 / 密码校验 |
| 2 | DEBUG环境变量 / 密码校验调用 / 回调Token→.env / .env.example |
| 3 | Redis延迟初始化 / notify重试(指数退避) / token黑名单(Redis) / Header传参 |
| 4 | create_token支持app_id / parse_token查黑名单 / 密钥分离(GATEWAY_TOKEN/CALLBACK_SIGN_KEY) |

### 后续轮次（R9-R12）
- R9: 补全7个缺失文件(admin_api/app_crud/models)
- R10: admin_api限流+ADMIN_SECRET环境变量+app_id用secrets+密码8位+分页
- R11: app_key改secrets+require_admin改HTTPException+管理接口限流
- R12: brain.py API Key→env+JSON安全解析+engine文件锁+event_bus+SSH重连

### 安全审计清单（FastAPI项目必查）

1. **密钥管理** → JWT_SECRET/密钥是否.env？有无硬编码？
2. **认证链路** → token生成→传递→解析→鉴权，每步是否完整？
3. **输入验证** → SQL注入/XSS/密码强度/参数校验
4. **支付安全** → 回调验签(HMAC/RSA)？防重放？密钥分离？
5. **权限控制** → logout是否真正失效？RBAC？白名单？
6. **错误处理** → HTTP状态码正确？异常不泄露信息？
7. **敏感数据** → 密码哈希？日志不记密码？.env权限600？
8. **依赖安全** → Redis连接延迟初始化？连接池？超时？

### 教训
- **生产修了但没同步GitHub** → 两边不一致。修代码后必须：源码目录 + 运行目录 + GitHub
- **密钥分离** → GATEWAY_TOKEN(简单Token) vs CALLBACK_SIGN_KEY(HMAC签名)，不能混用
- **require_admin用Depends装饰器** → 不要手写if not admin，用HTTPException统一鉴权
- **app_id/app_key用secrets** → 不要用time+random，用`secrets.token_hex()`
- **密码最低8位** → 所有注册/修改密码接口统一8位+字母数字
- **限流** → 登录/注册/敏感接口必须有Redis后端限流
