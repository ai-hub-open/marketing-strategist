"""Общие helpers для чтения артефактов из рабочей папки кампании."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

DEFAULT_PLANNING_HORIZON_MONTHS = 6
_LEGACY_3M_HORIZON = 3

# Markdown-tolerant: «Горизонт планирования: 6» and «**Горизонт планирования:** 6 месяцев»
_HORIZON_RE = re.compile(
    r"горизонт\s+планирования\D{0,12}(\d+)",
    re.IGNORECASE,
)


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

    data = {
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
    horizon, total = resolve_horizon_and_budget(data)
    data["planning_horizon_months"] = horizon
    data["total_budget"] = total
    return data


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


HISTORY_VERDICTS = {
    "works": "работает",
    "expensive": "дорого",
    "no_leads": "не дал лидов",
    "no_data": "мало данных",
    "never_ran": "не запускали",
}


def history_label(channel: dict) -> str:
    """Client's own history for a top-3 channel (see references/channel-history.md).

    No history field at all, or "none", means the recommendation was made without it.
    """
    h = channel.get("history")
    if not h or h == "none":
        return "без истории"
    if isinstance(h, dict):
        verdict = HISTORY_VERDICTS.get(h.get("verdict"), h.get("verdict") or "?")
        reason = h.get("verdict_reason")
        return f"{verdict}: {reason}" if reason else verdict
    return str(h)


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


def _as_positive_int(value) -> int | None:
    try:
        n = int(round(float(value)))
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


def ru_month_word(n: int) -> str:
    n = abs(int(n))
    if 11 <= n % 100 <= 14:
        return "месяцев"
    last = n % 10
    if last == 1:
        return "месяц"
    if 2 <= last <= 4:
        return "месяца"
    return "месяцев"


def budget_for_horizon_label(months: int) -> str:
    return f"Бюджет на {months} {ru_month_word(months)}"


def parse_horizon_from_brief(brief_md: str) -> int | None:
    """Вытащить горизонт из строки «Горизонт планирования: N месяцев» в брифе."""
    match = _HORIZON_RE.search(brief_md or "")
    return _as_positive_int(match.group(1)) if match else None


def resolve_horizon_and_budget(data: dict[str, Any]) -> tuple[int, int]:
    """Вернуть (horizon_months, total_budget).

    Источник горизонта — бриф, затем _state.json, затем budget_allocation.json.
    Скрипты не выбирают срок сами и не подставляют 3 месяца по умолчанию.
    """
    bg = data.get("budget_allocation") or {}
    state = data.get("state") or {}
    legacy_3m = _as_positive_int(bg.get("total_budget_3m"))

    horizon = (
        parse_horizon_from_brief(data.get("brief_md") or "")
        or _as_positive_int(state.get("planning_horizon_months"))
        or _as_positive_int(bg.get("planning_horizon_months"))
        or (_LEGACY_3M_HORIZON if legacy_3m is not None else DEFAULT_PLANNING_HORIZON_MONTHS)
    )

    total = _as_positive_int(bg.get("total_budget"))
    if total is not None:
        return horizon, total

    monthly = _as_positive_int(bg.get("monthly_budget"))
    if monthly is not None:
        return horizon, monthly * horizon

    phases_sum = sum(
        _as_positive_int(ph.get("budget")) or 0
        for ph in (bg.get("phases") or [])
    )
    return horizon, phases_sum or legacy_3m or 0


def planning_horizon_of(data: dict[str, Any]) -> int:
    return _as_positive_int(data.get("planning_horizon_months")) or DEFAULT_PLANNING_HORIZON_MONTHS


def total_budget_of(data: dict[str, Any]) -> Any:
    bg = data.get("budget_allocation") or {}
    return data.get("total_budget") or bg.get("total_budget") or bg.get("total_budget_3m")


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
