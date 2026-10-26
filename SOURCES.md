# Sources

Every real source this project uses or plans to use is listed here with its terms. A source is only used for research
work after the Night Shift operator registers a curated source entry for it. Nothing listed below has been analysed.

## Inventory and blockers

Real-data state: **pending_source_entry** (gate: curated source entry).

Real work uses only three selected paragraph excerpts of the FBI's own case summary (registered as one text source; labels are local locators, not pages), as bounded one-excerpt tasks the Worker generates, only while that exact text is registered. The FBI Vault PDF pages are not in a page-cited pipeline and no task reads them.

Inventory:
- FBI D.B. Cooper hijacking case summary: three selected paragraph excerpts (public domain government text)

Blockers:
- The FBI Vault PDF pages have no page-cited text pipeline yet.
- Real-data tasks exist only while the reviewed excerpt text is registered with its exact hash.

## Rules

- Do not commit source data files. Records point to sources; they do not copy them (a test enforces this).
- Records built from a description alone are `unverified` and carry no hash.
- A source whose redistribution terms are restricted or unresolved is never marked publishable.
