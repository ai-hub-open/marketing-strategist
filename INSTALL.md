# Установка — marketing-strategist v2 (3 пакета)

Cowork импортирует **один SKILL.md за раз**, поэтому пакет разбит на три отдельных
скилла. Ставятся независимо, через тот же интерфейс загрузки zip.

## Что ставим (3 файла)

| Пакет | Что это | Обязателен |
|---|---|---|
| `marketing-strategist.zip` | главный оркестратор (шаги 0–12) | да |
| `industry-research.zip` | субагент Шага 4 (отрасль) | желательно |
| `competitor-research.zip` | субагент Шага 5 (конкуренты) | желательно |

Оркестратор работает и без субагентов — на Шагах 4–5 есть фолбэк на инлайн-выполнение.
Но именно субагенты дают выигрыш по контексту, ради которого делалась v2.
Рекомендуется ставить все три.

## Установка (Cowork)

Загрузите каждый zip по очереди через Settings → Skills → Upload (или кнопку добавления
скилла). Cowork прочитает SKILL.md и покажет карточку. После загрузки убедитесь, что
тумблер скилла включён.

## Установка (Claude Code)

```bash
unzip marketing-strategist.zip -d ~/.claude/skills/
unzip industry-research.zip   -d ~/.claude/skills/
unzip competitor-research.zip -d ~/.claude/skills/
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
Без них — graceful fallback: DOCX → MD, XLSX → CSV, PDF → MD.

## На что обратить внимание на первом прогоне

1. **Субагенты — самодостаточны.** В каждый вложен свой reference (`references/...md`),
   путь внутри скилла уже поправлен. Дополнительно ничего класть не нужно.
2. **agent: general-purpose** в субагентах — они ПИШУТ артефакты. Хотите только
   исследование без записи — поменяйте на `agent: Explore` и уберите `Write`.
3. **Защита бюджета.** Площадочные скиллы (vk-ads-launcher, yandex-direct-funnel)
   должны иметь `disable-model-invocation: true` и создавать кампании в PAUSED.
   Это ставится в самих площадочных скиллах, не в этом пакете — проверьте отдельно.

## Версия

v2 — июнь 2026. Изменения — в CHANGELOG-v2.md.
