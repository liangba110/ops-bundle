# Python API Security Audit Pattern

## softapi实测四轮修复 (2026-08-29)

| 轮次 | 焦点 | 典型问题 |
|---|---|---|
| 1 | 核心安全机制 | JWT密钥/回调验签/密码哈希/SQL注入 |
| 2 | 配置管理 | DEBUG/环境变量/.env.example |
| 3 | 架构优化 | Redis延迟初始化/重试机制/黑名单/Header传参 |
| 4 | 完整性 | 鉴权链路/密钥分离/分页/限流 |

## 逐文件审查清单

```bash
grep -rn "secret\|password\|token\|key.*=" app/ --include="*.py" | grep -v "os.getenv\|env_file"
grep -rn "status_code=200" app/ --include="*.py"
grep -rn "min_length" app/schemas/
grep -rn "parse_token\|create_token" app/ --include="*.py"
```

## 常见漏洞模式

| 模式 | 修复 |
|---|---|
| `JWT_SECRET = "xxx"` | `os.getenv("JWT_SECRET")` |
| `if token != "xxx"` | HMAC-SHA256签名 |
| `status_code=200` for errors | 返回正确状态码 |
| `def f(token: str)` | 改Header |
| `random.randint()` | `secrets.token_hex()` |
| 模块级 `r = redis.Redis()` | 延迟初始化 |
| 无分页 | page/page_size参数 |

## 密钥分离原则

- `GATEWAY_TOKEN` — 简单Token认证
- `CALLBACK_SIGN_KEY` — HMAC-SHA256签名
- `JWT_SECRET` — JWT签名
- `DB_PASSWORD` — 数据库密码

**不同用途的密钥必须用不同环境变量，不能混用。**

## GitHub同步铁律

修代码后必须同步三处：源码 + 运行目录 + GitHub
