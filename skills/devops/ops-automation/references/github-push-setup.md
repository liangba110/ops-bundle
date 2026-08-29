# GitHub推送配置

## SSH方式（推荐）

```bash
# 生成密钥
ssh-keygen -t ed25519 -N '' -f ~/.ssh/github_id_ed25519

# 配置SSH
cat >> ~/.ssh/config << 'EOF'
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/github_id_ed25519
    IdentitiesOnly yes
EOF

# 验证
ssh -T git@github.com
# 返回: Hi 用户名! You've successfully authenticated
```

## Token方式

```bash
git config --global credential.helper store
echo "https://用户名:TOKEN@github.com" > ~/.git-credentials
chmod 600 ~/.git-credentials
```

## 一键部署脚本

```bash
#!/bin/bash
TOKEN="github_pat_xxx"
USER="liangba110"
git config --global user.name "$USER"
git config --global user.email "${USER}@users.noreply.github.com"
git config --global credential.helper store
echo "https://${USER}:${TOKEN}@github.com" > ~/.git-credentials
chmod 600 ~/.git-credentials
```

## 自动同步cron

```bash
# 每6小时
0 */6 * * * cd /项目路径 && git add -A && git diff --cached --quiet || git commit -m 'auto-sync' && git push 2>/dev/null
```
