# Owner Guide -- Moonjar PMS

> Version: 1.0 | Date: 2026-04-06
> Moonjar Production Management System

---

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Dashboard Overview](#2-dashboard-overview)
3. [Financial Summary](#3-financial-summary)
4. [Operational KPIs](#4-operational-kpis)
5. [Performance Trends](#5-performance-trends)
6. [OPEX Breakdown](#6-opex-breakdown)
7. [Factory Leaderboard](#7-factory-leaderboard)
8. [Factory Performance Matrix](#8-factory-performance-matrix)
9. [Critical Positions & Deficits](#9-critical-positions--deficits)
10. [Access to All Roles](#10-access-to-all-roles)
11. [Export & Reporting](#11-export--reporting)
12. [User & Factory Management](#12-user--factory-management)
13. [System Health & Diagnostics](#13-system-health--diagnostics)
14. [Telegram Bot](#14-telegram-bot)
15. [Strategic Decision Framework](#15-strategic-decision-framework)
16. [Navigation Reference](#16-navigation-reference)
17. [Tips and Best Practices](#17-tips-and-best-practices)

---

## 1. Getting Started

### 1.1. Logging In

1. Open the Moonjar PMS dashboard in your browser.
2. Sign in using one of the available methods:
   - **Google OAuth** -- click "Sign in with Google"
   - **Email and password** -- enter your credentials and click "Login"
3. After authentication, the system detects your Owner role and redirects you to `/owner` -- the Owner dashboard.

### 1.2. Owner Role Privileges

As Owner, you have the **highest level of access** in the system:

- Full access to all dashboards (Owner, CEO, PM, QM, Warehouse, Sorter, Purchaser, Admin)
- Financial data visibility (revenue, expenses, margins, OPEX, CAPEX)
- User and factory management
- All export capabilities
- Strategic analytics and trend data
- System health monitoring

### 1.3. Period Selection

The Owner dashboard features a **Period Selector** (top right) with options:

- **Week** -- last 7 days
- **Month** -- last 30 days (default)
- **Quarter** -- last 90 days
- **Year** -- last 365 days

All financial and operational data on the dashboard adjusts to the selected period.

---

## 2. Dashboard Overview

The Owner Dashboard (`/owner`) provides a strategic, financial-first view of the business.

### 2.1. Layout

1. **Header** -- title, period selector, Export Excel button
2. **Financial Summary Cards** -- revenue, expenses, margin, output, orders
3. **Operational KPI Cards** -- on-time, defect rate, kiln utilization, OEE
4. **Financial Block** -- detailed financial breakdown
5. **Performance Trends** -- 6-month trend charts
6. **OPEX Breakdown** -- expense category analysis
7. **Factory Leaderboard** -- competitive ranking of factories
8. **Factory Performance Matrix** -- detailed comparison table
9. **Critical Positions** -- positions at risk
10. **Material Deficits** -- materials blocking production

---

## 3. Financial Summary

### 3.1. Financial KPI Cards

Five financial cards across the top:

| KPI | Description |
|---|---|
| **Revenue** | Total revenue for the selected period (USD) |
| **Expenses** | OPEX + CAPEX combined |
| **Profit Margin** | Margin percentage and absolute amount |
| **Output m²** | Total production output with cost per m² |
| **Orders Completed** | Completed orders with in-progress count |

### 3.2. Financial Block

A detailed financial breakdown component showing:

- Revenue by source
- OPEX categories (materials, labor, utilities, maintenance)
- CAPEX items (equipment, facility improvements)
- Margin analysis
- Period-over-period comparison

### 3.3. Key Financial Ratios

| Ratio | Good | Warning | Action Needed |
|---|---|---|---|
| Profit Margin | > 30% | 15-30% | < 15% |
| Cost per m² | Decreasing | Stable | Increasing |
| OPEX to Revenue | < 60% | 60-75% | > 75% |

---

## 4. Operational KPIs

### 4.1. KPI Cards

Four operational KPI cards:

| KPI | Target | Description |
|---|---|---|
| **On-Time** | > 90% | Percentage of positions delivered on schedule |
| **Defect Rate** | < 3% | Percentage of defective products |
| **Kiln Util.** | > 75% | Kiln capacity utilization |
| **OEE** | > 85% | Overall Equipment Effectiveness |

### 4.2. OEE Breakdown

OEE (Overall Equipment Effectiveness) combines three factors:

- **Availability** -- uptime vs. planned production time
- **Performance** -- actual speed vs. maximum speed
- **Quality** -- good products vs. total products

OEE = Availability x Performance x Quality

---

## 5. Performance Trends

### 5.1. Trend Charts

Four 6-month trend charts provide historical context:

| Chart | What It Shows |
|---|---|
| **Output Trend** | Monthly production output in m² |
| **On-Time Rate** | Monthly on-time delivery percentage |
| **Defect Rate Trend** | Monthly defect rate progression |
| **OEE Trend** | Monthly OEE score |

### 5.2. Reading Trends

- **Upward trend in Output + On-Time**: Business is growing efficiently
- **Rising Defect Rate**: Quality problems -- investigate root causes
- **Falling OEE with stable Output**: Equipment issues, maintenance needed
- **Declining On-Time with high Kiln Util.**: Capacity constraint, consider expansion

> **Tip**: Trends are more meaningful than snapshots. A single bad week is noise; a declining 3-month trend requires action.

---

## 6. OPEX Breakdown

### 6.1. OPEX Categories

The OPEX Breakdown Chart shows expenses categorized by type:

- **Materials** -- raw materials, glazes, engobe, chemicals
- **Labor** -- salaries, overtime, BPJS contributions
- **Utilities** -- electricity, gas, water
- **Maintenance** -- equipment repair, kiln shelf replacements
- **Logistics** -- shipping, delivery costs
- **Other** -- miscellaneous operational expenses

### 6.2. Analyzing OPEX

Look for:

- Categories growing faster than revenue (cost creep)
- Sudden spikes in maintenance costs (equipment failure)
- Material costs increasing without corresponding output increase
- Labor costs rising without headcount change (excessive overtime)

---

## 7. Factory Leaderboard

### 7.1. Competitive Ranking

The Factory Leaderboard component ranks factories by overall performance score. This creates healthy competition between factory teams.

### 7.2. Scoring Factors

Factories are scored on:

- Production output (m²)
- On-time delivery rate
- Defect rate (lower is better)
- OEE
- Kiln utilization

---

## 8. Factory Performance Matrix

### 8.1. Comparison Table

A detailed table comparing all factories:

| Column | Description |
|---|---|
| Factory | Name and location |
| Output m² | Production volume (green = highest) |
| Quality (Defect %) | Defect rate (green = lowest) |
| Efficiency (OEE) | Equipment effectiveness (green = highest) |
| Kiln Util. | Kiln utilization percentage |
| On-Time % | Delivery reliability |
| Active Orders | Current workload |

### 8.2. Color Coding

- **Green**: Best performer or above target
- **Yellow**: Needs attention
- **Red**: Below acceptable level

---

## 9. Critical Positions & Deficits

### 9.1. Critical Positions

Positions that are:

- Overdue (past deadline)
- Severely delayed (> 48 hours behind)
- At risk of missing deadline (buffer health in red zone)

### 9.2. Material Deficits

Materials where current stock is below minimum threshold, potentially blocking production. For each deficit:

- Material name and current balance
- How much below minimum
- Whether a purchase request exists

---

## 10. Access to All Roles

### 10.1. Dashboard Access

As Owner, you can navigate to any role's dashboard:

| Dashboard | URL | What You See |
|---|---|---|
| Owner | `/owner` | Strategic overview (you are here) |
| CEO | `/ceo` | Operational overview, cross-factory |
| PM | `/manager` | Day-to-day production |
| Quality | `/quality` | QC queue, blocks, problem cards |
| Warehouse | `/warehouse` | Inventory, deliveries |
| Sorter/Packer | `/sorter-packer` | Sorting, packing operations |
| Purchaser | `/purchaser` | Procurement, suppliers |
| Admin | `/admin` | System configuration |

### 10.2. When to Use Each Dashboard

| Situation | Dashboard |
|---|---|
| Weekly strategic review | Owner |
| Daily operational check | CEO |
| Investigate production delay | PM |
| Understand quality issues | Quality |
| Check material availability | Warehouse |
| Review procurement status | Purchaser |
| System configuration change | Admin |

---

## 11. Export & Reporting

### 11.1. Owner Monthly Export

Click **Export Excel** on the Owner dashboard to download a comprehensive monthly report:

- Financial summary (revenue, expenses, margins)
- Factory comparison data
- Production metrics
- Quality metrics
- Trend data

File format: `owner-report-YYYY-MM.xlsx`

### 11.2. Other Reports

Navigate to `/reports` for additional report types:

- Orders summary
- Kiln utilization
- Production analytics
- Custom date range selection

### 11.3. CEO Daily Export

Also available from the CEO dashboard: `ceo-daily-YYYY-MM-DD.xlsx`

---

## 12. User & Factory Management

### 12.1. User Management

Navigate to `/users` to manage all system users:

- Create and edit user accounts
- Assign roles and factory access
- Activate/deactivate accounts
- Reset passwords

### 12.2. Factory Management

Navigate to `/admin` to manage factories:

- Add new factories
- Configure Telegram integrations per factory
- Activate/deactivate factories
- Set PM cleanup permissions

---

## 13. System Health & Diagnostics

### 13.1. Health Check

The system provides a health endpoint:

```
GET /api/health -> {"status": "ok"}
```

If health returns anything other than "ok", the system has issues that need attention.

### 13.2. Monitoring Points

| Check | How | What to Look For |
|---|---|---|
| API Health | `/api/health` | Should return `{"status":"ok"}` |
| Bot Status | Admin Panel > Telegram Bot | Green dot = connected |
| Active Sessions | Admin Panel > Security > Sessions | No suspicious sessions |
| Audit Log | Admin Panel > Security > Audit | No unauthorized changes |
| Error Rate | Backend logs (Railway) | No repeated 500 errors |

### 13.3. Backup and Data Safety

- Database is managed by Railway with automatic backups
- Audit logs capture all data changes
- Financial entries are never deleted (only soft-deleted)
- Export to Excel provides additional backup for reports

---

## 14. Telegram Bot

### 14.1. Commands

| Command | Description |
|---|---|
| `/start` | Initialize bot connection |
| `/ceoreport` | Get CEO-level daily report |
| `/mystats` | View personal stats |
| `/leaderboard` | View factory/worker leaderboards |
| `/stock` | Check material stock levels |
| `/help` | List all commands |

### 14.2. Notifications You Receive

As Owner, you receive all critical notifications:

- Force unblock events
- Attendance gaps (3+ workers absent)
- Quality anomalies
- New orders from Sales webhook
- Escalated issues

---

## 15. Strategic Decision Framework

### 15.1. Monthly Review Checklist

| Question | Data Source | Action Threshold |
|---|---|---|
| Is the business profitable? | Financial Cards | Margin < 15% |
| Are we producing enough? | Output Trend | Declining 3+ months |
| Is quality acceptable? | Defect Rate Trend | Rising above 5% |
| Are we delivering on time? | On-Time Trend | Below 85% |
| Are costs under control? | OPEX Breakdown | Growing faster than revenue |
| Which factory needs help? | Factory Matrix | OEE below 70% |

### 15.2. Expansion Decision Criteria

Consider adding capacity (new kiln, new factory) when:

- Kiln utilization consistently > 85% across all factories
- Order backlog is growing month-over-month
- On-time rate is dropping despite full utilization
- Profitable orders are being turned down

### 15.3. Cost Reduction Opportunities

| Area | Signal | Approach |
|---|---|---|
| Materials | Cost per m² rising | Negotiate with suppliers, consider alternatives |
| Energy | Utility costs increasing | Optimize kiln schedules (batch similar firings) |
| Quality | Defect rate high | Invest in QC training, update recipes |
| Maintenance | Shelf OPEX increasing | Evaluate higher-quality shelf materials |
| Labor | Overtime excessive | Hire additional workers or improve scheduling |

---

## 16. Navigation Reference

| Page | URL | Purpose |
|---|---|---|
| Owner Dashboard | `/owner` | Strategic financial overview |
| CEO Dashboard | `/ceo` | Operational overview |
| PM Dashboard | `/manager` | Production management |
| QM Dashboard | `/quality` | Quality management |
| Warehouse Dashboard | `/warehouse` | Inventory management |
| Sorter Packer | `/sorter-packer` | Sorting and packing |
| Purchaser | `/purchaser` | Procurement |
| Admin Panel | `/admin` | System configuration |
| Users | `/users` | User management |
| Reports | `/reports` | Analytics and reports |
| Gamification | `/gamification` | Points and leaderboards |
| Tablo | `/tablo` | Production display |
| Settings | `/settings` | Personal settings |

---

## 17. Tips and Best Practices

> **Financial first**: As Owner, start with the financial summary. Revenue, margins, and cost per m² are your north star metrics. Everything else supports these.

> **Weekly, not daily**: The Owner dashboard is designed for weekly or bi-weekly reviews. For daily monitoring, use the CEO dashboard. Over-checking leads to reactive decisions.

> **Trends over snapshots**: A single week's data can be misleading. Use the period selector to look at monthly and quarterly trends before making strategic decisions.

> **Factory leaderboard**: Use the leaderboard to create healthy competition but also to identify which factory needs more support. A consistently last-place factory isn't just underperforming -- it may need resources.

> **Export for board meetings**: The Excel export contains all the data needed for investor or partner updates. Export monthly and keep an archive.

> **Delegate operational issues**: If you see a quality spike or delivery problem on the Owner dashboard, don't solve it yourself. Flag it to the CEO or PM and let them investigate. Your job is to ensure the system works, not to operate it.

> **Monitor the monitors**: Check the Admin Panel periodically to ensure audit logs are being generated, active sessions look normal, and the Telegram bot is connected.

> **Security awareness**: As the highest-privilege account, your credentials are the most valuable target. Use strong passwords, enable Google OAuth, and never share your login.

---

*This guide covers Moonjar PMS v1.0 features for the Owner role. For technical support, contact the system developer.*
