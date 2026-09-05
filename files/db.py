# -*- coding: utf-8 -*-
import os
import ctypes

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "catalog", "roms_store.sqlite3")

# ==============================================================================
# UNIVERSAL SQLITE CONNECTION (NATIVE OR CTYPES FALLBACK FOR TRIMUI LINUX)
# ==============================================================================
class CTypesSQLiteRow(dict):
    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)

class CTypesSQLiteCursor:
    def __init__(self, db_handle, lib):
        self.db_handle = db_handle
        self.lib = lib
        self.stmt_p = None
        self.col_names = []

    def execute(self, sql, params=()):
        if self.stmt_p:
            self.lib.sqlite3_finalize(self.stmt_p)
            self.stmt_p = None
            
        stmt = ctypes.c_void_p()
        sql_bytes = sql.encode('utf-8')
        rc = self.lib.sqlite3_prepare_v2(self.db_handle, sql_bytes, len(sql_bytes), ctypes.byref(stmt), None)
        if rc != 0:
            err = self.lib.sqlite3_errmsg(self.db_handle).decode('utf-8', errors='ignore')
            raise RuntimeError(f"SQLite error: {err}")
        self.stmt_p = stmt
        
        # Bind parameters
        for idx, val in enumerate(params, start=1):
            if val is None:
                self.lib.sqlite3_bind_null(self.stmt_p, idx)
            elif isinstance(val, int):
                self.lib.sqlite3_bind_int64(self.stmt_p, idx, ctypes.c_int64(val))
            elif isinstance(val, float):
                self.lib.sqlite3_bind_double(self.stmt_p, idx, ctypes.c_double(val))
            else:
                str_bytes = str(val).encode('utf-8')
                self.lib.sqlite3_bind_text(self.stmt_p, idx, str_bytes, len(str_bytes), ctypes.c_void_p(-1))

        # Retrieve column names
        n_cols = self.lib.sqlite3_column_count(self.stmt_p)
        self.col_names = [self.lib.sqlite3_column_name(self.stmt_p, i).decode('utf-8', errors='ignore') for i in range(n_cols)]

        # Statements with no result columns (INSERT/UPDATE/DELETE/DDL) are never
        # followed by a fetch call, and stepping only happens in fetchall() - so
        # without this they would be prepared, bound, and then silently discarded.
        if n_cols == 0:
            rc = self.lib.sqlite3_step(self.stmt_p)
            self.lib.sqlite3_finalize(self.stmt_p)
            self.stmt_p = None
            if rc not in (100, 101):  # SQLITE_ROW, SQLITE_DONE
                err = self.lib.sqlite3_errmsg(self.db_handle).decode('utf-8', errors='ignore')
                raise RuntimeError(f"SQLite step error: {err}")

    def fetchall(self):
        rows = []
        if not self.stmt_p:
            return rows
        while self.lib.sqlite3_step(self.stmt_p) == 100: # SQLITE_ROW
            row_data = {}
            for i, name in enumerate(self.col_names):
                col_type = self.lib.sqlite3_column_type(self.stmt_p, i)
                if col_type == 5: # SQLITE_NULL
                    row_data[name] = None
                elif col_type == 1: # SQLITE_INTEGER
                    row_data[name] = self.lib.sqlite3_column_int64(self.stmt_p, i)
                elif col_type == 2: # SQLITE_FLOAT
                    row_data[name] = self.lib.sqlite3_column_double(self.stmt_p, i)
                else:
                    txt = self.lib.sqlite3_column_text(self.stmt_p, i)
                    row_data[name] = txt.decode('utf-8', errors='ignore') if txt else ""
            rows.append(CTypesSQLiteRow(row_data))
        self.lib.sqlite3_finalize(self.stmt_p)
        self.stmt_p = None
        return rows

    def fetchone(self):
        res = self.fetchall()
        return res[0] if res else None

    def close(self):
        if self.stmt_p:
            self.lib.sqlite3_finalize(self.stmt_p)
            self.stmt_p = None

class CTypesSQLiteConnection:
    _cached_lib = None

    def __init__(self, db_path):
        if CTypesSQLiteConnection._cached_lib is None:
            lib_candidates = ['libsqlite3.so.0', '/usr/lib/libsqlite3.so.0', 'libsqlite3.dylib', 'sqlite3.dll']
            for cand in lib_candidates:
                try:
                    CTypesSQLiteConnection._cached_lib = ctypes.CDLL(cand)
                    break
                except Exception:
                    continue
            if not CTypesSQLiteConnection._cached_lib:
                raise RuntimeError("Could not load SQLite C library")

            lib = CTypesSQLiteConnection._cached_lib
            lib.sqlite3_open.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)]
            lib.sqlite3_open.restype = ctypes.c_int
            lib.sqlite3_close.argtypes = [ctypes.c_void_p]
            lib.sqlite3_close.restype = ctypes.c_int
            lib.sqlite3_prepare_v2.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_char_p)]
            lib.sqlite3_prepare_v2.restype = ctypes.c_int
            lib.sqlite3_step.argtypes = [ctypes.c_void_p]
            lib.sqlite3_step.restype = ctypes.c_int
            lib.sqlite3_column_count.argtypes = [ctypes.c_void_p]
            lib.sqlite3_column_count.restype = ctypes.c_int
            lib.sqlite3_column_name.argtypes = [ctypes.c_void_p, ctypes.c_int]
            lib.sqlite3_column_name.restype = ctypes.c_char_p
            lib.sqlite3_column_text.argtypes = [ctypes.c_void_p, ctypes.c_int]
            lib.sqlite3_column_text.restype = ctypes.c_char_p
            lib.sqlite3_column_int64.argtypes = [ctypes.c_void_p, ctypes.c_int]
            lib.sqlite3_column_int64.restype = ctypes.c_int64
            lib.sqlite3_column_double.argtypes = [ctypes.c_void_p, ctypes.c_int]
            lib.sqlite3_column_double.restype = ctypes.c_double
            lib.sqlite3_column_type.argtypes = [ctypes.c_void_p, ctypes.c_int]
            lib.sqlite3_column_type.restype = ctypes.c_int
            lib.sqlite3_finalize.argtypes = [ctypes.c_void_p]
            lib.sqlite3_finalize.restype = ctypes.c_int
            lib.sqlite3_errmsg.argtypes = [ctypes.c_void_p]
            lib.sqlite3_errmsg.restype = ctypes.c_char_p
            lib.sqlite3_bind_null.argtypes = [ctypes.c_void_p, ctypes.c_int]
            lib.sqlite3_bind_int64.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int64]
            lib.sqlite3_bind_double.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_double]
            lib.sqlite3_bind_text.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p]

        self.lib = CTypesSQLiteConnection._cached_lib
        self.db_handle = ctypes.c_void_p()
        path_bytes = db_path.encode('utf-8')
        rc = self.lib.sqlite3_open(path_bytes, ctypes.byref(self.db_handle))
        if rc != 0:
            err = self.lib.sqlite3_errmsg(self.db_handle).decode('utf-8', errors='ignore')
            raise RuntimeError(f"Failed to open SQLite db: {err}")

    def cursor(self):
        return CTypesSQLiteCursor(self.db_handle, self.lib)

    def commit(self):
        pass

    def close(self):
        if self.db_handle:
            self.lib.sqlite3_close(self.db_handle)
            self.db_handle = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False

    def __del__(self):
        """Safety net for the error path.

        Every query function closes on the way out, but only after execute()
        succeeds - a failing statement skipped the close and leaked an open
        handle on the 33MB database, and catalog.py swallows those errors so
        nothing surfaced. Refcounting frees the local as the frame unwinds,
        which closes the handle here.
        """
        try:
            self.close()
        except Exception:
            pass

_db_optimized = False

def _ensure_db_optimization(conn):
    global _db_optimized
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA cache_size = -8000") # 8MB RAM page cache
        cur.execute("PRAGMA temp_store = MEMORY")
        cur.execute("PRAGMA mmap_size = 33554432") # 32MB mmap for fast zero-copy reads
        if not _db_optimized:
            cur.execute("CREATE INDEX IF NOT EXISTS idx_games_sys_code ON games(sys_code)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_games_viet ON games(is_viet)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_games_hack ON games(is_hack)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_games_dl ON games(download_count DESC)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_games_clean_title ON games(clean_title)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_sources_lookup ON game_sources(game_id, is_alive, priority, id)")
            if hasattr(conn, "commit"):
                conn.commit()
            _db_optimized = True
        cur.close()
    except Exception:
        pass

def get_db_connection():
    try:
        import sqlite3
        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.row_factory = sqlite3.Row
    except Exception:
        conn = CTypesSQLiteConnection(DB_PATH)
    _ensure_db_optimization(conn)
    return conn

# ==============================================================================
# DATA ACCESS METHODS
# ==============================================================================
def get_source_systems_counts(source_type):
    conn = get_db_connection()
    cursor = conn.cursor()
    if source_type == "VIET":
        cursor.execute("SELECT sys_code, COUNT(*) as cnt FROM games WHERE is_viet = 1 GROUP BY sys_code ORDER BY cnt DESC")
        rows = cursor.fetchall()
        total = sum(r["cnt"] for r in rows)
        res = [("ALL", total)] + [(r["sys_code"], r["cnt"]) for r in rows]
    elif source_type == "HACK":
        cursor.execute("SELECT sys_code, COUNT(*) as cnt FROM games WHERE is_hack = 1 GROUP BY sys_code ORDER BY cnt DESC")
        rows = cursor.fetchall()
        total = sum(r["cnt"] for r in rows)
        res = [("ALL", total)] + [(r["sys_code"], r["cnt"]) for r in rows]
    elif source_type == "HITS":
        cursor.execute("SELECT sys_code, MIN(100, COUNT(*)) as cnt, MAX(download_count) as top_dl FROM games WHERE download_count > 0 GROUP BY sys_code ORDER BY top_dl DESC")
        rows = cursor.fetchall()
        res = [("ALL", 100)] + [(r["sys_code"], r["cnt"]) for r in rows]
    elif source_type == "JAVA":
        cursor.execute("SELECT sys_code, COUNT(*) as cnt FROM games WHERE sys_code = 'JAVA' GROUP BY sys_code")
        rows = cursor.fetchall()
        total = sum(r["cnt"] for r in rows)
        res = [("ALL", total)] + [(r["sys_code"], r["cnt"]) for r in rows]
    elif source_type == "ARCHIVE":
        cursor.execute("SELECT g.sys_code, COUNT(DISTINCT g.id) as cnt FROM games g JOIN game_sources s ON g.id = s.game_id WHERE s.source_name = 'ARCHIVE' AND s.is_alive = 1 GROUP BY g.sys_code ORDER BY cnt DESC")
        rows = cursor.fetchall()
        total = sum(r["cnt"] for r in rows)
        res = [("ALL", total)] + [(r["sys_code"], r["cnt"]) for r in rows]
    elif source_type == "RETROSTIC":
        cursor.execute("SELECT g.sys_code, COUNT(DISTINCT g.id) as cnt FROM games g JOIN game_sources s ON g.id = s.game_id WHERE s.source_name = 'RETROSTIC' AND s.is_alive = 1 GROUP BY g.sys_code ORDER BY cnt DESC")
        rows = cursor.fetchall()
        total = sum(r["cnt"] for r in rows)
        res = [("ALL", total)] + [(r["sys_code"], r["cnt"]) for r in rows]
    else:
        cursor.execute("SELECT sys_code, COUNT(*) as cnt FROM games GROUP BY sys_code ORDER BY cnt DESC")
        rows = cursor.fetchall()
        total = sum(r["cnt"] for r in rows)
        res = [("ALL", total)] + [(r["sys_code"], r["cnt"]) for r in rows]
        
    conn.close()
    return res

# The J2ME source groups its jars into topic folders, and that grouping only
# exists inside the filename ("category/<name>/<file>.jar"). These helpers read
# it back out so the store can offer the same shelves the source site uses.
_CAT_EXPR = ("CASE WHEN s.filename LIKE 'category/%/%' "
             "THEN substr(s.filename, 10, instr(substr(s.filename, 10), '/') - 1) "
             "ELSE '' END")

# Hai ke khong den tu thu muc cua nguon ma duoc tinh ra, va duoc ghim len dau
# danh sach. Ma cua chung bat dau bang "@" - ky tu khong the co trong ten thu muc
# mot nguon dat ra - nen khong the dung ten voi mot ke that.
CAT_TEAMOBI = "@teamobi"
CAT_GIAITRI321 = "@giaitri321"
CAT_LANDSCAPE = "@320x240"
PINNED_CATS = (CAT_TEAMOBI, CAT_GIAITRI321, CAT_LANDSCAPE)

# "Da chon" chu khong phai "co ton tai": ke 320x240 phai la nhung game that su
# tai ve ban ngang. Mot game co ban 320x240 nam lam mirror nhung mac dinh van
# tai ban doc thi de trong ke nay la noi doi voi nguoi bam vao.
_DEFAULT_SRC = ("(SELECT id FROM game_sources WHERE game_id = g.id AND is_alive = 1"
                " ORDER BY priority ASC, id ASC LIMIT 1)")
_PINNED_SQL = {
    CAT_TEAMOBI: ("EXISTS (SELECT 1 FROM game_sources WHERE game_id = g.id"
                  " AND is_alive = 1 AND (source_name IN ('TEAMOBI', 'GOMOBI')"
                  " OR filename LIKE 'category/TeaMobi/%%'))"),
    CAT_GIAITRI321: ("EXISTS (SELECT 1 FROM game_sources WHERE game_id = g.id"
                     " AND is_alive = 1 AND source_name = 'GIAITRI321')"),
    CAT_LANDSCAPE: ("EXISTS (SELECT 1 FROM game_sources WHERE id = %s"
                    " AND lower(filename) LIKE '%%320x240%%')" % _DEFAULT_SRC),
}


def get_java_categories():
    """[(category, count)] for JAVA, most populated first, with ALL on top.

    An empty category name is the bucket for jars stored without a folder."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT {_CAT_EXPR} AS cat, COUNT(DISTINCT g.id) AS cnt "
        "FROM games g JOIN game_sources s ON s.game_id = g.id "
        "WHERE g.sys_code = 'JAVA' AND s.is_alive = 1 "
        "GROUP BY cat ORDER BY cnt DESC")
    rows = cursor.fetchall()
    cursor.execute("SELECT COUNT(*) FROM games WHERE sys_code = 'JAVA'")
    total = cursor.fetchone()[0]

    # Cac ke tinh ra, ghim ngay sau ALL. Dem rieng chu khong lay tu vong group o
    # tren: chung cat ngang cac ke that chu khong phai mot ke nua trong so do.
    pinned = []
    for code in PINNED_CATS:
        cursor.execute("SELECT COUNT(*) FROM games g WHERE g.sys_code = 'JAVA'"
                       " AND " + _PINNED_SQL[code])
        cnt = cursor.fetchone()[0]
        if cnt:
            pinned.append((code, cnt))
    conn.close()
    return [("ALL", total)] + pinned + [(r["cat"], r["cnt"]) for r in rows if r["cat"] != "TeaMobi"]


def get_games_page(source_type, sys_code, sort_by="downloads", limit=None, offset=0,
                   category=None):
    """limit=None nghia la lay het. Man hinh rom_games nap ca ke roi cache lai,
    nen mot tran cung o day se lam bien mat phan duoi danh sach."""
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT g.id, g.sys_code, g.title, g.img_url, g.region, g.genre, g.is_viet, g.is_hit, g.is_hack, g.download_count, g.rating, s.id as source_id, s.source_name, s.rom_url, s.filename, s.file_size_str FROM games g LEFT JOIN game_sources s ON s.id = (SELECT id FROM game_sources WHERE game_id = g.id AND is_alive = 1 ORDER BY priority ASC, id ASC LIMIT 1) WHERE 1=1"
    params = []
    
    if source_type == "VIET":
        query += " AND g.is_viet = 1"
    elif source_type == "HACK":
        query += " AND g.is_hack = 1"
    elif source_type == "HITS":
        query += " AND g.download_count > 0"
        sort_by = "downloads"
        limit = 100 if limit is None else min(limit, 100)
    elif source_type == "JAVA":
        query += " AND g.sys_code = 'JAVA'"
    elif source_type == "ARCHIVE":
        query += " AND EXISTS (SELECT 1 FROM game_sources WHERE game_id = g.id AND source_name = 'ARCHIVE' AND is_alive = 1)"
    elif source_type == "RETROSTIC":
        query += " AND EXISTS (SELECT 1 FROM game_sources WHERE game_id = g.id AND source_name = 'RETROSTIC' AND is_alive = 1)"
        
    if sys_code != "ALL":
        query += " AND g.sys_code = ?"
        params.append(sys_code)

    if category in _PINNED_SQL:
        query += " AND " + _PINNED_SQL[category]
    elif category is not None and category != "ALL":
        if category:
            query += (" AND EXISTS (SELECT 1 FROM game_sources WHERE game_id = g.id"
                      " AND is_alive = 1 AND filename LIKE 'category/' || ? || '/%')")
            params.append(category)
        else:
            # The uncategorised shelf: jars the source stored without a folder.
            query += (" AND EXISTS (SELECT 1 FROM game_sources WHERE game_id = g.id"
                      " AND is_alive = 1 AND filename NOT LIKE 'category/%')")
        
    if sort_by == "downloads":
        query += " ORDER BY g.download_count DESC, g.title ASC LIMIT ? OFFSET ?"
    elif sort_by == "rating":
        query += " ORDER BY g.rating DESC, g.download_count DESC LIMIT ? OFFSET ?"
    else: # title / alpha / A-Z
        query += " ORDER BY g.title ASC LIMIT ? OFFSET ?"
    # SQLite coi LIMIT -1 la khong gioi han, van giu duoc OFFSET.
    params.extend([-1 if limit is None else limit, offset])
    
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_game_mirrors(game_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, source_name, rom_url, filename, file_size_str, priority FROM game_sources WHERE game_id = ? AND is_alive = 1 ORDER BY priority ASC, id ASC", (game_id,))
    mirrors = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return mirrors

# Source filters shared by the store listing and search, so both narrow a
# result set the same way.
_SOURCE_CLAUSE = {
    "VIET": " AND g.is_viet = 1",
    "HACK": " AND g.is_hack = 1",
    "HITS": " AND g.download_count > 0",
    "JAVA": " AND g.sys_code = 'JAVA'",
    "ARCHIVE": (" AND EXISTS (SELECT 1 FROM game_sources WHERE game_id = g.id"
                " AND source_name = 'ARCHIVE' AND is_alive = 1)"),
    "RETROSTIC": (" AND EXISTS (SELECT 1 FROM game_sources WHERE game_id = g.id"
                  " AND source_name = 'RETROSTIC' AND is_alive = 1)"),
}


def search_games_fts(query_str, sys_code="ALL", limit=100, source_type="ALL"):
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
    return rows

def mark_source_dead(source_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE game_sources SET is_alive = 0 WHERE id = ?", (source_id,))
    conn.commit()
    conn.close()

def update_source_file_size(source_id, file_size_str):
    if not source_id or not file_size_str:
        return
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE game_sources SET file_size_str = ? WHERE id = ?", (file_size_str, source_id))
        conn.commit()
        conn.close()
    except Exception:
        pass
