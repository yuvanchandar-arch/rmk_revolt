# DESIGN_SYSTEM_BRIEF.md
## Visual Reference Mapping for LOTUS-EMAT Frontend (Gates 10–11)

**Companion file:** `reference_screenshots.zip`, containing 7 images (`dashboard.jpg`, `p1.jpg`...`p6.jpg`).
Open and study all 7 before building any frontend page.

**Hard rule, non-negotiable:** these images define **layout, density, component language, color
temperature, and visual polish only.** None of their on-screen content, brand names, product names, or
copy may appear anywhere in our product. If the words "EV Champ," "ZIPSURE," "AVILOO," "TWAICE,"
"CTNS," "123car," or any text visible in these screenshots shows up in our build, that is a compliance
failure at Gate 10, regardless of how good the code is. Every number, label, and panel in our dashboard
must be LOTUS-EMAT data as defined in `01_project_details.md`.

---

## Page-by-Page Mapping

### `dashboard.jpg` → **Operations Overview** (Section 8, Page 1)
Borrow: light theme, top nav bar with pill-shaped nav items, left icon rail, rounded widget cards,
multi-line chart for a "live" metric, donut-chart cluster for status breakdown, a highlighted
assistant/insight panel.
Replace: "EV Champ" assistant → a LOTUS insight panel surfacing one computed observation (e.g. "This
lot saved 64% of qualification time"). "Live Voltage" multi-line chart → per-unit electrical fingerprint
trend across a lot. "Battery Health" donut cluster (Running/Inactive/Idle/Stop) → decision breakdown
donuts (Approved / Escalated / Rejected / Abstained). "Measured Metrics" panel → live LOTUS summary
(Lot size N, reference sample m, certified ε, time saved).

### `p1.jpg` (dense data table) → **Lot Registry / Batteries Table** (Section 8, Page 2)
Borrow: dark theme, dense sortable table, colored pill/bar indicator per row, quick-search box,
pagination, "select a collection" filter dropdown.
Replace: "Health (%)" pill → Decision status pill (Approve/Escalate/Reject/Abstain, color-coded).
Columns become: Unit ID, Lot ID, Chemistry, Decision, Certified Risk ε, Application, Timestamp.
"Select a Collection" dropdown → lot filter.

### `p2.jpg` (sampling-methods infographic) → **conceptual explainer widget only**, used inside the
**Lot Detail / Live Calibration View** (Section 8, Page 3), not a full page.
Borrow: the clean "population → sample" diagram visual language.
Replace: relabel as "Random In-Lot Reference Sampling" — show the actual lot population, the randomly
drawn reference subset, and an arrow into "Full Stage-3 Qualification." This becomes a small live
diagram, not a static infographic — it should animate or highlight using Gate 7's real sampling output.

### `p3.jpg` (NEWARE cycler software) → **Stage-3 reference test viewer**, embedded inside the **Lot
Detail / Live Calibration View** (Page 3) when a reference unit is selected.
Borrow: dual-axis voltage/current-vs-time plot, right-hand parameter table with scrollable rows.
Replace: plot becomes the actual charge/discharge curve for a selected reference unit from Gate 1/2
data; parameter table becomes extracted Stage-3 features (capacity, DCIR, self-discharge, thermal) for
that unit.

### `p4.jpg` (Korean EV battery monitoring, dark theme) → **general visual-density reference for
Operations Overview and Shifted-Lot Demo** (Pages 1 and 7).
Borrow: dark theme with bright accent donuts for state counts, map/regional panel treatment (if we show
multi-fleet geography later), "replacement prediction" style forecast panel, compact claims/alerts feed.
Replace: state donuts → our four decision counts; "replacement prediction (β)" panel → escalation-rate
forecast or OOD-flag count; claims feed → recent lot-processing events log.

### `p5.jpg` (TWAICE Energy Analytics) → **Analytics & Reports page** (Section 8, Page 5)
Borrow: left sidebar section nav, daily bar-chart breakdown, large percentage donut with a legend list,
two-stat row ("Recoverable energy" / "Financial Impact" style), download button.
Replace: left nav items → Qualification / Risk Certificate / Test-Time Savings / Safety Flags /
Lifecycle. Daily bar chart → daily lot throughput (units processed per day, stacked by decision). Large
donut → fused vs. electrical-only time-savings comparison. Two-stat row → "Certified Risk Bound ε" and
"Time Saved (hours)" computed from real pipeline runs (Section 6 worked example on first load).

### `p6.jpg` (AVILOO certificate) → **Lot Certificate / Evidence Record Viewer** (Section 8, Page 6) —
this is the most directly reusable reference; treat it as close to a literal template.
Borrow: printable-card layout, large headline result box, benchmark bell-curve panel, checklist with
checkmarks, QR code block, signature/seal area, "status" banner line.
Replace: "State of Health 92.7%" headline → **two stacked values**, clearly labeled: "Certified Risk
Bound: ε ≤ X% (CERTIFIED)" and "Estimated Conditional Fail Rate: Y% (ESTIMATE — NOT CONTROLLED)" — these
must never collapse into a single number, per Section 5.8's hard requirement. Benchmark bell curve →
optional, can show where this unit's fused feature vector sits relative to the lot's calibration
population. Checklist (Battery Management System / Sensor / Pack Parameters / etc.) → our evidence
checklist (Stage 0 veto passed / Electrical fingerprint complete / Acoustic fingerprint complete / OOD
check passed / Application limits assigned). QR block → links to the full per-unit evidence record.
Signature/seal → replace "AVILOO Certified" seal with a "LOTUS-EMAT Decision Support — Not a Safety
Certification" seal, matching the explicit non-claim in Section 2 of the project details.

---

## Consolidated Design Tokens (derive from the set above, keep consistent across all pages)

- **Two supported themes across the product:** a light theme (primary, used for Overview/Analytics/
  Certificate, closest to `dashboard.jpg`, `p5.jpg`, `p6.jpg`) and a dark theme (used for Lot Registry/
  Shifted-Lot Demo and optionally the EMAT Multiphysics page for better heatmap contrast, closest to
  `p1.jpg`, `p4.jpg`). Pick one as default; make the choice intentional and documented in the Gate 10
  report, not accidental.
- **Card language:** consistently rounded corners, soft shadows, generous internal padding, icon + title
  header per card, an expand/open icon in the top-right corner of every widget card (all 7 references
  share this pattern).
- **Status color convention (lock this and never deviate):** Approve = green, Escalate = amber/yellow,
  Reject = red, Abstain = purple/blue (distinct from the other three; several references use a 4th
  "Inactive/Disconnected" color for a 4th-state treatment — reuse that slot for Abstain).
  Risk labels: CERTIFIED badge = solid/filled style; ESTIMATE badge = outlined/dashed style — this visual
  distinction is a functional requirement, not decoration.
- **Typography:** large, bold numerals for headline metrics (every reference does this); smaller
  uppercase or medium-weight labels beneath. Keep this pattern for every KPI shown.
- **The EMAT Multiphysics page is the one page allowed to break from the standard card grid** — it needs
  full-bleed canvas space for the cross-section renderer, with supporting panels (waveform, feature
  readout, state selector) docked to one side, similar in spirit to how `p3.jpg`'s cycler software
  dedicates most of the screen to the live plot with a parameter rail beside it.

---

## What Antigravity Must Confirm Before Gate 10 Is Marked Passed

A short "Design-Reference Compliance Check" section (already required by Gate 10's report format) must
explicitly state, page by page, which reference image informed which of our pages, and confirm — by
name search through the built frontend source — that none of the reference screenshots' brand/product
names appear anywhere in the codebase or rendered output.
