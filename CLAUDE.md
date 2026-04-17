# Moonjar PMS — Project-Specific AI Rules

> Этот файл читается Claude Code при каждой сессии в этом репозитории.
> Глобальные правила в `~/.claude/CLAUDE.md`. Этот файл переопределяет и дополняет их конкретикой Moonjar.

## ЖЕЛЕЗНОЕ ПРАВИЛО: Никаких предположений — только проверенные факты

**НИКОГДА не говори «возможно», «скорее всего», «наверное» если можешь ПРОВЕРИТЬ.**
Если не проверил — не озвучивай. Молча проверь и дай факт.
- Не «возможно у неё дефицит» → проверь API и скажи «позиция X заблокирована потому что Cobalt Black: need 3.85, have 2.88, deficit 0.97»
- Не «скорее всего деплой упал» → проверь GH deployments API и скажи «деплой c853cda status=failure»
- Если проверить невозможно — скажи «не могу проверить потому что [причина]», а не выдумывай

## ЖЕЛЕЗНОЕ ПРАВИЛО: После каждого деплоя — проверяй Railway логи сам

После `git push origin main` и успешного деплоя — **обязательно**:
```bash
railway logs --service d080298d-26a1-47b0-ac44-766c1b3b10b2 2>&1 | grep -iE "error|fail|exception|traceback|critical|warning" | tail -30
```

Если находишь ошибки — чинишь их в том же сеансе. Не ждёшь пока пользователь скажет.
Не только про свою текущую задачу — **любые** ошибки на сервере требуют внимания.
Пользователя не дёргать, чтобы скидывал логи — у тебя есть Railway CLI доступ.

Service IDs (запомнить):
- Backend: `d080298d-26a1-47b0-ac44-766c1b3b10b2`
- Project: `d37c96fa-1d73-41a6-8853-aab39128cc40`

## ЖЕЛЕЗНОЕ ПРАВИЛО: Починил — проверь результат сам

**После ЛЮБОГО багфикса или изменения, влияющего на данные/UI:**
1. Дождись деплоя (health check)
2. Сделай запрос к API и ПОКАЖИ реальные данные — до и после
3. Если фикс касается отображения (UI) — сделай скриншот или покажи ответ API, который рендерит фронт
4. Если фикс касается расчётов — покажи конкретные числа (было X, стало Y, ожидалось Z)
5. **НЕ ГОВОРИ пользователю "обнови страницу и проверь"** — это твоя работа, не его

Если нет возможности проверить (например, нет данных в БД для теста) — честно скажи: "не могу проверить потому что [причина], нужна помощь".

## ЖЕЛЕЗНОЕ ПРАВИЛО: Pre-flight check перед ЛЮБОЙ задачей в этом репо

Прежде чем писать или править код в Moonjar PMS, **обязательно** пройти этот чек-лист и явно упомянуть результат в ответе. Никаких догадок.

### 1. Бизнес-логика (source of truth)

Прочитать релевантный раздел в:
- `docs/BUSINESS_LOGIC.md` — краткий свод правил
- `docs/BUSINESS_LOGIC_FULL.md` — полная версия с §-нумерацией (~950 строк)
- `ARCHITECTURE.md` — системная архитектура
- `docs/BLOCKING_TASKS.md` — блокирующие задачи
- `docs/guides/GUIDE_PRODUCTION_MANAGER.md` — как PM реально работает с системой
- `docs/guides/GUIDE_CEO_EN.md` — что видит CEO
- `docs/guides/GUIDE_QM_EN.md` — QC workflow

**Если бизнес-правило в доках расходится с моей памятью о диалоге — доки источник истины, не память.**
**Если правила нет в доках вообще — первым шагом дописать его в `BUSINESS_LOGIC_FULL.md`, потом кодить.**

### 2. Существующий код

- `grep` по именам функций/моделей — может уже реализовано
- `git log --oneline -S "keyword" -- path` — был ли коммит на эту тему, был ли откачен
- Прочитать HEAD-версию файла, не полагаться на "я помню как было"

### 3. API контракты

- `docs/API_CONTRACTS.md` + `docs/API_ENDPOINTS_FULL.md`
- Актуальный роутер в `api/routers/*.py`
- Схемы запроса/ответа должны совпасть с frontend hook'ом

### 4. Frontend ↔ Backend совместная проверка

Если задача касается UI:
- Frontend: `presentation/dashboard/src/` (компонент → hook → axios/fetch)
- Backend: `api/routers/*.py` → `business/services/*.py` → `api/models.py`

**Не правлю одну сторону не глядя в другую.** Не добавляю поле в ответ API не проверив, рендерит ли его фронт. Не добавляю кнопку на UI не проверив, что эндпоинт её принимает.

### 5. Память vs git

Если я "помню" что "мы уже это делали/фиксили/обсуждали" — **подтвердить в git**:
```
git log --oneline -S "<keyword>" -- <path>
git log --oneline --grep "<keyword>"
```
Если коммита нет — значит не делали, только обсуждали. Честно сказать: "мы это обсуждали, но в коде нет, делаю сейчас".

## Формат отчёта перед началом работы

Перед тем как писать код, всегда отчитываюсь примерно так:

> Проверил:
> — `docs/BUSINESS_LOGIC_FULL.md §N` говорит X
> — В коде `business/services/Y.py:123` реализовано Z
> — В git log фикса на эту тему не было
> — Расхождение: [что именно]
> План: [конкретные файлы и изменения]

Только после этого начинаю Edit/Write.

## Пост-деплой верификация (Moonjar-specific)

После `git push origin main`:
1. Подождать ~90 сек (Railway Nixpacks билд)
2. `curl -s https://moonjar-pms-production.up.railway.app/api/health` → `{"status":"ok"}`
3. Ключевые эндпоинты возвращают 401, а не 500: `/api/orders`, `/api/materials`, `/api/positions`
4. Если был новый эндпоинт — проверить что он отвечает

## Ключевые бизнес-правила (справочник для self-check)

**Эти правила ОБЯЗАНЫ быть задокументированы в `docs/BUSINESS_LOGIC_FULL.md`. Если их там нет — добавить, прежде чем кодить.**

### Scheduling (§4 Backward Scheduling)
- **Стратегия**: HIGH-WIP left-shift (forward). Всё что можно делать сегодня — делается сегодня. Завтра — завтра. И т.д.
- **Hard-блокеры** (сдвигают вправо): materials availability, blocking tasks (stone/recipe/stencil с учётом сроков поставщиков), FIFO min_start (предыдущие ордера), `date.today()`.
- **Daily capacity cap per stage**: для каждой стадии (glazing, engobe, sorting, packing, edge_cleaning, etc.) считается пропускная способность дня на основе `StageTypologySpeed`: `brigade_size × shift_count × shift_duration_hours × productivity_rate`. Как только capacity заполнена — остаток работы уходит на следующий день.
- **Kiln** — отдельный constraint (печь как drum), проверяется по зонам (`get_zone_capacity`) + maintenance windows.
- **Дедлайн** — только триггер алерта (`_create_deadline_exceeded_alert`), не анкор расписания.
- **Файлы**: `business/services/production_scheduler.py`, `business/services/pull_system.py`, `business/planning_engine/scheduler.py`

### Materials (§2 Stone Reservation)
- Резерв при статусе `PLANNED` → `IN_PRODUCTION`. Адаптируется при split/merge позиций.
- INSUFFICIENT_MATERIALS → блокирующая задача + дата прибытия партии становится `material_ready_date` для планировщика.

### Blocking Tasks
- См. `docs/BLOCKING_TASKS.md`. Типы: INSUFFICIENT_MATERIALS, AWAITING_RECIPE, AWAITING_STENCIL, COLOR_MATCHING, CONSUMPTION_DATA, BOARD_ORDER_NEEDED, SHELF_REPLACEMENT_NEEDED.
- Каждый тип имеет ETA от поставщика → блокирует scheduling до этой даты.

### Points & Gamification (§ appended)
- Accuracy scoring: ±1%=10pts, ±3%=7pts, ±5%=5pts, ±10%=3pts, else 1pt. Photo verify +2 pts.
- Годовое накопление, reset 1 января.

### Payroll
- `docs/PAYROLL_RULES_INDONESIA.md` — PPh 21, BPJS, overtime per PP 35/2021.

## Git / Commit hygiene

- Commit messages в формате: `short summary` + пустая строка + тело.
- Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
- Никаких `git add -A` / `git add .` без проверки `git status` — боязнь случайно закоммитить `.env` или фото.
- Не amend, только новые коммиты (pre-commit хук падает → фиксим → новый коммит).

## Тест-прогон перед коммитом

- `python3 -c "import ast; ast.parse(open('<file>').read())"` — минимум syntax check
- Если есть тесты на модуль — прогнать их: `pytest tests/unit/test_<module>.py -x`
- Для миграций — dry-run на копии БД, если задеваем большие таблицы

## Anti-patterns (что НЕ делать)

- ❌ "Щас быстро поправлю backward на forward" без чтения `BUSINESS_LOGIC_FULL.md §4`
- ❌ Писать "мы уже фиксили X" без `git log -S`
- ❌ Добавлять поле в модель не проверив, нужна ли Alembic migration
- ❌ `try: ... except Exception: pass` без логирования — тихо глотает ошибки
- ❌ Править `production_scheduler.py` не проверив, что реально крутится в проде через `/api/health`
- ❌ Менять `Column(JSONB)` на `Column(MutableDict.as_mutable(JSONB))` без понимания как это взаимодействует с existing data (мы на это уже наступали — см. commit `0f5b496`)
