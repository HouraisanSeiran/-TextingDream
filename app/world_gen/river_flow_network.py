"""Finite-year, physical-Q river symbols on an existing irregular receiver graph.

Q[m, cell] is the actual monthly mean discharge THROUGH that cell's receiver edge,
after lake retention/losses. No accumulation, downstream activation or rain is done
here. A parent vector is a stable topological skeleton, NOT an instruction to draw
blue. Only ``draw_segments`` may be drawn; these break at dry/unknown edges and
monthly wet lakes. Classes describe this supplied year, not long-term permanence.
"""
from __future__ import annotations

import hashlib
import json

import numpy as np

from app.world_gen import graph_hydro as gh

SCHEMA = 'finite-year-river-flow-v1'
DEFAULT_MONTH_DAYS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
SYMBOL_WIDTH = dict(reference_q_m3_s=1., minimum_px=1.1, maximum_px=3.8, log_gain_px=.45)


def symbol_width(q_m3_s, recipe=None):
    """Absolute-Q cartographic width at the reference 1800px atlas, not metres."""
    p = SYMBOL_WIDTH if recipe is None else recipe
    return float(np.clip(p['minimum_px'] + p['log_gain_px'] * np.log2(
        1. + np.sqrt(float(q_m3_s) / p['reference_q_m3_s'])),
        p['minimum_px'], p['maximum_px']))


def _cartographic_lines(rec, order, raw_active, coords, area, shape, first, spacing, profile, maximum):
    """TG's explicit-mask graph partition; never reroute or invent downstream Q."""
    import sys
    root = str(gh.terragenesis_root())
    if root not in sys.path:
        sys.path.append(root)
    from terrain_pipeline.surface_rivers.metric_backbone_precompute import segment_on_channel, reach_downstream

    active = raw_active.copy()
    minimum_length = 30000. if profile == 'overview-mainstem-30km' else 0.
    edge_length = np.zeros(rec.size)
    cells = np.flatnonzero(active)
    edge_length[cells] = np.linalg.norm(coords[cells] - coords[rec[cells]], axis=1)
    if minimum_length:
        # Longest original upstream path, including its outgoing edge. Keep all
        # qualifying trunks and restore their upstream mainstems, not every twig.
        # A zero/unknown-only gap is outside raw_active and is NEVER crossed.
        longest = edge_length.copy()
        donor = np.full(rec.size, -1, np.int64)
        ordered = order[active[order]]
        for cell in ordered[::-1]:
            below = rec[cell]
            if active[below] and longest[cell] + edge_length[below] > longest[below]:
                longest[below] = longest[cell] + edge_length[below]
                donor[below] = cell
        active &= longest >= minimum_length
        for cell in ordered:
            if active[cell] and donor[cell] >= 0:
                active[donor[cell]] = True
    partition = segment_on_channel(receiver=rec, valid_mask=np.ones(rec.size, bool),
                                   channel_mask=active, max_reaches=maximum)
    chains = partition['chains']
    downstream, ends = reach_downstream(receiver=rec, chains=chains)
    end_reasons = {e['reach_index']: e['reason'] for e in ends}
    ids = [gh._stable_id(c[0], first, spacing, shape[1]) for c in chains]
    upstream = [[] for _ in chains]
    for i, below in enumerate(downstream):
        if below >= 0:
            upstream[below].append(ids[i])
    lines = []
    for i, chain in enumerate(chains):
        # TG chains are vertex-disjoint. Append the REAL tail receiver so the
        # confluence handoff and a single-edge/two-node reach do not disappear.
        nodes = list(map(int, chain)) + [int(rec[chain[-1]])]
        below = int(downstream[i])
        lines.append(dict(id=ids[i], downstream_id=ids[below] if below >= 0 else None,
            upstream_ids=sorted(upstream[i]), nodes=nodes,
            end_reason='reach_handoff' if below >= 0 else end_reasons[i],
            head_area_km2=float(area[nodes[0]] / 1e6), outlet_area_km2=float(area[nodes[-1]] / 1e6)))
    recipe = dict(profile=profile, min_mainstem_length_m=minimum_length,
        selection='known active in any supplied month; longest upstream original-mesh path, restored mainstem; no downstream forcing',
        length_scope=('30km is about 5.4px at 10Mm/1800px overview; shorter tributaries omitted only from display'
                      if minimum_length else 'all supplied known-active edges retained; no length filtering'),
        tg_functions=['segment_on_channel', 'reach_downstream'], symbol_width=dict(SYMBOL_WIDTH),
        reference_width_px=1800)
    return sorted(lines, key=lambda v: v['id']), active, recipe, edge_length


def _flow_stats(q, seconds, minimum, perennial, seasonal):
    known = np.isfinite(q)
    active = known & (q >= minimum)
    count = int(active.sum())
    kind = ('unknown' if not known.all() else 'perennial' if count >= perennial else
            'seasonal' if count >= seasonal else 'intermittent' if count else 'dry_valley')
    observed = float(np.sum(q[known] * seconds[known]))
    return dict(monthly_q_m3_s=[float(v) if k else None for v, k in zip(q, known)],
                min_q_m3_s=float(q[known].min()) if known.any() else None,
                max_q_m3_s=float(q[known].max()) if known.any() else None,
                annual_mean_q_m3_s=observed / float(seconds.sum()) if known.all() else None,
                annual_volume_m3=observed if known.all() else None,
                observed_volume_m3=observed, known_months=int(known.sum()),
                active_months=(np.flatnonzero(active) + 1).tolist(), active_month_count=count,
                monthly_type=['unknown' if not k else 'active' if a else 'inactive'
                              for k, a in zip(known, active)], flow_class=kind)


def _draw_month(vectors, q, wet, ocean, coords, minimum, month):
    """Reuse cut_lines_at_lakes' dry-run/midpoint convention, retaining edge anchors.

    Lake raster cells are the available geometry: shore midpoints are a coarse-grid
    approximation, not surveyed shore intersections. Wet-wet edges are never drawn.
    A wet->dry edge uses Q at its wet source (actual routed release), not dry-cell Q.
    """
    out = []
    for vector in vectors:
        nodes = vector['nodes']
        pieces = []
        for a, b in zip(nodes[:-1], nodes[1:]):
            if not np.isfinite(q[a]) or q[a] < minimum or ocean[a] or (wet[a] and wet[b]):
                pieces.append(None)
                continue
            pa, pb = coords[a].tolist(), coords[b].tolist()
            midpoint = ((coords[a] + coords[b]) * .5).tolist()
            pieces.append(dict(a=a, b=b, start=midpoint if wet[a] else pa,
                               end=midpoint if wet[b] else pb,
                               from_lake=bool(wet[a]), to_lake=bool(wet[b])))
        # Group only truly continuous dry edges. Never reconnect across a wet node.
        i = 0
        while i < len(pieces):
            if pieces[i] is None:
                i += 1
                continue
            j = i + 1
            while (j < len(pieces) and pieces[j] is not None
                   and not pieces[j - 1]['to_lake'] and not pieces[j]['from_lake']):
                j += 1
            run = pieces[i:j]
            anchors = [p['a'] for p in run]
            out.append(dict(id=f"{vector['id']}@m{month:02d}:{anchors[0]}-{run[-1]['b']}",
                            parent_id=vector['id'], month=month, anchor_cell=anchors[0],
                            edge_anchor_cells=anchors, edge_q_m3_s=[float(q[a]) for a in anchors],
                            points_xz_m=[run[0]['start']] + [p['end'] for p in run],
                            from_lake=run[0]['from_lake'], to_lake=run[-1]['to_lake'],
                            through_lake=False, blue=True, symbol_width=1.0))
            i = j
    return out


def build_flow_network(receiver, order, monthly_q_m3_s, area_m2, grid, *, ocean=None,
                       monthly_wet_lake=None, cell_coords_xz_m=None,
                       min_active_q_m3_s=0.1, perennial_months=12, seasonal_months=3,
                       dry_valley_min_area_m2=1e10, month_days=None, max_segments=18000,
                       min_display_area_m2=0., cartography_profile=None):
    """Return ``vectors``, monthly ``draw_segments`` and finite-year class summary.

    ``grid``: shape_zx (or shape), first_xz_m (or first_sample_xz_m), spacing_m.
    Optional coordinates are original mesh node [N,2] or [z,x,2] X/Z metres;
    omitted coordinates are grid centres along the SUPPLIED graph, never D8 routing.
    TG ``order`` is a permutation in downstream-first order. NaN Q is unknown;
    negative or infinite Q is rejected. Day weighting uses the declared calendar.

    Each parent samples ``monthly_q_m3_s`` at ``anchor_cell`` (its head), not at a
    nearest existing vector. ``edge_monthly_q_m3_s`` preserves all along-channel
    increases/decreases. Parent topology does not depend on a selected month;
    draw slices carry parent_id without rewriting upstream/downstream links.
    Legacy skeleton = (any active month OR geometric-area dry valley) AND
    display area. An explicit cartography_profile instead uses the supplied
    known-active edges, TG maximal reaches, optionally fixed 30km mainstem support.
    This is reference-year display eligibility, NOT permanent-channel existence.
    Display omission never means no water. max_segments is a hard refusal, never
    clipping or threshold auto-tuning; profiles do not alter the legacy default.
    Width is a dimensionless game symbol, not a measured physical river width.
    """
    shape = tuple(grid.get('shape_zx', grid.get('shape', ())))
    first = tuple(grid.get('first_xz_m', grid.get('first_sample_xz_m', ())))
    spacing = float(grid['spacing_m'])
    if len(shape) != 2 or any(int(v) != v or v < 1 for v in shape):
        raise ValueError('grid requires positive integral shape_zx')
    shape = tuple(map(int, shape)); n = int(np.prod(shape))
    if len(first) != 2 or not np.isfinite(first).all() or not np.isfinite(spacing) or spacing <= 0:
        raise ValueError('invalid grid origin/spacing')
    r0 = np.asarray(receiver); o0 = np.asarray(order)
    if (r0.size != n or o0.size != n or not np.isfinite(r0).all() or
            not np.isfinite(o0).all() or np.any(r0 != np.floor(r0)) or np.any(o0 != np.floor(o0))):
        raise ValueError('receiver/order must be integral arrays of grid size')
    rec = r0.astype(np.int64).ravel(); order = o0.astype(np.int64).ravel()
    if np.any((rec < -1) | (rec >= n)) or not np.array_equal(np.sort(order), np.arange(n)):
        raise ValueError('invalid receiver or order permutation')
    rank = np.empty(n, np.int64); rank[order] = np.arange(n)
    edges = rec >= 0
    if np.any(rank[rec[edges]] >= rank[np.flatnonzero(edges)]):
        raise ValueError('receiver cycle or order not downstream-first')
    q = np.asarray(monthly_q_m3_s, np.float64)
    if q.shape not in ((12,) + shape, (12, n)):
        raise ValueError('monthly Q requires [12,z,x] or [12,N]')
    q = q.reshape(12, n)
    if np.isinf(q).any() or np.any(q < 0):
        raise ValueError('Q must be nonnegative finite or NaN (unknown)')
    area = np.asarray(area_m2, np.float64).ravel()
    if area.size != n or not np.isfinite(area).all() or np.any(area < 0):
        raise ValueError('area_m2 requires nonnegative finite cell values')
    ocean = np.zeros(n, bool) if ocean is None else np.asarray(ocean, bool).ravel()
    wet = np.zeros((12, n), bool) if monthly_wet_lake is None else np.asarray(monthly_wet_lake, bool)
    if ocean.size != n or wet.shape not in ((12,) + shape, (12, n)):
        raise ValueError('ocean or monthly wet lake shape mismatch')
    wet = wet.reshape(12, n)
    days = np.asarray(DEFAULT_MONTH_DAYS if month_days is None else month_days, np.float64)
    if days.shape != (12,) or not np.isfinite(days).all() or np.any(days <= 0):
        raise ValueError('month_days requires 12 positive finite durations')
    if (not np.isfinite(min_active_q_m3_s) or min_active_q_m3_s <= 0 or
            not np.isfinite(dry_valley_min_area_m2) or dry_valley_min_area_m2 < 0 or
            not np.isfinite(min_display_area_m2) or min_display_area_m2 < 0 or
            not 1 <= seasonal_months <= perennial_months <= 12 or
            int(seasonal_months) != seasonal_months or int(perennial_months) != perennial_months or
            int(max_segments) != max_segments or max_segments < 1):
        raise ValueError('invalid game-symbol thresholds or segment budget')
    if cell_coords_xz_m is None:
        zz, xx = np.indices(shape)
        coords = np.column_stack((first[0] + xx.ravel() * spacing, first[1] + zz.ravel() * spacing))
        coordinate_source = 'grid-centres-on-supplied-receiver'
    else:
        coords = np.asarray(cell_coords_xz_m, np.float64)
        if coords.shape not in ((n, 2), shape + (2,)) or not np.isfinite(coords).all():
            raise ValueError('cell_coords_xz_m requires finite original node [N,2] coordinates')
        coords = coords.reshape(n, 2); coordinate_source = 'original-irregular-mesh-nodes'
    raw_active = (np.isfinite(q) & (q >= min_active_q_m3_s)).any(axis=0) & ~ocean & edges
    active = (raw_active | (area >= dry_valley_min_area_m2)) & (area >= min_display_area_m2) & ~ocean & edges
    # Default remains byte-for-byte compatible with legacy display-area callers.
    # Explicit display profiles separate channel eligibility from monthly activity.
    recipe = None
    if cartography_profile is not None:
        if cartography_profile not in ('all-active', 'overview-mainstem-30km'):
            raise ValueError('unknown cartography profile')
        if min_display_area_m2 != 0.:
            raise ValueError('cartography profile requires min_display_area_m2=0')
        lines, active, recipe, edge_length = _cartographic_lines(
            rec, order, raw_active, coords, area, shape, first, spacing, cartography_profile, max_segments)
    else:
        # Deliberately NOT gh.active_rivers: that function forces downstream activity.
        lines = gh.trace_lines(rec, area, active, shape, first, spacing)
    if len(lines) > max_segments:
        raise ValueError(f'skeleton exceeds max_segments ({len(lines)} > {max_segments})')
    vectors = []
    seconds = days * 86400.0
    for line in lines:
        nodes = line['nodes']; anchors = nodes[:-1]; head = anchors[0]
        vector = dict(line, anchor_cell=head, anchor_cell_zx=list(divmod(head, shape[1])),
                      points_xz_m=coords[nodes].tolist(), edge_anchor_cells=anchors,
                      edge_monthly_q_m3_s=[[float(v) if np.isfinite(v) else None for v in q[:, a]]
                                          for a in anchors],
                      symbol_width=1.0, blue=False)
        vector.update(_flow_stats(q[:, head], seconds, min_active_q_m3_s, perennial_months, seasonal_months))
        vectors.append(vector)
    draws = [_draw_month(vectors, q[m], wet[m], ocean, coords, min_active_q_m3_s, m + 1)
             for m in range(12)]
    if any(len(month) > max_segments for month in draws):
        raise ValueError('monthly draw slices exceed max_segments; no clipping or auto-tuning')
    parameters = dict(min_active_q_m3_s=float(min_active_q_m3_s), perennial_months=int(perennial_months),
                      seasonal_months=int(seasonal_months), dry_valley_min_area_m2=float(dry_valley_min_area_m2),
                      max_segments=int(max_segments), month_days=days.tolist(),
                      min_display_area_m2=float(min_display_area_m2))
    binding = dict(schema=SCHEMA, grid=dict(shape_zx=shape, first_xz_m=first, spacing_m=spacing),
                   parameters=parameters, coordinate_source=coordinate_source)
    if recipe is not None:
        binding['cartography'] = recipe
    identity = hashlib.sha256(json.dumps(binding, sort_keys=True).encode())
    for array in (rec, order, q, area, ocean, wet, coords):
        identity.update(np.ascontiguousarray(array).tobytes())
    counts = {key: sum(v['flow_class'] == key for v in vectors)
              for key in ('perennial', 'seasonal', 'intermittent', 'dry_valley', 'unknown')}
    result = dict(**binding, identity=identity.hexdigest(), vectors=vectors, draw_segments=draws,
                 summary=dict(segments=len(vectors), classes=counts,
                              raw_active_edge_count=int(raw_active.sum()),
                              display_candidate_edge_count=int(active.sum()),
                              display_omitted_active_edges=int((raw_active & ~active).sum()),
                              monthly_draw_segments=[len(v) for v in draws]),
                 display_scope='cartographic area visibility only; omitted active edges retain original raster Q and water budget',
                classification_scope='supplied finite year; NOT long-term perennial certification; NOT permanent-channel existence certification',
                class_labels=dict(perennial='本年全年有流（按声明月数阈值）', seasonal='本年季节性有流',
                                  intermittent='本年间歇有流', dry_valley='本年未达图符流量阈值的候选干谷', unknown='月份未知'),
                stability_scope='same supplied-year graph: invariant under selected month; source-cell ID stable only for same physical head; climate/Q changes may resegment',
                discharge_semantics='actual monthly mean receiver-edge outflow at anchor cell; m3/s',
                symbol_standard='game cartography on coarse grid; width NOT physical river width',
                lake_cut_semantics='monthly wet-node midpoint shore approximation; no wet-wet chords',
                 skeleton_not_blue=True)
    if recipe is not None:
        result['summary'].update(raw_active_length_m=float(edge_length[raw_active].sum()),
            retained_active_length_m=float(edge_length[active].sum()),
            reach_handoffs=sum(v['downstream_id'] is not None for v in vectors),
            monthly_draw_edges=[sum(len(s['edge_anchor_cells']) for s in m) for m in draws])
        result['display_scope'] = 'explicit fixed-scale mainstem cartography only; ALL omitted edges retain original saved Q and water budget'
    return result
