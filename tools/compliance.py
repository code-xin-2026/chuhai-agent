"""认证 / 准入查询（美国 · 儿童声光电动早教玩具 深度案例数据）。

数据为整理的研究资料；金额/限值标注为【估算值】，正式版接入官方法规文档(RAG)并带来源引用。
"""

COMPLIANCE_PROFILE = {
    "美国": {
        "儿童声光电动早教玩具": {
            "summary": "儿童声光电动玩具是「高风险高价值」品类：CPC 是生死线，锂电池决定危险品判定，两者直接决定物流与仓储成本。",
            "mandatory": [
                {
                    "name": "CPC 儿童产品证书（CPSC 强制）",
                    "why": "儿童产品（≤12 岁）强制第三方检测 + 儿童产品证书；铅 ≤100ppm、邻苯(DEHP 等 8 种) ≤1000ppm 限值。",
                    "risk": "无 CPC → 海关直接扣货/销毁；铅/邻苯超限是最常见召回与罚款点。",
                    "one_time_cost_usd": [300, 800],
                    "lead_time_days": 10,
                },
                {
                    "name": "FCC 认证（电磁兼容）",
                    "why": "含声光电路，必须过 FCC Part 15。",
                    "risk": "无 FCC → 海关/平台下架、罚款、召回。",
                    "one_time_cost_usd": [500, 1500],
                    "lead_time_days": 15,
                },
                {
                    "name": "UL / ETL 电气安全",
                    "why": "电气玩具电气安全（非强制，但平台与大买家常要求）。",
                    "risk": "无 UL/ETL → 影响上架与产品责任险，召回风险高。",
                    "one_time_cost_usd": [2000, 5000],
                    "lead_time_days": 30,
                },
                {
                    "name": "UN 38.3 锂电池运输鉴定",
                    "why": "含锂电池属危险品，需运输鉴定报告（UN38.3）。",
                    "risk": "无 UN38.3 → 无法正常空运/海运，或按危险品大幅加价、拒收。",
                    "one_time_cost_usd": [800, 1500],
                    "lead_time_days": 10,
                },
            ],
            "notes": [
                "附带音频/教育内容 → 注意版权 + 标签警告语言（英文）。",
                "电池供应商/电芯型号变更 → UN38.3 及电池相关测试通常需重做。",
                "小卖家最致命点：漏 CPC，货到港直接销毁。",
            ],
        },
    },
}


def check_compliance(destination: str, product: str):
    """查询认证/准入要求（含风险与一次性成本）。"""
    profile = COMPLIANCE_PROFILE.get(destination, {}).get(product)
    if profile is None:
        return {
            "destination": destination,
            "product": product,
            "in_scope": False,
            "message": "该国家/产品暂不在当前数据范围内（当前仅覆盖：美国 · 儿童声光电动早教玩具），能力正在扩展。",
        }
    return {
        "destination": destination,
        "product": product,
        "in_scope": True,
        **profile,
        "source_note": "金额/限值为整理估算值，正式版接入官方法规(RAG)并带来源引用",
    }


def certification_total_cost_usd(destination: str, product: str):
    """认证一次性成本合计（取各认证成本区间中值求和）。"""
    profile = COMPLIANCE_PROFILE.get(destination, {}).get(product)
    if profile is None:
        return 0.0
    total = sum((lo + hi) / 2 for c in profile["mandatory"] for lo, hi in [c["one_time_cost_usd"]])
    return round(total, 2)
