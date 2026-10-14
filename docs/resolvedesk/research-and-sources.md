# Research and source register

Research reviewed 13 October 2026. The initial corpus now contains 16 checksum-frozen official HTML pages; see [source manifest](../../data/resolvedesk/manifests/sources.json) and [validation](validation-2026-10-13.md). Independent human scoring remains open.

## Market observations

| Primary source | Observation | Implication |
| --- | --- | --- |
| [Inkeep Agent Copilot](https://docs.inkeep.com/cloud/support-tools/agent-copilot/overview) | Offers draft answers, relevant links, and support investigation suggestions | A technical support workflow already has commercial offerings |
| [Inkeep quality approach](https://docs.inkeep.com/cloud/overview/why-inkeep) | Describes citations, authoritative sources, and admitting knowledge gaps | Citations and abstention alone are not a unique differentiator |
| [Kapa documentation](https://docs.kapa.ai/) | Describes indexed knowledge and drafted ticket replies | Competing with a generic documentation assistant would require a stronger advantage |
| [Vanta questionnaire workflow](https://help.vanta.com/en/articles/11345464-getting-started-with-questionnaire-automation) | Uses company knowledge and approval to answer questionnaires | Another viable RAG market, but public search cannot establish a company's private controls |

Recommendation is an inference: start with a constrained support workflow where versions, source passages, and missing details can be tested. These vendor descriptions establish competition, not independent proof of effectiveness or our customers' willingness to pay.

Interview questions: Which ticket types consume investigation time? How often do client/server versions differ? Which sources do engineers trust? What would make a draft unsafe to send? Would a standalone workbench be adopted before helpdesk integration? Measure baseline reply time on consented pilot cases.

## Knowledge sources

| Source | Intended use | Acquisition decision |
| --- | --- | --- |
| [PostgreSQL manuals](https://www.postgresql.org/docs/) | Versioned technical knowledge | Start with selected 16/17 HTML pages; freeze content and anchors |
| [PostgreSQL 17 release notes](https://www.postgresql.org/docs/17/release.html) | Version changes and migration behavior | Select relevant sections; record publication/version and capture time |
| [PostgreSQL 16 pg_dump](https://www.postgresql.org/docs/16/app-pgdump.html), [17 pg_dump](https://www.postgresql.org/docs/17/app-pgdump.html) | Client/server backup compatibility | Acquired and frozen in the initial source manifest |
| [PostgreSQL 17 pg_upgrade](https://www.postgresql.org/docs/17/pgupgrade.html) | Upgrade preparation and constraints | Use historical version explicitly |
| [PostgreSQL license](https://www.postgresql.org/about/licence/) | Documentation reuse terms | Preserve required notices with redistributed documentation |

Prefer section-sized HTML sources over ingesting an entire manual PDF. Preserve headings and code blocks. Adjacent context can be fetched when a result crosses a boundary, subject to the context budget.

## Actual support-question candidates

| Case source | Real symptom | Dataset treatment |
| --- | --- | --- |
| [DBA Stack Exchange: backup failure](https://dba.stackexchange.com/questions/10996/backup-of-postgres-database) | Windows backup command with client/server mismatch | Historical case; retain original versions and attribution |
| [Stack Overflow: pg_dump version mismatch](https://stackoverflow.com/questions/40520919/how-to-fix-pg-dump-aborting-because-of-server-version-mismatch) | Backup utility rejects server version | Question candidate; adjudicate against official documentation |
| [PostgreSQL bug report 16973](https://www.postgresql.org/message-id/16973-399e0677315a26a6%40postgresql.org) | Unsupported archive version with incomplete environment | Clarification/escalation candidate; link and metadata pending reuse review |
| [PostgreSQL mailing-list version discussion](https://www.postgresql.org/message-id/8b459360516e4a32aa0d675afae8357e%40zuerich.ch) | Different server, dump, restore, and target versions | Complex historical question; not an automatic gold answer |

These examples concern older versions; do not silently relabel them as 16/17 customer cases. Community answers and the fact that a report is filed as a bug do not establish the correct diagnosis. Public messages can include personal data; retain only necessary case content. The PostgreSQL software/documentation license is not assumed to cover every mailing-list contribution.

[Stack Exchange licensing](https://stackoverflow.com/help/licensing) describes attribution/share-alike licenses that vary by contribution date/revision. Record the applicable revision and license when copying; use links/metadata until reuse requirements are resolved.

## Technical sources and decisions

- [SQLite FTS5](https://www.sqlite.org/fts5.html): lexical retrieval baseline with BM25; smaller FTS5 BM25 values rank better. Raw ranking scores are not correctness probabilities.
- [Brave Web Search API](https://api-dashboard.search.brave.com/api-reference/web/search/get) and [search operators](https://api-dashboard.search.brave.com/documentation/resources/search-operators): proposed search backend, returning links/snippets. The application must fetch and validate source pages; snippets alone are not accepted as final evidence.
- [C4 diagram definitions](https://c4model.com/diagrams): architecture zoom levels used in this delivery pack.

Implementation decision: use the official PostgreSQL site's [version-scoped search](https://www.postgresql.org/search/?q=pg_dump+version&u=%2Fdocs%2F17%2F) by default. Its actual documentation form supplies the `u` parameter; a live fallback smoke succeeded without a key. Brave remains an optional adapter requiring credentials and applicable terms. Search is separate from model generation through the installed Codex adapter; the coding assistant's browser is not an application dependency. The site-search HTML can change and must remain covered by parsing/failure tests.
