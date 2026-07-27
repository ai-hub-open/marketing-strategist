"""Генератор медиаплана и распределения бюджета в XLSX.

Запуск:
    python scripts/generate_media_plan_xlsx.py --workspace marketing-campaigns/<slug>

Создаёт `<workspace>/media_plan.xlsx` с листами:
    1. "Дашборд"   — ключевые числа + графики (бюджет по каналам и по фазам)
    2. "Сводно"    — канал × фаза × сумма (формулы =SUM, формат ₽)
    3. "По неделям"— канал × неделя × сумма
    4. "KPI"       — канал × фаза × target × ожидаемые лиды (=бюджет/target)

Фолбек: если нет openpyxl — пишем CSV с теми же листами.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _io_helpers import (  # noqa: E402
    BRAND,
    PHASE_HEX,
    PHASE_LABELS,
    channel_label,
    check_required,
    currency_sign,
    format_money,
    load_workspace,
    s,
)

MONEY_FMT_BASE = '#,##0" {sign}"'


def _channels_in_order(phases) -> list:
    out = []
    for ph in phases:
        for a in ph.get("allocation", []) or []:
            ch = a.get("channel")
            if ch and ch not in out:
                out.append(ch)
    return out


def _amount(ph, ch_key) -> int:
    for a in ph.get("allocation", []) or []:
        if a.get("channel") == ch_key:
            try:
                return int(round(float(a.get("amount", 0))))
            except (TypeError, ValueError):
                return 0
    return 0


# ─────────────────────────────── XLSX ──────────────────────────────────────
def _xlsx(workspace: Path, data: dict) -> Path:
    from openpyxl import Workbook
    from openpyxl.chart import BarChart, PieChart, Reference
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    bg = data.get("budget_allocation", {}) or {}
    kpi = data.get("kpi_framework", {}) or {}
    cur = bg.get("currency", "RUB")
    sign = currency_sign(cur)
    money_fmt = MONEY_FMT_BASE.format(sign=sign)
    phases = bg.get("phases", []) or []
    channels = _channels_in_order(phases)
    kpi_channels = kpi.get("channels", []) or []

    header_fill = PatternFill("solid", fgColor=BRAND["header_bg"])
    title_font = Font(bold=True, size=16, color=BRAND["primary"])
    header_font = Font(bold=True, color="FFFFFF")
    bold = Font(bold=True)
    center = Alignment(horizontal="center", vertical="center")
    right = Alignment(horizontal="right")
    thin = Side(style="thin", color="D0D0D0")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    zebra = PatternFill("solid", fgColor=BRAND["zebra"])

    def style_header(ws, row, ncols):
        for j in range(1, ncols + 1):
            c = ws.cell(row=row, column=j)
            c.fill = header_fill
            c.font = header_font
            c.alignment = center
            c.border = border

    def grid(ws, r0, r1, c0, c1, zebra_on=True):
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                cell = ws.cell(row=r, column=c)
                cell.border = border
            if zebra_on and (r - r0) % 2 == 1:
                for c in range(c0, c1 + 1):
                    ws.cell(row=r, column=c).fill = zebra

    wb = Workbook()

    # ============ Sheet: Сводно ============
    ws = wb.active
    ws.title = "Сводно"
    phase_names = [PHASE_LABELS.get(p.get("name", ""), p.get("name", "")) for p in phases]
    ncols = 1 + len(phases) + 1
    ws.append(["Канал"] + phase_names + ["Всего"])
    style_header(ws, 1, ncols)
    first_data = 2
    for ch in channels:
        row = [channel_label(ch)] + [_amount(ph, ch) for ph in phases]
        ws.append(row + [0])  # placeholder, заменим формулой
    last_data = ws.max_row
    # формулы "Всего" по строкам
    for r in range(first_data, last_data + 1):
        c0 = get_column_letter(2)
        c1 = get_column_letter(1 + len(phases))
        ws.cell(row=r, column=ncols).value = f"=SUM({c0}{r}:{c1}{r})"
    # строка ИТОГО
    total_row = last_data + 1
    ws.cell(row=total_row, column=1, value="ИТОГО").font = bold
    for j in range(2, ncols + 1):
        col = get_column_letter(j)
        ws.cell(row=total_row, column=j).value = f"=SUM({col}{first_data}:{col}{last_data})"
        ws.cell(row=total_row, column=j).font = bold
    # форматы
    for r in range(first_data, total_row + 1):
        for j in range(2, ncols + 1):
            cell = ws.cell(row=r, column=j)
            cell.number_format = money_fmt
            cell.alignment = right
    grid(ws, first_data, last_data, 1, ncols)
    for j in range(1, ncols + 1):
        ws.cell(row=total_row, column=j).border = border
        ws.cell(row=total_row, column=j).fill = PatternFill("solid", fgColor=BRAND["light"])
    ws.column_dimensions["A"].width = 26
    for j in range(2, ncols + 1):
        ws.column_dimensions[get_column_letter(j)].width = 16
    ws.freeze_panes = "B2"
    ws.auto_filter.ref = f"A1:{get_column_letter(ncols)}1"

    # ============ Sheet: По неделям ============
    ws2 = wb.create_sheet("По неделям")
    total_weeks = sum(int(p.get("duration_weeks", 0) or 0) for p in phases)
    wcols = 1 + total_weeks + 1
    ws2.append(["Канал"] + [f"Нед {i+1}" for i in range(total_weeks)] + ["Всего"])
    style_header(ws2, 1, wcols)
    for ch in channels:
        row = [channel_label(ch)]
        for ph in phases:
            weeks = int(ph.get("duration_weeks", 0) or 0) or 1
            per = round(_amount(ph, ch) / weeks)
            row += [per] * weeks
        ws2.append(row + [0])
    w_last = ws2.max_row
    for r in range(2, w_last + 1):
        c0 = get_column_letter(2)
        c1 = get_column_letter(1 + total_weeks)
        ws2.cell(row=r, column=wcols).value = f"=SUM({c0}{r}:{c1}{r})"
        for j in range(2, wcols + 1):
            ws2.cell(row=r, column=j).number_format = money_fmt
    grid(ws2, 2, w_last, 1, wcols)
    ws2.column_dimensions["A"].width = 26
    for j in range(2, wcols + 1):
        ws2.column_dimensions[get_column_letter(j)].width = 12
    ws2.freeze_panes = "B2"

    # ============ Sheet: KPI ============
    ws3 = wb.create_sheet("KPI")
    headers = ["Канал", "Метрика", "Target Тест", "Target Опт", "Target Масштаб",
               "Бюджет Тест", "Бюджет Опт", "Бюджет Масштаб",
               "Лиды Тест", "Лиды Опт", "Лиды Масштаб"]
    ws3.append(headers)
    style_header(ws3, 1, len(headers))
    phase_order = ("test", "optimize", "scale")
    for ch in kpi_channels:
        ch_key = ch.get("channel", "")
        targets = ch.get("targets_by_phase", {}) or {}
        budgets = []
        for pn in phase_order:
            ph = next((p for p in phases if p.get("name") == pn), None)
            budgets.append(_amount(ph, ch_key) if ph else 0)
        row = [
            channel_label(ch_key), s(ch.get("main_metric")),
            targets.get("test"), targets.get("optimize"), targets.get("scale"),
            budgets[0], budgets[1], budgets[2], None, None, None,
        ]
        ws3.append(row)
        r = ws3.max_row
        # ожидаемые лиды = бюджет / target (формула)
        for i in range(3):
            tcol = get_column_letter(3 + i)   # target
            bcol = get_column_letter(6 + i)   # budget
            lcell = ws3.cell(row=r, column=9 + i)
            lcell.value = f'=IF({tcol}{r}>0,ROUND({bcol}{r}/{tcol}{r},0),0)'
        for i in range(3):
            ws3.cell(row=r, column=6 + i).number_format = money_fmt
            ws3.cell(row=r, column=3 + i).number_format = money_fmt
    k_last = ws3.max_row
    grid(ws3, 2, k_last, 1, len(headers))
    ws3.column_dimensions["A"].width = 26
    ws3.column_dimensions["B"].width = 12
    for j in range(3, len(headers) + 1):
        ws3.column_dimensions[get_column_letter(j)].width = 14
    ws3.freeze_panes = "C2"

    # ============ Sheet: Дашборд ============
    wsd = wb.create_sheet("Дашборд", 0)
    wsd["A1"] = f"{s(data['product_name'])} — медиаплан"
    wsd["A1"].font = title_font
    wsd.merge_cells("A1:D1")

    biz = kpi.get("business_kpi", {}) or {}
    cards = [
        ("Бюджет на 3 месяца", format_money(bg.get("total_budget_3m", 0), cur)),
        ("Каналов в плане", str(len(channels))),
        ("Главный KPI",
         f"{s(biz.get('main'),'CPL')} ≤ {format_money(biz.get('target', 0), cur)}" if biz else "—"),
        ("Целевой объём", f"≥ {s(biz.get('volume_target_monthly'))}/мес" if biz else "—"),
    ]
    r = 3
    for label, value in cards:
        wsd.cell(row=r, column=1, value=label).font = Font(bold=True, color=BRAND["muted"], size=10)
        vc = wsd.cell(row=r, column=2, value=value)
        vc.font = Font(bold=True, size=13, color=BRAND["primary"])
        for cc in (1, 2):
            wsd.cell(row=r, column=cc).fill = PatternFill("solid", fgColor=BRAND["light"])
            wsd.cell(row=r, column=cc).border = border
        r += 1
    wsd.column_dimensions["A"].width = 24
    wsd.column_dimensions["B"].width = 28

    # График 1: бюджет по каналам (из "Сводно", колонка Всего)
    if channels:
        bar = BarChart()
        bar.type = "col"
        bar.title = "Бюджет по каналам, итог"
        bar.height = 7.5
        bar.width = 15
        cats = Reference(ws, min_col=1, min_row=first_data, max_row=last_data)
        vals = Reference(ws, min_col=ncols, min_row=1, max_row=last_data)
        bar.add_data(vals, titles_from_data=True)
        bar.set_categories(cats)
        bar.legend = None
        wsd.add_chart(bar, "D3")

    # График 2: бюджет по фазам (из строки ИТОГО)
    if phases:
        pie = PieChart()
        pie.title = "Доли фаз"
        pie.height = 7.5
        pie.width = 9
        cats2 = Reference(ws, min_col=2, max_col=1 + len(phases), min_row=1)
        vals2 = Reference(ws, min_col=2, max_col=1 + len(phases), min_row=total_row)
        pie.add_data(vals2, titles_from_data=False, from_rows=True)
        pie.set_categories(cats2)
        wsd.add_chart(pie, "D20")

    out = workspace / "media_plan.xlsx"
    wb.save(out)
    return out


# ─────────────────────────────── CSV fallback ──────────────────────────────
def _csv_fallback(workspace: Path, data: dict) -> Path:
    bg = data.get("budget_allocation", {}) or {}
    phases = bg.get("phases", []) or []
    channels = _channels_in_order(phases)
    base = workspace / "media_plan"
    base.mkdir(exist_ok=True)

    summary = [["Канал"] + [PHASE_LABELS.get(p.get("name", ""), p.get("name", "")) for p in phases] + ["Всего"]]
    for ch in channels:
        amounts = [_amount(ph, ch) for ph in phases]
        summary.append([channel_label(ch)] + amounts + [sum(amounts)])

    for name, rows in [("summary", summary)]:
        with (base / f"{name}.csv").open("w", encoding="utf-8", newline="") as f:
            csv.writer(f).writerows(rows)
    return base


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate media plan XLSX")
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    if not workspace.exists():
        print(f"ERROR: workspace not found: {workspace}", file=sys.stderr)
        sys.exit(1)

    data = load_workspace(workspace)
    missing = check_required(data)
    if missing:
        print(f"WARNING: missing artefacts: {', '.join(missing)}", file=sys.stderr)

    try:
        out = _xlsx(workspace, data)
        print(f"OK: {out}")
    except ImportError:
        print("openpyxl не установлен. Фолбек: CSV в media_plan/", file=sys.stderr)
        out = _csv_fallback(workspace, data)
        print(f"OK (fallback): {out}")


if __name__ == "__main__":
    main()
