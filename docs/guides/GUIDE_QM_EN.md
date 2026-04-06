# Quality Manager (QM) Guide -- Moonjar PMS

> Version: 1.0 | Date: 2026-04-06
> Moonjar Production Management System

---

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Dashboard Overview](#2-dashboard-overview)
3. [QC Queue](#3-qc-queue)
4. [Pre-Kiln QC Checklist](#4-pre-kiln-qc-checklist)
5. [Final QC Checklist](#5-final-qc-checklist)
6. [QM Blocks](#6-qm-blocks)
7. [Problem Cards](#7-problem-cards)
8. [Defect Identification & Classification](#8-defect-identification--classification)
9. [Defect Coefficient Matrix](#9-defect-coefficient-matrix)
10. [Grinding Decisions](#10-grinding-decisions)
11. [Quality Photos & Analysis](#11-quality-photos--analysis)
12. [Working with Production Manager](#12-working-with-production-manager)
13. [Kiln Inspections](#13-kiln-inspections)
14. [Telegram Bot Commands](#14-telegram-bot-commands)
15. [Reports and Analytics](#15-reports-and-analytics)
16. [Navigation Reference](#16-navigation-reference)
17. [Tips and Best Practices](#17-tips-and-best-practices)

---

## 1. Getting Started

### 1.1. Logging In

1. Open the Moonjar PMS dashboard in your browser.
2. Sign in using one of the available methods:
   - **Google OAuth** -- click "Sign in with Google"
   - **Email and password** -- enter your credentials and click "Login"
3. After authentication, the system detects your role and redirects you to `/quality` -- the Quality Manager dashboard.

### 1.2. Factory Selection

When you log in, the system checks your factory assignments:

- **One factory**: Auto-selected, no dropdown visible.
- **Multiple factories**: A factory selector dropdown appears in the top-right corner.

> **Important**: Quality checks are factory-specific. Always verify you have the correct factory selected before performing inspections.

### 1.3. Role Capabilities

As Quality Manager, you can:

- Perform Pre-Kiln and Final QC inspections
- Create and resolve QM blocks on positions
- Create and manage problem cards
- Classify defects and determine corrective actions
- Make grinding decisions on defective products
- Participate in kiln inspections
- Upload and review quality photos

---

## 2. Dashboard Overview

The QM Dashboard (`/quality`) is organized with KPI cards at the top and a tabbed interface below.

### 2.1. KPI Cards

Four key metrics displayed across the top:

| KPI | Color | Description |
|---|---|---|
| **Pending QC** | Orange | Positions waiting for quality check |
| **Blocked** | Red | Positions currently blocked by QM |
| **Problem Cards** | Yellow | Open problem cards requiring action |
| **Today's Checks** | Green | Number of inspections completed today |

### 2.2. Tabs

| Tab | Purpose |
|---|---|
| **QC Queue** | Positions ready for quality inspection |
| **QM Blocks** | Active quality blocks on positions |
| **Problem Cards** | Issue tracking and resolution |

---

## 3. QC Queue

### 3.1. Overview

The QC Queue shows all positions that have reached a quality checkpoint stage. These are positions waiting for your inspection.

### 3.2. Position Information

For each position in the queue, you see:

| Field | Description |
|---|---|
| Order Number | Parent order reference |
| Color | Product color/glaze |
| Size | Product dimensions |
| Collection | Product collection |
| Quantity | Number of pieces |
| Stage | Current production stage |
| Status | Current position status |

### 3.3. Performing a Quality Check

1. Click on a position in the QC Queue.
2. The **Quality Check Dialog** opens with the full checklist.
3. Go through each checklist item (see sections 4 and 5 for details).
4. Mark each item as Pass or Fail.
5. For failed items, add notes describing the issue.
6. Upload photos if needed (especially for defects).
7. Submit the inspection result:
   - **Pass** -- position advances to the next stage
   - **Fail** -- position gets blocked or sent to corrective action

### 3.4. Bulk Operations

When multiple positions from the same batch share identical quality characteristics, you can:

1. Inspect one position thoroughly
2. Apply the same result to other positions in the batch (if they are identical products)

> **Important**: Never bulk-pass without physically inspecting at least a sample from each position. Document the sample size in notes.

---

## 4. Pre-Kiln QC Checklist

The Pre-Kiln QC is performed **before** tiles are loaded into the kiln. This catches issues that would be permanent after firing.

### 4.1. Checklist Items

| Item | What to Check |
|---|---|
| **Surface Quality** | No cracks, chips, or scratches on the bisque surface |
| **Glaze Application** | Even coverage, correct thickness, no bare spots |
| **Glaze Color Match** | Color matches the approved sample |
| **Edge Quality** | Clean edges, no chips, proper shape |
| **Thickness** | Within tolerance of specified mm |
| **Dimensions** | Length and width within tolerance |
| **Engobe Layer** | Present and even (if specified) |
| **Stencil Placement** | Pattern correctly positioned (if applicable) |
| **Drying Status** | Fully dried before firing |

### 4.2. Common Pre-Kiln Failures

| Issue | Severity | Typical Action |
|---|---|---|
| Uneven glaze | Medium | Return to glazing stage |
| Wrong color | High | Block and escalate to PM |
| Cracked bisque | High | Reject and write off |
| Wet tiles | Low | Return to drying |
| Wrong stencil | High | Block and verify with PM |

### 4.3. Recording Results

For each checklist item:

1. Select **Pass** (green) or **Fail** (red)
2. For failures, select the defect cause from the dropdown
3. Add descriptive notes
4. Upload a photo showing the defect (recommended for all failures)

---

## 5. Final QC Checklist

The Final QC is performed **after** firing, before the tiles move to sorting and packing.

### 5.1. Checklist Items

| Item | What to Check |
|---|---|
| **Surface Finish** | Smooth, no pinholes, no crawling, no blistering |
| **Color Consistency** | Matches approved sample, no color variation within batch |
| **Glaze Adhesion** | No peeling, flaking, or delamination |
| **Dimensions Post-Firing** | Within shrinkage tolerance |
| **Warping** | Tile lies flat, no bowing or cupping |
| **Edge Chips** | No chips from kiln handling |
| **Cracking** | No firing cracks (dunting, thermal shock) |
| **Crazing** | No fine network of cracks in the glaze |
| **Pattern Quality** | Stencil/silkscreen pattern intact and sharp (if applicable) |

### 5.2. Common Post-Firing Defects

| Defect | Description | Typical Cause |
|---|---|---|
| **Pinholing** | Small holes in glaze surface | Gas escape during firing |
| **Crawling** | Glaze pulls away from surface | Dirty bisque or too-thick glaze |
| **Blistering** | Raised bubbles in glaze | Overfiring or contamination |
| **Dunting** | Cracks from thermal stress | Cooling too fast |
| **Crazing** | Fine crack network | Glaze-body expansion mismatch |
| **Warping** | Tile not flat | Uneven kiln temperature or support |
| **Color shift** | Different from expected color | Temperature deviation or atmosphere |
| **Black coring** | Dark center in cross-section | Underfiring, organic matter not burned out |

### 5.3. Grading

After inspection, assign a quality grade:

| Grade | Description | Action |
|---|---|---|
| **A** | Perfect, meets all specs | Pass to packing |
| **B** | Minor cosmetic issues, still sellable | Pass to packing (mark as B-grade) |
| **C** | Significant issues, needs corrective action | Consider grinding or reject |
| **Reject** | Unusable, does not meet minimum standards | Write off, record defect data |

---

## 6. QM Blocks

### 6.1. What Are QM Blocks?

A QM Block is a hold placed on a position by the Quality Manager. It prevents the position from advancing through production until the quality concern is resolved.

### 6.2. Creating a QM Block

1. From the QC Queue, find the position with a quality concern.
2. Click the **Block** action button.
3. Fill in:
   - **Reason** -- why you are blocking (mandatory)
   - **Category** -- type of quality issue
   - **Photos** -- attach evidence photos (recommended)
4. Submit the block.

The position status changes to include a QM hold, and a blocking task is created.

### 6.3. Resolving a QM Block

1. Go to the **QM Blocks** tab.
2. Find the block you want to resolve.
3. Click **Resolve**.
4. Fill in:
   - **Resolution** -- what was done to fix the issue
   - **Outcome** -- pass (resume production) or reject (write off)
5. Submit the resolution.

### 6.4. Block Types

| Category | Description |
|---|---|
| **Color Mismatch** | Product color doesn't match specification |
| **Surface Defect** | Physical defect on the surface |
| **Dimension Issue** | Size or thickness out of tolerance |
| **Process Deviation** | Production process was not followed correctly |
| **Material Issue** | Raw material quality concern |

---

## 7. Problem Cards

### 7.1. Overview

Problem Cards are a formalized way to track quality issues that require investigation and corrective action. Unlike QM Blocks (which hold specific positions), Problem Cards address systemic issues.

### 7.2. Creating a Problem Card

1. Go to the **Problem Cards** tab.
2. Click **+ Create Problem Card**.
3. Fill in:
   - **Title** -- brief description of the problem
   - **Description** -- detailed explanation
   - **Severity** -- low, medium, high, critical
   - **Category** -- defect type classification
   - **Affected Orders** -- link to specific orders (optional)
4. Submit.

### 7.3. Problem Card Lifecycle

| Status | Description |
|---|---|
| **Open** | Problem identified, investigation not started |
| **Investigating** | Root cause analysis in progress |
| **Corrective Action** | Fix is being implemented |
| **Verification** | Checking that the fix works |
| **Closed** | Problem resolved and verified |

### 7.4. Updating a Problem Card

1. Click on the problem card.
2. Add investigation notes, root cause findings, or corrective actions.
3. Update the status as the investigation progresses.
4. Attach supporting photos or documents.

> **Best practice**: Always document the root cause, not just the symptom. "Glaze too thick" is a symptom. "Spray gun pressure set too high due to worn nozzle" is a root cause.

---

## 8. Defect Identification & Classification

### 8.1. Defect Categories

Defects in the Moonjar PMS are organized hierarchically:

1. **Defect Type** -- broad category (surface, structural, dimensional, aesthetic)
2. **Defect Cause** -- specific cause code with description
3. **Severity** -- low, medium, high, critical

### 8.2. Recording Defects

When you find a defect during QC:

1. Select the defect cause from the system's dropdown list
2. Enter the number of affected pieces
3. Add descriptive notes
4. Upload a photo
5. The system records this against the position and calculates the defect rate

### 8.3. Defect Rate Monitoring

The system tracks defect rates at multiple levels:

- **Per position** -- defect rate for a specific production run
- **Per order** -- aggregate defect rate across all positions in an order
- **Per factory** -- factory-wide defect rate
- **Per glaze** -- defect rate per glaze type (helps identify problematic recipes)

When defect rates exceed configured thresholds, the system:

1. Shows a **DefectAlertBanner** on the PM dashboard
2. Creates an automatic problem card
3. Sends a Telegram notification

---

## 9. Defect Coefficient Matrix

### 9.1. What Is It?

The Defect Coefficient is a 2D matrix that predicts expected defect rates based on two factors:

- **Glaze type** (rows)
- **Product type** (columns)

This replaces the simpler 1D model that only used product size.

### 9.2. How It Works

For each glaze-product combination, the matrix stores an expected defect percentage. For example:

| Glaze \ Product | Tile 10x10 | Tile 15x15 | Tile 20x20 | Sink |
|---|---|---|---|---|
| **Authentic** | 3% | 4% | 5% | 8% |
| **Raku** | 8% | 10% | 12% | 15% |
| **Gold** | 5% | 7% | 9% | 12% |

### 9.3. Usage

The defect coefficient is used to:

1. **Plan overproduction** -- if expected defect rate is 10%, produce 10% extra
2. **Set quality targets** -- compare actual defect rates against expected
3. **Identify anomalies** -- when actual defect rate significantly exceeds expected, the system triggers an alert

### 9.4. Updating Coefficients

As Quality Manager, you can propose updates to the defect coefficient matrix based on actual production data. Changes go through the admin for approval.

> **Tip**: Review and propose coefficient updates quarterly. As the team improves processes, expected defect rates should decrease.

---

## 10. Grinding Decisions

### 10.1. Overview

Navigate to `/manager/grinding` for the Grinding Decisions page. When fired tiles have minor surface defects, grinding can sometimes restore them to sellable condition.

### 10.2. Decision Workflow

1. After Final QC, defective tiles that are candidates for grinding appear in the Grinding Decisions queue.
2. For each tile/batch, evaluate:
   - **Defect type** -- is it grindable? (surface roughness, minor chips, uneven glaze)
   - **Defect depth** -- can grinding reach it without compromising tile integrity?
   - **Cost-benefit** -- is grinding cheaper than re-making the tile?
3. Select a decision:
   - **Grind** -- send to grinding stage
   - **Reject** -- write off (defect too severe)
   - **Refire** -- attempt to fix with another firing cycle

### 10.3. Non-Grindable Defects

The following defects cannot be fixed by grinding:

- Deep cracks (structural integrity compromised)
- Color mismatch (grinding doesn't change color)
- Warping (grinding changes thickness, not flatness)
- Crazing (cracks go through the glaze layer)
- Black coring (internal defect)

### 10.4. Recording Grinding Results

After grinding is complete, inspect the result:

1. Pass -- tile meets quality standards after grinding
2. Fail -- grinding did not fix the issue, tile should be rejected

Record the result in the system to update the position status and defect tracking.

---

## 11. Quality Photos & Analysis

### 11.1. Photo Upload

Photos are a critical part of quality documentation. Upload photos:

- During Pre-Kiln QC (glaze application issues)
- During Final QC (firing defects)
- When creating QM Blocks (evidence)
- When creating Problem Cards (documentation)

### 11.2. AI-Powered Photo Analysis

The system includes AI vision capabilities for quality photos:

- **Defect detection** -- AI can identify common defects from photos
- **Color matching** -- AI compares product color against the specification sample
- **Surface analysis** -- AI evaluates surface uniformity

To use AI analysis:
1. Upload a clear, well-lit photo of the defect or product
2. The system automatically runs the analysis
3. Review the AI's assessment and confirm or override

> **Tip**: For best AI analysis results, photograph defects with good lighting, include a color reference card, and shoot straight-on (not at an angle).

### 11.3. Photo Best Practices

- Always include a ruler or size reference in defect photos
- Take multiple angles for complex defects
- Use consistent lighting across inspections
- Include the position barcode/label in at least one photo per inspection

---

## 12. Working with Production Manager

### 12.1. Communication Flow

The QM and PM work closely together. Key interaction points:

| Situation | QM Action | PM Action |
|---|---|---|
| Defect found during QC | Create QM Block or fail the position | Reviews block, decides on rework or rejection |
| Defect rate spike | Create Problem Card | Investigates root cause in production |
| Color mismatch | Block position, upload comparison photos | Checks recipe and glazing process |
| Recipe issue suspected | Document findings, link to recipe | Adjusts recipe parameters |
| Force unblock needed | Review and approve quality aspect | Executes force unblock |

### 12.2. QM Blocks and PM Response

When you create a QM Block:

1. The PM sees it in their **Blocking** tab on the dashboard
2. A blocking task is automatically created
3. The PM must work with you to resolve the root cause
4. Only after QM resolves the block can the position continue

### 12.3. Escalation Path

If a quality issue is not being addressed:

1. Create a Problem Card (if not already done)
2. Escalate severity to "Critical"
3. The system sends a Telegram notification to the CEO
4. Schedule a review meeting with PM and CEO

---

## 13. Kiln Inspections

### 13.1. Overview

Navigate to `/manager/kiln-inspections` to participate in weekly kiln condition assessments.

### 13.2. Inspection Checklist

Kiln inspections check the physical condition of the kiln:

- Interior walls and ceiling -- cracks, spalling, wear
- Heating elements -- visible damage, hot spots
- Door seals -- integrity, heat leakage
- Temperature uniformity -- based on firing log data
- Shelf condition -- wear, warping, contamination

### 13.3. Reporting Issues

If an inspection reveals a kiln problem:

1. Document the issue with photos
2. Rate the severity (minor, moderate, severe)
3. The system creates a maintenance task if needed
4. Kiln may be marked for maintenance (unavailable for firing)

---

## 14. Telegram Bot Commands

| Command | Description |
|---|---|
| `/start` | Initialize bot connection |
| `/mystats` | View your QC statistics |
| `/stock` | Check material stock levels |
| `/help` | List all available commands |

### 14.1. Automatic Notifications

As QM, you receive notifications for:

- New positions ready for QC
- Defect rate threshold exceeded
- Problem card status changes
- Morning briefing with quality summary

### 14.2. Morning Briefing

The daily morning briefing includes quality-specific information:

- Positions waiting for QC
- Open QM blocks count
- Yesterday's defect rate
- Open problem cards

---

## 15. Reports and Analytics

### 15.1. Quality Metrics

Navigate to `/reports` for quality analytics:

- **Defect rate trends** -- daily/weekly/monthly
- **Defect distribution by type** -- which defects are most common
- **Defect distribution by glaze** -- which glazes have highest defect rates
- **First-pass yield** -- percentage of positions passing QC on first attempt
- **QC throughput** -- positions inspected per day

### 15.2. Using Data for Improvement

| Metric | Goal | Action if Missed |
|---|---|---|
| Overall defect rate | < 5% | Investigate top defect causes |
| First-pass yield | > 90% | Review pre-kiln QC thoroughness |
| Color match rate | > 95% | Calibrate color matching process |
| QC throughput | >= 20/day | Optimize inspection workflow |

---

## 16. Navigation Reference

| Page | URL | Purpose |
|---|---|---|
| QM Dashboard | `/quality` | Main dashboard with QC queue, blocks, problem cards |
| Grinding Decisions | `/manager/grinding` | Grinding decision workflow |
| Kiln Inspections | `/manager/kiln-inspections` | Weekly kiln condition assessments |
| Reports | `/reports` | Quality analytics and trends |
| Order Details | `/orders/:id` | Detailed view of a specific order |
| Settings | `/settings` | Personal account settings |

---

## 17. Tips and Best Practices

> **Consistency is key**: Use the same lighting, angle, and reference points for all quality photos. This makes comparison and trend analysis much more reliable.

> **Document everything**: Even if you pass a position, add a note if you noticed anything borderline. This creates a paper trail if the issue recurs.

> **Root cause, not symptoms**: When creating problem cards, always dig into why the defect happened, not just what the defect is. The "5 Whys" technique is effective.

> **Collaborate with PM**: Quality is a shared responsibility. Regular brief meetings with the PM to review defect trends and discuss improvements will have more impact than just blocking positions.

> **Track your own metrics**: Use `/mystats` in Telegram to see how many inspections you're completing. Set a personal target for thoroughness vs. speed.

> **Use the defect coefficient**: When defect rates for a specific glaze-product combination consistently deviate from the matrix, propose an update. Accurate coefficients lead to better production planning.

> **Photo evidence for all failures**: Make it a habit to photograph every failed QC check. This protects both you and the production team by creating an objective record.

---

*This guide covers Moonjar PMS v1.0 features for the Quality Manager role. For technical support, contact the system administrator.*
