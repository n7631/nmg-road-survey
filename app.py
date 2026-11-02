"""
内蒙古公路养护工程后评价专家咨询系统 - 专家填报端
运行: streamlit run app.py --server.port 8501
"""
import streamlit as st
import json
import os
import sys
from datetime import datetime

# 设置页面配置
st.set_page_config(
    page_title="内蒙古公路养护工程后评价专家咨询系统",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 导入数据库模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db

# 加载指标数据
@st.cache_data
def load_survey_data():
    with open("survey_data.json", "r", encoding="utf-8") as f:
        return json.load(f)

survey_data = load_survey_data()

# ============ 会话状态初始化 ============
def init_session():
    if 'page' not in st.session_state:
        st.session_state.page = 1
    if 'response_id' not in st.session_state:
        st.session_state.response_id = None
    if 'resume_token' not in st.session_state:
        st.session_state.resume_token = None
    if 'expert_info' not in st.session_state:
        st.session_state.expert_info = {}
    if 'judgment_basis' not in st.session_state:
        st.session_state.judgment_basis = {}
    if 'structure_reviews' not in st.session_state:
        st.session_state.structure_reviews = {}  # key: 序号
    if 'indicator_ratings' not in st.session_state:
        st.session_state.indicator_ratings = {}  # key: 编码
    if 'supplementary' not in st.session_state:
        st.session_state.supplementary = []
    if 'overall_opinion' not in st.session_state:
        st.session_state.overall_opinion = ""
    if 'submitted' not in st.session_state:
        st.session_state.submitted = False

init_session()

# ============ 函数 ============
def get_or_create_response():
    """获取或创建答卷"""
    if st.session_state.response_id:
        resp = db.get_response(st.session_state.response_id)
        if resp:
            return resp
    
    resp = db.create_or_get_response(
        response_id=st.session_state.get('response_id'),
        resume_token=st.session_state.get('resume_token')
    )
    st.session_state.response_id = resp['response_id']
    st.session_state.resume_token = resp['resume_token']
    return resp

def auto_save():
    """自动保存到数据库"""
    resp = get_or_create_response()
    
    # 计算进度
    total_indicators = len(survey_data['所有三级指标'])
    rated = len([v for v in st.session_state.indicator_ratings.values() if v.get('处理建议')])
    progress = round((rated / total_indicators) * 100, 1) if total_indicators > 0 else 0
    
    data = {
        'expert_number': st.session_state.expert_info.get('expert_number', ''),
        'expert_name': st.session_state.expert_info.get('expert_name', ''),
        'work_unit_type': st.session_state.expert_info.get('work_unit_type', ''),
        'profession': st.session_state.expert_info.get('profession', ''),
        'title': st.session_state.expert_info.get('title', ''),
        'work_years': st.session_state.expert_info.get('work_years', ''),
        'has_mongolia_experience': st.session_state.expert_info.get('has_mongolia_experience', ''),
        'familiarity': st.session_state.expert_info.get('familiarity', ''),
        'judgment_basis': st.session_state.judgment_basis,
        'structure_reviews': list(st.session_state.structure_reviews.values()),
        'indicator_ratings': list(st.session_state.indicator_ratings.values()),
        'supplementary_indicators': st.session_state.supplementary,
        'overall_opinion': st.session_state.overall_opinion,
        'current_page': st.session_state.page,
        'progress_percent': progress
    }
    
    db.save_response(resp['response_id'], data)
    return progress

def next_page():
    """下一页"""
    auto_save()
    if st.session_state.page < 9:
        st.session_state.page += 1
    st.rerun()

def prev_page():
    """上一页"""
    auto_save()
    if st.session_state.page > 1:
        st.session_state.page -= 1
    st.rerun()

def rating_component(label, key_prefix, indicator_code, dimension, required=False):
    """通用五维评分组件"""
    full_key = f"{indicator_code}_{dimension}"
    options = ["未选择", "1分", "2分", "3分", "4分", "5分", "无法判断"]
    
    rating = st.radio(
        label,
        options,
        key=f"rating_{full_key}",
        horizontal=True,
        index=0,
        label_visibility="visible"
    )
    
    # 保存到 session
    if indicator_code not in st.session_state.indicator_ratings:
        st.session_state.indicator_ratings[indicator_code] = {'编码': indicator_code}
    st.session_state.indicator_ratings[indicator_code][dimension] = rating if rating != "未选择" else None
    
    return rating if rating != "未选择" else None

# ============ 页面1: 首页 ============
def page_intro():
    st.markdown("""
    <style>
    .header-card {
        background: linear-gradient(135deg, #1a5276 0%, #2980b9 100%);
        color: white;
        padding: 40px 30px;
        border-radius: 16px;
        margin-bottom: 20px;
    }
    </style>
    <div class="header-card">
        <h1 style="margin:0;font-size:28px;">📋 内蒙古公路养护工程后评价专家咨询系统</h1>
        <p style="margin:10px 0 0 0;font-size:16px;opacity:0.95;">德尔菲专家咨询 · 指标体系论证</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📌 咨询目的")
        st.info(survey_data['填写说明']['咨询目的'])
        
        st.subheader("👥 咨询对象")
        st.write("公路沥青路面设计、施工、检测、养护、运营技术、材料、结构及经济评价等相关领域专家。")
        
        st.subheader("📊 候选指标")
        st.write("**一级指标 4 项 · 二级指标 12 项 · 三级指标 45 项**")
        st.write("· 设计后评价 13 项  \n· 施工后评价 11 项  \n· 技术状况后评价 15 项  \n· 经济社会效益后评价 6 项")
        
        st.subheader("📖 填写原则")
        st.write("""
        · 请基于本人专业判断**独立填写**
        · 没有把握的项目可选"无法判断"
        · 选择"修改后保留/合并/限定适用范围/删除"时，请在意见栏简要说明原因
        · 选择"合并"时请注明拟合并至哪个指标编码
        """)
        
        st.subheader("⭐ 五维评分标准")
        with st.expander("展开查看五维评分详细释义", expanded=False):
            for dim, desc in survey_data['填写说明']['五维评分释义'].items():
                st.markdown(f"**{dim}**")
                st.caption(f"1分: {desc['1分']} | 3分: {desc['3分']} | 5分: {desc['5分']}")
                st.caption(f"说明: {desc['说明']}")
                st.markdown("---")
    
    with col2:
        st.subheader("📋 填写进度")
        steps = [
            "① 专家基本信息",
            "② 指标层级结构审查",
            "③ 设计后评价（13项）",
            "④ 施工后评价（11项）",
            "⑤ 技术状况后评价（15项）",
            "⑥ 经济社会效益后评价（6项）",
            "⑦ 补充指标与总体建议",
            "⑧ 确认并提交"
        ]
        for i, step in enumerate(steps):
            st.write(f"{'✅' if i < st.session_state.page - 1 else '⏳'} {step}")
        
        st.markdown("---")
        
        # 续填功能
        st.subheader("🔄 续填问卷")
        with st.expander("已有续填码？点击恢复填写"):
            token = st.text_input("请输入续填码（首次填写后可获得）", key="resume_input")
            if st.button("恢复填写") and token:
                resp = db.create_or_get_response(resume_token=token.strip())
                if resp:
                    st.session_state.response_id = resp['response_id']
                    st.session_state.resume_token = resp['resume_token']
                    # 恢复数据
                    saved = db.get_response(resp['response_id'])
                    if saved:
                        if saved.get('expert_info'):
                            st.session_state.expert_info = json.loads(saved['expert_info']) if isinstance(saved['expert_info'], str) else saved['expert_info']
                    st.success("✅ 已恢复到上次填写状态！")
                    st.session_state.page = saved.get('current_page', 2) if saved else 2
                    st.rerun()
                else:
                    st.error("续填码无效")
        
        st.markdown("---")
        st.success("🔒 您的填写数据将自动保存并保密，仅用于科研分析。")
    
    # 开始按钮
    st.markdown("---")
    col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
    with col_btn2:
        if st.button("🚀 开始填写问卷", type="primary", use_container_width=True):
            get_or_create_response()
            st.session_state.page = 2
            st.rerun()

# ============ 页面2: 专家信息 ============
def page_expert_info():
    st.markdown("## 📝 第 1 步 · 专家基本信息与判断依据")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("一、专家基本信息")
        
        info = st.session_state.expert_info
        
        info['expert_name'] = st.text_input("专家姓名（选填）", value=info.get('expert_name', ''))
        info['expert_number'] = st.text_input("专家编号（研究组分配，如有请填写）", value=info.get('expert_number', ''), 
                                            help="如未收到编号，留空即可，系统将自动生成")
        info['work_unit_type'] = st.selectbox("工作单位类型", 
            [""] + survey_data['专家信息选项']['工作单位类型'],
            index=[""] + survey_data['专家信息选项']['工作单位类型'].index(info['work_unit_type']) if info.get('work_unit_type') in survey_data['专家信息选项']['工作单位类型'] else 0)
        info['profession'] = st.text_input("主要专业领域", value=info.get('profession', ''), placeholder="如：沥青路面设计、施工工艺、材料研究等")
        info['title'] = st.selectbox("职称", 
            [""] + survey_data['专家信息选项']['职称'],
            index=[""] + survey_data['专家信息选项']['职称'].index(info['title']) if info.get('title') in survey_data['专家信息选项']['职称'] else 0)
        info['work_years'] = st.selectbox("相关工作年限", 
            [""] + survey_data['专家信息选项']['相关工作年限'],
            index=[""] + survey_data['专家信息选项']['相关工作年限'].index(info['work_years']) if info.get('work_years') in survey_data['专家信息选项']['相关工作年限'] else 0)
        info['has_mongolia_experience'] = st.selectbox("是否具有内蒙古/寒区公路养护项目经验", 
            [""] + survey_data['专家信息选项']['内蒙古/寒区公路养护项目经验'],
            index=[""] + survey_data['专家信息选项']['内蒙古/寒区公路养护项目经验'].index(info['has_mongolia_experience']) if info.get('has_mongolia_experience') in survey_data['专家信息选项']['内蒙古/寒区公路养护项目经验'] else 0)
        info['familiarity'] = st.selectbox("对本研究主题的熟悉程度", 
            [""] + survey_data['专家信息选项']['对研究主题的熟悉程度'],
            index=[""] + survey_data['专家信息选项']['对研究主题的熟悉程度'].index(info['familiarity']) if info.get('familiarity') in survey_data['专家信息选项']['对研究主题的熟悉程度'] else 0)
    
    with col2:
        st.subheader("二、判断依据影响程度")
        st.caption("请根据您填写评分时各类判断依据的影响程度，分别选择")
        
        basis = st.session_state.judgment_basis
        degrees = survey_data['专家信息选项']['判断依据程度']
        
        for item in survey_data['专家信息选项']['判断依据']:
            key = item.replace('/', '_')
            basis[key] = st.selectbox(f"**{item}**", [""] + degrees, 
                index=([""] + degrees).index(basis.get(key, "")) if basis.get(key) in degrees else 0,
                key=f"basis_{key}")
    
    st.session_state.expert_info = info
    st.session_state.judgment_basis = basis
    
    nav_buttons()

# ============ 页面3: 结构审查 ============
def page_structure_review():
    st.markdown("## 🏗️ 第 2 步 · 指标层级结构审查")
    st.caption("请判断一级/二级指标名称、归属及下级三级指标配置是否清晰合理；重点审查技术逻辑和指标间边界。")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown("""
        **结构合理性评分：**
        · 1分 = 非常不合理  
        · 3分 = 基本合理  
        · 5分 = 非常合理  
        · 无法判断
        """)
    
    items = survey_data['结构审查项']
    
    for item in items:
        seq = item['序号']
        layer = item['层级']
        parent = item['上级指标']
        name = item['指标名称']
        child_count = item['下级三级项数']
        
        with st.container():
            # 一级指标卡片
            if layer == '一级':
                st.markdown(f"""
                <div style="background:#eaf4fb;padding:15px;border-radius:10px;border-left:5px solid #1a5276;margin:10px 0;">
                    <span style="color:#666;font-size:13px;">一级指标 · 共 {child_count} 项三级指标</span>
                    <h3 style="margin:5px 0 0 0;color:#1a5276;">{name}</h3>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="background:#f8f9fa;padding:10px;border-radius:8px;margin:8px 0;border-left:3px solid #3498db;">
                    <span style="color:#888;font-size:12px;">二级指标 · 上级：{parent}</span>
                    <strong>{name}</strong> · 下级 {child_count} 项
                </div>
                """, unsafe_allow_html=True)
            
            # 评分
            key = str(seq)
            if key not in st.session_state.structure_reviews:
                st.session_state.structure_reviews[key] = {'序号': seq, '层级': layer, '指标名称': name}
            
            col_r1, col_r2, col_r3 = st.columns([2, 1, 1])
            with col_r2:
                rating = st.radio("合理性评分", 
                    ["未选择", "1", "2", "3", "4", "5", "无法判断"],
                    key=f"struct_rating_{seq}", horizontal=True, index=0)
                st.session_state.structure_reviews[key]['结构合理性评分'] = rating if rating != "未选择" else None
            
            with col_r3:
                suggestion = st.selectbox("处理建议",
                    ["未选择"] + survey_data['填写说明']['处理建议选项'],
                    key=f"struct_suggest_{seq}", index=0)
                st.session_state.structure_reviews[key]['处理建议'] = suggestion if suggestion != "未选择" else None
            
            suggestion_detail = st.text_input("修改意见（选填）", 
                value=st.session_state.structure_reviews[key].get('修改意见', ''),
                key=f"struct_comment_{seq}", placeholder="如有修改建议请简要说明...")
            st.session_state.structure_reviews[key]['修改意见'] = suggestion_detail
    
    nav_buttons()

# ============ 通用指标评分模块 ============
def indicator_module(level1_name, indicators, page_num, total_pages):
    """通用三级指标评分"""
    st.markdown(f"## 📊 第 {page_num} 步 · {level1_name}")
    
    # 进度
    total = len(indicators)
    rated = sum(1 for ind in indicators if st.session_state.indicator_ratings.get(ind['编码'], {}).get('处理建议'))
    progress_pct = int((rated / total) * 100) if total > 0 else 0
    st.progress(progress_pct / 100, text=f"📌 已完成 {rated}/{total} 项 · {progress_pct}%")
    
    st.markdown("---")
    
    # 按二级指标分组
    from collections import OrderedDict
    grouped = OrderedDict()
    for ind in indicators:
        l2 = ind['二级指标']
        if l2 not in grouped:
            grouped[l2] = []
        grouped[l2].append(ind)
    
    for level2_name, level2_indicators in grouped.items():
        st.markdown(f"### 📂 {level2_name}")
        
        for ind in level2_indicators:
            code = ind['编码']
            with st.container():
                if code not in st.session_state.indicator_ratings:
                    st.session_state.indicator_ratings[code] = {'编码': code}
                
                # 指标卡片
                st.markdown(f"""
                <div style="background:#ffffff;padding:20px;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,0.08);margin:15px 0;border-top:4px solid #2980b9;">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <h4 style="margin:0;color:#1a5276;">{code} · {ind['三级指标名称']}</h4>
                        <span style="background:#eaf4fb;color:#1a5276;padding:3px 10px;border-radius:12px;font-size:12px;">{ind['区域特征']}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # 折叠区域
                with st.expander("📖 指标详细信息", expanded=False):
                    st.markdown(f"**指标定义：** {ind['指标定义']}")
                    st.markdown(f"**主要量测/计算口径：** {ind['主要量测/计算口径']}")
                    st.markdown(f"**评价时点：** {ind['评价时点']}")
                
                # 五维评分
                col1, col2 = st.columns([3, 2])
                with col1:
                    st.markdown("**五维评分（1-5分，或选择无法判断）**")
                    dimensions = [
                        ("重要性", "评价该指标的重要程度"),
                        ("敏感性", "评价对效果变化的响应能力"),
                        ("可获取性", "评价数据获取的难易程度"),
                        ("区域适配性", "评价在内蒙古区域的适用性"),
                        ("独立性", "评价与其他指标的重复程度")
                    ]
                    for dim_name, dim_tip in dimensions:
                        col_r1, col_r2 = st.columns([2, 3])
                        with col_r1:
                            st.markdown(f"**{dim_name}**")
                            st.caption(dim_tip)
                        with col_r2:
                            rating = st.radio("",
                                ["未选择", "1分", "2分", "3分", "4分", "5分", "无法判断"],
                                key=f"rate_{code}_{dim_name}", horizontal=True, label_visibility="collapsed", index=0)
                            st.session_state.indicator_ratings[code][dim_name] = rating if rating != "未选择" else None
                
                with col2:
                    st.markdown("**处理建议**")
                    suggestion = st.radio("",
                        survey_data['填写说明']['处理建议选项'],
                        key=f"sugg_{code}", label_visibility="collapsed", index=0,
                        help='选择"修改后保留/合并/限定适用范围/删除"时建议填写下方意见')
                    st.session_state.indicator_ratings[code]['处理建议'] = suggestion
                    
                    opinion = st.text_area("意见/修改建议",
                        value=st.session_state.indicator_ratings[code].get('意见', ''),
                        key=f"opinion_{code}", height=80,
                        placeholder="如有修改、合并、删除建议请说明理由...")
                    st.session_state.indicator_ratings[code]['意见'] = opinion
                
                st.markdown("---")
    
    nav_buttons()

# ============ 页面4-7: 四个评分模块 ============
def page_design():
    indicators = [i for i in survey_data['所有三级指标'] if i['一级指标'] == '设计后评价']
    indicator_module("设计后评价", indicators, 3, 8)

def page_construction():
    indicators = [i for i in survey_data['所有三级指标'] if i['一级指标'] == '施工后评价']
    indicator_module("施工后评价", indicators, 4, 8)

def page_technical():
    indicators = [i for i in survey_data['所有三级指标'] if i['一级指标'] == '技术状况后评价']
    indicator_module("技术状况后评价", indicators, 5, 8)

def page_economic():
    indicators = [i for i in survey_data['所有三级指标'] if i['一级指标'] == '经济社会效益后评价']
    indicator_module("经济社会效益后评价", indicators, 6, 8)

# ============ 页面8: 补充指标 ============
def page_supplement():
    st.markdown("## 💡 第 7 步 · 补充指标与总体建议")
    st.caption("如认为现有体系存在遗漏，请提出新增指标；如无新增，可仅填写总体意见。")
    
    st.subheader("一、补充指标建议（最多10项）")
    
    # 初始化补充指标列表
    if not st.session_state.supplementary:
        for i in range(10):
            st.session_state.supplementary.append({
                '序号': i + 1,
                '建议阶段': '',
                '建议二级指标': '',
                '建议三级指标名称': '',
                '建议定义': '',
                '建议量测/计算口径': '',
                '建议评价时点': '',
                '提出理由': '',
                '备注': ''
            })
    
    for i in range(10):
        sup = st.session_state.supplementary[i]
        with st.expander(f"补充指标 #{i+1} {'（已填写）' if sup.get('建议三级指标名称') else ''}"):
            col1, col2 = st.columns(2)
            with col1:
                sup['建议阶段'] = st.selectbox(f"建议阶段 #{i+1}", 
                    [""] + survey_data['补充指标建议选项'],
                    key=f"sup_phase_{i}",
                    index=([""] + survey_data['补充指标建议选项']).index(sup['建议阶段']) if sup.get('建议阶段') in survey_data['补充指标建议选项'] else 0)
                sup['建议二级指标'] = st.text_input(f"建议二级指标 #{i+1}", value=sup.get('建议二级指标', ''), key=f"sup_l2_{i}")
                sup['建议三级指标名称'] = st.text_input(f"建议三级指标名称 #{i+1}", value=sup.get('建议三级指标名称', ''), key=f"sup_name_{i}")
                sup['建议定义'] = st.text_area(f"建议定义 #{i+1}", value=sup.get('建议定义', ''), key=f"sup_def_{i}", height=80)
            with col2:
                sup['建议量测/计算口径'] = st.text_area(f"建议量测/计算口径 #{i+1}", value=sup.get('建议量测/计算口径', ''), key=f"sup_meas_{i}", height=80)
                sup['建议评价时点'] = st.text_input(f"建议评价时点 #{i+1}", value=sup.get('建议评价时点', ''), key=f"sup_time_{i}")
                sup['提出理由'] = st.text_area(f"提出理由/适用场景 #{i+1}", value=sup.get('提出理由', ''), key=f"sup_reason_{i}", height=80)
                sup['备注'] = st.text_input(f"备注 #{i+1}", value=sup.get('备注', ''), key=f"sup_remark_{i}")
    
    st.subheader("二、总体意见")
    st.session_state.overall_opinion = st.text_area("请对整个评价指标体系提出总体意见",
        value=st.session_state.overall_opinion, height=150,
        placeholder="可从体系完整性、阶段划分、内蒙古特色、数据可获得性、评价时点等方面提出建议...")
    
    nav_buttons()

# ============ 页面9: 确认提交 ============
def page_submit():
    st.markdown("## ✅ 第 8 步 · 确认提交")
    
    # 汇总完成情况
    info_filled = all([
        st.session_state.expert_info.get('work_unit_type'),
        st.session_state.expert_info.get('familiarity'),
    ])
    
    total_indicators = len(survey_data['所有三级指标'])
    rated_indicators = len([v for v in st.session_state.indicator_ratings.values() if v.get('处理建议')])
    
    structure_filled = len([v for v in st.session_state.structure_reviews.values() if v.get('处理建议')])
    total_structure = len(survey_data['结构审查项'])
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📊 完成情况检查")
        check_items = [
            ("专家基本信息", "✅ 已填写" if info_filled else "⚠️ 部分未填"),
            ("结构审查", f"✅ {structure_filled}/{total_structure} 已完成"),
            ("三级指标评分", f"✅ {rated_indicators}/{total_indicators} 已完成"),
            ("总体意见", "✅ 已填写" if st.session_state.overall_opinion else "⚪ 未填写（选填）"),
        ]
        for label, status in check_items:
            st.write(f"**{label}：** {status}")
    
    with col2:
        st.subheader("💾 续填方式")
        resp = get_or_create_response()
        st.info(f"""
        **您的续填码：** `{resp['resume_token']}`
        
        请妥善保存此码，如需中途退出可凭此码恢复填写。
        """)
        
        # 自动计算完成率
        progress = auto_save()
        st.metric("当前填写进度", f"{progress}%")
    
    st.markdown("---")
    st.warning("""
    ⚠️ **重要提示：**
    - 正式提交后将**锁定答案**，如需修改请联系研究组
    - 提交前请仔细检查各项内容
    - 数据提交后不可撤回
    """)
    
    # 提交按钮
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("✅ 正式提交问卷", type="primary", use_container_width=True):
            auto_save()
            resp = get_or_create_response()
            db.submit_response(resp['response_id'])
            st.session_state.submitted = True
            st.success(f"""
            ## 🎉 提交成功！
            
            **问卷编号：** `{resp['response_id']}`  
            **续填码：** `{resp['resume_token']}`（提交后仅供参考，如需修改请联系研究组）
            
            感谢您的宝贵意见！您的评分将严格保密，仅用于科研统计分析。
            """)
            st.balloons()
            return
    
    nav_buttons(show_submit_warning=True)

# ============ 通用导航 ============
def nav_buttons(show_submit_warning=False):
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 3, 1])
    
    with col1:
        if st.session_state.page > 1:
            st.button("← 上一页", on_click=prev_page, use_container_width=True, key="prev_btn")
        else:
            st.write("")
    
    with col3:
        if st.session_state.page < 9:
            st.button("下一页 →", on_click=next_page, use_container_width=True, type="primary", key="next_btn")
        elif show_submit_warning:
            st.write("")
    
    # 显示进度指示
    st.caption(f"📑 当前第 {st.session_state.page} / 9 步")

# ============ 主流程 ============
def main():
    # 检查问卷是否开放
    config = db.get_config()
    if config.get('survey_open', 1) == 0:
        st.error("🚫 问卷当前已关闭，感谢您的关注！如有疑问请联系研究组。")
        return
    
    # 如果已提交
    if st.session_state.submitted:
        st.stop()
    
    # 根据当前页码渲染
    pages = {
        1: page_intro,
        2: page_expert_info,
        3: page_structure_review,
        4: page_design,
        5: page_construction,
        6: page_technical,
        7: page_economic,
        8: page_supplement,
        9: page_submit
    }
    
    # 自动保存（每页切换时）
    if st.session_state.page > 1:
        try:
            get_or_create_response()
            auto_save()
        except:
            pass
    
    pages[st.session_state.page]()

if __name__ == "__main__":
    main()
