import mysql.connector
from configparser import ConfigParser
import os
import subprocess
import signal

config = ConfigParser()
config.read('config.ini')

db_config = {
    'host': config.get('database', 'host'),
    'user': config.get('database', 'user'),
    'password': config.get('database', 'password'),
    'database': config.get('database', 'database'),
    'ssl_disabled': True
}

try:
    # 查找并终止Python进程
    print("查找并终止Python进程...")
    python_processes = subprocess.check_output(["pgrep", "-f", "python"]).decode().split()
    for pid in python_processes:
        try:
            os.kill(int(pid), signal.SIGTERM)
            print(f"已终止Python进程: {pid}")
        except Exception as e:
            print(f"无法终止进程 {pid}: {e}")

    # 检查并终止MySQL连接
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SHOW PROCESSLIST")
    
    print("Active MySQL Connections:")
    print("-" * 50)
    for (id, user, host, db, command, time, state, info) in cursor:
        if time > 60:  # 显示运行超过60秒的连接
            print(f"ID: {id}, User: {user}, Host: {host}, DB: {db}")
            print(f"Time: {time}s, State: {state}, Command: {command}")
            print(f"Query: {info}")
            print("-" * 50)
            
    # 终止空闲连接
    kill_ids = []
    for (id, user, host, db, command, time, state, info) in cursor:
        if time > 60 and command == "Sleep":
            kill_ids.append(id)
            
    if kill_ids:
        print("\nTerminating idle connections:")
        for id in kill_ids:
            try:
                cursor.execute(f"KILL CONNECTION {id}")
                print(f"Successfully killed connection ID: {id}")
            except mysql.connector.Error as e:
                print(f"Failed to kill connection {id}: {e}")
                print("You may need SUPER privilege to kill connections")
    
    cursor.close()
    conn.close()
except Exception as e:
    print(f"Error checking MySQL connections: {e}")
