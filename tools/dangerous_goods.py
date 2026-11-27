"""危险品运输合规检查（确定性知识：UN38.3 / IMDG / IATA 公开稳定规则）。

这是「分支」能力的核心：当产品含锂电池/电池时，智能体主动调用本工具，
追加查询普通合规/成本流程里没有覆盖的危险品运输要求。
"""
LITHIUM_KW = ("锂电", "电池", "充电宝", "移动电源", "电芯", "18650", "lithium", "battery")


def check_dangerous_goods(product, has_lithium_battery=False):
    """检查产品是否为危险品、含锂电池时给出运输合规要求。"""
    is_lithium = bool(has_lithium_battery) or any(
        k in (product or "").lower() for k in LITHIUM_KW
    )
    if not is_lithium:
        return {
            "product": product,
            "hazmat": False,
            "lithium": False,
            "required": [],
            "notes": ["未识别到锂电池/电池特征，按一般货物运输；若含液体、粉末、磁性或喷雾类需另行确认。"],
            "source_note": "以承运商与最新 IATA DGR / IMDG Code 为准",
        }

    required = [
        {"name": "UN38.3 测试报告", "reg": "联合国《试验和标准手册》38.3 节",
         "detail": "锂电池运输安全 8 项测试，运输前必须通过并出报告"},
        {"name": "MSDS / SDS 安全数据表", "reg": "GHS",
         "detail": "货代与承运商必查文件"},
        {"name": "UN 编号申报", "reg": "UN3480 / UN3481",
         "detail": "锂离子电池单独运输 UN3480；装在设备中/与设备同包 UN3481"},
        {"name": "UN 规格包装 + 防短路", "reg": "UN 包装规范",
         "detail": "独立包装防短路、防移动，贴 9 类危险品标 + 锂电池操作标记"},
    ]
    notes = [
        "空运（IATA DGR）：锂离子电池荷电状态通常需 ≤30%，部分客机禁运，走货前与货代确认。",
        "海运（IMDG Code）：按 9 类危险品申报，需危险品订舱。",
    ]
    return {
        "product": product,
        "hazmat": True,
        "lithium": True,
        "required": required,
        "notes": notes,
        "source_note": "UN38.3 / UN 编号 / IATA / IMDG 为公开稳定规则；具体承运商限制以最新规定为准",
    }
