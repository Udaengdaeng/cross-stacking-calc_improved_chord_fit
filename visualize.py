import math
import plotly.graph_objects as go


def _circle_points(cx, cz, r, n=96):
    xs, zs = [], []
    for i in range(n + 1):
        t = 2 * math.pi * i / n
        xs.append(cx + r * math.cos(t))
        zs.append(cz + r * math.sin(t))
    return xs, zs


def _add_tire(fig, y, z, D, d, name, opacity=0.78, dash=None):
    R = D / 2.0
    r = d / 2.0
    x1, z1 = _circle_points(y, z, R)
    x2, z2 = _circle_points(y, z, r)
    fig.add_trace(go.Scatter(x=x1, y=z1, mode="lines", name=name, opacity=opacity, line=dict(width=2, dash=dash or "solid")))
    fig.add_trace(go.Scatter(x=x2, y=z2, mode="lines", showlegend=False, opacity=opacity, line=dict(width=1, dash="dot")))


def create_stack_figure(
    result,
    render_mode="front_only",
    realistic_tire_mesh=True,
    tread_detail=True,
    mesh_quality="medium",
    tire_opacity=0.82,
    show_container=True,
    show_edge_tires=True,
):
    W = result.get("W_c", 235.0)
    H = result.get("H_c", 270.0)
    D = result["D"]
    d = result["d"]
    p = result["p"]
    n_width = int(result["n_width"])
    n_pair = int(result["n_pair"])
    H_pair = result["H_pair"]
    first_h = result["first_layer_height"]

    fig = go.Figure()

    if show_container:
        fig.add_shape(type="rect", x0=0, y0=0, x1=W, y1=H, line=dict(width=3), fillcolor="rgba(0,0,0,0)")

    # Center the row in width.
    row_w = D + max(0, n_width - 1) * p
    start_y = (W - row_w) / 2.0 + D / 2.0

    # Base row.
    z0 = max(D / 2.0, first_h / 2.0)
    for i in range(n_width):
        _add_tire(fig, start_y + i * p, z0, D, d, f"base {i+1}", tire_opacity)

    # Cross pairs.
    for k in range(n_pair):
        base = first_h + k * H_pair
        z_low = base + H_pair * 0.35
        z_up = base + H_pair * 0.75
        shift = p * 0.5
        for i in range(n_width):
            y = start_y + i * p
            _add_tire(fig, y, z_low, D, d, f"cross L{k+1}" if i == 0 else "", tire_opacity * 0.82)
            _add_tire(fig, min(W - D/2, y + shift), z_up, D, d, f"cross U{k+1}" if i == 0 else "", tire_opacity * 0.68, dash="dash")

    # Optional edge tires in side gaps, shown as vertical column of section-width circles/markers.
    if show_edge_tires and result.get("edge_columns", 0):
        sw = result["SW"]
        n_edge = int(result.get("n_edge_H", 0))
        xs = [sw / 2.0]
        if result["edge_columns"] >= 2:
            xs.append(W - sw / 2.0)
        for x in xs:
            for j in range(n_edge):
                z = sw / 2.0 + j * sw
                if z + sw / 2.0 <= H:
                    fig.add_shape(type="circle", x0=x-sw/2, y0=z-sw/2, x1=x+sw/2, y1=z+sw/2, line=dict(width=1, dash="dot"))

    fig.update_yaxes(scaleanchor="x", scaleratio=1, range=[-5, H + 10], title="height z (cm)")
    fig.update_xaxes(range=[-5, W + 5], title="container width y (cm)")
    fig.update_layout(
        height=720,
        margin=dict(l=20, r=20, t=40, b=20),
        title=f"Front section | chord fit: {'OK' if result.get('chord_fit') else 'NG'} | N_face={int(result['N_face'])}",
        legend=dict(orientation="h"),
    )
    return fig
