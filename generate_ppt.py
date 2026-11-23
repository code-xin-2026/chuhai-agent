# -*- coding: utf-8 -*-
"""生成帆朵比赛 PPT v2（16:9，章节化 + 图表 + 表格，参考农业保险学术风格）。"""
import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from PIL import Image

IMG = r'C:/Users/12785/AppData/Roaming/Hermes/composer-images'
OUT = r'E:/SongBIn2.0/AiMaShi-Hermes/duihua/chuhai-agent/帆朵_比赛PPT.pptx'

# —— 配色 ——
DARK   = RGBColor(0x12, 0x3C, 0x5E)   # 深蓝主色
BLUE   = RGBColor(0x2E, 0x86, 0xC1)   # 青蓝
TEAL   = RGBColor(0x16, 0xA0, 0x85)   # 青绿(合规/确定)
ORANGE = RGBColor(0xE6, 0x7E, 0x22)   # 橙(风险/强调)
RED    = RGBColor(0xC0, 0x39, 0x2B)   # 红(高风险)
GOLD   = RGBColor(0xF3, 0x9C, 0x12)   # 黄(估算)
LIGHT  = RGBColor(0xEE, 0xF4, 0xF9)   # 浅蓝底
LIGHT2 = RGBColor(0xF7, 0xFA, 0xFD)   # 更浅
WHITE  = RGBColor(0xFF, 0xFF, 0xFF)
TEXT   = RGBColor(0x2C, 0x3E, 0x50)
GRAY   = RGBColor(0x7F, 0x8C, 0x8D)
PALE   = RGBColor(0xBD, 0xD0, 0xE2)   # 封面浅字

FONT = '微软雅黑'

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]

def new_slide(bg=WHITE):
    s = prs.slides.add_slide(BLANK)
    r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    r.fill.solid(); r.fill.fore_color.rgb = bg
    r.line.fill.background(); r.shadow.inherit = False
    return s

def box(slide, left, top, width, height, fill=None, line=None, line_w=1.0, shape=MSO_SHAPE.RECTANGLE, radius=None):
    sh = slide.shapes.add_shape(shape, Inches(left), Inches(top), Inches(width), Inches(height))
    if fill is None:
        sh.fill.background()
    else:
        sh.fill.solid(); sh.fill.fore_color.rgb = fill
    if line is None:
        sh.line.fill.background()
    else:
        sh.line.color.rgb = line; sh.line.width = Pt(line_w)
    sh.shadow.inherit = False
    if radius is not None and shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        try: sh.adjustments[0] = radius
        except Exception: pass
    return sh

def txt(slide, text, left, top, width, height, size=18, bold=False, color=TEXT,
        align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, font=FONT, italic=False):
    tb = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = tb.text_frame; tf.word_wrap = True; tf.vertical_anchor = anchor
    tf.margin_left = 0; tf.margin_right = 0; tf.margin_top = 0; tf.margin_bottom = 0
    p = tf.paragraphs[0]; p.alignment = align
    r = p.add_run(); r.text = text
    r.font.size = Pt(size); r.font.bold = bold; r.font.italic = italic
    r.font.color.rgb = color; r.font.name = font
    return tb

def para(slide, text, left, top, width, height, size=15, bold=False, color=TEXT,
         align=PP_ALIGN.LEFT, gap=6, font=FONT):
    """多段文本，text 为 list of (内容, bold, color) 或纯字符串段落列表。"""
    tb = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = tb.text_frame; tf.word_wrap = True
    tf.margin_left = 0; tf.margin_right = 0; tf.margin_top = 0; tf.margin_bottom = 0
    for i, item in enumerate(text):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align; p.space_after = Pt(gap)
        if isinstance(item, str):
            r = p.add_run(); r.text = item
            r.font.size = Pt(size); r.font.color.rgb = color; r.font.name = font
        else:
            content, b, c = item
            r = p.add_run(); r.text = content
            r.font.size = Pt(size); r.font.bold = b; r.font.color.rgb = c; r.font.name = font
    return tb

def chip(slide, left, top, width, height, label, fill, size=13, color=WHITE):
    sh = box(slide, left, top, width, height, fill=fill, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.5)
    tf = sh.text_frame; tf.word_wrap = False
    tf.margin_left = 0; tf.margin_right = 0; tf.margin_top = 0; tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = label
    r.font.size = Pt(size); r.font.bold = True; r.font.color.rgb = color; r.font.name = FONT
    return sh

def header(slide, ch_no, title, sub=None):
    """顶部标题条：章节号色块 + 标题 + 副标题 + 底部细线。"""
    chip(slide, 0.5, 0.42, 0.9, 0.9, ch_no, DARK, size=26)
    txt(slide, title, 1.6, 0.42, 11.0, 0.6, size=27, bold=True, color=DARK)
    if sub:
        txt(slide, sub, 1.62, 1.0, 11.2, 0.35, size=13, color=GRAY)
    box(slide, 0.5, 1.42, 12.33, 0.03, fill=BLUE)

def card(slide, left, top, width, height, title, body, accent=BLUE, bg=LIGHT, tsize=16, bsize=12):
    box(slide, left, top, width, height, fill=bg, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.08)
    box(slide, left, top, 0.09, height, fill=accent)  # 左侧色条
    txt(slide, title, left + 0.25, top + 0.15, width - 0.4, 0.4, size=tsize, bold=True, color=accent)
    para(slide, body, left + 0.25, top + 0.55, width - 0.45, height - 0.65, size=bsize, color=TEXT)

def add_img_scaled(slide, name, left, top, width=None, height=None, max_w=12.33, max_h=5.4):
    path = os.path.join(IMG, name)
    im = Image.open(path); w, h = im.size; ratio = w / h
    if width is None and height is None:
        width = max_w; height = width / ratio
        if height > max_h:
            height = max_h; width = height * ratio
    elif width is not None:
        height = width / ratio
    else:
        width = height * ratio
    slide.shapes.add_picture(path, Inches(left), Inches(top), Inches(width), Inches(height))
    return width, height

def prompt_bar(slide, text, top=1.15, height=0.62, label='提示词'):
    box(slide, 0.5, top, 12.33, height, fill=LIGHT2, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.2)
    box(slide, 0.5, top, 0.06, height, fill=BLUE)
    chip(slide, 0.62, top + 0.12, 1.0, 0.38, label, BLUE, size=12)
    txt(slide, text, 1.78, top + 0.09, 10.9, height - 0.15, size=13.5, color=TEXT, anchor=MSO_ANCHOR.MIDDLE)

# ================= 页1 封面 =================
s = new_slide(bg=DARK)
box(s, 0, 0, 13.333, 0.12, fill=BLUE)
box(s, 0, 7.38, 13.333, 0.12, fill=BLUE)
txt(s, 'CROSS-BORDER COMPLIANCE & COST AGENT', 0.9, 1.1, 11.5, 0.5, size=15, bold=True, color=BLUE)
txt(s, '帆朵', 0.85, 1.7, 11.6, 1.5, size=76, bold=True, color=WHITE)
txt(s, '跨境出海合规与成本智能助手', 0.9, 3.25, 11.6, 0.9, size=34, bold=True, color=PALE)
box(s, 0.9, 4.25, 3.6, 0.05, fill=BLUE)
txt(s, '一句话搞定：认证准入 · 分层关税 · 到岸成本 · 风险识别 · 订单自动化', 0.9, 4.55, 11.6, 0.6, size=17, color=RGBColor(0xEA, 0xF2, 0xFB))
txt(s, '文字 · 图片 · 语音 三种输入 ｜ 覆盖 美国 / 印度 / 俄罗斯', 0.9, 5.2, 11.6, 0.5, size=14, color=PALE)
txt(s, '全国人工智能应用创新大赛 · AI Agent 赋能行业创新 · 出海方向', 0.9, 6.55, 11.6, 0.5, size=13, color=RGBColor(0x8F, 0xA8, 0xC4))

# ================= 页2 目录 =================
s = new_slide()
header(s, '目录', 'CONTENTS', '六大章节')
toc = [
    ('01', '研究背景及意义', '跨境卖家的合规与成本痛点', BLUE),
    ('02', '数据收集', '真实税率库 + 认证知识库 + 可信度分级', TEAL),
    ('03', '合规与关税分析', '多国分层关税 + 认证准入测算', ORANGE),
    ('04', '风险识别与成本预测', '到岸成本测算 + 订单异常识别', RED),
    ('05', 'Agent 应用', '架构 + 界面 + 四大场景演示', GOLD),
    ('06', '总结', '应用价值 + 体验链接', GRAY),
]
for i, (no, t, b, c) in enumerate(toc):
    y = 1.85 + i * 0.85
    box(s, 0.7, y, 11.9, 0.7, fill=LIGHT if i % 2 == 0 else LIGHT2, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.15)
    chip(s, 0.85, y + 0.12, 0.7, 0.46, no, c, size=16)
    txt(s, t, 1.75, y + 0.12, 3.4, 0.46, size=18, bold=True, color=DARK, anchor=MSO_ANCHOR.MIDDLE)
    txt(s, b, 5.2, y + 0.12, 7.2, 0.46, size=13, color=GRAY, anchor=MSO_ANCHOR.MIDDLE)

# ================= 01 研究背景 =================
s = new_slide()
header(s, '01', '研究背景及意义', '中小卖家把产品卖到海外，卡在四道坎上')
txt(s, '跨境出海是外贸增长最快的赛道，但合规与成本门槛把大量中小卖家挡在门外。传统方式是逐项翻官网、咨询报关行、试错踩坑——成本高、周期长、风险大。',
    0.5, 1.7, 12.3, 0.9, size=14.5, color=TEXT)
bg_cards = [
    ('📋 认证复杂', 'CPC / FCC / FDA / BIS / EAC… 各国强制认证名目繁多，漏一项就被海关扣货甚至销毁。', BLUE),
    ('💰 关税多变', '基础 MFN 之上叠加对华 232/301 附加税，政策频繁调整，算错税率直接吃掉利润。', ORANGE),
    ('⚠️ 风险隐蔽', 'PO Box 转口、低报逃税、危险品漏报、受制裁… 埋在海量订单里，人工盯不过来。', RED),
    ('📦 订单量大', '中小卖家一天几十上百单，逐单人工核合规、算成本不现实，急需自动化。', TEAL),
]
for i, (t, b, c) in enumerate(bg_cards):
    x = 0.5 + (i % 2) * 6.4
    y = 2.75 + (i // 2) * 2.2
    card(s, x, y, 6.0, 2.0, t, b, accent=c)

# ================= 02 数据收集 =================
s = new_slide()
header(s, '02', '数据收集', '真实数据打底，不编造数字')
txt(s, '真实 HS 税率库（SQLite，每条带来源 + 更新时间）', 0.5, 1.65, 12.3, 0.4, size=17, bold=True, color=DARK)
rows = [
    ('美国', 'USITC HTS 基础税率 + USTR/CBP 对华 232/301 附加税', '真实可核实', TEAL),
    ('印度', 'CBIC 关税表 + AIDC 附加税 + IGST', '部分估算待核实', GOLD),
    ('俄罗斯', 'EAEU 统一关税表 CCT', '部分估算待核实', GOLD),
]
y = 2.1
for c, src, tag, tc in rows:
    box(s, 0.5, y, 12.33, 0.55, fill=LIGHT, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.2)
    txt(s, c, 0.7, y + 0.12, 1.4, 0.35, size=14, bold=True, color=DARK)
    txt(s, src, 2.2, y + 0.12, 8.6, 0.35, size=13, color=TEXT)
    chip(s, 10.9, y + 0.11, 1.7, 0.34, tag, tc, size=11)
    y += 0.65
txt(s, '认证知识库：每条认证带法规编号（CPSIA / 47 CFR Part 15 / TR CU…）+ 跳过后果 + 成本区间 + 周期', 0.5, y + 0.1, 12.3, 0.5, size=13.5, color=TEXT)
txt(s, '库外产品由大模型自动归类 HS + 估算税率，覆盖率从固定品类扩展到「任意产品」', 0.5, y + 0.55, 12.3, 0.5, size=13.5, color=TEXT)

# ================= 02 可信度分级 =================
s = new_slide()
header(s, '02', '可信度分级', '核心设计：每个数字都有底气')
txt(s, 'AI 最大的信任危机是「一本正经地编数字」。帆朵对每一个关键数字强制标注三档置信度，并给出核实路径。',
    0.5, 1.7, 12.3, 0.7, size=14.5)
trust = [
    ('✅ 确定', '来自工具真实数据或公开稳定事实（如 MFN 税率、法规编号），附来源。', TEAL),
    ('⚠️ 估算', '给出区间，并说明估算依据（如认证成本、物流单价）。', GOLD),
    ('❓ 需核实', '给出具体核实路径——哪个网站、哪个编号、哪个机构，绝不空说「需确认」。', RED),
]
for i, (t, b, c) in enumerate(trust):
    y = 2.7 + i * 1.35
    box(s, 0.5, y, 12.33, 1.1, fill=LIGHT if i != 2 else RGBColor(0xFD, 0xED, 0xED), shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.12)
    box(s, 0.5, y, 0.09, 1.1, fill=c)
    txt(s, t, 0.8, y + 0.22, 2.4, 0.6, size=20, bold=True, color=c, anchor=MSO_ANCHOR.MIDDLE)
    txt(s, b, 3.4, y + 0.22, 9.2, 0.7, size=14, color=TEXT, anchor=MSO_ANCHOR.MIDDLE)

# ================= 03 合规与关税分析（关税表 + 柱状图） =================
s = new_slide()
header(s, '03', '合规与关税分析 · 分层关税', '同一件产品，不同国家关税天差地别')
# 左：表格
txt(s, '玩具（HS 9503.00.00）分层税率', 0.5, 1.65, 6.0, 0.4, size=16, bold=True, color=DARK)
tbl = s.shapes.add_table(4, 4, Inches(0.5), Inches(2.1), Inches(6.2), Inches(2.6)).table
tbl.columns[0].width = Inches(1.2)
tbl.columns[1].width = Inches(1.5)
tbl.columns[2].width = Inches(1.7)
tbl.columns[3].width = Inches(1.8)
data = [
    ('国家', '基础MFN', '附加税', '有效税率'),
    ('美国', '0%', '301: 12.5%', '12.5%'),
    ('印度', 'BCD 20%', 'AIDC 20%', '40%'),
    ('俄罗斯', 'CCT 5%', '—', '5%'),
]
for ri, row in enumerate(data):
    for ci, val in enumerate(row):
        cell = tbl.cell(ri, ci)
        cell.text = val
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = cell.text_frame.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
        r = p.runs[0]; r.font.size = Pt(12); r.font.name = FONT
        if ri == 0:
            r.font.bold = True; r.font.color.rgb = WHITE
            cell.fill.solid(); cell.fill.fore_color.rgb = DARK
        else:
            r.font.color.rgb = TEXT
            cell.fill.solid(); cell.fill.fore_color.rgb = LIGHT if ri % 2 else WHITE
        if ci == 3 and ri > 0:
            r.font.bold = True; r.font.color.rgb = ORANGE
# 右：柱状图
chart_data = CategoryChartData()
chart_data.categories = ['美国', '印度', '俄罗斯']
chart_data.add_series('玩具 9503', (12.5, 40, 5))
chart_data.add_series('锂电池 8507', (40.9, 20, 5))
gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(7.1), Inches(1.7), Inches(5.7), Inches(3.6), chart_data)
chart = gf.chart
chart.has_legend = True
chart.legend.position = XL_LEGEND_POSITION.BOTTOM
chart.legend.include_in_layout = False
chart.legend.font.size = Pt(10)
plot = chart.plots[0]
plot.gap_width = 80
txt(s, '结论：同一玩具，印度有效关税是美国 3 倍多。帆朵自动拆「基础税 + 附加税」两层并标注时效。',
    0.5, 5.0, 12.3, 0.6, size=13.5, color=GRAY)
txt(s, '来源：USITC HTS 2026 / 印度 CBIC + Budget 2025-26 / EAEU CCT（附加税标注「以最新为准」）',
    0.5, 5.6, 12.3, 0.5, size=12, color=GRAY)

# ================= 03 合规准入 =================
s = new_slide()
header(s, '03', '合规与关税分析 · 认证准入', '每条认证带法规编号 + 跳过后果 + 成本 + 周期')
txt(s, '示例：含锂电池早教玩具 → 美国', 0.5, 1.65, 8.0, 0.4, size=16, bold=True, color=DARK)
tbl2 = s.shapes.add_table(4, 5, Inches(0.5), Inches(2.1), Inches(12.3), Inches(3.4)).table
widths = [2.6, 3.4, 2.6, 1.6, 2.1]
for i, w in enumerate(widths):
    tbl2.columns[i].width = Inches(w)
data2 = [
    ('认证项', '法规编号', '跳过后果', '成本(USD)', '周期'),
    ('CPC 儿童产品证书(强制)', 'CPSIA + 16 CFR 1101/1107', '海关扣货/销毁', '300-800', '10天'),
    ('FCC Part 15(强制)', '47 CFR Part 15', '下架/罚款/召回', '500-1500', '15天'),
    ('UN 38.3(强制)', 'UN 38.3 运输鉴定', '无法正常运输/加价', '800-1500', '10天'),
]
for ri, row in enumerate(data2):
    for ci, val in enumerate(row):
        cell = tbl2.cell(ri, ci)
        cell.text = val
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = cell.text_frame.paragraphs[0]; p.alignment = PP_ALIGN.CENTER if ci >= 2 else PP_ALIGN.LEFT
        r = p.runs[0]; r.font.size = Pt(11.5); r.font.name = FONT
        if ri == 0:
            r.font.bold = True; r.font.color.rgb = WHITE
            cell.fill.solid(); cell.fill.fore_color.rgb = DARK
        else:
            r.font.color.rgb = TEXT
            cell.fill.solid(); cell.fill.fore_color.rgb = LIGHT if ri % 2 else WHITE
        if ci == 0 and ri > 0:
            r.font.bold = True; r.font.color.rgb = RED
        if ci == 2 and ri > 0:
            r.font.color.rgb = RED
txt(s, '建议项：UL/ETL 电气安全（UL 588/696，$2000-5000，约30天）。法规编号公开可核实，金额/周期为整理估算值。',
    0.5, 5.75, 12.3, 0.5, size=12.5, color=GRAY)

# ================= 04 成本预测 =================
s = new_slide()
header(s, '04', '风险识别与成本预测 · 到岸成本', '把隐形成本算清楚，避免「卖一单亏一单」')
# 左：成本构成（横向条形）
txt(s, '500 件含锂电池早教玩具（$15/件）→ 美国到岸成本构成', 0.5, 1.65, 12.3, 0.4, size=15, bold=True, color=DARK)
costs = [
    ('进口关税(12.5%)', 937.5, BLUE),
    ('认证一次性摊薄', 2700.0, RED),
    ('物流(空/海派)', 600.0, BLUE),
    ('FBA预处理/贴标', 250.0, BLUE),
    ('危险品附加费', 225.0, ORANGE),
    ('风险备用金', 150.0, GOLD),
]
maxv = 2700.0
y = 2.15
for name, val, c in costs:
    txt(s, name, 0.5, y, 2.9, 0.35, size=12, color=TEXT, anchor=MSO_ANCHOR.MIDDLE)
    bw = 5.0 * (val / maxv)
    box(s, 3.5, y + 0.02, bw, 0.3, fill=c, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.5)
    txt(s, f'${val:,.0f}', 3.55 + bw, y, 1.3, 0.35, size=12, bold=True, color=TEXT, anchor=MSO_ANCHOR.MIDDLE)
    y += 0.5
txt(s, '合计到岸成本 $12,401 · 单件 $24.8（vs 售价 $15，倒挂）', 0.5, y + 0.15, 8.0, 0.5, size=15, bold=True, color=RED)
# 右：结论卡
card(s, 7.0, 2.15, 5.8, 3.4, '关键结论', '认证一次性成本(2700)占额外成本一半以上，小批量是最大痛点。\n\n若批量放大到 5000 件，认证摊薄降到 $0.54/件，单件成本可降至 ≈$19.9。\n\n若 301 豁免生效，关税省 $937，单件再降。', accent=ORANGE, tsize=16, bsize=13)

# ================= 04 风险识别 =================
s = new_slide()
header(s, '04', '风险识别与成本预测 · 订单异常', '批量订单里自动揪出高风险')
risk_cards = [
    ('PO Box 转口', '收货地址为 PO Box，常见于货代转口，无法核实实际收货方', RED),
    ('低报嫌疑', '申报单价明显低于同类参考价（<40%），疑似逃税', RED),
    ('危险品漏报', '产品疑似含锂但「是否含锂」填否，物流按普货发出', ORANGE),
    ('认证缺失', 'BIS/FCC/EAC 等强制认证状态为「未提供/未申请」', ORANGE),
    ('受制裁地区', '目的地为俄罗斯，存在收款结算受限 + 次级制裁风险', RED),
    ('数量异常', '数量为 0 / 负数 / 远超常规阈值，疑似录入错误', GOLD),
]
for i, (t, b, c) in enumerate(risk_cards):
    x = 0.5 + (i % 3) * 4.2
    y = 1.75 + (i // 3) * 1.95
    card(s, x, y, 3.95, 1.75, t, b, accent=c, bsize=11.5)

# ================= 05 Agent 应用 · 架构 =================
s = new_slide()
header(s, '05', 'Agent 应用 · 支撑架构', 'ReAct 智能体循环 + 工具调用 + 多供应商容灾 + 多模态输入')
flow = [
    ('多模态输入', '文字 / 图片(GLM-4V-Flash) / 语音(Qwen3-ASR)', BLUE),
    ('ReAct 智能体循环', '大模型理解意图 → 决定调哪个工具 → 执行 → 迭代补全', DARK),
    ('工具层', '合规查询 · 关税查询 · 成本测算 · 订单批量处理', TEAL),
    ('数据底座', '真实 HS 税率库 + 认证知识库（SQLite，带来源）', GOLD),
    ('可信输出', '带来源 · 可信度分级 · 风险量化 · 结构化结论', RED),
]
y = 1.7
for i, (t, b, c) in enumerate(flow):
    sh = box(s, 1.1, y, 11.1, 0.78, fill=LIGHT, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.15)
    box(s, 1.1, y, 0.08, 0.78, fill=c)
    txt(s, t, 1.4, y + 0.1, 2.9, 0.6, size=15, bold=True, color=c, anchor=MSO_ANCHOR.MIDDLE)
    txt(s, b, 4.4, y + 0.1, 7.7, 0.6, size=12.5, color=TEXT, anchor=MSO_ANCHOR.MIDDLE)
    if i < len(flow) - 1:
        ar = box(s, 6.5, y + 0.79, 0.34, 0.14, fill=GRAY, shape=MSO_SHAPE.DOWN_ARROW)
    y += 0.94
txt(s, '多供应商自动容灾：JoyCode / DeepSeek / tokenrhythm 任一失效自动切换，评委无感知。历史会话按访问者隔离。',
    1.1, 6.55, 11.1, 0.5, size=12.5, color=GRAY)

# ================= 05 演示1：一句话全流程 =================
s = new_slide()
header(s, '05', 'Agent 应用 · 演示① 一句话全流程')
prompt_bar(s, '500 个含锂电池早教玩具（单价 $15）卖到美国，算合规与到岸成本')
add_img_scaled(s, 'composer_2026-11-10_08-33-16-775_26c690.png', 0.5, 1.95, width=6.0)
add_img_scaled(s, 'composer_2026-11-10_08-33-09-794_8e27ac.png', 6.85, 1.95, width=5.95)

# ================= 05 演示2：推理过程 =================
s = new_slide()
header(s, '05', 'Agent 应用 · 演示② 推理过程可视化')
prompt_bar(s, '评委可展开「🔍 推理过程」，看到 Agent 实际调用哪些工具、传什么参数、拿到什么结果——区别于 chatbot 的核心', height=0.62)
add_img_scaled(s, 'composer_2026-11-10_08-33-21-719_2e3e56.png', 0.5, 1.95, width=6.0)
add_img_scaled(s, 'composer_2026-11-10_08-33-39-006_0a1e8c.png', 6.85, 1.95, width=5.95)

# ================= 05 演示3：图片识别 + 订单自动化 =================
s = new_slide()
header(s, '05', 'Agent 应用 · 演示③ 图片识别 + 订单批量自动化')
prompt_bar(s, '上传保温杯照片→自动识别分析印度市场；上传24笔订单CSV→逐单核合规+成本，自动标出18异常/9高风险', height=0.62)
add_img_scaled(s, 'composer_2026-11-10_07-41-26-892_1c5806.png', 0.5, 1.95, width=5.95)
add_img_scaled(s, 'composer_2026-11-10_08-01-54-478_672384.png', 6.85, 1.95, width=5.95)

# ================= 06 总结 =================
s = new_slide()
header(s, '06', '总结', '应用价值与体验')
vals = [
    ('对中小卖家', '省去翻官网、咨询报关行的时间，一句话拿到合规+成本+风险全套结论，降低扣货/罚款风险。', TEAL),
    ('对订单团队', '批量订单自动处理，异常自动标出并分级，人只需处理高风险那几单，效率数倍提升。', BLUE),
    ('可信可落地', '税率来自真实官方来源，可信度分级不编造，结论可直接作为决策参考。', GOLD),
]
for i, (t, b, c) in enumerate(vals):
    card(s, 0.5, 1.75 + i * 1.35, 12.33, 1.15, t, b, accent=c, tsize=16, bsize=13)

# ================= 谢谢页 =================
s = new_slide(bg=DARK)
box(s, 0, 0, 13.333, 0.12, fill=BLUE)
box(s, 0, 7.38, 13.333, 0.12, fill=BLUE)
txt(s, '谢谢！请各位评委批评指正', 0.8, 2.2, 11.7, 1.0, size=42, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
txt(s, '帆朵 · 跨境出海合规与成本智能助手', 0.8, 3.35, 11.7, 0.6, size=20, color=PALE, align=PP_ALIGN.CENTER)
box(s, 5.17, 4.25, 3.0, 0.04, fill=BLUE)
txt(s, '智能体体验链接（密码 123456）', 0.8, 4.55, 11.7, 0.5, size=15, color=RGBColor(0xEA, 0xF2, 0xFB), align=PP_ALIGN.CENTER)
txt(s, 'https://chuhai-agent-j9evpefvwgrnu3hskvmvvh.streamlit.app/', 0.8, 5.1, 11.7, 0.5, size=14, color=BLUE, align=PP_ALIGN.CENTER)

prs.save(OUT)
print('SAVED:', OUT)
print('slides:', len(prs.slides._sldIdLst))
