#!/usr/bin/env python3
import os
import time
import psutil
import subprocess
import time
from datetime import datetime

# 休眠检测配置
SLEEP_CHECK_INTERVAL = 300  # 5分钟检查一次
import hashlib
import socket
import logging
import re
from datetime import datetime

# 登录监控配置
AUTH_LOG = '/var/log/system.log'  # macOS系统
MAX_FAILED_ATTEMPTS = 3  # 最大允许失败登录次数
NORMAL_LOGIN_HOURS = range(8, 20)  # 正常登录时间(8:00-20:00)
TRUSTED_IPS = ['192.168.1.0/24', '10.0.0.0/8']  # 可信IP范围

# 配置日志
from logging.handlers import RotatingFileHandler

# 文件日志记录所有级别(供前端使用)
file_handler = RotatingFileHandler(
    os.path.expanduser('~/logs/system_monitor.log'),
    maxBytes=1*1024*1024,  # 1MB
    backupCount=3
)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
file_handler.setLevel(logging.INFO)

# 控制台只记录ERROR级别
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
console_handler.setLevel(logging.ERROR)

logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, console_handler]
)

# 监控配置
CHECK_INTERVAL = 60  # 检查间隔(秒)
TRUSTED_PROCESSES = ['systemd', 'bash', 'python3', 'nginx', 'Google Chrome Helper', 'rapportd', 'mDNSResponder']
TRUSTED_PORTS = [80, 443, 22, 5228, 5353, 3478, 5349]
BASELINE_FILES = {
    '/etc/passwd': None,
    '/etc/hosts': None
}

def get_file_hash(filepath):
    """计算文件哈希值"""
    try:
        with open(filepath, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception as e:
        logging.warning(f"无法计算 {filepath} 的哈希值: {str(e)}")
        return None

def init_baseline():
    """初始化基准文件哈希"""
    for filepath in BASELINE_FILES:
        BASELINE_FILES[filepath] = get_file_hash(filepath)

def check_network():
    """检查异常网络连接"""
    suspicious = []
    try:
        for conn in psutil.net_connections():
            if conn.status == 'ESTABLISHED' and conn.raddr:
                if conn.raddr.port not in TRUSTED_PORTS:
                    try:
                        suspicious.append({
                            'pid': conn.pid,
                            'local': f"{conn.laddr.ip}:{conn.laddr.port}",
                            'remote': f"{conn.raddr.ip}:{conn.raddr.port}",
                            'process': psutil.Process(conn.pid).name() if conn.pid else 'unknown'
                        })
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        suspicious.append({
                            'pid': conn.pid,
                            'local': f"{conn.laddr.ip}:{conn.laddr.port}",
                            'remote': f"{conn.raddr.ip}:{conn.raddr.port}",
                            'process': 'unknown (access denied)'
                        })
    except psutil.AccessDenied:
        logging.error("没有足够的权限检查网络连接 - 需要管理员权限")
        return []
    return suspicious

def check_processes():
    """检查可疑进程"""
    suspicious = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['name'] not in TRUSTED_PROCESSES:
                suspicious.append({
                    'pid': proc.info['pid'],
                    'name': proc.info['name'],
                    'cmd': ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                })
        except psutil.NoSuchProcess:
            continue
    return suspicious

def check_logins():
    """检查异常登录"""
    suspicious = []
    try:
        with open(AUTH_LOG, 'r') as f:
            log_lines = f.readlines()
        
        failed_attempts = {}
        for line in log_lines[-1000:]:  # 检查最近的1000行日志
            # 检查失败登录
            if 'Failed password' in line:
                ip_match = re.search(r'from (\d+\.\d+\.\d+\.\d+)', line)
                user_match = re.search(r'for (\w+)', line)
                if ip_match and user_match:
                    ip = ip_match.group(1)
                    user = user_match.group(1)
                    key = f"{user}@{ip}"
                    failed_attempts[key] = failed_attempts.get(key, 0) + 1
            
            # 检查成功登录
            if 'Accepted password' in line:
                time_match = re.search(r'(\d{2}):\d{2}:\d{2}', line)
                ip_match = re.search(r'from (\d+\.\d+\.\d+\.\d+)', line)
                user_match = re.search(r'for (\w+)', line)
                if time_match and ip_match and user_match:
                    hour = int(time_match.group(1))
                    ip = ip_match.group(1)
                    user = user_match.group(1)
                    
                    # 检查非正常时间登录
                    if hour not in NORMAL_LOGIN_HOURS:
                        suspicious.append({
                            'type': '非正常时间登录',
                            'user': user,
                            'ip': ip,
                            'time': hour
                        })
                    
                    # 检查来自不可信IP的登录
                    trusted = False
                    for trusted_ip in TRUSTED_IPS:
                        if ip.startswith(trusted_ip.split('/')[0]):
                            trusted = True
                            break
                    if not trusted:
                        suspicious.append({
                            'type': '来自不可信IP的登录',
                            'user': user,
                            'ip': ip
                        })
        
        # 检查过多失败尝试
        for key, count in failed_attempts.items():
            if count > MAX_FAILED_ATTEMPTS:
                user, ip = key.split('@')
                suspicious.append({
                    'type': '过多失败登录尝试',
                    'user': user,
                    'ip': ip,
                    'attempts': count
                })
                
    except Exception as e:
        logging.error(f"无法检查登录日志: {str(e)}")
    
    return suspicious

def check_files():
    """检查文件完整性"""
    modified = []
    for filepath, baseline_hash in BASELINE_FILES.items():
        current_hash = get_file_hash(filepath)
        if current_hash and current_hash != baseline_hash:
            modified.append(filepath)
    return modified

def check_system_resources():
    """检查系统资源使用情况"""
    resources = {
        'cpu': psutil.cpu_percent(interval=1),
        'memory': psutil.virtual_memory().percent,
        'disk': psutil.disk_usage('/').percent,
        'network': {
            'bytes_sent': psutil.net_io_counters().bytes_sent,
            'bytes_recv': psutil.net_io_counters().bytes_recv
        },
        'timestamp': datetime.now().isoformat()
    }
    return resources

def check_sleep_wake():
    """检测Mac休眠唤醒事件"""
    try:
        # 获取上次唤醒时间
        result = subprocess.run(['syslog', '-k', 'Sender', 'kernel', 
                              '-k', 'Message', 'Wake reason'],
                              capture_output=True, text=True)
        wake_logs = result.stdout.splitlines()
        
        if wake_logs:
            last_wake = wake_logs[-1]
            wake_time = datetime.strptime(last_wake.split(' ')[0], '%Y-%m-%d')
            now = datetime.now()
            
            # 检查是否在休眠期间被唤醒
            if (now - wake_time).total_seconds() < SLEEP_CHECK_INTERVAL:
                # 检查风扇状态
                temps = psutil.sensors_temperatures()
                fan_speeds = psutil.sensors_fans()
                
                if any(fan.current > 3000 for fan in fan_speeds.get('', [])):
                    return f"异常唤醒检测: {last_wake} | 风扇高速运转"
                return f"异常唤醒检测: {last_wake}"
    except Exception as e:
        return f"休眠检测错误: {str(e)}"
    return None

def run_monitor():
    init_baseline()
    # 系统监控启动(不记录日志)
    
    try:
        while True:
            # 检查休眠唤醒事件
            sleep_alert = check_sleep_wake()
            if sleep_alert:
                logging.warning(f"[休眠监控] {sleep_alert}")
            
            # 执行检查
            net_issues = check_network()
            proc_issues = check_processes()
            file_issues = check_files()
            login_issues = check_logins()
            
            # 记录发现问题
            if net_issues:
                logging.error(f"发现可疑网络连接: {net_issues}")
            if file_issues:
                logging.error(f"关键文件被修改: {file_issues}")
            if login_issues:
                logging.error(f"发现可疑登录活动: {login_issues}")
            
            time.sleep(CHECK_INTERVAL)
            
    except KeyboardInterrupt:
        # 系统监控停止(不记录日志)
        pass

def main():
    run_monitor()

if __name__ == '__main__':
    main()
