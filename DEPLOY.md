# Streamlit Cloud + Supabase 部署步骤

## 一、创建 Supabase 项目（5分钟）

1. 访问 https://supabase.com ，用 GitHub 账号免费注册
2. 点击 "New Project"
   - Name: `nmg-road-survey`（随意）
   - Database Password: 设置一个强密码（要记下来！）
   - Region: 选靠近中国的（如 Singapore）
3. 等待项目创建完成（1-2分钟）

## 二、在 Supabase 创建数据表

1. 左侧菜单 → **SQL Editor** → **New query**
2. 打开项目中的 `SUPABASE_SETUP.md` 文件
3. 复制里面全部 SQL 粘贴执行
4. 看到 "Success. No rows returned" 就是成功

## 三、获取 Supabase 连接信息

1. 左侧菜单 → **Project Settings** → **API**
2. 找到以下两个值（复制保存）：
   - **Project URL**: `https://xxxxx.supabase.co`
   - **anon public key**: 很长的一串（以 eyJ 开头）

## 四、推送到 GitHub

```bash
# 在项目文件夹下执行
cd "D:\a研发中心\2026年\0 0615内蒙古公路养护工程后评价体系及方法研究\3.项目调研\问卷调研"

# 初始化 Git（如果还没有）
git init
git add .
git commit -m "专家咨询系统 v1.0"

# 创建 GitHub 仓库后
git remote add origin https://github.com/你的用户名/仓库名.git
git push -u origin main
```

**建议排除的文件**（创建 .gitignore）：
```
survey.db
__pycache__/
*.pyc
*.xlsx
!survey_data.json
```

## 五、Streamlit Cloud 部署

1. 访问 https://share.streamlit.io ，用 GitHub 账号登录
2. **Deploy an app** → 选择刚才推的仓库
3. 创建 **两个** 应用：

### 应用 1：专家端
- Main file path: `app.py`
- 点击 "Advanced settings" → **Secrets** 标签，粘贴：
```toml
SUPABASE_URL = "https://你的项目ID.supabase.co"
SUPABASE_KEY = "你的anon public key"
```
- 部署

### 应用 2：管理端
- Main file path: `admin.py`
- 同样的 Secrets 配置
- 部署

## 六、创建管理员账号

部署完成后，打开 **管理端应用**（admin.py）：
- 首次访问会显示 "⚙️ 首次使用，请创建管理员账号"
- 设置用户名和密码
- 登录后进入后台

## 七、获得 HTTPS 链接

部署完成后 Streamlit Cloud 会给你：
- 专家端：`https://你的app名-expert.streamlit.app`
- 管理端：`https://你的app名-admin.streamlit.app`

都自动是 HTTPS！可以直接分享给专家。

## 八、后续维护

- **重新部署**：git push 后 Streamlit Cloud 自动 rebuild
- **修改指标**：改 Excel → 跑 extract_data.py → git push
- **导出数据**：管理后台 → 📥 数据导出
- **关闭问卷**：管理后台 → ⚙️ 问卷管理
