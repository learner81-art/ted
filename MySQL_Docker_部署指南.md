# MySQL 5.7 Docker 部署完整过程

## 1. 拉取并运行MySQL容器
```bash
docker run --name mysql57 \
  -e MYSQL_ROOT_PASSWORD=my-secret-pw \
  -p 3306:3306 \
  -v /Users/a/Desktop/data/mysql_data:/var/lib/mysql \
  -d swr.cn-east-2.myhuaweicloud.com/library/mysql:5.7
```
- `--name mysql57`: 指定容器名称
- `-e MYSQL_ROOT_PASSWORD`: 设置root密码(初始可能不生效)
- `-p 3306:3306`: 端口映射
- `-v /path/to/data:/var/lib/mysql`: 数据持久化存储
- `-d`: 后台运行

## 2. 检查容器状态
```bash
docker ps | grep mysql57
```

## 3. 连接测试遇到的问题

### 3.1 初始密码连接失败
```bash
docker exec -it mysql57 mysql -uroot -pmy-secret-pw
```
报错：Access denied

### 3.2 检查容器日志
```bash 
docker logs mysql57
```
发现日志显示初始化时创建了空密码root账户

### 3.3 使用无密码连接成功
```bash
docker exec -it mysql57 mysql -uroot
```

## 4. 配置root密码和远程访问

在MySQL命令行中执行：
```sql
ALTER USER 'root'@'localhost' IDENTIFIED BY 'my-secret-pw';
GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' IDENTIFIED BY 'my-secret-pw';
FLUSH PRIVILEGES;
```

或通过单条命令：
```bash
docker exec -it mysql57 mysql -uroot -e "ALTER USER 'root'@'localhost' IDENTIFIED BY 'my-secret-pw'; GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' IDENTIFIED BY 'my-secret-pw'; FLUSH PRIVILEGES;"
```

## 5. 验证最终配置

```bash
docker exec -it mysql57 mysql -h127.0.0.1 -uroot -pmy-secret-pw -e "SHOW DATABASES;"
```

## 常见问题解决

1. **连接被拒绝**：检查是否已设置远程访问权限
2. **密码不生效**：可能需要重启容器
   ```bash
   docker stop mysql57 && docker start mysql57
   ```
3. **数据持久化**：确保挂载目录有正确权限

## 最佳实践建议

1. 使用更复杂的密码
2. 考虑创建专用用户而非使用root
3. 定期备份挂载目录中的数据
4. 生产环境建议使用MySQL 8.0+版本
