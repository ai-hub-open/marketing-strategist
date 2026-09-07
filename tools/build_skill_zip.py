#!/usr/bin/env python3
"""
build_skill_zip.py — собирает marketing-strategist.zip для загрузки в Claude.

Архив устроен ровно так, как ждёт загрузчик Claude Desktop / claude.ai:

    marketing-strategist.zip
    └── marketing-strategist/
        ├── SKILL.md          ← ровно один на весь архив
        ├── references/
        └── scripts/

Перед упаковкой прогоняется валидация (см. validate()). Если она падает —
архив не собирается: лучше поймать здесь, чем получить от пользователя
«Zip must contain exactly one SKILL.md file».

Использование:
    python tools/build_skill_zip.py                 # → dist/marketing-strategist.zip
    python tools/build_skill_zip.py --check         # только валидация, без сборки
    python tools/build_skill_zip.py --output ~/Downloads
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import sys
import zipfile
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("Нужен PyYAML для валидации фронтматтера: pip install pyyaml")


REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_NAME = "marketing-strategist"

# Загрузчик claude.ai заявляет лимит описания в 200 символов, спека Agent Skills —
# 1024. Держим 200: так архив принимают все среды. Дополнительно Claude Code при
# авто-вызове показывает только первые 250 символов, так что более длинное
# описание всё равно не улучшило бы триггер.
DESCRIPTION_MAX = 200
NAME_MAX = 64

# claude.ai понимает во фронтматтере только name и description. Остальное
# (context, agent, allowed-tools, disable-model-invocation, argument-hint) —
# фронтматтер Claude Code, при загрузке архива он ломает валидацию схемы.
ALLOWED_FRONTMATTER_KEYS = {"name", "description"}

# Не попадает в архив: инструменты сборки, документация репозитория, мусор.
# Список намеренно шире, чем текущий состав репозитория: INSTALL.md, CHANGELOG.md
# и .gitignore удалены, но живут в старых ветках и вернутся при первом же мердже
# оттуда — пусть они и в этом случае не доезжают до пользователя.
# subagents/ здесь намеренно НЕТ: если папка вернётся мерджем из старой ветки,
# валидация должна упасть с «в пакет попало 3 файлов SKILL.md», а не молча
# собрать архив поверх испорченного репозитория.
EXCLUDE_DIRS = {"__pycache__", ".git", ".github", ".venv", "venv", "dist", "tools",
                "marketing-campaigns"}
EXCLUDE_FILES = {".gitignore", ".DS_Store", "Thumbs.db", "package.sh",
                 "README.md", "INSTALL.md", "CHANGELOG.md", "LICENSE"}
EXCLUDE_GLOBS = {"*.pyc", "*.pyo", "*.swp", "*.bak", "*.tmp"}


def is_excluded(rel: Path) -> bool:
    if any(part in EXCLUDE_DIRS for part in rel.parts):
        return True
    if rel.name in EXCLUDE_FILES:
        return True
    return any(fnmatch.fnmatch(rel.name, pat) for pat in EXCLUDE_GLOBS)


def collect_files() -> list[Path]:
    """Пути файлов пакета относительно корня репозитория."""
    files = []
    for fp in sorted(REPO_ROOT.rglob("*")):
        if not fp.is_file():
            continue
        rel = fp.relative_to(REPO_ROOT)
        if not is_excluded(rel):
            files.append(rel)
    return files


def parse_frontmatter(skill_md: Path) -> tuple[dict, int]:
    """Возвращает (фронтматтер, число строк тела). Кидает ValueError с внятным текстом."""
    text = skill_md.read_text(encoding="utf-8")
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.DOTALL)
    if not m:
        raise ValueError(f"{skill_md}: файл должен начинаться с YAML-фронтматтера в тройных дефисах")

    try:
        data = yaml.safe_load(m.group(1))
    except yaml.YAMLError as exc:
        # Самая частая причина — незакавыченное значение с «: » или начинающееся с «[».
        raise ValueError(f"{skill_md}: невалидный YAML во фронтматтере — {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"{skill_md}: фронтматтер должен быть YAML-словарём")

    body_lines = text[m.end():].count("\n") + 1
    return data, body_lines


def validate(files: list[Path]) -> list[str]:
    """Возвращает список проблем. Пустой список — всё в порядке."""
    problems: list[str] = []

    # 1. Ровно один SKILL.md на весь архив.
    skill_mds = [f for f in files if f.name == "SKILL.md"]
    if len(skill_mds) != 1:
        problems.append(
            f"в пакет попало {len(skill_mds)} файлов SKILL.md "
            f"({', '.join(f.as_posix() for f in skill_mds)}) — "
            "загрузчик Claude принимает ровно один")
        return problems
    if skill_mds[0] != Path("SKILL.md"):
        problems.append(f"SKILL.md должен лежать в корне пакета, а лежит в {skill_mds[0]}")
        return problems

    # 2. Фронтматтер парсится и содержит только поля из схемы claude.ai.
    try:
        fm, body_lines = parse_frontmatter(REPO_ROOT / "SKILL.md")
    except ValueError as exc:
        problems.append(str(exc))
        return problems

    extra = set(fm) - ALLOWED_FRONTMATTER_KEYS
    if extra:
        problems.append(
            f"во фронтматтере поля вне схемы claude.ai: {', '.join(sorted(extra))} — "
            "оставьте только name и description")

    # 3. name.
    name = fm.get("name")
    if not name:
        problems.append("во фронтматтере нет name")
    else:
        if name != SKILL_NAME:
            problems.append(f"name: {name} не совпадает с именем пакета {SKILL_NAME}")
        if len(name) > NAME_MAX:
            problems.append(f"name длиннее {NAME_MAX} символов")
        if not re.fullmatch(r"[a-z0-9-]+", name):
            problems.append(f"name: {name} — допустимы только строчные латинские буквы, цифры и дефис")
        if "anthropic" in name.lower() or "claude" in name.lower():
            problems.append(f"name: {name} содержит зарезервированное слово (anthropic / claude)")

    # 4. description.
    desc = fm.get("description")
    if not desc or not str(desc).strip():
        problems.append("во фронтматтере нет непустого description")
    else:
        desc = str(desc).strip()
        if len(desc) > DESCRIPTION_MAX:
            problems.append(f"description — {len(desc)} символов, лимит {DESCRIPTION_MAX}")
        if "<" in desc or "<" in str(name or ""):
            problems.append("name / description не должны содержать XML-теги")

    # 5. Тело SKILL.md — рекомендация Anthropic держать под 500 строк.
    if body_lines > 500:
        problems.append(f"тело SKILL.md — {body_lines} строк, рекомендованный предел 500")

    # 6. Все файлы, на которые SKILL.md ссылается, реально лежат в пакете.
    skill_text = (REPO_ROOT / "SKILL.md").read_text(encoding="utf-8")
    packaged = {f.as_posix() for f in files}
    for ref in sorted(set(re.findall(r"`((?:references|scripts)/[\w./-]+)`", skill_text))):
        if ref not in packaged:
            problems.append(f"SKILL.md ссылается на {ref}, но такого файла в пакете нет")

    # 7. Мусор, который не должен доехать до пользователя.
    for f in files:
        if any(part == "__pycache__" for part in f.parts) or f.suffix in {".pyc", ".pyo"}:
            problems.append(f"в пакет попал байт-код: {f}")

    return problems


def build(files: list[Path], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    archive = out_dir / f"{SKILL_NAME}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in files:
            # Единственная папка верхнего уровня в архиве названа именем скилла —
            # это то, что загрузчик показывает как имя скилла.
            zf.write(REPO_ROOT / rel, Path(SKILL_NAME) / rel)
    return archive


def main() -> int:
    parser = argparse.ArgumentParser(description="Сборка marketing-strategist.zip")
    parser.add_argument("--check", action="store_true", help="только валидация, без сборки")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "dist",
                        help="куда положить архив (по умолчанию dist/)")
    args = parser.parse_args()

    files = collect_files()
    problems = validate(files)

    if problems:
        print("Валидация не пройдена:", file=sys.stderr)
        for problem in problems:
            print(f"  ✗ {problem}", file=sys.stderr)
        return 1

    print(f"✓ валидация пройдена, файлов в пакете: {len(files)}")

    if args.check:
        return 0

    archive = build(files, args.output)
    size_kb = archive.stat().st_size / 1024
    print(f"✓ {archive} ({size_kb:.0f} КБ)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
