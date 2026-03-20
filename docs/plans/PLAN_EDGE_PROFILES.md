# ПЛАН: Edge Profiles (Торцевые профили)

## Контекст

Сейчас у плитки по умолчанию прямые торцы. Но торцы могут быть разных видов (фаска, скругление, bullnose и т.д.). Нужно:
1. Настроить в Sales/webhook передачу типа торца
2. Хранить в PMS
3. Отображать, если торец нестандартный
4. Учитывать в расчёте площади глазурования

---

## 1. Список стандартных профилей торцов

```
edge_profile_type:
  straight      — Прямой (по умолчанию, 90°)
  beveled_45    — Фаска 45°
  beveled_30    — Фаска 30°
  rounded       — Скруглённый (radius)
  bullnose      — Полукруг (полный bullnose)
  pencil        — Карандаш (маленькое скругление)
  ogee          — Ogee (S-образный)
  waterfall     — Водопад (скос + скругление)
  stepped       — Ступенчатый
  custom        — Кастомный (описание в notes)
```

Также хранятся:
- **Количество обработанных сторон**: 1, 2, 3, 4
- **Примечание**: для custom-профиля

---

## 2. Изменения в базе данных

### 2a. Новый enum

Файл: **`/api/enums.py`**

Добавить `EdgeProfileType(str, Enum)` с values: `straight`, `beveled_45`, `beveled_30`, `rounded`, `bullnose`, `pencil`, `ogee`, `waterfall`, `stepped`, `custom`.

### 2b. Новые поля в `production_order_items`

Файл: **`/api/models.py`** (класс `ProductionOrderItem`)

```python
edge_profile = Column(sa.String(30), nullable=True)           # enum value: 'straight', 'bullnose', etc.
edge_profile_sides = Column(sa.SmallInteger, nullable=True)   # 1, 2, 3, 4 — количество обработанных сторон
edge_profile_notes = Column(sa.String(255), nullable=True)    # описание для custom
```

### 2c. Новые поля в `order_positions`

Файл: **`/api/models.py`** (класс `OrderPosition`)

```python
edge_profile = Column(sa.String(30), nullable=True)
edge_profile_sides = Column(sa.SmallInteger, nullable=True)
edge_profile_notes = Column(sa.String(255), nullable=True)
```

**Решение**: Использовать `String(30)` (не PgEnum) — по аналогии с `place_of_application`, `bowl_shape`, `application_method_code`. Проще для расширения, не требует ALTER TYPE.

### 2d. Миграция

- ADD COLUMN `edge_profile` VARCHAR(30) к `production_order_items`
- ADD COLUMN `edge_profile_sides` SMALLINT к `production_order_items`
- ADD COLUMN `edge_profile_notes` VARCHAR(255) к `production_order_items`
- ADD COLUMN `edge_profile` VARCHAR(30) к `order_positions`
- ADD COLUMN `edge_profile_sides` SMALLINT к `order_positions`
- ADD COLUMN `edge_profile_notes` VARCHAR(255) к `order_positions`

---

## 3. Изменения API (Backend)

### 3a. Pydantic-схемы

Файл: **`/api/schemas.py`**

В `OrderPositionCreate`, `OrderPositionUpdate`, `OrderPositionResponse` добавить:

```python
edge_profile: Optional[str] = None
edge_profile_sides: Optional[int] = None
edge_profile_notes: Optional[str] = None
```

### 3b. Webhook (Sales → PMS)

Файл: **`/api/routers/integration.py`**

В `_create_order_from_webhook()`:

```python
item = ProductionOrderItem(
    ...
    edge_profile=item_data.get("edge_profile"),
    edge_profile_sides=item_data.get("edge_profile_sides"),
    edge_profile_notes=item_data.get("edge_profile_notes"),
)
```

**Payload от Sales** (новые поля в `items[]`):

```json
{
  "items": [
    {
      "color": "Ivory",
      "size": "10x20",
      "edge_profile": "bullnose",
      "edge_profile_sides": 2,
      "edge_profile_notes": null
    }
  ]
}
```

Если `edge_profile` не передан — считаем `straight` (NULL = straight = стандартный).

### 3c. Order Intake Pipeline

Файл: **`/business/services/order_intake.py`**

В `process_order_item()` добавить копирование:

```python
position = OrderPosition(
    ...
    edge_profile=getattr(item, "edge_profile", None),
    edge_profile_sides=getattr(item, "edge_profile_sides", None),
    edge_profile_notes=getattr(item, "edge_profile_notes", None),
)
```

### 3d. Position router

В сериализации ответа добавить `edge_profile`, `edge_profile_sides`, `edge_profile_notes`.
При split позиции — пробросить новые поля.

---

## 4. Изменения Frontend

### 4a. TypeScript интерфейсы

В `PositionItem` interface добавить:

```typescript
edge_profile?: string | null;
edge_profile_sides?: number | null;
edge_profile_notes?: string | null;
```

### 4b. Human-readable labels

```typescript
const EDGE_PROFILE_LABELS: Record<string, string> = {
  straight: 'Straight',
  beveled_45: 'Bevel 45°',
  beveled_30: 'Bevel 30°',
  rounded: 'Rounded',
  bullnose: 'Bullnose',
  pencil: 'Pencil',
  ogee: 'Ogee',
  waterfall: 'Waterfall',
  stepped: 'Stepped',
  custom: 'Custom',
};
```

### 4c. Отображение

Показывать badge **только когда профиль нестандартный** (не `straight` и не `null`).
Пример: `Bullnose x2` или `Bevel 45° x4`.

Места:
- **OrderDetailPage** — колонка "Edge" в таблице
- **PositionRow (Tablo)** — badge
- **KilnLevelView** — badge

---

## 5. Влияние на Kiln Calculator

**Минимальное**. Декоративный профиль торца **НЕ влияет** на:
- Геометрию загрузки (edge loading зависит от L/W/thickness)
- Вместимость печи
- Flat vs edge loading decision

**Но влияет** на площадь глазурования (если `place_of_application` включает торцы):

| Профиль | Коэффициент площади торца |
|---------|--------------------------|
| straight | 1.0 |
| beveled_45 | 1.0 |
| beveled_30 | 1.05 |
| rounded | 1.15 |
| bullnose | 1.57 (полукруг: π*r vs 2r) |
| pencil | 1.05 |
| ogee | 1.25 |
| waterfall | 1.15 |
| stepped | 1.1 |
| custom | 1.2 (среднее) |

Изменить **`/business/services/surface_area.py`**: при расчёте площади торца (`one_long_edge = h_m * t_m`) умножать на коэффициент.

---

## 6. Flow данных

```
1. Sales App → edge_profile per item
   ↓
2. POST /api/integration/webhook/sales-order
   payload.items[].edge_profile = "bullnose"
   payload.items[].edge_profile_sides = 2
   ↓
3. _create_order_from_webhook() → ProductionOrderItem(edge_profile="bullnose")
   ↓
4. process_order_item() → OrderPosition(edge_profile="bullnose")
   ↓
5. calculate_glazeable_sqm_for_position() — коэффициент для bullnose
   ↓
6. Frontend:
   - OrderDetailPage: колонка "Edge" → "Bullnose x2"
   - PositionRow (Tablo): badge если нестандартный
   - KilnLevelView: badge
```

---

## 7. Порядок реализации

1. Миграция — добавить 6 колонок (2 таблицы × 3 поля)
2. Enum + Models — `EdgeProfileType` enum, поля в моделях
3. Schemas — Pydantic Create/Update/Response
4. Webhook — маппинг из payload в ProductionOrderItem
5. Order Intake — копирование в OrderPosition
6. Position Router — сериализация + копирование при split
7. Surface Area — поправочный коэффициент
8. Frontend — labels, badges, колонка в таблице

---

## 8. Координация с Sales App

Sales App должен добавить в payload три новых опциональных поля per item:
- `edge_profile: string | null`
- `edge_profile_sides: number | null`
- `edge_profile_notes: string | null`

**Backward compatible**: если Sales не передаёт эти поля, PMS считает `straight` (null = straight). Миграции существующих данных не требуется.

---

## Критические файлы для реализации

| Файл | Что делать |
|------|-----------|
| `api/models.py` | Добавить 3 поля в `ProductionOrderItem` и `OrderPosition` |
| `api/enums.py` | Добавить `EdgeProfileType` |
| `api/schemas.py` | Добавить поля в Pydantic-схемы |
| `api/routers/integration.py` | Маппинг webhook payload → item |
| `business/services/order_intake.py` | Копирование item → position |
| `api/routers/positions.py` | Сериализация + split |
| `business/services/surface_area.py` | Коэффициент площади торца |
| `presentation/dashboard/src/components/tablo/PositionRow.tsx` | Interface + badge |
| `presentation/dashboard/src/pages/OrderDetailPage.tsx` | Колонка "Edge" |
