# Administrator Guide -- Moonjar PMS

> Version: 1.0 | Date: 2026-04-06
> Moonjar Production Management System

---

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Admin Panel Overview](#2-admin-panel-overview)
3. [User Management](#3-user-management)
4. [Factory Management](#4-factory-management)
5. [Telegram Bot Configuration](#5-telegram-bot-configuration)
6. [Security: Audit Log & Sessions](#6-security-audit-log--sessions)
7. [Collections Management](#7-collections-management)
8. [Colors & Color Collections](#8-colors--color-collections)
9. [Sizes Management](#9-sizes-management)
10. [Materials & Material Groups](#10-materials--material-groups)
11. [Recipes Management](#11-recipes-management)
12. [Firing Profiles](#12-firing-profiles)
13. [Temperature Groups](#13-temperature-groups)
14. [Consumption Rules](#14-consumption-rules)
15. [Warehouse Sections](#15-warehouse-sections)
16. [Packaging Box Types](#16-packaging-box-types)
17. [Suppliers](#17-suppliers)
18. [Application Types & Places](#18-application-types--places)
19. [Finishing Types](#19-finishing-types)
20. [Stages Management](#20-stages-management)
21. [Admin Settings](#21-admin-settings)
22. [Dashboard Access Control](#22-dashboard-access-control)
23. [Factory Calendar](#23-factory-calendar)
24. [PM Cleanup Permissions](#24-pm-cleanup-permissions)
25. [Integration Stubs](#25-integration-stubs)
26. [Navigation Reference](#26-navigation-reference)
27. [Tips and Best Practices](#27-tips-and-best-practices)

---

## 1. Getting Started

### 1.1. Logging In

1. Open the Moonjar PMS dashboard in your browser.
2. Sign in using one of the available methods:
   - **Google OAuth** -- click "Sign in with Google"
   - **Email and password** -- enter your credentials and click "Login"
3. After authentication, the system detects your role and redirects you to `/admin` -- the Admin Panel.

### 1.2. Role Capabilities

As Administrator, you manage all system configuration and reference data:

- User accounts and role assignments
- Factory configuration (name, location, timezone, Telegram groups)
- All product reference data (collections, colors, sizes, materials, recipes)
- Firing profiles and temperature groups
- Warehouse sections and packaging rules
- System settings (escalation rules, defect thresholds, lead times)
- Security monitoring (audit logs, active sessions)
- Dashboard access control
- Telegram bot configuration

---

## 2. Admin Panel Overview

The Admin Panel (`/admin`) is your central hub for all configuration.

### 2.1. Layout

1. **KPI Cards** -- Users count, Factories count, Active Factories count
2. **Telegram Bot Status** -- connection status and owner chat configuration
3. **Factories Section** -- factory list with CRUD operations
4. **Security Section** -- Audit Log and Active Sessions tabs
5. **Integration Stubs** -- toggle for development/test integrations
6. **Quick Links** -- shortcuts to Users and Tablo pages
7. **Reference Data** -- buttons to all reference data management pages
8. **PM Cleanup Permissions** -- temporary data deletion permissions

### 2.2. Quick Links

The Reference Data card provides direct links to all management pages:

- Recipes, Suppliers, Collections, Color Collections
- Colors, Application Types, Places of Application
- Finishing Types, Temperature Groups, Materials
- Warehouses, Packaging Rules, Sizes
- Consumption Rules, Firing Profiles

---

## 3. User Management

### 3.1. Accessing Users

Navigate to `/users` via the Quick Links section.

### 3.2. User Roles

The system supports 8 roles:

| Role | Code | Description |
|---|---|---|
| **Owner** | `owner` | Full access to everything, strategic oversight |
| **Administrator** | `administrator` | System configuration and reference data |
| **CEO** | `ceo` | Operational oversight across all factories |
| **Production Manager** | `production_manager` | Day-to-day production management |
| **Quality Manager** | `quality_manager` | Quality control and inspections |
| **Warehouse** | `warehouse` | Material inventory management |
| **Sorter Packer** | `sorter_packer` | Sorting and packing operations |
| **Purchaser** | `purchaser` | Procurement and supplier management |

### 3.3. Creating a User

1. Navigate to `/users`.
2. Click **+ Add User**.
3. Fill in:
   - **Email** -- unique email address
   - **Full Name** -- display name
   - **Role** -- select from the 8 roles
   - **Password** -- initial password (user can change later)
   - **Factory Assignment** -- which factory/factories the user can access
   - **Language** -- preferred language (en/id/ru) for Telegram bot
   - **Telegram Chat ID** -- for bot notifications (optional, can be set later)
4. Click **Create**.

### 3.4. Editing a User

- Change role, factory assignments, language, or Telegram settings
- Reset password
- Activate or deactivate accounts

> **Important**: Deactivating a user immediately revokes their access. Active sessions are terminated.

### 3.5. Factory Assignment Rules

- **Single factory users**: See only data from their assigned factory
- **Multi-factory users**: Can switch between assigned factories
- **All-factory roles** (Owner, CEO, Administrator): Automatically have access to all factories

---

## 4. Factory Management

### 4.1. Factory List

The Factories section on the Admin Panel shows all configured factories.

| Column | Description |
|---|---|
| Name | Factory display name |
| Location | Physical location |
| Timezone | Timezone for scheduling |
| Telegram | Configured chat groups (Masters, Purchaser) |
| Status | Active or Inactive |
| Actions | Edit, Delete |

### 4.2. Creating a Factory

1. Click **+ Add Factory**.
2. Fill in the Factory Dialog:
   - **Name** -- factory name (e.g., "Moonjar Bali", "Moonjar Java")
   - **Location** -- physical address or area
   - **Timezone** -- timezone (e.g., "Asia/Makassar" for Bali WITA)
   - **Masters Group Chat ID** -- Telegram group for production masters
   - **Purchaser Chat ID** -- Telegram chat for purchaser alerts
   - **Is Active** -- whether the factory is operational
3. Click **Save**.

### 4.3. Editing a Factory

Click **Edit** on any factory row to modify its settings. Common changes:

- Updating Telegram chat IDs when groups change
- Changing timezone (e.g., seasonal adjustments)
- Deactivating a factory temporarily

### 4.4. Deleting a Factory

> **Warning**: Deleting a factory is permanent and removes all associated data. Only delete test factories. To take a factory offline, deactivate it instead.

---

## 5. Telegram Bot Configuration

### 5.1. Bot Status

The Telegram Bot card shows:

- **Connected** (green dot): Bot is active, shows username
- **Not connected** (red dot): Bot is not configured or token is invalid

### 5.2. Owner Chat ID

Configure the owner's Telegram chat ID for receiving critical notifications:

1. Enter the chat ID in the input field.
2. Click **Test** to verify the connection.
3. If successful, click **Save**.

### 5.3. Discovering Chat IDs

Click **Discover Chat IDs** to see recent chats the bot has received messages from. This helps you find group chat IDs:

1. Send a message in the target Telegram group (where the bot is a member).
2. Click **Discover Chat IDs**.
3. Copy the relevant chat ID.
4. Paste it into the factory's Telegram settings.

### 5.4. Refreshing Bot Status

Click **Refresh** to re-check the bot connection status.

---

## 6. Security: Audit Log & Sessions

### 6.1. Audit Log

The Audit Log viewer shows all system changes automatically captured by the Auto Audit Logger:

- **INSERT** events -- new records created
- **UPDATE** events -- records modified
- **DELETE** events -- records removed

For each event:
- Timestamp
- User who performed the action
- Table affected
- Record ID
- Changes (old value -> new value)

> **Tip**: Use the audit log to investigate discrepancies, verify who made changes, and track system activity.

### 6.2. Active Sessions

The Active Sessions viewer shows currently logged-in users:

- User name and email
- Role
- Last activity time
- IP address
- Device/browser information

You can terminate suspicious sessions from this view.

---

## 7. Collections Management

Navigate to `/admin/collections`.

### 7.1. What Are Collections?

Collections define the product lines of Moonjar:

- **Authentic** -- natural stone finish
- **Creative** -- artistic designs
- **Stencil** -- stencil-based patterns
- **Silkscreen** -- silkscreen printing
- **Raku** -- traditional Japanese firing technique
- **Gold** -- gold leaf application
- **Exclusive** -- one-of-a-kind pieces
- **Stock** -- standard inventory items

### 7.2. Managing Collections

- **Create**: Add new collections with name and description
- **Edit**: Modify collection names or descriptions
- **Delete**: Remove collections (only if no products use them)

---

## 8. Colors & Color Collections

### 8.1. Colors

Navigate to `/admin/colors`.

Manage the color catalog:

- **Name** -- color name (e.g., "Ocean Blue", "Desert Sand")
- **Code** -- color reference code
- **Hex Value** -- hex color code for display

### 8.2. Color Collections

Navigate to `/admin/color-collections`.

Color Collections group colors by theme or collection, making it easier for sales and production to find the right colors.

---

## 9. Sizes Management

Navigate to `/admin/sizes`.

### 9.1. Size Definitions

Sizes define product dimensions with shape-specific parameters:

| Shape | Parameters |
|---|---|
| **Rectangle** | Length (cm), Width (cm) |
| **Round** | Diameter (cm) |
| **Triangle** | Side A, Side B, Side C (cm) |
| **Octagon** | Width (cm) |
| **Freeform** | Approximate dimensions |

### 9.2. Size Fields

- **Name** -- display name (e.g., "10x10", "15x20", "D30")
- **Shape** -- rectangle, round, triangle, octagon, freeform
- **Dimensions** -- shape-specific measurements
- **Area (m²)** -- automatically calculated from dimensions
- **Thickness (mm)** -- default tile thickness

---

## 10. Materials & Material Groups

### 10.1. Material Groups

Navigate to `/admin/materials` for the full material catalog.

Materials are organized in a hierarchy:

- **Type** (top level): Raw Material, Glaze Component, Engobe, Tool, etc.
- **Subgroup** (second level): Pigments / Iron Oxide, Frits / Lead-free, etc.

### 10.2. Material Fields

| Field | Description |
|---|---|
| Name | Descriptive name |
| Code | Auto-generated (M-0001, M-0002, ...) |
| Subgroup | Category in hierarchy |
| Unit | kg, g, L, ml, pcs, m, m² |
| Supplier | Default supplier |
| Warehouse Section | Storage location |

### 10.3. Material vs. Stock

Important distinction:

- **Material** (catalog entry): The definition -- name, type, unit
- **MaterialStock** (per factory): The inventory -- balance, min balance, factory ID

One material can have stock entries in multiple factories.

---

## 11. Recipes Management

Navigate to `/admin/recipes`.

### 11.1. Recipe Types

| Type | Description |
|---|---|
| **Glaze** | Glaze formulation for tile surface |
| **Engobe** | Engobe formulation (base layer under glaze) |
| **Bisque** | Body/bisque recipe (if relevant) |

### 11.2. Recipe Structure

A recipe consists of:

- **Name** -- recipe identifier
- **Type** -- glaze, engobe, or bisque
- **Temperature** -- target firing temperature
- **Ingredients** -- list of materials with percentages (must total 100%)
- **Notes** -- preparation instructions

### 11.3. Temperature Groups Integration

Recipes can be assigned to temperature groups for co-firing optimization. Tiles with recipes in the same temperature group can be fired together.

---

## 12. Firing Profiles

Navigate to `/admin/firing-profiles`.

### 12.1. What Are Firing Profiles?

A firing profile defines the heating and cooling curve for a kiln firing:

- **Name** -- profile identifier (e.g., "Standard 1050C", "Raku Fast")
- **Target Temperature** -- peak temperature in degrees Celsius
- **Total Duration** -- total firing time
- **Intervals** -- list of temperature-time segments

### 12.2. Profile Intervals

Each interval defines:

| Field | Description |
|---|---|
| Start Temperature | Beginning temperature (C) |
| End Temperature | Target temperature (C) |
| Duration | How long this segment takes (hours) |
| Ramp Rate | Degrees per hour |
| Hold | Whether to hold at end temperature |
| Hold Duration | How long to hold (hours) |

### 12.3. Multi-Round Firing

For positions requiring multiple firing rounds (firing_round > 1), stage-specific profiles can be assigned. This is used for:

- Double-fired glazes
- Gold application (requires separate firing)
- Complex layered techniques

---

## 13. Temperature Groups

Navigate to `/admin/temperature-groups`.

### 13.1. Purpose

Temperature groups allow co-firing of different recipes that share compatible firing parameters. This maximizes kiln utilization.

### 13.2. Managing Groups

- **Create**: Define a group with name and temperature range
- **Assign Recipes**: Link recipes to the group
- **View Recipes**: See which recipes belong to each group

---

## 14. Consumption Rules

Navigate to `/admin/consumption-rules`.

### 14.1. What Are Consumption Rules?

Consumption rules define how much material is used per square meter of production:

| Field | Description |
|---|---|
| Material | Which material |
| Application Method | How it's applied (spray, dip, brush) |
| Rate | Grams per square meter |
| Product Type | Which product types this rule applies to |

### 14.2. Usage

When a position moves through the glazing stage, the system:

1. Looks up the consumption rule for the glaze/engobe
2. Calculates: position area (m²) x rate (g/m²) = required amount
3. Converts units if needed (g to kg via specific gravity)
4. Deducts from material stock

---

## 15. Warehouse Sections

Navigate to `/admin/warehouses`.

### 15.1. Purpose

Warehouse sections define physical storage locations within a factory:

- Raw material storage
- Glaze storage
- Finished goods area
- Tool storage

### 15.2. Managing Sections

- **Create**: Add new sections with name, factory assignment, and description
- **Edit**: Update section names or descriptions
- **Delete**: Remove sections (only if no materials are stored there)

---

## 16. Packaging Box Types

Navigate to `/admin/packaging`.

### 16.1. Box Type Definitions

| Field | Description |
|---|---|
| Name | Box type name |
| Inner Dimensions | Length x Width x Height (cm) |
| Capacity | How many tiles fit (varies by tile size) |
| Spacer Required | Whether tiles need spacers |
| Weight Limit | Maximum weight in kg |

### 16.2. Capacity Calculation

The system calculates how many tiles fit based on:

- Tile dimensions and thickness
- Box inner dimensions
- Whether spacers are used (takes up space)

---

## 17. Suppliers

Navigate to `/admin/suppliers`.

### 17.1. Supplier Fields

| Field | Description |
|---|---|
| Name | Company name |
| Contact Person | Primary contact |
| Phone | Contact phone |
| Email | Contact email |
| Address | Physical address |
| Materials | Which materials they supply |
| Notes | Additional information |

### 17.2. Managing Suppliers

- **Create**: Add new suppliers with full contact details
- **Edit**: Update supplier information
- **Delete**: Remove suppliers (only if no active purchase requests reference them)

---

## 18. Application Types & Places

### 18.1. Application Types

Navigate to `/admin/application-types`.

Application types define how glazes are applied:

- Spray
- Dip
- Brush
- Pour
- Silkscreen
- Stencil

### 18.2. Places of Application

Navigate to `/admin/places-of-application`.

Defines where the product is installed:

- Wall
- Floor
- Countertop
- Facade
- Pool
- Bathroom

This affects production parameters (e.g., floor tiles need different glazing than wall tiles).

---

## 19. Finishing Types

Navigate to `/admin/finishing-types`.

Defines the final surface treatment:

- Glossy
- Matte
- Satin
- Textured
- Polished
- Raw

---

## 20. Stages Management

Navigate to `/admin/stages`.

### 20.1. Production Stages

The system tracks positions through production stages:

| Stage | Description |
|---|---|
| Planned | Order received, not started |
| Engobe | Engobe application |
| Glazing | Glaze application |
| Drying | Drying before firing |
| Pre-Kiln QC | Quality check before firing |
| Firing | In the kiln |
| Cooling | Cooling after firing |
| Final QC | Quality check after firing |
| Sorting | Grade sorting |
| Packing | Boxing and labeling |
| Ready | Ready for shipment |

### 20.2. Stage Configuration

For each stage, you can configure:

- Name and display order
- Average duration (days)
- Required resources
- Whether QC is required at this stage

---

## 21. Admin Settings

Navigate to `/admin/settings`.

### 21.1. Tabs

| Tab | Purpose |
|---|---|
| **Escalation Rules** | Define when and how issues are escalated |
| **Receiving** | Material receiving configuration |
| **Defect Thresholds** | When to trigger quality alerts |
| **Purchase Consolidation** | Grouping rules for purchase orders |
| **Service Lead Times** | Expected duration for each service type |

### 21.2. Escalation Rules

Configure when the system should escalate issues:

- Delay thresholds (hours before escalation)
- Notification targets (who gets notified)
- Escalation levels (PM -> CEO -> Owner)

### 21.3. Defect Thresholds

Set thresholds for automatic defect alerts:

- Position-level: alert when defect rate exceeds X% for a single position
- Factory-level: alert when overall defect rate exceeds Y%

### 21.4. Service Lead Times

Configure expected durations for production services. These are used by the scheduling engine.

---

## 22. Dashboard Access Control

Navigate to `/admin/dashboard-access`.

### 22.1. Purpose

Dashboard Access Control lets you customize which dashboard sections are visible to each role. This is useful for:

- Hiding incomplete features
- Restricting sensitive data
- Simplifying the interface for specific roles

### 22.2. Configuration

For each role, toggle visibility of:

- Specific dashboard tabs
- KPI cards
- Report sections
- Export buttons

---

## 23. Factory Calendar

Navigate to `/admin/factory-calendar`.

### 23.1. Purpose

The Factory Calendar defines working days and holidays per factory. The scheduling engine uses this to calculate realistic deadlines.

### 23.2. Managing the Calendar

- **View**: Full year calendar with holidays highlighted
- **Toggle**: Click any day to switch between working and non-working
- **Holidays**: Add named holidays (Indonesian national holidays, company holidays)
- **Per Factory**: Each factory has its own calendar

### 23.3. Impact on Scheduling

Non-working days are excluded from deadline calculations. If a holiday falls in the middle of a production run, the scheduler adds extra days automatically.

---

## 24. PM Cleanup Permissions

The Admin Panel includes PM Cleanup Permissions per factory:

| Permission | Default | Description |
|---|---|---|
| PM can delete tasks | Off | Allow PM to delete tasks |
| PM can delete positions | Off | Allow PM to delete order positions |

> **Best Practice**: Keep these off during normal operations. Enable temporarily only for data cleanup or corrections.

---

## 25. Integration Stubs

The **Stubs Toggle** allows enabling or disabling integration stubs for development and testing:

- When enabled, certain API endpoints return mock data instead of real data
- Useful during development when external services are unavailable
- Should always be **disabled** in production

---

## 26. Navigation Reference

| Page | URL | Purpose |
|---|---|---|
| Admin Panel | `/admin` | Central configuration hub |
| Users | `/users` | User management |
| Collections | `/admin/collections` | Product collections |
| Color Collections | `/admin/color-collections` | Color groupings |
| Colors | `/admin/colors` | Color catalog |
| Application Types | `/admin/application-types` | Application methods |
| Places of Application | `/admin/places-of-application` | Installation locations |
| Finishing Types | `/admin/finishing-types` | Surface treatments |
| Temperature Groups | `/admin/temperature-groups` | Co-firing groups |
| Materials | `/admin/materials` | Material catalog |
| Warehouses | `/admin/warehouses` | Warehouse sections |
| Packaging | `/admin/packaging` | Box type definitions |
| Sizes | `/admin/sizes` | Product size definitions |
| Consumption Rules | `/admin/consumption-rules` | Material usage rates |
| Firing Profiles | `/admin/firing-profiles` | Kiln firing curves |
| Recipes | `/admin/recipes` | Glaze/engobe recipes |
| Suppliers | `/admin/suppliers` | Supplier directory |
| Stages | `/admin/stages` | Production stage definitions |
| Admin Settings | `/admin/settings` | Escalation, thresholds, lead times |
| Dashboard Access | `/admin/dashboard-access` | Role-based dashboard visibility |
| Factory Calendar | `/admin/factory-calendar` | Working days and holidays |
| Tablo | `/tablo` | Production display board |
| Settings | `/settings` | Personal account settings |

---

## 27. Tips and Best Practices

> **Reference data first**: Before the system can process orders, you need to set up: factories, collections, colors, sizes, materials, recipes, firing profiles, consumption rules, and warehouse sections. Set these up in this order.

> **Test with a dummy factory**: When experimenting with settings, create a test factory. This keeps production data clean.

> **Audit log is your friend**: If something goes wrong, the audit log is the first place to look. It records every change, who made it, and when.

> **Keep recipes up to date**: When the production team adjusts a recipe, update it in the system immediately. Outdated recipes cause incorrect material consumption calculations.

> **Calendar maintenance**: At the start of each year, set up all known holidays in the Factory Calendar. This prevents scheduling surprises.

> **Session monitoring**: Check Active Sessions periodically. If you see sessions from unknown devices or locations, investigate immediately and consider resetting the affected user's password.

> **Supplier data quality**: Keep supplier contacts current. Outdated phone numbers and emails cause procurement delays.

> **Minimize cleanup permissions**: The PM cleanup permissions should be temporary. After data cleanup is complete, turn them off immediately.

> **Backup before changes**: Before making bulk changes to reference data (e.g., renaming all colors), consider the impact on existing orders and recipes. Changes to reference data can cascade through the system.

---

*This guide covers Moonjar PMS v1.0 features for the Administrator role. For technical support, contact the system developer.*
