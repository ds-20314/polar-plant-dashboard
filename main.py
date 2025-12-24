import streamlit as st
import pandas as pd
from pathlib import Path
import unicodedata
from plotly.subplots import make_subplots
import plotly.express as px
import plotly.graph_objects as go
import io

# =========================
# 기본 설정
# =========================
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

PLOTLY_FONT = dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")

# =========================
# 상수 정의
# =========================
DATA_DIR = Path("data")

SCHOOL_INFO = {
    "송도고": {"ec": 1.0, "color": "#1f77b4"},
    "하늘고": {"ec": 2.0, "color": "#2ca02c"},  # 최적
    "아라고": {"ec": 4.0, "color": "#ff7f0e"},
    "동산고": {"ec": 8.0, "color": "#d62728"},
}

# =========================
# 유틸 함수
# =========================
def nfc(text):
    return unicodedata.normalize("NFC", text)

def find_file_by_keyword(directory: Path, keyword: str):
    keyword = nfc(keyword)
    for file in directory.iterdir():
        if keyword in nfc(file.name):
            return file
    return None

# =========================
# 데이터 로딩
# =========================
@st.cache_data
def load_environment_data():
    env_data = {}
    for school in SCHOOL_INFO.keys():
        file = find_file_by_keyword(DATA_DIR, school)
        if file is None:
            st.error(f"{school} 환경 데이터 파일을 찾을 수 없습니다.")
            continue

        df = pd.read_csv(file)
        df["time"] = pd.to_datetime(df["time"])
        env_data[school] = df

    return env_data

@st.cache_data
def load_growth_data():
    xlsx_file = None
    for file in DATA_DIR.iterdir():
        if "생육결과" in nfc(file.name) and file.suffix == ".xlsx":
            xlsx_file = file
            break

    if xlsx_file is None:
        st.error("생육 결과 XLSX 파일을 찾을 수 없습니다.")
        return {}

    xls = pd.ExcelFile(xlsx_file)
    growth_data = {}

    for sheet in xls.sheet_names:
        df = pd.read_excel(xlsx_file, sheet_name=sheet)
        growth_data[sheet] = df

    return growth_data

# =========================
# 데이터 로딩 실행
# =========================
with st.spinner("데이터 로딩 중..."):
    env_data = load_environment_data()
    growth_data = load_growth_data()

if not env_data or not growth_data:
    st.stop()

# =========================
# 사이드바
# =========================
st.sidebar.title("학교 선택")
school_option = st.sidebar.selectbox(
    "분석 대상",
    ["전체"] + list(SCHOOL_INFO.keys())
)

# =========================
# 타이틀
# =========================
st.title("🌱 극지식물 최적 EC 농도 연구")

tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

# =========================
# Tab 1: 실험 개요
# =========================
with tab1:
    st.subheader("연구 배경 및 목적")
    st.markdown("""
본 연구는 **EC(전기전도도)** 농도 차이가 극지식물의 생육에 미치는 영향을 분석하여  
최적의 EC 조건을 도출하는 것을 목표로 한다.
""")

    table_data = []
    total_count = 0

    for school, info in SCHOOL_INFO.items():
        count = len(growth_data.get(school, []))
        total_count += count
        table_data.append([school, info["ec"], count, info["color"]])

    summary_df = pd.DataFrame(
        table_data,
        columns=["학교", "EC 목표", "개체수", "색상"]
    )
    st.dataframe(summary_df, use_container_width=True)

    avg_temp = pd.concat(env_data.values())["temperature"].mean()
    avg_hum = pd.concat(env_data.values())["humidity"].mean()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("총 개체수", total_count)
    col2.metric("평균 온도(℃)", f"{avg_temp:.2f}")
    col3.metric("평균 습도(%)", f"{avg_hum:.2f}")
    col4.metric("최적 EC", "2.0 (하늘고)")

# =========================
# Tab 2: 환경 데이터
# =========================
with tab2:
    st.subheader("학교별 환경 평균 비교")

    avg_env = []
    for school, df in env_data.items():
        avg_env.append([
            school,
            df["temperature"].mean(),
            df["humidity"].mean(),
            df["ph"].mean(),
            df["ec"].mean()
        ])

    avg_df = pd.DataFrame(
        avg_env,
        columns=["학교", "온도", "습도", "pH", "EC"]
    )

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=["평균 온도", "평균 습도", "평균 pH", "목표 EC vs 실측 EC"]
    )

    fig.add_trace(go.Bar(x=avg_df["학교"], y=avg_df["온도"]), 1, 1)
    fig.add_trace(go.Bar(x=avg_df["학교"], y=avg_df["습도"]), 1, 2)
    fig.add_trace(go.Bar(x=avg_df["학교"], y=avg_df["pH"]), 2, 1)

    fig.add_trace(go.Bar(
        x=avg_df["학교"],
        y=[SCHOOL_INFO[s]["ec"] for s in avg_df["학교"]],
        name="목표 EC"
    ), 2, 2)
    fig.add_trace(go.Bar(
        x=avg_df["학교"],
        y=avg_df["EC"],
        name="실측 EC"
    ), 2, 2)

    fig.update_layout(height=700, font=PLOTLY_FONT, showlegend=True)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("학교별 시계열 데이터")
    target_schools = env_data.keys() if school_option == "전체" else [school_option]

    for school in target_schools:
        df = env_data[school]

        fig_ts = go.Figure()
        fig_ts.add_trace(go.Scatter(x=df["time"], y=df["temperature"], name="온도"))
        fig_ts.add_trace(go.Scatter(x=df["time"], y=df["humidity"], name="습도"))
        fig_ts.add_trace(go.Scatter(x=df["time"], y=df["ec"], name="EC"))
        fig_ts.add_hline(
            y=SCHOOL_INFO[school]["ec"],
            line_dash="dot",
            annotation_text="목표 EC"
        )

        fig_ts.update_layout(
            title=f"{school} 환경 변화",
            font=PLOTLY_FONT
        )
        st.plotly_chart(fig_ts, use_container_width=True)

        with st.expander(f"{school} 환경 데이터 원본"):
            st.dataframe(df)
            buffer = io.BytesIO()
            df.to_excel(buffer, index=False, engine="openpyxl")
            buffer.seek(0)
            st.download_button(
                "CSV 다운로드",
                data=buffer,
                file_name=f"{school}_환경데이터.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# =========================
# Tab 3: 생육 결과
# =========================
with tab3:
    st.subheader("EC별 평균 생중량")

    result = []
    for school, df in growth_data.items():
        result.append([school, df["생중량(g)"].mean()])

    res_df = pd.DataFrame(result, columns=["학교", "평균 생중량"])
    best_school = res_df.loc[res_df["평균 생중량"].idxmax(), "학교"]

    col = st.columns(len(res_df))
    for i, row in res_df.iterrows():
        if row["학교"] == best_school:
            col[i].metric(row["학교"], f"{row['평균 생중량']:.2f} g", "🥇 최고")
        else:
            col[i].metric(row["학교"], f"{row['평균 생중량']:.2f} g")

    metrics = [
        ("생중량(g)", "평균 생중량"),
        ("잎 수(장)", "평균 잎 수"),
        ("지상부 길이(mm)", "평균 지상부 길이"),
        (None, "개체수")
    ]

    fig = make_subplots(rows=2, cols=2, subplot_titles=[m[1] for m in metrics])

    for idx, (col_name, _) in enumerate(metrics):
        r, c = divmod(idx, 2)
        if col_name:
            y = [growth_data[s][col_name].mean() for s in SCHOOL_INFO]
        else:
            y = [len(growth_data[s]) for s in SCHOOL_INFO]

        fig.add_trace(go.Bar(
            x=list(SCHOOL_INFO.keys()),
            y=y
        ), r + 1, c + 1)

    fig.update_layout(height=700, font=PLOTLY_FONT)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("학교별 생중량 분포")
    box_df = pd.concat([
        df.assign(학교=school) for school, df in growth_data.items()
    ])
    fig_box = px.box(box_df, x="학교", y="생중량(g)")
    fig_box.update_layout(font=PLOTLY_FONT)
    st.plotly_chart(fig_box, use_container_width=True)

    st.subheader("상관관계 분석")
    fig1 = px.scatter(box_df, x="잎 수(장)", y="생중량(g)", color="학교")
    fig1.update_layout(font=PLOTLY_FONT)
    st.plotly_chart(fig1, use_container_width=True)

    fig2 = px.scatter(box_df, x="지상부 길이(mm)", y="생중량(g)", color="학교")
    fig2.update_layout(font=PLOTLY_FONT)
    st.plotly_chart(fig2, use_container_width=True)

    with st.expander("생육 데이터 원본 다운로드"):
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            for school, df in growth_data.items():
                df.to_excel(writer, sheet_name=school, index=False)
        buffer.seek(0)

        st.download_button(
            "XLSX 다운로드",
            data=buffer,
            file_name="학교별_생육결과.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
