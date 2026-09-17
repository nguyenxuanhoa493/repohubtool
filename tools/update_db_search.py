with open("files/db.py", "r", encoding="utf-8") as f:
    content = f.read()

old_func = """def search_games_fts(query_str, sys_code="ALL", limit=100, source_type="ALL"):
    if not query_str or not query_str.strip():
        return []
    conn = get_db_connection()
    cursor = conn.cursor()
    clean_q = query_str.strip().replace("'", "").replace('"', '').strip()
    like_term = f"%{clean_q}%"
    
    base_sql = "SELECT g.id, g.sys_code, g.title, g.img_url, g.region, g.genre, g.is_viet, g.is_hit, g.is_hack, g.download_count, g.rating, s.id as source_id, s.source_name, s.rom_url, s.filename, s.file_size_str FROM games g LEFT JOIN game_sources s ON s.id = (SELECT id FROM game_sources WHERE game_id = g.id AND is_alive = 1 ORDER BY priority ASC, id ASC LIMIT 1) WHERE (g.clean_title LIKE ? OR g.title LIKE ?)"
    params = [like_term, like_term]
    if sys_code != "ALL":
        base_sql += " AND g.sys_code = ?"
        params.append(sys_code)
    base_sql += _SOURCE_CLAUSE.get(source_type or "ALL", "")
    base_sql += " ORDER BY g.download_count DESC, g.title ASC LIMIT ?"
    params.append(limit)
    
    cursor.execute(base_sql, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows"""

new_func = """def search_games_fts(query_str, sys_code="ALL", limit=100, source_type="ALL", offset=0):
    if not query_str or not query_str.strip():
        return []
    conn = get_db_connection()
    cursor = conn.cursor()
    clean_q = query_str.strip().replace("'", "").replace('"', '').strip()
    like_term = f"%{clean_q}%"
    
    base_sql = "SELECT g.id, g.sys_code, g.title, g.img_url, g.region, g.genre, g.is_viet, g.is_hit, g.is_hack, g.download_count, g.rating, s.id as source_id, s.source_name, s.rom_url, s.filename, s.file_size_str FROM games g LEFT JOIN game_sources s ON s.id = (SELECT id FROM game_sources WHERE game_id = g.id AND is_alive = 1 ORDER BY priority ASC, id ASC LIMIT 1) WHERE (g.clean_title LIKE ? OR g.title LIKE ?)"
    params = [like_term, like_term]
    if sys_code != "ALL":
        base_sql += " AND g.sys_code = ?"
        params.append(sys_code)
    base_sql += _SOURCE_CLAUSE.get(source_type or "ALL", "")
    base_sql += " ORDER BY g.download_count DESC, g.title ASC LIMIT ? OFFSET ?"
    params.append(limit)
    params.append(offset)
    
    cursor.execute(base_sql, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows"""

if old_func in content:
    content = content.replace(old_func, new_func)
    with open("files/db.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Updated search_games_fts in db.py!")
else:
    print("Could not find old_func in db.py!")
