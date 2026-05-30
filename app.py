import pandas as pd
import streamlit as st

from calc import calculate_loading
from visualize import create_stack_figure


st.set_page_config(page_title="40HFT Tire Cross Stack", layout="wide")


def _format_value(value):
    if isinstance(value, float):
        return f"{value:,.2f}"
    return value


def _metrics_table(result):
    rows = [
        ("입력 타이어 규격", result["spec"], ""),
        ("SW", result["SW"], "cm"),
        ("림 직경 d", result["d"], "cm"),
        ("외경 D", result["D"], "cm"),
        ("스케일 r", result["r"], ""),
        ("폭 방향 전진량 p", result["p"], "cm"),
        ("접촉 현 길이 c", result["c"], "cm"),
        ("구멍 내부 현 c_hole", result.get("c_hole", "-"), "cm"),
        ("타이어 외부 현 c_outer", result.get("c_outer", "-"), "cm"),
        ("현 비율 c_hole/c_outer", result.get("chord_fit_ratio_actual", "-"), ""),
        ("사용자 허용 비율", result.get("chord_fit_ratio_threshold", "-"), ""),
        ("현 비교 fit", "yes" if result.get("chord_fit", True) else "no", ""),
        ("높이 공식 L", result["L"], "cm"),
        ("alpha_deg", result["alpha_deg"], "deg"),
        ("theta_deg", result["theta_deg"], "deg"),
        ("n_width", result["n_width"], "개"),
        ("n_width_tilted", result["n_width_tilted"], "개"),
        ("Row 1 폭 W1", result["W1"], "cm"),
        ("Row 2 폭 W2", result["W2"], "cm"),
        ("gap", result["gap"], "cm"),
        ("left edge actual gap", result["edge_left_gap"], "cm"),
        ("right edge actual gap", result["edge_right_gap"], "cm"),
        ("left edge fit", "yes" if result["edge_left_fit"] else "no", ""),
        ("right edge fit", "yes" if result["edge_right_fit"] else "no", ""),
        ("edge start z", result["edge_start_z"], "cm"),
        ("edge h_need", result["h_need_edge"], "cm"),
        ("edge h3", result["h3_edge"], "cm"),
        ("a", result["a"], "cm"),
        ("one_len", result["one_len"], "cm"),
        ("two_len", result["two_len"], "cm"),
        ("overlap_height", result["overlap_height"], "cm"),
        ("H_pair", result["H_pair"], "cm"),
        ("top single layer", result["top_single_layer"], "?"),
        ("half pair height", result["half_pair_height"], "cm"),
        ("strict 기준 n_pair", result["n_pair_strict"], "쌍"),
        ("tolerance 적용 n_pair", result["n_pair_tolerance"], "쌍"),
        ("최종 사용 n_pair", result["n_pair"], "쌍"),
        ("stack model", result["stack_model"], ""),
        ("1층 기준 높이", result["first_layer_height"], "cm"),
        ("선택 기준 총 stack 높이", result["selected_stack_height"], "cm"),
        ("크로스 row 수", result["n_cross_rows"], "줄"),
        ("strict 초과/여유 높이", result["strict_height_margin"], "cm"),
        ("tolerance 초과/여유 높이", result["tolerance_height_margin"], "cm"),
        ("선택 기준 초과/여유 높이", result["selected_height_margin"], "cm"),
        ("N_cross", result["N_cross"], "개/단면"),
        ("edge column 수", result["edge_columns"], "열"),
        ("n_edge_H", result["n_edge_H"], "개/측면"),
        ("N_edge", result["N_edge"], "개/단면"),
        ("N_face", result["N_face"], "개/단면"),
        ("n_L", result["n_L"], "층"),
        ("N_total", result["N_total"], "개"),
        ("컨테이너 적합 여부", "적합" if result["container_fit"] else "초과", ""),
    ]
    return pd.DataFrame(rows, columns=["항목", "값", "단위"])


with st.sidebar:
    st.header("Input")
    tire_spec = st.text_input("Tire spec", value="205/55R16")

    st.divider()
    st.subheader("Angle")

    alpha_deg = st.number_input(
        "alpha_deg: 타이어 기울기 각도 [deg]",
        min_value=0.0,
        max_value=89.0,
        value=30.0,
        step=1.0,
        help="시각화에서 타이어가 좌우로 기울어지는 각도이며, H_pair 계산의 sin(alpha)에 들어갑니다.",
    )

    theta_deg = st.number_input(
        "theta_deg: 꽈배기/끼임 각도 [deg]",
        min_value=0.0,
        max_value=89.0,
        value=30.0,
        step=1.0,
        help="overlap_height 계산식의 cos(theta), tan(theta)에 들어가는 각도입니다.",
    )

    same_angle = st.checkbox(
        "alpha_deg와 theta_deg를 같은 값으로 사용",
        value=False,
    )

    if same_angle:
        theta_deg = alpha_deg
        st.caption(f"현재 theta_deg = alpha_deg = {alpha_deg:.1f}°")

    st.divider()
    st.subheader("Chord Fit")
    chord_fit_ratio = st.slider(
        "끼임 허용 비율: 내부현 / 외부현",
        min_value=0.70,
        max_value=1.00,
        value=0.90,
        step=0.01,
        help=(
            "1.00은 내부현이 외부현 이상이어야 통과, "
            "0.90은 내부현이 외부현의 90% 이상이면 통과로 보는 완화 기준입니다."
        ),
    )
    st.caption(f"현재 기준: 내부현 / 외부현 ≥ {chord_fit_ratio:.2f}")

W_c = 235.0
H_c = 270.0
L_c = 1203.0
p_base = 45.0
c_base = 30.0
l_mode = "scaled_p"
manual_l = 45.0
height_tolerance = 1.5
n_pair_mode = "tolerance"
stack_model = "base_layer_pairs"
render_mode = "front_only"
realistic_tire_mesh = True
tread_detail = True
mesh_quality = "medium"
tire_opacity = 0.82
show_container = True
show_edge_tires = True
show_calculation_table = True

st.title("40HFT 컨테이너 타이어 꽈배기/크로스 적재 계산기")
st.caption("3D 시각화는 보고서 수식 기반 근사 배치이며 실제 충돌 물리 시뮬레이션이 아닙니다.")

try:
    result = calculate_loading(
        tire_spec,
        W_c=W_c,
        H_c=H_c,
        L_c=L_c,
        p_base=p_base,
        c_base=c_base,
        alpha_deg=alpha_deg,
        theta_deg=theta_deg,
        l_mode=l_mode,
        manual_l=manual_l,
        height_tolerance=height_tolerance,
        n_pair_mode=n_pair_mode,
        stack_model=stack_model,
        chord_fit_ratio=chord_fit_ratio,
    )
except ValueError as exc:
    st.error(str(exc))
    st.stop()

st.info(f"현재 적용 각도: alpha_deg = {alpha_deg:.1f}°, theta_deg = {theta_deg:.1f}°")

summary_cols = st.columns(5)
summary_cols[0].metric("n_width", int(result["n_width"]))
summary_cols[1].metric("n_pair", int(result["n_pair"]))
summary_cols[2].metric("N_face", int(result["N_face"]))
summary_cols[3].metric("n_L", int(result["n_L"]))
summary_cols[4].metric("N_total", f"{int(result['N_total']):,}")

section_tab, total_tab, calc_tab = st.tabs(["단면 적재", "전체 적재량", "계산 결과"])

with section_tab:
    st.subheader("단면 3D tire mesh")
    st.caption(
        "한 단면의 꽈배기 적재를 실제 타이어 mesh로 보여줍니다. "
        "배치는 보고서 수식 기반 근사이며 실제 물리 충돌 계산은 수행하지 않습니다."
    )
    fig = create_stack_figure(
        result,
        render_mode=render_mode,
        realistic_tire_mesh=realistic_tire_mesh,
        tread_detail=tread_detail,
        mesh_quality=mesh_quality,
        tire_opacity=tire_opacity,
        show_container=show_container,
        show_edge_tires=show_edge_tires,
    )
    st.plotly_chart(fig, use_container_width=True)

with total_tab:
    st.subheader("전체 적재량")
    total_cols = st.columns(4)
    total_cols[0].metric("단면 적재 N_face", f"{int(result['N_face']):,}")
    total_cols[1].metric("길이 방향 n_L", f"{int(result['n_L']):,}")
    total_cols[2].metric("총 적재 N_total", f"{int(result['N_total']):,}")
    total_cols[3].metric("컨테이너", "적합" if result["container_fit"] else "초과")
    st.caption(
        f"N_total = N_face × n_L = {int(result['N_face']):,} × "
        f"{int(result['n_L']):,} = {int(result['N_total']):,}"
    )
    st.caption(
        "아래 그림은 길이 방향 반복 구조를 앞쪽 3줄로 샘플 표시합니다. "
        f"전체 적재량은 {int(result['n_L']):,}줄 전체를 기준으로 계산됩니다."
    )
    total_fig = create_stack_figure(
        result,
        render_mode="sample_layers",
        realistic_tire_mesh=True,
        tread_detail=False,
        mesh_quality="low",
        tire_opacity=0.68,
        show_container=show_container,
        show_edge_tires=show_edge_tires,
    )
    st.plotly_chart(total_fig, use_container_width=True)
    if st.button("전체 3D 렌더링", help="전체 mesh 렌더링은 타이어 수가 많아 느릴 수 있습니다."):
        full_fig = create_stack_figure(
            result,
            render_mode="full",
            realistic_tire_mesh=True,
            tread_detail=False,
            mesh_quality="low",
            tire_opacity=0.58,
            show_container=show_container,
            show_edge_tires=show_edge_tires,
        )
        st.plotly_chart(full_fig, use_container_width=True)

with calc_tab:
    if show_calculation_table:
        st.subheader("계산 결과")
        table = _metrics_table(result)
        display_table = table.copy()
        display_table["값"] = display_table["값"].map(_format_value)
        st.dataframe(display_table, use_container_width=True, hide_index=True)

with st.expander("205/55R16 검산 포인트", expanded=False):
    st.write(
        "기본 stack model은 `base_layer_pairs`입니다. 1층을 별도 기준층으로 두고, "
        "2-3층/4-5층/...만 꽈배기 pair로 계산합니다. "
        "사이드 타이어는 실제 좌우 빈 폭이 SW 이상일 때만 계산/표시합니다."
    )

with st.expander("층별 꽈배기 수식", expanded=False):
    st.markdown(
        """
        기본 계산은 `1층 단독 + (2,3층), (4,5층), ... 꽈배기 pair` 모델입니다.
        1층만 첫 번째 타이어를 편평하게 두고, 2층 이상은 첫 타이어부터 모두 기울어진 타이어로 계산합니다.

        ```text
        H_pair = 2 * D * sin(alpha) - overlap_height

        overlap_height = (L - a*cos(theta)) * tan(theta)
        기존: a = d/2 - sqrt((d/2)^2 - (c/2)^2)
        수정: 후보 a별 c_hole/c_outer를 비교해 허용비율 이상인 가장 깊은 a 선택
        ```

        1층:

        ```text
        first_layer_height = max(SW, D * sin(alpha))
        z_1_center = first_layer_height / 2
        y_i = D/2 + i*p
        i = 0 orientation = 0도, i >= 1 orientation = +alpha
        n_width_first = max n such that D + (n - 1)*p <= W_c
        ```

        2,3층 pair (`k=1`):

        ```text
        z_pair_base_1 = D
        z_2_center = z_pair_base_1 + H_pair/4
        z_3_center = z_pair_base_1 + 3*H_pair/4
        ```

        4,5층 pair (`k=2`):

        ```text
        z_pair_base_2 = D + H_pair
        z_4_center = z_pair_base_2 + H_pair/4
        z_5_center = z_pair_base_2 + 3*H_pair/4
        ```

        일반식 (`k=1, 2, 3, ...`):

        ```text
        z_pair_base_k = D + (k-1)*H_pair
        z_lower_center = z_pair_base_k + H_pair/4
        z_upper_center = z_pair_base_k + 3*H_pair/4

        Row lower: orientation = +alpha for every i
        Row upper: orientation = -alpha for every i
        n_width_tilted = floor(W_c / p)
        ```

        이 모델은 1층을 별도로 빼므로 기존 보고서 재현용 `report_pairs` 모델보다 총량이 줄어듭니다.
        `report_pairs`는 기존 보고서의 pair 계산 방식만 비교할 때 사용합니다.
        사이드 타이어는 실제 좌우 빈 폭이 SW 이상일 때만 추가합니다.
        """
    )
