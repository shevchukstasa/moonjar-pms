# Moonjar PMS — Complete Database Schema

> Auto-extracted from `api/models.py` (2575 lines, 90+ models)
> Generated: 2026-03-26

All tables use UUID primary keys (`uuid4`), timestamps with timezone, and follow PostgreSQL naming conventions.

---

## Table of Contents

1. [Auth & Users](#1-auth--users) (7 tables)
2. [Factories & Settings](#2-factories--settings) (8 tables)
3. [Orders & Positions](#3-orders--positions) (8 tables)
4. [Materials & Recipes](#4-materials--recipes) (12 tables)
5. [Kilns & Batches](#5-kilns--batches) (14 tables)
6. [Quality & Inspections](#6-quality--inspections) (8 tables)
7. [Defects & Repairs](#7-defects--repairs) (8 tables)
8. [Warehouse & Inventory](#8-warehouse--inventory) (6 tables)
9. [Packaging](#9-packaging) (3 tables)
10. [Shipments & Delivery](#10-shipments--delivery) (4 tables)
11. [HR & Payroll](#11-hr--payroll) (2 tables)
12. [TPS & Production Metrics](#12-tps--production-metrics) (5 tables)
13. [Notifications & Audit](#13-notifications--audit) (5 tables)
14. [Security](#14-security) (5 tables)
15. [AI & Media](#15-ai--media) (3 tables)
16. [Reference & Configuration](#16-reference--configuration) (8 tables)

---

## 1. Auth & Users

### `users`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default uuid4 |
| email | String(255) | UNIQUE, NOT NULL |
| name | String(200) | NOT NULL |
| role | Enum(UserRole) | NOT NULL |
| password_hash | String(255) | nullable |
| google_id | String(255) | UNIQUE, nullable |
| telegram_user_id | BigInteger | UNIQUE, nullable |
| language | Enum(LanguagePreference) | NOT NULL, default EN |
| is_active | Boolean | NOT NULL, default true |
| failed_login_count | Integer | NOT NULL, default 0 |
| locked_until | DateTime(tz) | nullable |
| totp_secret_encrypted | String(500) | nullable |
| totp_enabled | Boolean | NOT NULL, default false |
| last_password_change | DateTime(tz) | nullable |
| created_at | DateTime(tz) | NOT NULL, server_default now() |
| updated_at | DateTime(tz) | NOT NULL, server_default now() |

**Relationships:** user_factories (UserFactory, selectin)

**UserRole values:** owner, administrator, ceo, production_manager, quality_manager, warehouse, sorter_packer, purchaser, master, senior_master

### `user_factories`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| user_id | UUID | FK users.id CASCADE, NOT NULL |
| factory_id | UUID | FK factories.id CASCADE, NOT NULL |
| created_at | DateTime(tz) | NOT NULL |

**Unique:** (user_id, factory_id)

### `user_dashboard_access`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| user_id | UUID | FK users.id CASCADE, NOT NULL |
| dashboard_type | Enum(DashboardType) | NOT NULL |
| granted_by | UUID | FK users.id, NOT NULL |
| granted_at | DateTime(tz) | NOT NULL |

**Unique:** (user_id, dashboard_type)

### `active_sessions`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| user_id | UUID | FK users.id CASCADE, NOT NULL |
| token_jti | String(64) | UNIQUE, NOT NULL |
| ip_address | INET | NOT NULL |
| user_agent | Text | nullable |
| device_label | String(200) | nullable |
| expires_at | DateTime(tz) | NOT NULL |
| revoked | Boolean | NOT NULL, default false |
| revoked_at | DateTime(tz) | nullable |
| revoked_reason | String(100) | nullable |
| created_at | DateTime(tz) | NOT NULL |

### `totp_backup_codes`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| user_id | UUID | FK users.id CASCADE, NOT NULL |
| code_hash | String(255) | NOT NULL |
| used | Boolean | NOT NULL, default false |
| used_at | DateTime(tz) | nullable |
| created_at | DateTime(tz) | NOT NULL |

### `notification_preferences`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| user_id | UUID | FK users.id CASCADE, NOT NULL |
| category | String(50) | NOT NULL |
| channel | Enum(NotificationChannel) | NOT NULL, default IN_APP |
| created_at | DateTime(tz) | NOT NULL |
| updated_at | DateTime(tz) | NOT NULL |

**Unique:** (user_id, category)

### `master_permissions`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| user_id | UUID | FK users.id, NOT NULL |
| operation_id | UUID | FK operations.id, NOT NULL |
| granted_by | UUID | FK users.id, NOT NULL |
| granted_at | DateTime(tz) | auto |

**Unique:** (user_id, operation_id)

---

## 2. Factories & Settings

### `factories`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| name | String(200) | NOT NULL |
| location | String(200) | nullable |
| address | Text | nullable |
| region | String(100) | nullable |
| settings | JSONB | nullable |
| timezone | String(50) | NOT NULL, default Asia/Makassar |
| masters_group_chat_id | BigInteger | nullable |
| purchaser_chat_id | BigInteger | nullable |
| telegram_language | String(10) | NOT NULL, default 'id' |
| receiving_approval_mode | String(20) | NOT NULL, default 'all' |
| kiln_constants_mode | Enum(KilnConstantsMode) | NOT NULL, default MANUAL |
| rotation_rules | JSONB | nullable |
| served_locations | JSONB | nullable (e.g. ["Bali", "Lombok"]) |
| is_active | Boolean | NOT NULL, default true |
| created_at | DateTime(tz) | NOT NULL |

### `factory_calendar`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| factory_id | UUID | FK factories.id, NOT NULL |
| date | Date | NOT NULL |
| is_working_day | Boolean | NOT NULL, default true |
| num_shifts | Integer | NOT NULL, default 2 |
| holiday_name | String(200) | nullable |
| holiday_source | String(50) | nullable ('government', 'balinese', 'manual') |
| approved_by | UUID | FK users.id, nullable |
| approved_at | DateTime(tz) | nullable |
| notes | Text | nullable |
| created_at | DateTime(tz) | auto |

**Unique:** (factory_id, date)

### `shifts`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| factory_id | UUID | FK factories.id, NOT NULL |
| shift_number | Integer | NOT NULL |
| shift_name | String(100) | nullable |
| start_time | Time | NOT NULL |
| end_time | Time | NOT NULL |
| days_of_week | ARRAY(Integer) | default {1,2,3,4,5,6} |
| is_active | Boolean | NOT NULL, default true |

**Unique:** (factory_id, shift_number)

### `system_settings`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| key | String(100) | UNIQUE, NOT NULL |
| value | Text | nullable |
| updated_at | DateTime(tz) | auto |

### `receiving_settings`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| factory_id | UUID | FK factories.id, UNIQUE, NOT NULL |
| approval_mode | String(20) | NOT NULL, default 'all' |
| updated_by | UUID | FK users.id, nullable |
| updated_at | DateTime(tz) | auto |

### `escalation_rules`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| factory_id | UUID | FK factories.id, NOT NULL |
| task_type | String(50) | NOT NULL |
| pm_timeout_hours | Numeric(6,2) | NOT NULL |
| ceo_timeout_hours | Numeric(6,2) | NOT NULL |
| owner_timeout_hours | Numeric(6,2) | NOT NULL |
| night_level | Integer | default 1 |
| is_active | Boolean | default true |

**Unique:** (factory_id, task_type)

### `operations`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| factory_id | UUID | FK factories.id, NOT NULL |
| name | String(100) | NOT NULL |
| description | Text | nullable |
| default_time_minutes | Numeric(8,2) | nullable |
| is_active | Boolean | default true |
| sort_order | Integer | default 0 |
| created_at | DateTime(tz) | auto |
| updated_at | DateTime(tz) | auto |

### `edge_height_rules`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| factory_id | UUID | FK factories.id, NOT NULL |
| thickness_mm_min | Numeric(6,2) | NOT NULL |
| thickness_mm_max | Numeric(6,2) | NOT NULL |
| max_edge_height_cm | Numeric(6,2) | NOT NULL |
| is_tested | Boolean | default false |
| notes | Text | nullable |
| created_at | DateTime(tz) | auto |

---

## 3. Orders & Positions

### `production_orders`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| order_number | String(100) | NOT NULL |
| client | String(300) | NOT NULL |
| client_location | String(300) | nullable |
| sales_manager_name | String(200) | nullable |
| sales_manager_contact | String(300) | nullable |
| factory_id | UUID | FK factories.id, NOT NULL |
| document_date | Date | nullable |
| production_received_date | Date | nullable |
| final_deadline | Date | nullable |
| schedule_deadline | Date | nullable |
| desired_delivery_date | Date | nullable |
| status | Enum(OrderStatus) | NOT NULL, default NEW |
| status_override | Boolean | NOT NULL, default false |
| sales_status | String(100) | nullable |
| source | Enum(OrderSource) | NOT NULL, default MANUAL |
| external_id | String(255) | nullable |
| sales_payload_json | JSONB | nullable |
| mandatory_qc | Boolean | NOT NULL, default false |
| notes | Text | nullable |
| shipped_at | DateTime(tz) | nullable |
| cancellation_requested | Boolean | NOT NULL, default false |
| cancellation_requested_at | DateTime(tz) | nullable |
| cancellation_decision | String(20) | nullable |
| cancellation_decided_at | DateTime(tz) | nullable |
| cancellation_decided_by | UUID | FK users.id, nullable |
| change_req_payload | JSONB | nullable |
| change_req_status | String(20) | NOT NULL, default 'none' |
| change_req_requested_at | DateTime(tz) | nullable |
| change_req_decided_at | DateTime(tz) | nullable |
| change_req_decided_by | UUID | FK users.id, nullable |
| created_at | DateTime(tz) | NOT NULL |
| updated_at | DateTime(tz) | NOT NULL |

**Unique:** (source, external_id)

### `production_order_items`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| order_id | UUID | FK production_orders.id CASCADE, NOT NULL |
| color | String(100) | NOT NULL |
| color_2 | String(100) | nullable |
| size | String(50) | NOT NULL |
| application | String(100) | nullable |
| finishing | String(100) | nullable |
| thickness | Numeric(5,1) | NOT NULL, default 11.0 |
| quantity_pcs | Integer | NOT NULL |
| quantity_sqm | Numeric(10,3) | nullable |
| collection | String(100) | nullable |
| application_type | String(100) | nullable |
| place_of_application | String(50) | nullable |
| product_type | Enum(ProductType) | NOT NULL, default TILE |
| shape | String(20) | nullable |
| length_cm | Numeric(7,2) | nullable |
| width_cm | Numeric(7,2) | nullable |
| depth_cm | Numeric(7,2) | nullable (sinks) |
| bowl_shape | String(20) | nullable (sinks) |
| shape_dimensions | JSON | nullable |
| edge_profile | String(30) | nullable |
| edge_profile_sides | SmallInteger | nullable |
| edge_profile_notes | String(255) | nullable |
| created_at | DateTime(tz) | NOT NULL |

### `order_positions`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| order_id | UUID | FK production_orders.id CASCADE, NOT NULL |
| order_item_id | UUID | FK production_order_items.id, NOT NULL |
| parent_position_id | UUID | FK order_positions.id, nullable (self-ref for splits) |
| factory_id | UUID | FK factories.id, NOT NULL |
| status | Enum(PositionStatus) | NOT NULL, default PLANNED |
| batch_id | UUID | FK batches.id, nullable |
| resource_id | UUID | FK resources.id, nullable |
| placement_position | String(100) | nullable |
| placement_level | Integer | nullable |
| delay_hours | Numeric(8,1) | default 0 |
| reservation_at | DateTime(tz) | nullable |
| materials_written_off_at | DateTime(tz) | nullable |
| quantity | Integer | NOT NULL |
| quantity_sqm | Numeric(10,3) | nullable |
| quantity_with_defect_margin | Integer | nullable |
| color | String(100) | NOT NULL |
| color_2 | String(100) | nullable |
| size | String(50) | NOT NULL |
| application | String(100) | nullable |
| finishing | String(100) | nullable |
| collection | String(100) | nullable |
| application_type | String(100) | nullable |
| place_of_application | String(50) | nullable |
| product_type | Enum(ProductType) | NOT NULL, default TILE |
| shape | Enum(ShapeType) | default RECTANGLE |
| length_cm | Numeric(7,2) | nullable |
| width_cm | Numeric(7,2) | nullable |
| depth_cm | Numeric(7,2) | nullable (sinks) |
| bowl_shape | String(20) | nullable |
| shape_dimensions | JSON | nullable |
| edge_profile | String(30) | nullable |
| edge_profile_sides | SmallInteger | nullable |
| edge_profile_notes | String(255) | nullable |
| glazeable_sqm | Numeric(10,4) | nullable |
| thickness_mm | Numeric(5,1) | NOT NULL, default 11.0 |
| recipe_id | UUID | FK recipes.id, nullable |
| size_id | UUID | FK sizes.id, nullable |
| mandatory_qc | Boolean | NOT NULL, default false |
| split_category | Enum(SplitCategory) | nullable |
| is_merged | Boolean | NOT NULL, default false |
| priority_order | Integer | default 0 |
| firing_round | Integer | NOT NULL, default 1 |
| two_stage_firing | Boolean | NOT NULL, default false |
| two_stage_type | String(20) | nullable ('gold','countertop') |
| application_collection_code | String(30) | nullable |
| application_method_code | String(20) | nullable |
| planned_glazing_date | Date | nullable |
| planned_kiln_date | Date | nullable |
| planned_sorting_date | Date | nullable |
| planned_completion_date | Date | nullable |
| estimated_kiln_id | UUID | FK resources.id, nullable |
| schedule_version | Integer | NOT NULL, default 1 |
| position_number | Integer | nullable |
| split_index | Integer | nullable |
| created_at | DateTime(tz) | NOT NULL |
| updated_at | DateTime(tz) | NOT NULL |

### `production_order_change_requests`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| order_id | UUID | FK production_orders.id CASCADE, NOT NULL |
| change_type | String(50) | NOT NULL, default 'modification' |
| diff_json | JSONB | NOT NULL |
| status | Enum(ChangeRequestStatus) | NOT NULL, default PENDING |
| reviewed_by | UUID | FK users.id, nullable |
| notes | Text | nullable |
| created_at | DateTime(tz) | NOT NULL |
| reviewed_at | DateTime(tz) | nullable |

### `production_order_status_logs`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| order_id | UUID | FK production_orders.id CASCADE, NOT NULL |
| old_status | Enum(OrderStatus) | nullable |
| new_status | Enum(OrderStatus) | NOT NULL |
| changed_by | UUID | FK users.id, nullable |
| is_override | Boolean | NOT NULL, default false |
| notes | Text | nullable |
| created_at | DateTime(tz) | NOT NULL |

### `sales_webhook_events`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| event_id | String(255) | UNIQUE, NOT NULL |
| payload_json | JSONB | NOT NULL |
| processed | Boolean | NOT NULL, default false |
| error_message | Text | nullable |
| created_at | DateTime(tz) | NOT NULL |

### `tasks`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| factory_id | UUID | FK factories.id, NOT NULL |
| type | Enum(TaskType) | NOT NULL |
| status | Enum(TaskStatus) | NOT NULL, default PENDING |
| assigned_to | UUID | FK users.id, nullable |
| assigned_role | Enum(UserRole) | nullable |
| related_order_id | UUID | FK production_orders.id, nullable |
| related_position_id | UUID | FK order_positions.id, nullable |
| blocking | Boolean | NOT NULL, default false |
| description | Text | nullable |
| priority | Integer | NOT NULL, default 0 |
| due_at | DateTime(tz) | nullable |
| created_at | DateTime(tz) | NOT NULL |
| completed_at | DateTime(tz) | nullable |
| updated_at | DateTime(tz) | NOT NULL |
| metadata_json | JSONB | nullable |

### `order_stage_history`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| order_id | UUID | FK production_orders.id CASCADE, NOT NULL |
| stage_id | UUID | FK production_stages.id, NOT NULL |
| entered_at | DateTime(tz) | NOT NULL |
| exited_at | DateTime(tz) | nullable |

---

## 4. Materials & Recipes

### `materials`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| material_code | String(20) | UNIQUE, nullable (auto: "M-0001") |
| name | String(300) | UNIQUE, NOT NULL |
| unit | String(20) | NOT NULL, default 'pcs' |
| material_type | String(50) | NOT NULL |
| product_subtype | String(30) | nullable (tiles/sinks/table_top/custom) |
| subgroup_id | UUID | FK material_subgroups.id, nullable |
| supplier_id | UUID | FK suppliers.id, nullable |
| size_id | UUID | FK sizes.id, nullable |
| created_at | DateTime(tz) | NOT NULL |
| updated_at | DateTime(tz) | NOT NULL |

### `material_stock`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| material_id | UUID | FK materials.id CASCADE, NOT NULL |
| factory_id | UUID | FK factories.id, NOT NULL |
| balance | Numeric(12,3) | NOT NULL, default 0 |
| min_balance | Numeric(12,3) | NOT NULL, default 0 |
| min_balance_recommended | Numeric(12,3) | nullable |
| min_balance_auto | Boolean | NOT NULL, default true |
| avg_daily_consumption | Numeric(12,3) | default 0 |
| avg_monthly_consumption | Numeric(12,3) | default 0 |
| warehouse_section | String(50) | default 'raw_materials' |
| created_at | DateTime(tz) | NOT NULL |
| updated_at | DateTime(tz) | NOT NULL |

**Unique:** (material_id, factory_id)

### `material_transactions`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| material_id | UUID | FK materials.id, NOT NULL |
| factory_id | UUID | FK factories.id, nullable |
| type | Enum(TransactionType) | NOT NULL |
| quantity | Numeric(12,3) | NOT NULL |
| related_order_id | UUID | FK production_orders.id, nullable |
| related_position_id | UUID | FK order_positions.id, nullable |
| reason | Enum(WriteOffReason) | nullable |
| notes | Text | nullable |
| created_by | UUID | FK users.id, nullable |
| created_at | DateTime(tz) | NOT NULL |
| defect_percent | Numeric(5,2) | nullable |
| quality_notes | Text | nullable |
| approval_status | String(20) | nullable ('pending','approved','rejected','partial') |
| approved_by | UUID | FK users.id, nullable |
| approved_at | DateTime(tz) | nullable |
| accepted_quantity | Numeric(12,3) | nullable |

### `material_purchase_requests`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| factory_id | UUID | FK factories.id, NOT NULL |
| supplier_id | UUID | FK suppliers.id, nullable |
| materials_json | JSONB | NOT NULL |
| status | Enum(PurchaseStatus) | NOT NULL, default PENDING |
| source | String(20) | NOT NULL, default 'auto' |
| approved_by | UUID | FK users.id, nullable |
| sent_to_chat_at | DateTime(tz) | nullable |
| ordered_at | Date | nullable |
| expected_delivery_date | Date | nullable |
| actual_delivery_date | Date | nullable |
| received_quantity_json | JSONB | nullable |
| notes | Text | nullable |
| created_at | DateTime(tz) | NOT NULL |
| updated_at | DateTime(tz) | NOT NULL |

### `material_groups`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| name | String(200) | UNIQUE, NOT NULL |
| code | String(50) | UNIQUE, NOT NULL |
| description | Text | nullable |
| icon | String(10) | nullable |
| display_order | Integer | NOT NULL, default 0 |
| is_active | Boolean | NOT NULL, default true |
| created_at | DateTime(tz) | NOT NULL |
| updated_at | DateTime(tz) | NOT NULL |

### `material_subgroups`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| group_id | UUID | FK material_groups.id CASCADE, NOT NULL |
| name | String(200) | NOT NULL |
| code | String(50) | UNIQUE, NOT NULL |
| description | Text | nullable |
| icon | String(10) | nullable |
| default_lead_time_days | Integer | nullable |
| default_unit | String(20) | default 'kg' |
| display_order | Integer | NOT NULL, default 0 |
| is_active | Boolean | NOT NULL, default true |
| created_at | DateTime(tz) | NOT NULL |
| updated_at | DateTime(tz) | NOT NULL |

**Unique:** (group_id, name)

### `material_defect_thresholds`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| material_id | UUID | FK materials.id, UNIQUE, NOT NULL |
| max_defect_percent | Numeric(5,2) | NOT NULL, default 3.0 |
| updated_by | UUID | FK users.id, nullable |
| updated_at | DateTime(tz) | auto |

### `recipes`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| name | String(300) | NOT NULL |
| color_collection | String(100) | nullable |
| description | Text | nullable |
| recipe_type | String(20) | NOT NULL, default 'product' ('product','glaze','engobe') |
| color_type | String(20) | nullable ('base','custom') |
| specific_gravity | Numeric(5,3) | nullable |
| consumption_spray_ml_per_sqm | Numeric(8,2) | nullable |
| consumption_brush_ml_per_sqm | Numeric(8,2) | nullable |
| is_default | Boolean | NOT NULL, default false |
| client_name | String(200) | nullable |
| glaze_settings | JSONB | NOT NULL, default {} |
| is_active | Boolean | NOT NULL, default true |
| created_at | DateTime(tz) | NOT NULL |
| updated_at | DateTime(tz) | NOT NULL |

**Unique:** (color_collection, name)

### `recipe_materials`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| recipe_id | UUID | FK recipes.id CASCADE, NOT NULL |
| material_id | UUID | FK materials.id, NOT NULL |
| quantity_per_unit | Numeric(10,4) | NOT NULL |
| unit | String(20) | NOT NULL, default 'per_piece' |
| notes | Text | nullable |
| spray_rate | Numeric(10,4) | nullable |
| brush_rate | Numeric(10,4) | nullable |
| splash_rate | Numeric(10,4) | nullable |
| silk_screen_rate | Numeric(10,4) | nullable |

**Unique:** (recipe_id, material_id)

### `recipe_kiln_config`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| recipe_id | UUID | FK recipes.id CASCADE, UNIQUE, NOT NULL |
| firing_temperature | Integer | nullable |
| firing_duration_hours | Numeric(5,1) | nullable |
| two_stage_firing | Boolean | NOT NULL, default false |
| special_instructions | Text | nullable |
| created_at | DateTime(tz) | NOT NULL |
| updated_at | DateTime(tz) | NOT NULL |

### `recipe_firing_stages`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| recipe_id | UUID | FK recipes.id CASCADE, NOT NULL |
| stage_number | Integer | NOT NULL, default 1 |
| firing_profile_id | UUID | FK firing_profiles.id, nullable |
| requires_glazing_before | Boolean | NOT NULL, default true |
| description | String(200) | nullable |
| created_at | DateTime(tz) | NOT NULL |

**Unique:** (recipe_id, stage_number)

### `consumption_rules`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| rule_number | Integer | NOT NULL |
| name | String(200) | NOT NULL |
| description | Text | nullable |
| collection | String(100) | nullable (match criterion) |
| color_collection | String(100) | nullable |
| product_type | String(30) | nullable |
| size_id | UUID | FK sizes.id, nullable |
| shape | String(20) | nullable |
| thickness_mm_min | Numeric(5,1) | nullable |
| thickness_mm_max | Numeric(5,1) | nullable |
| place_of_application | String(50) | nullable |
| recipe_type | String(20) | nullable |
| application_method | String(20) | nullable |
| consumption_ml_per_sqm | Numeric(10,2) | nullable |
| coats | Integer | NOT NULL, default 1 |
| specific_gravity_override | Numeric(5,3) | nullable |
| priority | Integer | NOT NULL, default 0 |
| is_active | Boolean | NOT NULL, default true |
| notes | Text | nullable |
| created_at | DateTime(tz) | NOT NULL |
| updated_at | DateTime(tz) | NOT NULL |

---

## 5. Kilns & Batches

### `resources` (Kilns / Stations)

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| name | String(200) | NOT NULL |
| resource_type | Enum(ResourceType) | NOT NULL (kiln, glazing_station, sorting_station) |
| factory_id | UUID | FK factories.id, NOT NULL |
| capacity_sqm | Numeric(10,3) | nullable |
| capacity_pcs | Integer | nullable |
| num_levels | Integer | default 1 |
| status | Enum(ResourceStatus) | NOT NULL, default ACTIVE |
| kiln_dimensions_cm | JSONB | nullable |
| kiln_working_area_cm | JSONB | nullable |
| kiln_multi_level | Boolean | default false |
| kiln_coefficient | Numeric(4,2) | nullable |
| kiln_type | String(20) | nullable |
| thermocouple | String(50) | nullable |
| control_cable | String(50) | nullable |
| control_device | String(50) | nullable |
| is_active | Boolean | NOT NULL, default true |
| created_at | DateTime(tz) | NOT NULL |
| updated_at | DateTime(tz) | NOT NULL |

### `batches`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| resource_id | UUID | FK resources.id, NOT NULL |
| factory_id | UUID | FK factories.id, NOT NULL |
| batch_date | Date | NOT NULL |
| status | Enum(BatchStatus) | NOT NULL, default PLANNED |
| created_by | Enum(BatchCreator) | NOT NULL, default AUTO |
| notes | Text | nullable |
| metadata_json | JSONB | nullable |
| created_at | DateTime(tz) | NOT NULL |
| updated_at | DateTime(tz) | NOT NULL |
| firing_profile_id | UUID | FK firing_profiles.id, nullable |
| target_temperature | Integer | nullable |

### `schedule_slots`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| resource_id | UUID | FK resources.id, NOT NULL |
| start_at | DateTime(tz) | NOT NULL |
| end_at | DateTime(tz) | NOT NULL |
| batch_id | UUID | FK batches.id, nullable |
| status | Enum(ScheduleSlotStatus) | NOT NULL, default PLANNED |
| created_at | DateTime(tz) | NOT NULL |

### `kiln_constants`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| constant_name | String(100) | UNIQUE, NOT NULL |
| value | Numeric(12,4) | NOT NULL |
| unit | String(50) | nullable |
| description | Text | nullable |
| updated_at | DateTime(tz) | NOT NULL |
| updated_by | UUID | FK users.id, nullable |

### `kiln_loading_rules`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| kiln_id | UUID | FK resources.id CASCADE, UNIQUE, NOT NULL |
| rules | JSONB | NOT NULL |
| created_at | DateTime(tz) | NOT NULL |
| updated_at | DateTime(tz) | NOT NULL |

### `kiln_firing_schedules`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| kiln_id | UUID | FK resources.id, NOT NULL |
| name | String(200) | NOT NULL |
| schedule_data | JSONB | NOT NULL |
| is_default | Boolean | NOT NULL, default false |
| created_at | DateTime(tz) | NOT NULL |
| updated_at | DateTime(tz) | NOT NULL |

### `kiln_actual_loads`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| kiln_id | UUID | FK resources.id, NOT NULL |
| batch_id | UUID | FK batches.id, NOT NULL |
| actual_pieces | Integer | NOT NULL |
| actual_area_sqm | Numeric(10,3) | nullable |
| calculated_capacity | Integer | NOT NULL |
| loading_type | String(20) | NOT NULL |
| created_at | DateTime(tz) | NOT NULL |

### `kiln_calculation_logs`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| calculation_type | String(100) | NOT NULL |
| batch_id | UUID | FK batches.id, nullable |
| resource_id | UUID | FK resources.id, nullable |
| input_json | JSONB | NOT NULL |
| output_json | JSONB | NOT NULL |
| duration_ms | Integer | nullable |
| created_at | DateTime(tz) | NOT NULL |

### `firing_profiles`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| name | String(200) | NOT NULL |
| temperature_group_id | UUID | FK firing_temperature_groups.id SET NULL, nullable |
| product_type | Enum(ProductType) | nullable |
| collection | String(100) | nullable |
| thickness_min_mm | Numeric(5,1) | nullable |
| thickness_max_mm | Numeric(5,1) | nullable |
| target_temperature | Integer | NOT NULL |
| total_duration_hours | Numeric(5,1) | NOT NULL |
| stages | JSONB | NOT NULL, default [] |
| match_priority | Integer | NOT NULL, default 0 |
| is_default | Boolean | NOT NULL, default false |
| is_active | Boolean | NOT NULL, default true |
| created_at | DateTime(tz) | NOT NULL |
| updated_at | DateTime(tz) | NOT NULL |

### `firing_temperature_groups`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| name | String(100) | NOT NULL |
| temperature | Integer | NOT NULL |
| min_temperature | Integer | nullable (DEPRECATED) |
| max_temperature | Integer | nullable (DEPRECATED) |
| description | Text | nullable |
| thermocouple | String(50) | nullable (DEPRECATED) |
| control_cable | String(50) | nullable (DEPRECATED) |
| control_device | String(50) | nullable (DEPRECATED) |
| is_active | Boolean | NOT NULL, default true |
| display_order | Integer | NOT NULL, default 0 |
| created_at | DateTime(tz) | NOT NULL |
| updated_at | DateTime(tz) | NOT NULL |

### `firing_temperature_group_recipes`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| temperature_group_id | UUID | FK firing_temperature_groups.id CASCADE, NOT NULL |
| recipe_id | UUID | FK recipes.id CASCADE, NOT NULL |
| is_default | Boolean | NOT NULL, default false |

**Unique:** (temperature_group_id, recipe_id)

### `firing_logs`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| batch_id | UUID | FK batches.id CASCADE, NOT NULL |
| kiln_id | UUID | FK resources.id, NOT NULL |
| started_at | DateTime(tz) | nullable |
| ended_at | DateTime(tz) | nullable |
| peak_temperature | Numeric(6,1) | nullable |
| target_temperature | Numeric(6,1) | nullable |
| temperature_readings | JSONB | nullable |
| firing_profile_id | UUID | FK firing_profiles.id, nullable |
| result | String(30) | nullable ('success','partial_failure','abort') |
| notes | Text | nullable |
| recorded_by | UUID | FK users.id, nullable |
| created_at | DateTime(tz) | NOT NULL |

### `kiln_rotation_rules`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| factory_id | UUID | FK factories.id, NOT NULL |
| kiln_id | UUID | FK resources.id, nullable (null = factory-wide) |
| rule_name | String(100) | NOT NULL |
| glaze_sequence | JSONB | NOT NULL |
| cooldown_minutes | Integer | default 0 |
| incompatible_pairs | JSONB | default [] |
| is_active | Boolean | default true |
| created_at | DateTime(tz) | NOT NULL |
| updated_at | DateTime(tz) | NOT NULL |

**Unique:** (factory_id, kiln_id, rule_name)

---

## 6. Quality & Inspections

### `quality_checks`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| position_id | UUID | FK order_positions.id, NOT NULL |
| factory_id | UUID | FK factories.id, NOT NULL |
| operation_type | String(100) | nullable |
| stage | Enum(QcStage) | NOT NULL |
| result | Enum(QcResult) | NOT NULL |
| defect_cause_id | UUID | FK defect_causes.id, nullable |
| photos | ARRAY(Text) | nullable |
| notes | Text | nullable |
| checked_by | UUID | FK users.id, nullable |
| created_at | DateTime(tz) | NOT NULL |

### `quality_assignment_config`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| factory_id | UUID | FK factories.id, NOT NULL |
| stage | Enum(QcStage) | NOT NULL |
| base_percentage | Numeric(5,2) | NOT NULL, default 2.0 |
| increase_on_defect_percentage | Numeric(5,2) | NOT NULL, default 2.0 |
| current_percentage | Numeric(5,2) | NOT NULL, default 2.0 |
| updated_at | DateTime(tz) | NOT NULL |

**Unique:** (factory_id, stage)

### `quality_checklists`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| position_id | UUID | FK order_positions.id, NOT NULL |
| factory_id | UUID | FK factories.id, NOT NULL |
| check_type | String(30) | NOT NULL ('pre_kiln', 'final') |
| checklist_results | JSONB | NOT NULL |
| overall_result | String(20) | NOT NULL ('pass','fail','needs_rework') |
| checked_by | UUID | FK users.id, nullable |
| notes | Text | nullable |
| created_at | DateTime(tz) | NOT NULL |

### `kiln_inspection_items` (Template)

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| category | String(100) | NOT NULL |
| item_text | String(500) | NOT NULL |
| sort_order | Integer | NOT NULL, default 0 |
| is_active | Boolean | NOT NULL, default true |
| applies_to_kiln_types | JSONB | nullable (null = all) |

### `kiln_inspections`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| resource_id | UUID | FK resources.id, NOT NULL |
| factory_id | UUID | FK factories.id, NOT NULL |
| inspection_date | Date | NOT NULL |
| inspected_by_id | UUID | FK users.id, NOT NULL |
| notes | Text | nullable |
| created_at | DateTime(tz) | NOT NULL |

**Unique:** (resource_id, inspection_date)

### `kiln_inspection_results`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| inspection_id | UUID | FK kiln_inspections.id CASCADE, NOT NULL |
| item_id | UUID | FK kiln_inspection_items.id, NOT NULL |
| result | String(20) | NOT NULL ('ok','not_applicable','damaged','needs_repair') |
| notes | Text | nullable |

### `kiln_repair_logs`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| resource_id | UUID | FK resources.id, NOT NULL |
| factory_id | UUID | FK factories.id, NOT NULL |
| date_reported | Date | NOT NULL |
| reported_by_id | UUID | FK users.id, NOT NULL |
| issue_description | Text | NOT NULL |
| diagnosis | Text | nullable |
| repair_actions | Text | nullable |
| spare_parts_used | Text | nullable |
| technician | String(200) | nullable |
| date_completed | Date | nullable |
| status | String(30) | NOT NULL, default 'open' |
| notes | Text | nullable |
| inspection_result_id | UUID | FK kiln_inspection_results.id, nullable |
| created_at | DateTime(tz) | NOT NULL |
| updated_at | DateTime(tz) | NOT NULL |

### `qm_blocks`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| factory_id | UUID | FK factories.id, NOT NULL |
| block_type | Enum(QmBlockType) | NOT NULL |
| position_id | UUID | FK order_positions.id, nullable |
| batch_id | UUID | FK batches.id, nullable |
| reason | Text | NOT NULL |
| severity | String(20) | NOT NULL, default 'critical' |
| photo_urls | JSONB | default [] |
| blocked_by | UUID | FK users.id, NOT NULL |
| resolved_by | UUID | FK users.id, nullable |
| resolved_at | DateTime(tz) | nullable |
| resolution_note | Text | nullable |
| created_at | DateTime(tz) | NOT NULL |

---

## 7. Defects & Repairs

### `defect_causes`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| code | String(50) | UNIQUE, NOT NULL |
| category | String(100) | NOT NULL |
| description | Text | nullable |
| is_active | Boolean | NOT NULL, default true |
| created_at | DateTime(tz) | NOT NULL |

### `defect_records`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| factory_id | UUID | FK factories.id, NOT NULL |
| stage | Enum(DefectStage) | NOT NULL |
| position_id | UUID | FK order_positions.id, nullable |
| batch_id | UUID | FK batches.id, nullable |
| supplier_id | UUID | FK suppliers.id, nullable |
| defect_type | String(200) | NOT NULL |
| quantity | Integer | NOT NULL |
| outcome | Enum(DefectOutcome) | NOT NULL |
| reported_by | UUID | FK users.id, nullable |
| reported_via | String(20) | NOT NULL, default 'dashboard' |
| photos | ARRAY(Text) | nullable |
| notes | Text | nullable |
| date | Date | NOT NULL |
| created_at | DateTime(tz) | NOT NULL |

### `production_defects`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| factory_id | UUID | FK factories.id, NOT NULL |
| position_id | UUID | FK order_positions.id, nullable |
| glaze_type | String(50) | nullable |
| product_type | String(50) | nullable |
| total_quantity | Integer | NOT NULL |
| defect_quantity | Integer | NOT NULL |
| defect_pct | Numeric(5,4) | nullable |
| fired_at | Date | NOT NULL |
| created_at | DateTime(tz) | NOT NULL |

### `stone_defect_coefficients`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| factory_id | UUID | FK factories.id, NOT NULL |
| stone_type | String(100) | NOT NULL |
| supplier_id | UUID | FK suppliers.id, nullable |
| coefficient | Numeric(4,3) | NOT NULL, default 0.000 |
| sample_size | Integer | NOT NULL, default 0 |
| last_updated | DateTime(tz) | nullable |
| calculation_period_days | Integer | NOT NULL, default 30 |

**Unique:** (factory_id, stone_type, supplier_id)

### `stone_defect_rates`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| factory_id | UUID | FK factories.id, nullable |
| size_category | String(20) | NOT NULL |
| product_type | String(50) | NOT NULL |
| defect_pct | Numeric(5,4) | NOT NULL |
| updated_at | DateTime(tz) | NOT NULL |
| updated_by | UUID | FK users.id, nullable |

**Unique:** (factory_id, size_category, product_type)

### `grinding_stock`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| factory_id | UUID | FK factories.id, NOT NULL |
| color | String(100) | NOT NULL |
| size | String(50) | NOT NULL |
| quantity | Integer | NOT NULL |
| source_order_id | UUID | FK production_orders.id, nullable |
| source_position_id | UUID | FK order_positions.id, nullable |
| status | Enum(GrindingStatus) | NOT NULL, default IN_STOCK |
| decided_by | UUID | FK users.id, nullable |
| decided_at | DateTime(tz) | nullable |
| notes | Text | nullable |
| created_at | DateTime(tz) | NOT NULL |
| updated_at | DateTime(tz) | NOT NULL |

### `repair_queue`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| factory_id | UUID | FK factories.id, NOT NULL |
| color | String(100) | NOT NULL |
| size | String(50) | NOT NULL |
| quantity | Integer | NOT NULL |
| defect_type | String(200) | nullable |
| source_order_id | UUID | FK production_orders.id, nullable |
| source_position_id | UUID | FK order_positions.id, nullable |
| status | Enum(RepairStatus) | NOT NULL, default IN_REPAIR |
| created_at | DateTime(tz) | NOT NULL |
| repaired_at | DateTime(tz) | nullable |
| updated_at | DateTime(tz) | NOT NULL |

### `supplier_defect_reports`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| supplier_id | UUID | FK suppliers.id, NOT NULL |
| factory_id | UUID | FK factories.id, NOT NULL |
| period_start | Date | NOT NULL |
| period_end | Date | NOT NULL |
| total_inspected | Integer | NOT NULL, default 0 |
| total_defective | Integer | NOT NULL, default 0 |
| defect_percentage | Numeric(5,2) | NOT NULL, default 0 |
| report_file_url | Text | nullable |
| sent_at | DateTime(tz) | nullable |
| created_at | DateTime(tz) | NOT NULL |

---

## 8. Warehouse & Inventory

### `warehouse_sections`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| factory_id | UUID | FK factories.id, nullable |
| code | String(50) | NOT NULL |
| name | String(200) | NOT NULL |
| description | Text | nullable |
| managed_by | UUID | FK users.id, nullable |
| warehouse_type | String(50) | NOT NULL, default 'section' |
| display_order | Integer | NOT NULL, default 0 |
| is_default | Boolean | NOT NULL, default false |
| is_active | Boolean | NOT NULL, default true |
| created_at | DateTime(tz) | NOT NULL |
| updated_at | DateTime(tz) | auto |

**Unique:** (factory_id, code)

### `inventory_reconciliations`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| factory_id | UUID | FK factories.id, NOT NULL |
| section_id | UUID | FK warehouse_sections.id, nullable |
| status | Enum(ReconciliationStatus) | NOT NULL, default IN_PROGRESS |
| started_by | UUID | FK users.id, NOT NULL |
| completed_at | DateTime(tz) | nullable |
| notes | Text | nullable |
| staff_count | Integer | nullable |
| scheduled_date | Date | nullable |
| approved_by | UUID | FK users.id, nullable |
| approved_at | DateTime(tz) | nullable |
| created_at | DateTime(tz) | NOT NULL |

### `inventory_reconciliation_items`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| reconciliation_id | UUID | FK inventory_reconciliations.id CASCADE, NOT NULL |
| material_id | UUID | FK materials.id, NOT NULL |
| system_quantity | Numeric(12,3) | NOT NULL |
| actual_quantity | Numeric(12,3) | NOT NULL |
| difference | Numeric(12,3) | NOT NULL |
| adjustment_applied | Boolean | NOT NULL, default false |
| reason | String(50) | nullable |
| explanation | Text | nullable |
| explained_by | UUID | FK users.id, nullable |
| explained_at | DateTime(tz) | nullable |

### `finished_goods_stock`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| factory_id | UUID | FK factories.id, NOT NULL |
| color | String(100) | NOT NULL |
| size | String(50) | NOT NULL |
| collection | String(100) | nullable |
| product_type | Enum(ProductType) | default TILE |
| quantity | Integer | NOT NULL, default 0 |
| reserved_quantity | Integer | NOT NULL, default 0 |
| updated_at | DateTime(tz) | auto |

**Unique:** (factory_id, color, size, collection, product_type)

### `stage_reconciliation_logs`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| factory_id | UUID | FK factories.id, NOT NULL |
| batch_id | UUID | FK batches.id, nullable |
| stage_from | String(50) | NOT NULL |
| stage_to | String(50) | NOT NULL |
| input_count | Integer | NOT NULL |
| output_good | Integer | NOT NULL, default 0 |
| output_defect | Integer | NOT NULL, default 0 |
| output_write_off | Integer | NOT NULL, default 0 |
| discrepancy | Integer | NOT NULL, default 0 |
| is_balanced | Boolean | NOT NULL, default true |
| checked_at | DateTime(tz) | NOT NULL |
| alert_sent | Boolean | NOT NULL, default false |

### `stone_reservations`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| position_id | UUID | FK order_positions.id CASCADE, NOT NULL |
| factory_id | UUID | FK factories.id, NOT NULL |
| size_category | String(20) | NOT NULL |
| product_type | String(50) | NOT NULL |
| reserved_qty | Integer | NOT NULL |
| reserved_sqm | Numeric(10,3) | NOT NULL |
| stone_defect_pct | Numeric(5,4) | NOT NULL |
| status | String(20) | NOT NULL, default 'active' |
| created_at | DateTime(tz) | NOT NULL |
| reconciled_at | DateTime(tz) | nullable |

### `stone_reservation_adjustments`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| reservation_id | UUID | FK stone_reservations.id CASCADE, NOT NULL |
| type | String(20) | NOT NULL |
| qty_sqm | Numeric(10,3) | NOT NULL |
| reason | Text | nullable |
| created_at | DateTime(tz) | NOT NULL |
| created_by | UUID | FK users.id, nullable |

---

## 9. Packaging

### `packaging_box_types`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| material_id | UUID | FK materials.id CASCADE, NOT NULL |
| name | String(200) | NOT NULL |
| notes | Text | nullable |
| is_active | Boolean | NOT NULL, default true |
| created_at | DateTime(tz) | NOT NULL |
| updated_at | DateTime(tz) | NOT NULL |

### `packaging_box_capacities`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| box_type_id | UUID | FK packaging_box_types.id CASCADE, NOT NULL |
| size_id | UUID | FK sizes.id CASCADE, NOT NULL |
| pieces_per_box | Integer | nullable |
| sqm_per_box | Numeric(10,4) | nullable |

**Unique:** (box_type_id, size_id)

### `packaging_spacer_rules`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| box_type_id | UUID | FK packaging_box_types.id CASCADE, NOT NULL |
| size_id | UUID | FK sizes.id CASCADE, NOT NULL |
| spacer_material_id | UUID | FK materials.id CASCADE, NOT NULL |
| qty_per_box | Integer | NOT NULL, default 1 |

**Unique:** (box_type_id, size_id, spacer_material_id)

---

## 10. Shipments & Delivery

### `shipments`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| order_id | UUID | FK production_orders.id, NOT NULL |
| factory_id | UUID | FK factories.id, NOT NULL |
| tracking_number | String(100) | nullable |
| carrier | String(100) | nullable |
| shipping_method | String(50) | nullable |
| total_pieces | Integer | NOT NULL, default 0 |
| total_boxes | Integer | nullable |
| total_weight_kg | Numeric(10,2) | nullable |
| status | String(30) | NOT NULL, default 'prepared' |
| shipped_at | DateTime(tz) | nullable |
| estimated_delivery | Date | nullable |
| delivered_at | DateTime(tz) | nullable |
| shipped_by | UUID | FK users.id, nullable |
| received_by | String(200) | nullable |
| delivery_note_url | String(500) | nullable |
| notes | Text | nullable |
| created_at | DateTime(tz) | NOT NULL |

### `shipment_items`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| shipment_id | UUID | FK shipments.id CASCADE, NOT NULL |
| position_id | UUID | FK order_positions.id, NOT NULL |
| quantity_shipped | Integer | NOT NULL |
| box_number | Integer | nullable |
| notes | Text | nullable |

### `mana_shipments`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| factory_id | UUID | FK factories.id, NOT NULL |
| items_json | JSONB | NOT NULL |
| status | Enum(ManaShipmentStatus) | NOT NULL, default PENDING |
| confirmed_by | UUID | FK users.id, nullable |
| confirmed_at | DateTime(tz) | nullable |
| shipped_at | DateTime(tz) | nullable |
| notes | Text | nullable |
| created_at | DateTime(tz) | NOT NULL |

### `surplus_dispositions`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| factory_id | UUID | FK factories.id, NOT NULL |
| order_id | UUID | FK production_orders.id, NOT NULL |
| position_id | UUID | FK order_positions.id, NOT NULL |
| surplus_quantity | Integer | NOT NULL |
| disposition_type | Enum(SurplusDispositionType) | NOT NULL |
| size | String(50) | NOT NULL |
| color | String(100) | NOT NULL |
| is_base_color | Boolean | NOT NULL, default false |
| task_id | UUID | FK tasks.id, nullable |
| created_at | DateTime(tz) | NOT NULL |

---

## 11. HR & Payroll

### `employees`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| factory_id | UUID | FK factories.id, NOT NULL |
| full_name | String(200) | NOT NULL |
| short_name | String(50) | nullable |
| position | String(100) | NOT NULL |
| phone | String(50) | nullable |
| email | String(255) | nullable |
| birth_date | Date | nullable |
| has_own_bpjs | Boolean | NOT NULL, default false |
| hire_date | Date | nullable |
| is_active | Boolean | NOT NULL, default true |
| employment_type | String(50) | NOT NULL, default 'full_time' |
| department | String(50) | NOT NULL, default 'production' |
| work_schedule | String(20) | NOT NULL, default 'six_day' |
| bpjs_mode | String(20) | NOT NULL, default 'company_pays' |
| employment_category | String(20) | NOT NULL, default 'formal' |
| commission_rate | Numeric(5,2) | nullable |
| base_salary | Numeric(12,2) | NOT NULL, default 0 |
| allowance_bike | Numeric(10,2) | NOT NULL, default 0 |
| allowance_housing | Numeric(10,2) | NOT NULL, default 0 |
| allowance_food | Numeric(10,2) | NOT NULL, default 0 |
| allowance_bpjs | Numeric(10,2) | NOT NULL, default 0 |
| allowance_other | Numeric(10,2) | NOT NULL, default 0 |
| allowance_other_note | String(200) | nullable |
| created_at | DateTime(tz) | NOT NULL |
| updated_at | DateTime(tz) | NOT NULL, auto-update |

### `attendance`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| employee_id | UUID | FK employees.id, NOT NULL |
| date | Date | NOT NULL |
| status | String(20) | NOT NULL ('present','absent','sick','leave','half_day') |
| overtime_hours | Numeric(4,1) | NOT NULL, default 0 |
| notes | Text | nullable |
| recorded_by | UUID | FK users.id, nullable |
| created_at | DateTime(tz) | NOT NULL |

**Unique:** (employee_id, date)

---

## 12. TPS & Production Metrics

### `tps_parameters`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| factory_id | UUID | FK factories.id, NOT NULL |
| stage | String(100) | NOT NULL |
| metric_name | String(200) | NOT NULL |
| target_value | Numeric(12,3) | NOT NULL |
| tolerance_percent | Numeric(5,2) | NOT NULL, default 10.0 |
| unit | String(50) | nullable |
| created_at | DateTime(tz) | NOT NULL |

**Unique:** (factory_id, stage, metric_name)

### `tps_shift_metrics`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| factory_id | UUID | FK factories.id, NOT NULL |
| shift | Integer | NOT NULL |
| date | Date | NOT NULL |
| stage | String(100) | NOT NULL |
| planned_output | Numeric(12,3) | NOT NULL |
| actual_output | Numeric(12,3) | NOT NULL |
| actual_output_pcs | Integer | NOT NULL, default 0 |
| deviation_percent | Numeric(8,2) | NOT NULL, default 0 |
| defect_rate | Numeric(5,2) | default 0 |
| downtime_minutes | Numeric(8,1) | default 0 |
| cycle_time_minutes | Numeric(8,2) | default 0 |
| oee_percent | Numeric(5,2) | default 0 |
| takt_time_minutes | Numeric(8,2) | default 0 |
| status | Enum(TpsStatus) | NOT NULL, default NORMAL |
| notes | Text | nullable |
| created_at | DateTime(tz) | NOT NULL |

**Unique:** (factory_id, shift, date, stage)

### `tps_deviations`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| factory_id | UUID | FK factories.id, NOT NULL |
| shift | Integer | NOT NULL |
| stage | String(100) | NOT NULL |
| deviation_type | Enum(TpsDeviationType) | NOT NULL |
| description | Text | NOT NULL |
| severity | String(20) | NOT NULL, default 'low' |
| resolved | Boolean | NOT NULL, default false |
| created_at | DateTime(tz) | NOT NULL |

### `process_steps`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| name | String(200) | NOT NULL |
| factory_id | UUID | FK factories.id, NOT NULL |
| norm_time_minutes | Numeric(8,2) | NOT NULL |
| sequence | Integer | NOT NULL |
| productivity_rate | Numeric(10,2) | nullable |
| productivity_unit | String(50) | nullable |
| measurement_basis | String(50) | nullable |
| is_active | Boolean | NOT NULL, default true |
| notes | Text | nullable |

**Unique:** (factory_id, sequence)

### `standard_work`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| process_step_id | UUID | FK process_steps.id CASCADE, NOT NULL |
| description | Text | NOT NULL |
| time_minutes | Numeric(8,2) | NOT NULL |
| is_setup | Boolean | NOT NULL, default false |
| created_at | DateTime(tz) | NOT NULL |

### `operation_logs`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| factory_id | UUID | FK factories.id, NOT NULL |
| operation_id | UUID | FK operations.id, NOT NULL |
| user_id | UUID | FK users.id, NOT NULL |
| position_id | UUID | FK order_positions.id, nullable |
| batch_id | UUID | FK batches.id, nullable |
| shift_date | Date | NOT NULL |
| shift_number | Integer | nullable |
| started_at | DateTime(tz) | nullable |
| completed_at | DateTime(tz) | nullable |
| duration_minutes | Numeric(8,2) | nullable |
| quantity_processed | Integer | nullable |
| defect_count | Integer | default 0 |
| notes | Text | nullable |
| source | String(20) | default 'telegram' |
| created_at | DateTime(tz) | auto |

---

## 13. Notifications & Audit

### `notifications`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| user_id | UUID | FK users.id, NOT NULL |
| factory_id | UUID | FK factories.id, nullable |
| type | Enum(NotificationType) | NOT NULL |
| title | String(500) | NOT NULL |
| message | Text | nullable |
| related_entity_type | Enum(RelatedEntityType) | nullable |
| related_entity_id | UUID | nullable |
| is_read | Boolean | NOT NULL, default false |
| created_at | DateTime(tz) | NOT NULL |

### `audit_logs`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| action | String(20) | NOT NULL (INSERT, UPDATE, DELETE, DEACTIVATE) |
| table_name | String(100) | NOT NULL |
| record_id | UUID | NOT NULL |
| old_data | JSONB | nullable |
| new_data | JSONB | nullable |
| user_id | UUID | nullable |
| user_email | String(255) | nullable |
| ip_address | String(45) | nullable |
| request_path | String(255) | nullable |
| created_at | DateTime(tz) | NOT NULL |

### `reference_audit_log`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| table_name | String(100) | NOT NULL |
| record_id | UUID | NOT NULL |
| action | Enum(ReferenceAction) | NOT NULL |
| old_values_json | JSONB | nullable |
| new_values_json | JSONB | nullable |
| changed_by | UUID | FK users.id, nullable |
| changed_at | DateTime(tz) | NOT NULL |

### `daily_task_distributions`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| factory_id | UUID | FK factories.id, NOT NULL |
| distribution_date | Date | NOT NULL |
| glazing_tasks_json | JSONB | nullable |
| kiln_loading_json | JSONB | nullable |
| glaze_recipes_json | JSONB | nullable |
| sent_at | DateTime(tz) | nullable |
| sent_to_chat | Boolean | NOT NULL, default false |
| message_id | BigInteger | nullable |

**Unique:** (factory_id, distribution_date)

### `backup_logs`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| started_at | DateTime(tz) | NOT NULL |
| completed_at | DateTime(tz) | nullable |
| status | String(20) | NOT NULL, default 'in_progress' |
| file_size_bytes | BigInteger | nullable |
| s3_key | String(500) | nullable |
| error_message | Text | nullable |
| backup_type | String(20) | NOT NULL, default 'scheduled' |

---

## 14. Security

### `security_audit_log`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| action | Enum(AuditActionType) | NOT NULL |
| actor_id | UUID | FK users.id, nullable |
| actor_email | String(255) | nullable |
| ip_address | INET | NOT NULL |
| user_agent | Text | nullable |
| target_entity | String(100) | nullable |
| target_id | UUID | nullable |
| details | JSONB | nullable |
| factory_id | UUID | FK factories.id, nullable |
| created_at | DateTime(tz) | NOT NULL |

### `ip_allowlist`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| cidr | INET | NOT NULL |
| scope | Enum(IpScope) | NOT NULL |
| description | String(200) | nullable |
| is_active | Boolean | NOT NULL, default true |
| created_by | UUID | FK users.id, NOT NULL |
| created_at | DateTime(tz) | NOT NULL |

### `rate_limit_events`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| ip_address | INET | NOT NULL |
| user_id | UUID | FK users.id, nullable |
| endpoint | String(200) | NOT NULL |
| created_at | DateTime(tz) | NOT NULL |

---

## 15. AI & Media

### `ai_chat_history`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| user_id | UUID | FK users.id, NOT NULL |
| messages_json | JSONB | NOT NULL, default [] |
| context | Text | nullable |
| session_name | String(200) | nullable |
| created_at | DateTime(tz) | NOT NULL |
| updated_at | DateTime(tz) | NOT NULL |

### `rag_embeddings`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| source_table | String(100) | NOT NULL |
| source_id | UUID | NOT NULL |
| content_text | Text | NOT NULL |
| content_tsvector | TSVECTOR | nullable |
| embedding | ARRAY(Float) | nullable |
| metadata_json | JSONB | nullable |
| created_at | DateTime(tz) | NOT NULL |
| updated_at | DateTime(tz) | NOT NULL |

### `worker_media`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| file_id | String(255) | nullable |
| file_url | Text | nullable |
| media_type | Enum(MediaType) | NOT NULL |
| telegram_user_id | BigInteger | nullable |
| related_order_id | UUID | FK production_orders.id, nullable |
| related_position_id | UUID | FK order_positions.id, nullable |
| factory_id | UUID | FK factories.id, nullable |
| notes | Text | nullable |
| created_at | DateTime(tz) | NOT NULL |

### `position_photos`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| position_id | UUID | FK order_positions.id, nullable |
| factory_id | UUID | FK factories.id, NOT NULL |
| telegram_file_id | String(200) | nullable |
| telegram_chat_id | BigInteger | nullable |
| uploaded_by_telegram_id | BigInteger | nullable |
| uploaded_by_user_id | UUID | FK users.id, nullable |
| batch_id | UUID | FK batches.id, nullable |
| photo_type | String(30) | nullable ('glazing','firing','defect','packing','other') |
| photo_url | String(2048) | nullable |
| caption | Text | nullable |
| created_at | DateTime(tz) | NOT NULL |

---

## 16. Reference & Configuration

### `collections`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| name | String(100) | UNIQUE, NOT NULL |
| created_at | DateTime(tz) | NOT NULL |

### `color_collections`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| name | String(100) | UNIQUE, NOT NULL |
| description | String(255) | nullable |
| is_active | Boolean | NOT NULL, default true |
| created_at | DateTime(tz) | NOT NULL |

### `colors`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| name | String(100) | UNIQUE, NOT NULL |
| code | String(20) | nullable |
| is_basic | Boolean | NOT NULL, default false |
| created_at | DateTime(tz) | NOT NULL |

### `application_types`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| name | String(100) | UNIQUE, NOT NULL |
| created_at | DateTime(tz) | NOT NULL |

### `places_of_application`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| code | String(50) | UNIQUE, NOT NULL |
| name | String(100) | NOT NULL |
| created_at | DateTime(tz) | NOT NULL |

### `finishing_types`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| name | String(100) | UNIQUE, NOT NULL |
| created_at | DateTime(tz) | NOT NULL |

### `sizes`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| name | String(50) | UNIQUE, NOT NULL |
| width_mm | Integer | NOT NULL |
| height_mm | Integer | NOT NULL |
| thickness_mm | Integer | nullable |
| shape | String(20) | nullable, default 'rectangle' |
| is_custom | Boolean | NOT NULL, default false |
| created_at | DateTime(tz) | NOT NULL |

### `glazing_board_specs`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| size_id | UUID | FK sizes.id, UNIQUE, NOT NULL |
| board_length_cm | Numeric(6,1) | NOT NULL, default 122.0 |
| board_width_cm | Numeric(6,1) | NOT NULL |
| tiles_per_board | Integer | NOT NULL |
| area_per_board_m2 | Numeric(8,4) | NOT NULL |
| area_per_two_boards_m2 | Numeric(8,4) | nullable |
| tiles_along_length | Integer | NOT NULL |
| tiles_across_width | Integer | NOT NULL |
| tile_orientation_cm | String(30) | nullable |
| is_custom_board | Boolean | NOT NULL, default false |
| notes | Text | nullable |
| calculated_at | DateTime(tz) | NOT NULL |

### `production_stages`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| name | String(100) | UNIQUE, NOT NULL |
| order | Integer | UNIQUE, NOT NULL |

### `suppliers`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| name | String(200) | NOT NULL |
| contact_person | String(200) | nullable |
| phone | String(50) | nullable |
| email | String(255) | nullable |
| address | Text | nullable |
| material_types | ARRAY(String(50)) | nullable |
| default_lead_time_days | Integer | NOT NULL, default 35 |
| rating | Numeric(3,2) | nullable |
| notes | Text | nullable |
| is_active | Boolean | NOT NULL, default true |
| created_at | DateTime(tz) | NOT NULL |

### `supplier_subgroups`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| supplier_id | UUID | FK suppliers.id CASCADE, NOT NULL |
| subgroup_id | UUID | FK material_subgroups.id CASCADE, NOT NULL |

**Unique:** (supplier_id, subgroup_id)

### `supplier_lead_times`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| supplier_id | UUID | FK suppliers.id CASCADE, NOT NULL |
| material_type | String(50) | NOT NULL |
| default_lead_time_days | Integer | NOT NULL |
| avg_actual_lead_time_days | Numeric(5,1) | nullable |
| last_updated | DateTime(tz) | nullable |
| sample_count | Integer | NOT NULL, default 0 |

**Unique:** (supplier_id, material_type)

### `application_methods`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| code | String(20) | UNIQUE, NOT NULL |
| name | String(100) | NOT NULL |
| engobe_method | String(20) | nullable |
| glaze_method | String(20) | NOT NULL |
| needs_engobe | Boolean | NOT NULL, default true |
| two_stage_firing | Boolean | NOT NULL, default false |
| special_kiln | String(20) | nullable ('raku') |
| consumption_group_engobe | String(20) | nullable |
| consumption_group_glaze | String(20) | NOT NULL |
| blocking_task_type | String(50) | nullable |
| sort_order | Integer | NOT NULL, default 0 |
| is_active | Boolean | NOT NULL, default true |
| created_at | DateTime(tz) | NOT NULL |

### `application_collections`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| code | String(30) | UNIQUE, NOT NULL |
| name | String(100) | NOT NULL |
| allowed_methods | JSONB | NOT NULL, default [] |
| any_method | Boolean | NOT NULL, default false |
| no_base_colors | Boolean | NOT NULL, default false |
| no_base_sizes | Boolean | NOT NULL, default false |
| product_type_restriction | String(50) | nullable |
| sort_order | Integer | NOT NULL, default 0 |
| is_active | Boolean | NOT NULL, default true |
| created_at | DateTime(tz) | NOT NULL |

### `shape_consumption_coefficients`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| shape | String(20) | NOT NULL |
| product_type | String(20) | NOT NULL, default 'tile' |
| coefficient | Numeric(5,3) | NOT NULL, default 1.0 |
| description | Text | nullable |
| updated_by | UUID | FK users.id, nullable |
| updated_at | DateTime(tz) | NOT NULL |

**Unique:** (shape, product_type)

### `consumption_adjustments`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| factory_id | UUID | FK factories.id, NOT NULL |
| position_id | UUID | FK order_positions.id, NOT NULL |
| material_id | UUID | FK materials.id, NOT NULL |
| expected_qty | Numeric(12,4) | NOT NULL |
| actual_qty | Numeric(12,4) | NOT NULL |
| variance_pct | Numeric(7,2) | nullable |
| shape | String(20) | nullable |
| product_type | String(20) | nullable |
| suggested_coefficient | Numeric(5,3) | nullable |
| status | String(20) | NOT NULL, default 'pending' |
| approved_by | UUID | FK users.id, nullable |
| approved_at | DateTime(tz) | nullable |
| notes | Text | nullable |
| created_at | DateTime(tz) | NOT NULL |

### `bottleneck_config` (TOC/DBR)

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| factory_id | UUID | FK factories.id, UNIQUE, NOT NULL |
| constraint_resource_id | UUID | FK resources.id, nullable |
| buffer_target_hours | Numeric(6,1) | NOT NULL, default 24.0 |
| rope_limit | Integer | nullable |
| rope_max_days | Integer | NOT NULL, default 2 |
| rope_min_days | Integer | NOT NULL, default 1 |
| batch_mode | Enum(BatchMode) | NOT NULL, default HYBRID |
| current_bottleneck_utilization | Numeric(5,2) | default 0 |

### `buffer_status`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| resource_id | UUID | FK resources.id, NOT NULL |
| buffered_positions_count | Integer | NOT NULL, default 0 |
| buffered_sqm | Numeric(10,3) | NOT NULL, default 0 |
| buffer_health | Enum(BufferHealth) | NOT NULL, default GREEN |
| updated_at | DateTime(tz) | NOT NULL |

### `kiln_maintenance_types`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| name | String(200) | NOT NULL |
| description | Text | nullable |
| duration_hours | Numeric(5,1) | NOT NULL, default 2 |
| requires_empty_kiln | Boolean | NOT NULL, default false |
| requires_cooled_kiln | Boolean | NOT NULL, default false |
| requires_power_off | Boolean | NOT NULL, default false |
| default_interval_days | Integer | nullable |
| is_active | Boolean | NOT NULL, default true |
| created_at | DateTime(tz) | NOT NULL |
| updated_at | DateTime(tz) | NOT NULL |

### `kiln_maintenance_schedule`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| resource_id | UUID | FK resources.id, NOT NULL |
| maintenance_type | String(200) | NOT NULL |
| maintenance_type_id | UUID | FK kiln_maintenance_types.id, nullable |
| scheduled_date | Date | NOT NULL |
| scheduled_time | Time | nullable |
| estimated_duration_hours | Numeric(5,1) | nullable |
| status | Enum(MaintenanceStatus) | NOT NULL, default PLANNED |
| notes | Text | nullable |
| completed_at | DateTime(tz) | nullable |
| completed_by_id | UUID | FK users.id, nullable |
| created_by | UUID | FK users.id, nullable |
| factory_id | UUID | FK factories.id, nullable |
| is_recurring | Boolean | NOT NULL, default false |
| recurrence_interval_days | Integer | nullable |
| requires_empty_kiln | Boolean | NOT NULL, default false |
| requires_cooled_kiln | Boolean | NOT NULL, default false |
| requires_power_off | Boolean | NOT NULL, default false |
| created_at | DateTime(tz) | NOT NULL |
| updated_at | DateTime(tz) | NOT NULL |

### `kiln_maintenance_materials`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| maintenance_id | UUID | FK kiln_maintenance_schedule.id CASCADE, NOT NULL |
| material_id | UUID | FK materials.id, NOT NULL |
| required_quantity | Numeric(12,3) | NOT NULL |
| in_stock_quantity | Numeric(12,3) | NOT NULL, default 0 |

### `casters_boxes`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| factory_id | UUID | FK factories.id, NOT NULL |
| color | String(100) | NOT NULL |
| size | String(50) | NOT NULL |
| quantity | Integer | NOT NULL |
| source_order_id | UUID | FK production_orders.id, nullable |
| added_at | DateTime(tz) | NOT NULL |
| removed_at | DateTime(tz) | nullable |
| removed_reason | Enum(CastersRemovedReason) | nullable |
| notes | Text | nullable |

### `order_packing_photos`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| order_id | UUID | FK production_orders.id, NOT NULL |
| position_id | UUID | FK order_positions.id, nullable |
| photo_url | Text | NOT NULL |
| uploaded_by | UUID | FK users.id, nullable |
| uploaded_at | DateTime(tz) | NOT NULL |
| notes | Text | nullable |

### `financial_entries`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| factory_id | UUID | FK factories.id, NOT NULL |
| entry_type | Enum(ExpenseType) | NOT NULL |
| category | Enum(ExpenseCategory) | NOT NULL |
| amount | Numeric(14,2) | NOT NULL |
| currency | String(3) | NOT NULL, default 'USD' |
| description | Text | nullable |
| entry_date | Date | NOT NULL |
| reference_id | UUID | nullable |
| reference_type | String(50) | nullable |
| created_by | UUID | FK users.id, NOT NULL |
| created_at | DateTime(tz) | NOT NULL |
| updated_at | DateTime(tz) | NOT NULL |

### `order_financials`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| order_id | UUID | FK production_orders.id, UNIQUE, NOT NULL |
| total_price | Numeric(14,2) | nullable |
| currency | String(3) | NOT NULL, default 'USD' |
| cost_estimate | Numeric(14,2) | nullable |
| margin_percent | Numeric(5,2) | nullable |
| updated_at | DateTime(tz) | NOT NULL |

### `purchase_consolidation_settings`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| factory_id | UUID | FK factories.id, UNIQUE, NOT NULL |
| consolidation_window_days | Integer | NOT NULL, default 7 |
| urgency_threshold_days | Integer | NOT NULL, default 5 |
| planning_horizon_days | Integer | NOT NULL, default 30 |
| updated_by | UUID | FK users.id, nullable |
| updated_at | DateTime(tz) | auto |

### `service_lead_times`

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| factory_id | UUID | FK factories.id, NOT NULL |
| service_type | String(50) | NOT NULL |
| lead_time_days | Integer | NOT NULL, default 3 |
| updated_at | DateTime(tz) | NOT NULL |
| updated_by | UUID | FK users.id, nullable |

**Unique:** (factory_id, service_type)
