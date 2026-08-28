#!/usr/bin/env python3
"""
auto_fixer — 自动代码修复
自动修复常见的服务器问题：配置错误、权限问题、服务异常

用法:
  python3 /opt/ttdazi/ops/auto_fixer.py scan      # 扫描可修复问题
  python3 /opt/ttdazi/ops/auto_fixer.py fix <id>   # 修复指定问题
  python3 /opt/ttdazi/ops/auto_fixer.py fix-all    # 修复所有可自动修复的问题
"""
import os
import sys
import json
import subprocess
import re
from datetime import datetime
from pathlib import Path

BASE_DIR = Path('/opt/ttdazi/ops')

def run(cmd, timeout=30):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.returncode
    except:
        return '', -1

# ═══════════════════════════════════════════
# 可修复问题检测器
# ═══════════════════════════════════════════

def check_nginx_config():
    """检查Nginx配置语法"""
    out, code = run("sudo nginx -t 2>&1")
    if code != 0:
        return {
            'id': 'nginx_config',
            'title': 'Nginx配置语法错误',
            'severity': 'critical',
            'auto_fix': True,
            'fix_cmd': 'sudo nginx -t && sudo systemctl reload nginx',
            'error': out[:200]
        }
    return None

def check_service_stuck():
    """检查服务是否卡死（CPU 100%）"""
    out, _ = run("ps aux --sort=-%cpu | head -5 | tail -4")
    issues = []
    for line in out.split('\n'):
        parts = line.split()
        if len(parts) >= 11:
            try:
                cpu = float(parts[2])
                if cpu > 95:
                    pid = parts[1]
                    cmd = ' '.join(parts[10:])[:80]
                    issues.append({
                        'id': f'stuck_{pid}',
                        'title': f'进程卡死: CPU {cpu}% (PID {pid})',
                        'severity': 'critical',
                        'auto_fix': True,
                        'fix_cmd': f'kill -9 {pid}',
                        'error': cmd
                    })
            except:
                pass
    return issues if issues else None

def check_file_permissions():
    """检查关键文件权限"""
    checks = [
        ('/etc/nginx/nginx.conf', 'www-data', 644),
        ('/opt/ttdazi/backend/app/ttdazi.log', 'ubuntu', 644),
    ]
    issues = []
    for path, expected_owner, expected_mode in checks:
        if not os.path.exists(path):
            continue
        out, _ = run(f"stat -c '%U %a' {path}")
        parts = out.split()
        if len(parts) >= 2:
            owner, mode = parts[0], parts[1]
            if mode != str(expected_mode):
                issues.append({
                    'id': f'perm_{os.path.basename(path)}',
                    'title': f'文件权限异常: {path} ({mode}→{expected_mode})',
                    'severity': 'warn',
                    'auto_fix': True,
                    'fix_cmd': f'sudo chmod {expected_mode} {path}',
                    'error': f'当前{mode}，期望{expected_mode}'
                })
    return issues if issues else None

def check_zombie_processes():
    """检查僵尸进程"""
    out, _ = run("ps aux | awk '$8 ~ /Z/ {print $2, $11}'")
    if out.strip():
        issues = []
        for line in out.strip().split('\n'):
            parts = line.split(maxsplit=1)
            if parts:
                issues.append({
                    'id': f'zombie_{parts[0]}',
                    'title': f'僵尸进程: PID {parts[0]}',
                    'severity': 'warn',
                    'auto_fix': True,
                    'fix_cmd': f'kill -9 {parts[0]}',
                    'error': parts[1] if len(parts) > 1 else 'unknown'
                })
        return issues
    return None

def check_disk_inodes():
    """检查inode使用率"""
    out, _ = run("df -i / | tail -1 | awk '{print $5}' | tr -d '%'")
    try:
        pct = int(out)
        if pct >= 80:
            return {
                'id': 'inode_full',
                'title': f'Inode使用率{pct}%（可能影响文件创建）',
                'severity': 'warn',
                'auto_fix': True,
                'fix_cmd': 'find /tmp -type f -mtime +7 -delete',
                'error': f'inode使用{pct}%'
            }
    except:
        pass
    return None

def check_ssl_cert_files():
    """检查SSL证书文件是否存在"""
    cert_dirs = [
        '/etc/letsencrypt/live/www.ttdazi.xyz',
        '/etc/letsencrypt/live/aiweb.openai2000.cn',
    ]
    issues = []
    for d in cert_dirs:
        if os.path.exists(d):
            cert_file = os.path.join(d, 'fullchain.pem')
            key_file = os.path.join(d, 'privkey.pem')
            if not os.path.exists(cert_file) or not os.path.exists(key_file):
                issues.append({
                    'id': f'ssl_missing_{os.path.basename(d)}',
                    'title': f'SSL证书文件缺失: {os.path.basename(d)}',
                    'severity': 'critical',
                    'auto_fix': False,
                    'error': f'证书或密钥文件不存在'
                })
    return issues if issues else None

# ═══════════════════════════════════════════
# 修复器
# ═══════════════════════════════════════════

def fix_issue(issue):
    """执行修复"""
    if not issue.get('auto_fix'):
        return {'status': 'skip', 'reason': '不可自动修复'}

    cmd = issue.get('fix_cmd', '')
    if not cmd:
        return {'status': 'skip', 'reason': '无修复命令'}

    out, code = run(cmd, timeout=60)
    return {
        'status': 'fixed' if code == 0 else 'failed',
        'command': cmd,
        'output': out[:200],
        'exit_code': code
    }

# ═══════════════════════════════════════════
# 扫描+修复
# ═══════════════════════════════════════════

def scan_all():
    """扫描所有可修复问题"""
    detectors = [
        check_nginx_config,
        check_service_stuck,
        check_file_permissions,
        check_zombie_processes,
        check_disk_inodes,
        check_ssl_cert_files,
    ]

    all_issues = []
    for detector in detectors:
        try:
            result = detector()
            if result:
                if isinstance(result, list):
                    all_issues.extend(result)
                else:
                    all_issues.append(result)
        except Exception as e:
            pass

    return {
        'timestamp': datetime.now().isoformat(),
        'total_issues': len(all_issues),
        'auto_fixable': len([i for i in all_issues if i.get('auto_fix')]),
        'issues': all_issues
    }

def fix_all():
    """修复所有可自动修复的问题"""
    scan = scan_all()
    results = []

    for issue in scan['issues']:
        if issue.get('auto_fix'):
            result = fix_issue(issue)
            results.append({
                'id': issue['id'],
                'title': issue['title'],
                **result
            })

    return {
        'timestamp': datetime.now().isoformat(),
        'scanned': scan['total_issues'],
        'fixed': len([r for r in results if r['status'] == 'fixed']),
        'failed': len([r for r in results if r['status'] == 'failed']),
        'results': results
    }

# ═══════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════

if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'scan'

    if cmd == 'scan':
        result = scan_all()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif cmd == 'fix' and len(sys.argv) > 2:
        # 修复指定问题
        scan = scan_all()
        for issue in scan['issues']:
            if issue['id'] == sys.argv[2]:
                result = fix_issue(issue)
                print(json.dumps({'issue': issue['title'], **result}, ensure_ascii=False, indent=2))
                break
        else:
            print(f'未找到问题: {sys.argv[2]}')
    elif cmd == 'fix-all':
        result = fix_all()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print('用法: scan | fix <id> | fix-all')
