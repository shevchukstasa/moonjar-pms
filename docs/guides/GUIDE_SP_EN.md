# Sorter Packer Guide -- Moonjar PMS

> Version: 1.0 | Date: 2026-04-06
> Moonjar Production Management System

---

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Dashboard Overview](#2-dashboard-overview)
3. [Sorting Workflow](#3-sorting-workflow)
4. [Quality Grading During Sorting](#4-quality-grading-during-sorting)
5. [Packing Workflow](#5-packing-workflow)
6. [Grinding Tab](#6-grinding-tab)
7. [Packing Photos](#7-packing-photos)
8. [Tasks](#8-tasks)
9. [Stock Collection Handling](#9-stock-collection-handling)
10. [Telegram Bot Commands](#10-telegram-bot-commands)
11. [Navigation Reference](#11-navigation-reference)
12. [Tips and Best Practices](#12-tips-and-best-practices)

---

## 1. Getting Started

### 1.1. Logging In

1. Open the Moonjar PMS dashboard in your browser (works on phone and tablet too).
2. Sign in using one of the available methods:
   - **Google OAuth** -- click "Sign in with Google"
   - **Email and password** -- enter your credentials and click "Login"
3. After authentication, the system redirects you to `/sorter-packer` -- the Sorting & Packing dashboard.

### 1.2. Factory Selection

Your factory is typically auto-selected. If you work at multiple locations, use the factory dropdown in the top-right corner.

### 1.3. Role Capabilities

As a Sorter Packer, you can:

- Sort fired tiles by quality grade
- Pack sorted tiles into boxes
- Upload packing photos as proof
- Process tiles for grinding (minor defects)
- Complete assigned tasks
- Split positions when needed (with approval)
- Check stock availability

---

## 2. Dashboard Overview

The Sorter Packer Dashboard (`/sorter-packer`) is designed for simplicity and mobile use.

### 2.1. KPI Cards

Three compact cards at the top:

| KPI | Color | Description |
|---|---|---|
| **Awaiting Sorting** | Orange | Positions transferred to sorting, waiting for you |
| **Packed** | Green | Positions you have already packed |
| **Open Tasks** | Blue | Active tasks assigned to you |

### 2.2. Tabs

| Tab | Purpose |
|---|---|
| **Sorting** | Positions waiting to be sorted after firing |
| **Packing** | Positions ready to be packed into boxes |
| **Grinding** | Positions sent for grinding (minor defect repair) |
| **Photos** | Packing photo upload and management |
| **Tasks** | Tasks assigned to your role |

---

## 3. Sorting Workflow

### 3.1. Overview

After tiles come out of the kiln and pass QC, they are transferred to sorting. Your job is to examine each tile, grade its quality, and prepare it for packing.

### 3.2. Sorting a Position

1. Go to the **Sorting** tab.
2. You see positions with status `transferred_to_sorting`.
3. Click on a position to view its details:
   - Order number, color, size, collection
   - Quantity expected
   - Any QC notes from the Quality Manager
4. Physically sort the tiles.
5. Update the position:
   - Enter the count of A-grade tiles
   - Enter the count of B-grade tiles (if any)
   - Enter the count of rejects
   - Enter the count of tiles sent to grinding
6. Confirm the sorting result.

### 3.3. What to Look For

During sorting, examine each tile for:

| Check | Pass | Fail |
|---|---|---|
| **Surface** | Smooth, no defects | Pinholes, crawling, bumps |
| **Color** | Consistent, matches order | Variation, wrong shade |
| **Edges** | Clean, no chips | Chipped, rough |
| **Shape** | Flat, correct dimensions | Warped, too large/small |
| **Pattern** | Clear, properly placed | Smudged, misaligned |

### 3.4. Handling Defective Tiles

When you find defective tiles:

- **Minor surface defect** -- consider sending to grinding
- **Color variation** -- separate as B-grade if still sellable
- **Structural defect** (crack, warping) -- reject
- **Wrong product** -- report to PM immediately

---

## 4. Quality Grading During Sorting

### 4.1. Grade Definitions

| Grade | Criteria | Destination |
|---|---|---|
| **A** | Perfect quality, meets all specifications | Pack for customer |
| **B** | Minor cosmetic issues, functional and sellable | Pack separately, mark as B-grade |
| **Reject** | Does not meet minimum quality standards | Write off |
| **Grinding** | Minor surface defect that can be repaired | Send to grinding stage |

### 4.2. Recording Grades

For each position you sort, the system expects a breakdown:

```
Total received: 100 tiles
A-grade: 85 tiles
B-grade: 8 tiles
Grinding: 4 tiles
Rejected: 3 tiles
```

The total must equal the number received from firing.

> **Important**: Be honest and consistent in grading. The system tracks your accuracy over time, and you earn points for precise work.

---

## 5. Packing Workflow

### 5.1. Overview

After sorting, A-grade and B-grade tiles move to the **Packing** tab.

### 5.2. Packing a Position

1. Go to the **Packing** tab.
2. Select a position to pack.
3. View the packing specification:
   - **Box type** -- which box to use (based on tile size)
   - **Tiles per box** -- how many tiles fit in one box
   - **Spacer requirement** -- whether spacers are needed between tiles
   - **Total boxes needed** -- calculated from quantity and box capacity
4. Pack the tiles physically.
5. In the system, update:
   - Number of boxes packed
   - Confirm the tile count per box
   - Note any packing issues
6. Change the position status to **Packed**.

### 5.3. Box Types

The system has configured box types with specific capacities:

| Box Type | Typical Use | Capacity |
|---|---|---|
| Small | Tiles up to 10x10 cm | Varies by tile thickness |
| Medium | Tiles 10-20 cm | Varies by tile thickness |
| Large | Tiles 20-30 cm | Varies by tile thickness |
| Custom | Irregular shapes, sinks | As specified |

The exact capacity depends on the tile size, thickness, and spacer requirements -- the system calculates this for you.

### 5.4. Spacer Requirements

Some products require spacers between tiles to prevent damage:

- **Glazed tiles** -- spacers required (glaze can scratch)
- **Unglazed tiles** -- spacers may not be required
- **Delicate patterns** -- extra padding recommended

Follow the packing specification in the system.

---

## 6. Grinding Tab

### 6.1. Overview

Tiles sent to grinding during sorting appear in the **Grinding** tab. After grinding is completed:

1. Re-inspect the tile.
2. If the defect is fixed, mark as A-grade or B-grade.
3. If the defect remains, mark as Rejected.
4. Update the position in the system.

### 6.2. Tracking Grinding Results

For each tile that went through grinding:

- Record whether grinding was successful
- Update the grade (A, B, or Reject)
- The system adjusts the position counts accordingly

---

## 7. Packing Photos

### 7.1. Overview

Navigate to the **Photos** tab to manage packing photos. Photos serve as proof of packing quality and quantity.

### 7.2. Uploading Photos

1. Go to the **Photos** tab.
2. Select the position you want to photograph.
3. Click **Upload Photo** or drag and drop.
4. The system accepts JPEG, PNG, and WebP formats.
5. Add a caption if needed.

### 7.3. What to Photograph

For each packed position, take photos of:

- **Open box** -- showing tiles neatly arranged inside
- **Box label** -- showing order number, color, size, quantity
- **Full pallet** -- if multiple boxes, show the complete pallet
- **Any damage** -- if tiles were damaged during packing

### 7.4. Photo Tips

- Ensure good lighting
- Include all four corners of the box in one shot
- Make labels readable in the photo
- Photograph any issues before reporting them

> **Tip**: Photos earn you bonus points in the gamification system (+2 points per verified photo).

---

## 8. Tasks

### 8.1. Overview

The **Tasks** tab shows tasks assigned to the Sorter Packer role. Common task types:

| Task Type | Description |
|---|---|
| **Sort batch** | Sort a specific batch of fired tiles |
| **Pack order** | Pack a specific order for shipment |
| **Re-sort** | Re-sort tiles that were returned from QC |
| **Label boxes** | Apply labels to packed boxes |
| **Prepare shipment** | Gather and organize boxes for a shipment |

### 8.2. Completing a Task

1. Click on a task in the Tasks tab.
2. Review the task details and requirements.
3. Perform the work.
4. Click **Complete Task**.
5. Add any notes about the completed work.

### 8.3. Task Priority

Tasks are color-coded by priority:

| Priority | Color | Meaning |
|---|---|---|
| **High** | Red | Urgent, do first |
| **Medium** | Yellow | Normal priority |
| **Low** | Gray | Can wait |

Blocking tasks (those that prevent production from advancing) are highlighted with a special badge.

---

## 9. Stock Collection Handling

### 9.1. What Is Stock Collection?

Positions marked as "Stock" or "Stok" belong to the Stock collection -- these are products produced for inventory rather than for a specific customer order.

### 9.2. Special Handling

Stock collection items:

- May have different packing requirements
- Are stored in the warehouse after packing (not shipped immediately)
- Should be labeled clearly as stock items
- May not have a specific deadline

The system automatically detects Stock collection items and may adjust the workflow accordingly.

---

## 10. Telegram Bot Commands

| Command | Description |
|---|---|
| `/start` | Initialize bot connection |
| `/mystats` | View your sorting/packing statistics |
| `/points` | Check your current points |
| `/leaderboard` | See how you rank among peers |
| `/challenge` | View today's daily challenge |
| `/achievements` | View your achievement badges |
| `/help` | List all available commands |

### 10.1. Daily Challenges

The system may issue daily challenges like:

- "Pack 50 boxes today" (bonus points if completed)
- "Zero rejects in sorting today"
- "Upload photos for all packed positions"

Check `/challenge` each morning.

### 10.2. Automatic Notifications

You receive notifications for:

- New batches ready for sorting
- Task assignments
- Points earned
- Achievement unlocked
- Morning briefing with daily plan

---

## 11. Navigation Reference

| Page | URL | Purpose |
|---|---|---|
| Sorter Packer Dashboard | `/sorter-packer` | Main dashboard with all tabs |
| Settings | `/settings` | Personal account settings |

The Sorter Packer role has a single, focused dashboard with everything accessible through tabs.

---

## 12. Tips and Best Practices

> **Sort before you pack**: Never pack tiles without sorting them first. Even if they look fine at a glance, each tile should be individually examined.

> **Be consistent with grading**: The line between A-grade and B-grade should be consistent day to day. If you're unsure, ask the Quality Manager for guidance.

> **Photograph everything**: Packing photos are your protection. If a customer claims damage during shipping, your photos prove the product left the factory in good condition.

> **Handle tiles with care**: Glazed surfaces are delicate. Always use gloves and place tiles gently. A small chip at this stage wastes all the previous production work.

> **Check your challenges**: Daily challenges are a great way to earn extra points. Check the Telegram bot each morning for the day's challenge.

> **Report anomalies immediately**: If you receive tiles from the kiln that look wrong (wrong color, wrong size, wrong quantity), report to the Production Manager before starting to sort. Do not assume it's correct.

> **Count accurately**: The system compares your counts against what was sent from firing. Consistent discrepancies will be flagged for investigation.

> **Keep your workspace clean**: A clean sorting table means fewer accidental damages and faster work. Clean your area at the end of each shift.

---

*This guide covers Moonjar PMS v1.0 features for the Sorter Packer role. For technical support, contact the system administrator.*
