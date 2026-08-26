# QLBI Phase 4C — AQR Common-Engine Decomposition

## Scope and data discipline

This phase compares the direct cash-equity (`ASSET_CAT=EC`) long and short books of:

- AQR Equity Market Neutral Fund (`S000046740`; accession `0002071691-26-010941`)
- AQR Long-Short Equity Fund (`S000041116`; accession `0002071691-26-010957`)

Both books have report date 2026-03-31. Holdings were extracted by accession from the public typed-Parquet mirror of the SEC quarterly Form N-PORT flat files. The SEC filing remains authoritative; the mirror is a transport layer only.

A directly observed short is an economic exposure, not automatically a negative-alpha view. Hedge, pair, event and mandate-overlay intent remain unresolved at this stage.

## Main result

The two products are better represented as one common signed stock engine plus diffuse fund-level sizing and threshold transformations than as two independent investment views.

| Statistic | Result |
|---|---:|
| Signed Pearson correlation | 0.913713 |
| Signed Spearman correlation | 0.902993 |
| Country-neutral signed correlation | 0.912688 |
| Long common mass | 81.1117% |
| Short common mass | 79.2228% |
| Weighted same-side rate | 98.1897% |
| Common squared-exposure share | 95.6772% |
| Mandate-residual squared-exposure share | 4.3228% |
| Fund B on Fund A slope | 0.8963 |
| Fund B on Fund A R-squared | 0.8349 |
| Shared-name regression slope | 0.9177 |
| Shared-name regression R-squared | 0.8652 |

The visible U.S. cash-equity + CUSIP proxy also preserves sibling ranking strongly (`Pearson=0.9055`, `Spearman=0.8553`), although the visible manager-long projection correlates only moderately with the full signed engine (`Pearson=0.5564`). Thus 13F-like data appear much better suited to engine identification than to exact signed-view recovery.

## Mismatch decomposition

The total signed L1 mismatch decomposes as follows:

| Source | Share of mismatch |
|---|---:|
| Same-direction sizing differences | 72.6873% |
| Opposite direction on shared names | 12.3989% |
| Names present in only one fund | 14.9137% |

The fund-level residual is not sparse. Its effective position count is approximately 900. The largest 50 names explain only 12.77% of residual L1 mass and the largest 100 explain 21.66%. This is more consistent with a broad mandate transformation of a common ranking than with a short list of discretionary overlay trades.

## Sign flips are boundary effects

The 123 shared names with opposite signs are concentrated close to zero common conviction:

- Median absolute common score, opposite-sign names: `0.0001157`
- Median absolute common score, same-side names: `0.0009825`
- Same-side/opposite median ratio: `8.49x`
- Opposite-sign names below shared-book first quartile: `92.68%`
- Opposite-sign names below shared-book median: `100%`
- Opposite-sign names in the top half of common conviction: `0`

Sign-flip rates by common-conviction decile fall monotonically:

| Decile, low to high | Flip rate |
|---:|---:|
| 1 | 45.24% |
| 2 | 19.76% |
| 3 | 4.76% |
| 4 | 2.40% |
| 5 | 1.19% |
| 6-10 | 0% |

This favors a latent-score formulation:

\[
q_{p,i,t}=g_{p,t}(z_{e,i,t};\tau^+_{p,t},\tau^-_{p,t},c_{p,i,t})+u_{p,i,t},
\]

where `z` is a common engine score, `g` is a fund-specific monotone scaling/capping rule, `tau+` and `tau-` are long/short thresholds, and `u` is a smaller residual.

## Cross-manager null and the legal-entity trap

The only nominally registrant-distinct pair with higher coherence than AQR was:

- Federated Hermes MDT Market Neutral Fund
- Federated Hermes MDT Market Neutral ETF

Their signed correlation was `0.9582` and country-neutral correlation `0.9592`. These are mutual-fund and ETF wrappers of the same MDT strategy, so they are a second positive control, not an independent-manager null observation.

After excluding that same-parent strategy pair, 39 registrant-distinct pairs had:

| Statistic | Signed correlation |
|---|---:|
| Median | 0.0290 |
| Maximum | 0.0975 |
| AQR sibling pair | 0.9137 |

A provisional engine-coherence score,

\[
EC=(\max(\rho,0)J_LJ_S)^{1/3},
\]

is `0.742` for AQR and `0.818` for the Federated MDT wrapper pair, versus a median `0.0265` and maximum `0.0855` among the parent-filtered unrelated pairs.

## Consequence for Institutional Intent Field

Neither filing count, series count, CIK count nor parent-manager count is the correct voting unit. The correct unit is the latent stock engine.

A parent manager can run multiple engines, while one engine can appear through multiple registrants and wrappers. The hierarchy should therefore be:

```text
fund/share class
  -> series
    -> adviser/subadviser and parent manager
      -> empirically inferred stock-engine cluster
        -> mandate-specific residual
```

IIF consensus should count the engine common component once. Fund residuals should be retained for mandate-spread analysis rather than treated as independent confirmation.

## Revised QLBI order of operations

1. Resolve legal entities and adviser/subadviser relationships with N-CEN.
2. Infer engine clusters from direct N-PORT long/short coherence.
3. Estimate a common latent score per engine.
4. Estimate fund-specific monotone thresholds, scaling and caps.
5. Transport only the visible engine projection into synthetic-13F tests.
6. Add independent short sensors before constructing signed conviction.
7. Decompose direct short exposure into alpha, hedge, pair/event and unresolved components.
8. Test consensus, polarization and transition signals out of sample.

## Remaining gates

- Longitudinal persistence of level and quarter-to-quarter rebalancing coherence
- Point-in-time style-factor residualization
- N-CEN adviser/subadviser/CRD/LEI bridge
- Parent- and engine-clustered cross-manager null
- Synthetic-13F transport across multiple manager families
- Incremental predictive value over long-only and long-implied-short placebos

## Current verdict

`GO — COMMON ENGINE IDENTIFIED CROSS-SECTIONALLY`

The evidence is strong enough to promote engine inference to a formal layer of QLBI/IIF. It is not yet sufficient to claim that an observed short is negative-alpha intent, that the engine persists through time, or that Renaissance's hidden U.S. short book can be reconstructed.
