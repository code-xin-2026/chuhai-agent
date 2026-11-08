"""订单导入：解析 CSV/Excel → 标准化订单结构（列名容错）。

真实店铺导出的订单表头五花八门，这里做容错映射：把各种可能的列名归一化到标准字段。
缺失的字段填 None，交给异常检测去标（而不是解析时直接报错）。
"""
import csv
import io
import os

STANDARD_FIELDS = [
    "order_id", "buyer_name", "product", "category", "quantity", "unit_value_usd",
    "country", "city", "state", "postal_code", "has_lithium", "mode",
    "notes", "address_type", "origin", "cert_status",
]

# 别名映射：同义词 → 标准字段
ALIASES = {
    "order_id": ["订单号", "订单编号", "orderid", "order_id", "orderno", "order_no", "订单id", "id"],
    "buyer_name": ["买家", "买家名", "buyer", "buyername", "buyer_name", "客户", "客户名", "收件人", "consignee", "name", "收货人"],
    "product": ["产品", "产品名", "品名", "商品名称", "商品名", "product", "productname", "product_name", "商品", "goods", "item", "sku", "sku名称"],
    "category": ["品类", "产品类别", "类别", "类目", "分类", "category", "cat"],
    "quantity": ["数量", "件数", "qty", "quantity", "数量(件)", "数量（件）", "units", "数量(pcs)"],
    "unit_value_usd": ["单价", "单价usd", "单价(usd)", "单价（usd）", "unitprice", "unit_price", "price", "value", "单价(美元)", "申报单价"],
    "country": ["国家", "目的地", "目的地国家", "country", "destination", "目的国", "shipcountry", "ship_country", "国家/地区", "国家地区", "目的国家"],
    "city": ["城市", "city", "收货城市", "市"],
    "state": ["州", "省", "州/省", "州省", "state", "province", "省份", "州(省)"],
    "postal_code": ["邮编", "邮政编码", "zip", "postcode", "postal_code", "zipcode", "postalcode", "邮编/邮政编码"],
    "has_lithium": ["是否含锂电池", "含锂电池", "是否含锂", "锂电池", "haslithium", "has_lithium", "battery", "是否带电", "带电", "是否含电池"],
    "mode": ["物流方式", "运输方式", "走货方式", "mode", "shipping", "物流", "shipmode", "ship_mode", "发货方式"],
    "notes": ["备注", "说明", "备注说明", "notes", "remark", "remarks", "comment", "订单备注"],
    "address_type": ["地址类型", "地址性质", "address_type", "addresstype", "收件地址类型"],
    "origin": ["原产地", "产地", "origin", "原产国", "生产国"],
    "cert_status": ["认证状态", "认证情况", "cert_status", "certstatus", "认证"],
}


def _norm(s):
    """统一小写、去空格，用于别名匹配。"""
    return (s or "").strip().lower().replace(" ", "").replace("　", "")


def _build_alias_map():
    m = {}
    for field, aliases in ALIASES.items():
        for a in aliases:
            m[_norm(a)] = field
    return m


def _to_int(v):
    try:
        return int(float(str(v).replace(",", "").strip()))
    except (ValueError, TypeError):
        return None


def _to_float(v):
    try:
        return float(str(v).replace(",", "").replace("$", "").replace("￥", "").strip())
    except (ValueError, TypeError):
        return None


def _to_bool(v):
    s = _norm(str(v))
    if s in ("是", "有", "含", "true", "yes", "y", "1", "带", "带电", "含电池"):
        return True
    if s in ("否", "无", "不含", "false", "no", "n", "0", "不带", "不含电池"):
        return False
    return None


def _rows_to_orders(rows):
    if not rows:
        return []
    header = rows[0]
    alias_map = _build_alias_map()
    col_map = {}
    for i, h in enumerate(header):
        field = alias_map.get(_norm(h))
        if field:
            col_map[i] = field
    orders = []
    for row in rows[1:]:
        if not row or all(not str(c).strip() for c in row):
            continue
        o = {f: None for f in STANDARD_FIELDS}
        for i, field in col_map.items():
            val = str(row[i]).strip() if i < len(row) else ""
            if field == "quantity":
                o[field] = _to_int(val)
            elif field == "unit_value_usd":
                o[field] = _to_float(val)
            elif field == "has_lithium":
                o[field] = _to_bool(val)
            else:
                o[field] = val or None
        orders.append(o)
    return orders


def parse_csv_text(text):
    """解析 CSV 文本 → 标准订单列表。"""
    try:
        rows = list(csv.reader(io.StringIO(text)))
    except Exception:
        return []
    return _rows_to_orders(rows)


def parse_file(path):
    """解析文件（.csv / .xlsx / .xls）→ 标准订单列表。"""
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xls"):
        return parse_xlsx(path)
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        return parse_csv_text(f.read())


def parse_xlsx(path):
    """解析 Excel（需 openpyxl）。"""
    try:
        import openpyxl
    except ImportError:
        raise RuntimeError("读取 Excel 需要 openpyxl，请 pip install openpyxl 或改用 CSV")
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows = [[str(c.value) if c.value is not None else "" for c in row] for row in ws.iter_rows()]
    wb.close()
    return _rows_to_orders(rows)


def describe_orders(orders):
    """订单摘要：总数 + 按国家分组计数。"""
    by_country = {}
    for o in orders:
        c = o.get("country") or "未填"
        by_country[c] = by_country.get(c, 0) + 1
    return {"total": len(orders), "by_country": by_country}
