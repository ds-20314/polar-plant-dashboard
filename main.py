import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import unicodedata
import io

# ===============================
# 기본 설정
# ===============================
st.set_page_config(
    page_title="극지식물 최적 EC 농도 연구",
    layout="wide"
)

# 한글 폰트 (Streamlit)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)

# ===============================
# 유틸 함수
# ===============================
def normalize_name(name: str) -> str:
    return unicodedata.normalize("NFC", name)

def find_files_by_ext(directory: Path, ext: str):
    files = []
    for f in directory.iterdir():
        if normalize_name(f.suffix.lower()) == ext:
            files.append(f)
    return files

# ===============================
# 데이터 로딩
# ===============================
@st.cache_data
def load_environment_data(data_dir: Path):
    env_data = {}

    csv_files = find_files_by_ext(data_dir, ".csv")
    if not csv_files:
        st.error("환경 데이터 CSV 파일을 찾을 수 없습니다.")
        return None

    for file in csv_files:
        school = normalize_name(file.stem.split("_")[0])
        df = pd.read_csv(file)
        env_data[school] = df

    return env_data


@st.cache_data
def load_growth_data(data_dir: Path):
    xlsx_files = find_files_by_ext(data_dir, ".xlsx")
    if not xlsx_files:
        st.error("생육 결과 XLSX 파일을 찾을 수 없습니다.")
        return None

    xlsx_path = xlsx_files[0]
    xls = pd.ExcelFile(xlsx_path)

    growth_data = {}
    for sheet in xls.sheet_names:
        school = normalize_name(sheet)
        growth_data[school] = pd.read_excel(xlsx_path, sheet_name=sheet)

    return growth_data


# ===============================
# 데이터 불러오기
# ===============================
DATA_DIR = Path("data")

with st.spinner("데이터를 불러오는 중입니다..."):
    env_data = load_environment_data(DATA_DIR)
    growth_data = load_growth_data(DATA_DIR)

if env_data is None or growth_data is None:
    st.stop()

schools = sorted(set(env_data.keys()) & set(growth_data.keys()))

ec_conditions = {
    "송도고": 1.0,
    "하늘고": 2.0,
    "아라고": 4.0,
    "동산고": 8.0
}

color_map = {
    "송도고": "#1f77b4",
    "하늘고": "#2ca02c",
    "아라고": "#ff7f0e",
    "동산고": "#d62728"
}

# ===============================
# 사이드바
# ===============================
st.sidebar.title("학교 선택")
selected_school = st.sidebar.selectbox(
    "학교",
    ["전체"] + schools
)

# ===============================
# 제목
# ===============================
st.title("🌱 극지식물 최적 EC 농도 연구")

# ===============================
# 탭 구성
# ===============================
tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

# =====================================================
# Tab 1 실험 개요
# =====================================================
with tab1:
    st.subheader("연구 배경 및 목적")
    st.write(
        """
        본 연구는 학교별 서로 다른 EC 조건에서 극지 식물의 생육 결과를 비교 분석하여  
        **최적 EC 농도 조건을 도출**하는 것을 목적으로 한다.
        """
    )

    summary_rows = []
    total_count = 0
    for school in schools:
        count = len(growth_data[school])
        total_count += count
        summary_rows.append([
            school,
            ec_conditions.get(school),
            count,
            color_map.get(school)
        ])

    summary_df = pd.DataFrame(
        summary_rows,
        columns=["학교명", "EC 목표", "개체수", "색상"]
    )
    st.dataframe(summary_df, use_container_width=True)

    avg_temp = pd.concat([df["temperature"] for df in env_data.values()]).mean()
    avg_hum = pd.concat([df["humidity"] for df in env_data.values()]).mean()

    weight_means = {
        ec_conditions[s]: growth_data[s]["생중량(g)"].mean()
        for s in schools
    }
    optimal_ec = max(weight_means, key=weight_means.get)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총 개체수", total_count)
    c2.metric("평균 온도", f"{avg_temp:.1f} ℃")
    c3.metric("평균 습도", f"{avg_hum:.1f} %")
    c4.metric("최적 EC", f"{ec_conditions[optimal_ec]} (하늘고)" if optimal_ec == "하늘고" else ec_conditions[optimal_ec])

# =====================================================
# Tab 2 환경 데이터
# =====================================================
with tab2:
    st.subheader("학교별 환경 평균 비교")

    rows = []
    for s in schools:
        df = env_data[s]
        rows.append([
            s,
            df["temperature"].mean(),
            df["humidity"].mean(),
            df["ph"].mean(),
            df["ec"].mean(),
            ec_conditions.get(s)
        ])

    avg_df = pd.DataFrame(
        rows,
        columns=["학교", "온도", "습도", "pH", "EC", "목표 EC"]
    )

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=["평균 온도", "평균 습도", "평균 pH", "목표 EC vs 실측 EC"]
    )

    fig.add_trace(go.Bar(x=avg_df["학교"], y=avg_df["온도"]), row=1, col=1)
    fig.add_trace(go.Bar(x=avg_df["학교"], y=avg_df["습도"]), row=1, col=2)
    fig.add_trace(go.Bar(x=avg_df["학교"], y=avg_df["pH"]), row=2, col=1)

    fig.add_trace(go.Bar(x=avg_df["학교"], y=avg_df["목표 EC"], name="목표 EC"), row=2, col=2)
    fig.add_trace(go.Bar(x=avg_df["학교"], y=avg_df["EC"], name="실측 EC"), row=2, col=2)

    fig.update_layout(
        height=700,
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )
    st.plotly_chart(fig, use_container_width=True)

    if selected_school != "전체":
        st.subheader(f"{selected_school} 시계열 변화")
        df = env_data[selected_school]

        ts_fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            subplot_titles=["온도", "습도", "EC"]
        )

        ts_fig.add_trace(go.Scatter(x=df["time"], y=df["temperature"]), row=1, col=1)
        ts_fig.add_trace(go.Scatter(x=df["time"], y=df["humidity"]), row=2, col=1)
        ts_fig.add_trace(go.Scatter(x=df["time"], y=df["ec"]), row=3, col=1)
        ts_fig.add_hline(
            y=ec_conditions[selected_school],
            line_dash="dash",
            row=3, col=1
        )

        ts_fig.update_layout(
            height=700,
            font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
        )
        st.plotly_chart(ts_fig, use_container_width=True)

        with st.expander("환경 데이터 원본"):
            st.dataframe(df)
            csv_buffer = io.BytesIO()
            df.to_csv(csv_buffer, index=False)
            csv_buffer.seek(0)
            st.download_button(
                data=csv_buffer,
                file_name=f"{selected_school}_환경데이터.csv",
                mime="text/csv"
            )

# =====================================================
# Tab 3 생육 결과
# =====================================================
with tab3:
    st.subheader("EC별 평균 생중량")

    growth_summary = []
    for s in schools:
        growth_summary.append([
            s,
            ec_conditions[s],
            growth_data[s]["생중량(g)"].mean()
        ])

    gdf = pd.DataFrame(
        growth_summary,
        columns=["학교", "EC", "평균 생중량"]
    )

    best_idx = gdf["평균 생중량"].idxmax()
    best_row = gdf.loc[best_idx]

    st.metric(
        "최대 평균 생중량",
        f"{best_row['평균 생중량']:.2f} g",
        help="하늘고 (EC 2.0) 최적"
    )

    fig2 = make_subplots(rows=2, cols=2,
                          subplot_titles=["생중량", "잎 수", "지상부 길이", "개체수"])

    fig2.add_trace(go.Bar(x=gdf["학교"], y=gdf["평균 생중량"]), row=1, col=1)

    fig2.add_trace(
        go.Bar(
            x=schools,
            y=[growth_data[s]["잎 수(장)"].mean() for s in schools]
        ),
        row=1, col=2
    )

    fig2.add_trace(
        go.Bar(
            x=schools,
            y=[growth_data[s]["지상부 길이(mm)"].mean() for s in schools]
        ),
        row=2, col=1
    )

    fig2.add_trace(
        go.Bar(
            x=schools,
            y=[len(growth_data[s]) for s in schools]
        ),
        row=2, col=2
    )

    fig2.update_layout(
        height=700,
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("학교별 생중량 분포")
    box_fig = go.Figure()
    for s in schools:
        box_fig.add_trace(
            go.Box(
                y=growth_data[s]["생중량(g)"],
                name=s
            )
        )

    box_fig.update_layout(
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )
    st.plotly_chart(box_fig, use_container_width=True)

    st.subheader("상관관계 분석")
    c1, c2 = st.columns(2)

    with c1:
        sc1 = go.Figure()
        for s in schools:
            sc1.add_trace(
                go.Scatter(
                    x=growth_data[s]["잎 수(장)"],
                    y=growth_data[s]["생중량(g)"],
                    mode="markers",
                    name=s
                )
            )
        sc1.update_layout(
            title="잎 수 vs 생중량",
            font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
        )
        st.plotly_chart(sc1, use_container_width=True)

    with c2:
        sc2 = go.Figure()
        for s in schools:
            sc2.add_trace(
                go.Scatter(
                    x=growth_data[s]["지상부 길이(mm)"],
                    y=growth_data[s]["생중량(g)"],
                    mode="markers",
                    name=s
                )
            )
        sc2.update_layout(
            title="지상부 길이 vs 생중량",
            font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
        )
        st.plotly_chart(sc2, use_container_width=True)

    with st.expander("생육 데이터 원본"):
        combined = pd.concat(
            [growth_data[s].assign(학교=s) for s in schools],
            ignore_index=True
        )
        st.dataframe(combined)

        excel_buffer = io.BytesIO()
        combined.to_excel(excel_buffer, index=False, engine="openpyxl")
        excel_buffer.seek(0)

        st.download_button(
            data=excel_buffer,
            file_name="학교별_생육결과.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
