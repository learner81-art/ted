#!/bin/bash

# 配置参数
REMOTE_HOST="192.168.3.205"
REMOTE_USER="root"
REMOTE_PASS="root"
REMOTE_DB="ted_talks_db"
LOCAL_USER="root"
LOCAL_PASS="root"
LOCAL_DB="ted_talks_db"
DUMP_FILE="ted_dump.sql"

echo "开始迁移TED数据库..."

# 1. 从远程服务器导出数据
echo "正在从远程服务器导出数据..."
docker exec mysql57 mysqldump -h$REMOTE_HOST -u$REMOTE_USER -p$REMOTE_PASS $REMOTE_DB > $DUMP_FILE
if [ $? -ne 0 ]; then
  echo "导出失败，请检查远程连接参数"
  exit 1
fi

# 2. 在本地Docker MySQL中创建数据库
echo "正在创建本地数据库..."
docker exec -i mysql57 mysql -u$LOCAL_USER -p$LOCAL_PASS -e "CREATE DATABASE IF NOT EXISTS $LOCAL_DB;"

# 3. 导入数据到本地Docker MySQL
echo "正在导入数据到本地数据库..."
docker exec -i mysql57 mysql -u$LOCAL_USER -p$LOCAL_PASS $LOCAL_DB < $DUMP_FILE
if [ $? -ne 0 ]; then
  echo "导入失败"
  exit 1
fi

# 4. 清理临时文件
rm $DUMP_FILE

echo "数据库迁移完成！"
echo "本地连接信息:"
echo "主机: 127.0.0.1"
echo "端口: 3306"
echo "数据库: $LOCAL_DB"
echo "用户名: $LOCAL_USER"
echo "密码: $LOCAL_PASS"
