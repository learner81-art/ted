from flask import Flask, render_template, request
import mysql.connector

app = Flask(__name__)

# 数据库配置
db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': 'root',
    'database': 'ted_talks_db',
    'charset': 'utf8mb4'
}

@app.route('/')
@app.route('/page/<int:page>')
def show_speakers(page=1):
    per_page = 100
    search_term = request.args.get('search', '')
    sort_order = request.args.get('sort', 'desc')  # 默认倒序
    
    # 数据库配置
    db_config = {
        'host': '127.0.0.1',
        'user': 'root',
        'password': 'root',
        'database': 'ted_talks_db',
        'charset': 'utf8mb4'
    }
    
    conn = None
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        
        # 构建基础查询
        base_query = """
            SELECT id, english_name, chinese_name, bio, year, pdf_url
            FROM speakers
            {where_clause}
            ORDER BY 
                CASE WHEN %s = 'english_name_asc' THEN english_name END ASC,
                CASE WHEN %s = 'english_name_desc' THEN english_name END DESC,
                CASE WHEN %s = 'year_asc' THEN year END ASC,
                CASE WHEN %s = 'year_desc' THEN year END DESC
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
        sort_type = request.args.get('sort_type', 'english_asc')
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
        cursor.execute(count_query, params)
        total = cursor.fetchone()['total']
        
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
        
        query = base_query.format(where_clause=where_clause if where_clause else "")
        query += " LIMIT %s OFFSET %s"
        # 分离ORDER BY参数和WHERE条件参数
        order_params = [sort_type, sort_type, sort_type, sort_type]
        full_params = params + order_params + [per_page, offset]
        print(f"Final query: {query}")
        print(f"Full params: {full_params}")

        # 打印完整SQL语句
        # 注意: 这里需要将ORDER BY参数放在WHERE条件参数之后
        full_query = query % tuple(params + order_params + [per_page, offset])
        logger.debug(f"Full SQL with parameters:\n{full_query}")
        
        cursor.execute(query, full_params)
        print(f"Found {cursor.rowcount} records")
        speakers = cursor.fetchall()
        print(f"Query results: {speakers}")  # 添加调试输出
        
        # 获取所有记录用于列表显示
        list_query = "SELECT id, english_name FROM speakers ORDER BY english_name ASC"
        cursor.execute(list_query)
        all_speakers = cursor.fetchall()

        return render_template('speakers.html', 
                            speakers=speakers,
                            all_speakers=all_speakers,
                            page=page,
                            per_page=per_page,
                            total_pages=total_pages,
                            sort_order=sort_order,
                            current_sort=sort_type,
                            query_params=query_params)
        
    except mysql.connector.Error as err:
        return f"""
        <h1>数据库连接错误</h1>
        <p>错误详情: {err}</p>
        <p>请检查:</p>
        <ul>
            <li>MySQL服务是否正在运行</li>
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
        cursor.execute(query, (talk_id,))
        talk = cursor.fetchone()
        
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
        
    except mysql.connector.Error as err:
        return f"Database error: {err}", 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
