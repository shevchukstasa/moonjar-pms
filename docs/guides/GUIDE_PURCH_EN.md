# Purchaser Guide -- Moonjar PMS

> Version: 1.0 | Date: 2026-04-06
> Moonjar Production Management System

---

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Dashboard Overview](#2-dashboard-overview)
3. [Active Purchase Requests](#3-active-purchase-requests)
4. [Deliveries Management](#4-deliveries-management)
5. [Material Deficits](#5-material-deficits)
6. [Supplier Management](#6-supplier-management)
7. [Cost Tracking](#7-cost-tracking)
8. [Purchase Consolidation](#8-purchase-consolidation)
9. [Telegram Bot Commands](#9-telegram-bot-commands)
10. [Navigation Reference](#10-navigation-reference)
11. [Tips and Best Practices](#11-tips-and-best-practices)

---

## 1. Getting Started

### 1.1. Logging In

1. Open the Moonjar PMS dashboard in your browser.
2. Sign in using one of the available methods:
   - **Google OAuth** -- click "Sign in with Google"
   - **Email and password** -- enter your credentials and click "Login"
3. After authentication, the system redirects you to `/purchaser` -- the Purchaser dashboard.

### 1.2. Factory Selection

When you log in, the system checks your factory assignments:

- **One factory**: Auto-selected, no dropdown visible.
- **Multiple factories**: A factory selector dropdown appears in the top-right corner.

> **Important**: Purchase requests and supplier deliveries are factory-specific. Ensure the correct factory is selected.

### 1.3. Role Capabilities

As a Purchaser, you can:

- View and manage purchase requests
- Track deliveries from suppliers
- Monitor material deficits across the factory
- Manage supplier information
- Update purchase request statuses
- Coordinate with warehouse for delivery receipt

---

## 2. Dashboard Overview

The Purchaser Dashboard (`/purchaser`) is your daily workspace for procurement activities.

### 2.1. KPI Cards

Four key metrics at the top:

| KPI | Color | Description |
|---|---|---|
| **Active Requests** | Blue | Purchase requests in pending/approved/sent status |
| **Pending Approval** | Yellow | Requests waiting for PM approval |
| **In Transit** | Purple | Deliveries currently on the way |
| **Deficit Materials** | Red | Materials below minimum stock threshold |

### 2.2. Tabs

| Tab | Purpose |
|---|---|
| **Active** | Purchase requests that need action (pending, approved, sent) |
| **Deliveries** | Delivery tracking for sent orders |
| **Deficits** | Materials currently below minimum stock |
| **Suppliers** | Supplier contact information and management |

---

## 3. Active Purchase Requests

### 3.1. Request Lifecycle

Purchase requests follow this lifecycle:

| Status | Meaning | Your Action |
|---|---|---|
| **Pending** | Created, waiting for approval | Wait or follow up with PM |
| **Approved** | PM approved the purchase | Contact supplier, place the order |
| **Sent** | Order placed with supplier | Track delivery |
| **Delivered** | Materials received at warehouse | Verify with warehouse staff |
| **Cancelled** | Request cancelled | No action needed |

### 3.2. Viewing Request Details

For each purchase request, you see:

| Field | Description |
|---|---|
| Material | Material name and code |
| Quantity | Amount requested |
| Unit | Unit of measurement |
| Current Stock | Current balance in warehouse |
| Min Balance | Minimum threshold |
| Deficit | How much below minimum |
| Status | Current request status |
| Requested By | Who created the request |
| Date | When created |
| Notes | Additional context |

### 3.3. Updating Request Status

1. Find the request in the **Active** tab.
2. Click the status update button.
3. Select the new status:
   - **Approved** -> **Sent**: After placing the order with the supplier
   - **Sent** -> **Delivered**: After warehouse confirms receipt
4. Add notes (supplier order number, expected delivery date, etc.).
5. Confirm.

### 3.4. Deleting a Request

If a request is no longer needed:

1. Click the delete button on the request.
2. Confirm the deletion.
3. Add a reason (optional but recommended).

> **Note**: Only pending requests can be deleted. Approved or sent requests must be cancelled instead.

---

## 4. Deliveries Management

### 4.1. Delivery Tracking

The **Deliveries** tab shows all orders that have been sent to suppliers:

| Column | Description |
|---|---|
| Material | What was ordered |
| Supplier | Who the order was placed with |
| Quantity | Amount ordered |
| Order Date | When the order was placed |
| Expected Date | Expected delivery date |
| Status | In Transit / Delivered / Overdue |

### 4.2. Overdue Deliveries

Deliveries past their expected date are highlighted in red. When you see an overdue delivery:

1. Contact the supplier for a status update
2. Update the expected delivery date in the system
3. If the material is critical (blocks production), notify the PM immediately

### 4.3. Confirming Receipt

When a delivery arrives at the warehouse:

1. Coordinate with warehouse staff to verify quantities
2. Update the purchase request status to "Delivered"
3. Warehouse staff will receive the material into inventory

---

## 5. Material Deficits

### 5.1. Understanding Deficits

The **Deficits** tab shows all materials where the current stock is below the minimum threshold. For each deficit material:

| Column | Description |
|---|---|
| Material | Name and code |
| Current Balance | What's in stock now |
| Min Balance | Threshold that triggered the alert |
| Deficit Amount | How much below minimum |
| Unit | Unit of measurement |
| Has Active Request | Whether a purchase request already exists |

### 5.2. Prioritizing Purchases

Not all deficits are equally urgent. Prioritize based on:

1. **Production impact**: Does the deficit block any active positions?
2. **Lead time**: How long does the supplier take to deliver?
3. **Deficit size**: How far below minimum is the stock?
4. **Material criticality**: Can production continue without this material?

> **Tip**: Check the PM dashboard's Blocking tab to see which positions are blocked by material shortages. These correspond to your most urgent purchases.

### 5.3. Creating Purchase Requests from Deficits

1. View a deficit material.
2. If no active request exists, click **Create Request**.
3. Enter the quantity to order (consider ordering above minimum to buffer against future needs).
4. Add notes (preferred supplier, urgency level).
5. Submit -- the request goes to PM for approval.

---

## 6. Supplier Management

### 6.1. Viewing Suppliers

The **Suppliers** tab lists all registered suppliers:

| Column | Description |
|---|---|
| Name | Supplier company name |
| Contact | Primary contact person |
| Phone | Contact phone number |
| Email | Contact email |
| Materials | Which materials this supplier provides |
| Rating | Performance rating (if available) |

### 6.2. Supplier Selection

When placing an order, consider:

- **Price**: Compare quotes from multiple suppliers
- **Lead time**: How fast can they deliver?
- **Quality**: Past experience with material quality
- **Reliability**: Do they deliver on time?
- **Minimum order**: Does the supplier have minimum order requirements?

### 6.3. Supplier Information

Navigate to `/admin/suppliers` to view the full supplier directory. As a Purchaser, you can view supplier details but cannot modify them -- contact the Administrator to update supplier information.

---

## 7. Cost Tracking

### 7.1. Purchase Costs

For each purchase request, track:

- **Unit price**: Cost per unit of material
- **Total cost**: Quantity x unit price
- **Shipping cost**: If applicable
- **Payment terms**: When payment is due

### 7.2. Budget Awareness

Monitor purchase spending against budget:

- Review monthly spending trends
- Compare unit prices across suppliers
- Identify opportunities for bulk purchasing
- Flag unusual price increases to management

> **Tip**: If a supplier raises prices significantly, document the increase and notify the PM/CEO. The system tracks financial entries, and unexplained cost spikes will be flagged.

---

## 8. Purchase Consolidation

### 8.1. What Is Consolidation?

The Admin Settings page includes a **Purchase Consolidation** feature that groups small purchase requests for the same supplier into a single order. This reduces shipping costs and simplifies logistics.

### 8.2. How It Works

1. The system analyzes pending purchase requests
2. Groups requests by supplier
3. Suggests consolidated orders
4. You review and approve the consolidation

### 8.3. When to Consolidate

Consolidate when:

- Multiple materials come from the same supplier
- No individual item is urgently needed
- Shipping costs are significant relative to material cost
- Supplier offers volume discounts

Do NOT consolidate when:

- A material is critically needed (blocks production)
- Supplier has minimum order requirements that are already met
- Different materials have very different lead times

---

## 9. Telegram Bot Commands

| Command | Description |
|---|---|
| `/start` | Initialize bot connection |
| `/stock` | Check material stock levels |
| `/mystats` | View your statistics |
| `/help` | List all available commands |

### 9.1. Automatic Notifications

As Purchaser, you receive notifications for:

- New purchase requests created
- Requests approved by PM (ready for you to place)
- Low stock alerts for critical materials
- Delivery reminders for overdue shipments
- Morning briefing with procurement summary

### 9.2. Factory-Specific Alerts

If your factory has a Telegram purchaser chat configured, you receive alerts directly in that chat group. This keeps procurement communication centralized.

---

## 10. Navigation Reference

| Page | URL | Purpose |
|---|---|---|
| Purchaser Dashboard | `/purchaser` | Main dashboard with requests, deliveries, deficits, suppliers |
| Suppliers Directory | `/admin/suppliers` | Full supplier list (view only) |
| Settings | `/settings` | Personal account settings |

---

## 11. Tips and Best Practices

> **Stay ahead of deficits**: Don't wait for materials to hit zero before ordering. Review the Deficits tab daily and place orders when materials approach the minimum threshold.

> **Communicate lead times**: When you know a delivery will be late, update the system immediately. This allows the PM to adjust the production schedule before positions get blocked.

> **Build supplier relationships**: Good supplier relationships mean faster deliveries, better prices, and priority treatment when materials are scarce. Visit key suppliers periodically.

> **Track price trends**: Keep notes on price changes from suppliers. If prices are rising, consider ordering larger quantities at current prices (if storage allows and the material doesn't expire).

> **Consolidate smartly**: Combine orders when it saves money, but never at the expense of blocking production. A small shipping cost is always cheaper than idle kiln time.

> **Document everything**: Keep records of all supplier communications, price quotes, and delivery promises. The system's notes field is your paper trail.

> **Morning routine**: Start each day by checking: (1) New approved requests to place, (2) Overdue deliveries to follow up, (3) Deficit materials that need attention.

> **Coordinate with warehouse**: After placing an order, tell the warehouse team what to expect and when. This ensures smooth receiving when the delivery arrives.

---

*This guide covers Moonjar PMS v1.0 features for the Purchaser role. For technical support, contact the system administrator.*
