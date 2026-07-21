# external/ — input data drop-zone

`cycleform` reads its **inputs** from here (via `settings.external`). Drop data
files in, keep this README describing what each one is. Nothing here is written
by the pipeline — outputs go to `../results/`.

## cycling_rates/

The cycling-rate outcome sources, harmonised by `cycleform.outcomes` into one
long table (one row per place × year × source; see CLAUDE.md §4).

| file | source | construct | notes |
|------|--------|-----------|-------|
| `max_value.csv` | old project (Eurostat + 2011 census) | mixed | `Place, max_value` (% cycling). Mixed constructs — kept for continuity/comparison; modelled with a `source` fixed effect. |
| `oecd_fua_commute_bicycle.csv` | OECD Functional Urban Areas | commute mode share | Bicycle main-mode-to-work, % of workers, multi-year. **We take the most recent year per FUA.** |

### To add UK census / Active Lives

Drop a CSV here with at least `place` and a cycling-rate column, then tell me its
columns and construct (commute mode share vs all-trip vs weekly participation)
and I'll wire it into `cycleform.outcomes`. Do not pre-clean it — the harmoniser
handles cleaning so the raw file stays traceable.

## Provenance

- OECD file originally: `OECD.CFE.EDS,DSD_FUA_TRAN@DF_TRAN_COMMUT,1.2+all.csv`
  (copied from the old repo's `external/data/`, renamed for clarity).
- `max_value.csv` copied from the old repo's
  `Data/eurostat/cleaned_data/max_value.csv`.

Both are **copies** — the old repo is untouched.
