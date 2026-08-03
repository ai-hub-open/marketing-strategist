"""Генератор одностраничного саммари в PDF — для отправки клиенту.

Запуск:
    python scripts/generate_pdf_summary.py --workspace marketing-campaigns/<slug>

Создаёт `<workspace>/strategy_summary.pdf` (одна страница A4):
  • цветной хедер-баннер с продуктом и датой
  • KPI-карточки
  • таблицы «Площадки» и «Бюджет по фазам» с цветовой кодировкой
  • футер с датой

Зависимости: reportlab. Фолбек — markdown, если reportlab недоступен.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _io_helpers import (  # noqa: E402
    BRAND,
    PHASE_HEX,
    PHASE_LABELS,
    PRIORITY_COLORS,
    channel_label,
    currency_sign,
    format_money,
    load_workspace,
    s,
)

RU_MONTHS = ["", "января", "февраля", "марта", "апреля", "мая", "июня",
             "июля", "августа", "сентября", "октября", "ноября", "декабря"]


def _today_ru() -> str:
    d = _dt.date.today()
    return f"{d.day} {RU_MONTHS[d.month]} {d.year}"


def _register_font():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    reg, bold = "Helvetica", "Helvetica-Bold"
    base = "/usr/share/fonts/truetype/dejavu"
    cands = [
        (f"{base}/DejaVuSans.ttf", f"{base}/DejaVuSans-Bold.ttf"),
        ("/usr/share/fonts/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"),
        ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
        # macOS: ни один из путей выше здесь не существует, без этих строк
        # фолбэк уходил в Helvetica и кириллица в PDF не рисовалась.
        ("/System/Library/Fonts/Supplemental/Arial.ttf",
         "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
        ("/Library/Fonts/Arial.ttf", "/Library/Fonts/Arial Bold.ttf"),
        ("/opt/homebrew/share/fonts/DejaVuSans.ttf",
         "/opt/homebrew/share/fonts/DejaVuSans-Bold.ttf"),
    ]
    for r, b in cands:
        if Path(r).exists():
            try:
                pdfmetrics.registerFont(TTFont("Body", r))
                reg = "Body"
                if Path(b).exists():
                    pdfmetrics.registerFont(TTFont("Body-Bold", b))
                    bold = "Body-Bold"
                else:
                    bold = "Body"
                break
            except Exception:
                pass

    if reg == "Helvetica":
        # Молчать нельзя: PDF соберётся, скрипт отчитается «OK», а кириллица
        # выйдет пустыми прямоугольниками — встроенные шрифты её не рисуют.
        print(
            "WARN: не найден системный шрифт с кириллицей — в PDF русский текст "
            "будет нечитаемым.\n"
            "      Linux: sudo apt install fonts-dejavu-core · macOS: Arial в "
            "/System/Library/Fonts/Supplemental/ · Windows: C:/Windows/Fonts/arial.ttf",
            file=sys.stderr,
        )
    return reg, bold


def _pdf(workspace: Path, data: dict) -> Path:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
    )

    reg, bold = _register_font()
    primary = colors.HexColor("#" + BRAND["primary"])
    accent = colors.HexColor("#" + BRAND["accent"])
    muted = colors.HexColor("#" + BRAND["muted"])

    cs = data.get("channel_selection", {}) or {}
    top3 = cs.get("top3", []) or []
    bg = data.get("budget_allocation", {}) or {}
    kpi = data.get("kpi_framework", {}) or {}
    usp = data.get("usp_final", {}) or {}
    biz = kpi.get("business_kpi", {}) or {}
    cur = bg.get("currency", "RUB")
    product = s(data["product_name"])

    out = workspace / "strategy_summary.pdf"

    BAND_H = 2.3 * cm

    def decorate(canvas, doc):
        w, h = A4
        # хедер-баннер
        canvas.setFillColor(primary)
        canvas.rect(0, h - BAND_H, w, BAND_H, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor("#" + BRAND["accent"]))
        canvas.rect(0, h - BAND_H, w, 0.12 * cm, fill=1, stroke=0)  # тонкая акцентная линия снизу баннера
        canvas.setFillColor(colors.white)
        canvas.setFont(bold, 18)
        canvas.drawString(1.5 * cm, h - 1.15 * cm, product)
        canvas.setFont(reg, 9.5)
        canvas.drawString(1.5 * cm, h - 1.75 * cm, "Маркетинговая стратегия — саммари для согласования")
        canvas.setFont(reg, 9)
        canvas.drawRightString(w - 1.5 * cm, h - 1.15 * cm, _today_ru())
        # футер
        canvas.setFillColor(muted)
        canvas.setFont(reg, 7.5)
        canvas.drawString(1.5 * cm, 1.0 * cm,
                          "Подробности — в marketing_strategy.docx и media_plan.xlsx")
        canvas.drawRightString(w - 1.5 * cm, 1.0 * cm, f"{product} · {_today_ru()}")

    doc = SimpleDocTemplate(
        str(out), pagesize=A4,
        leftMargin=1.5 * cm, rightMargin=1.5 * cm,
        topMargin=BAND_H + 0.5 * cm, bottomMargin=1.5 * cm,
    )

    h2 = ParagraphStyle("H2", fontName=bold, fontSize=12, spaceBefore=8,
                        spaceAfter=5, textColor=primary)
    normal = ParagraphStyle("N", fontName=reg, fontSize=9, leading=12)
    card_lbl = ParagraphStyle("CL", fontName=reg, fontSize=7.5, textColor=muted,
                              leading=9)
    card_val = ParagraphStyle("CV", fontName=bold, fontSize=11.5, textColor=primary,
                              leading=13)
    cell = ParagraphStyle("C", fontName=reg, fontSize=8.5, leading=10.5)
    cell_b = ParagraphStyle("CB", fontName=bold, fontSize=8.5, leading=10.5)
    cell_w = ParagraphStyle("CW", fontName=bold, fontSize=8.5, leading=10,
                            textColor=colors.white, alignment=1)

    story = []

    if usp.get("primary", {}).get("text"):
        story.append(Paragraph(f"<b>УТП:</b> {usp['primary']['text']}", normal))
        story.append(Spacer(1, 0.25 * cm))

    # KPI-карточки
    def card(label, value):
        return Table([[Paragraph(label, card_lbl)], [Paragraph(value, card_val)]],
                     colWidths=[4.05 * cm], rowHeights=[0.55 * cm, 0.7 * cm])

    cards_data = [
        ("Бюджет на 3 месяца", format_money(bg.get("total_budget_3m", 0), cur)),
        ("Главный KPI",
         f"{s(biz.get('main'),'CPL')} ≤ {format_money(biz.get('target', 0), cur)}" if biz else "—"),
        ("Объём", f"≥ {s(biz.get('volume_target_monthly'))}/мес" if biz else "—"),
        ("Payback", f"≤ {s(biz.get('payback_months'))} мес" if biz else "—"),
    ]
    cards_row = Table(
        [[card(l, v) for l, v in cards_data]],
        colWidths=[4.5 * cm] * 4,
    )
    cards_row.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#" + BRAND["light"])),
        ("BOX", (0, 0), (0, 0), 0.5, colors.white),
        ("INNERGRID", (0, 0), (-1, -1), 3, colors.white),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(cards_row)
    story.append(Spacer(1, 0.35 * cm))

    # Площадки
    if top3:
        story.append(Paragraph("Рекомендация по площадкам", h2))
        tdata = [[Paragraph("Приоритет", cell_w), Paragraph("Канал", cell_w),
                  Paragraph("Зачем", cell_w)]]
        style = [
            ("BACKGROUND", (0, 0), (-1, 0), primary),
            ("FONTNAME", (0, 0), (-1, -1), reg),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#C8C8C8")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
        for i, c in enumerate(top3, start=1):
            rationale = s(c.get("rationale"), "")
            short = rationale[:130] + ("…" if len(rationale) > 130 else "")
            tdata.append([
                Paragraph(str(s(c.get("priority"))), cell_w),
                Paragraph(channel_label(c.get("channel", "")), cell_b),
                Paragraph(short, cell),
            ])
            try:
                pc = colors.HexColor("#" + PRIORITY_COLORS.get(int(c.get("priority")), BRAND["muted"]))
            except (TypeError, ValueError):
                pc = colors.HexColor("#" + BRAND["muted"])
            style.append(("BACKGROUND", (0, i), (0, i), pc))
            if i % 2 == 0:
                style.append(("BACKGROUND", (1, i), (-1, i), colors.HexColor("#" + BRAND["zebra"])))
        tbl = Table(tdata, colWidths=[2.4 * cm, 4.8 * cm, 10.8 * cm])
        tbl.setStyle(TableStyle(style))
        story.append(tbl)
        story.append(Spacer(1, 0.35 * cm))

    # Бюджет по фазам
    if bg.get("phases"):
        story.append(Paragraph("Бюджет по фазам", h2))
        pdata = [[Paragraph(x, cell_w) for x in ("Фаза", "Срок", "Бюджет", "Доля")]]
        style = [
            ("BACKGROUND", (0, 0), (-1, 0), primary),
            ("FONTNAME", (0, 0), (-1, -1), reg),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#C8C8C8")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
        for i, ph in enumerate(bg["phases"], start=1):
            name = ph.get("name", "")
            try:
                share = f"{int(round(float(ph.get('share', 0)) * 100))}%"
            except (TypeError, ValueError):
                share = "—"
            pdata.append([
                Paragraph(PHASE_LABELS.get(name, name), cell_b),
                Paragraph(f"{s(ph.get('duration_weeks'))} нед", cell),
                Paragraph(format_money(ph.get("budget", 0), cur), cell),
                Paragraph(share, cell),
            ])
            hexc = PHASE_HEX.get(name)
            if hexc:
                style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#" + hexc)))
        tbl = Table(pdata, colWidths=[5 * cm, 4 * cm, 5 * cm, 4 * cm])
        tbl.setStyle(TableStyle(style))
        story.append(tbl)

    doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
    return out


def _md_fallback(workspace: Path, data: dict) -> Path:
    lines = [f"# {data['product_name']} — Маркетинговая стратегия (саммари)",
             "", f"_Дата: {_today_ru()}_", ""]
    cs = data.get("channel_selection", {}) or {}
    top3 = cs.get("top3", []) or []
    bg = data.get("budget_allocation", {}) or {}
    kpi = data.get("kpi_framework", {}) or {}
    usp = data.get("usp_final", {}) or {}
    if usp.get("primary", {}).get("text"):
        lines += [f"**Основное УТП:** {usp['primary']['text']}", ""]
    if top3:
        lines += ["## Рекомендация по площадкам", ""]
        for c in top3:
            rationale = s(c.get("rationale"), "")
            short = rationale[:150] + ("…" if len(rationale) > 150 else "")
            lines.append(f"- **Приоритет {s(c.get('priority'))}: {channel_label(c.get('channel', ''))}** — {short}")
        lines.append("")
    if bg.get("phases"):
        lines += ["## Бюджет по фазам", ""]
        for ph in bg["phases"]:
            name = PHASE_LABELS.get(ph.get("name", ""), ph.get("name", ""))
            try:
                share = f"{int(round(float(ph.get('share', 0)) * 100))}%"
            except (TypeError, ValueError):
                share = "—"
            lines.append(f"- **{name}** ({s(ph.get('duration_weeks'))} нед, {share}): "
                         f"{format_money(ph.get('budget', 0), bg.get('currency', 'RUB'))}")
        lines.append("")
    biz = kpi.get("business_kpi", {}) or {}
    if biz:
        lines += ["## Бизнес-KPI", "",
                  f"- {s(biz.get('main'),'CPL')} target: {format_money(biz.get('target', 0), bg.get('currency', 'RUB'))}",
                  f"- Объём: ≥ {s(biz.get('volume_target_monthly'))} в месяц",
                  f"- Payback: ≤ {s(biz.get('payback_months'))} месяцев"]
    out = workspace / "strategy_summary.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate strategy summary PDF (1 page)")
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    if not workspace.exists():
        print(f"ERROR: workspace not found: {workspace}", file=sys.stderr)
        sys.exit(1)

    data = load_workspace(workspace)
    try:
        out = _pdf(workspace, data)
        print(f"OK: {out}")
    except ImportError:
        print("reportlab не установлен. Фолбек: strategy_summary.md", file=sys.stderr)
        out = _md_fallback(workspace, data)
        print(f"OK (fallback): {out}")


if __name__ == "__main__":
    main()
