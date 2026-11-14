# Recorder compatibility

Home Assistant's recorder metadata migration requires an explicit mean type
and unit class beginning with Core 2026.11. PSEG supplies cumulative kWh sums,
so imports use `StatisticMeanType.NONE`, `unit_class="energy"`, and
`has_sum=True`. Older Core versions without `StatisticMeanType` retain the
legacy `has_mean=False` metadata. Existing statistic identifiers and cumulative
values are unchanged.

The equivalent metadata is deployed on a PSEG-LI installation running Core
2026.10.4 and is visible in recorder readback for its import/export statistics.
