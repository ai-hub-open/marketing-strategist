# Установка — Маркетинг-стратег

Ставится из готовых архивов, приложенных к релизу. Клонировать репозиторий и
собирать что-либо самому не нужно.

Набор состоит из трёх скиллов: среда импортирует один `SKILL.md` за раз, поэтому
оркестратор и два исследовательских потока — отдельные пакеты.

## Шаг 1. Скачайте архивы

Все три файла лежат на странице
[последнего релиза](https://github.com/ai-hub-open/marketing-strategist/releases/latest),
в разделе Assets. Прямые ссылки:

| Пакет | Что это | Обязателен | Скачать |
|---|---|---|---|
| `marketing-strategist` | оркестратор, шаги 0–12 | да | [marketing-strategist.zip](https://github.com/ai-hub-open/marketing-strategist/releases/latest/download/marketing-strategist.zip) |
| `industry-research` | исследование отрасли, Шаг 4 | желательно | [industry-research.zip](https://github.com/ai-hub-open/marketing-strategist/releases/latest/download/industry-research.zip) |
| `competitor-research` | исследование конкурентов, Шаг 5 | желательно | [competitor-research.zip](https://github.com/ai-hub-open/marketing-strategist/releases/latest/download/competitor-research.zip) |

Оркестратор работает и без двух других: на Шагах 4–5 он выполнит ту же работу
сам, по тем же справочникам. Но отдельные потоки экономят контекст, ради чего
они и сделаны, — ставьте все три.

Рядом лежат те же три архива с расширением `.skill` — это те же файлы, для сред,
которые ждут именно такое расширение. Если ваша среда просит ZIP, берите `.zip`.

## Шаг 2. Установите

### Claude Cowork

Загрузите каждый архив по очереди через **Settings → Skills → Upload** (или
кнопку добавления скилла). Cowork прочитает `SKILL.md` и покажет карточку.
После загрузки проверьте, что переключатель скилла включён.

### Claude Code

Из папки, куда скачались архивы:

```bash
unzip -o marketing-strategist.zip -d ~/.claude/skills/
unzip -o industry-research.zip   -d ~/.claude/skills/
unzip -o competitor-research.zip -d ~/.claude/skills/
```

Перезапустите `claude` — новые скиллы подхватятся после рестарта. Ключ `-o`
перезаписывает прошлую версию, так что теми же командами скилл обновляется.

## Шаг 3. Проверьте

Спросите агента `What skills are available?` — в списке должны быть три:
`marketing-strategist`, `industry-research`, `competitor-research`.

Первый запуск: «Подготовь маркетинговую стратегию для [продукт], сайт [адрес]».
Агент заведёт рабочую папку `marketing-campaigns/<slug>/` и остановится на
подтверждении Шага 0 — значит, всё встало правильно.

## Необязательные зависимости

Нужны только главному пакету и только для выгрузки в DOCX, XLSX и PDF:

```bash
pip install python-docx openpyxl reportlab
```

Без них документы сохраняются в текстовых форматах: DOCX → Markdown,
XLSX → CSV, PDF → Markdown. Скилл при этом работает полностью.

## На что обратить внимание на первом прогоне

1. **Исследовательские потоки самодостаточны.** В каждый вложен свой справочник
   (`references/…md`), путь внутри скилла уже поправлен. Класть что-то рядом не нужно.
2. **`agent: general-purpose` в потоках** — они ПИШУТ артефакты. Нужно только
   исследование без записи — поменяйте на `agent: Explore` и уберите `Write`.
3. **Защита бюджета.** Площадочные пакеты
   ([yandex-direct-manager](https://github.com/ai-hub-open/yandex-direct-manager),
   [vk-ads-manager](https://github.com/ai-hub-open/vk-ads-manager)) создают кампании
   черновиком или на паузе — запуск остаётся за человеком. Это свойство самих
   площадочных пакетов, не этого набора; проверьте его при их установке.

## Сборка архивов самому

Нужна только тем, кто правит скилл. Из клонированного репозитория:

```bash
./package.sh
```

Скрипт положит в `dist/` три пакета в двух расширениях. Главный пакет собирается
без папки `subagents/` — она уезжает в собственные архивы, поэтому после
установки у себя ничего удалять не приходится.

## Версия

Изменения — в [CHANGELOG.md](CHANGELOG.md).
