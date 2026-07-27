"""Генератор основного стратегического отчёта в DOCX для медиабайера.

Запуск:
    python scripts/generate_strategy_doc.py --workspace marketing-campaigns/<slug>

Создаёт `<workspace>/marketing_strategy.docx`:
  • титульная страница с датой и палитрой бренда
  • оглавление (Word-поле, обновляется по F9 / правый клик → Обновить поле)
  • колонтитул с номером страницы и продуктом
  • Executive Summary в виде выделенного блока
  • цветовая кодировка приоритетов каналов
  • markdown-секции рендерятся настоящими заголовками/списками/таблицами,
    а не сырым текстом с ## и |

Зависимости: python-docx (если нет — фолбек в .md рядом).
"""
from __future__ import annotations

import argparse
import datetime as _dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _io_helpers import (  # noqa: E402
    BRAND,
    PHASE_GOALS,
    PHASE_LABELS,
    PRIORITY_COLORS,
    channel_label,
    check_required,
    currency_sign,
    format_money,
    load_workspace,
    parse_inline,
    parse_markdown,
    s,
)

RU_MONTHS = [
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]


def _today_ru() -> str:
    d = _dt.date.today()
    return f"{d.day} {RU_MONTHS[d.month]} {d.year}"


# ────────────────────────── low-level docx helpers ──────────────────────────
def _shade(cell, hex_color: str) -> None:
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def _set_cell(cell, text, *, bold=False, color=None, align=None, size=None, italic=False):
    from docx.shared import Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    cell.text = ""
    p = cell.paragraphs[0]
    if align == "center":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif align == "right":
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = p.add_run(s(text, ""))
    run.bold = bold
    run.italic = italic
    if size:
        run.font.size = Pt(size)
    if color:
        run.font.color.rgb = RGBColor.from_string(color)


def _table_borders(table, color="BFBFBF", sz=4) -> None:
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    tblPr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), str(sz))
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), color)
        borders.append(el)
    tblPr.append(borders)


def _add_inline(paragraph, text: str) -> None:
    """Добавить в параграф текст с инлайн **bold**."""
    for seg, bold in parse_inline(text):
        run = paragraph.add_run(seg)
        run.bold = bold


def _render_md(doc, md: str, base_level: int = 2, max_blocks: int = 400) -> None:
    """Отрендерить markdown как настоящие блоки Word."""
    from docx.shared import Pt, RGBColor

    blocks = parse_markdown(md)
    if not blocks:
        doc.add_paragraph("—")
        return
    for blk in blocks[:max_blocks]:
        t = blk["type"]
        if t == "heading":
            lvl = min(base_level + blk["level"] - 1, 5)
            h = doc.add_heading("", level=lvl)
            _add_inline(h, blk["text"])
        elif t == "paragraph":
            p = doc.add_paragraph()
            _add_inline(p, blk["text"])
        elif t == "list":
            style = "List Number" if blk.get("ordered") else "List Bullet"
            for item in blk["items"]:
                p = doc.add_paragraph(style=style)
                _add_inline(p, item)
        elif t == "table":
            header = blk["header"]
            rows = blk["rows"]
            cols = max(len(header), *(len(r) for r in rows)) if rows else len(header)
            if cols == 0:
                continue
            table = doc.add_table(rows=1, cols=cols)
            _table_borders(table)
            for j in range(cols):
                cell = table.rows[0].cells[j]
                _shade(cell, BRAND["header_bg"])
                _set_cell(cell, header[j] if j < len(header) else "",
                          bold=True, color="FFFFFF", size=9)
            for ri, r in enumerate(rows):
                cells = table.add_row().cells
                if ri % 2 == 1:
                    for c in cells:
                        _shade(c, BRAND["zebra"])
                for j in range(cols):
                    _set_cell(cells[j], r[j] if j < len(r) else "", size=9)
            doc.add_paragraph()


def _footer_with_page_number(doc, product_name: str) -> None:
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    from docx.shared import Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    section = doc.sections[0]
    footer = section.footer
    p = footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(f"{product_name}  ·  Маркетинговая стратегия  ·  стр. ")
    run.font.size = Pt(8)
    run.font.color.rgb = RGBColor.from_string(BRAND["muted"])
    # поле PAGE
    fldStart = OxmlElement("w:fldSimple")
    fldStart.set(qn("w:instr"), "PAGE")
    r = OxmlElement("w:r")
    rpr = OxmlElement("w:rPr")
    sz = OxmlElement("w:sz"); sz.set(qn("w:val"), "16"); rpr.append(sz)
    r.append(rpr)
    t = OxmlElement("w:t"); t.text = "1"; r.append(t)
    fldStart.append(r)
    p._p.append(fldStart)


def _add_toc(doc) -> None:
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    p = doc.add_paragraph()
    run = p.add_run()
    fldBegin = OxmlElement("w:fldChar"); fldBegin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText"); instr.set(qn("xml:space"), "preserve")
    instr.text = 'TOC \\o "1-2" \\h \\z \\u'
    fldSep = OxmlElement("w:fldChar"); fldSep.set(qn("w:fldCharType"), "separate")
    hint = OxmlElement("w:t")
    hint.text = "Оглавление обновится по правому клику → «Обновить поле» (или F9)."
    fldEnd = OxmlElement("w:fldChar"); fldEnd.set(qn("w:fldCharType"), "end")
    for el in (fldBegin, instr, fldSep, hint, fldEnd):
        run._r.append(el)


# ──────────────────────────────── cover ────────────────────────────────────
def _cover(doc, data: dict) -> None:
    from docx.shared import Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    for _ in range(4):
        doc.add_paragraph()

    band = doc.add_paragraph()
    band.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = band.add_run("МАРКЕТИНГОВАЯ СТРАТЕГИЯ")
    r.bold = True
    r.font.size = Pt(13)
    r.font.color.rgb = RGBColor.from_string(BRAND["accent"])

    title = doc.add_paragraph()
    r = title.add_run(s(data["product_name"]))
    r.bold = True
    r.font.size = Pt(34)
    r.font.color.rgb = RGBColor.from_string(BRAND["primary"])

    usp = data.get("usp_final", {}) or {}
    if usp.get("primary", {}).get("text"):
        sub = doc.add_paragraph()
        r = sub.add_run(usp["primary"]["text"])
        r.italic = True
        r.font.size = Pt(13)
        r.font.color.rgb = RGBColor.from_string(BRAND["muted"])

    for _ in range(10):
        doc.add_paragraph()

    meta = doc.add_paragraph()
    r = meta.add_run("Документ для медиабайера")
    r.bold = True
    r.font.size = Pt(11)
    site = s(data.get("state", {}).get("site_url"), "")
    line = doc.add_paragraph()
    parts = [f"Дата: {_today_ru()}"]
    if site:
        parts.append(f"Сайт: {site}")
    r = line.add_run("   ·   ".join(parts))
    r.font.size = Pt(10)
    r.font.color.rgb = RGBColor.from_string(BRAND["muted"])

    doc.add_page_break()


# ─────────────────────────── executive summary ─────────────────────────────
def _exec_summary(doc, data: dict) -> None:
    from docx.shared import Pt, RGBColor

    cs = data.get("channel_selection", {}) or {}
    top3 = cs.get("top3", []) or []
    bg = data.get("budget_allocation", {}) or {}
    kpi = data.get("kpi_framework", {}) or {}
    cur = bg.get("currency", "RUB")

    doc.add_heading("Executive Summary", level=1)

    # карточка с заливкой через однострочную таблицу
    card = doc.add_table(rows=1, cols=1)
    _table_borders(card, color=BRAND["primary"], sz=6)
    cell = card.rows[0].cells[0]
    _shade(cell, BRAND["light"])
    cell.text = ""

    def kv(label, value):
        p = cell.add_paragraph()
        rl = p.add_run(f"{label}: ")
        rl.bold = True
        rl.font.size = Pt(10.5)
        rl.font.color.rgb = RGBColor.from_string(BRAND["primary"])
        rv = p.add_run(value)
        rv.font.size = Pt(10.5)

    # удалить пустой первый параграф ячейки
    cell.paragraphs[0].text = ""

    names = ", ".join(channel_label(c.get("channel", "")) for c in top3[:3]) or "не определены"
    kv("Топ-3 канала", names)
    if bg.get("total_budget_3m"):
        kv("Бюджет на 3 месяца", format_money(bg["total_budget_3m"], cur))
    biz = kpi.get("business_kpi", {}) or {}
    if biz:
        kv(
            "Главный бизнес-KPI",
            f"{s(biz.get('main'),'CPL')} ≤ {s(biz.get('target'))} {currency_sign(biz.get('currency', cur))}, "
            f"объём ≥ {s(biz.get('volume_target_monthly'))}/мес, "
            f"payback ≤ {s(biz.get('payback_months'))} мес",
        )
    dem = (data.get("industry_research", {}) or {}).get("demand_type")
    if dem:
        dem_ru = {"deferred": "отложенный", "urgent": "срочный", "none": "формируем спрос"}.get(dem, dem)
        kv("Тип спроса", dem_ru)
    doc.add_paragraph()


# ──────────────────────────────── main body ────────────────────────────────
def _generate_docx(workspace: Path, data: dict) -> Path:
    from docx import Document
    from docx.shared import Pt, RGBColor

    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)

    # цвет заголовков
    for lvl in range(1, 6):
        try:
            st = doc.styles[f"Heading {lvl}"]
            st.font.color.rgb = RGBColor.from_string(BRAND["primary"])
        except KeyError:
            pass

    _footer_with_page_number(doc, s(data["product_name"]))
    _cover(doc, data)

    doc.add_heading("Содержание", level=1)
    _add_toc(doc)
    doc.add_page_break()

    _exec_summary(doc, data)

    cs = data.get("channel_selection", {}) or {}
    top3 = cs.get("top3", []) or []
    bg = data.get("budget_allocation", {}) or {}
    kpi = data.get("kpi_framework", {}) or {}
    cur = bg.get("currency", "RUB")

    # 1. Продукт и ЦА
    doc.add_heading("1. Продукт и целевая аудитория", level=1)
    doc.add_heading("1.1 Бриф", level=2)
    _render_md(doc, data.get("brief_md", ""), base_level=3)
    doc.add_heading("1.2 Buyer Personas", level=2)
    _render_md(doc, data.get("personas_md", ""), base_level=3)

    # 2. Конкуренты и отрасль
    doc.add_heading("2. Конкурентный контекст и отрасль", level=1)
    doc.add_heading("2.1 Отраслевая аналитика", level=2)
    _render_md(doc, data.get("industry_research_md", ""), base_level=3)
    doc.add_heading("2.2 Конкуренты — матрица каналов", level=2)
    _render_md(doc, data.get("competitor_analysis_md", ""), base_level=3)

    # 3. Стратегия и УТП
    doc.add_heading("3. Стратегия и УТП", level=1)
    doc.add_heading("3.1 Стратегический слой", level=2)
    _render_md(doc, data.get("strategy_md", ""), base_level=3)
    doc.add_heading("3.2 Гипотезы запуска", level=2)
    _render_md(doc, data.get("hypotheses_md", ""), base_level=3)
    doc.add_heading("3.3 УТП", level=2)
    usp = data.get("usp_final", {}) or {}
    if usp.get("primary", {}).get("text"):
        p = doc.add_paragraph()
        p.add_run("Основное УТП: ").bold = True
        p.add_run(usp["primary"]["text"])
    if usp.get("secondary_for_ab", {}).get("text"):
        p = doc.add_paragraph()
        p.add_run("Резерв для A/B: ").bold = True
        p.add_run(usp["secondary_for_ab"]["text"])

    # 4. Выбор площадок — ГЛАВНЫЙ раздел
    doc.add_heading("4. Рекомендация по площадкам", level=1)
    if top3:
        table = doc.add_table(rows=1, cols=4)
        _table_borders(table)
        heads = ["Приоритет", "Канал", "Балл", "Площадочный скилл"]
        for j, htext in enumerate(heads):
            c = table.rows[0].cells[j]
            _shade(c, BRAND["header_bg"])
            _set_cell(c, htext, bold=True, color="FFFFFF", size=10)
        for c in top3:
            cells = table.add_row().cells
            pr = c.get("priority")
            _set_cell(cells[0], s(pr), bold=True, color="FFFFFF", align="center")
            try:
                _shade(cells[0], PRIORITY_COLORS.get(int(pr), BRAND["muted"]))
            except (TypeError, ValueError):
                _shade(cells[0], BRAND["muted"])
            _set_cell(cells[1], channel_label(c.get("channel", "")))
            _set_cell(cells[2], s(c.get("total_score", c.get("score"))), align="center")
            _set_cell(cells[3], s(c.get("platform_skill"), "— (вручную)"))
        doc.add_paragraph()

        doc.add_heading("4.1 Обоснование по каналам", level=2)
        for c in top3:
            doc.add_heading(
                f"Приоритет {s(c.get('priority'),'?')}: {channel_label(c.get('channel', ''))}",
                level=3,
            )
            if c.get("rationale"):
                doc.add_paragraph(c["rationale"])
            if c.get("hypotheses_to_test"):
                p = doc.add_paragraph()
                p.add_run("Гипотезы для теста: ").bold = True
                p.add_run(", ".join(map(str, c["hypotheses_to_test"])))
            if c.get("recommended_formats"):
                p = doc.add_paragraph()
                p.add_run("Рекомендуемые форматы: ").bold = True
                p.add_run(", ".join(map(str, c["recommended_formats"])))
            if c.get("risks"):
                p = doc.add_paragraph()
                p.add_run("Риски: ").bold = True
                p.add_run("; ".join(map(str, c["risks"])))

    doc.add_heading("4.2 Полная матрица выбора", level=2)
    _render_md(doc, data.get("channel_selection_md", ""), base_level=3)

    # 5. Бюджет по фазам
    doc.add_heading("5. Распределение бюджета по фазам", level=1)
    phases = bg.get("phases", []) or []
    if phases:
        table = doc.add_table(rows=1, cols=5)
        _table_borders(table)
        for j, htext in enumerate(["Фаза", "Срок", "Бюджет", "Доля", "Цель"]):
            c = table.rows[0].cells[j]
            _shade(c, BRAND["header_bg"])
            _set_cell(c, htext, bold=True, color="FFFFFF", size=10)
        for ph in phases:
            cells = table.add_row().cells
            name = ph.get("name", "")
            _set_cell(cells[0], PHASE_LABELS.get(name, name), bold=True)
            _set_cell(cells[1], f"{s(ph.get('duration_weeks'))} нед", align="center")
            _set_cell(cells[2], format_money(ph.get("budget", 0), cur), align="right")
            try:
                share = f"{int(round(float(ph.get('share', 0)) * 100))}%"
            except (TypeError, ValueError):
                share = "—"
            _set_cell(cells[3], share, align="center")
            _set_cell(cells[4], PHASE_GOALS.get(name, "—"))
        doc.add_paragraph()
    doc.add_heading("5.1 Детально по фазам и каналам", level=2)
    _render_md(doc, data.get("budget_allocation_md", ""), base_level=3)

    # 6. KPI
    doc.add_heading("6. KPI и мониторинг", level=1)
    channels_kpi = kpi.get("channels", []) or []
    if channels_kpi:
        table = doc.add_table(rows=1, cols=5)
        _table_borders(table)
        for j, htext in enumerate(["Канал", "Главная метрика", "Target Тест", "Target Опт", "Target Масштаб"]):
            c = table.rows[0].cells[j]
            _shade(c, BRAND["header_bg"])
            _set_cell(c, htext, bold=True, color="FFFFFF", size=9)
        for ch in channels_kpi:
            cells = table.add_row().cells
            _set_cell(cells[0], channel_label(ch.get("channel", "")))
            _set_cell(cells[1], s(ch.get("main_metric")), align="center")
            t = ch.get("targets_by_phase", {}) or {}
            _set_cell(cells[2], s(t.get("test")), align="center")
            _set_cell(cells[3], s(t.get("optimize")), align="center")
            _set_cell(cells[4], s(t.get("scale")), align="center")
        doc.add_paragraph()
    doc.add_heading("6.1 Триггеры и чек-листы", level=2)
    _render_md(doc, data.get("kpi_framework_md", ""), base_level=3)

    # 7. Handoff
    doc.add_heading("7. План передачи в площадочные скиллы", level=1)
    doc.add_paragraph(
        "Этот отчёт — общая часть. Для запуска конкретных кампаний используются "
        "специализированные скиллы (yandex-direct-funnel, vk-ads-launcher и др.). "
        "Они принимают артефакты из этой папки как вход и не переделывают бриф/"
        "гипотезы/УТП с нуля."
    )
    for c in top3:
        skill = c.get("platform_skill")
        p = doc.add_paragraph(style="List Bullet")
        r = p.add_run(f"{channel_label(c.get('channel', ''))}: ")
        r.bold = True
        if skill:
            p.add_run(f"скилл `{skill}`. Передаём: 01_brief, hypotheses, personas, "
                      f"usp_final, kpi_framework, budget_allocation.")
        else:
            p.add_run("автоматизации пока нет — запуск вручную по этому отчёту.")

    out = workspace / "marketing_strategy.docx"
    doc.save(out)
    return out


# ──────────────────────────────── fallback ─────────────────────────────────
def _md_fallback(workspace: Path, data: dict) -> Path:
    out = workspace / "marketing_strategy.md"
    lines = [f"# Маркетинговая стратегия: {data['product_name']}", "",
             f"_Дата: {_today_ru()}_", "", "## Executive Summary", ""]
    cs = data.get("channel_selection", {}) or {}
    top3 = cs.get("top3", []) or []
    if top3:
        names = ", ".join(channel_label(c.get("channel", "")) for c in top3[:3])
        lines += [f"**Топ-3 канала:** {names}", ""]
    bg = data.get("budget_allocation", {}) or {}
    if bg.get("total_budget_3m"):
        lines += [f"**Бюджет на 3 месяца:** {format_money(bg['total_budget_3m'], bg.get('currency', 'RUB'))}", ""]
    lines += ["---", ""]
    sections = [
        ("1. Бриф", data.get("brief_md", "")),
        ("2. Стратегический слой", data.get("strategy_md", "")),
        ("3. Отраслевая аналитика", data.get("industry_research_md", "")),
        ("4. Конкуренты", data.get("competitor_analysis_md", "")),
        ("5. Гипотезы", data.get("hypotheses_md", "")),
        ("6. Buyer Personas", data.get("personas_md", "")),
        ("7. УТП — аудит", data.get("usp_audit_md", "")),
        ("8. Выбор каналов", data.get("channel_selection_md", "")),
        ("9. Бюджет по фазам", data.get("budget_allocation_md", "")),
        ("10. KPI Framework", data.get("kpi_framework_md", "")),
    ]
    for title, body in sections:
        if body:
            lines += [f"## {title}", "", body, ""]
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate marketing strategy DOCX report")
    parser.add_argument("--workspace", required=True, help="Path to marketing-campaigns/<slug>/")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    if not workspace.exists():
        print(f"ERROR: workspace not found: {workspace}", file=sys.stderr)
        sys.exit(1)

    data = load_workspace(workspace)
    missing = check_required(data)
    if missing:
        print(f"WARNING: missing artefacts: {', '.join(missing)}", file=sys.stderr)
        print("Будет сгенерирован отчёт с пробелами.", file=sys.stderr)

    try:
        out = _generate_docx(workspace, data)
        print(f"OK: {out}")
    except ImportError:
        print("python-docx не установлен. Фолбек: marketing_strategy.md", file=sys.stderr)
        out = _md_fallback(workspace, data)
        print(f"OK (fallback): {out}")


if __name__ == "__main__":
    main()
