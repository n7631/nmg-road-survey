"""
内蒙古公路养护工程后评价专家咨询系统 - 管理员后台
运行: streamlit run admin.py --server.port 8502
首次运行会提示创建管理员账号
"""
import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import sys
import hashlib
from datetime import datetime
from collections import defaultdict

# 页面配置
st.set_page_config(
    page_title="管理员后台 - 内蒙古公路养护后评价专家咨询系统",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded"
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db

# 加载指标数据
@st.cache_data
def load_survey_data():
    with open("survey_data.json", "r", encoding="utf-8") as f:
        return json.load(f)

survey_data = load_survey_data()

# ============ 登录验证 ============
def check_admin_setup():
    """检查是否需要初始化管理员（SQLite / Supabase 通用）"""
    count = db.count_admins()
    if count < 0:
        ok, detail = db.diagnose()
        st.error("❌ 云数据库无法访问，管理员功能不可用")
        st.code(detail, language="text")
        st.stop()
    return count == 0

def show_login():
    """显示登录页面"""
    st.markdown("""
    <style>
    .login-card {
        max-width: 420px;
        margin: 80px auto;
        background: white;
        padding: 40px;
        border-radius: 16px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("## 🔐 管理员登录")
    
    is_setup = check_admin_setup()
    
    if is_setup:
        st.warning("⚙️ 首次使用，请创建管理员账号")
        with st.form("setup_form"):
            username = st.text_input("用户名")
            password = st.text_input("密码", type="password")
            confirm_pwd = st.text_input("确认密码", type="password")
            submitted = st.form_submit_button("创建管理员")
            
            if submitted:
                if not username or not password:
                    st.error("请填写完整信息")
                elif password != confirm_pwd:
                    st.error("两次密码不一致")
                else:
                    if db.init_admin(username, password):
                        st.success("✅ 管理员创建成功！请使用新账号登录")
                        st.rerun()
                    else:
                        st.error("创建失败")
    else:
        with st.form("login_form"):
            username = st.text_input("用户名")
            password = st.text_input("密码", type="password")
            submitted = st.form_submit_button("登录")
            
            if submitted:
                if db.verify_admin(username, password):
                    st.session_state.admin_logged_in = True
                    st.session_state.admin_username = username
                    st.rerun()
                else:
                    st.error("❌ 用户名或密码错误")

# ============ 数据统计函数 ============
def calculate_statistics(submitted_responses):
    """计算五维评分统计"""
    if not submitted_responses:
        return {}
    
    # 按指标编码汇总
    indicator_stats = defaultdict(lambda: {
        'ratings': defaultdict(list),  # dimension -> [values]
        'suggestions': defaultdict(int),  # suggestion -> count
        'opinions': [],  # 文字意见列表
        'ratings_raw': defaultdict(list)  # 原始评分（包含无法判断）
    })
    
    for resp in submitted_responses:
        expert_id = resp.get('response_id', '')
        
        # 三级指标评分
        for rating in resp.get('indicator_ratings', []):
            code = rating.get('编码', '')
            if not code:
                continue
            
            for dim in ['重要性', '敏感性', '可获取性', '区域适配性', '独立性']:
                val = rating.get(dim)
                if val:
                    indicator_stats[code]['ratings_raw'][dim].append((expert_id, val))
                    # 只统计1-5分，排除无法判断
                    if val in ['1分', '2分', '3分', '4分', '5分']:
                        num_val = int(val.replace('分', ''))
                        indicator_stats[code]['ratings'][dim].append(num_val)
            
            # 处理建议
            sugg = rating.get('处理建议')
            if sugg:
                indicator_stats[code]['suggestions'][sugg] += 1
            
            # 文字意见
            opinion = rating.get('意见')
            if opinion:
                indicator_stats[code]['opinions'].append({
                    'expert_id': expert_id,
                    'opinion': opinion
                })
    
    # 计算统计量
    result = {}
    for code, stats in indicator_stats.items():
        indicator_result = {'编码': code}
        
        for dim in ['重要性', '敏感性', '可获取性', '区域适配性', '独立性']:
            values = stats['ratings'][dim]
            raw = stats['ratings_raw'][dim]
            
            if values:
                arr = np.array(values)
                indicator_result[f'{dim}_有效人数'] = len(values)
                indicator_result[f'{dim}_平均分'] = round(np.mean(arr), 2)
                indicator_result[f'{dim}_中位数'] = round(np.median(arr), 2)
                indicator_result[f'{dim}_标准差'] = round(np.std(arr, ddof=1), 2) if len(arr) > 1 else 0
                indicator_result[f'{dim}_变异系数'] = round(np.std(arr, ddof=1) / np.mean(arr) * 100, 1) if np.mean(arr) > 0 else 0
                indicator_result[f'{dim}_无法判断人数'] = sum(1 for _, v in raw if v == '无法判断')
                # 分布
                dist = defaultdict(int)
                for v in values:
                    dist[v] += 1
                indicator_result[f'{dim}_分布'] = dict(dist)
            else:
                indicator_result[f'{dim}_有效人数'] = 0
                indicator_result[f'{dim}_无法判断人数'] = sum(1 for _, v in raw if v == '无法判断')
        
        # 处理建议统计
        total_sugg = sum(stats['suggestions'].values())
        for opt in survey_data['填写说明']['处理建议选项']:
            count = stats['suggestions'].get(opt, 0)
            indicator_result[f'建议_{opt}_人数'] = count
            indicator_result[f'建议_{opt}_比例'] = round(count / total_sugg * 100, 1) if total_sugg > 0 else 0
        
        indicator_result['意见数'] = len(stats['opinions'])
        result[code] = indicator_result
    
    return result

# ============ Excel 导出函数 ============
def export_excel(submitted_responses, filename_prefix="专家咨询数据"):
    """导出三种 Excel"""
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    files = []
    
    # ========== 导出1：专家原始数据汇总 ==========
    wb1 = Workbook()
    ws1 = wb1.active
    ws1.title = "专家原始评分"
    
    # 表头
    headers = ['专家编号', '专家姓名', '工作单位', '熟悉程度', '编码', '三级指标名称', 
               '重要性', '敏感性', '可获取性', '区域适配性', '独立性', '处理建议', '意见']
    for col, h in enumerate(headers, 1):
        cell = ws1.cell(row=1, column=col, value=h)
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        cell.font = Font(bold=True, color="FFFFFF")
    
    # 指标名称映射
    indicator_names = {ind['编码']: ind['三级指标名称'] for ind in survey_data['所有三级指标']}
    
    row = 2
    for resp in submitted_responses:
        expert_id = resp.get('response_id', '')
        expert_name = resp.get('expert_name', '') or '(未填写)'
        work_unit = resp.get('work_unit_type', '')
        familiarity = resp.get('familiarity', '')
        
        for rating in resp.get('indicator_ratings', []):
            code = rating.get('编码', '')
            ws1.cell(row=row, column=1, value=expert_id)
            ws1.cell(row=row, column=2, value=expert_name)
            ws1.cell(row=row, column=3, value=work_unit)
            ws1.cell(row=row, column=4, value=familiarity)
            ws1.cell(row=row, column=5, value=code)
            ws1.cell(row=row, column=6, value=indicator_names.get(code, ''))
            ws1.cell(row=row, column=7, value=rating.get('重要性', '') or '')
            ws1.cell(row=row, column=8, value=rating.get('敏感性', '') or '')
            ws1.cell(row=row, column=9, value=rating.get('可获取性', '') or '')
            ws1.cell(row=row, column=10, value=rating.get('区域适配性', '') or '')
            ws1.cell(row=row, column=11, value=rating.get('独立性', '') or '')
            ws1.cell(row=row, column=12, value=rating.get('处理建议', '') or '')
            ws1.cell(row=row, column=13, value=rating.get('意见', '') or '')
            row += 1
    
    # 调整列宽
    for col in range(1, len(headers) + 1):
        ws1.column_dimensions[chr(64 + col) if col <= 26 else 'A'].width = 18
    
    fname1 = f"{filename_prefix}_原始数据_{timestamp}.xlsx"
    wb1.save(fname1)
    files.append(fname1)
    
    # ========== 导出2：按指标统计结果 ==========
    wb2 = Workbook()
    ws2 = wb2.active
    ws2.title = "指标统计汇总"
    
    stats = calculate_statistics(submitted_responses)
    
    # 表头
    headers2 = ['一级指标', '二级指标', '编码', '三级指标名称']
    for dim in ['重要性', '敏感性', '可获取性', '区域适配性', '独立性']:
        headers2.extend([f'{dim}_有效人数', f'{dim}_平均分', f'{dim}_标准差', f'{dim}_变异系数%', f'{dim}_无法判断数'])
    for opt in survey_data['填写说明']['处理建议选项']:
        headers2.append(f'建议_{opt}_人数')
    headers2.append('意见数量')
    
    for col, h in enumerate(headers2, 1):
        cell = ws2.cell(row=1, column=col, value=h)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    
    row = 2
    for ind in survey_data['所有三级指标']:
        code = ind['编码']
        s = stats.get(code, {})
        
        ws2.cell(row=row, column=1, value=ind['一级指标'])
        ws2.cell(row=row, column=2, value=ind['二级指标'])
        ws2.cell(row=row, column=3, value=code)
        ws2.cell(row=row, column=4, value=ind['三级指标名称'])
        
        col = 5
        for dim in ['重要性', '敏感性', '可获取性', '区域适配性', '独立性']:
            ws2.cell(row=row, column=col, value=s.get(f'{dim}_有效人数', 0))
            ws2.cell(row=row, column=col + 1, value=s.get(f'{dim}_平均分', ''))
            ws2.cell(row=row, column=col + 2, value=s.get(f'{dim}_标准差', ''))
            ws2.cell(row=row, column=col + 3, value=s.get(f'{dim}_变异系数', ''))
            ws2.cell(row=row, column=col + 4, value=s.get(f'{dim}_无法判断人数', 0))
            col += 5
        
        for opt in survey_data['填写说明']['处理建议选项']:
            ws2.cell(row=row, column=col, value=s.get(f'建议_{opt}_人数', 0))
            col += 1
        
        ws2.cell(row=row, column=col, value=s.get('意见数', 0))
        row += 1
    
    fname2 = f"{filename_prefix}_统计汇总_{timestamp}.xlsx"
    wb2.save(fname2)
    files.append(fname2)
    
    # ========== 导出3：专家意见汇总 ==========
    wb3 = Workbook()
    ws3 = wb3.active
    ws3.title = "文字意见汇总"
    
    headers3 = ['专家编号', '编码', '三级指标名称', '意见类型', '内容']
    for col, h in enumerate(headers3, 1):
        cell = ws3.cell(row=1, column=col, value=h)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    
    row = 2
    for resp in submitted_responses:
        expert_id = resp.get('response_id', '')
        
        # 三级指标意见
        for rating in resp.get('indicator_ratings', []):
            code = rating.get('编码', '')
            opinion = rating.get('意见')
            if opinion:
                ws3.cell(row=row, column=1, value=expert_id)
                ws3.cell(row=row, column=2, value=code)
                ws3.cell(row=row, column=3, value=indicator_names.get(code, ''))
                sugg = rating.get('处理建议', '')
                ws3.cell(row=row, column=4, value=f"处理建议: {sugg}")
                ws3.cell(row=row, column=5, value=opinion)
                row += 1
        
        # 总体意见
        overall = resp.get('overall_opinion')
        if overall:
            ws3.cell(row=row, column=1, value=expert_id)
            ws3.cell(row=row, column=2, value='—')
            ws3.cell(row=row, column=3, value='总体意见')
            ws3.cell(row=row, column=4, value='总体意见')
            ws3.cell(row=row, column=5, value=overall)
            row += 1
    
    fname3 = f"{filename_prefix}_意见汇总_{timestamp}.xlsx"
    wb3.save(fname3)
    files.append(fname3)
    
    return files

# ============ 各模块页面 ============
def page_dashboard():
    """仪表盘概览"""
    st.markdown("## 📊 数据概览")
    
    submitted = db.get_all_responses(status='submitted')
    drafts = db.get_all_responses(status='draft')
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("总答卷数", len(submitted) + len(drafts))
    col2.metric("已提交", len(submitted))
    col3.metric("草稿中", len(drafts))
    col4.metric("问卷版本", "v1.0")
    
    # 提交时间趋势
    if submitted:
        st.subheader("📈 提交时间分布")
        submit_times = [r['submitted_at'] for r in submitted if r.get('submitted_at')]
        if submit_times:
            df_times = pd.DataFrame({'时间': pd.to_datetime(submit_times)})
            df_times['日期'] = df_times['时间'].dt.date
            counts = df_times.groupby('日期').size().reset_index(name='提交数')
            st.bar_chart(counts.set_index('日期'))

def page_manage():
    """问卷管理"""
    st.markdown("## ⚙️ 问卷管理")
    
    config = db.get_config()
    is_open = bool(config.get('survey_open', 1))
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("问卷状态")
        st.info(f"当前状态：**{'🟢 开放中' if is_open else '🔴 已关闭'}**")
        
        if is_open:
            if st.button("🔴 关闭问卷"):
                db.set_survey_open(False)
                st.success("问卷已关闭")
                st.rerun()
        else:
            if st.button("🟢 开放问卷"):
                db.set_survey_open(True)
                st.success("问卷已开放")
                st.rerun()
    
    with col2:
        st.subheader("问卷链接")
        # 从 config 文件读取部署地址
        survey_url = st.text_input("专家填写链接（部署后填写）", 
            value="http://localhost:8501", 
            help="部署上线后请替换为实际的 HTTPS 链接")
        
        if survey_url:
            import qrcode
            from io import BytesIO
            qr = qrcode.make(survey_url)
            buf = BytesIO()
            qr.save(buf, format='PNG')
            buf.seek(0)
            st.image(buf.getvalue(), caption="扫描二维码填写问卷", width=200)
        
        with st.expander("📋 复制链接"):
            st.code(survey_url, language="text")

def page_responses_list():
    """专家答卷列表"""
    st.markdown("## 📋 专家答卷列表")
    
    # 筛选
    col1, col2 = st.columns([1, 3])
    with col1:
        status_filter = st.selectbox("状态筛选", ["全部", "已提交", "草稿"])
    
    all_resp = db.get_all_responses()
    df = pd.DataFrame(all_resp)
    
    if status_filter != "全部":
        df = df[df['status'] == status_filter]
    
    if df.empty:
        st.info("暂无答卷数据")
        return
    
    # 格式化显示
    def format_row(row):
        status_emoji = "✅" if row['status'] == 'submitted' else "✏️"
        return f"{status_emoji} {row.get('expert_name') or '(未填)'} - {row['response_id'][:8]}"
    
    df['状态'] = df['status'].apply(lambda x: "✅ 已提交" if x == 'submitted' else "✏️ 草稿")
    
    display_cols = ['response_id', 'expert_name', 'work_unit_type', 'profession', 
                    'familiarity', 'progress_percent', 'status', 'created_at', 'submitted_at']
    display_names = ['问卷编号', '姓名', '单位类型', '专业领域', '熟悉程度', 
                     '进度%', '状态', '创建时间', '提交时间']
    
    available_cols = [c for c in display_cols if c in df.columns]
    df_display = df[available_cols].copy()
    df_display.columns = display_names[:len(available_cols)]
    
    st.dataframe(df_display, use_container_width=True, hide_index=True)
    
    # 批量清理草稿
    drafts_count = len([r for r in all_resp if r.get('status') == 'draft'])
    if drafts_count > 0:
        st.markdown("---")
        c1, c2 = st.columns([1, 4])
        with c1:
            confirm_key = "bulk_clear_drafts_confirm"
            if confirm_key not in st.session_state:
                st.session_state[confirm_key] = False
            if st.button(f"🧹 清空所有草稿（共 {drafts_count} 份）", type="secondary"):
                st.session_state[confirm_key] = True
        with c2:
            if st.session_state.get(confirm_key):
                st.warning(f"确认删除全部 {drafts_count} 份草稿？已提交答卷不受影响。此操作不可恢复。")
                ok_col, cancel_col = st.columns(2)
                with ok_col:
                    if st.button("✅ 确认清空", type="primary"):
                        n = db.clear_all_drafts()
                        st.session_state.pop(confirm_key, None)
                        if n >= 0:
                            st.success(f"已删除 {n} 份草稿")
                        else:
                            st.error("删除失败，请查看日志")
                        st.rerun()
                with cancel_col:
                    if st.button("❌ 取消"):
                        st.session_state.pop(confirm_key, None)
                        st.rerun()
    
    # 查看详情
    st.subheader("🔍 查看单份答卷详情")
    options = [f"{r.get('expert_name') or '(未填)'} - {r['response_id'][:8]} - {'已提交' if r['status'] == 'submitted' else '草稿'}" for r in all_resp]
    selected = st.selectbox("选择答卷", options, key="response_detail_select")
    
    if selected:
        resp_idx = options.index(selected)
        resp = db.get_response(all_resp[resp_idx]['response_id'])
        if resp:
            show_response_detail(resp)
            
            # 草稿删除（二次确认）
            st.markdown("---")
            if resp.get('status') == 'draft':
                col_a, col_b = st.columns([1, 3])
                with col_a:
                    confirm_key = f"del_confirm_{resp['response_id']}"
                    if confirm_key not in st.session_state:
                        st.session_state[confirm_key] = False
                    if st.button("🗑️ 删除该草稿", key=f"del_btn_{resp['response_id']}", type="secondary"):
                        st.session_state[confirm_key] = True
                with col_b:
                    if st.session_state[confirm_key]:
                        st.warning(f"确认删除草稿 `{resp['response_id'][:12]}`？此操作不可恢复。")
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.button("✅ 确认删除", key=f"del_ok_{resp['response_id']}", type="primary"):
                                ok, msg = db.delete_response(resp['response_id'], only_draft=True)
                                if ok:
                                    st.success(f"已删除。{msg}")
                                    st.session_state.pop(confirm_key, None)
                                    st.rerun()
                                else:
                                    st.error(msg)
                        with c2:
                            if st.button("❌ 取消", key=f"del_cancel_{resp['response_id']}"):
                                st.session_state.pop(confirm_key, None)
                                st.rerun()
            else:
                st.caption("ℹ️ 已提交答卷不可删除。如需作废请联系开发人员清空数据库。")

def show_response_detail(resp):
    """显示单份答卷详情"""
    with st.expander("📄 答卷详情", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**专家基本信息**")
            st.write(f"问卷编号: `{resp['response_id']}`")
            st.write(f"专家姓名: {resp.get('expert_name') or '(未填写)'}")
            st.write(f"单位类型: {resp.get('work_unit_type') or '(未填写)'}")
            st.write(f"专业领域: {resp.get('profession') or '(未填写)'}")
            st.write(f"职称: {resp.get('title') or '(未填写)'}")
            st.write(f"工作年限: {resp.get('work_years') or '(未填写)'}")
            st.write(f"内蒙古经验: {resp.get('has_mongolia_experience') or '(未填写)'}")
            st.write(f"熟悉程度: {resp.get('familiarity') or '(未填写)'}")
        
        with col2:
            st.markdown("**判断依据**")
            basis = resp.get('judgment_basis') or {}
            for k, v in basis.items():
                st.write(f"- {k}: {v or '(未填)'}")
        
        st.markdown("---")
        
        # 指标评分
        st.markdown("**指标评分详情**")
        ratings = resp.get('indicator_ratings') or []
        if ratings:
            df_ratings = pd.DataFrame(ratings)
            # 合并指标名称
            indicator_map = {ind['编码']: ind['三级指标名称'] for ind in survey_data['所有三级指标']}
            df_ratings['指标名称'] = df_ratings['编码'].map(indicator_map)
            
            cols = ['编码', '指标名称', '重要性', '敏感性', '可获取性', '区域适配性', '独立性', '处理建议', '意见']
            existing_cols = [c for c in cols if c in df_ratings.columns]
            st.dataframe(df_ratings[existing_cols], use_container_width=True, hide_index=True)
        
        # 总体意见
        if resp.get('overall_opinion'):
            st.markdown("**总体意见**")
            st.info(resp['overall_opinion'])
        
        # 补充指标
        if resp.get('supplementary_indicators'):
            st.markdown("**补充指标建议**")
            df_sup = pd.DataFrame(resp['supplementary_indicators'])
            st.dataframe(df_sup, use_container_width=True, hide_index=True)

def page_statistics():
    """数据统计分析"""
    st.markdown("## 📈 数据统计分析")
    
    submitted = db.get_submitted_responses()
    
    if not submitted:
        st.warning("暂无已提交的答卷数据")
        return
    
    st.info(f"当前分析基于 **{len(submitted)}** 份已提交答卷")
    
    stats = calculate_statistics(submitted)
    
    # 按模块分组展示
    modules = {
        "设计后评价": [ind['编码'] for ind in survey_data['所有三级指标'] if ind['一级指标'] == '设计后评价'],
        "施工后评价": [ind['编码'] for ind in survey_data['所有三级指标'] if ind['一级指标'] == '施工后评价'],
        "技术状况后评价": [ind['编码'] for ind in survey_data['所有三级指标'] if ind['一级指标'] == '技术状况后评价'],
        "经济社会效益后评价": [ind['编码'] for ind in survey_data['所有三级指标'] if ind['一级指标'] == '经济社会效益后评价']
    }
    
    # 指标名称映射
    indicator_map = {ind['编码']: ind['三级指标名称'] for ind in survey_data['所有三级指标']}
    
    for module_name, codes in modules.items():
        with st.expander(f"📊 {module_name}（{len(codes)}项）", expanded=False):
            # 构建 DataFrame
            rows = []
            for code in codes:
                s = stats.get(code, {})
                row = {
                    '编码': code,
                    '三级指标': indicator_map.get(code, code),
                }
                for dim in ['重要性', '敏感性', '可获取性', '区域适配性', '独立性']:
                    row[f'{dim}_均分'] = s.get(f'{dim}_平均分', '')
                    row[f'{dim}_变异%'] = s.get(f'{dim}_变异系数', '')
                    row[f'{dim}_有效n'] = s.get(f'{dim}_有效人数', 0)
                
                # 处理建议
                for opt in survey_data['填写说明']['处理建议选项']:
                    row[f'{opt}'] = s.get(f'建议_{opt}_人数', 0)
                row['意见数'] = s.get('意见数', 0)
                rows.append(row)
            
            df_module = pd.DataFrame(rows)
            st.dataframe(df_module, use_container_width=True, hide_index=True)
    
    # 指标筛选
    st.subheader("🎯 指标筛选分析")
    
    filter_type = st.selectbox("筛选类型", [
        "平均分较低的指标（重要性<3.5）",
        "意见分歧较大的指标（变异系数>30%）",
        "删除建议较多的指标",
        "保留建议较少的指标"
    ])
    
    if filter_type:
        filtered = []
        for code, s in stats.items():
            avg_importance = s.get('重要性_平均分', 0)
            cv_importance = s.get('重要性_变异系数', 0)
            delete_count = s.get('建议_删除_人数', 0)
            keep_count = s.get('建议_保留_人数', 0)
            total_sugg = sum(s.get(f'建议_{opt}_人数', 0) for opt in survey_data['填写说明']['处理建议选项'])
            
            match = False
            if filter_type == "平均分较低的指标（重要性<3.5）" and avg_importance and avg_importance < 3.5:
                match = True
            elif filter_type == "意见分歧较大的指标（变异系数>30%）" and cv_importance and cv_importance > 30:
                match = True
            elif filter_type == "删除建议较多的指标" and delete_count >= 2:
                match = True
            elif filter_type == "保留建议较少的指标" and keep_count < total_sugg * 0.5 and total_sugg > 0:
                match = True
            
            if match:
                filtered.append({
                    '编码': code,
                    '三级指标': indicator_map.get(code, code),
                    '重要性均分': avg_importance,
                    '变异系数%': cv_importance,
                    '删除建议': delete_count,
                    '保留建议': keep_count,
                    '意见数': s.get('意见数', 0)
                })
        
        if filtered:
            df_filtered = pd.DataFrame(filtered)
            st.dataframe(df_filtered, use_container_width=True, hide_index=True)
        else:
            st.info("无符合条件的指标")

def page_opinions():
    """文字意见汇总"""
    st.markdown("## 💬 文字意见汇总")
    
    submitted = db.get_submitted_responses()
    
    if not submitted:
        st.warning("暂无已提交的答卷数据")
        return
    
    # 指标选择
    indicator_map = {ind['编码']: f"{ind['编码']} · {ind['三级指标名称']}" for ind in survey_data['所有三级指标']}
    selected_indicator = st.selectbox("选择指标查看专家意见", ["全部"] + list(indicator_map.values()))
    
    # 汇总意见
    all_opinions = []
    
    for resp in submitted:
        expert_id = resp.get('response_id', '')
        expert_name = resp.get('expert_name') or '(未填)'
        
        # 三级指标意见
        for rating in resp.get('indicator_ratings', []):
            code = rating.get('编码', '')
            opinion = rating.get('意见')
            sugg = rating.get('处理建议', '')
            
            if opinion:
                if selected_indicator == "全部" or code == selected_indicator.split(' · ')[0]:
                    all_opinions.append({
                        '专家': f"{expert_name} ({expert_id[:8]})",
                        '指标': indicator_map.get(code, code),
                        '处理建议': sugg,
                        '意见内容': opinion
                    })
        
        # 总体意见
        overall = resp.get('overall_opinion')
        if overall and (selected_indicator == "全部"):
            all_opinions.append({
                '专家': f"{expert_name} ({expert_id[:8]})",
                '指标': '总体意见',
                '处理建议': '—',
                '意见内容': overall
            })
    
    if all_opinions:
        df_opinions = pd.DataFrame(all_opinions)
        st.dataframe(df_opinions, use_container_width=True, hide_index=True)
    else:
        st.info("该指标暂无文字意见")

def page_export():
    """数据导出"""
    st.markdown("## 📥 Excel 数据导出")
    
    submitted = db.get_submitted_responses()
    
    if not submitted:
        st.warning("暂无已提交的答卷数据，无法导出")
        return
    
    st.success(f"将基于 **{len(submitted)}** 份已提交答卷进行导出")
    
    if st.button("📦 生成 Excel 导出文件", type="primary"):
        with st.spinner("正在生成 Excel 文件..."):
            files = export_excel(submitted)
        
        st.success("✅ Excel 文件生成完成！")
        
        # 显示下载链接
        st.markdown("### 📥 下载文件")
        for f in files:
            with open(f, 'rb') as fp:
                filename = os.path.basename(f)
                st.download_button(
                    label=f"下载 {filename}",
                    data=fp.read(),
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

# ============ 主入口 ============
def main():
    # 检查登录
    if 'admin_logged_in' not in st.session_state or not st.session_state.admin_logged_in:
        show_login()
        return
    
    # 侧边栏导航
    st.markdown("""
    <style>
    .stApp {
        background-color: #f8f9fa;
    }
    </style>
    """, unsafe_allow_html=True)
    
    with st.sidebar:
        st.markdown("## 🔐 管理员后台")
        st.markdown("---")
        
        page = st.radio("功能菜单", [
            "📊 数据概览",
            "⚙️ 问卷管理",
            "📋 答卷列表",
            "📈 统计分析",
            "💬 文字意见",
            "📥 数据导出"
        ], label_visibility="collapsed")
        
        st.markdown("---")
        
        _info = db.backend_info()
        if _info['backend'] == 'supabase':
            st.success("☁️ 云数据库：Supabase 已连接")
        else:
            st.warning("⚠️ 本地 SQLite（云端部署下数据会丢失，请检查 Secrets）")
        
        st.caption(f"管理员: {st.session_state.get('admin_username', '')}")
        if st.button("退出登录"):
            st.session_state.admin_logged_in = False
            st.rerun()
    
    # 渲染页面
    page_map = {
        "📊 数据概览": page_dashboard,
        "⚙️ 问卷管理": page_manage,
        "📋 答卷列表": page_responses_list,
        "📈 统计分析": page_statistics,
        "💬 文字意见": page_opinions,
        "📥 数据导出": page_export
    }
    
    page_map[page]()

if __name__ == "__main__":
    main()
