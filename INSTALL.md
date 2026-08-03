# Установка — marketing-strategist (3 пакета)

Cowork импортирует **один SKILL.md за раз**, поэтому набор разбит на три отдельных
скилла. Ставятся независимо, через тот же интерфейс загрузки ZIP.

## Что ставим (3 пакета)

| Пакет | Что это | Обязателен |
|---|---|---|
| `marketing-strategist` | главный оркестратор (шаги 0–12) | да |
| `industry-research` | субагент Шага 4 (отрасль) | желательно |
| `competitor-research` | субагент Шага 5 (конкуренты) | желательно |

Оркестратор работает и без субагентов — на Шагах 4–5 он выполняет те же шаги сам
по тем же справочникам. Но именно субагенты дают выигрыш по контексту.
Рекомендуется ставить все три.

Готовые архивы к релизу не прикладываются — упакуйте папки из клонированного
репозитория сами:

- основной скилл — содержимое корня репозитория без папки `subagents/`;
- `subagents/industry-research/` — отдельным архивом;
- `subagents/competitor-research/` — отдельным архивом.

## Установка (Cowork)

Загрузите каждый ZIP по очереди через Settings → Skills → Upload (или кнопку
добавления скилла). Cowork прочитает SKILL.md и покажет карточку. После загрузки
убедитесь, что переключатель скилла включён.

## Установка (Claude Code)

```bash
# из папки, куда клонирован репозиторий
cp -r marketing-strategist ~/.claude/skills/
cp -r marketing-strategist/subagents/industry-research ~/.claude/skills/
cp -r marketing-strategist/subagents/competitor-research ~/.claude/skills/
rm -rf ~/.claude/skills/marketing-strategist/subagents
```

Перезапустите `claude` — новые папки подхватятся после рестарта.

## Проверка

В списке скиллов (`What skills are available?`) должны быть три:
`marketing-strategist`, `industry-research`, `competitor-research`.

Триггер оркестратора: «подготовь маркетинговую стратегию для X, сайт Y».
На Шагах 4 и 5 оркестратор вызывает `/industry-research` и `/competitor-research`.

## Зависимости scripts (опционально, только для главного пакета)

```bash
pip install python-docx openpyxl reportlab
```

Без них документы сохраняются в текстовых форматах: DOCX → Markdown,
XLSX → CSV, PDF → Markdown.

## На что обратить внимание на первом прогоне

1. **Субагенты — самодостаточны.** В каждый вложен свой справочник (`references/...md`),
   путь внутри скилла уже поправлен. Дополнительно ничего класть не нужно.
2. **agent: general-purpose** в субагентах — они ПИШУТ артефакты. Хотите только
   исследование без записи — поменяйте на `agent: Explore` и уберите `Write`.
3. **Защита бюджета.** Площадочные пакеты ([yandex-direct-manager](https://github.com/ai-hub-open/yandex-direct-manager),
   [vk-ads-manager](https://github.com/ai-hub-open/vk-ads-manager)) создают кампании
   черновиком или на паузе — запуск остаётся за человеком. Это свойство самих
   площадочных пакетов, не этого набора; проверьте его при их установке.

## Версия

Изменения — в [CHANGELOG.md](CHANGELOG.md).
