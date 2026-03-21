# Moonjar PMS — Roadmap (План на будущее)

Последнее обновление: 2026-03-21

## v2.0 — Planned Features

### 🔐 MasterPermission — Гранулярные права на операции
**Приоритет:** Средний
**Когда:** После стабилизации v1

**Что это:** Возможность давать/забирать конкретные разрешения у конкретных пользователей, сверх их роли.

**Примеры:**
- PM Bali может управлять печами, но НЕ может отменять заказы
- PM Java может отменять заказы, но НЕ может менять рецепты
- Warehouse Bali может принимать материалы, но НЕ может списывать

**Что нужно:**
- [ ] Модель `MasterPermission` уже есть (api/models.py) — user_id + operation_id + granted_by
- [ ] Модель `Operation` нужна — справочник всех операций системы
- [ ] API: CRUD для разрешений (GET/POST/DELETE /api/permissions)
- [ ] Frontend: страница в Admin → "User Permissions" с матрицей пользователь × операция
- [ ] Middleware: `require_permission("cancel_order")` декоратор для эндпоинтов
- [ ] Миграция: от текущих ролевых проверок (`require_management`) к permission-based
- [ ] Обратная совместимость: если permission не задан → fallback на роль

**Зависимости:**
- Стабильная система ролей (v1)
- Dashboard Access (уже реализован)

---

### 📊 TOC Optimizer — Оптимизация загрузки печей
**Приоритет:** Высокий (v2)

**Что это:** Автоматическая оптимизация заполнения печей по Theory of Constraints.

**Что нужно:**
- [ ] Реализовать `business/planning_engine/optimizer.py` (сейчас заглушка)
- [ ] `optimize_batch_fill()` — максимизировать утилизацию печи
- [ ] `calculate_kiln_utilization()` — отчёт по утилизации за период
- [ ] API: POST /api/batches/{id}/optimize, GET /api/kilns/utilization-report
- [ ] Frontend: кнопка "Optimize" на странице батча

---

### 📅 Global Production Scheduler
**Приоритет:** Высокий (v2)

**Что это:** Глобальный планировщик — генерация производственного расписания на 14 дней.

**Что нужно:**
- [ ] Реализовать `business/planning_engine/scheduler.py` (сейчас заглушка)
- [ ] `generate_production_schedule()` — с учётом мощностей, календаря, приоритетов
- [ ] `recalculate_schedule()` — при изменении условий (отмена, поломка печи)
- [ ] API: POST /api/schedule/regenerate
- [ ] Scheduler job: ежедневно в 06:00 Bali

---

### 🏭 ManaShipment UI — Отгрузки в Mana
**Приоритет:** Низкий (v2)

**Что это:** Интерфейс для Warehouse — просмотр и подтверждение отгрузок дефектных плиток в Mana.

**Что нужно:**
- [ ] API router для ManaShipment (модель уже есть)
- [ ] Frontend: страница в Warehouse с таблицей отгрузок
- [ ] Кнопки: подтвердить, отклонить, отметить отгруженным

---

### 🤖 AI Chat Enhancement — Расширение RAG
**Приоритет:** Средний (v2)

**Что нужно:**
- [ ] Автоматическая переиндексация при изменении данных
- [ ] Индексация: заказы, рецепты, материалы, печи
- [ ] Семантический поиск по всей базе
- [ ] Чат-бот в Telegram с контекстом производства

---

### 🔒 2FA (Two-Factor Authentication)
**Приоритет:** Низкий (v2)

**Что нужно:**
- [ ] TOTP (Google Authenticator) — модели TotpBackupCode уже есть
- [ ] TOTP_ENCRYPTION_KEY уже в Settings
- [ ] UI: настройка 2FA в профиле пользователя
- [ ] Backup codes для восстановления

---

### ☁️ Cloud Backups (AWS S3)
**Приоритет:** Низкий (v2)

**Что нужно:**
- [ ] AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY уже в Settings
- [ ] daily_database_backup() — ежедневный бэкап в S3
- [ ] UI: статус бэкапов в Admin

---

## Completed (v1)

- ✅ 10/10 Backend→Frontend страниц реализованы
- ✅ Kiln Inspection + Repair Log
- ✅ Consumption Measurement Tasks
- ✅ Firing Profiles (multi-interval)
- ✅ Admin Settings (escalation, receiving, defects, consolidation, lead times)
- ✅ Reports, Dashboard Access, Grinding, Factory Calendar
- ✅ Finished Goods, Reconciliations, Kiln Maintenance
- ✅ Stages, Firing Schedules
- ✅ Prompt Caching (-90% на AI вызовы)
- ✅ Audit Logging infrastructure
- ✅ Dead code scanner
- ✅ Architecture audit system
