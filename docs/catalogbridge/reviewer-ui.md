# Premium catalog workbench

Status: design specification; no UI exists yet. Premium means clear operational decisions, evidence and fast review—not decorative charts or fabricated savings.

## Information architecture

Primary areas: batches, feed library, review queue, analytics and owner settings. Desktop workbench: batch navigation on the left; supplier row/candidate table in the center; side-by-side source evidence and decision panel on the right. Compact screens use a readable stacked detail view, not squeezed columns.

Batch header always shows input rows, resolved/review/failed counts, remaining/reserved/unknown usage, budget mode and source revisions. Separate reviewed acceptance from automatic recommendations. A partial batch retains completed rows and clearly names why others stopped. Waiting for review must not look like a spinning model call.

## Journeys

1. **Import:** choose master/supplier CSV or JSON; preview actual rows, mapping and counts; surface duplicate/invalid rows without silent drop; freeze revision after explicit confirmation.
2. **Start:** show profile availability, egress requirement, expected usage range and strict-versus-advisory token mode. Owner approves allowance; missing capabilities have actionable blocking reasons. No invented dollar estimate where price basis is unknown.
3. **Observe:** staged progress, current route, retries, reservation and failure status; cancel stops future dispatch but explains possible already incurred usage.
4. **Review:** inspect original fields with highlighted matches/conflicts, candidate alternatives and missing information. Show calibrated confidence basis/sample support, not a misleading precision percentage from the model. Accept/correct/reject requires explicit action; no preselected acceptance.
5. **Resolve conflict:** changed revision/authority returns visible stale state; user refreshes evidence and makes a new decision. Never replay old form silently.
6. **Export:** show reviewed eligible rows and exclusions; download reviewed mappings plus unresolved report/manifest. Unreviewed recommendation export is a separate, clearly warned option, not the primary CTA.
7. **Analytics:** route/model breakdown with all attempts, denominators, uncertainty and price basis. “No baseline measured” replaces unsupported savings. Unknown usage remains conspicuous.

## Visual and accessibility targets

Restrained neutral palette, clear typography and spacing, readable dense tables, semantic status chips with text/icons, visible focus, sufficient contrast and no status conveyed by color alone. Virtualize/paginate large lists; no full batch history embedded into every poll. Accessible form labels, table headers, error summaries, focus restoration and screen-reader progress announcements. Respect reduced motion; never animate artificial progress.

Acceptance viewports: 1440×900, 1280×800 and 390×844; keyboard-only start/review/export; 200% zoom, long titles and missing attributes; loading/empty/partial/error/stale/forbidden states. Test session expiry/CSRF, rapid double-click, failed download, network reconnect and browser refresh mid-run. Frontend tests plus actual browser screenshots and evidence are required; a successful Vite build is not visual QA.
