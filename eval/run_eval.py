"""评测 harness：跑标注陷阱集，量化「异常识别」准确率/漏检率/耗时 + 税率/成本一致性校验。

运行：python eval/run_eval.py
产出：终端摘要 + eval/eval_report.md（硬指标，供 PPT/答辩引用）
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orders.anomaly import detect_all
from orders.processor import norm_country
from tools import tariff_db
from tools.cost import estimate_landed_cost
from eval.eval_cases import CASES


def run_case(case):
    order = case["order"]
    country = norm_country(order.get("country"))
    match_key = f"{order.get('category') or ''} {order.get('product') or ''}".strip()
    try:
        cost_info = estimate_landed_cost(
            destination=country, product=match_key,
            unit_value_usd=order.get("unit_value_usd") or 0,
            quantity=order.get("quantity") or 0,
            has_lithium_battery=bool(order.get("has_lithium")))
    except Exception:
        cost_info = None
    t0 = time.perf_counter()
    detected = detect_all(order, cost_info)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    detected_types = set(a["type"] for a in detected)
    return detected_types, elapsed_ms, detected


def compute_metrics(results):
    tp = fn = fp = 0
    for r in results:
        expected = set(r["expected"])
        detected = set(r["detected"])
        tp += len(expected & detected)
        fn += len(expected - detected)
        fp += len(detected - expected)
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    f1 = 2 * recall * precision / (recall + precision) if (recall + precision) else 0.0
    return {
        "tp": tp, "fn": fn, "fp": fp,
        "recall": recall, "precision": precision, "f1": f1,
        "漏检率": 1 - recall,
    }


def consistency_checks():
    """① 税率库内部一致（effective == 基础+附加）② 成本分项加总 == 到岸总成本。"""
    issues = []
    # ① 税率库
    import sqlite3
    db = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "tariff.db")
    conn = sqlite3.connect(db)
    rows = conn.execute("SELECT hs_code, country, mfn_pct, china_surcharge_pct, effective_pct FROM tariff_rates").fetchall()
    conn.close()
    for hs, c, mfn, sur, eff in rows:
        if abs((mfn + sur) - eff) > 0.011:
            issues.append(f"税率不一致：{hs}/{c} 基础{mfn}+附加{sur}≠有效{eff}")
    # ② 成本加总
    for p, d, q, v in [("儿童声光电动早教玩具", "美国", 500, 15.0),
                       ("不锈钢保温杯", "印度", 500, 5.0),
                       ("蓝牙耳机", "俄罗斯", 800, 12.0)]:
        try:
            ci = estimate_landed_cost(destination=d, product=p, unit_value_usd=v, quantity=q, mode="FBA大批量")
            total = ci["declared_value_usd"] + sum(ci["breakdown"].values())
            if abs(total - ci["total_landed_usd"]) > 0.05:
                issues.append(f"成本加总不一致：{p}/{d} {total}≠{ci['total_landed_usd']}")
        except Exception as e:
            issues.append(f"成本测算异常：{p}/{d} {e}")
    return len(rows), issues


def main():
    results = []
    for case in CASES:
        detected, ms, raw = run_case(case)
        expected = set(case["expected"])
        missed = expected - detected
        extra = detected - expected
        results.append({
            "name": case["name"], "expected": case["expected"],
            "detected": sorted(detected), "missed": sorted(missed),
            "extra": sorted(extra), "elapsed_ms": round(ms, 2),
        })

    m = compute_metrics(results)
    n_rows, cons_issues = consistency_checks()
    latencies = [r["elapsed_ms"] for r in results]

    # —— 终端摘要 ——
    print("=" * 60)
    print("帆朵 · 异常识别评测报告")
    print("=" * 60)
    for r in results:
        ok = "✅" if not r["missed"] and not r["extra"] else ("⚠️" if r["missed"] else "➕")
        print(f"{ok} {r['name']:<28} 检出{len(r['detected'])} 漏检{r['missed']} 误报{r['extra']} ({r['elapsed_ms']}ms)")
    print("-" * 60)
    print(f"用例数: {len(CASES)}")
    print(f"标注异常总数: {m['tp'] + m['fn']}  正确识别(TP): {m['tp']}  漏检(FN): {m['fn']}  误报(FP): {m['fp']}")
    print(f"召回率 Recall: {m['recall']:.1%}   精确率 Precision: {m['precision']:.1%}   F1: {m['f1']:.3f}")
    print(f"漏检率: {m['漏检率']:.1%}   平均耗时: {sum(latencies)/len(latencies):.1f}ms   最慢: {max(latencies):.1f}ms")
    print(f"税率库行数: {n_rows}  一致性: {'✅ 全部一致' if not cons_issues else f'❌ {len(cons_issues)} 处不一致'}")
    for i in cons_issues:
        print("  -", i)

    # —— 写报告 ——
    report = [
        "# 帆朵 · 异常识别评测报告", "",
        f"生成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}", "",
        "## 一、核心指标", "",
        f"| 指标 | 值 |", "|---|---|",
        f"| 用例数 | {len(CASES)} |",
        f"| 标注陷阱总数 | {m['tp'] + m['fn']} |",
        f"| 正确识别 (TP) | {m['tp']} |",
        f"| 漏检 (FN) | {m['fn']} |",
        f"| 误报 (FP) | {m['fp']} |",
        f"| 召回率 Recall | {m['recall']:.1%} |",
        f"| 精确率 Precision | {m['precision']:.1%} |",
        f"| F1 | {m['f1']:.3f} |",
        f"| 漏检率 | {m['漏检率']:.1%} |",
        f"| 平均单笔耗时 | {sum(latencies)/len(latencies):.1f} ms |",
        f"| 最慢单笔耗时 | {max(latencies):.1f} ms |",
        "", "## 二、逐用例明细", "",
        "| 用例 | 期望检出 | 实际检出 | 漏检 | 误报 | 耗时 |", "|---|---|---|---|---|---|",
    ]
    for r in results:
        report.append(
            f"| {r['name']} | {', '.join(r['expected']) or '（无陷阱）'} | "
            f"{', '.join(r['detected']) or '（无）'} | {', '.join(r['missed']) or '—'} | "
            f"{', '.join(r['extra']) or '—'} | {r['elapsed_ms']}ms |")
    report += ["", "## 三、税率库与成本一致性", "",
               f"- 税率库共 **{n_rows}** 条，内部一致（有效=基础+附加）：**{'✅ 全部通过' if not cons_issues else '❌ ' + str(len(cons_issues)) + ' 处异常'}**"]
    if cons_issues:
        for i in cons_issues:
            report.append(f"- {i}")
    report += ["", "> 说明：异常识别为确定性规则（无 LLM），可复现、零幻觉、零 API 成本。漏检/误报均为 0 代表规则覆盖完整。"]
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eval_report.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(report))
    print(f"\n报告已写入: {out}")


if __name__ == "__main__":
    main()
