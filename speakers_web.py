from flask import Flask, render_template, request
import mysql.connector
import subprocess

app = Flask(__name__)

# 数据库配置 - 远程备份配置
REMOTE_DB_CONFIG = {
    'host': '192.168.3.205',
    'user': 'root',
    'password': 'root',
    'database': 'ted_talks_db',
    'charset': 'utf8mb4'
}

# 本地Docker MySQL配置
DOCKER_CONTAINER_ID = "3cd61799063e"  # MySQL容器短ID
LOCAL_DB_CONFIG = {
    'user': 'root',
    'password': 'root',
    'database': 'ted_talks_db'
}

# 本地端口连接配置
LOCAL_PORT_CONFIG = {
    'host': 'localhost',
    'port': '3306',
    'user': 'root',
    'password': 'root',
    'database': 'ted_talks_db',
    'ssl_disabled': True
}

def get_db_connection():
    """获取MySQL数据库连接(使用本地端口方式)"""
    try:
        conn = mysql.connector.connect(**LOCAL_PORT_CONFIG)
        return conn
    except Error as e:
        print(f"本地端口连接失败: {e}")
        # 回退到Docker容器内执行方式
        print("尝试使用Docker容器内执行方式...")
        return None

def run_mysql_command(sql_command, timeout=30):
    """在容器中执行MySQL命令"""
    # 先尝试本地端口连接
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql_command)
            result = cursor.fetchall()
            # 将结果格式化为类似命令行输出的格式
            if not result:
                return ""
            output = "\t".join(result[0].keys()) + "\n"
            for row in result:
                output += "\t".join(str(v) for v in row.values()) + "\n"
            return output
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    
    # 本地端口连接失败时回退到Docker容器内执行
    mysql_cmd = f"mysql -u {LOCAL_DB_CONFIG['user']} -p{LOCAL_DB_CONFIG['password']} {LOCAL_DB_CONFIG['database']} -e \"{sql_command}\""
    docker_cmd = f"docker exec {DOCKER_CONTAINER_ID} /bin/sh -c '{mysql_cmd}'"
    print(f"Executing Docker MySQL command: {docker_cmd}")
    
    try:
        result = subprocess.run(
            docker_cmd,
            shell=True,
            check=True,
            timeout=timeout,
            capture_output=True,
            text=True
        )
        print(f"Command output: {result.stdout}")
        print(f"Command stderr: {result.stderr}")
        return result.stdout
    except subprocess.TimeoutExpired as e:
        print(f"命令执行超时: {e}")
        return None
    except subprocess.CalledProcessError as e:
        print(f"命令执行失败: {e.stderr}")
        print(f"完整错误: {e}")
        return None

# 使用本地Docker配置
db_config = None  # 强制使用Docker容器内执行方式

@app.route('/')
@app.route('/page/<int:page>')
def show_speakers(page=1):
    per_page = 100
    search_term = request.args.get('search', '')
    sort_order = request.args.get('sort', 'desc')  # 默认倒序
    
    conn = None
    try:
        # 构建基础查询
        base_query = """
            SELECT id, english_name, chinese_name, bio, year, pdf_url
            FROM speakers
            {where_clause}
            ORDER BY english_name %s
        """
        
        # 多条件搜索
        where_clause = ""
        params = []
        conditions = []
        
        english_name = request.args.get('english_name', '').strip()
        chinese_name = request.args.get('chinese_name', '').strip()
        year = request.args.get('year', '').strip()
        bio = request.args.get('bio', '').strip()
        
        if english_name:
            conditions.append("english_name LIKE %s")
            params.append(f"%{english_name}%")
        if chinese_name:
            conditions.append("chinese_name LIKE %s")
            params.append(f"%{chinese_name}%")
        if year:
            # 精确匹配年份
            conditions.append("year = %s")
            params.append(year)
        if bio:
            conditions.append("bio LIKE %s")
            params.append(f"%{bio}%")
            
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)
            
        # 日志配置
        import logging
        from datetime import datetime
        
        # 创建日志记录器
        logger = logging.getLogger('sql_logger')
        logger.setLevel(logging.DEBUG)
        
        # 创建文件处理器
        log_file = f"logs/sql_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        
        # 创建格式化器
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        # 添加处理器
        logger.addHandler(file_handler)
        
        # 记录SQL调试信息
        sort_type = request.args.get('sort', 'english_name_desc')
        logger.debug("\n=== SQL DEBUG ===")
        logger.debug(f"Base query: {base_query.format(where_clause=where_clause if where_clause else '')}")
        logger.debug(f"Where clause: {where_clause}")
        logger.debug(f"Params: {params}")
        logger.debug(f"Sort type: {sort_type}")
        logger.debug(f"Page: {page}, Per page: {per_page}")

        # 获取总记录数
        count_query = "SELECT COUNT(*) as total FROM speakers"
        if where_clause:
            count_query += " " + where_clause
            
        if db_config:  # 远程连接方式
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor(dictionary=True)
            cursor.execute(count_query, params)
            total = cursor.fetchone()['total']
        else:  # 本地Docker方式
            full_sql = count_query
            if params:
                full_sql += " WHERE " + " AND ".join(["%s"] * len(params))
                full_sql = full_sql % tuple(params)
            query_result = run_mysql_command(full_sql)
            if not query_result:
                raise Exception(f"计数查询执行失败: {query_result}\n执行的SQL: {full_sql}")
            
            # 更安全的COUNT(*)结果解析
            result_lines = query_result.strip().split('\n')
            if len(result_lines) < 2:
                raise Exception(f"无效的计数查询结果: {query_result}")
            
            try:
                total = int(result_lines[1].split('\t')[0])
            except (IndexError, ValueError) as e:
                raise Exception(f"无法解析计数结果: {e}\n原始结果:\n{query_result}")
        
        # 计算总页数
        total_pages = (total + per_page - 1) // per_page
        
        # 获取当前页数据
        offset = (page - 1) * per_page
        # 保留所有搜索条件用于翻页
        query_params = {
            'english_name': english_name,
            'chinese_name': chinese_name,
            'year': year,
            'bio': bio,
            'sort': sort_order,
            'sort_type': sort_type
        }
        
        # 确保cursor变量在两种模式下都定义
        cursor = None
        if db_config:  # 远程连接方式
            if not conn or not conn.is_connected():
                conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor(dictionary=True)
        
        query = base_query.format(where_clause=where_clause if where_clause else "")
        query += " LIMIT %s OFFSET %s"
        # 分离ORDER BY参数和WHERE条件参数
        order_direction = 'ASC' if sort_type == 'english_name_asc' else 'DESC'
        full_params = params + [order_direction, per_page, offset]
        print(f"Final query: {query}")
        print(f"Full params: {full_params}")

        # 打印完整SQL语句
        # 注意: 这里需要将ORDER BY参数放在WHERE条件参数之后
        full_query = query % tuple(params + [order_direction, per_page, offset])
        logger.debug(f"Full SQL with parameters:\n{full_query}")
        
        if db_config:  # 远程连接方式
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, full_params)
            print(f"Found {cursor.rowcount} records")
            speakers = cursor.fetchall()
            print(f"Query results: {speakers}")
        else:  # 本地Docker方式
            # 构建完整的SQL查询字符串
            full_sql = query % tuple(full_params)
            print(f"Executing Docker MySQL query: {full_sql}")
            
            # 执行查询并解析结果
            query_result = run_mysql_command(full_sql)
            if not query_result:
                raise Exception(f"查询执行失败: {query_result}")
            
            try:
                # 解析MySQL命令行输出为字典列表
                lines = query_result.strip().split('\n')
                if len(lines) < 2:
                    speakers = []
                else:
                    headers = [h.strip() for h in lines[0].split('\t')]
                    speakers = []
                    for line in lines[1:]:
                        values = [v.strip() for v in line.split('\t')]
                        speakers.append(dict(zip(headers, values)))
                
                print(f"Found {len(speakers)} records")
                print(f"Query results: {speakers}")
            except Exception as e:
                raise Exception(f"结果解析失败: {str(e)}\n原始输出:\n{query_result}")
        
        # 获取所有记录用于列表显示
        list_query = "SELECT id, english_name FROM speakers ORDER BY english_name ASC"
        if db_config:  # 远程连接方式
            cursor.execute(list_query)
            all_speakers = cursor.fetchall()
        else:  # 本地Docker方式
            query_result = run_mysql_command(list_query)
            if not query_result:
                all_speakers = []
            else:
                lines = query_result.strip().split('\n')
                if len(lines) < 2:
                    all_speakers = []
                else:
                    headers = [h.strip() for h in lines[0].split('\t')]
                    all_speakers = []
                    for line in lines[1:]:
                        values = [v.strip() for v in line.split('\t')]
                        all_speakers.append(dict(zip(headers, values)))

        return render_template('speakers.html', 
                            speakers=speakers,
                            all_speakers=all_speakers,
                            page=page,
                            per_page=per_page,
                            total_pages=total_pages,
                            sort_order=sort_order,
                            current_sort=sort_type,
                            query_params=query_params,
                            debug_sql=full_query)  # 总是传递debug_sql
        
    except (mysql.connector.Error, Exception) as err:
        error_type = "远程数据库" if db_config else "本地Docker"
        return f"""
        <h1>{error_type}连接错误</h1>
        <p>错误详情: {err}</p>
        <p>请检查:</p>
        <ul>
            <li>MySQL服务是否正在运行</li>
            <li>Docker容器是否运行(本地模式)</li>
            <li>数据库配置是否正确</li>
            <li>用户名和密码是否正确</li>
        </ul>
        """
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/talk_detail/<int:talk_id>')
def talk_detail(talk_id):
    if not talk_id:
        return "Missing talk ID", 400
    
    try:
        # 初始化conn变量
        conn = None
        cursor = None
        
        if db_config:  # 远程连接方式
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor(dictionary=True)
        
        # 查询演讲详情
        query = """
            SELECT 
                s.english_name as speaker_name_en,
                s.chinese_name as speaker_name_zh,
                s.year,
                s.pdf_url,
                t.speaker_name_zh as title_zh,
                t.content as content,
                t.content_display,
                t.page_count
            FROM speakers s
            JOIN talks t ON s.id = t.speaker_id
            WHERE s.id = %s
        """
        
        if db_config:  # 远程连接方式
            cursor.execute(query, (talk_id,))
            talk = cursor.fetchone()
        else:  # 本地Docker方式
            full_sql = query % (talk_id,)
            query_result = run_mysql_command(full_sql)
            if not query_result:
                raise Exception(f"详情查询执行失败: {query_result}")
            
            # 解析MySQL命令行输出
            lines = query_result.strip().split('\n')
            if len(lines) < 2:
                talk = None
            else:
                headers = [h.strip() for h in lines[0].split('\t')]
                values = [v.strip() for v in lines[1].split('\t')]
                talk = dict(zip(headers, values))
        
        if not talk:
            return "Talk not found", 404

        # 解析中英文内容
        content = talk['content']
        chinese_parts = []
        english_parts = []
        
        # 按行分割，奇数行中文，偶数行英文
        lines = content.split('\n')
        for i in range(0, len(lines), 2):
            if i < len(lines):
                chinese_parts.append(lines[i].strip())
            if i+1 < len(lines):
                english_parts.append(lines[i+1].strip())
        
        # 生成摘要（取前3行中文）
        summary = '\n'.join(chinese_parts[:3]) if chinese_parts else "无内容摘要"
        
        return render_template('talk_detail.html', 
                            talk=talk,
                            chinese_parts=chinese_parts,
                            english_parts=english_parts,
                            summary=summary)
        
    except (mysql.connector.Error, Exception) as err:
        error_type = "远程数据库" if db_config else "本地Docker"
        return f"""
        <h1>{error_type}连接错误</h1>
        <p>错误详情: {err}</p>
        <p>请检查:</p>
        <ul>
            <li>MySQL服务是否正在运行</li>
            <li>Docker容器是否运行(本地模式)</li>
            <li>数据库配置是否正确</li>
            <li>用户名和密码是否正确</li>
        </ul>
        """, 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050, debug=True)
