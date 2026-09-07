# Mobile Layer V1 (Core MVP)

## Breakpoints
- `phone`: `< 768` (`md:hidden` / `md:block`)
- `tablet`: `768–1023`
- `desktop`: `>= 1024`

## What Was Implemented

### Shell and overlays
- Kept phone shell pattern: `bottom nav + side sheet`.
- Added compact command entry in phone topbar.
- Improved safe-area handling in app layout and sticky action bars:
  - bottom content padding uses `env(safe-area-inset-bottom)`.
- Normalized dropdown behavior for overlays:
  - `Select` and `Combobox` use portal by default.
  - option selection uses pointer events (`onPointerDown`) for mouse/touch consistency.
  - floating menus use higher z-index to avoid clipping under containers/modals.
- Updated modal container:
  - constrained height (`max-h-[90vh]`),
  - internal scroll in body area,
  - safe-area aware footer padding.

### Shared mobile primitives
- Added `MobilePagination` primitive for phone list/card screens.
- Kept desktop/tablet data tables unchanged.

### Core screen scope
- Dashboard:
  - Added `Quick actions` block at top.
  - Maintained one-column behavior on phone.
- Clients / Vehicles / Employees:
  - Added phone card-list rendering.
  - Kept row click behavior.
  - Kept direct frequent actions visible on phone.
  - Added phone pagination.
- Work Orders list:
  - Added phone queue-card layout (no mandatory horizontal scroll).
  - Kept compact filter bar and KPI strip.
  - Added phone pagination.
- Work Order detail:
  - Strengthened first-screen hierarchy with created time + status badge above summary.
  - Kept first-screen data priority: status/client/vehicle/total/paid.
- Work Order intake:
  - Preserved guided flow `1 -> 2 -> 3`.
  - Sticky action area now safe-area aware.
- Settings:
  - Preserved one-column phone flow.
  - Sticky save footer now safe-area aware.

## Mandatory QA Checklist

### Viewports
- Phone: `360x800`, `390x844`
- Tablet: `768x1024`
- Desktop: `>=1024`

### Flow
- Login -> Dashboard -> Client -> Vehicle -> Work order -> Payment -> Close

### Layout and interaction
- No mandatory horizontal scroll in phone queues/registries.
- Touch targets for key actions are at least `44px` where critical.
- Frequent actions are directly visible on phone screens.

### Keyboard and safe-area
- Keyboard open on phone does not block core form actions.
- Sticky/bottom action areas respect `env(safe-area-inset-bottom)`.
- Bottom nav remains usable with system safe-area.

### Overlay/pointer stability
- Closing select/combobox/modal/sheet does not leave invisible click blockers.
- Backdrops do not remain active after close.
- Dropdown selection works via mouse and touch consistently.

### State transitions
- Filter changes do not produce layout jumps.
- Loading/empty/error states remain stable in height and interaction.
