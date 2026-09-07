# Установка — marketing-strategist

Один скилл, один архив. Скачали, загрузили, работает.

## Claude Desktop и claude.ai

1. Скачайте `marketing-strategist.zip` со страницы
   [последнего релиза](https://github.com/ai-hub-open/marketing-strategist/releases/latest)
   — файл лежит в разделе **Assets**.
2. В Claude откройте **Settings → Capabilities → Skills** и нажмите загрузку скилла.
3. Выберите скачанный `marketing-strategist.zip`.
4. Убедитесь, что переключатель скилла включён.

> Не используйте зелёную кнопку **Code → Download ZIP** на главной странице
> репозитория. Она отдаёт архив с папкой `marketing-strategist-main/` внутри и
> файлами репозитория, которых загрузчик скиллов не ждёт. Нужен именно файл из
> раздела Assets релиза.

**Требуется включённое выполнение кода.** Скилл генерирует DOCX, XLSX и PDF
питоновскими скриптами. В Claude это работает при включённой настройке
[создания и редактирования файлов](https://support.claude.com/en/articles/12111783-create-and-edit-files-with-claude).
Если она выключена, документы сохранятся в текстовом виде: DOCX → Markdown,
XLSX → CSV, PDF → Markdown.

## Claude Code

```bash
git clone https://github.com/ai-hub-open/marketing-strategist.git
cp -r marketing-strategist ~/.claude/skills/marketing-strategist
```

Перезапустите `claude` — новая папка подхватится после рестарта.

Зависимости скриптов ставятся отдельно:

```bash
pip install python-docx openpyxl reportlab
```
Без них скрипты не падают, а сохраняют документы в текстовых форматах.


## Проверка

Спросите Claude: `Какие скиллы доступны?` — в списке должен быть
`marketing-strategist`.

Триггер: «подготовь маркетинговую стратегию для X, сайт Y».

Скилл работает пошагово и после каждого шага ждёт подтверждения. Первый прогон
занимает 1-2 сессии; артефакты складываются в папку `marketing-campaigns/<slug>/`.

## Сборка архива вручную

Релизный архив собирается из репозитория:

```bash
pip install pyyaml
python tools/build_skill_zip.py          # → dist/marketing-strategist.zip
python tools/build_skill_zip.py --check  # только валидация
```

Сборщик проверяет то, на чём чаще всего ломается загрузка: ровно один `SKILL.md`,
корректный YAML во фронтматтере, только поля `name` и `description`, длина
описания, существование всех файлов, на которые ссылается `SKILL.md`. Файлы
репозитория (README, LICENSE, CHANGELOG, `tools/`) в архив не попадают.

## Что дальше

На Шаге 12 скилл предлагает передать готовые артефакты в площадочные скиллы —
[yandex-direct-manager](https://github.com/ai-hub-open/yandex-direct-manager) и
[vk-ads-manager](https://github.com/ai-hub-open/vk-ads-manager). Они ставятся
отдельно и создают кампании черновиком или на паузе — запуск остаётся за
человеком. Это свойство самих площадочных пакетов; проверьте его при установке.

## Версия

v2 — июнь 2026. Изменения — в CHANGELOG-v2.md.
