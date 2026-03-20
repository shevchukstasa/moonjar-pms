# ТЗ: Edge Profiles — Приложение Sales

## Контекст

PMS теперь принимает через webhook 3 новых поля в каждом item заказа.
Sales App должен позволить менеджеру выбирать тип торца при создании заказа
и передавать эти данные в PMS.

---

## Что нужно сделать

### 1. UI: Выбор торцевого профиля в карточке товара

В форме создания/редактирования позиции заказа (там, где выбирают цвет, размер, коллекцию) добавить:

**Поле 1: "Edge Profile" (Профиль торца)**
- Тип: dropdown (select)
- Значение по умолчанию: `straight` (Прямой)
- Варианты:

| Код | Название (EN) | Название (RU) |
|-----|---------------|---------------|
| `straight` | Straight | Прямой |
| `beveled_45` | Bevel 45° | Фаска 45° |
| `beveled_30` | Bevel 30° | Фаска 30° |
| `rounded` | Rounded | Скруглённый |
| `bullnose` | Bullnose | Полукруг |
| `pencil` | Pencil | Карандаш |
| `ogee` | Ogee | Ogee (S-профиль) |
| `waterfall` | Waterfall | Водопад |
| `stepped` | Stepped | Ступенчатый |
| `custom` | Custom | Кастомный |

**Поле 2: "Sides" (Количество сторон)**
- Тип: number selector (1-4) или кнопки 1/2/3/4
- Показывается ТОЛЬКО если edge_profile ≠ `straight`
- Значение по умолчанию: `1`
- Пояснение: "На скольких сторонах плитки обработать торец"

**Поле 3: "Edge Notes" (Примечание)**
- Тип: текстовое поле
- Показывается ТОЛЬКО если edge_profile = `custom`
- Placeholder: "Опишите профиль торца..."
- Макс длина: 255 символов

### 2. Визуальное отображение

- Если выбран не `straight` → показывать оранжевый badge в списке позиций заказа
- Формат: `Bullnose ×2` или `Фаска 45° ×4`
- Если `straight` или не выбран — ничего не показывать (стандартный)

### 3. Webhook Payload

При отправке заказа в PMS, добавить 3 поля в каждый элемент `items[]`:

```json
{
  "order_number": "02-21/02/2026",
  "items": [
    {
      "color": "Moss Glaze",
      "size": "10x10",
      "application": "SS",
      "collection": "Exclusive",
      "quantity": 260,
      "finishing": "Matt",
      "place_of_application": "face_only",

      "edge_profile": "bullnose",
      "edge_profile_sides": 2,
      "edge_profile_notes": null
    },
    {
      "color": "Milk Crackle",
      "size": "6x6",
      "application": "SS",

      "edge_profile": null,
      "edge_profile_sides": null,
      "edge_profile_notes": null
    }
  ]
}
```

**Правила:**
- Если профиль стандартный (`straight`) → отправлять `null` или `"straight"` (оба варианта OK)
- Если edge_profile не выбран → поля можно не отправлять вообще (backward compatible)
- `edge_profile_sides` обязателен если edge_profile ≠ straight/null
- `edge_profile_notes` обязателен только если edge_profile = `custom`

### 4. Валидация

- `edge_profile` должен быть одним из 10 допустимых значений (или null)
- `edge_profile_sides` — целое число от 1 до 4
- `edge_profile_notes` — строка до 255 символов

---

## Backward Compatibility

- Если Sales не отправляет эти поля → PMS считает `straight` (всё работает как раньше)
- Старые заказы не затрагиваются
- Изменения на стороне Sales можно деплоить независимо от PMS (PMS уже готов принимать)

---

## Приоритет

Средний. Реализовать после текущих задач. Основной production flow не зависит от этой фичи.
