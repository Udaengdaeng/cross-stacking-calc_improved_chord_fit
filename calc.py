import math
import re
from dataclasses import dataclass
from typing import Dict, Any, List, Tuple


D_REF_CM = 63.19  # 205/55R16 approximate OD
P_REF_CM = 45.0


@dataclass
class ChordFitResult:
    fit: bool
    h_insert: float
    c_hole: float
    c_outer: float
    c_outer_eff: float
    margin: float
    theta_deg: float


def parse_tire_spec(spec: str) -> Tuple[float, float, float, float, float]:
    """Return SW_cm, aspect, rim_in, rim_d_cm, outer_d_cm."""
    m = re.match(r"^\s*(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)\s*R\s*(\d+(?:\.\d+)?)\s*$", spec, re.I)
    if not m:
        raise ValueError("타이어 규격은 예: 205/55R16 형식으로 입력하세요.")
    sw_mm = float(m.group(1))
    aspect = float(m.group(2))
    rim_in = float(m.group(3))

    sw_cm = sw_mm / 10.0
    sidewall_cm = sw_cm * aspect / 100.0
    rim_d_cm = rim_in * 2.54
    outer_d_cm = rim_d_cm + 2.0 * sidewall_cm
    return sw_cm, aspect, rim_in, rim_d_cm, outer_d_cm


def chord(radius: float, offset_from_center: float) -> float:
    """Chord length at signed offset from circle center."""
    v = radius * radius - offset_from_center * offset_from_center
    if v <= 0:
        return 0.0
    return 2.0 * math.sqrt(v)


def evaluate_chord_fit(
    D: float,
    d: float,
    theta_deg: float,
    inner_margin: float = 1.05,
    outer_margin: float = 0.95,
    rubber_allowance: float = 1.08,
    max_hole_ratio: float = 0.90,
    samples: int = 240,
) -> ChordFitResult:
    """
    Relaxed fit test:
    receiving tire hole chord >= inserted tire effective outer chord.

    h_insert is the penetration depth measured from the lower tangent of the receiving hole.
    The inserted tire's required outer chord is reduced by an angle projection factor and a rubber allowance.
    """
    R = D / 2.0
    r = d / 2.0
    theta = math.radians(theta_deg)

    # Tilt/projection relief: larger theta lets the entering tire present a narrower effective section.
    # Clamp avoids unrealistically large benefit at extreme angles.
    projection_factor = max(0.45, math.cos(theta))

    best = ChordFitResult(False, 0.0, 0.0, 0.0, 0.0, -1e9, theta_deg)
    h_max = max(0.1, 2.0 * r * max_hole_ratio)

    for i in range(1, samples + 1):
        h = h_max * i / samples

        # Hole chord at depth h from the lower edge of the inner circle.
        y_hole = -r + h
        c_hole = chord(r, y_hole)

        # Outer tire section that must pass through the hole.
        # The vertical depth that actually cuts into the entering tire is moderated by sin(theta),
        # because shallow insertion presents less of the outer circle to the hole.
        h_outer = min(2.0 * R, h * max(0.15, math.sin(theta)))
        y_outer = -R + h_outer
        c_outer = chord(R, y_outer)
        c_outer_eff = c_outer * projection_factor

        # Relaxed judgement. User-requested style: inner chord slightly advantaged, outer chord slightly softened.
        lhs = c_hole * inner_margin * rubber_allowance
        rhs = c_outer_eff * outer_margin
        margin = lhs - rhs

        if margin >= 0 and h > best.h_insert:
            best = ChordFitResult(True, h, c_hole, c_outer, c_outer_eff, margin, theta_deg)
        elif not best.fit and margin > best.margin:
            best = ChordFitResult(False, h, c_hole, c_outer, c_outer_eff, margin, theta_deg)

    return best


def calculate_loading(
    spec: str,
    W_c: float = 235.0,
    H_c: float = 270.0,
    L_c: float = 1203.0,
    p_base: float = 45.0,
    alpha_deg: float = 30.0,
    theta_deg: float = 30.0,
    height_tolerance: float = 1.5,
    inner_margin: float = 1.05,
    outer_margin: float = 0.95,
    rubber_allowance: float = 1.08,
    max_hole_ratio: float = 0.90,
    auto_theta: bool = False,
    theta_min: float = 10.0,
    theta_max: float = 65.0,
    theta_step: float = 1.0,
) -> Dict[str, Any]:
    SW, aspect, rim_in, d, D = parse_tire_spec(spec)
    alpha = math.radians(alpha_deg)

    # Width pitch scaled from 205/55R16 reference, but never below tire section width.
    p = max(SW * 1.02, p_base * D / D_REF_CM)
    n_width = max(1, int(math.floor((W_c - D) / p)) + 1) if W_c >= D else 0
    n_width_tilted = n_width
    W1 = D + max(0, n_width - 1) * p
    W2 = D + max(0, n_width_tilted - 1) * p
    gap = max(0.0, W_c - max(W1, W2))

    # Evaluate chord fit. Optionally scan theta and choose the deepest feasible insertion.
    candidates: List[ChordFitResult] = []
    if auto_theta:
        t = theta_min
        while t <= theta_max + 1e-9:
            candidates.append(evaluate_chord_fit(D, d, t, inner_margin, outer_margin, rubber_allowance, max_hole_ratio))
            t += theta_step
        feasible = [x for x in candidates if x.fit]
        if feasible:
            fit_result = max(feasible, key=lambda x: (x.h_insert, x.margin))
        else:
            fit_result = max(candidates, key=lambda x: x.margin)
        theta_deg = fit_result.theta_deg
    else:
        fit_result = evaluate_chord_fit(D, d, theta_deg, inner_margin, outer_margin, rubber_allowance, max_hole_ratio)
        candidates = [fit_result]

    overlap_height = fit_result.h_insert if fit_result.fit else max(0.0, fit_result.h_insert * 0.35)

    # Pair height: two tilted rows minus relaxed interlock depth.
    raw_pair = 2.0 * D * max(0.05, math.sin(alpha))
    H_pair = max(SW * 1.15, raw_pair - overlap_height)

    first_layer_height = max(SW, D * max(0.05, math.sin(alpha)))
    available_after_first = max(0.0, H_c + height_tolerance - first_layer_height)
    n_pair = max(0, int(math.floor(available_after_first / H_pair))) if H_pair > 0 else 0
    n_cross_rows = 1 + 2 * n_pair
    selected_stack_height = first_layer_height + n_pair * H_pair
    selected_height_margin = H_c - selected_stack_height

    N_cross = n_width + 2 * n_pair * n_width_tilted

    # Edge columns: only add side tires if actual side gap can accept tire section width.
    edge_columns = 0
    if gap >= SW:
        edge_columns = 1 if gap < 2 * SW else 2
    n_edge_H = int(math.floor(H_c / max(SW, 1e-6))) if edge_columns else 0
    N_edge = edge_columns * n_edge_H
    N_face = N_cross + N_edge

    # Length direction: repeated face layers by section width.
    n_L = max(1, int(math.floor(L_c / max(SW, 1e-6))))
    N_total = N_face * n_L

    container_fit = (W1 <= W_c + 1e-6) and (selected_stack_height <= H_c + height_tolerance + 1e-6) and fit_result.fit

    return {
        "spec": spec,
        "SW": SW,
        "aspect": aspect,
        "rim_in": rim_in,
        "d": d,
        "D": D,
        "r": D / D_REF_CM,
        "p": p,
        "c": fit_result.c_hole,
        "L": fit_result.h_insert,
        "alpha_deg": alpha_deg,
        "theta_deg": theta_deg,
        "n_width": n_width,
        "n_width_tilted": n_width_tilted,
        "W1": W1,
        "W2": W2,
        "gap": gap,
        "edge_left_gap": gap / 2.0,
        "edge_right_gap": gap / 2.0,
        "edge_left_fit": gap / 2.0 >= SW,
        "edge_right_fit": gap / 2.0 >= SW,
        "edge_start_z": SW / 2.0,
        "h_need_edge": SW,
        "h3_edge": H_c,
        "a": fit_result.h_insert,
        "one_len": SW,
        "two_len": 2 * SW,
        "overlap_height": overlap_height,
        "H_pair": H_pair,
        "top_single_layer": False,
        "half_pair_height": H_pair / 2.0,
        "n_pair_strict": max(0, int(math.floor(max(0.0, H_c - first_layer_height) / H_pair))) if H_pair > 0 else 0,
        "n_pair_tolerance": n_pair,
        "n_pair": n_pair,
        "stack_model": "base_layer_pairs_chord_fit",
        "first_layer_height": first_layer_height,
        "selected_stack_height": selected_stack_height,
        "n_cross_rows": n_cross_rows,
        "strict_height_margin": H_c - (first_layer_height + (max(0, int(math.floor(max(0.0, H_c - first_layer_height) / H_pair))) if H_pair > 0 else 0) * H_pair),
        "tolerance_height_margin": H_c + height_tolerance - selected_stack_height,
        "selected_height_margin": selected_height_margin,
        "N_cross": N_cross,
        "edge_columns": edge_columns,
        "n_edge_H": n_edge_H,
        "N_edge": N_edge,
        "N_face": N_face,
        "n_L": n_L,
        "N_total": N_total,
        "container_fit": container_fit,
        "chord_fit": fit_result.fit,
        "c_hole": fit_result.c_hole,
        "c_outer": fit_result.c_outer,
        "c_outer_eff": fit_result.c_outer_eff,
        "chord_margin": fit_result.margin,
        "inner_margin": inner_margin,
        "outer_margin": outer_margin,
        "rubber_allowance": rubber_allowance,
        "max_hole_ratio": max_hole_ratio,
        "theta_candidates": [x.__dict__ for x in candidates],
        "W_c": W_c,
        "H_c": H_c,
        "L_c": L_c,
    }
