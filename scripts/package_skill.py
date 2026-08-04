#!/usr/bin/env python3
"""
package_skill.py — собирает устанавливаемые пакеты набора «Маркетинг-стратег».

Cowork импортирует один SKILL.md за раз, поэтому набор поставляется тремя
отдельными скиллами:

    marketing-strategist   ← корень репозитория БЕЗ папки subagents/
    industry-research      ← subagents/industry-research/
    competitor-research    ← subagents/competitor-research/

Главный пакет собирается без `subagents/` здесь, на стороне сборки, — поэтому
пользователю не нужно ничего удалять у себя после распаковки.

Каждый пакет пишется в двух расширениях, .zip и .skill; содержимое байт в байт
одинаковое, это один и тот же ZIP. `.zip` принимают среды с загрузкой архива
(Cowork), `.skill` — среды, ожидающие такое расширение; так же названы артефакты
yandex-direct-manager и vk-ads-manager.

Имена файлов не содержат номер версии: ссылка вида
releases/latest/download/marketing-strategist.zip работает только при постоянном
имени артефакта. Версию задаёт тег релиза.

Использование:
    ./package.sh                                        # 3 пакета × 2 расширения → dist/
    python3 scripts/package_skill.py --only industry-research
    python3 scripts/package_skill.py --formats zip --output ~/Downloads
"""

import argparse
import fnmatch
import re
import sys
import zipfile
from pathlib import Path


# Состав набора: имя пакета → папка-источник относительно корня репозитория.
# Для главного пакета `subagents` попадает в ROOT_EXCLUDE_DIRS: субагенты
# поставляются отдельными скиллами и внутри главного архива только мешают.
PACKAGES = {
    "marketing-strategist": {"src": ".", "root_exclude": {"subagents"}},
    "industry-research": {"src": "subagents/industry-research", "root_exclude": set()},
    "competitor-research": {"src": "subagents/competitor-research", "root_exclude": set()},
}

FORMATS = ("zip", "skill")

EXCLUDE_DIRS = {
    "__pycache__",
    "node_modules",
    ".git",
    ".github",
    ".venv",
    "venv",
    "dist",
    "marketing-campaigns",  # рабочие папки кампаний, а не часть скилла
}
EXCLUDE_GLOBS = {"*.pyc", "*.pyo", "*.swp", "*.bak", "*.tmp"}
# package.sh и package_skill.py — инструменты сборки, в пакет пользователя не идут
EXCLUDE_FILES = {".DS_Store", ".gitignore", "Thumbs.db", "package.sh", "package_skill.py"}


def should_exclude(rel_path: Path, root_exclude: set) -> bool:
    """Решает, исключить ли файл. rel_path начинается с имени пакета."""
    parts = rel_path.parts

    if any(part in EXCLUDE_DIRS for part in parts):
        return True

    # parts[0] — имя пакета, parts[1] — папка первого уровня внутри него
    if len(parts) > 1 and parts[1] in root_exclude:
        return True

    name = rel_path.name
    if name in EXCLUDE_FILES:
        return True
    if any(fnmatch.fnmatch(name, pat) for pat in EXCLUDE_GLOBS):
        return True

    return False


def validate_skill(src: Path, expected_name: str) -> tuple:
    """Проверяет, что папка вообще является скиллом и объявляет ожидаемое имя."""
    if not src.is_dir():
        return False, f"нет папки {src}"

    skill_md = src / "SKILL.md"
    if not skill_md.exists():
        return False, f"нет SKILL.md в {src}"

    content = skill_md.read_text(encoding="utf-8")
    fm_match = re.match(r"^---\n(.+?)\n---", content, re.DOTALL)
    if not fm_match:
        return False, "SKILL.md должен начинаться с YAML-фронтматтера в тройных дефисах"

    fm = fm_match.group(1)
    name_match = re.search(r"^name:\s*(\S+)", fm, re.MULTILINE)
    if not name_match:
        return False, "во фронтматтере SKILL.md нет `name:`"
    if not re.search(r"^description:\s*\S+", fm, re.MULTILINE):
        return False, "во фронтматтере SKILL.md нет `description:`"

    # Имя в архиве и имя в карточке скилла должны совпадать, иначе среда
    # покажет один скилл, а папка будет называться иначе
    if name_match.group(1) != expected_name:
        return False, f"`name: {name_match.group(1)}` не совпадает с именем пакета {expected_name}"

    return True, "OK"


def collect_files(src: Path, package_name: str, root_exclude: set) -> list:
    """Возвращает пары (файл на диске, путь внутри архива)."""
    collected = []
    for fp in sorted(src.rglob("*")):
        if not fp.is_file():
            continue
        arcname = Path(package_name) / fp.relative_to(src)
        if should_exclude(arcname, root_exclude):
            continue
        collected.append((fp, arcname))
    return collected


def build_package(repo_root: Path, package_name: str, output_dir: Path, formats: tuple) -> list:
    """Собирает один пакет во всех запрошенных расширениях."""
    spec = PACKAGES[package_name]
    src = (repo_root / spec["src"]).resolve()

    valid, msg = validate_skill(src, package_name)
    if not valid:
        print(f"[!] {package_name}: {msg}", file=sys.stderr)
        return []

    files = collect_files(src, package_name, spec["root_exclude"])
    if not files:
        print(f"[!] {package_name}: нечего упаковывать", file=sys.stderr)
        return []

    written = []
    for fmt in formats:
        output_file = output_dir / f"{package_name}.{fmt}"
        with zipfile.ZipFile(output_file, "w", zipfile.ZIP_DEFLATED) as zf:
            for fp, arcname in files:
                zf.write(fp, arcname)
        written.append(output_file)

    size_kb = written[0].stat().st_size / 1024
    names = ", ".join(f.name for f in written)
    print(f"[+] {names} — файлов: {len(files)}, размер: {size_kb:.1f} КБ")
    return written


def main():
    parser = argparse.ArgumentParser(
        description="Упаковщик набора «Маркетинг-стратег» в устанавливаемые архивы"
    )
    parser.add_argument(
        "--only",
        choices=sorted(PACKAGES),
        help="собрать только один пакет (по умолчанию — все три)",
    )
    parser.add_argument(
        "--formats",
        default=",".join(FORMATS),
        help=f"расширения через запятую из {', '.join(FORMATS)} (по умолчанию оба)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="куда сложить архивы (по умолчанию — dist/ в корне репозитория)",
    )
    args = parser.parse_args()

    formats = tuple(f.strip() for f in args.formats.split(",") if f.strip())
    unknown = [f for f in formats if f not in FORMATS]
    if unknown:
        parser.error(f"неизвестное расширение: {', '.join(unknown)}")

    repo_root = Path(__file__).resolve().parent.parent
    output_dir = Path(args.output).expanduser().resolve() if args.output else repo_root / "dist"
    output_dir.mkdir(parents=True, exist_ok=True)

    names = [args.only] if args.only else list(PACKAGES)
    print(f"Сборка из {repo_root}")
    print(f"Складываю в {output_dir}\n")

    written = []
    for name in names:
        written.extend(build_package(repo_root, name, output_dir, formats))

    expected = len(names) * len(formats)
    if len(written) != expected:
        print(f"\nСобрано {len(written)} из {expected} — смотрите ошибки выше", file=sys.stderr)
        sys.exit(1)

    print(f"\nГотово, собрано архивов: {len(written)}. Прикладывайте к релизу как есть, не переименовывая.")
    sys.exit(0)


if __name__ == "__main__":
    main()
