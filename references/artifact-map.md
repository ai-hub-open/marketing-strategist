# Карта артефактов стратега (связи между шагами)

Какой файл папки кампании нужен какому шагу. Справка для агента: в чат имена файлов не пишутся.

```
00_client_materials.md ─┬─→ Шаг 2 (заполнение брифа)
                        ├─→ Шаг 4 industry-research (источники)
                        ├─→ Шаг 6 hypothesis-builder (сырые гипотезы)
                        ├─→ Шаг 7 Buyer Personas
                        └─→ Шаг 8 usp-generator

01_brief.md ─┬─→ Шаг 3 strategy (в т.ч. горизонт планирования)
             ├─→ Шаг 4 industry-research
             ├─→ Шаг 9 channel-selection (бюджет, гео, горизонт)
             └─→ Шаг 10 budget-allocation (месячный бюджет × горизонт из брифа)

channel_history.md ─┬─→ Шаг 9 channel-selection (колонка «История», пометка «без истории»)
                    └─→ Шаг 12 handoff (обязательный файл для площадочных скиллов)

03_demand.md ───→ Шаг 4 industry-research, Шаг 9 channel-selection (показы по группам запросов)

02_strategy.md ─┬─→ Шаг 4 industry-research (тип спроса)
                ├─→ Шаг 9 channel-selection (тип спроса)
                ├─→ Шаг 10 budget-allocation (фазы)
                └─→ Шаг 11 kpi-framework (целевые KPI)

industry_research.json ─┬─→ Шаг 9 channel-selection (бенчмарки CAC)
                        ├─→ Шаг 10 budget-allocation (отраслевые доли)
                        └─→ Шаг 11 kpi-framework (отраслевые KPI)

05_competitor_analysis.md ─→ Шаг 9 channel-selection (матрица каналов конкурентов)

hypotheses.md (selected) ─┬─→ Шаг 7 Buyer Personas (сегменты)
                          ├─→ Шаг 8 usp-generator (способы подачи)
                          └─→ Шаг 9 channel-selection (где проверяем)

07_personas.md ─→ Шаг 9 channel-selection (где бывают в интернете)

usp_final.json ─→ финальный отчёт + handoff

channel_selection.json ─┬─→ Шаг 10 budget-allocation (по каким каналам)
                        ├─→ Шаг 11 kpi-framework (по каким каналам KPI)
                        └─→ Шаг 12 финальный отчёт + handoff

budget_allocation.json ─┬─→ Шаг 11 kpi-framework
                        └─→ Шаг 12 финальный отчёт

kpi_framework.json ─→ Шаг 12 финальный отчёт
```

При сбое любого шага — проверь, что у него есть все нужные входы. Нет входа — возвращайся, закрой пробел, потом продолжай.
