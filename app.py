import pandas as pd
import streamlit as st

from calc import calculate_loading
from visualize import create_stack_figure


st.set_page_config(page_title="40HFT Tire Cross Stack - Chord Fit", layout="wide")


def _format_value(value):
    if isinstance(value, float):
        return f"{value:,.2f}"
    return value


def _metrics_table(result):
    keys = [
        ("입력 타이어 규격", "spec", ""),
        ("SW", "SW", "cm"),
        ("림 직경 d", "d", "cm"),
        ("외경 D", "D", "cm"),
        ("폭 방향 전진량 p", "p", "cm"),
        ("alpha_deg", "alpha_deg", "deg"),
        ("theta_deg", "theta_deg", "deg"),
        ("구멍 내부 현 c_hole", "c_hole", "cm"),
        ("타이어 외부 현 c_outer", "c_outer", "cm"),
        ("각도 보정 외부 현 c_outer_eff", "c_outer_eff", "cm"),
        ("현 비교 margin", "chord_margin", "cm"),
        ("chord fit", "chord_fit", ""),
        ("끼임 깊이/overlap_height", "overlap_height", "cm"),
        ("H_pair", "H_pair", "cm"),
        ("first_layer_height", "first_layer_height", "cm"),
        ("n_width", "n_width", "개"),
        ("n_pair", "n_pair", "쌍"),
        ("크로스 row 수", "n_cross_rows", "줄"),
        ("N_cross", "N_cross", "개/단면"),
        ("edge column 수", "edge_columns", "열"),
        ("N_edge", "N_edge", "개/단면"),
        ("N_face", "N_face", "개/단면"),
        ("n_L", "n_L", "층"),
        ("N_total", "N_total", "개"),
        ("선택 기준 stack 높이", "selected_stack_height", "cm"),
        ("선택 기준 초과/여유 높이", "selected_height_margin", "cm"),
        ("컨테이너 적합 여부", "container_fit", ""),
    ]
    rows = []
    for label, key, unit in keys:
        v = result.get(key, "")
        if isinstance(v, bool):
            v = "yes" if v else "no"
        rows.append((label, v, unit))
    return pd.DataFrame(rows, columns=["항목", "값", "단위"])


with st.sidebar:
    st.header("Input")
    tire_spec = st.text_input("Tire spec", value="205/55R16")

    st.divider()
    st.subheader("Container [cm]")
    W_c = st.number_input("Width W", value=235.0, step=1.0)
    H_c = st.number_input("Height H", value=270.0, step=1.0)
    L_c = st.number_input("Length L", value=1203.0, step=1.0)

    st.divider()
    st.subheader("Angle")
    alpha_deg = st.number_input("alpha_deg: 타이어 기울기 각도", min_value=1.0, max_value=89.0, value=30.0, step=1.0)
    auto_theta = st.checkbox("theta 자동 탐색", value=False)
    theta_deg = st.number_input("theta_deg: 끼임/진입 각도", min_value=1.0, max_value=89.0, value=30.0, step=1.0, disabled=auto_theta)
    same_angle = st.checkbox("alpha_deg와 theta_deg를 같은 값으로 사용", value=False, disabled=auto_theta)
    if same_angle and not auto_theta:
        theta_deg = alpha_deg

    st.divider()
    st.subheader("Chord fit tolerance")
    inner_margin = st.slider("구멍 내부 현 완화계수", 1.00, 1.20, 1.05, 0.01)
    outer_margin = st.slider("외부 현 완화계수", 0.80, 1.00, 0.95, 0.01)
    rubber_allowance = st.slider("고무 변형 허용계수", 1.00, 1.25, 1.08, 0.01)
    max_hole_ratio = st.slider("구멍 최대 사용 비율", 0.60, 0.98, 0.90, 0.01)
    height_tolerance = st.slider("높이 허용 오차 [cm]", 0.0, 5.0, 1.5, 0.1)

st.title("40HFT 컨테이너 타이어 꽈배기/크로스 적재 계산기")
st.caption("고정 현 길이 c_base를 쓰지 않고, 구멍 내부 현과 끼워지는 타이어 외부 현을 비교하는 완화 판정 모델입니다.")

try:
    result = calculate_loading(
        tire_spec,
        W_c=W_c,
        H_c=H_c,
        L_c=L_c,
        alpha_deg=alpha_deg,
        theta_deg=theta_deg,
        height_tolerance=height_tolerance,
        inner_margin=inner_margin,
        outer_margin=outer_margin,
        rubber_allowance=rubber_allowance,
        max_hole_ratio=max_hole_ratio,
        auto_theta=auto_theta,
    )
except ValueError as exc:
    st.error(str(exc))
    st.stop()

status = "가능" if result["chord_fit"] else "불리/불가"
st.info(
    f"현 판정: {status} | c_hole={result['c_hole']:.2f}cm, "
    f"c_outer_eff={result['c_outer_eff']:.2f}cm, margin={result['chord_margin']:.2f}cm"
)

summary_cols = st.columns(6)
summary_cols[0].metric("theta", f"{result['theta_deg']:.0f}°")
summary_cols[1].metric("n_width", int(result["n_width"]))
summary_cols[2].metric("n_pair", int(result["n_pair"]))
summary_cols[3].metric("N_face", int(result["N_face"]))
summary_cols[4].metric("n_L", int(result["n_L"]))
summary_cols[5].metric("N_total", f"{int(result['N_total']):,}")

section_tab, calc_tab, logic_tab = st.tabs(["단면 적재", "계산 결과", "판정 로직"])

with section_tab:
    fig = create_stack_figure(result, show_container=True, show_edge_tires=True)
    st.plotly_chart(fig, use_container_width=True)

with calc_tab:
    table = _metrics_table(result)
    display_table = table.copy()
    display_table["값"] = display_table["값"].map(_format_value)
    st.dataframe(display_table, use_container_width=True, hide_index=True)

    if auto_theta:
        st.subheader("theta 후보 탐색 결과")
        cand = pd.DataFrame(result["theta_candidates"])
        if not cand.empty:
            st.dataframe(cand, use_container_width=True, hide_index=True)

with logic_tab:
    st.markdown(
        """
        ### 핵심 변경점

        기존 방식은 `c_base = 30cm`처럼 현 길이를 고정했습니다.  
        이 버전은 고정 현 길이를 쓰지 않고 다음 판정을 사용합니다.

        ```text
        구멍 내부 현 c_hole × 내부 완화계수 × 고무변형 허용계수
        >=
        끼워지는 타이어 외부 현 c_outer_eff × 외부 완화계수
        ```

        즉 엄격하게 `내부현 >= 외부현`만 보지 않고,
        현장 적재에서 발생하는 고무 변형·압입·마찰 고정을 반영해 완화합니다.

        ### 해석 주의

        이 모델은 실제 물리엔진 충돌 계산이 아니라, 단면 기하 기반의 근사 판정입니다.
        따라서 최종 수량 확정 전에는 실제 샘플 적재 또는 3D 충돌 검증이 필요합니다.
        """
    )
