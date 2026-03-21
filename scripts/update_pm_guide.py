#!/usr/bin/env python3
"""
Update PM Guide — scans the codebase for features accessible to the
production_manager role and adds missing sections to docs/guides/GUIDE_PM_EN.md.

Usage:
    python scripts/update_pm_guide.py
"""

import os
import re
import sys
import difflib

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUIDE_PATH = os.path.join(PROJECT_ROOT, "docs", "guides", "GUIDE_PM_EN.md")


# ---------------------------------------------------------------------------
# Step 1 — Read current guide and extract existing section headers
# ---------------------------------------------------------------------------

def read_guide() -> str:
    with open(GUIDE_PATH, "r", encoding="utf-8") as f:
        return f.read()


def extract_section_keywords(guide_text: str) -> set[str]:
    """Return a set of normalised keywords from all ## and ### headings."""
    keywords: set[str] = set()
    for m in re.finditer(r"^#{2,3}\s+(.+)$", guide_text, re.MULTILINE):
        heading = m.group(1).strip().lower()
        # strip leading numbers like "8.1." or "10."
        heading = re.sub(r"^\d+(\.\d+)?\.\s*", "", heading)
        keywords.add(heading)
    return keywords


# ---------------------------------------------------------------------------
# Step 2 — Define features accessible to production_manager
# ---------------------------------------------------------------------------

# Each entry: (keyword_match, section_number, heading, markdown_body)
# keyword_match is checked against existing headings (case-insensitive).
# If none of the keywords appear in the existing guide headings, the section
# is considered missing and will be added.

MISSING_FEATURES: list[dict] = [
    # ── Kiln Maintenance ──────────────────────────────────────────────
    {
        "match_keywords": ["kiln maintenance"],
        "section": "11",
        "heading": "Kiln Maintenance",
        "body": """\
### 11.1. Overview

The Kiln Maintenance page provides a structured workflow for scheduling, tracking, and completing preventive and corrective maintenance on kilns. Unlike Kiln Inspections (Section 8), which focus on weekly condition assessments, Kiln Maintenance manages scheduled work: element replacements, thermocouple calibrations, brick repairs, deep cleans, and more.

**Path**: `/manager/kiln-maintenance`

### 11.2. Page Tabs

| Tab | Purpose |
|---|---|
| **Upcoming** | Shows all planned maintenance items sorted by date, with overdue items highlighted in red |
| **History** | Completed and cancelled maintenance records |
| **Maintenance Types** | Manage the catalogue of maintenance type definitions (e.g., "Element replacement", "Deep clean") |

### 11.3. Scheduling Maintenance

1. On the **Upcoming** tab, click **"+ Schedule Maintenance"**.
2. Fill in the form:
   - **Kiln** -- select the kiln (filtered by factory if a factory is selected).
   - **Maintenance Type** -- choose from predefined types.
   - **Scheduled Date** -- when the maintenance should be performed.
   - **Notes** -- any additional instructions.
3. Requirements are set automatically based on the maintenance type:
   - **Requires empty kiln** -- the kiln must be unloaded before work begins.
   - **Requires cooled kiln** -- the kiln must be at room temperature.
   - **Requires power off** -- electrical supply must be disconnected.
4. For recurring maintenance, set the **Recurrence Interval** (in days). The system automatically schedules the next occurrence after each completion.

### 11.4. Completing Maintenance

1. Find the maintenance item on the **Upcoming** tab.
2. Click **"Complete"**.
3. Optionally add **Completion Notes** describing what was done.
4. Click **"Confirm"**. The item moves to the History tab.
5. If the item is recurring, a new scheduled item is automatically created for the next interval.

### 11.5. Summary Cards

The Upcoming tab shows four summary cards at the top:

| Card | Description |
|---|---|
| Total Scheduled | All planned maintenance items in the next 90 days |
| Overdue | Items past their scheduled date (highlighted red) |
| Today | Items due today (highlighted yellow) |
| + Schedule | Quick-action button to add new maintenance |

### 11.6. Managing Maintenance Types

On the **Maintenance Types** tab you can create, edit, and delete type definitions. Each type has:
- **Name** -- e.g., "Element replacement", "Thermocouple calibration"
- **Default requirements** -- whether the kiln must be empty, cooled, or powered off
- **Default recurrence interval** -- automatic repeat period in days

""",
    },

    # ── Grinding Decisions ────────────────────────────────────────────
    {
        "match_keywords": ["grinding", "grinding decisions"],
        "section": "12",
        "heading": "Grinding Decisions",
        "body": """\
### 12.1. Overview

The Grinding Decisions page manages products that were sorted into the "grinding" category during the Sorting stage. These items have minor surface defects that can potentially be recovered by grinding or, alternatively, sent to Mana (an external party) for disposal or rework.

**Path**: `/manager/grinding`

### 12.2. Status Workflow

Each grinding stock item has one of three statuses:

| Status | Meaning |
|---|---|
| **Pending** | Awaiting PM decision |
| **Grinding** | Decided: will be ground and reused |
| **Sent to Mana** | Decided: sent to external party for processing |

### 12.3. Making Decisions

For each pending item you see three action buttons:

- **Grind** (green) -- mark the item for internal grinding and reuse.
- **Hold** (amber) -- keep the item in pending status for later decision.
- **Mana** (red) -- send to Mana. A confirmation dialog appears before this action is finalised.

### 12.4. Summary Cards

Four KPI cards are displayed at the top:

| Card | Description |
|---|---|
| Total Items | All grinding stock items |
| Pending Decision | Items awaiting PM action |
| Decided (Grind) | Items approved for grinding |
| Sent to Mana | Items sent to external party |

### 12.5. Filters

- **Status tabs**: All / Pending / Decided (Grind) / Sent to Mana
- **Factory selector**: Filter by factory
- **Pagination**: 50 items per page

""",
    },

    # ── Finished Goods ────────────────────────────────────────────────
    {
        "match_keywords": ["finished goods"],
        "section": "13",
        "heading": "Finished Goods",
        "body": """\
### 13.1. Overview

The Finished Goods page tracks the inventory of completed products that are ready for shipment or storage. It records stock by colour, size, collection, product type, and factory.

**Path**: `/warehouse/finished-goods`

### 13.2. Key Actions

- **+ Add Stock** -- add a new finished goods record (factory, colour, size, collection, product type, quantity, reserved quantity).
- **Edit** -- update quantity or reserved quantity for an existing item.
- **Check Availability** -- query across all factories to see if a specific colour/size combination is available in the required quantity. The system shows which factories hold matching stock and how many pieces are available.

### 13.3. Understanding the Table

| Column | Description |
|---|---|
| **Color** | Product colour name |
| **Size** | Product size |
| **Collection** | Product collection |
| **Type** | Product type (tile, sink, pebble) |
| **Factory** | Which factory holds the stock |
| **Quantity** | Total pieces in stock |
| **Reserved** | Pieces reserved for orders |
| **Available** | Quantity minus reserved (colour-coded: red if zero, yellow if low, green if sufficient) |

### 13.4. Filters

- **Factory** dropdown -- filter by a specific factory or view all.
- **Color search** -- search by colour name (debounced).
- **Pagination** -- 50 items per page.

### 13.5. Totals

Summary totals at the bottom of the page show aggregate Quantity, Reserved, and Available across all visible items.

""",
    },

    # ── Reconciliations ───────────────────────────────────────────────
    {
        "match_keywords": ["reconciliations", "reconciliation"],
        "section": "14",
        "heading": "Reconciliations",
        "body": """\
### 14.1. Overview

The Reconciliations page manages formal inventory check sessions. Unlike the single-material Inventory Audit (Section 3.6), a Reconciliation is a structured event that can cover multiple materials at once. It is used for periodic full or partial stock-takes.

**Path**: `/warehouse/reconciliations`

### 14.2. Reconciliation Statuses

| Status | Meaning |
|---|---|
| **Scheduled** | Planned for a future date |
| **Draft** | Created but not yet started |
| **In Progress** | Currently being counted |
| **Completed** | All items counted and adjustments applied |
| **Cancelled** | Reconciliation cancelled |

### 14.3. Creating a Reconciliation

1. Click **"+ New Reconciliation"**.
2. Select the **Factory**.
3. Add optional **Notes** (e.g., "Monthly stock-take -- warehouse A").
4. Click **"Create"**.

### 14.4. Working with a Reconciliation

1. Click on a reconciliation row to expand it.
2. **Add items** -- select materials to include in the count.
3. For each item, enter the **actual counted quantity**.
4. The system shows the **system balance** alongside the counted quantity and calculates the **difference**.
5. When all items are counted, click **"Complete"**.
6. On completion the system applies the balance adjustments as inventory audit transactions.

### 14.5. Summary Cards

| Card | Description |
|---|---|
| Total | All reconciliations |
| In Progress | Active reconciliations being counted |
| Completed | Finished reconciliations |
| Scheduled | Reconciliations planned for the future |

### 14.6. Filters

- **Factory Selector** -- filter by factory.
- **Status tabs** -- All / In Progress / Completed / Scheduled / Cancelled.

""",
    },

    # ── Reports & Analytics ───────────────────────────────────────────
    {
        "match_keywords": ["reports", "analytics"],
        "section": "15",
        "heading": "Reports and Analytics",
        "body": """\
### 15.1. Overview

The Reports page provides aggregated production metrics with date-range and factory filters.

**Path**: `/reports`

### 15.2. Filters

- **Factory** -- select a specific factory or "All Factories".
- **Date range** -- From / To date pickers (defaults to the last 30 days).

### 15.3. Orders Summary

Four KPI cards at the top:

| Card | Description |
|---|---|
| **Total Orders** | Number of orders in the selected period (with in-progress count as subtitle) |
| **Completed** | Orders that reached shipped status (with on-time count as subtitle) |
| **On-time %** | Percentage of completed orders delivered by their deadline. Green >= 80%, Yellow >= 50%, Red < 50% |
| **Avg Days to Complete** | Average number of days from order creation to shipped status |

### 15.4. Kiln Utilization

For each kiln, a card displays:

- **Kiln name** and utilization percentage badge (green >= 80%, yellow >= 50%, red < 50%).
- A **progress bar** showing visual utilization.
- **Total firings** count for the period.
- **Average load** (m2 per firing).

This section helps you identify under-utilized kilns that could take additional batches and over-loaded kilns that may need scheduling adjustments.

""",
    },

    # ── Factory Calendar ──────────────────────────────────────────────
    {
        "match_keywords": ["factory calendar"],
        "section": "16",
        "heading": "Factory Calendar",
        "body": """\
### 16.1. Overview

The Factory Calendar manages working days, holidays, and non-working days for each factory. The schedule engine uses this calendar to calculate accurate production timelines and deadlines.

**Path**: `/admin/factory-calendar`

### 16.2. Calendar View

The page displays a visual monthly calendar grid. Each day is colour-coded:

| Colour | Meaning |
|---|---|
| **White** | Normal working day |
| **Red / marked** | Non-working day (holiday, day off) |

Click any day to add or remove a holiday entry. Click and drag to select a range of dates.

### 16.3. Navigation

- **Month arrows** -- move forward or backward by month.
- **Year arrows** -- move forward or backward by year.
- **Factory selector** -- choose which factory's calendar to manage.

### 16.4. Bulk Holiday Presets

Two quick-import presets are available:

- **Indonesian National Holidays** -- imports major government holidays (New Year, Eid, Independence Day, Christmas, etc.).
- **Balinese Holidays** -- imports Nyepi, Galungan, Kuningan, and other Balinese ceremony days.

Click a preset to preview the dates, then confirm to add them all at once. Existing entries are not duplicated.

### 16.5. Adding and Removing Holidays

**Add**: Click a day on the calendar, enter a name (e.g., "Nyepi"), and save.

**Remove**: Click an existing holiday day and confirm deletion.

> **Important**: Changes to the factory calendar may affect scheduled production timelines. After significant calendar changes, consider triggering a reschedule from the Schedule page.

""",
    },

    # ── Recipes ───────────────────────────────────────────────────────
    {
        "match_keywords": ["recipes management", "recipe management"],
        "section": "17",
        "heading": "Recipes Management",
        "body": """\
### 17.1. Overview

The Recipes page allows PM to view and manage glaze, engobe, and product recipes. Each recipe defines its ingredients with quantities, application rates (spray, brush, splash, silk screen), and links to temperature groups for firing.

**Path**: `/admin/recipes`

### 17.2. Recipe Fields

| Field | Description |
|---|---|
| **Name** | Recipe name (e.g., "Moonjar White Glaze M-01") |
| **Type** | Product, Glaze, or Engobe |
| **Color Collection** | Which colour collection this recipe belongs to |
| **Client** | Client name (if recipe is client-specific) |
| **Specific Gravity** | Density of the mixed glaze/engobe (g/ml) |
| **Spray Rate** | Consumption rate for spray application (ml/m2) |
| **Brush Rate** | Consumption rate for brush application (ml/m2) |
| **Default** | Whether this recipe is the default for its type |
| **Active** | Whether the recipe is currently in use |

### 17.3. Ingredients

Each recipe has a list of ingredients grouped by material type (Frits, Pigments, Oxides/Carbonates, Other). For each ingredient:
- **Material** -- selected from the materials catalogue.
- **Quantity** -- weight in the recipe formula.
- **Per-ingredient rates** -- spray, brush, splash, and silk screen rates can be set individually.

### 17.4. Key Actions

- **Create** -- add a new recipe with ingredients.
- **Edit** -- modify recipe fields or ingredient list.
- **Duplicate** -- copy an existing recipe to create a variant.
- **CSV Import** -- bulk import recipes from a CSV file.

### 17.5. Temperature Group Links

Recipes can be linked to one or more temperature groups. This determines which kiln temperatures are compatible with the recipe and is used by the batch formation algorithm when grouping positions for co-firing.

""",
    },

    # ── Firing Profiles ───────────────────────────────────────────────
    {
        "match_keywords": ["firing profiles"],
        "section": "18",
        "heading": "Firing Profiles",
        "body": """\
### 18.1. Overview

Firing Profiles define the heating and cooling curves used during kiln firing. Each profile specifies multi-interval temperature stages: how fast the kiln heats from one temperature to another, and how it cools down afterward.

**Path**: `/admin/firing-profiles`

### 18.2. Profile Fields

| Field | Description |
|---|---|
| **Name** | Profile name (e.g., "Standard 1012°C -- 14h") |
| **Temperature Group** | Which temperature group this profile is for |
| **Total Duration** | Expected total firing time in hours |
| **Active** | Whether this profile is available for use |

### 18.3. Heating and Cooling Stages

Each profile has two lists of temperature stages:

**Heating stages** (type = heating):
- **Start Temp** -- starting temperature in °C (first stage typically starts at ~20°C).
- **End Temp** -- target temperature for this stage.
- **Rate** -- heating rate in °C per hour.

**Cooling stages** (type = cooling):
- **Start Temp** -- temperature at the start of cooling (typically the peak firing temperature).
- **End Temp** -- temperature at the end of this cooling stage.
- **Rate** -- cooling rate in °C per hour.

You can add multiple intervals to create complex curves. For example:
- Stage 1: 20°C -> 600°C at 100°C/h (slow initial heating)
- Stage 2: 600°C -> 1012°C at 50°C/h (slow approach to target)
- Cooling 1: 1012°C -> 600°C at 80°C/h (controlled initial cooling)
- Cooling 2: 600°C -> 20°C at 120°C/h (natural cooling)

### 18.4. Key Actions

- **Create** -- define a new profile with heating and cooling stages.
- **Edit** -- modify stages, rates, or duration.
- **Activate / Deactivate** -- toggle profile availability.

""",
    },

    # ── Temperature Groups ────────────────────────────────────────────
    {
        "match_keywords": ["temperature groups"],
        "section": "19",
        "heading": "Temperature Groups",
        "body": """\
### 19.1. Overview

Temperature Groups categorise firing temperatures. Each group has a name, a target temperature (°C), and a display order. Recipes and firing profiles are linked to temperature groups, allowing the system to automatically group compatible positions for co-firing.

**Path**: `/admin/temperature-groups`

### 19.2. Fields

| Field | Description |
|---|---|
| **Name** | Group name (e.g., "Standard 1012°C", "Low-fire 800°C") |
| **Temperature** | Target firing temperature in °C |
| **Description** | Optional notes |
| **Display Order** | Sort position in lists |

### 19.3. Recipe Links

Each temperature group shows its linked recipes. This makes it easy to see which glazes and engobes fire at the same temperature and can share a kiln batch.

### 19.4. Key Actions

- **Create** -- add a new temperature group.
- **Edit** (inline) -- modify name, temperature, description, or display order.
- **Delete** -- remove a temperature group (only if no recipes are linked).
- **CSV Import** -- bulk import from a CSV file.

""",
    },

    # ── Stages Management ─────────────────────────────────────────────
    {
        "match_keywords": ["stages management", "stages"],
        "section": "20",
        "heading": "Stages Management",
        "body": """\
### 20.1. Overview

The Stages page manages the production stage definitions that positions move through. Each stage has a name and a sort order that determines its sequence in the production pipeline.

**Path**: `/admin/stages`

### 20.2. Fields

| Field | Description |
|---|---|
| **Name** | Stage name (e.g., "Glazing", "Firing", "Sorting", "QC") |
| **Order** | Numeric position in the production sequence |

### 20.3. Key Actions

- **Create** -- add a new production stage.
- **Edit** -- modify name or order.
- **Delete** -- remove a stage (only if not referenced by active positions).

> **Note**: Stage definitions are used by the schedule engine and the position lifecycle. Changing stage order or names may affect how positions are displayed on the Schedule page.

""",
    },

    # ── Firing Schedules ──────────────────────────────────────────────
    {
        "match_keywords": ["firing schedules"],
        "section": "21",
        "heading": "Firing Schedules",
        "body": """\
### 21.1. Overview

The Firing Schedules page manages per-kiln firing schedule templates. A firing schedule defines the planned firing parameters for a specific kiln, including timing and configuration data.

**Path**: `/admin/firing-schedules`

### 21.2. Fields

| Field | Description |
|---|---|
| **Kiln** | Which kiln this schedule applies to |
| **Name** | Schedule name (e.g., "Standard weekday firing") |
| **Schedule Data** | JSON configuration with firing parameters |
| **Default** | Whether this is the default schedule for the kiln |

### 21.3. Filters

- **Kiln dropdown** -- filter schedules by kiln.

### 21.4. Key Actions

- **Create** -- add a new firing schedule for a kiln.
- **Edit** -- modify schedule parameters.
- **Set as Default** -- mark a schedule as the default for its kiln.
- **Delete** -- remove a schedule.

""",
    },

    # ── Warehouses Management ─────────────────────────────────────────
    {
        "match_keywords": ["warehouses management"],
        "section": "22",
        "heading": "Warehouses Management",
        "body": """\
### 22.1. Overview

The Warehouses page manages warehouse sections where materials are stored. Each section belongs to a factory and can be assigned to a specific user.

**Path**: `/admin/warehouses`

### 22.2. Fields

| Field | Description |
|---|---|
| **Name** | Section name (e.g., "Raw Materials Store A") |
| **Code** | Short identifier code |
| **Factory** | Which factory this section belongs to |
| **Type** | Section (physical), Warehouse (full warehouse), or Virtual |
| **Managed By** | User responsible for this section |
| **Display Order** | Sort position |
| **Default** | Whether this is the default section for its factory |
| **Active** | Whether the section is currently in use |

### 22.3. Key Actions

- **Create** -- add a new warehouse section.
- **Edit** -- modify section details.
- **Delete** -- remove a section.
- **CSV Import** -- bulk import from a CSV file.

""",
    },

    # ── Packaging Management ──────────────────────────────────────────
    {
        "match_keywords": ["packaging management"],
        "section": "23",
        "heading": "Packaging Management",
        "body": """\
### 23.1. Overview

The Packaging page manages box type definitions and their capacities. Each box type specifies how many pieces of each size fit per box, and which spacer materials are used.

**Path**: `/admin/packaging`

### 23.2. Key Concepts

- **Box Type** -- a specific packaging box linked to a material (the box itself is a material in the inventory).
- **Capacity** -- for each product size, defines the number of pieces per box and the area (m2) per box.
- **Spacers** -- for each product size, defines which spacer material is used and how many spacers go in each box.

### 23.3. Key Actions

- **Create** -- add a new box type with capacities and spacer definitions.
- **Edit** -- modify capacities or spacer configurations.
- **CSV Import** -- bulk import packaging definitions.

""",
    },

    # ── Sizes Management ──────────────────────────────────────────────
    {
        "match_keywords": ["sizes management"],
        "section": "24",
        "heading": "Sizes Management",
        "body": """\
### 24.1. Overview

The Sizes page manages product size definitions. Each size has dimensions, a shape, and an automatically calculated area used for material consumption calculations.

**Path**: `/admin/sizes`

### 24.2. Fields

| Field | Description |
|---|---|
| **Name** | Size name (e.g., "30x60", "20x20 round") |
| **Width** | Width in mm |
| **Height** | Height in mm |
| **Thickness** | Default thickness in mm |
| **Shape** | Rectangle, Round, Triangle, Octagon, Freeform |
| **Shape Dimensions** | Additional dimension parameters for non-rectangular shapes |
| **Area** | Calculated area in cm2 (automatic based on shape and dimensions) |
| **Custom** | Whether this is a one-off custom size |

### 24.3. Key Actions

- **Create** -- add a new size definition with shape-specific dimension editors.
- **Edit** -- modify dimensions or shape.
- **Delete** -- remove a size (only if not used by active positions).
- **CSV Import** -- bulk import sizes.

""",
    },

    # ── Tablo ─────────────────────────────────────────────────────────
    {
        "match_keywords": ["tablo"],
        "section": "25",
        "heading": "Tablo (Production Display)",
        "body": """\
### 25.1. Overview

The Tablo page is a full-screen production display board designed to be shown on a workshop TV or monitor. It provides a real-time overview of production status without requiring interaction.

**Path**: `/tablo`

### 25.2. Usage

- Open the Tablo page on a dedicated screen in the production area.
- The display auto-refreshes to show current production status.
- No authentication actions are needed on this page -- it is a read-only view.

""",
    },

    # ── Updated Navigation Table ──────────────────────────────────────
    {
        "match_keywords": ["__navigation_table_update__"],  # never matches -- we handle this specially
        "section": "NAV_UPDATE",
        "heading": "",
        "body": "",
    },
]


# ---------------------------------------------------------------------------
# Step 3 — Compare and determine what is missing
# ---------------------------------------------------------------------------

def find_missing_features(guide_text: str) -> list[dict]:
    headings = extract_section_keywords(guide_text)
    missing: list[dict] = []
    for feat in MISSING_FEATURES:
        if feat["section"] == "NAV_UPDATE":
            continue
        matched = any(kw in heading for kw in feat["match_keywords"] for heading in headings)
        if not matched:
            missing.append(feat)
    return missing


# ---------------------------------------------------------------------------
# Step 4 — Build the updated navigation table
# ---------------------------------------------------------------------------

FULL_NAV_TABLE = """\
| Page | URL | Purpose |
|---|---|---|
| PM Dashboard | `/manager` | Main control panel with tabs for orders, tasks, materials, defects, and more |
| Schedule | `/manager/schedule` | Production schedule by section (Glazing, Firing, Sorting, QC, Kilns) |
| Kilns | `/manager/kilns` | Kiln management, maintenance, loading rules |
| Kiln Inspections | `/manager/kiln-inspections` | Weekly checklist-based kiln condition assessments |
| Kiln Maintenance | `/manager/kiln-maintenance` | Scheduled preventive and corrective maintenance |
| Grinding | `/manager/grinding` | Grinding decisions for defective products |
| Materials | `/manager/materials` | Material inventory, receiving, audit, transaction history |
| Recipes | `/admin/recipes` | Glaze, engobe, and product recipe management |
| Firing Profiles | `/admin/firing-profiles` | Multi-interval heating/cooling curves for kilns |
| Temp Groups | `/admin/temperature-groups` | Temperature group definitions for co-firing |
| Warehouses | `/admin/warehouses` | Warehouse section management |
| Packaging | `/admin/packaging` | Box types, capacities, and spacer definitions |
| Sizes | `/admin/sizes` | Product size definitions with shape-specific dimensions |
| Consumption Rules | `/admin/consumption-rules` | Glaze/engobe consumption rates per square meter |
| Factory Calendar | `/admin/factory-calendar` | Working days, holidays, and non-working days per factory |
| Finished Goods | `/warehouse/finished-goods` | Finished product inventory and availability checks |
| Reconciliations | `/warehouse/reconciliations` | Formal multi-material inventory check sessions |
| Reports | `/reports` | Orders summary, kiln utilization, and production analytics |
| Tablo | `/tablo` | Full-screen production display board for workshop monitors |
| Order Details | `/orders/:id` | Detailed view of a specific order and its positions |
| Guide | `/manager/guide` | This PM guide (in-app) |"""


# ---------------------------------------------------------------------------
# Step 5 — Generate updated guide
# ---------------------------------------------------------------------------

def build_updated_guide(original: str, missing: list[dict]) -> str:
    updated = original

    # --- Update the navigation table in Section 1.3 ---
    nav_pattern = re.compile(
        r"(### 1\.3\. Navigation.*?As a Production Manager, you have access to the following pages:\s*\n\n)"
        r"(\|.*?\|.*?\n(?:\|.*?\n)*)",
        re.DOTALL,
    )
    m = nav_pattern.search(updated)
    if m:
        updated = updated[: m.start(2)] + FULL_NAV_TABLE + "\n" + updated[m.end(2):]

    # --- Update the Table of Contents ---
    toc_entries: list[str] = []
    for feat in missing:
        sec = feat["section"]
        heading = feat["heading"]
        anchor = f"{sec.lower()}-{heading.lower().replace(' ', '-').replace('&', 'and').replace('(', '').replace(')', '')}"
        toc_entries.append(f"{sec}. [{heading}](#{anchor})")

    # Insert new TOC entries before "Tips and Best Practices"
    tips_toc_pattern = re.compile(r"(10\. \[Tips and Best Practices\])")
    if toc_entries and tips_toc_pattern.search(updated):
        toc_block = "\n".join(toc_entries) + "\n"
        updated = tips_toc_pattern.sub(toc_block + r"\1", updated)

    # --- Insert new sections before Section 10 (Tips and Best Practices) ---
    # Find the line "## 10. Tips and Best Practices"
    tips_section_pattern = re.compile(r"\n(## 10\. Tips and Best Practices)")
    if missing and tips_section_pattern.search(updated):
        new_sections = ""
        for feat in missing:
            new_sections += f"\n## {feat['section']}. {feat['heading']}\n\n"
            new_sections += feat["body"]
            new_sections += "---\n"
        updated = tips_section_pattern.sub("\n" + new_sections + r"\1", updated)

    # --- Renumber section 10 (Tips) to the correct number ---
    if missing:
        new_tips_num = 10 + len(missing)
        updated = updated.replace(
            "## 10. Tips and Best Practices",
            f"## {new_tips_num}. Tips and Best Practices",
        )
        # Update TOC reference
        updated = updated.replace(
            "10. [Tips and Best Practices]",
            f"{new_tips_num}. [Tips and Best Practices]",
        )
        # Update sub-section numbers within Tips section ONLY.
        # Use a targeted regex that only matches subsections AFTER the Tips heading.
        def renumber_tips_subsections(text: str) -> str:
            tips_heading = f"## {new_tips_num}. Tips and Best Practices"
            idx = text.find(tips_heading)
            if idx == -1:
                return text
            before = text[:idx]
            after = text[idx:]
            for i in range(1, 7):
                after = after.replace(f"### 10.{i}.", f"### {new_tips_num}.{i}.")
            return before + after
        updated = renumber_tips_subsections(updated)

    # --- Update version date ---
    updated = updated.replace(
        "> Version: 1.0 | Date: 2026-03-20",
        "> Version: 1.1 | Date: 2026-03-21",
    )

    return updated


# ---------------------------------------------------------------------------
# Step 6 — Print diff and write
# ---------------------------------------------------------------------------

def print_diff_summary(original: str, updated: str):
    orig_lines = original.splitlines(keepends=True)
    new_lines = updated.splitlines(keepends=True)
    diff = list(difflib.unified_diff(orig_lines, new_lines, fromfile="GUIDE_PM_EN.md (old)", tofile="GUIDE_PM_EN.md (new)", n=1))

    if not diff:
        print("No changes needed — the guide is up to date.")
        return

    added = sum(1 for l in diff if l.startswith("+") and not l.startswith("+++"))
    removed = sum(1 for l in diff if l.startswith("-") and not l.startswith("---"))
    print(f"\n{'='*60}")
    print(f"  DIFF SUMMARY")
    print(f"{'='*60}")
    print(f"  Lines added:   +{added}")
    print(f"  Lines removed: -{removed}")
    print(f"{'='*60}\n")

    # Print the full diff for review
    for line in diff:
        print(line, end="")
    print()


def main():
    print("="*60)
    print("  PM Guide Updater")
    print("="*60)

    # Step 1: Read current guide
    print("\n[1/4] Reading current guide...")
    original = read_guide()
    print(f"  Current guide: {len(original.splitlines())} lines")

    # Step 2: Analyse existing content
    print("\n[2/4] Analysing existing content...")
    headings = extract_section_keywords(original)
    print(f"  Found {len(headings)} existing section headings")

    # Step 3: Find missing features
    print("\n[3/4] Comparing with codebase features...")
    missing = find_missing_features(original)
    if not missing:
        print("  No missing features found. Guide is up to date!")
        return

    print(f"  Found {len(missing)} missing feature(s):")
    for feat in missing:
        print(f"    - Section {feat['section']}: {feat['heading']}")

    # Step 4: Generate updated guide
    print("\n[4/4] Generating updated guide...")
    updated = build_updated_guide(original, missing)
    print(f"  Updated guide: {len(updated.splitlines())} lines")

    # Print diff
    print_diff_summary(original, updated)

    # Write
    with open(GUIDE_PATH, "w", encoding="utf-8") as f:
        f.write(updated)
    print(f"\nGuide written to: {GUIDE_PATH}")
    print("Done!")


if __name__ == "__main__":
    main()
