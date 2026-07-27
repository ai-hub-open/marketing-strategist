"""Общие helpers для чтения артефактов из рабочей папки кампании."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_json(path: Path, default: Any = None) -> Any:
    """Безопасно прочитать JSON, вернуть default если файла нет/невалидный."""
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def read_text(path: Path, default: str = "") -> str:
    """Безопасно прочитать текст, вернуть default если файла нет."""
    if not path.exists():
        return default
    return path.read_text(encoding="utf-8")


def load_workspace(workspace: Path) -> dict[str, Any]:
    """Загрузить все ключевые артефакты кампании в один dict."""
    state = read_json(workspace / "_state.json", default={})

    return {
        "state": state,
        "slug": state.get("slug", workspace.name),
        "product_name": state.get("product_name", workspace.name),
        "client_materials_md": read_text(workspace / "00_client_materials.md"),
        "brief_md": read_text(workspace / "01_brief.md"),
        "strategy_md": read_text(workspace / "02_strategy.md"),
        "industry_research_md": read_text(workspace / "industry_research.md"),
        "industry_research": read_json(workspace / "industry_research.json", default={}),
        "competitors_md": read_text(workspace / "04_competitors.md"),
        "competitor_analysis_md": read_text(workspace / "05_competitor_analysis.md"),
        "hypotheses_md": read_text(workspace / "hypotheses.md"),
        "personas_md": read_text(workspace / "07_personas.md"),
        "usp_audit_md": read_text(workspace / "usp_audit.md"),
        "usp_final": read_json(workspace / "usp_final.json", default={}),
        "channel_selection_md": read_text(workspace / "channel_selection.md"),
        "channel_selection": read_json(workspace / "channel_selection.json", default={}),
        "budget_allocation_md": read_text(workspace / "budget_allocation.md"),
        "budget_allocation": read_json(workspace / "budget_allocation.json", default={}),
        "kpi_framework_md": read_text(workspace / "kpi_framework.md"),
        "kpi_framework": read_json(workspace / "kpi_framework.json", default={}),
    }


def check_required(data: dict[str, Any]) -> list[str]:
    """Проверить, какие ключевые артефакты отсутствуют."""
    missing = []
    required_keys = {
        "brief_md": "01_brief.md",
        "strategy_md": "02_strategy.md",
        "channel_selection": "channel_selection.json",
        "budget_allocation": "budget_allocation.json",
        "kpi_framework": "kpi_framework.json",
        "usp_final": "usp_final.json",
    }
    for key, fname in required_keys.items():
        v = data.get(key)
        if not v:
            missing.append(fname)
    return missing


CHANNEL_LABELS = {
    "yandex_direct_search": "Яндекс.Директ — Поиск",
    "yandex_direct_rsya": "Яндекс.Директ — РСЯ",
    "yandex_direct": "Яндекс.Директ",
    "vk_ads": "VK Ads / myTarget",
    "meta_ads": "Meta (Facebook/Instagram)",
    "telegram_ads": "Telegram Ads",
    "tiktok_ads": "TikTok Ads",
    "dzen": "Яндекс.Дзен",
    "avito": "Avito",
    "programmatic": "Programmatic / DSP",
    "google_ads": "Google Ads",
    "linkedin_ads": "LinkedIn Ads",
    "youtube": "YouTube",
    "influencer": "Инфлюенсеры",
    "seo": "SEO",
}


def channel_label(channel_key: str) -> str:
    return CHANNEL_LABELS.get(channel_key, channel_key)


def format_money(amount, currency: str = "RUB") -> str:
    """Отформатировать сумму с разделителями тысяч."""
    try:
        amount = int(round(float(amount)))
    except (TypeError, ValueError):
        amount = 0
    sign = "₽" if currency == "RUB" else currency
    return f"{amount:,}".replace(",", " ") + f" {sign}"


def currency_sign(currency: str = "RUB") -> str:
    return "₽" if currency == "RUB" else currency


def s(value, default: str = "—") -> str:
    """Безопасно привести любое значение к непустой строке (None/'' → default)."""
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


# ──────────────────────────────────────────────────────────────────────────
# Фирменная палитра (единая для DOCX / XLSX / PDF)
# ──────────────────────────────────────────────────────────────────────────
BRAND = {
    "primary": "1F3864",
    "accent": "2E5AAC",
    "header_bg": "4472C4",
    "band": "1F3864",
    "zebra": "EEF3FB",
    "light": "D9E1F2",
    "muted": "7F7F7F",
    "ok": "2E7D32",
    "warn": "B7791F",
    "risk": "C0392B",
}
PRIORITY_COLORS = {1: BRAND["ok"], 2: BRAND["accent"], 3: BRAND["warn"]}
PHASE_LABELS = {"test": "Тест", "optimize": "Оптимизация", "scale": "Масштаб"}
PHASE_GOALS = {
    "test": "Найти рабочий канал и связку",
    "optimize": "Доразогнать лучшие связки",
    "scale": "Максимум объёма при целевом CPA",
}
PHASE_HEX = {"test": "FCE4D6", "optimize": "FFF2CC", "scale": "E2EFDA"}


def parse_inline(text: str):
    """Разбить строку на сегменты (текст, bold) по **...**."""
    segments = []
    i = 0
    bold = False
    buf = ""
    while i < len(text):
        if text[i:i + 2] == "**":
            if buf:
                segments.append((buf, bold))
                buf = ""
            bold = not bold
            i += 2
            continue
        buf += text[i]
        i += 1
    if buf:
        segments.append((buf, bold))
    return segments or [("", False)]


def _is_table_sep(line: str) -> bool:
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    return bool(cells) and all(set(c) <= set("-: ") and "-" in c for c in cells)


def _split_row(line: str):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse_markdown(md: str):
    """Markdown → список блоков. Безопасно: всегда возвращает list."""
    blocks = []
    if not md:
        return blocks
    lines = md.replace("\r\n", "\n").split("\n")
    i = 0
    n = len(lines)
    para = []

    def flush_para():
        if para:
            blocks.append({"type": "paragraph", "text": " ".join(para).strip()})
            para.clear()

    while i < n:
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            flush_para()
            i += 1
            continue
        if stripped.startswith("#"):
            flush_para()
            level = len(stripped) - len(stripped.lstrip("#"))
            blocks.append({"type": "heading", "level": min(level, 6),
                           "text": stripped[level:].strip()})
            i += 1
            continue
        if "|" in stripped and i + 1 < n and _is_table_sep(lines[i + 1]):
            flush_para()
            header = _split_row(stripped)
            rows = []
            i += 2
            while i < n and "|" in lines[i] and lines[i].strip():
                rows.append(_split_row(lines[i]))
                i += 1
            blocks.append({"type": "table", "header": header, "rows": rows})
            continue
        is_ul = stripped[:2] in ("- ", "* ", "• ")
        is_ol = False
        if not is_ul:
            head = stripped.split(" ", 1)[0]
            if head[:-1].isdigit() and head.endswith("."):
                is_ol = True
        if is_ul or is_ol:
            flush_para()
            ordered = is_ol
            items = []
            while i < n and lines[i].strip():
                ls = lines[i].strip()
                if ls[:2] in ("- ", "* ", "• "):
                    items.append(ls[2:].strip())
                else:
                    head = ls.split(" ", 1)[0]
                    if head[:-1].isdigit() and head.endswith("."):
                        items.append(ls.split(" ", 1)[1] if " " in ls else "")
                    else:
                        break
                i += 1
            blocks.append({"type": "list", "ordered": ordered, "items": items})
            continue
        para.append(stripped)
        i += 1
    flush_para()
    return blocks
