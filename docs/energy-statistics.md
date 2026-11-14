# Grid imports, exports, and backfills

PSEG's bidirectional meters expose separate import and export channels. Default
labels such as `Meter #123g - Off-Peak` identify generation with a `g` suffix;
those negative kWh become positive export statistics. Consumption channels stay
positive. The writer preserves gross imports and exports independently, sums
multiple meters once per tariff/hour, and rejects unexpected signs, nonfinite
values, duplicate hours, and non-hourly timestamps.

Existing `psegli:off_peak_usage` and `psegli:on_peak_usage` identifiers are
preserved. The new `psegli:off_peak_export` and `psegli:on_peak_export` series
can be selected as the matching Energy grid sources' energy returned to grid.
Custom portal channel names that remove the default meter label need a mapping
change before importing. Exports measure grid feed-in, not total solar output.

ChartData encodes New York wall-clock labels as UTC-looking epochs. Conversion
uses `America/New_York` for the date's UTC offset rather than a fixed four-hour
shift. Duplicate hours are rejected instead of guessing an ambiguous reading.

`psegli.update_statistics` accepts `days_back` from 0 through 365 and
`exports_only` (default false). Zero requests yesterday through today. Fetches
use inclusive windows of at most 28 days because PSEG silently truncates large
hourly responses. Use `exports_only: true` to add export history without
rewriting imports. A backfill always runs through the present so later
cumulative totals are recalculated as well.

Imports share a lock and wait for recorder commits before reading offsets and
before returning. Offset lookups include older history, including export gaps
longer than seven days. New series receive a zero baseline one hour before the
first reading so the Energy dashboard includes that hour. Every series is
validated and its offset resolved before any writes for that window are queued;
earlier windows remain committed if a later window fails.

The maintenance task uses the config entry background-task API so it does not
hold Core startup open. Imports are deferred until Core is running.

Validation: deployed on Home Assistant OS/Core 2026.10.4, including historical
exports and repeated overlapping imports. `python -m unittest discover -s tests
-v` covers signed directions, winter/summer offsets, window coverage, malformed
readings, queued writes, long inactive export gaps, first-hour baselines, and
idempotent overlaps. Tests isolate recorder with an in-memory queue; they do not
replace validation on a real recorder. New recorder metadata is supplied where
available, with a legacy fallback for older Core versions.

To roll back the code, restore the previous integration directory and restart
Core. Remove the two export selections from Energy preferences if reverting to
a version without exports; retain their recorded history. Existing imports and
their identifiers remain in place.
