"""认证 / 准入查询（美国 · 多品类结构化数据，带法规编号与来源）。

设计原则（解决「工具库未覆盖→没底气」的问题）：
- 每条认证都带 reg（法规/标准编号，可核实）、mandatory/optional（强制 vs 建议）、
  risk（跳过该认证的真实后果）、成本区间、周期。
- 关键词匹配：产品名命中 keywords 任一子串即命中该品类（如「不锈钢保温杯」→ 不锈钢品类），
  不再要求产品名和库里的名字一字不差。
金额/周期为整理估算值；法规编号为公开可核实标准，正式版接官方 RAG 逐条挂来源链接。
"""

PROFILES = [
    {
        "destination": "美国",
        "label": "儿童声光电动早教玩具",
        "keywords": ["玩具", "儿童", "早教", "积木", "玩偶", "toy"],
        "hs_hint": "9503.00.00",
        "summary": "儿童声光电动玩具是「高风险高价值」品类：CPC 是生死线，锂电池决定危险品判定。",
        "mandatory": [
            {
                "name": "CPC 儿童产品证书（CPSC 强制）",
                "reg": "CPSIA + 16 CFR 1101/1107；铅 ≤100ppm、8 种邻苯 ≤1000ppm",
                "why": "儿童产品（≤12 岁）强制第三方检测 + 儿童产品证书。",
                "risk": "无 CPC → 海关直接扣货/销毁；铅/邻苯超限是最常见召回与罚款点。",
                "one_time_cost_usd": [300, 800],
                "lead_time_days": 10,
            },
            {
                "name": "FCC Part 15（电磁兼容）",
                "reg": "47 CFR Part 15",
                "why": "含声光电路，必须过 FCC Part 15。",
                "risk": "无 FCC → 海关/平台下架、罚款、召回。",
                "one_time_cost_usd": [500, 1500],
                "lead_time_days": 15,
            },
            {
                "name": "UN 38.3 锂电池运输鉴定",
                "reg": "UN Manual of Tests and Criteria, 38.3",
                "why": "含锂电池属危险品，需运输鉴定报告。",
                "risk": "无 UN38.3 → 无法正常空运/海运，或按危险品大幅加价、拒收。",
                "one_time_cost_usd": [800, 1500],
                "lead_time_days": 10,
            },
        ],
        "optional": [
            {
                "name": "UL / ETL 电气安全",
                "reg": "UL 588 / UL 696",
                "why": "电气玩具电气安全（非强制，但平台与大买家常要求）。",
                "risk": "无 UL/ETL → 影响上架与产品责任险。",
                "one_time_cost_usd": [2000, 5000],
                "lead_time_days": 30,
            },
        ],
        "notes": [
            "附带音频/教育内容 → 注意版权 + 标签警告语言（英文）。",
            "电池供应商/电芯型号变更 → UN38.3 及电池相关测试通常需重做。",
            "小卖家最致命点：漏 CPC，货到港直接销毁。",
        ],
    },
    {
        "destination": "美国",
        "label": "不锈钢食品接触容器",
        "keywords": ["保温杯", "水杯", "餐具", "厨具", "食品接触", "焖烧杯", "饭盒", "餐盒", "马克杯", "保温瓶", "水瓶"],
        "hs_hint": "7323.93.00",
        "summary": "食品接触是 FDA 重点盯防品类：核心是 FDA 食品接触合规 + 食品设施注册，漏注册会被列入进口警示(Import Alert)。",
        "mandatory": [
            {
                "name": "FDA 食品接触合规",
                "reg": "21 CFR 174–179（间接食品添加剂）+ 300 系不锈钢 GRAS",
                "why": "300 系不锈钢对食品接触属 GRAS（一般认为安全），无需 FDA 预审批，但需材质合规声明；带涂层/塑料件需对应 21 CFR 175.300 等。",
                "risk": "材质不合规 → FDA 扣货、列入 Import Alert（长期禁入）。",
                "one_time_cost_usd": [500, 2000],
                "lead_time_days": 15,
            },
            {
                "name": "FDA 食品设施注册（FFR）",
                "reg": "21 CFR Part 1 Subpart H（FDA Food Facility Registration）",
                "why": "对美出口食品接触器具的生产/加工/出口企业须在 FDA 注册并每两年续期。",
                "risk": "漏注册/过期 → FDA 可直接拒绝放行（小卖家最高频翻车点）。",
                "one_time_cost_usd": [0, 500],
                "lead_time_days": 3,
            },
        ],
        "optional": [
            {
                "name": "加州 Prop 65 警示标签",
                "reg": "California Proposition 65",
                "why": "若产品含铅/镉/不锈钢焊接料等 Prop 65 清单物质，销往加州须贴警示标签。",
                "risk": "漏标 → 加州消费者/律师函诉讼，和解成本高。",
                "one_time_cost_usd": [200, 800],
                "lead_time_days": 7,
            },
        ],
        "notes": [
            "「保温」功能若为真空保温杯，建议同步核对 HS 9617.00（真空保温容器）的归类。",
            "带电子部件（测温/显示）→ 需另加 FCC Part 15。",
            "走亚马逊：需平台食品安全类目审核 + 合规文档上传。",
        ],
    },
    {
        "destination": "美国",
        "label": "锂电池/充电宝",
        "keywords": ["充电宝", "移动电源", "锂电", "电芯", "18650", "power bank"],
        "hs_hint": "8507.60.00",
        "summary": "含锂电池是危险品品类：UN 38.3 是空运/海运的硬门槛，且对华关税叠加严重，成本测算务必把关税打足。",
        "mandatory": [
            {
                "name": "UN 38.3 运输鉴定",
                "reg": "UN Manual of Tests and Criteria, 38.3",
                "why": "锂电池运输强制鉴定，空运/海运报关必须。",
                "risk": "无 UN38.3 → 无法运输或按危险品大幅加价、拒收。",
                "one_time_cost_usd": [800, 1500],
                "lead_time_days": 10,
            },
            {
                "name": "FCC Part 15（若带无线充电/蓝牙/电路）",
                "reg": "47 CFR Part 15",
                "why": "含电子电路/无线功能须过电磁兼容。",
                "risk": "无 FCC → 海关/平台下架。",
                "one_time_cost_usd": [500, 1500],
                "lead_time_days": 15,
            },
        ],
        "optional": [
            {
                "name": "UL 2054 / UL 1642 电池安全",
                "reg": "UL 2054（电池包）/ UL 1642（电芯）",
                "why": "平台（亚马逊）与大买家常要求电池安全认证。",
                "risk": "无 UL → 影响上架与产品责任险。",
                "one_time_cost_usd": [2000, 5000],
                "lead_time_days": 30,
            },
        ],
        "notes": [
            "对华关税叠加严重（MFN 3.4% + 301 + 新301 强迫劳动），测算务必用 query_tariff 拉真实值并留意时效。",
            "儿童可用的充电宝 → 需另加 CPC + 溯源标签。",
        ],
    },
    {
        "destination": "美国",
        "label": "蓝牙耳机/音箱",
        "keywords": ["耳机", "耳塞", "音箱", "音响", "扬声器", "earphone", "headphone", "speaker"],
        "hs_hint": "8518.30.00",
        "summary": "无线音频产品：FCC Part 15 是准入门槛；带电池再加 UN 38.3。",
        "mandatory": [
            {
                "name": "FCC Part 15（无线/电磁兼容）",
                "reg": "47 CFR Part 15",
                "why": "含蓝牙/无线功能，强制电磁兼容认证。",
                "risk": "无 FCC → 海关/平台下架、罚款。",
                "one_time_cost_usd": [500, 1500],
                "lead_time_days": 15,
            },
            {
                "name": "UN 38.3（若内置锂电池）",
                "reg": "UN Manual of Tests and Criteria, 38.3",
                "why": "内置锂电池运输强制鉴定。",
                "risk": "无 UN38.3 → 无法正常运输/加价。",
                "one_time_cost_usd": [800, 1500],
                "lead_time_days": 10,
            },
        ],
        "optional": [
            {
                "name": "加州 Prop 65",
                "reg": "California Proposition 65",
                "why": "含铅焊料/邻苯等清单物质时，销往加州需警示标签。",
                "risk": "漏标 → 诉讼/和解成本。",
                "one_time_cost_usd": [200, 800],
                "lead_time_days": 7,
            },
        ],
        "notes": [
            "音箱若为「单箱多扬声器」建议核对 HS 8518.22（多扬声器箱体）。",
            "带麦克风的耳机 → 部分平台另需通话认证说明。",
        ],
    },
    {
        "destination": "印度",
        "label": "儿童声光电动早教玩具",
        "keywords": ["玩具", "儿童", "早教", "积木", "玩偶", "toy"],
        "hs_hint": "9503.00.00",
        "summary": "印度玩具自 2021 年起强制 BIS ISI 认证，无证不可进口、不可销售。",
        "mandatory": [
            {
                "name": "BIS ISI 标志（强制）",
                "reg": "BIS IS 9873（机械/化学/易燃）/ IS 15644（电动玩具），QCO 强制自 2021",
                "why": "印度对玩具强制第三方检测 + BIS 标志。",
                "risk": "无 BIS → 海关禁止进口、查扣。",
                "one_time_cost_usd": [800, 2000],
                "lead_time_days": 120,
            },
        ],
        "optional": [],
        "notes": [
            "BIS ISI 需工厂审核（海外工厂走 FMCS 方案），周期 4–8 个月，务必提前规划。",
            "印度对华玩具另可能涉反倾销/保障措施，需核实 CBIC 最新公告。",
        ],
    },
    {
        "destination": "印度",
        "label": "不锈钢食品接触容器",
        "keywords": ["保温杯", "水杯", "餐具", "厨具", "食品接触", "焖烧杯", "饭盒", "餐盒", "马克杯", "保温瓶", "水瓶"],
        "hs_hint": "7323.93.00",
        "summary": "印度不锈钢餐具/厨具纳入 BIS QCO 强制范围；直接接触食品另需 FSSAI 合规。",
        "mandatory": [
            {
                "name": "BIS ISI 标志",
                "reg": "BIS IS 14756（不锈钢餐具/厨具）QCO",
                "why": "不锈钢制品列入印度 QCO 强制认证清单。",
                "risk": "无 BIS → 禁止进口。",
                "one_time_cost_usd": [800, 2000],
                "lead_time_days": 90,
            },
            {
                "name": "FSSAI 食品接触合规",
                "reg": "FSSAI FSSR 2011（食品接触材料）",
                "why": "直接接触食品的器具需符合 FSSAI 食品接触要求。",
                "risk": "不合规 → 海关/市场监管下架。",
                "one_time_cost_usd": [300, 1000],
                "lead_time_days": 15,
            },
        ],
        "optional": [],
        "notes": ["食品接触是印度海关抽查重点，材质报告/合规声明务必备齐。"],
    },
    {
        "destination": "印度",
        "label": "锂电池/充电宝",
        "keywords": ["充电宝", "移动电源", "锂电", "电芯", "18650", "power bank"],
        "hs_hint": "8507.60.00",
        "summary": "充电宝属电子 IT 产品，印度强制 BIS CRS 注册。",
        "mandatory": [
            {
                "name": "BIS CRS 注册",
                "reg": "BIS CRS（IS 13252 / IS 16046）",
                "why": "电子/IT 产品强制 CRS 注册。",
                "risk": "无 CRS → 禁止进口清关。",
                "one_time_cost_usd": [500, 1500],
                "lead_time_days": 150,
            },
            {
                "name": "UN 38.3 运输鉴定（若空运）",
                "reg": "UN Manual of Tests and Criteria, 38.3",
                "why": "锂电池运输强制鉴定。",
                "risk": "无 UN38.3 → 无法空运。",
                "one_time_cost_usd": [800, 1500],
                "lead_time_days": 10,
            },
        ],
        "optional": [],
        "notes": ["CRS 为送检+自我声明（无工厂审核），周期约 5–6 个月。"],
    },
    {
        "destination": "印度",
        "label": "蓝牙耳机/音箱",
        "keywords": ["耳机", "耳塞", "音箱", "音响", "扬声器", "earphone", "headphone", "speaker"],
        "hs_hint": "8518.30.00",
        "summary": "蓝牙耳机/音箱属电子 IT 产品，印度强制 BIS CRS 注册。",
        "mandatory": [
            {
                "name": "BIS CRS 注册",
                "reg": "BIS CRS（IS 13252 / IS/IEC 62368）",
                "why": "电子/IT 产品强制 CRS 注册。",
                "risk": "无 CRS → 禁止进口清关。",
                "one_time_cost_usd": [500, 1500],
                "lead_time_days": 150,
            },
        ],
        "optional": [],
        "notes": ["含电池需另加 UN38.3。"],
    },
    {
        "destination": "俄罗斯",
        "label": "儿童声光电动早教玩具",
        "keywords": ["玩具", "儿童", "早教", "积木", "玩偶", "toy"],
        "hs_hint": "9503.00.00",
        "summary": "俄罗斯/欧亚经济联盟(EAEU)玩具强制 EAC 认证。",
        "mandatory": [
            {
                "name": "EAC 认证",
                "reg": "TR CU 008/2011（玩具安全）",
                "why": "EAEU 对玩具强制 EAC 符合性认证。",
                "risk": "无 EAC → 禁止进口清关。",
                "one_time_cost_usd": [800, 2000],
                "lead_time_days": 30,
            },
        ],
        "optional": [],
        "notes": [
            "EAC 一证覆盖 EAEU 五国（俄/白俄/哈萨克/亚美尼亚/吉尔吉斯）。",
            "🔴 制裁/结算风险：对俄收款结算受限，若含美国技术/组件有次级制裁风险，需核实 OFAC/BIS 清单。",
        ],
    },
    {
        "destination": "俄罗斯",
        "label": "不锈钢食品接触容器",
        "keywords": ["保温杯", "水杯", "餐具", "厨具", "食品接触", "焖烧杯", "饭盒", "餐盒", "马克杯", "保温瓶", "水瓶"],
        "hs_hint": "7323.93.00",
        "summary": "食品接触材料需符合 EAEU 技术法规 EAC 符合性声明。",
        "mandatory": [
            {
                "name": "EAC 符合性声明",
                "reg": "TR CU 005/2011（包装/食品接触）",
                "why": "直接接触食品的材料需 EAC 符合性声明。",
                "risk": "无声明 → 禁止进口。",
                "one_time_cost_usd": [300, 1000],
                "lead_time_days": 15,
            },
        ],
        "optional": [],
        "notes": ["🔴 同制裁/结算风险，需核实结算通道。"],
    },
    {
        "destination": "俄罗斯",
        "label": "锂电池/充电宝",
        "keywords": ["充电宝", "移动电源", "锂电", "电芯", "18650", "power bank"],
        "hs_hint": "8507.60.00",
        "summary": "电子电器产品需 EAC（低压+EMC）+ EAC RoHS；含锂另需运输鉴定。",
        "mandatory": [
            {
                "name": "EAC 认证（低压 + EMC）",
                "reg": "TR CU 004/2011（低压设备）+ TR CU 020/2011（EMC）",
                "why": "电子电器强制 EAC。",
                "risk": "无 EAC → 禁止进口。",
                "one_time_cost_usd": [800, 2000],
                "lead_time_days": 30,
            },
            {
                "name": "EAC RoHS",
                "reg": "TR CU 037/2016",
                "why": "电子电器有害物质限制，2020 起强制。",
                "risk": "超限 → 禁止进入 EAEU 市场。",
                "one_time_cost_usd": [300, 800],
                "lead_time_days": 15,
            },
            {
                "name": "UN 38.3（若空运）",
                "reg": "UN Manual of Tests and Criteria, 38.3",
                "why": "锂电池运输强制鉴定。",
                "risk": "无 UN38.3 → 无法空运。",
                "one_time_cost_usd": [800, 1500],
                "lead_time_days": 10,
            },
        ],
        "optional": [],
        "notes": ["🔴 同制裁/结算风险，需核实结算通道。"],
    },
    {
        "destination": "俄罗斯",
        "label": "蓝牙耳机/音箱",
        "keywords": ["耳机", "耳塞", "音箱", "音响", "扬声器", "earphone", "headphone", "speaker"],
        "hs_hint": "8518.30.00",
        "summary": "电子电器产品需 EAC（低压+EMC）+ EAC RoHS。",
        "mandatory": [
            {
                "name": "EAC 认证（低压 + EMC）",
                "reg": "TR CU 004/2011（低压设备）+ TR CU 020/2011（EMC）",
                "why": "电子电器强制 EAC。",
                "risk": "无 EAC → 禁止进口。",
                "one_time_cost_usd": [800, 2000],
                "lead_time_days": 30,
            },
            {
                "name": "EAC RoHS",
                "reg": "TR CU 037/2016",
                "why": "电子电器有害物质限制，2020 起强制。",
                "risk": "超限 → 禁止进入 EAEU 市场。",
                "one_time_cost_usd": [300, 800],
                "lead_time_days": 15,
            },
        ],
        "optional": [],
        "notes": ["🔴 同制裁/结算风险，需核实结算通道。"],
    },
    # ================= 以下为扩品类（2026-11-08 新增 11 组） =================
    {
        "destination": "美国",
        "label": "电子配件（充电器/无线充电/数据线）",
        "keywords": ["充电器", "无线充电", "充电板", "充电头", "快充", "数据线", "编织线", "type-c", "type c", "cable", "连接线", "适配器"],
        "hs_hint": "8504.40.00",
        "summary": "电子配件：FCC Part 15 是准入门槛，平台常另要求 UL 安全。",
        "mandatory": [
            {"name": "FCC Part 15（电磁兼容）", "reg": "47 CFR Part 15", "why": "含电子电路强制 FCC。", "risk": "无 FCC → 海关/平台下架。", "one_time_cost_usd": [500, 1500], "lead_time_days": 15},
        ],
        "optional": [
            {"name": "UL / ETL 安全", "reg": "UL 60950/62368", "why": "平台与大买家常要求。", "risk": "无 → 影响上架与责任险。", "one_time_cost_usd": [1500, 4000], "lead_time_days": 30},
        ],
        "notes": ["数据线若无电子电路，FCC 可豁免，但多数带芯片仍需报备。"],
    },
    {
        "destination": "美国",
        "label": "智能手机",
        "keywords": ["智能手机", "安卓手机", "smartphone"],
        "hs_hint": "8517.13.00",
        "summary": "智能手机：FCC Part 15 + FCC ID 强制，且需 SAR 人体辐射评估。",
        "mandatory": [
            {"name": "FCC Part 15 + FCC ID", "reg": "47 CFR Part 15 + 47 CFR 2.925", "why": "含射频强制 FCC ID 认证。", "risk": "无 FCC ID → 禁止入市。", "one_time_cost_usd": [3000, 8000], "lead_time_days": 30},
        ],
        "optional": [
            {"name": "UL 安全", "reg": "UL 60950/62368", "why": "平台常要求。", "risk": "无 → 影响上架。", "one_time_cost_usd": [2000, 5000], "lead_time_days": 30},
        ],
        "notes": ["FCC ID 是硬门槛，周期长、成本高，务必提前规划。"],
    },
    {
        "destination": "美国",
        "label": "智能穿戴（手表/手环）",
        "keywords": ["智能穿戴", "运动手表", "手环", "智能手表", "smartwatch", "wearable", "手表"],
        "hs_hint": "8517.62.00",
        "summary": "智能穿戴：FCC Part 15 强制，含锂另需 UN38.3。",
        "mandatory": [
            {"name": "FCC Part 15", "reg": "47 CFR Part 15", "why": "含蓝牙/射频强制 FCC。", "risk": "无 → 海关/平台下架。", "one_time_cost_usd": [500, 1500], "lead_time_days": 15},
            {"name": "UN 38.3（若内置电池）", "reg": "UN Manual of Tests 38.3", "why": "锂电池运输鉴定。", "risk": "无 → 无法空运。", "one_time_cost_usd": [800, 1500], "lead_time_days": 10},
        ],
        "optional": [],
        "notes": [],
    },
    {
        "destination": "美国",
        "label": "个护电器（电动牙刷等）",
        "keywords": ["电动牙刷", "牙刷", "个护", "剃须", "美容仪", "吹风"],
        "hs_hint": "8509.80.00",
        "summary": "个护小家电：电气安全(UL) + 电磁兼容(FCC)。",
        "mandatory": [
            {"name": "FCC Part 15（若含电子电路）", "reg": "47 CFR Part 15", "why": "含电路强制 FCC。", "risk": "无 → 下架。", "one_time_cost_usd": [500, 1500], "lead_time_days": 15},
        ],
        "optional": [
            {"name": "UL 电气安全", "reg": "UL 859/UL 1436", "why": "平台/大买家常要求。", "risk": "无 → 影响上架。", "one_time_cost_usd": [1500, 4000], "lead_time_days": 30},
        ],
        "notes": ["内置电池另需 UN38.3。"],
    },
    {
        "destination": "美国",
        "label": "小家电（加湿器等）",
        "keywords": ["加湿器", "小家电", "净化器", "电水壶", "电风扇", "取暖器"],
        "hs_hint": "8509.80.00",
        "summary": "小家电：电气安全 UL 为核心，带电的另需 FCC。",
        "mandatory": [
            {"name": "UL / ETL 电气安全", "reg": "UL 998/UL 499", "why": "小家电电气安全是平台强制常见要求。", "risk": "无 UL → 影响上架与责任险。", "one_time_cost_usd": [1500, 4000], "lead_time_days": 30},
        ],
        "optional": [
            {"name": "FCC Part 15", "reg": "47 CFR Part 15", "why": "含电子电路时需。", "risk": "无 → 下架。", "one_time_cost_usd": [500, 1500], "lead_time_days": 15},
        ],
        "notes": [],
    },
    {
        "destination": "美国",
        "label": "照明（LED灯等）",
        "keywords": ["照明", "led", "灯串", "灯具", "灯泡", "灯带", "夜灯"],
        "hs_hint": "9405.42.00",
        "summary": "LED 照明：UL 电气安全是核心门槛。",
        "mandatory": [
            {"name": "UL 电气安全", "reg": "UL 588/UL 8750", "why": "照明产品电气安全强制常见要求。", "risk": "无 UL → 影响上架。", "one_time_cost_usd": [1500, 4000], "lead_time_days": 30},
        ],
        "optional": [
            {"name": "FCC Part 15", "reg": "47 CFR Part 15", "why": "含驱动电路时需。", "risk": "无 → 下架。", "one_time_cost_usd": [500, 1500], "lead_time_days": 15},
        ],
        "notes": [],
    },
    {
        "destination": "美国",
        "label": "无人机",
        "keywords": ["无人机", "航拍", "drone", "飞行器", "无人飞行"],
        "hs_hint": "8806.99.00",
        "summary": "无人机：FCC + 出口管制(敏感，部分含美技术/受管制)。",
        "mandatory": [
            {"name": "FCC Part 15", "reg": "47 CFR Part 15", "why": "含射频强制 FCC。", "risk": "无 → 禁止入市。", "one_time_cost_usd": [800, 2000], "lead_time_days": 15},
            {"name": "出口管制审查（敏感）", "reg": "BIS EAR 出口管制", "why": "无人机属敏感物项，含美国技术/组件可能受限。", "risk": "违规 → 法律风险。", "one_time_cost_usd": [0, 1000], "lead_time_days": 30},
        ],
        "optional": [],
        "notes": ["🔴 无人机是出口管制重点盯防品类，务必核查最终用途与收货方。"],
    },
    {
        "destination": "美国",
        "label": "监控摄像头",
        "keywords": ["摄像头", "监控", "光电", "camera", "安防", "摄像"],
        "hs_hint": "8525.89.00",
        "summary": "监控摄像头：FCC + 出口管制(部分中国厂商被 FCC 禁)。",
        "mandatory": [
            {"name": "FCC Part 15", "reg": "47 CFR Part 15", "why": "含射频强制 FCC。", "risk": "无 → 禁止入市。", "one_time_cost_usd": [500, 1500], "lead_time_days": 15},
            {"name": "出口管制/制裁审查", "reg": "FCC 设备授权名单 + BIS", "why": "部分中国摄像头厂商被 FCC 列入受限名单。", "risk": "受限 → 禁止销售。", "one_time_cost_usd": [0, 1000], "lead_time_days": 15},
        ],
        "optional": [],
        "notes": ["🔴 监控类敏感，需核查厂商是否在 FCC 受限名单。"],
    },
    {
        "destination": "美国",
        "label": "纺织服装（T恤等）",
        "keywords": ["t恤", "t恤衫", "服装", "纺织", "纯棉", "衣服", "衬衫", "针织", "裤子"],
        "hs_hint": "6109.10.00",
        "summary": "服装：易燃性 + 铅含量强制，且美国对华服装关税高(36.5%)。",
        "mandatory": [
            {"name": "纺织品易燃性", "reg": "16 CFR 1610", "why": "服装易燃性强制标准。", "risk": "不合格 → 召回/罚款。", "one_time_cost_usd": [300, 1000], "lead_time_days": 15},
            {"name": "铅含量（CPSIA）", "reg": "CPSIA 总铅 ≤100ppm", "why": "服装染料/印花铅限值。", "risk": "超标 → 召回。", "one_time_cost_usd": [200, 800], "lead_time_days": 10},
        ],
        "optional": [],
        "notes": ["对华服装关税 36.5%(MFN 16.5% + 301)，成本测算务必打足。"],
    },
    {
        "destination": "美国",
        "label": "液体/精油（易燃）",
        "keywords": ["精油", "香精", "液体", "香水", "易燃", "化学品", "香氛"],
        "hs_hint": "3301.90.00",
        "summary": "液体/精油：FDA + 易燃危险品运输是重点。",
        "mandatory": [
            {"name": "FDA 合规", "reg": "21 CFR（食品/化妆品/接触）", "why": "食用香精/精油需 FDA 合规。", "risk": "不合规 → 扣货。", "one_time_cost_usd": [300, 1000], "lead_time_days": 15},
            {"name": "危险品运输（易燃）", "reg": "IMDG/IATA 危险品规则", "why": "含醇/易燃成分按危险品运输。", "risk": "漏报 → 拒收/罚款。", "one_time_cost_usd": [300, 1000], "lead_time_days": 10},
        ],
        "optional": [{"name": "加州 Prop 65", "reg": "California Proposition 65", "why": "含清单物质需警示标签。", "risk": "漏标 → 诉讼。", "one_time_cost_usd": [200, 800], "lead_time_days": 7}],
        "notes": ["🔴 易燃液体是危险品，运输方式和申报要特别核实。"],
    },
    {
        "destination": "美国",
        "label": "一般消费品（手机壳/收纳/饰品/工具等）",
        "keywords": ["手机壳", "钥匙扣", "收纳", "饰品", "项链", "折叠椅", "工具", "小商品", "家居", "户外", "配件", "保护盖", "手机镜头", "箱包", "挂钩", "扳手", "螺丝刀", "桌", "椅"],
        "hs_hint": "3926.90.00",
        "summary": "一般消费品：无强制认证，注意铅含量与加州 Prop 65。",
        "mandatory": [],
        "optional": [
            {"name": "加州 Prop 65（如含铅/邻苯）", "reg": "California Proposition 65", "why": "含清单物质需警示标签。", "risk": "漏标 → 诉讼。", "one_time_cost_usd": [200, 800], "lead_time_days": 7},
        ],
        "notes": ["儿童用品另需 CPSIA/CPC；金属饰品注意铅含量限值。"],
    },
    # ============ 印度 ============
    {
        "destination": "印度",
        "label": "电子配件（充电器/数据线）",
        "keywords": ["充电器", "无线充电", "充电板", "充电头", "快充", "数据线", "编织线", "type-c", "cable", "连接线", "适配器"],
        "hs_hint": "8504.40.00",
        "summary": "电子配件印度强制 BIS CRS 注册。",
        "mandatory": [{"name": "BIS CRS", "reg": "BIS CRS（IS 13252）", "why": "电子 IT 产品强制 CRS。", "risk": "无 → 禁止进口。", "one_time_cost_usd": [500, 1500], "lead_time_days": 150}],
        "optional": [], "notes": [],
    },
    {
        "destination": "印度",
        "label": "智能手机",
        "keywords": ["智能手机", "安卓手机", "smartphone"],
        "hs_hint": "8517.13.00",
        "summary": "智能手机印度需 BIS CRS + TEC 型号认证。",
        "mandatory": [
            {"name": "BIS CRS", "reg": "BIS CRS（IS 13252）", "why": "电子 IT 产品强制。", "risk": "无 → 禁止进口。", "one_time_cost_usd": [500, 1500], "lead_time_days": 150},
            {"name": "TEC 型号认证", "reg": "TEC MTCTE", "why": "电信设备需 TEC 认证。", "risk": "无 → 禁止销售。", "one_time_cost_usd": [800, 2000], "lead_time_days": 90},
        ],
        "optional": [], "notes": [],
    },
    {
        "destination": "印度",
        "label": "智能穿戴（手表/手环）",
        "keywords": ["智能穿戴", "运动手表", "手环", "智能手表", "smartwatch", "wearable", "手表"],
        "hs_hint": "8517.62.00",
        "summary": "智能穿戴印度强制 BIS CRS。",
        "mandatory": [{"name": "BIS CRS", "reg": "BIS CRS（IS 13252）", "why": "电子 IT 产品强制。", "risk": "无 → 禁止进口。", "one_time_cost_usd": [500, 1500], "lead_time_days": 150}],
        "optional": [], "notes": [],
    },
    {
        "destination": "印度",
        "label": "个护/小家电/照明",
        "keywords": ["电动牙刷", "牙刷", "个护", "加湿器", "小家电", "净化器", "照明", "led", "灯串", "灯具", "电水壶", "剃须"],
        "hs_hint": "8509.80.00",
        "summary": "印度电器类强制 BIS（CRS 或 ISI 视品类）。",
        "mandatory": [{"name": "BIS CRS / ISI", "reg": "BIS CRS（IS 13252）或 ISI", "why": "电器强制 BIS。", "risk": "无 → 禁止进口。", "one_time_cost_usd": [500, 2000], "lead_time_days": 150}],
        "optional": [], "notes": ["照明/小家电可能走 ISI 路线（需工厂审核）。"],
    },
    {
        "destination": "印度",
        "label": "无人机",
        "keywords": ["无人机", "航拍", "drone", "飞行器", "无人飞行"],
        "hs_hint": "8806.99.00",
        "summary": "印度无人机受 DGCA 严格管制。",
        "mandatory": [{"name": "DGCA 无人机管制", "reg": "DGCA Digital Sky", "why": "无人机进口/运营需 DGCA 审批。", "risk": "无 → 禁止进口。", "one_time_cost_usd": [1000, 3000], "lead_time_days": 90}],
        "optional": [], "notes": ["🔴 印度无人机管制极严，进口需前置审批。"],
    },
    {
        "destination": "印度",
        "label": "监控摄像头",
        "keywords": ["摄像头", "监控", "光电", "camera", "安防", "摄像"],
        "hs_hint": "8525.89.00",
        "summary": "监控摄像头印度需 BIS CRS，且涉数据安全敏感。",
        "mandatory": [{"name": "BIS CRS", "reg": "BIS CRS", "why": "电子设备强制。", "risk": "无 → 禁止进口。", "one_time_cost_usd": [500, 1500], "lead_time_days": 150}],
        "optional": [], "notes": ["🔴 监控类敏感，印度近年对中国设备有审查。"],
    },
    {
        "destination": "印度",
        "label": "纺织服装/一般消费品",
        "keywords": ["t恤", "服装", "纺织", "纯棉", "衣服", "手机壳", "钥匙扣", "收纳", "饰品", "项链", "折叠椅", "工具", "小商品", "家居", "户外", "配件", "保护盖"],
        "hs_hint": "6109.10.00",
        "summary": "服装与一般消费品印度无强制认证（儿童/食品接触除外）。",
        "mandatory": [], "optional": [], "notes": ["儿童用品需 BIS ISI；金属饰品注意铅限值。"],
    },
    {
        "destination": "印度",
        "label": "液体/精油",
        "keywords": ["精油", "香精", "液体", "香水", "易燃", "化学品", "香氛"],
        "hs_hint": "3301.90.00",
        "summary": "液体/精油印度需 FSSAI（食用）+ 危险品运输合规。",
        "mandatory": [
            {"name": "FSSAI（食用）", "reg": "FSSAI FSSR 2011", "why": "食用香精需 FSSAI。", "risk": "无 → 禁止进口。", "one_time_cost_usd": [300, 1000], "lead_time_days": 30},
            {"name": "危险品运输", "reg": "IMDG/IATA", "why": "易燃液体按危险品。", "risk": "漏报 → 拒收。", "one_time_cost_usd": [300, 1000], "lead_time_days": 10},
        ],
        "optional": [], "notes": [],
    },
    # ============ 俄罗斯 ============
    {
        "destination": "俄罗斯",
        "label": "电子配件/手机/穿戴/个护/小家电/照明",
        "keywords": ["充电器", "无线充电", "数据线", "智能手机", "手机", "手表", "手环", "电动牙刷", "个护", "加湿器", "小家电", "照明", "led", "灯串", "灯具", "cable", "适配器"],
        "hs_hint": "8504.40.00",
        "summary": "电子电器俄罗斯强制 EAC（低压+EMC+RoHS）。",
        "mandatory": [
            {"name": "EAC 认证（低压+EMC）", "reg": "TR CU 004/2011 + TR CU 020/2011", "why": "电子电器强制 EAC。", "risk": "无 → 禁止进口。", "one_time_cost_usd": [800, 2000], "lead_time_days": 30},
            {"name": "EAC RoHS", "reg": "TR CU 037/2016", "why": "有害物质限制。", "risk": "超限 → 禁止。", "one_time_cost_usd": [300, 800], "lead_time_days": 15},
        ],
        "optional": [], "notes": ["🔴 同制裁/结算风险，需核实结算通道。"],
    },
    {
        "destination": "俄罗斯",
        "label": "无人机/监控摄像头",
        "keywords": ["无人机", "航拍", "drone", "摄像头", "监控", "光电", "camera", "安防"],
        "hs_hint": "8806.99.00",
        "summary": "无人机/监控俄罗斯涉双用途敏感，管制严格。",
        "mandatory": [
            {"name": "双用途出口审查", "reg": "EEC 双用途清单 + FSTEC", "why": "无人机/监控属双用途敏感物项。", "risk": "违规 → 法律风险。", "one_time_cost_usd": [500, 2000], "lead_time_days": 60},
        ],
        "optional": [], "notes": ["🔴 双用途敏感 + 制裁/结算双重风险，务必核查最终用途。"],
    },
    {
        "destination": "俄罗斯",
        "label": "纺织服装/一般消费品",
        "keywords": ["t恤", "服装", "纺织", "纯棉", "衣服", "手机壳", "钥匙扣", "收纳", "饰品", "项链", "折叠椅", "工具", "小商品", "家居", "户外", "配件", "保护盖"],
        "hs_hint": "6109.10.00",
        "summary": "服装与一般消费品俄罗斯需 EAC 符合性声明（一般）。",
        "mandatory": [{"name": "EAC 符合性声明", "reg": "TR CU 017/2011（轻工业品）", "why": "服装/消费品需 EAC 声明。", "risk": "无 → 禁止进口。", "one_time_cost_usd": [300, 1000], "lead_time_days": 15}],
        "optional": [], "notes": ["🔴 同制裁/结算风险。"],
    },
    {
        "destination": "俄罗斯",
        "label": "液体/精油",
        "keywords": ["精油", "香精", "液体", "香水", "易燃", "化学品", "香氛"],
        "hs_hint": "3301.90.00",
        "summary": "液体/精油俄罗斯需 EAC + 危险品运输。",
        "mandatory": [
            {"name": "EAC 符合性声明", "reg": "TR CU 009/2011（化妆品）或相关", "why": "需 EAC 声明。", "risk": "无 → 禁止。", "one_time_cost_usd": [300, 1000], "lead_time_days": 15},
            {"name": "危险品运输", "reg": "IMDG/IATA", "why": "易燃液体按危险品。", "risk": "漏报 → 拒收。", "one_time_cost_usd": [300, 1000], "lead_time_days": 10},
        ],
        "optional": [], "notes": ["🔴 同制裁/结算风险。"],
    },
]


def _match(profile, product):
    return any(k in product for k in profile["keywords"])


def check_compliance(destination, product):
    """查询认证/准入要求。关键词匹配，命中返回结构化清单。"""
    for p in PROFILES:
        if p["destination"] == destination and _match(p, product):
            return {
                "destination": destination,
                "product": product,
                "in_scope": True,
                "label": p["label"],
                "hs_hint": p["hs_hint"],
                "summary": p["summary"],
                "mandatory": p["mandatory"],
                "optional": p["optional"],
                "notes": p["notes"],
                "source_note": "法规编号为公开可核实标准；金额/周期为整理估算值，正式版接官方 RAG 逐条挂来源",
            }
    return {
        "destination": destination,
        "product": product,
        "in_scope": False,
        "message": "该品类暂无结构化数据（当前覆盖：儿童玩具 / 不锈钢食品接触容器 / 锂电池·充电宝 / 蓝牙耳机·音箱）。请用通用知识给出带法规编号的清单，并标注需核实项与核实路径。",
    }


def certification_total_cost_usd(destination, product):
    """强制认证一次性成本合计（取各认证成本区间中值求和，只算强制项）。"""
    r = check_compliance(destination, product)
    if not r.get("in_scope"):
        return 0.0
    total = sum((lo + hi) / 2 for c in r["mandatory"] for lo, hi in [c["one_time_cost_usd"]])
    return round(total, 2)
