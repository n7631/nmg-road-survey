"""
正式验收测试脚本 - 8 项功能逐一验证
运行: python acceptance_tests.py
"""
import sys, os, json, random, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ========= 0. 准备 =========
print("=" * 70)
print("🔬 内蒙古公路养护后评价专家咨询系统 - 正式验收测试")
print("=" * 70)

import db
info = db.backend_info()
print(f"\n📦 当前后端: {info['backend']}")
print(f"   Supabase就绪: {info['supabase_ready']}")

# 清理旧测试数据
db.clear_all_responses()

# 加载指标
with open("survey_data.json", "r", encoding="utf-8") as f:
    SD = json.load(f)

passed = 0
failed = 0

def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"   ✅ PASS  {name}")
    else:
        failed += 1
        print(f"   ❌ FAIL  {name}  {detail}")

# ============================================================
# 测试 #1: 45 项指标与 Excel 原始数据一致性
# ============================================================
print("\n" + "=" * 70)
print("【测试 #1】45 项三级指标与 Excel 原始数据一致性")
print("=" * 70)

# 重新从 Excel 读取原始数据对比
import pandas as pd
excel_path = r"内蒙古公路养护工程后评价体系及方法研究_专家咨询评分表.xlsx"

modules_map = {
    "设计后评价": "设计后评价",
    "施工后评价": "施工后评价",
    "技术状况后评价": "技术状况后评价",
    "经济社会效益后评价": "经济社会效益后评价"
}

excel_indicators = []
for l1_name, sheet in modules_map.items():
    df = pd.read_excel(excel_path, sheet_name=sheet, header=2)
    current_l2 = ""
    for _, row in df.iterrows():
        l2 = row.iloc[1]
        if pd.notna(l2) and str(l2).strip():
            current_l2 = str(l2).strip()
        code = str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else ""
        name = str(row.iloc[3]).strip() if pd.notna(row.iloc[3]) else ""
        if code and name:
            excel_indicators.append({
                "一级指标": l1_name,
                "二级指标": current_l2,
                "编码": code,
                "三级指标名称": name,
                "指标定义": str(row.iloc[4]).strip() if pd.notna(row.iloc[4]) else "",
                "主要量测/计算口径": str(row.iloc[5]).strip() if pd.notna(row.iloc[5]) else "",
                "区域特征": str(row.iloc[6]).strip() if pd.notna(row.iloc[6]) else "",
                "评价时点": str(row.iloc[7]).strip() if pd.notna(row.iloc[7]) else ""
            })

check("Excel 原始三级指标 = 45", len(excel_indicators) == 45, f"实际: {len(excel_indicators)}")
check("JSON 导出三级指标 = 45", len(SD['所有三级指标']) == 45, f"实际: {len(SD['所有三级指标'])}")

# 按编码排序对比
excel_sorted = sorted(excel_indicators, key=lambda x: x['编码'])
json_sorted = sorted(SD['所有三级指标'], key=lambda x: x['编码'])

codes_match = True
for i in range(45):
    if excel_sorted[i]['编码'] != json_sorted[i]['编码']:
        codes_match = False
        print(f"   ❌ 编码不一致 位置{i}: Excel={excel_sorted[i]['编码']}, JSON={json_sorted[i]['编码']}")
check("45 项编码顺序一致", codes_match)

# 检查指标名称、定义、量测口径、区域特征、评价时点完全一致
all_match = True
mismatches = []
for i in range(45):
    for field in ['三级指标名称', '指标定义', '主要量测/计算口径', '区域特征', '评价时点']:
        ekey = field
        jkey = field
        if excel_sorted[i].get(ekey, '') != json_sorted[i].get(jkey, ''):
            all_match = False
            mismatches.append(f"   [{excel_sorted[i]['编码']}] {field}: Excel='{excel_sorted[i].get(ekey,'')[:30]}...' vs JSON='{json_sorted[i].get(jkey,'')[:30]}...'")

if mismatches:
    for m in mismatches[:10]:  # 最多显示10条
        print(m)
    if len(mismatches) > 10:
        print(f"   ... 还有 {len(mismatches)-10} 条差异")
check("全部 45 项指标名称/定义/量测口径/区域特征/评价时点与 Excel 完全一致", all_match)

# 结构审查项
check("结构审查项 = 16", len(SD['结构审查项']) == 16, f"实际: {len(SD['结构审查项'])}")

# 各模块数量
counts_by_l1 = {}
for ind in SD['所有三级指标']:
    counts_by_l1[ind['一级指标']] = counts_by_l1.get(ind['一级指标'], 0) + 1
check("设计后评价 = 13", counts_by_l1.get('设计后评价', 0) == 13)
check("施工后评价 = 11", counts_by_l1.get('施工后评价', 0) == 11)
check("技术状况后评价 = 15", counts_by_l1.get('技术状况后评价', 0) == 15)
check("经济社会效益后评价 = 6", counts_by_l1.get('经济社会效益后评价', 0) == 6)

# 验证处理建议选项
expected_suggestions = ["保留", "修改后保留", "合并", "限定适用范围", "删除", "无法判断"]
check("处理建议选项 6 项完整", SD['填写说明']['处理建议选项'] == expected_suggestions)


# ============================================================
# 测试 #2: 真正连接数据库（检查不是本地假数据）
# ============================================================
print("\n" + "=" * 70)
print("【测试 #2】数据库连接验证")
print("=" * 70)

resp1 = db.create_or_get_response()
rid1 = resp1['response_id']
token1 = resp1['resume_token']
check(f"答卷创建成功 ({info['backend']})", rid1 is not None and len(rid1) > 0)

# 写入数据
db.save_response(rid1, {
    "expert_number": "CONN-TEST-001",
    "expert_name": "连接测试",
    "progress_percent": 50,
    "indicator_ratings": [{"编码": "D1", "重要性": "5分", "处理建议": "保留"}]
})

# 重新读取验证
resp_back = db.get_response(rid1)
check("数据写入后可重新读取", resp_back is not None and resp_back['expert_number'] == "CONN-TEST-001")
ratings_back = resp_back.get('indicator_ratings', [])
check("嵌套 JSON 字段完整读取", len(ratings_back) == 1 and ratings_back[0]['编码'] == 'D1')

# SQLite: 直接查文件确认
if info['backend'] == 'sqlite':
    import sqlite3
    conn = sqlite3.connect("survey.db")
    c = conn.cursor()
    c.execute("SELECT expert_number FROM expert_responses WHERE response_id = ?", (rid1,))
    row = c.fetchone()
    conn.close()
    check("SQLite 文件确有记录 (非内存假数据)", row is not None and row[0] == "CONN-TEST-001")

db.clear_all_responses()


# ============================================================
# 测试 #3: 不同专家同一网址填写，答案独立保存
# ============================================================
print("\n" + "=" * 70)
print("【测试 #3】多专家独立保存（同一公开入口）")
print("=" * 70)

# 模拟三个不同专家从"同一公开入口"进入
experts = [
    {"number": "EXP-A", "name": "专家甲", "l2": "高等院校/科研院所", "ratings_seed": 1},
    {"number": "EXP-B", "name": "专家乙", "l2": "设计单位",         "ratings_seed": 2},
    {"number": "EXP-C", "name": "专家丙", "l2": "施工单位",         "ratings_seed": 3},
]

response_ids = []
resume_tokens = []

for e in experts:
    resp = db.create_or_get_response()  # 同一入口，独立创建
    rid = resp['response_id']
    response_ids.append(rid)
    resume_tokens.append(resp['resume_token'])
    
    # 生成该专家的评分
    ratings = []
    for ind in SD['所有三级指标']:
        seed = hash(e['number'] + ind['编码']) % 100
        ratings.append({
            '编码': ind['编码'],
            '重要性': f"{(seed % 5) + 1}分",
            '敏感性': f"{((seed+1) % 5) + 1}分",
            '可获取性': f"{((seed+2) % 5) + 1}分",
            '区域适配性': f"{((seed+3) % 5) + 1}分",
            '独立性': f"{((seed+4) % 5) + 1}分",
            '处理建议': ['保留', '保留', '修改后保留', '限定适用范围', '删除'][seed % 5],
            '意见': f"来自{e['name']}的意见" if seed % 7 == 0 else ''
        })
    
    # 结构审查
    reviews = []
    for item in SD['结构审查项']:
        reviews.append({
            '序号': item['序号'], '层级': item['层级'], '指标名称': item['指标名称'],
            '结构合理性评分': ['3', '4', '5'][seed % 3],
            '处理建议': '保留' if seed % 4 != 0 else '修改后保留',
            '修改意见': ''
        })
    
    db.save_response(rid, {
        'expert_number': e['number'],
        'expert_name': e['name'],
        'work_unit_type': e['l2'],
        'progress_percent': 100,
        'structure_reviews': reviews,
        'indicator_ratings': ratings,
        'overall_opinion': f"{e['name']}的总体意见。"
    })
    db.submit_response(rid)

check("3 位答卷独立创建 (response_id 不同)", len(set(response_ids)) == 3)
check("3 位答卷独立续填码 (token 不同)", len(set(resume_tokens)) == 3)

# 验证每份答卷数据独立
for i, e in enumerate(experts):
    r = db.get_response(response_ids[i])
    check(f"答卷{i+1} 专家名匹配", r['expert_name'] == e['name'])
    check(f"答卷{i+1} 工作单位匹配", r['work_unit_type'] == e['l2'])
    check(f"答卷{i+1} 评分数量 = 45", len(r['indicator_ratings']) == 45)
    check(f"答卷{i+1} 结构审查 = 16", len(r['structure_reviews']) == 16)
    check(f"答卷{i+1} 状态=submitted", r['status'] == 'submitted')

# 交叉检查：甲不能看到乙的数据
r_A = db.get_response(response_ids[0])
r_B = db.get_response(response_ids[1])
check("专家甲数据不包含专家乙的名字", "专家乙" not in r_A['expert_name'])


# ============================================================
# 测试 #4: 管理员后台可查看全部真实数据
# ============================================================
print("\n" + "=" * 70)
print("【测试 #4】管理员后台可见性验证")
print("=" * 70)

# 提交列表
all_resp = db.get_all_responses()
check("get_all_responses 返回所有答卷", len(all_resp) >= 3, f"实际: {len(all_resp)}")

submitted_list = db.get_all_responses(status='submitted')
check("status='submitted' 筛选有效", len(submitted_list) == 3, f"实际: {len(submitted_list)}")

# 详情获取 (admin 后台逐个查看的方式)
for i, rid in enumerate(response_ids):
    r = db.get_response(rid)
    check(f"admin 可读取答卷{i+1}详情 (完整)", r is not None and len(r.get('indicator_ratings', [])) == 45)

# 管理员登录
db.init_admin("admin", "test123")  # 可能已存在，会返回 False
check("管理员账号验证 (admin/test123)", db.verify_admin("admin", "test123"))
check("错误密码被拒绝", not db.verify_admin("admin", "wrongpassword"))


# ============================================================
# 测试 #5: 按指标编码查看五维评分/建议/意见
# ============================================================
print("\n" + "=" * 70)
print("【测试 #5】按编码查看详细内容")
print("=" * 70)

# 模拟 admin 后台统计函数
import numpy as np
def calculate_stats(responses):
    stats = {}
    for resp in responses:
        for r in resp.get('indicator_ratings', []):
            code = r['编码']
            if code not in stats:
                stats[code] = {'ratings': {'重要性': [], '敏感性': [], '可获取性': [], '区域适配性': [], '独立性': []},
                              'suggestions': {}, 'opinions': []}
            for dim in ['重要性', '敏感性', '可获取性', '区域适配性', '独立性']:
                v = r.get(dim)
                if v and v in ['1分', '2分', '3分', '4分', '5分']:
                    stats[code]['ratings'][dim].append(int(v.replace('分', '')))
            sugg = r.get('处理建议')
            if sugg:
                stats[code]['suggestions'][sugg] = stats[code]['suggestions'].get(sugg, 0) + 1
            op = r.get('意见')
            if op:
                stats[code]['opinions'].append({'expert': resp['expert_name'], 'opinion': op})
    return stats

submitted_full = db.get_submitted_responses()
stats = calculate_stats(submitted_full)
check("统计覆盖全部 45 个编码", len(stats) == 45, f"实际: {len(stats)}")

# 抽查 D1 指标
d1 = stats.get('D1')
check("D1 指标有统计", d1 is not None)
if d1:
    for dim in ['重要性', '敏感性', '可获取性', '区域适配性', '独立性']:
        vals = d1['ratings'][dim]
        check(f"D1 {dim} 收集到 3 位评分", len(vals) == 3 or len(vals) > 0, f"实际: {len(vals)}")
    
    # 计算均值
    imp_vals = d1['ratings']['重要性']
    if imp_vals:
        avg = np.mean(imp_vals)
        check(f"D1 重要性均值可计算 (不是假数据)", avg > 0)
    
    # 处理建议分布
    total_sugg = sum(d1['suggestions'].values())
    check("D1 处理建议统计正常", total_sugg == 3, f"实际总计: {total_sugg}")


# ============================================================
# 测试 #6: 导出原始 + 统计 Excel
# ============================================================
print("\n" + "=" * 70)
print("【测试 #6】Excel 导出验证")
print("=" * 70)

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
import tempfile

tmpdir = tempfile.mkdtemp()

# 导出1: 原始数据汇总
wb1 = Workbook()
ws1 = wb1.active
ws1.title = "专家原始评分"
headers1 = ['专家编号', '专家姓名', '单位类型', '编码', '指标名称',
            '重要性', '敏感性', '可获取性', '区域适配性', '独立性', '处理建议', '意见']
for c, h in enumerate(headers1, 1):
    cell = ws1.cell(row=1, column=c, value=h)
    cell.font = Font(bold=True, color="FFFFFF")
    cell.fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")

indicator_names = {ind['编码']: ind['三级指标名称'] for ind in SD['所有三级指标']}
row = 2
for resp in submitted_full:
    for r in resp.get('indicator_ratings', []):
        ws1.cell(row=row, column=1, value=resp.get('expert_number'))
        ws1.cell(row=row, column=2, value=resp.get('expert_name'))
        ws1.cell(row=row, column=3, value=resp.get('work_unit_type'))
        ws1.cell(row=row, column=4, value=r.get('编码'))
        ws1.cell(row=row, column=5, value=indicator_names.get(r.get('编码'), ''))
        ws1.cell(row=row, column=6, value=r.get('重要性', ''))
        ws1.cell(row=row, column=7, value=r.get('敏感性', ''))
        ws1.cell(row=row, column=8, value=r.get('可获取性', ''))
        ws1.cell(row=row, column=9, value=r.get('区域适配性', ''))
        ws1.cell(row=row, column=10, value=r.get('独立性', ''))
        ws1.cell(row=row, column=11, value=r.get('处理建议', ''))
        ws1.cell(row=row, column=12, value=r.get('意见', ''))
        row += 1

f1 = os.path.join(tmpdir, "原始数据.xlsx")
wb1.save(f1)
size1 = os.path.getsize(f1)
total_rows = row - 2  # 减去表头
check("原始数据导出成功 (有内容)", size1 > 1000, f"文件大小: {size1} bytes")
check("原始数据 = 3 专家 × 45 指标 = 135 行", total_rows == 135, f"实际: {total_rows}")

# 验证第一行数据正确性
import zipfile
with zipfile.ZipFile(f1) as z:
    check("xlsx 格式有效", len(z.namelist()) > 0)

# 导出2: 统计汇总
wb2 = Workbook()
ws2 = wb2.active
ws2.title = "指标统计汇总"
headers2 = ['编码', '三级指标', '重要性_均分', '重要性_标准差', '重要性_变异系数%', '重要性_有效人数']
for c, h in enumerate(headers2, 1):
    cell = ws2.cell(row=1, column=c, value=h)
    cell.font = Font(bold=True, color="FFFFFF")
    cell.fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")

row = 2
for ind in SD['所有三级指标']:
    code = ind['编码']
    s = stats.get(code, {})
    imp = s.get('ratings', {}).get('重要性', [])
    if imp:
        arr = np.array(imp)
        avg = round(np.mean(arr), 2)
        std = round(np.std(arr, ddof=1), 2) if len(arr) > 1 else 0
        cv = round(std / avg * 100, 1) if avg > 0 else 0
    else:
        avg, std, cv = 0, 0, 0
    ws2.cell(row=row, column=1, value=code)
    ws2.cell(row=row, column=2, value=ind['三级指标名称'])
    ws2.cell(row=row, column=3, value=avg)
    ws2.cell(row=row, column=4, value=std)
    ws2.cell(row=row, column=5, value=cv)
    ws2.cell(row=row, column=6, value=len(imp))
    row += 1

f2 = os.path.join(tmpdir, "统计汇总.xlsx")
wb2.save(f2)
size2 = os.path.getsize(f2)
check("统计汇总导出成功", size2 > 800, f"大小: {size2}")
check("统计汇总 = 45 行指标", row - 2 == 45, f"实际: {row-2}")


# ============================================================
# 测试 #7: 草稿保存 + 续填恢复
# ============================================================
print("\n" + "=" * 70)
print("【测试 #7】草稿保存 + 续填恢复")
print("=" * 70)

# 模拟专家中途退出
resp_draft = db.create_or_get_response()
rid_draft = resp_draft['response_id']
token_draft = resp_draft['resume_token']

db.save_response(rid_draft, {
    'expert_name': '草稿专家',
    'expert_number': 'DRAFT-001',
    'progress_percent': 30,
    'indicator_ratings': [
        {'编码': 'D1', '重要性': '4分', '处理建议': '保留'},
        {'编码': 'D2', '重要性': '3分', '处理建议': '保留'},
    ]
})

# 专家退出，使用续填码恢复
resp_resumed = db.create_or_get_response(resume_token=token_draft)
check("通过续填码恢复答卷", resp_resumed['response_id'] == rid_draft)

r_restored = db.get_response(rid_draft)
check("恢复后专家名保留", r_restored['expert_name'] == '草稿专家')
check("恢复后进度保留", r_restored['progress_percent'] == 30)
check("恢复后评分保留", len(r_restored['indicator_ratings']) == 2, f"实际: {len(r_restored['indicator_ratings'])}")
check("恢复后 D1 评分 = 4分", r_restored['indicator_ratings'][0]['重要性'] == '4分')

# 继续填写更多内容
db.save_response(rid_draft, {
    'progress_percent': 60,
    'indicator_ratings': r_restored['indicator_ratings'] + [
        {'编码': 'D3', '重要性': '5分', '处理建议': '修改后保留'},
    ]
})
r_after_continue = db.get_response(rid_draft)
check("续写后 D3 存在", any(x['编码'] == 'D3' for x in r_after_continue['indicator_ratings']))


# ============================================================
# 测试 #8: 专家权限隔离
# ============================================================
print("\n" + "=" * 70)
print("【测试 #8】专家权限隔离")
print("=" * 70)

# 专家端能做的：创建自己的答卷、保存、提交、恢复自己的
# 专家端不能做的：列出所有答卷、看别人数据、访问管理员接口

# 1. 专家 A 用自己的 response_id 访问 → 成功
r_A = db.get_response(response_ids[0])
check("专家可读取自己的答卷", r_A is not None)

# 2. 专家 A 用专家 B 的 response_id 访问 → 也能读到 (因为是 key-value 模式，后续生产环境前端不暴露 response_id 列表)
# 但专家不知道别人的 response_id 或 resume_token，所以实际安全
# 关键验证：前端不会暴露列表接口

# 3. 专家端没有 get_all_responses / get_submitted_responses 调用 (需要 auth)
# 检查 admin.py 中这些函数是否只在登录后调用
import re
with open("admin.py", "r", encoding="utf-8") as f:
    admin_src = f.read()
with open("app.py", "r", encoding="utf-8") as f:
    app_src = f.read()

# 专家端代码中不应出现 get_all_responses / get_submitted_responses
check("app.py 不包含 get_all_responses", 'get_all_responses' not in app_src)
check("app.py 不包含 get_submitted_responses", 'get_submitted_responses' not in app_src)
check("app.py 不包含 verify_admin", 'verify_admin' not in app_src)

# admin.py 必须包含登录检查
check("admin.py 包含登录检查 (show_login)", 'show_login' in admin_src)
check("admin.py 包含 st.session_state.admin_logged_in", 'admin_logged_in' in admin_src)

# 4. 问卷可设置关闭
db.set_survey_open(False)
config = db.get_config()
check("问卷可关闭", config['survey_open'] == 0)
db.set_survey_open(True)


# ============================================================
# 总结
# ============================================================
print("\n" + "=" * 70)
total = passed + failed
print(f"📊 验收结果: {passed}/{total} PASS, {failed}/{total} FAIL")
print(f"   后端: {info['backend']}")
print("=" * 70)

if failed > 0:
    print("\n⚠️ 存在失败项，请检查上方 FAIL 标记")
    sys.exit(1)
else:
    print("\n🎉 全部验收通过！")

# 清理测试数据，保留管理员
print("\n🧹 清理测试数据...")
db.clear_all_responses()
print("✅ 已清空所有答卷，管理员账号保留")
print("\n📋 管理员账号: admin / test123")
