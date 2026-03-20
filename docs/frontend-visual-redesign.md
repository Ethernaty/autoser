# AutoService CRM SaaS: Frontend Visual Redesign Direction

## 1) Product-level visual direction (strict)

### Design statement
Build an **operator-first enterprise CRM UI**: dense, calm, predictable, and fast to scan during 8-10 hour daily usage.

### Target perception
- Professional and trustworthy
- Data-first, not decoration-first
- Fast for repetitive operations
- Consistent action hierarchy
- Clear status visibility at a glance

### Explicitly avoid
- Generic bootstrap/admin look
- Large empty blocks and low information density
- Excessive rounded corners and playful styling
- Marketing-style hero sections or gradient-heavy visuals
- Random component styles per screen

## 2) Strict UI design system direction

## 2.1 Foundation tokens (replace coarse defaults)

Current spacing and sizing are too coarse (`h-5`, `h-6`, mostly 8px jumps), causing toy-like controls. Move to this compact operational scale:

- Spacing scale: `4, 8, 12, 16, 20, 24, 32`
- Control heights:
  - `input/button sm`: `32`
  - `input/button md`: `36`
  - `toolbar controls`: `36`
- Table heights:
  - header: `36`
  - row compact: `40`
  - row comfortable: `44`
- Card padding:
  - list/table containers: `16`
  - modal/forms: `20`
- Radius:
  - controls: `8`
  - cards/modals: `10`
- Border:
  - default stroke: neutral `200`
  - interactive stroke hover: neutral `300`

## 2.2 Typography hierarchy

Use stronger hierarchy and less oversized headings:

- `Page title`: `24/32`, `600`
- `Section title`: `18/26`, `600`
- `Table header`: `12/16`, `600`, uppercase optional
- `Body`: `14/20`
- `Meta text`: `12/16`

Reason: current `h1` at `28/36` with compact cards makes pages feel inflated while controls remain tiny.

## 2.3 Color strategy (neutral-first)

- Base surfaces:
  - App background: neutral `50`
  - Primary panels: neutral `0`
  - Secondary strips (filters, table header): neutral `50`/`100`
- Text:
  - Main: neutral `900`
  - Secondary: neutral `600`
  - Tertiary/meta: neutral `500`
- Accent:
  - Primary action only: current blue is acceptable
- Semantic:
  - success/warning/error only for statuses and critical feedback

## 2.4 Component behavior standards

- Every interactive element has visible hover, focus, disabled states
- One primary CTA per logical block
- Status never represented by color alone (add text)
- Validation inline under field, not generic top-level only
- Empty states must include next action

## 3) Structural recommendations by UI area

## 3.1 Sidebar

Current issue: feels template-like and visually light.

Direction:
- Add product identity strip at top:
  - product name + workspace slug (small)
- Group nav by workflow:
  - Operations: Dashboard, Work orders, Clients, Vehicles
  - Team: Employees
  - System: Settings
- Active item:
  - left 2px accent bar + stronger bg (`primary/8`)
  - icon + label weight `500`
- Increase nav item height to `36` (current too small)

## 3.2 Topbar

Current issue: cramped and visually flat.

Direction:
- Left: workspace name + role/meta
- Right: workspace switcher, global command/search, logout
- Add subtle bottom shadow and stronger separator from content
- Keep single-row layout at desktop widths >=1280

## 3.3 Page headers

Current issue: weak hierarchy and generic subtitles.

Direction:
- Header block contains:
  - title
  - concise operational subtitle
  - right-aligned primary action cluster
- Optional KPI chips in header for entity screens (count, open, overdue)
- Vertical rhythm:
  - header bottom margin: `16`
  - section gap: `16-20`

## 3.4 Filters/toolbars

Current issue: scattered controls, weak shell.

Direction:
- Wrap filters in dedicated toolbar container (light neutral background, border)
- Pattern:
  - left: search + key filters
  - right: create/export actions
- Keep controls same height (`36`)
- For large selects (vehicles/employees): searchable combobox pattern

## 3.5 Tables

Current issue: visually generic; actions compete with data.

Direction:
- Strong table shell:
  - header strip with neutral `50`
  - precise row separators
  - sticky header
- Row density:
  - default compact row `40`
  - numeric columns right-aligned
- Action column:
  - icon + menu pattern, not many full buttons per row
- Status column:
  - standardized status badge tokens
- Empty state inside table body with clear action link/button

## 3.6 Forms

Current issue: fields look tiny and inconsistent; select styling mixed inline.

Direction:
- Replace native `<select>` style duplication with a single `Select` primitive wrapper
- Use form sections:
  - identity
  - assignment
  - financial
  - notes
- Label + hint + error stack consistent
- Modal forms:
  - max width by form size (`sm/md/lg`)
  - sticky footer actions

## 3.7 Detail screens

Current issue: cards repeated without strong information architecture.

Direction:
- Use `DetailLayout` as default:
  - main column: timeline, lines, activity
  - aside column: status, totals, assignment, quick actions
- Add sticky “control rail” on right for status transitions and assignment
- Group financial summary into one compact finance card

## 3.8 Status badges

Direction:
- Use explicit semantic set:
  - `new`: neutral
  - `in_progress`: warning
  - `completed`: success
  - `canceled`: error
- Badge style:
  - pill with border + tint + text
  - same min width for visual alignment in tables

## 3.9 Empty states

Direction:
- Contextual message + one clear action
- Example:
  - "No vehicles yet for this client"
  - CTA: "Add vehicle"
- No decorative illustration needed

## 3.10 Buttons

Direction:
- Primary button reserved for main intent in region
- Secondary for alternate actions
- Ghost for table row/tool actions
- Destructive only for irreversible actions
- Standardize size:
  - toolbar: `md`
  - row actions: `sm`

## 4) Screen-by-screen redesign plan

## 4.1 Dashboard

- Header: title + date range + "New work order" primary CTA
- KPI strip: 4 cards
  - open work orders
  - closed today
  - revenue today
  - overdue/unpaid
- Two-column body:
  - left: recent work orders table
  - right: recent activity + quick actions
- Remove generic loose cards; use structured panels with clear headings

## 4.2 Clients

- Toolbar: search, status/filter chips, `Add client`
- Table columns tuned for operations:
  - name, phone, vehicles count, last work order date, updated
- Row click opens detail; actions in compact menu
- Create/edit form:
  - contact section
  - notes section

## 4.3 Vehicles

- Toolbar: plate/model search + client filter + `Add vehicle`
- Table columns:
  - plate, make/model, client, year, VIN short, open work orders
- Detail:
  - vehicle profile card
  - linked client card
  - work order history table

## 4.4 Employees

- Toolbar: search + role filter + active/inactive toggle + `Add employee`
- Table columns:
  - employee, role, status, last active, created
- Status toggle must be explicit action with confirmation for deactivate
- Form:
  - account info
  - role
  - activation state

## 4.5 Work orders (list)

- Most critical screen; prioritize density and scan speed
- Toolbar:
  - universal search
  - status filter
  - assignee filter
  - `New work order`
- Table columns:
  - number/id, client, vehicle, assignee, status, total, paid, remaining, updated
- Row color cue for urgent states (very subtle)

## 4.6 Work order detail

- Convert to true two-column detail layout:
  - Main:
    - lines table
    - payment history
    - notes/activity
  - Aside (sticky):
    - status badge
    - totals (total/paid/remaining)
    - assignee + vehicle
    - status transitions + close action
- Replace prompt-like edit interactions with inline edit modal pattern
- Separate "Payments" block visually from "Closure" actions

## 4.7 Settings

- Keep minimal MVP scope but improve structure:
  - Workspace profile
  - Operational defaults (timezone/currency)
  - Contact and schedule notes
- Form sections with headers and helper text
- Save bar pattern:
  - sticky footer in panel with save state

## 5) Concrete implementation guidance (Next.js + Tailwind + shadcn/ui)

## 5.1 Immediate file targets (no architecture rewrite)

- Layout shell:
  - `src/widgets/app-shell/sidebar.tsx`
  - `src/widgets/app-shell/header.tsx`
  - `src/design-system/patterns/layout/page-header.tsx`
  - `src/design-system/patterns/layout/toolbar.tsx`
  - `src/design-system/patterns/layout/section.tsx`
- Primitives:
  - `src/design-system/primitives/button.tsx`
  - `src/design-system/primitives/input.tsx`
  - `src/design-system/primitives/textarea.tsx`
  - `src/design-system/primitives/badge.tsx`
  - `src/design-system/primitives/data-table/data-table.tsx`
- Screens:
  - `src/features/workspace/ui/dashboard-screen.tsx`
  - `src/features/workspace/ui/clients-screen.tsx`
  - `src/features/workspace/ui/vehicles-screen.tsx`
  - `src/features/workspace/ui/employees-screen.tsx`
  - `src/features/workspace/ui/orders-screen.tsx`
  - `src/features/workspace/ui/work-order-detail-screen.tsx`
  - `src/features/workspace/ui/workspace-settings-screen.tsx`

## 5.2 Tailwind token updates

- In `tailwind.config.ts`:
  - add granular spacing (`0.5`, `1.5`, `2.5`, `3.5`, etc. or explicit px values)
  - add control heights (`control-sm`, `control-md`)
  - add table row/header heights (`row-compact`, `row-comfortable`, `table-head`)

## 5.3 Primitive standardization rules

- Build and use a single select primitive (`Select`) instead of repeated raw `<select className=...>`
- Add `size` variants to `Input` and `Textarea` aligned with button sizes
- Add badge variant `status` for canonical work-order states
- In `DataTable`, switch row actions from multiple buttons to action menu trigger when >2 actions

## 5.4 shadcn/ui usage guidance

- Use shadcn primitives where they add operational value:
  - `DropdownMenu` for row actions
  - `Popover + Command` for searchable selectors (vehicle/employee)
  - `Tabs` only for dense detail pages (if needed)
  - `Dialog` already used; enforce consistent modal sizing and footer
- Do not introduce decorative shadcn components with no workflow value

## 5.5 Delivery sequence (safe, high impact)

1. **Foundation pass**
- tokens, button/input/badge/table primitives
- sidebar/topbar/header shells

2. **Core list screens**
- work orders, clients, vehicles, employees

3. **Detail experience**
- work-order detail two-column operational layout

4. **Dashboard + settings polish**
- KPI and structured settings form sections

## 5.6 Acceptance criteria (visual quality gate)

- At 1280px and 1440px, screens feel dense but readable
- One primary CTA per page section
- Tables readable for 50+ rows without visual fatigue
- Status and financial fields scannable in <2 seconds
- No raw, inconsistent form controls across screens
- No page looks like a generic starter admin template

---

This direction is intentionally strict: improve **operational clarity and trust** first, then add aesthetic polish only where it helps workflow.
