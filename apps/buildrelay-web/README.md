# BuildRelay response desk

React/TypeScript, same-origin FastAPI sessions, no browser-stored credentials or
demo incident data. Views: incidents, event inbox, dead letters, connections,
audit, workspace/client/team administration; evidence drawers and handoff export.

`npm ci`, `npm test`, `npm run build`. Development proxy targets loopback 8007.
The production build is served by the API. Browser interaction/visual acceptance
could not be run in the implementation session; no connected browser was available.
