# Warehouse Guide -- Moonjar PMS

> Version: 1.0 | Date: 2026-04-06
> Moonjar Production Management System

---

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Dashboard Overview](#2-dashboard-overview)
3. [Inventory Management](#3-inventory-management)
4. [Low Stock Alerts](#4-low-stock-alerts)
5. [Material Transactions](#5-material-transactions)
6. [Delivery Photo Processing](#6-delivery-photo-processing)
7. [Finished Goods Management](#7-finished-goods-management)
8. [Reconciliations](#8-reconciliations)
9. [Mana Shipments](#9-mana-shipments)
10. [Purchase Requests](#10-purchase-requests)
11. [Telegram Bot Commands](#11-telegram-bot-commands)
12. [Navigation Reference](#12-navigation-reference)
13. [Tips and Best Practices](#13-tips-and-best-practices)

---

## 1. Getting Started

### 1.1. Logging In

1. Open the Moonjar PMS dashboard in your browser.
2. Sign in using one of the available methods:
   - **Google OAuth** -- click "Sign in with Google"
   - **Email and password** -- enter your credentials and click "Login"
3. After authentication, the system detects your role and redirects you to `/warehouse` -- the Warehouse dashboard.

### 1.2. Factory Selection

When you log in, the system checks your factory assignments:

- **One factory**: Auto-selected, no dropdown visible.
- **Multiple factories**: A factory selector dropdown appears in the top-right corner.

> **Important**: Material transactions are factory-specific. Always verify the correct factory is selected before receiving materials or performing audits.

### 1.3. Role Capabilities

As Warehouse staff, you can:

- View and manage material inventory
- Receive incoming material deliveries
- Perform inventory audits (stock counts)
- View material transaction history
- Process delivery photos
- Manage finished goods inventory
- Perform reconciliations
- Track Mana shipments
- View and respond to purchase requests

---

## 2. Dashboard Overview

The Warehouse Dashboard (`/warehouse`) shows a summary of your key responsibilities.

### 2.1. KPI Cards

Three key metrics at the top:

| KPI | Color | Description |
|---|---|---|
| **Total Materials** | Gray | Total number of materials in the system |
| **Low Stock** | Orange | Materials with balance below minimum threshold |
| **Pending Requests** | Blue | Purchase requests waiting for action |

### 2.2. Tabs

| Tab | Purpose |
|---|---|
| **Inventory** | Full material inventory list with current balances |
| **Low Stock** | Filtered view of materials below minimum threshold |
| **Transactions** | Recent material transactions across all types |
| **Requests** | Purchase requests requiring attention |

---

## 3. Inventory Management

### 3.1. Viewing Inventory

The Inventory tab shows all materials for the selected factory:

| Column | Description |
|---|---|
| **Name** | Material name |
| **Code** | System-generated code (e.g., M-0042) |
| **Type** | Material subgroup (pigment, oxide, frit, etc.) |
| **Balance** | Current stock quantity |
| **Min Balance** | Minimum threshold for alerts |
| **Unit** | Unit of measurement (kg, g, L, ml, pcs, m, m²) |
| **Status** | "OK" (green) or deficit amount (red) |

### 3.2. Receiving Materials

When a delivery arrives at the warehouse:

1. Find the material in the Inventory tab.
2. Click the **Receive** button (up arrow icon).
3. The Transaction dialog opens in "Receive" mode.
4. Enter:
   - **Quantity** -- amount received
   - **Notes** -- delivery reference, batch number, supplier info
5. Click **"Receive"**.

The balance updates immediately.

> **Important**: Always physically count the delivery before entering the quantity. Do not rely on supplier invoices alone.

### 3.3. Inventory Audit

When you need to correct a balance (physical count differs from system):

1. Find the material in the Inventory tab.
2. Click the **Audit** button (three-line icon).
3. The Transaction dialog opens in "Inventory Audit" mode.
4. You see the **current system balance** at the top.
5. Enter the **actual physical count** in the "New actual balance" field.
6. The system automatically calculates the **difference** (green = surplus, red = deficit).
7. Enter a **Reason** for the discrepancy (mandatory).
8. Click **"Confirm Audit"**.

> **Warning**: Always provide an honest, clear reason for the audit. These records are reviewed by management. Examples: "Spillage during transfer", "Measurement error in previous count", "Found extra stock in secondary storage".

### 3.4. Switching Between Receive and Audit

When the Transaction dialog is open, you can switch between modes:

- Click **"Receive"** (green) for incoming materials
- Click **"Inventory Audit"** (amber) for stock corrections

---

## 4. Low Stock Alerts

### 4.1. How Alerts Work

Materials with a balance below their minimum threshold are flagged:

- Row background turns red in the inventory table
- Status column shows "Deficit: X.X unit" in red
- A count badge appears on the Low Stock tab

### 4.2. Responding to Low Stock

When you see a low stock alert:

1. Check the **Requests** tab to see if a purchase request already exists
2. If no request exists, notify the Production Manager
3. Check if the material is available in another warehouse section
4. For critical materials that block production, flag it as urgent

### 4.3. Min Balance Override

The Production Manager can override the minimum balance threshold for specific materials. If you see a material where the threshold seems wrong, report it to the PM.

---

## 5. Material Transactions

### 5.1. Transaction Types

| Type | Direction | Description | Color |
|---|---|---|---|
| `receive` | In | Material delivered to warehouse | Green |
| `consume` | Out | Material used in production (glazing, engobe) | Red |
| `manual_write_off` | Out | Manual stock deduction | Red |
| `reserve` | Hold | Reserved for a specific position | Blue |
| `unreserve` | Release | Reservation cancelled | Blue |
| `audit` (inventory) | Correction | Stock count adjustment | Amber |

### 5.2. Viewing Transaction History

1. Find a material in the inventory table.
2. Click the **History** button (Hst icon).
3. A dialog opens showing all transactions, newest first.
4. Each entry shows: date, type, quantity (+/-), who performed it, and notes.

### 5.3. Understanding Consumption

Material consumption happens automatically when positions advance through production:

- **Glazing stage**: Glaze and engobe are consumed based on consumption rules
- **The system calculates**: required amount based on position area and consumption rate per m²
- **If insufficient**: The position gets blocked with `INSUFFICIENT_MATERIALS` status

You don't manually enter consumption -- the system handles it. But if you notice discrepancies, perform an inventory audit.

---

## 6. Delivery Photo Processing

### 6.1. Overview

When deliveries arrive, you can photograph the delivery and use AI-powered processing to identify materials.

### 6.2. How to Use

1. Take a photo of the delivery (labels, packaging, invoices).
2. Send the photo to the Telegram bot or upload via the system.
3. The AI processes the photo using OCR to extract material names and quantities.
4. The system attempts to match extracted items with existing materials in the database.
5. Review the matches and confirm.

### 6.3. Smart Material Matching

The system uses two matching strategies:

1. **Token-based matching** -- breaks material names into tokens and finds best matches
2. **AI fallback** -- if token matching is uncertain, AI is used for more accurate matching

### 6.4. Confirmation Flow

After AI processing, you see a list of matched materials:

- **Confident match** (green) -- automatically linked, verify and confirm
- **Uncertain match** (yellow) -- AI's best guess, review carefully
- **No match** (red) -- no existing material found, you can create new or skip

For each item:
- Confirm the match
- Edit the matched material (if wrong)
- Adjust the quantity
- Skip items you don't want to receive

---

## 7. Finished Goods Management

### 7.1. Overview

Navigate to `/warehouse/finished-goods` for managing finished product inventory.

### 7.2. Features

Finished goods are products that have completed all production stages:

- **Inventory view** -- all finished products with quantities and locations
- **Availability checks** -- verify if specific products are in stock for orders
- **Location tracking** -- which warehouse section stores which products

### 7.3. Stock Availability

When checking stock for a shipment:

1. Open the Finished Goods page.
2. Search or filter by product (color, size, collection).
3. Check available quantity.
4. Mark items for shipment if available.

---

## 8. Reconciliations

### 8.1. Overview

Navigate to `/warehouse/reconciliations` for formal multi-material inventory check sessions.

### 8.2. What Is a Reconciliation?

A reconciliation is a comprehensive, scheduled stock audit covering multiple materials at once. Unlike individual material audits, a reconciliation is a formal session with a clear scope and approval process.

### 8.3. Reconciliation Workflow

1. **Create Session** -- specify the scope (which materials, which warehouse sections)
2. **Count** -- physically count each material in the scope
3. **Enter Results** -- input actual counts for each material
4. **Review Discrepancies** -- system highlights differences between expected and actual
5. **Submit** -- send for review and approval
6. **Approve/Reject** -- PM or admin reviews and approves

### 8.4. Recording Discrepancies

For each discrepancy found during reconciliation:

| Field | Description |
|---|---|
| Expected | System balance |
| Actual | Physical count |
| Difference | Calculated automatically |
| Reason | Explanation for the discrepancy |

Common reasons:
- Unrecorded consumption
- Spillage or waste
- Measurement errors in previous counts
- Transfers between sections not recorded
- Supplier short-delivery not caught at receiving

---

## 9. Mana Shipments

### 9.1. Overview

Navigate to `/warehouse/mana-shipments` for tracking inter-factory or distribution center shipments.

### 9.2. Tracking Shipments

The Mana Shipments page shows:

- Shipment ID and date
- Origin and destination
- Items included (materials or finished goods)
- Carrier information
- Tracking status (prepared, in transit, delivered)

### 9.3. Creating a Shipment Record

1. Click **+ New Shipment**.
2. Select origin and destination.
3. Add items to the shipment.
4. Enter carrier details.
5. Submit.

### 9.4. Updating Shipment Status

As shipments progress, update their status:

- **Prepared** -- items are packed and ready
- **In Transit** -- shipment has left the origin
- **Delivered** -- shipment has arrived at destination

---

## 10. Purchase Requests

### 10.1. Viewing Requests

The **Requests** tab shows purchase requests relevant to the warehouse:

| Column | Description |
|---|---|
| Material | What needs to be purchased |
| Quantity | Amount requested |
| Status | Pending, Approved, Sent, Delivered |
| Requested By | Who created the request |
| Date | When the request was created |

### 10.2. Your Role in Purchase Requests

As warehouse staff, you:

1. **Verify need** -- confirm the material is indeed low
2. **Receive delivery** -- when the purchase arrives, receive it into inventory
3. **Update status** -- mark the request as delivered after receiving

---

## 11. Telegram Bot Commands

| Command | Description |
|---|---|
| `/start` | Initialize bot connection |
| `/stock` | Check material stock levels |
| `/mystats` | View your statistics |
| `/help` | List all available commands |

### 11.1. Delivery Photo via Telegram

You can send delivery photos directly to the Telegram bot:

1. Take a photo of the delivery labels/invoice.
2. Send the photo to the bot.
3. The bot processes the image and shows matched materials.
4. Confirm or edit the matches using inline buttons.
5. Materials are received into inventory automatically.

### 11.2. Automatic Notifications

You receive notifications for:

- Low stock alerts for your factory
- New purchase requests
- Incoming delivery notifications
- Morning briefing with stock summary

---

## 12. Navigation Reference

| Page | URL | Purpose |
|---|---|---|
| Warehouse Dashboard | `/warehouse` | Main dashboard with inventory, alerts, requests |
| Finished Goods | `/warehouse/finished-goods` | Finished product inventory |
| Reconciliations | `/warehouse/reconciliations` | Formal stock audit sessions |
| Mana Shipments | `/warehouse/mana-shipments` | Inter-factory shipment tracking |
| Settings | `/settings` | Personal account settings |

---

## 13. Tips and Best Practices

> **Count before you enter**: Always physically count deliveries before entering them into the system. Supplier invoices can contain errors.

> **Audit regularly**: Don't wait for formal reconciliation sessions. If something looks off for a specific material, do a quick individual audit immediately.

> **Label everything**: Ensure all materials in the warehouse are clearly labeled with the system code. This prevents confusion and speeds up reconciliations.

> **First In, First Out (FIFO)**: Always use older stock before newer stock. This is especially important for materials that can degrade over time (some glazes, certain chemicals).

> **Report discrepancies immediately**: If you find a significant discrepancy during any stock check, report it to the PM right away. Don't wait for the end of the day.

> **Use delivery photos**: The AI matching saves significant time compared to manually entering each item. Get in the habit of photographing every delivery.

> **Keep warehouse sections organized**: The system tracks which section stores which materials. If you move materials between sections, update the system accordingly.

> **Low stock is not your fault**: Your job is to report it accurately and receive materials when they arrive. The purchasing decision and timing are the Purchaser's and PM's responsibility.

---

*This guide covers Moonjar PMS v1.0 features for the Warehouse role. For technical support, contact the system administrator.*
