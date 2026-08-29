#!/bin/bash
# 同步skills到GitHub
cd /tmp/ops-bundle-repo
rsync -av --delete ~/.hermes/skills/ skills/ --exclude='__pycache__' --exclude='*.pyc' 2>/dev/null
git add -A
git commit -m "📝 更新skills: ops-automation安全审计+memory-system容量教训+skills铁律完善" 2>/dev/null
git push 2>&1 | tail -2