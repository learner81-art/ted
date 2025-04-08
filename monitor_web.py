#!/usr/bin/env python3
from flask import Flask, render_template, jsonify
import json
from datetime import datetime, timedelta
import os

app = Flask(__name__)

# 监控日志文件路径
LOG_FILE = 'system_monitor.log'

def parse_logs():
    """解析监控日志文件"""
    resources = []
    alerts = []
    
    if not os.path.exists(LOG_FILE):
        return {'resources': [], 'alerts': []}
    
    with open(LOG_FILE, 'r') as f:
        for line in f:
            if '系统资源使用情况' in line:
                try:
                    log_time = datetime.strptime(line.split(' - ')[0], '%Y-%m-%d %H:%M:%S,%f')
                    json_str = line.split('系统资源使用情况: ')[1].strip()
                    data = json.loads(json_str)
                    data['time'] = log_time.strftime('%H:%M:%S')
                    resources.append(data)
                except:
                    continue
            elif 'WARNING' in line:
                alert_time = datetime.strptime(line.split(' - ')[0], '%Y-%m-%d %H:%M:%S,%f')
                message = line.split(' - ')[-1].strip()
                alerts.append({
                    'time': alert_time.strftime('%H:%M:%S'),
                    'message': message
                })
    
    # 只保留最近1小时的数据
    one_hour_ago = datetime.now() - timedelta(hours=1)
    resources = [r for r in resources if datetime.strptime(r['time'], '%H:%M:%S') > one_hour_ago]
    alerts = alerts[-20:]  # 最多显示20条最新告警
    
    return {
        'resources': resources[-60:],  # 最多显示60个数据点
        'alerts': alerts
    }

@app.route('/')
def dashboard():
    return render_template('monitor.html')

@app.route('/api/data')
def get_data():
    return jsonify(parse_logs())

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=5000, help='Port to run the server on')
    args = parser.parse_args()
    app.run(host='0.0.0.0', port=args.port, debug=True)
