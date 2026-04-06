# CEO Guide -- Moonjar PMS

> Version: 1.0 | Date: 2026-04-06
> Moonjar Production Management System

---

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Dashboard Overview](#2-dashboard-overview)
3. [KPI Cards](#3-kpi-cards)
4. [Production Pipeline Tab](#4-production-pipeline-tab)
5. [Cross-Factory Tab](#5-cross-factory-tab)
6. [Tasks & Issues Tab](#6-tasks--issues-tab)
7. [Kilns & Schedule Tab](#7-kilns--schedule-tab)
8. [Kiln Shelf OPEX Analytics](#8-kiln-shelf-opex-analytics)
9. [PM Cleanup Permissions](#9-pm-cleanup-permissions)
10. [Employee Management](#10-employee-management)
11. [Financial Reports](#11-financial-reports)
12. [Gamification Oversight](#12-gamification-oversight)
13. [Export & Reporting](#13-export--reporting)
14. [Telegram Bot Commands](#14-telegram-bot-commands)
15. [Decision-Making with Data](#15-decision-making-with-data)
16. [Navigation Reference](#16-navigation-reference)
17. [Tips and Best Practices](#17-tips-and-best-practices)

---

## 1. Getting Started

### 1.1. Logging In

1. Open the Moonjar PMS dashboard in your browser.
2. Sign in using one of the available methods:
   - **Google OAuth** -- click "Sign in with Google"
   - **Email and password** -- enter your credentials and click "Login"
3. After authentication, the system detects your CEO role and redirects you to `/ceo` -- the CEO dashboard.

### 1.2. Factory Selection

As CEO, you have access to **all factories** simultaneously:

- **All Factories mode** (default): The dashboard shows aggregated data across every factory.
- **Single factory mode**: Use the factory selector dropdown (top right) to focus on one factory.

> **Tip**: Start each day in "All Factories" mode to see the full picture, then drill into individual factories when investigating issues.

### 1.3. Role Capabilities

As CEO, you can:

- View production pipeline, buffer health, and critical positions across all factories
- Compare factory performance side by side
- Review and manage blocking tasks and change requests
- Monitor kiln schedules and utilization
- Control PM cleanup permissions per factory
- View kiln shelf lifecycle and OPEX analytics
- Export daily CEO reports to Excel
- Access employee management across all factories
- Receive Telegram notifications for critical events

---

## 2. Dashboard Overview

The CEO Dashboard (`/ceo`) is your strategic command center. It provides a high-level view of operations with the ability to drill down into specifics.

### 2.1. Layout

The dashboard consists of:

1. **Header** -- page title, factory selector, and Export Excel button
2. **KPI Cards** -- six key performance indicators at a glance
3. **Tabs** -- four main sections (Production Pipeline, Cross-Factory, Tasks & Issues, Kilns & Schedule)
4. **Kiln Shelf OPEX widget** -- lifecycle analytics for kiln shelves
5. **PM Cleanup Permissions** -- temporary permission toggles

### 2.2. Error Handling

If the analytics API or factories API fails, a red error banner appears at the top:

> "Error loading dashboard data. Analytics API failed."

Try refreshing the page. If the error persists, check backend logs or contact the system administrator.

---

## 3. KPI Cards

Six KPI cards are displayed across the top of the dashboard:

| KPI | Description | What to Watch |
|---|---|---|
| **Active Orders** | Orders currently in production (of total) | Growing backlog may indicate capacity issues |
| **Output m²** | Square meters produced in the last 30 days | Compare against target capacity |
| **On-Time** | Percentage of positions delivered on schedule | Below 85% requires investigation |
| **Defect Rate** | Percentage of defective items | Above 5% is a quality red flag |
| **Kiln Util.** | Kiln utilization percentage | Below 70% means kilns are underused |
| **OEE** | Overall Equipment Effectiveness | World-class target is 85%+ |

> **Key insight**: If On-Time is dropping while Kiln Utilization is high, the bottleneck is likely in pre-firing or post-firing stages, not the kilns themselves.

---

## 4. Production Pipeline Tab

This is the default tab, showing the production flow and current state.

### 4.1. Production Pipeline Chart

A funnel visualization showing how many positions are at each stage:

- Planned → In Progress → Glazing → Firing → Sorting → QC → Ready → Shipped

This helps you see where work is accumulating and identify bottlenecks visually.

### 4.2. Daily Output Chart

A 30-day bar chart showing daily production output in square meters. Look for:

- Consistent daily output (good)
- Sudden drops (investigate -- kiln maintenance? material shortage?)
- Weekend dips (expected if factory doesn't work weekends)

### 4.3. Buffer Health (TOC)

The Theory of Constraints buffer health table shows positions by their buffer status:

| Zone | Condition | Action |
|---|---|---|
| **Green** | delta >= -5% | On track, no action needed |
| **Yellow** | -20% <= delta < -5% | Monitor closely, consider priority adjustment |
| **Red** | delta < -20% or deadline passed | Urgent: escalate to Production Manager |

### 4.4. Critical Positions

A table listing positions that need attention -- overdue, stalled, or at risk of missing deadlines. Sorted by urgency.

### 4.5. Material Deficits

Shows materials with stock below minimum balance, which may block production. If you see persistent deficits:

1. Check if purchase requests have been created
2. Verify supplier delivery timelines with the Purchaser
3. Consider whether production priorities need rebalancing

### 4.6. Activity Feed

A real-time feed of system events (auto-refreshes every 30 seconds):

- New orders received from Sales
- Positions advancing through stages
- Quality issues detected
- Material transactions
- Task completions

---

## 5. Cross-Factory Tab

### 5.1. Factory Performance Cards

Visual comparison cards for each factory showing key metrics at a glance:

- Output in m²
- Active orders
- Kiln utilization
- Defect rate
- On-time delivery rate
- OEE score

### 5.2. Detailed Comparison Table

A comprehensive table comparing all factories side by side:

| Column | Description |
|---|---|
| Factory | Name and location |
| Active Orders | Orders currently in production |
| Output m² | Production output |
| Kiln Util. | Kiln utilization percentage |
| Defect % | Defect rate (red if worst, green if best) |
| On-Time % | On-time delivery rate (green if best) |
| OEE % | Overall Equipment Effectiveness |

> **Tip**: Use this tab during weekly management meetings to compare factory performance and set improvement targets.

---

## 6. Tasks & Issues Tab

### 6.1. Summary Cards

Four quick-view cards at the top:

- **Blocking Tasks** -- tasks that prevent positions from advancing
- **Overdue Positions** -- positions past their deadline
- **Pending Change Requests** -- modification requests from Sales awaiting review
- **Total Open Tasks** -- all active tasks across factories

### 6.2. Blocking Tasks List

Shows all tasks with `blocking = true` that are currently preventing production progress. For each task:

- Task type and description
- Which position/order it blocks
- Assigned role
- Creation date and age

### 6.3. Change Requests

Sales change requests that modify existing orders. These require Production Manager approval but the CEO can monitor the queue and intervene if needed.

### 6.4. Overdue Positions

Positions that have passed their planned completion date. Color-coded by severity:

- **< 24h overdue**: Yellow
- **24-48h overdue**: Orange
- **> 48h overdue**: Red

---

## 7. Kilns & Schedule Tab

### 7.1. Kiln Status Overview

Shows all kilns across factories with their current status:

| Status | Color | Meaning |
|---|---|---|
| `idle` | Gray | Available for loading |
| `loading` | Blue | Currently being loaded |
| `firing` | Orange | Active firing in progress |
| `cooling` | Cyan | Cooling down after firing |
| `unloading` | Yellow | Being unloaded |
| `maintenance` | Red | Under maintenance, unavailable |

### 7.2. Firing Schedule

Calendar view of upcoming and recent firings. Shows:

- Kiln name and capacity
- Scheduled firing date and time
- Batch contents (positions, total m²)
- Firing profile being used

> **Tip**: If a kiln has been idle for more than 2 days, check with the PM whether there are batches ready to fire or if there's a blocking issue.

---

## 8. Kiln Shelf OPEX Analytics

A dedicated analytics widget at the bottom of the dashboard providing lifecycle and cost data for kiln shelves.

### 8.1. Overview KPIs

| KPI | Description |
|---|---|
| **Active Shelves** | Number of shelves currently in use (with total area in m²) |
| **Avg Lifespan** | Average number of firing cycles before write-off |
| **Cost / Cycle** | Average cost per firing cycle in IDR |
| **Total Investment** | Total money invested in shelves (with written-off amount) |

### 8.2. Projected Replacements

An amber-colored alert showing:

- Number of shelf replacements expected in the next **30 days** with estimated cost
- Number of shelf replacements expected in the next **90 days** with estimated cost

Use this for budgeting and procurement planning.

### 8.3. Nearing End of Life

A list of shelves that have used 80%+ of their maximum firing cycles, sorted by urgency:

- Shelf name and kiln location
- Progress bar showing cycle usage percentage
- Current cycles / maximum cycles

### 8.4. By Material Breakdown

Shows shelf statistics grouped by material type:

- **SiC** (Silicon Carbide) -- 200 max cycles default
- **Cordierite** -- 150 max cycles default
- **Mullite** -- 300 max cycles default
- **Alumina** -- 250 max cycles default

For each material: active count, written-off count, average lifespan.

### 8.5. Monthly Write-off Cost Trend

A 6-month bar chart showing monthly shelf write-off costs in IDR. Useful for:

- Tracking OPEX trends
- Identifying unexpected cost spikes
- Planning shelf procurement budget

---

## 9. PM Cleanup Permissions

A temporary feature allowing the CEO to grant or revoke Production Managers' ability to delete data:

| Permission | Description |
|---|---|
| **PM can delete tasks** | Allow PM to delete tasks |
| **PM can delete positions** | Allow PM to delete order positions |
| **PM can delete orders** | Allow PM to delete entire orders |

> **Warning**: These are destructive permissions. Enable them only when PMs need to clean up test data or correct mistakes. Disable them for normal operations.

This card appears per factory. Toggle checkboxes to enable/disable.

---

## 10. Employee Management

Navigate to `/ceo/employees` to manage employees across all factories.

### 10.1. Features

- View all employees across all factories in one place
- Filter by factory, role, and active status
- See attendance records
- View payroll data (Indonesian law: PPh 21, BPJS, overtime per PP 35/2021)

### 10.2. Payroll Overview

The CEO employee view includes payroll aggregation:

- Total payroll cost per factory
- Breakdown by role
- Overtime costs
- Tax and BPJS contributions

> **Important**: Salary data is access-controlled. Only CEO and Owner roles can view payroll information across all factories.

---

## 11. Financial Reports

### 11.1. Reports Page

Navigate to `/reports` for comprehensive analytics:

- **Orders Summary** -- order counts, completion rates, lead times
- **Kiln Utilization** -- firing frequency, capacity usage, idle time
- **Production Analytics** -- output trends, efficiency metrics

### 11.2. CEO Daily Export

Click the **Export Excel** button on the CEO dashboard to download a comprehensive daily report including:

- All KPIs for the current day
- Factory comparison data
- Active orders summary
- Material deficit list
- Task summary

The export file is named `ceo-daily-YYYY-MM-DD.xlsx`.

---

## 12. Gamification Oversight

### 12.1. Points System

Workers earn points through accurate work:

| Accuracy | Points |
|---|---|
| +/- 1% | 10 points |
| +/- 3% | 7 points |
| +/- 5% | 5 points |
| +/- 10% | 3 points |
| Other | 1 point |

Additional points:
- **Photo verification bonus**: +2 points per verified photo

Points accumulate yearly and reset on January 1.

### 12.2. Leaderboards

Monthly leaderboards visible at `/gamification`. As CEO, you can:

- View leaderboards for all factories
- See individual worker performance
- Monitor achievement badges

### 12.3. Daily Challenges

The system generates daily challenges for workers. As CEO, you can view challenge completion rates and overall engagement metrics.

### 12.4. Force Unblock Monitoring

When a PM uses Smart Force Unblock, you receive a Telegram notification. Monitor these closely -- frequent force unblocks may indicate systemic issues.

---

## 13. Export & Reporting

### 13.1. Available Exports

| Export | Format | Access |
|---|---|---|
| CEO Daily Report | Excel (.xlsx) | CEO Dashboard > Export Excel |
| Order Details | PDF | Order Detail Page > Export |
| Production Schedule | PDF | Schedule Page > Export |

### 13.2. Automated Reports

The Telegram bot sends automated reports:

- **Morning Briefing** (daily): Yesterday's results, today's plan, blocking issues
- **Evening Summary** (6 PM): Daily production results
- **Attendance Alerts**: Notification when 3+ attendance gaps detected

---

## 14. Telegram Bot Commands

The Telegram bot (`@LeanOpsAI_bot`) provides CEO-specific commands:

| Command | Description |
|---|---|
| `/start` | Initialize bot connection |
| `/ceoreport` | Get a comprehensive CEO daily report |
| `/mystats` | View personal interaction statistics |
| `/leaderboard` | View worker leaderboard |
| `/stock` | Check material stock levels |
| `/help` | List all available commands |

### 14.1. Automatic Notifications

As CEO, you automatically receive:

- **Force unblock alerts** -- when PM uses Smart Force Unblock on any position
- **Attendance gaps** -- when 3+ workers are absent
- **Quality anomalies** -- when defect rates spike above thresholds
- **Order intake** -- new orders received from Sales webhook

### 14.2. Night Escalation

Critical issues detected outside working hours follow the escalation path:

1. **MORNING** -- notification queued for morning delivery
2. **REPEAT** -- send reminder if not acknowledged
3. **CALL** -- escalate to phone call if still unacknowledged

---

## 15. Decision-Making with Data

### 15.1. Daily Review Checklist

Every morning, review these items:

1. **KPI Cards** -- any metric below target?
2. **Blocking Tasks count** -- anything stalled?
3. **Material Deficits** -- any production at risk?
4. **Buffer Health** -- any red zone positions?
5. **Kiln Schedule** -- any idle kilns?

### 15.2. Weekly Analysis

| Question | Where to Find Answer |
|---|---|
| Which factory performs best? | Cross-Factory tab > Comparison table |
| Are deadlines being met? | KPI: On-Time rate |
| Is quality improving? | KPI: Defect Rate + Quality trends |
| Are kilns used efficiently? | Kilns tab + KPI: Kiln Utilization |
| What's the shelf replacement budget? | Kiln Shelf OPEX widget > Projections |

### 15.3. Key Ratios to Monitor

| Ratio | Good | Warning | Critical |
|---|---|---|---|
| On-Time Delivery | > 90% | 80-90% | < 80% |
| Defect Rate | < 3% | 3-5% | > 5% |
| Kiln Utilization | > 75% | 60-75% | < 60% |
| OEE | > 85% | 70-85% | < 70% |

### 15.4. When to Intervene

Intervene directly when:

- **Red buffer zone** positions exceed 20% of active work
- **Kiln utilization** drops below 60% for more than 3 days
- **Material deficits** block 5+ positions simultaneously
- **Force unblocks** occur more than 3 times per week at one factory

---

## 16. Navigation Reference

| Page | URL | Purpose |
|---|---|---|
| CEO Dashboard | `/ceo` | Main command center |
| CEO Employees | `/ceo/employees` | All employees and payroll across factories |
| Reports | `/reports` | Production and analytics reports |
| Gamification | `/gamification` | Points, leaderboards, achievements |
| Order Details | `/orders/:id` | Detailed view of a specific order |
| Tablo | `/tablo` | Full-screen production display board |
| Settings | `/settings` | Personal account settings |

---

## 17. Tips and Best Practices

> **Morning routine**: Open the CEO dashboard in "All Factories" mode. Check the KPI cards first, then scan the Activity Feed for overnight events. Switch to individual factories only when investigating specific issues.

> **Weekly cadence**: Export the CEO daily report every Friday. Compare the week's data against the previous week. Look for trends, not just snapshots.

> **Factory comparison**: When one factory consistently underperforms, drill into its specific metrics. Common root causes: material supply issues, kiln maintenance backlog, workforce gaps.

> **Shelf OPEX**: Review the 30-day projection weekly. Place shelf orders at least 2 weeks before projected replacement dates to avoid production downtime.

> **Telegram integration**: Keep the Telegram bot active. The force unblock notifications and attendance alerts provide critical early warnings that may not be visible in the dashboard.

> **Data-driven decisions**: Never base decisions on a single day's data. Use the Export Excel feature to track trends over weeks and months. Short-term spikes (both positive and negative) are usually noise, not signal.

---

*This guide covers Moonjar PMS v1.0 features for the CEO role. For technical support, contact the system administrator.*
