#!/usr/bin/env python3
"""
event_bus.py — 简易事件总线
模块间通信：写入事件文件，其他模块轮询读取
"""
import json
import os
from pathlib import Path
from datetime import datetime

EVENTS_DIR = Path(os.environ.get('OPS_DIR', '/opt/ttdazi/ops')) / 'data' / 'events'
EVENTS_DIR.mkdir(parents=True, exist_ok=True)

def emit(event_type, data):
    """发布事件"""
    event = {
        'timestamp': datetime.now().isoformat(),
        'type': event_type,
        'data': data
    }
    event_file = EVENTS_DIR / f"{event_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    event_file.write_text(json.dumps(event, ensure_ascii=False))

def consume(event_type=None, since=None):
    """消费事件"""
    events = []
    for f in sorted(EVENTS_DIR.glob('*.json')):
        try:
            event = json.loads(f.read_text())
            if event_type and event.get('type') != event_type:
                continue
            if since and event.get('timestamp', '') < since:
                continue
            events.append(event)
        except:
            pass
    return events

def clear_old(hours=24):
    """清理旧事件"""
    cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
    for f in EVENTS_DIR.glob('*.json'):
        try:
            event = json.loads(f.read_text())
            if event.get('timestamp', '') < cutoff:
                f.unlink()
        except:
            pass
