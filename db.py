"""
数据库抽象层 - 支持 Supabase (Postgres) 和本地 SQLite

优先级：
1. 如果 Streamlit secrets 或环境变量中配置了 SUPABASE_URL + SUPABASE_KEY → 使用 Supabase
2. 否则 fallback 到本地 SQLite（用于本地开发测试）

Supabase 建表 SQL 见 init_supabase_tables() 函数
"""
import os
import json
import uuid
import hashlib
from datetime import datetime

# ========== 检测后端类型 ==========
BACKEND = "sqlite"  # 默认
supabase_client = None
_supabase_ready = False

try:
    # 尝试从 Streamlit secrets 读取
    import streamlit as st
    _secrets_url = None
    _secrets_key = None
    try:
        _secrets_url = st.secrets.get("SUPABASE_URL") or st.secrets.get("supabase_url")
        _secrets_key = st.secrets.get("SUPABASE_KEY") or st.secrets.get("supabase_key")
    except Exception:
        pass
    
    # 尝试环境变量
    _env_url = os.environ.get("SUPABASE_URL")
    _env_key = os.environ.get("SUPABASE_KEY")
    
    url = _secrets_url or _env_url
    key = _secrets_key or _env_key
    
    if url and key:
        try:
            from supabase import create_client
            # 容错：去掉多余的空格、结尾斜杠和 /rest/v1 后缀（create_client 只接受项目根地址）
            url = url.strip().rstrip("/")
            if url.endswith("/rest/v1"):
                url = url[: -len("/rest/v1")].rstrip("/")
            supabase_client = create_client(url, key)
            _supabase_ready = True
            BACKEND = "supabase"
            print(f"[DB] Supabase connected: {url[:30]}...")
        except ImportError:
            print("[DB] supabase-py not installed, falling back to SQLite")
        except Exception as e:
            print(f"[DB] Supabase connection failed: {e}, falling back to SQLite")
except Exception:
    pass

print(f"[DB] Backend: {BACKEND}")

# ========== SQLite fallback ==========
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "survey.db")

def _get_sqlite_conn():
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

# ========== 时间戳工具 ==========
def _now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def _gen_id():
    return str(uuid.uuid4())[:8].upper() + datetime.now().strftime('%H%M%S')

def _gen_token():
    return uuid.uuid4().hex[:16]

def _hash_pwd(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

def _json_or_none(val):
    if val is None:
        return None
    if isinstance(val, str):
        return val
    return json.dumps(val, ensure_ascii=False)

def _parse_json(val):
    if val is None:
        return None
    if isinstance(val, (list, dict)):
        return val
    try:
        return json.loads(val)
    except Exception:
        return val

# ============================================================
# SUPABASE 建表 SQL（Postgres 语法）
# 用户在 Supabase SQL Editor 中执行一次即可
# ============================================================
SUPABASE_INIT_SQL = """
-- 专家答卷表
CREATE TABLE IF NOT EXISTS expert_responses (
    response_id TEXT PRIMARY KEY,
    resume_token TEXT UNIQUE,
    expert_number TEXT,
    expert_name TEXT,
    work_unit_type TEXT,
    profession TEXT,
    title TEXT,
    work_years TEXT,
    has_mongolia_experience TEXT,
    familiarity TEXT,
    judgment_basis JSONB DEFAULT '{}',
    structure_reviews JSONB DEFAULT '[]',
    indicator_ratings JSONB DEFAULT '[]',
    supplementary_indicators JSONB DEFAULT '[]',
    overall_opinion TEXT,
    status TEXT DEFAULT 'draft',
    current_page INTEGER DEFAULT 1,
    progress_percent REAL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    submitted_at TIMESTAMPTZ
);

-- 问卷配置表（单行）
CREATE TABLE IF NOT EXISTS survey_config (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    survey_open INTEGER DEFAULT 1,
    current_version TEXT,
    admin_password TEXT
);
INSERT INTO survey_config (id, survey_open, current_version) VALUES (1, 1, 'v1.0')
ON CONFLICT (id) DO NOTHING;

-- 管理员表
CREATE TABLE IF NOT EXISTS admins (
    username TEXT PRIMARY KEY,
    password_hash TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- RLS: 允许匿名插入新答卷（public）
-- 允许匿名读取自己的答卷（通过 resume_token 或 response_id）
-- 管理员接口在后端验证，前端不应直接访问 admins 表
-- 可在 Supabase Dashboard > Authentication > Settings 关闭 email confirmation 简化流程

-- 或者直接暂时禁用 RLS（开发阶段）：
-- ALTER TABLE expert_responses DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE survey_config DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE admins DISABLE ROW LEVEL SECURITY;
"""

def get_init_sql():
    """返回 Supabase 初始化 SQL"""
    return SUPABASE_INIT_SQL

# ============================================================
# 初始化
# ============================================================
def init_db():
    """初始化数据库（自动创建表）"""
    if BACKEND == "supabase" and _supabase_ready:
        # Supabase: 检查表是否存在（通过一次简单查询）
        try:
            resp = supabase_client.table("survey_config").select("id").limit(1).execute()
        except Exception as e:
            # 表不存在 → 需要用户执行 SQL
            print(f"[DB] Supabase 表未就绪，请在 SQL Editor 执行 init_supabase_tables() 中的 SQL: {e}")
    else:
        # SQLite: 自动建表
        conn = _get_sqlite_conn()
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS expert_responses (
            response_id TEXT PRIMARY KEY, resume_token TEXT UNIQUE,
            expert_number TEXT, expert_name TEXT, work_unit_type TEXT, profession TEXT,
            title TEXT, work_years TEXT, has_mongolia_experience TEXT, familiarity TEXT,
            judgment_basis TEXT, structure_reviews TEXT, indicator_ratings TEXT,
            supplementary_indicators TEXT, overall_opinion TEXT,
            status TEXT DEFAULT 'draft', current_page INTEGER DEFAULT 1,
            progress_percent REAL DEFAULT 0, created_at TEXT, updated_at TEXT, submitted_at TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS survey_config (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            survey_open INTEGER DEFAULT 1, current_version TEXT, admin_password TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS admins (
            username TEXT PRIMARY KEY, password_hash TEXT, created_at TEXT
        )''')
        c.execute("INSERT OR IGNORE INTO survey_config (id, survey_open, current_version) VALUES (1, 1, 'v1.0')")
        conn.commit()
        conn.close()

init_db()

# ============================================================
# 公共函数
# ============================================================
def _row_to_dict(row, backend=None):
    """统一转换行数据为 dict，自动处理 JSON 字段"""
    if backend is None:
        backend = BACKEND
    
    if backend == "supabase":
        # Supabase 返回的是 dict，JSONB 已自动解析
        data = dict(row) if not isinstance(row, dict) else row
    else:
        data = dict(row)
    
    for key in ['structure_reviews', 'indicator_ratings', 'judgment_basis', 'supplementary_indicators']:
        if key in data:
            data[key] = _parse_json(data[key])
    
    return data

def create_or_get_response(response_id=None, resume_token=None):
    """创建新答卷或通过令牌恢复"""
    now = _now()
    
    if BACKEND == "supabase" and _supabase_ready:
        # 1. 优先按 resume_token 恢复
        if resume_token:
            try:
                resp = supabase_client.table("expert_responses").select("*").eq("resume_token", resume_token).limit(1).execute()
                if resp.data and len(resp.data) > 0:
                    return _row_to_dict(resp.data[0])
            except Exception as e:
                print(f"[DB] resume_token 查询失败: {e}")
        
        # 2. 按 response_id 恢复
        if response_id:
            try:
                resp = supabase_client.table("expert_responses").select("*").eq("response_id", response_id).limit(1).execute()
                if resp.data and len(resp.data) > 0:
                    return _row_to_dict(resp.data[0])
            except Exception as e:
                print(f"[DB] response_id 查询失败: {e}")
        
        # 3. 创建新答卷
        new_id = _gen_id()
        new_token = _gen_token()
        try:
            supabase_client.table("expert_responses").insert({
                "response_id": new_id,
                "resume_token": new_token,
                "status": "draft",
                "created_at": now,
                "updated_at": now,
                "judgment_basis": {},
                "structure_reviews": [],
                "indicator_ratings": [],
                "supplementary_indicators": []
            }).execute()
        except Exception as e:
            print(f"[DB] Supabase 插入失败: message={e}")
            raise
        
        return {
            "response_id": new_id,
            "resume_token": new_token,
            "status": "draft",
            "created_at": now,
            "updated_at": now
        }
    
    else:
        # SQLite
        conn = _get_sqlite_conn()
        c = conn.cursor()
        
        if resume_token:
            c.execute("SELECT * FROM expert_responses WHERE resume_token = ?", (resume_token,))
            row = c.fetchone()
            if row:
                conn.close()
                return _row_to_dict(row, "sqlite")
        
        if response_id:
            c.execute("SELECT * FROM expert_responses WHERE response_id = ?", (response_id,))
            row = c.fetchone()
            if row:
                conn.close()
                return _row_to_dict(row, "sqlite")
        
        new_id = _gen_id()
        new_token = _gen_token()
        c.execute('''INSERT INTO expert_responses 
            (response_id, resume_token, status, created_at, updated_at)
            VALUES (?, ?, 'draft', ?, ?)''', (new_id, new_token, now, now))
        conn.commit()
        conn.close()
        
        return {"response_id": new_id, "resume_token": new_token, "status": "draft", 
                "created_at": now, "updated_at": now}

def save_response(response_id, data):
    """保存答卷数据（upsert）"""
    data = dict(data)
    data['updated_at'] = _now()
    
    if BACKEND == "supabase" and _supabase_ready:
        # 字段映射：Python dict → Supabase row
        row = {}
        json_fields = {'judgment_basis', 'structure_reviews', 'indicator_ratings', 'supplementary_indicators'}
        for k, v in data.items():
            if k in json_fields:
                row[k] = v if isinstance(v, (list, dict)) else json.loads(v) if v else []
            else:
                row[k] = v
        
        try:
            supabase_client.table("expert_responses").update(row).eq("response_id", response_id).execute()
        except Exception as e:
            print(f"[DB] Supabase update 失败: message={e}, row_keys={list(row.keys())}")
            raise
    else:
        conn = _get_sqlite_conn()
        c = conn.cursor()
        fields = []
        values = []
        json_fields = {'judgment_basis', 'structure_reviews', 'indicator_ratings', 'supplementary_indicators'}
        for k, v in data.items():
            fields.append(f"{k} = ?")
            values.append(json.dumps(v, ensure_ascii=False) if k in json_fields else v)
        values.append(response_id)
        c.execute(f"UPDATE expert_responses SET {', '.join(fields)} WHERE response_id = ?", values)
        conn.commit()
        conn.close()

def get_response(response_id):
    """获取单份答卷"""
    if BACKEND == "supabase" and _supabase_ready:
        try:
            resp = supabase_client.table("expert_responses").select("*").eq("response_id", response_id).limit(1).execute()
            if resp.data:
                return _row_to_dict(resp.data[0])
        except Exception as e:
            print(f"[DB] Supabase get 失败: {e}")
        return None
    else:
        conn = _get_sqlite_conn()
        c = conn.cursor()
        c.execute("SELECT * FROM expert_responses WHERE response_id = ?", (response_id,))
        row = c.fetchone()
        conn.close()
        return _row_to_dict(row, "sqlite") if row else None

def submit_response(response_id):
    """正式提交"""
    now = _now()
    if BACKEND == "supabase" and _supabase_ready:
        try:
            supabase_client.table("expert_responses").update({
                "status": "submitted", "submitted_at": now, "updated_at": now
            }).eq("response_id", response_id).execute()
        except Exception as e:
            print(f"[DB] Supabase submit 失败: {e}")
            raise
    else:
        conn = _get_sqlite_conn()
        c = conn.cursor()
        c.execute("UPDATE expert_responses SET status='submitted', submitted_at=?, updated_at=? WHERE response_id=?", 
                  (now, now, response_id))
        conn.commit()
        conn.close()

def get_all_responses(status=None):
    """获取答卷列表"""
    cols = "response_id, expert_number, expert_name, work_unit_type, profession, familiarity, status, progress_percent, created_at, updated_at, submitted_at"
    
    if BACKEND == "supabase" and _supabase_ready:
        try:
            q = supabase_client.table("expert_responses").select(cols).order("created_at", desc=True)
            if status:
                q = q.eq("status", status)
            resp = q.execute()
            return [dict(r) for r in (resp.data or [])]
        except Exception as e:
            print(f"[DB] Supabase list 失败: {e}")
            return []
    else:
        conn = _get_sqlite_conn()
        c = conn.cursor()
        if status:
            c.execute(f"SELECT {cols} FROM expert_responses WHERE status=? ORDER BY created_at DESC", (status,))
        else:
            c.execute(f"SELECT {cols} FROM expert_responses ORDER BY created_at DESC")
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows

def get_submitted_responses():
    """获取所有已提交答卷（完整数据）"""
    if BACKEND == "supabase" and _supabase_ready:
        try:
            resp = supabase_client.table("expert_responses").select("*").eq("status", "submitted").order("submitted_at", desc=True).execute()
            return [_row_to_dict(r) for r in (resp.data or [])]
        except Exception as e:
            print(f"[DB] Supabase submitted 失败: {e}")
            return []
    else:
        conn = _get_sqlite_conn()
        c = conn.cursor()
        c.execute("SELECT * FROM expert_responses WHERE status='submitted' ORDER BY submitted_at DESC")
        rows = [_row_to_dict(r, "sqlite") for r in c.fetchall()]
        conn.close()
        return rows

def get_config():
    """获取问卷配置"""
    if BACKEND == "supabase" and _supabase_ready:
        try:
            resp = supabase_client.table("survey_config").select("*").eq("id", 1).limit(1).execute()
            return dict(resp.data[0]) if resp.data else {}
        except Exception as e:
            print(f"[DB] Supabase config 失败: {e}")
            return {}
    else:
        conn = _get_sqlite_conn()
        c = conn.cursor()
        c.execute("SELECT * FROM survey_config WHERE id = 1")
        row = c.fetchone()
        conn.close()
        return dict(row) if row else {}

def set_survey_open(is_open):
    """设置问卷开放状态"""
    val = 1 if is_open else 0
    if BACKEND == "supabase" and _supabase_ready:
        try:
            supabase_client.table("survey_config").update({"survey_open": val}).eq("id", 1).execute()
        except Exception as e:
            print(f"[DB] Supabase set_open 失败: {e}")
            raise
    else:
        conn = _get_sqlite_conn()
        c = conn.cursor()
        c.execute("UPDATE survey_config SET survey_open = ? WHERE id = 1", (val,))
        conn.commit()
        conn.close()

def init_admin(username, password):
    """初始化管理员（仅首次）"""
    pwd_hash = _hash_pwd(password)
    
    if BACKEND == "supabase" and _supabase_ready:
        try:
            resp = supabase_client.table("admins").select("username").limit(1).execute()
            if resp.data and len(resp.data) > 0:
                return False
            supabase_client.table("admins").insert({
                "username": username, "password_hash": pwd_hash, "created_at": _now()
            }).execute()
            return True
        except Exception as e:
            print(f"[DB] Supabase init_admin 失败: {e}")
            raise
    else:
        conn = _get_sqlite_conn()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM admins")
        if c.fetchone()[0] > 0:
            conn.close()
            return False
        c.execute("INSERT INTO admins (username, password_hash, created_at) VALUES (?, ?, ?)", 
                  (username, pwd_hash, _now()))
        conn.commit()
        conn.close()
        return True

def verify_admin(username, password):
    """验证管理员"""
    pwd_hash = _hash_pwd(password)
    if BACKEND == "supabase" and _supabase_ready:
        try:
            resp = supabase_client.table("admins").select("password_hash").eq("username", username).limit(1).execute()
            if resp.data:
                return resp.data[0]["password_hash"] == pwd_hash
        except Exception as e:
            print(f"[DB] Supabase verify 失败: {e}")
        return False
    else:
        conn = _get_sqlite_conn()
        c = conn.cursor()
        c.execute("SELECT password_hash FROM admins WHERE username = ?", (username,))
        row = c.fetchone()
        conn.close()
        return row and row[0] == pwd_hash

def count_admins():
    """统计管理员数量；返回 -1 表示表不存在或访问失败"""
    if BACKEND == "supabase" and _supabase_ready:
        try:
            resp = supabase_client.table("admins").select("username").execute()
            return len(resp.data or [])
        except Exception as e:
            print(f"[DB] Supabase count_admins 失败: {e}")
            return -1
    else:
        conn = _get_sqlite_conn()
        c = conn.cursor()
        try:
            c.execute("SELECT COUNT(*) FROM admins")
            n = c.fetchone()[0]
        except Exception:
            n = 0
        conn.close()
        return n

# ========== 导出清理函数 ==========
def clear_all_responses():
    """清理所有答卷（测试后使用）"""
    if BACKEND == "supabase" and _supabase_ready:
        try:
            supabase_client.table("expert_responses").delete().neq("response_id", "placeholder").execute()
            print("[DB] Supabase: 已清空所有答卷")
        except Exception as e:
            print(f"[DB] Supabase clear 失败: {e}")
    else:
        conn = _get_sqlite_conn()
        c = conn.cursor()
        c.execute("DELETE FROM expert_responses")
        conn.commit()
        conn.close()
        print(f"[DB] SQLite: 已删除 {c.rowcount} 条答卷")

def backend_info():
    """返回当前后端信息"""
    return {"backend": BACKEND, "supabase_ready": _supabase_ready, "db_path": DB_PATH}

def diagnose():
    """诊断数据库连通性，返回 (是否正常, 详细说明)"""
    info = backend_info()
    if info["backend"] != "supabase":
        return False, f"当前为本地 SQLite（未读到 SUPABASE_URL/SUPABASE_KEY，或 supabase 包未安装）"
    if not _supabase_ready:
        return False, "Supabase 客户端未初始化"
    try:
        supabase_client.table("admins").select("username").limit(1).execute()
        return True, "连接正常，admins 表可访问"
    except Exception as e:
        return False, f"{type(e).__name__}: {str(e)[:300]}"
