# Supabase 数据库初始化 SQL

部署到 Streamlit Cloud 时，请先在 Supabase 控制台执行以下 SQL：

1. 打开 https://supabase.com/dashboard → 进入你的项目
2. 左侧菜单 "SQL Editor" → "New query"
3. 粘贴以下 SQL 并执行

```sql
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

-- 开发阶段临时禁用 RLS（推荐！等系统稳定后再启用）
ALTER TABLE expert_responses DISABLE ROW LEVEL SECURITY;
ALTER TABLE survey_config DISABLE ROW LEVEL SECURITY;
ALTER TABLE admins DISABLE ROW LEVEL SECURITY;
```

执行成功后，返回 Streamlit Cloud 配置 secrets。
