"""评测集（带标注的陷阱订单）：用于量化「异常识别」的准确率/漏检率。

每个 case ：
- order：订单字段（只填要测的字段，其余用 _base() 默认「正常」值，避免误触发无关规则）。
- expected：正确实现应当检出的异常类型集合（完整标注，含规则耦合，如「充电宝→美国」既触发
  「危险品未标注」又触发「高关税目的地」）。

覆盖 traps：数量异常、单价异常、低报、危险品未标注/信息缺失、PO Box、原产地缺失、认证缺失、
转口、危险品申报风险、目的地缺失/制裁/未覆盖、地址缺失、邮编异常、高关税、收货方不明、干净订单。
"""


def _base(**over):
    """默认「正常」订单：儿童玩具 → 美国，字段齐全、无陷阱。"""
    o = {
        "product": "儿童声光电动早教玩具",
        "country": "美国",
        "quantity": 500,
        "unit_value_usd": 15.0,
        "has_lithium": True,
        "city": "洛杉矶", "state": "CA", "postal_code": "90001",
        "address_type": "住宅", "origin": "中国", "cert_status": "已完成",
        "notes": "",
    }
    o.update(over)
    return o


CASES = [
    # —— 数量陷阱 ——
    {"name": "数量为0", "order": _base(quantity=0), "expected": ["数量异常"]},
    {"name": "数量超阈值(6万件)", "order": _base(quantity=60000), "expected": ["数量异常"]},
    # —— 单价陷阱 ——
    {"name": "单价为负", "order": _base(unit_value_usd=-5), "expected": ["单价异常"]},
    {"name": "低报(不锈钢0.5美元)", "order": _base(product="不锈钢保温杯", unit_value_usd=0.5, country="印度"),
     "expected": ["低报嫌疑"]},
    # —— 危险品陷阱 ——
    {"name": "危险品未标注(充电宝标不含锂)", "order": _base(product="充电宝", has_lithium=False, country="印度"),
     "expected": ["危险品未标注"]},
    {"name": "危险品信息缺失(蓝牙耳机未标)", "order": _base(product="蓝牙耳机", has_lithium=None, country="印度"),
     "expected": ["危险品信息缺失"]},
    {"name": "高关税(充电宝→美国40.9%)", "order": _base(product="充电宝", unit_value_usd=20.0),
     "expected": ["高关税目的地"]},
    # —— 地址/收货陷阱 ——
    {"name": "PO Box 地址", "order": _base(address_type="PO Box"), "expected": ["PO Box 地址"]},
    {"name": "地址字段缺失", "order": _base(city=None, state=None), "expected": ["地址缺失"]},
    {"name": "邮编格式异常", "order": _base(postal_code="ABC"), "expected": ["邮编异常"]},
    {"name": "收货方不明", "order": _base(notes="备注：收货方不明"), "expected": ["收货方不明"]},
    # —— 合规/原产地陷阱 ——
    {"name": "原产地缺失", "order": _base(origin=None), "expected": ["原产地缺失"]},
    {"name": "认证缺失", "order": _base(cert_status="未提供"), "expected": ["认证缺失"]},
    # —— 转口/危险品申报陷阱 ——
    {"name": "疑似转口(货代)", "order": _base(notes="经由货代 forward 转口"), "expected": ["疑似转口贸易"]},
    {"name": "危险品申报风险(易燃液体)", "order": _base(notes="货物含易燃液体"), "expected": ["危险品申报风险"]},
    # —— 目的地陷阱 ——
    {"name": "目的地缺失", "order": _base(country=None), "expected": ["目的地缺失"]},
    {"name": "俄罗斯制裁/结算风险", "order": _base(country="俄罗斯"), "expected": ["目的地制裁/结算风险"]},
    {"name": "目的地未覆盖(日本)", "order": _base(country="日本"), "expected": ["目的地未覆盖"]},
    # —— 干净订单（测误报）——
    {"name": "干净订单(无陷阱)", "order": _base(), "expected": []},
]
