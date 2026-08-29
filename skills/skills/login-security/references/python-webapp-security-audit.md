# Python Web App Security Audit Patterns

## 快速审计清单

### 1. 缺失文件检测
```bash
for f in $(find /opt/项目/app -name "*.py" -not -path "*/venv/*"); do
    rel=${f#/opt/项目/}
    [ ! -f "repo/$rel" ] && echo "缺失: $rel"
done
```

### 2. 硬编码密钥扫描
```bash
grep -rn "SECRET\|PASSWORD\|API_KEY" app/ --include="*.py" | grep -v "os.getenv\|settings\.\|\.env"
```

### 3. SQL注入检测
```bash
grep -rn "f\".*SELECT\|f\".*INSERT" app/ --include="*.py" | grep -v "cursor.execute"
```

### 4. DEBUG模式检查
```bash
grep -n "DEBUG.*=.*True" app/config/settings.py
```

### 5. Token位置检查
```bash
grep -n "token.*:.*str" app/api/*.py  # 应在Header不在URL参数
```

## 常见漏洞模式

| 漏洞 | 检测 | 修复 |
|---|---|---|
| JWT密钥硬编码 | grep JWT_SECRET | 移到.env |
| 回调无验签 | grep callback | 加HMAC验签 |
| 密码校验未调用 | grep check_password | 在register中调用 |
| logout空操作 | grep -A3 def logout | 加token黑名单 |
| 无分页 | grep .all() crud | 加.limit() |
| 全局redis连接 | grep redis.Redis( | 改函数内连接 |
| 异常返回200 | grep status_code=200 | 改为500/400 |
