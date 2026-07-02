import streamlit as st
import pandas as pd
import numpy as np
import os
import re

# ==================================================
# 💡 [운영 모드 스위치] 배포 환경에 따라 True / False 만 변경하세요!
# ==================================================
IS_ONLINE_MODE = True  
# True  = 온라인 배포용 (비밀 URL ?admin=true 로 접속해야 카운터 보임)
# False = 오프라인 PC용 (비밀 URL 없이 카운터 버튼 즉시 사용 가능)
# ==================================================

# --- 1. 페이지 기본 설정 ---
st.set_page_config(page_title="2027 대진대 수시 입학상담 솔루션", layout="wide")

st.markdown("""
<style>
    /* 🚨 [보안 패치] 우측 상단 햄버거 메뉴 및 하단 스트림릿 워터마크 완벽 숨김 🚨 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* ========================================= */
    /* 아래부터는 기존 디자인 설정 (절대 지우지 마세요) */
    /* ========================================= */
    .stApp { background-color: #f7f9fc; }
    h1, h2, h3, h4 { color: #000000 !important; }
    
    div.stButton > button[kind="primary"] {
        background-color: #ff4b4b !important;
        border-color: #ff4b4b !important;
        color: #ffffff !important;
        font-weight: 800 !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #e63939 !important;
        border-color: #e63939 !important;
    }
    
    div[data-testid="stMetricValue"] {
        color: #00308F !important;
    }

    div[data-baseweb="select"] > div {
        background-color: #e2e8f0 !important; 
        border: 1px solid #cbd5e1 !important; 
    }

    .grade-title-panel {
        font-size: 15px;
        font-weight: 700;
        color: #00308F;
        border-left: 4px solid #00308F;
        padding-left: 8px;
        margin-bottom: 12px;
        margin-top: 5px;
    }
</style>
""", unsafe_allow_html=True)

# --- 실시간 누적 상담 카운팅 파일 제어 엔진 (방어 로직 적용) ---
COUNT_FILE = "consulting_count.txt"

def get_consulting_count():
    if not os.path.exists(COUNT_FILE):
        try:
            with open(COUNT_FILE, "w", encoding="utf-8") as f:
                f.write("0")
        except:
            pass # 생성 시 충돌 발생하면 무시
        return 0
    try:
        with open(COUNT_FILE, "r", encoding="utf-8") as f:
            return int(f.read().strip())
    except:
        return 0 # 읽기 실패 시 앱 크래시 방지

def increase_consulting_count():
    try:
        current = get_consulting_count()
        new_count = current + 1
        with open(COUNT_FILE, "w", encoding="utf-8") as f:
            f.write(str(new_count))
        return new_count
    except Exception:
        # [동시 접속 방어] 파일 잠금(Lock) 에러 발생 시 앱을 멈추지 않고, 
        # 화면의 성적 산출 기능을 정상 작동시키기 위해 기존 숫자만 반환
        return get_consulting_count()

def increase_consulting_count():
    current = get_consulting_count()
    new_count = current + 1
    with open(COUNT_FILE, "w", encoding="utf-8") as f:
        f.write(str(new_count))
    return new_count

current_total_consultations = get_consulting_count()

if "show_counter" not in st.session_state:
    st.session_state.show_counter = False

col_logo, col_title, col_count = st.columns([0.8, 8.2, 3.0])

with col_logo:
    if os.path.exists("logo.png"): st.image("logo.png", use_column_width=True)
    elif os.path.exists("logo.jpg"): st.image("logo.jpg", use_column_width=True)
    elif os.path.exists("logo.png.png"): st.image("logo.png.png", use_column_width=True)
    elif os.path.exists("스크린샷 2026-06-24 093817.png"): st.image("스크린샷 2026-06-24 093817.png", use_column_width=True)

with col_title:
    st.title("2027학년도 대진대학교 수시 입학상담 솔루션")

with col_count:
    if IS_ONLINE_MODE:
        try:
            is_admin = st.query_params.get("admin") == "true"
        except AttributeError:
            is_admin = st.experimental_get_query_params().get("admin", [""])[0] == "true"
    else:
        is_admin = True
        
    if is_admin:
        if st.button("📊 상담 건수 확인", use_container_width=True):
            st.session_state.show_counter = not st.session_state.show_counter
        
        if st.session_state.show_counter:
            st.metric(label="수시 상담 누적 건수", value=f"{current_total_consultations} 건")

st.markdown(
    "학생부우수자, 학교장추천전형 : 일반/진로 구분 없이 입력 (A/B/C 입력 시 진로과목 인식) | 상위 18과목 반영 (진로 최대 8과목) | 미달 시 9등급 적용 <br>"
    "💡 **학생부종합전형은 전과목 반영**", 
    unsafe_allow_html=True
)

# --- 2. 스마트 입시 결과 데이터 로드 ---
@st.cache_data
def load_admission_data():
    db = {}
    files = os.listdir(".")
    targets = {"학생부우수자": "학생부우수자", "윈윈대진": "윈윈대진", "학교장추천": "학교장추천"}

    for track_name, keyword in targets.items():
        matched_file = None
        for f in files:
            if keyword in f and not f.startswith("~"):
                matched_file = f
                break

        if matched_file:
            try:
                if matched_file.endswith(".csv"):
                    temp_df = pd.read_csv(matched_file, encoding="utf-8-sig", header=None)
                else:
                    temp_df = pd.read_excel(matched_file, header=None)

                idx_mojib = -1
                for i in range(min(5, len(temp_df))):
                    if any("모집단위" in str(x).replace(" ", "") for x in temp_df.iloc[i].values):
                        idx_mojib = i
                        break
                        
                if idx_mojib != -1:
                    row_top = pd.Series(temp_df.iloc[idx_mojib].values).ffill().fillna("").astype(str)
                    row_bottom = pd.Series(temp_df.iloc[idx_mojib + 1].values).fillna("").astype(str)
                    
                    new_cols = []
                    for t, b in zip(row_top, row_bottom):
                        t = t.replace("\n", "").strip()
                        b = b.replace("\n", "").strip()
                        if t == b or b == "" or b == "nan":
                            new_cols.append(t)
                        elif t == "" or t == "nan":
                            new_cols.append(b)
                        else:
                            new_cols.append(f"{t}_{b}")
                            
                    temp_df.columns = new_cols
                    temp_df = temp_df.iloc[idx_mojib + 2:].reset_index(drop=True)
                    temp_df.rename(columns=lambda x: "모집단위" if "모집단위" in x else x, inplace=True)
                
                db[track_name] = temp_df
            except Exception as e:
                pass

    dummy_data = pd.DataFrame({"모집단위": ["데이터 없음"], "평균": [0.0], "최저": [0.0], "최고": [0.0]})

    for track_name in targets.keys():
        if track_name not in db or db[track_name].empty:
            db[track_name] = dummy_data

    return db

db = load_admission_data()

# --- 3. 전형 및 학과 선택 UI ---
st.write("---")
col_sel1, col_sel2 = st.columns(2)
with col_sel1:
    track_list = ["학생부우수자", "윈윈대진", "학교장추천"]
    selected_track = st.selectbox("전형 선택", track_list)
with col_sel2:
    if "모집단위" in db[selected_track].columns:
        custom_order = [
            "영어영문학과", "문예콘텐츠창작학과", "역사·문화콘텐츠학과", "경영학과",
            "글로벌경제학과", "국제통상학과", "공공인재법학과", "국제지역학과",
            "중국학과", "아동학과", "사회복지학과", "미디어커뮤니케이션학과",
            "행정정보학과", "문헌정보학과", "의생명과학과", "식품영양학과",
            "간호학과", "보건경영학과", "스포츠건강과학과", "공학자율학부",
            "전기공학과", "건축공학과", "AI건설융합공학과", "스마트시티·환경공학과",
            "데이터경영산업공학과", "반도체융합공학과", "IT기계공학과", "화학공학과",
            "컴퓨터공학과", "스마트융합보안학과", "AI빅데이터공학과", "스마트모빌리티공학과",
            "자율전공학부"
        ]
        raw_dept_list = db[selected_track]["모집단위"].dropna().unique().tolist()
        
        dept_list = sorted([d for d in raw_dept_list if d in custom_order], key=lambda x: custom_order.index(x))
        dept_list += sorted([d for d in raw_dept_list if d not in custom_order])
    else:
        dept_list = ["데이터 로딩 실패"]

    selected_dept = st.selectbox("모집단위(학과) 선택", dept_list)

eval_methods = {
    "학생부우수자": "💡 **[학생부우수자] 전형 방법 :** 교과 70% + 면접 30%[면접 5분 이내]",
    "학교장추천": "💡 **[학교장추천] 전형 방법 :** 교과 100%",
    "윈윈대진": "💡 **[윈윈대진] 전형 방법 :** 1단계: 서류 100% ➔ 2단계: 1단계 성적 70% + 면접 30%[면접 10분 이내]"
}
st.info(eval_methods[selected_track])

if selected_track == "학생부우수자" and selected_dept != "데이터 로딩 실패":
    humanities = ["영어영문학과", "문예콘텐츠창작학과", "역사·문화콘텐츠학과", "경영학과", "글로벌경제학과", "국제통상학과", "공공인재법학과", "국제지역학과", "중국학과", "아동학과", "사회복지학과", "미디어커뮤니케이션학과", "행정정보학과", "문헌정보학과"]
    sciences = ["의생명과학과", "식품영양학과", "간호학과", "보건경영학과", "스포츠건강과학과", "공학자율학부", "전기공학과", "건축공학과", "AI건설융합공학과", "스마트시티·환경공학과", "데이터경영산업공학과", "반도체융합공학과", "IT기계공학과", "화학공학과", "컴퓨터공학과", "스마트융합보안학과", "AI빅데이터공학과", "스마트모빌리티공학과"]
    undecided = ["자율전공학부"]
    
    with st.expander(f"🗣️ [{selected_dept}] 면접 기출 문항 확인", expanded=False):
        st.markdown(f"**※ {selected_dept} 면접 문항**")
        q1 = "**1.** 자율주행차, 의료 AI 등 기술 발전으로 인해 알고리즘이 생사와 관련된 결정을 내리는 상황이 현실화되고 있습니다. 이러한 윤리적 판단을 인간이 아닌 AI에게 맡길 수 있는지에 대해 찬반 양 측의 입장을 고려하여 본인의 견해를 설명하시오."
        
        if selected_dept in humanities:
            st.caption("📌 인문사회계열(아래 3문항 중 1문항 출제)")
            st.write(q1)
            st.write("**2.** 최근 '워라밸(Work-Life Balance)' 중시 문화가 확산되면서, 주 4일 근무제 도입을 지지하는 주장과 기업 경쟁력 약화 및 생산성 저하를 우려하는 반론이 공존하고 있습니다. 주 4일 근무제가 우리 사회에 미칠 영향을 긍정적·부정적 측면에서 분석하고, 본인의 견해를 설명하시오.")
            st.write("**3.** 최근 전쟁과 국제 갈등으로 인해 석유와 가스 가격이 크게 오르면서 전기요금과 물가도 함께 상승하고 있습니다. 이런 상황이 계속되면 국민들의 생활 부담이 커지고 기업 활동에도 어려움이 생길 수 있습니다. 이러한 문제를 해결하기 위해 정부가 가장 먼저 해야 할 일은 무엇이라고 생각하는지 본인의 견해를 설명하시오.")
        elif selected_dept in sciences:
            st.caption("📌 자연공학계열(아래 3문항 중 1문항 출제)")
            st.write(q1)
            st.write("**2.** 최근 태양광·풍력 등 신재생에너지 비중이 빠르게 증가하고 있지만, 전력의 안정적 공급에는 한계가 있다는 지적도 있습니다. 이러한 한계의 원인과 이를 극복하기 위한 기술적 해결방안을 설명해 보세요.")
            st.write("**3.** 현실 세계를 가상 공간에 똑같이 구현하는 '디지털 트윈(Digital Twin)' 기술이 도시, 공장, 의료 등 다양한 분야에 적용되고 있습니다. 디지털 트윈이 어떤 원리로 작동하며, 이 기술이 가져올 수 있는 사회적 변화 또는 한계를 설명해 보세요.")
        elif selected_dept in undecided:
            st.caption("📌 자율전공학부(아래 3문항 중 1문항 출제)")
            st.write(q1)
            st.write("**2.** 최근 '워라밸(Work-Life Balance)' 중시 문화가 확산되면서, 주 4일 근무제 도입을 지지하는 주장과 기업 경쟁력 약화 및 생산성 저하를 우려하는 반론이 공존하고 있습니다. 주 4일 근무제가 우리 사회에 미칠 영향을 긍정적·부정적 측면에서 분석하고, 본인의 견해를 설명하시오.")
            st.write("**3.** 최근 태양광·풍력 등 신재생에너지 비중이 빠르게 증가하고 있지만, 전력의 안정적 공급에는 한계가 있다는 지적도 있습니다. 이러한 한계의 원인과 이를 극복하기 위한 기술적 해결방안을 설명해 보세요.")
        else:
            st.warning("선택하신 학과의 계열 정보가 매핑되지 않았습니다. 대학별 고사 안내서를 확인해주세요.")
        
        st.write("---")
        st.write("**4. 지정문항 :** 우리학과에 지원한 동기가 무엇인가요?")

# --- 4. 학생부 성적 입력 UI ---
st.write("---")

# [핵심 패치 1] 초기화 번호표(카운터)를 만듭니다.
if "reset_key" not in st.session_state:
    st.session_state.reset_key = 0

# 제목과 초기화 버튼을 좌우로 배치하기 위해 컬럼 분할 (비율 8.5 : 1.5)
col_grade_title, col_reset = st.columns([8.5, 1.5])

with col_grade_title:
    st.subheader("📝 학생부 성적 입력")

with col_reset:
    # 다음 학생 상담을 위한 리셋 버튼
    if st.button("🔄 초기화", use_container_width=True):
        # [핵심 패치 2] 리셋 버튼을 누르면 번호표를 1 올리고 화면을 새로고침합니다.
        st.session_state.reset_key += 1
        st.rerun() 

def get_empty_df():
    return pd.DataFrame([{"과목명": None, "이수단위": "", "등급/성취도": ""} for _ in range(15)])

col_config = {
    "과목명": st.column_config.SelectboxColumn(
        "과목명",
        options=["국어", "영어", "수학", "사회", "한국사", "과학"],
        required=False
    )
}

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown('<div class="grade-title-panel">🌱 1학년 성적</div>', unsafe_allow_html=True)
    # [핵심 패치 3] key 이름표에 번호표(reset_key)를 붙여 계속 새로운 표로 인식하게 만듭니다.
    df_1 = st.data_editor(get_empty_df(), column_config=col_config, num_rows="dynamic", key=f"df1_{st.session_state.reset_key}", use_container_width=True)
with col2:
    st.markdown('<div class="grade-title-panel">🌿 2학년 성적</div>', unsafe_allow_html=True)
    df_2 = st.data_editor(get_empty_df(), column_config=col_config, num_rows="dynamic", key=f"df2_{st.session_state.reset_key}", use_container_width=True)
with col3:
    st.markdown('<div class="grade-title-panel">🌳 3학년[1학기] 성적</div>', unsafe_allow_html=True)
    df_3 = st.data_editor(get_empty_df(), column_config=col_config, num_rows="dynamic", key=f"df3_{st.session_state.reset_key}", use_container_width=True)

# --- 5. 스마트 산출 엔진 ---
def calculate_score(df_list):
    gen_u, gen_g = [], []
    car_u, car_g = [], []

    for df in df_list:
        for _, row in df.iterrows():
            unit_raw = row["이수단위"]
            grade_str = str(row["등급/성취도"]).strip().upper()

            try: unit = float(unit_raw)
            except: unit = 0.0

            if unit == 0.0 and grade_str not in ["", "NAN", "NONE"]:
                unit = 1.0

            if unit > 0 and grade_str not in ["", "NAN", "NONE"]:
                if grade_str.isnumeric() or grade_str.replace(".", "", 1).isdigit():
                    grade = float(grade_str)
                    if 1 <= grade <= 9:
                        gen_u.append(unit)
                        gen_g.append(grade)
                else:
                    grade_map = {"A": 1.0, "B": 2.0, "C": 4.0}
                    if grade_str in grade_map:
                        grade = grade_map[grade_str]
                        car_u.append(unit)
                        car_g.append(grade)

    df_car = pd.DataFrame({"unit": car_u, "grade": car_g})
    df_car = df_car.sort_values(by=["grade", "unit"], ascending=[True, False]).head(8)

    df_gen = pd.DataFrame({"unit": gen_u, "grade": gen_g})
    df_pool = pd.concat([df_gen, df_car], ignore_index=True)
    df_pool = df_pool.sort_values(by=["grade", "unit"], ascending=[True, False]).head(18)

    actual_count = len(df_pool)
    sum_unit = df_pool["unit"].sum()
    sum_grade_unit = (df_pool["unit"] * df_pool["grade"]).sum()

    if actual_count < 18:
        missing = 18 - actual_count
        sum_unit += missing * 1.0
        sum_grade_unit += missing * 1.0 * 9.0

    final_score = round(sum_grade_unit / sum_unit, 2) if sum_unit > 0 else 0.0
    return final_score, actual_count

# --- 6. 결과 출력 패널 ---
st.write("---")

col_left, col_right = st.columns([6, 4])

with col_left:
    with st.container(border=True):
        st.markdown("### 🎯 성적 산출")
        
        # [수정 1] 버튼, 점수, 신호등이 들어갈 3분할 레이아웃 세팅
        col_btn, col_metric, col_badge = st.columns([3, 2, 3])
        with col_btn:
            calc_clicked = st.button("성적 산출", use_container_width=True, type="primary")
            manual_score = st.number_input("직접 입력(선택)", min_value=0.0, max_value=9.0, value=0.0, step=0.01)
            
        if calc_clicked or manual_score > 0:
            if calc_clicked:
                current_total_consultations = increase_consulting_count()
                
            calc_score, subj_count = calculate_score([df_1, df_2, df_3])
            final_score = manual_score if manual_score > 0 else calc_score
            
            with col_metric:
                st.metric(label="대진대 환산 등급", value=f"{final_score:.2f} 등급", delta=f"반영과목: {subj_count}개", delta_color="off")
            
            # [수정 2] 신호등을 그릴 빈 캔버스 예약
            badge_placeholder = col_badge.empty()
    
            st.write("---")
            st.markdown(f"#### 🏫 **[{selected_dept}] 입시 결과**")
            
            if selected_dept == "데이터 로딩 실패" or selected_dept == "데이터 없음":
                st.error("엑셀 파일 로딩 오류로 비교가 불가능합니다.")
            else:
                dept_data = db[selected_track][db[selected_track]["모집단위"] == selected_dept]
                
                def get_val(col_keywords):
                    for col in dept_data.columns:
                        if all(kw in str(col).replace(" ", "") for kw in col_keywords):
                            val = dept_data.iloc[0][col]
                            return val if pd.notna(val) else "-"
                    return "-"
    
                def format_num(val):
                    if val == "-": return val
                    try:
                        f_val = float(val)
                        if f_val.is_integer(): return str(int(f_val))
                        return f"{f_val:.2f}"
                    except: return str(val)
    
                mojib_2027 = format_num(get_val(["2027", "모집인원"]))
                hwansan_avg = format_num(get_val(["2027", "환산", "평균"]))
                hwansan_cut = format_num(get_val(["2027", "환산", "최저"]))
                hwansan_max = format_num(get_val(["2027", "환산", "최고"]))
    
                def get_year_data(year_full, year_short):
                    avg = get_val([year_full, "최종합격", "평균"])
                    if avg == "-": avg = get_val([year_full, "평균"])
                    if avg == "-": avg = get_val([year_short, "평균"])
                    
                    cut = get_val([year_full, "최종합격", "최저"])
                    if cut == "-": cut = get_val([year_full, "최저"])
                    if cut == "-": cut = get_val([year_short, "최저"])
                    
                    max_v = get_val([year_full, "최종합격", "최고"])
                    if max_v == "-": max_v = get_val([year_full, "최고"])
                    if max_v == "-": max_v = get_val([year_short, "최고"])
                    
                    chu = get_val([year_full, "추가합격"])
                    if chu == "-": chu = get_val([year_short, "추가합격"])
                    comp = get_val([year_full, "경쟁률"])
                    if comp == "-": comp = get_val([year_short, "경쟁률"])
                    return avg, cut, max_v, chu, comp
    
                avg_26, cut_26, max_26, chu_26, comp_26 = [format_num(x) for x in get_year_data("2026", "26")]
                avg_25, cut_25, max_25, chu_25, comp_25 = [format_num(x) for x in get_year_data("2025", "25")]
                avg_24, cut_24, max_24, chu_24, comp_24 = [format_num(x) for x in get_year_data("2024", "24")]
    
                # [디자인 패치] 모집인원을 둥근 배지 모양의 HTML로 묶어둡니다.
                mojib_badge = f'<div style="font-size: 28px; font-weight: bold; color: #1e3a8a; background-color: #dbeafe; border: 1px solid #bfdbfe; padding: 6px 18px; border-radius: 24px;">🎓 모집인원: {mojib_2027}명</div>' if mojib_2027 != "-" else ""
                
                if hwansan_avg != "-" and hwansan_cut != "-":
                    st.markdown(f"""
                    <div style="background-color: #edf4fe; padding: 16px 20px; border-left: 5px solid #00308F; border-radius: 6px; margin: 14px 0;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                            <div style="font-size: 20px; font-weight: bold; color: #00308F;">💡 2027학년도 산출 방식 적용 환산 점수 (예측 기준)</div>
                            {mojib_badge}
                        </div>
                        <div style="font-size: 16px; color: #333333; font-weight: bold;">
                            ▶ 평균: <span style="color: #ff4b4b; font-weight: bold; font-size: 24px;">{hwansan_avg}</span> 등급 &nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp; 
                            최저: <span style="color: #ff4b4b; font-weight: bold; font-size: 24px;">{hwansan_cut}</span> 등급 &nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp; 
                            최고: <span style="color: #ff4b4b; font-weight: bold; font-size: 24px;">{hwansan_max}</span> 등급
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    pred_avg, pred_cut, pred_max = hwansan_avg, hwansan_cut, hwansan_max
                else:
                    st.markdown(f"""
                    <div style="background-color: #fff1f1; padding: 16px 20px; border-left: 5px solid #ff4b4b; border-radius: 6px; margin: 14px 0;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div style="font-size: 16px; font-weight: bold; color: #d62728;">💡 해당 전형은 별도 환산점수가 없으므로, 2026학년도 결과를 기준으로 예측합니다.</div>
                            {mojib_badge}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    pred_avg, pred_cut, pred_max = avg_26, cut_26, max_26
                    
                st.markdown("📊 **최근 3개년 입시 결과 요약표**")
                summary_df = pd.DataFrame({
                    "연도": ["2026학년도", "2025학년도", "2024학년도"],
                    "경쟁률": [f"{comp_26}:1" if str(comp_26) != "-" else "-", f"{comp_25}:1" if str(comp_25) != "-" else "-", f"{comp_24}:1" if str(comp_24) != "-" else "-"],
                    "평균등급": [avg_26, avg_25, avg_24],
                    "최저": [cut_26, cut_25, cut_24],
                    "최고등급": [max_26, max_25, max_24],
                    "추가합격": [f"{chu_26}명" if str(chu_26) != "-" else "-", f"{chu_25}명" if str(chu_25) != "-" else "-", f"{chu_24}명" if str(chu_24) != "-" else "-"]
                }).set_index("연도")
                
                st.dataframe(summary_df.style.set_properties(**{'text-align': 'center'}), use_container_width=True)
    
                if str(pred_avg) != "-" and str(pred_cut) != "-" and str(pred_max) != "-":
                    try:
                        score_avg, score_cut, score_max = float(pred_avg), float(pred_cut), float(pred_max)
                        
                        if final_score <= score_max: st.success("✅ **안정권:** 기준 최고점보다 성적이 우수합니다.")
                        elif final_score <= score_avg: st.info("🔄 **적정권:** 기준 평균점보다 성적이 우수합니다.")
                        elif final_score <= score_cut: st.warning("⚠️ **소신지원:** 기준 평균점과 최저(커트라인) 사이입니다.")
                        else: st.error("🚨 **상향:** 기준 최저(커트라인)보다 성적이 낮습니다.")
                        
                        # [수정 3] 상하단 알림창 색상 완벽 동기화 패치
                        bg_color, border_color, icon, status_text, text_color = "", "", "", "", ""
                        
                        if final_score <= score_max:
                            bg_color, border_color, icon, status_text, text_color = "#e8f5e9", "#4caf50", "🟢", "안 정", "#2e7d32"
                        elif final_score <= score_avg:
                            bg_color, border_color, icon, status_text, text_color = "#e3f2fd", "#2196f3", "🔵", "적 정", "#1565c0"
                        elif final_score <= score_cut:
                            bg_color, border_color, icon, status_text, text_color = "#fff3e0", "#ff9800", "🟠", "소 신", "#ef6c00"
                        else:
                            bg_color, border_color, icon, status_text, text_color = "#ffebee", "#f44336", "🔴", "상 향", "#c62828"

                        badge_html = f"""
                        <div style="display: flex; align-items: center; justify-content: center; height: 100%; margin-top: 5px;">
                            <div style="background-color: {bg_color}; border: 2px solid {border_color}; border-radius: 12px; padding: 12px 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                                <span style="font-size: 26px; vertical-align: middle;">{icon}</span>
                                <span style="font-size: 22px; font-weight: 900; color: {text_color}; margin-left: 10px; vertical-align: middle;">{status_text}</span>
                            </div>
                        </div>
                        """
                        badge_placeholder.markdown(badge_html, unsafe_allow_html=True)
                        
                    except: st.warning("점수 비교 중 오류가 발생했습니다. (데이터 형식 확인 필요)")
                else: st.warning("예측 기준이 되는 데이터(최고, 평균, 최저)를 찾을 수 없습니다.")

            # --- 지원 전형 내 타 학과 추천 (Intra-track Recommendation) ---
            st.write("---")
            with st.expander(f"🔄 [{selected_track}] 지원 가능 타 학과 추천", expanded=False):
                st.markdown(f"현재 산출된 환산 점수로 **{selected_track}** 내에서 지원 시 **안정권(최고점 이내)** 또는 **적정권(평균점 이내)**으로 분석되는 타 학과 리스트입니다.")
                
                rec_data = []
                t_name = selected_track
                if t_name in db and not db[t_name].empty and "모집단위" in db[t_name].columns:
                    t_df = db[t_name]
                    for d_name in dept_list:
                        if d_name == selected_dept: continue
                        d_data = t_df[t_df["모집단위"] == d_name]
                        if d_data.empty: continue
                        
                        def _get_rec(keywords):
                            for col in d_data.columns:
                                if all(kw in str(col).replace(" ", "") for kw in keywords):
                                    v = d_data.iloc[0][col]
                                    return v if pd.notna(v) else "-"
                            return "-"
                            
                        rec_avg_27 = _get_rec(["2027", "환산", "평균"])
                        rec_max_27 = _get_rec(["2027", "환산", "최고"])
                        
                        p_avg, p_max = "-", "-"
                        if rec_avg_27 != "-" and rec_max_27 != "-": p_avg, p_max = rec_avg_27, rec_max_27
                        else:
                            rec_avg_26 = _get_rec(["2026", "최종합격", "평균"])
                            if rec_avg_26 == "-": rec_avg_26 = _get_rec(["2026", "평균"])
                            if rec_avg_26 == "-": rec_avg_26 = _get_rec(["26", "평균"])
                            
                            rec_max_26 = _get_rec(["2026", "최종합격", "최고"])
                            if rec_max_26 == "-": rec_max_26 = _get_rec(["2026", "최고"])
                            if rec_max_26 == "-": rec_max_26 = _get_rec(["26", "최고"])
                            
                            p_avg, p_max = rec_avg_26, rec_max_26
                            
                        if p_avg != "-" and p_max != "-":
                            try:
                                f_avg, f_max = float(p_avg), float(p_max)
                                status = ""
                                if final_score <= f_max: status = "✅ 안정권"
                                elif final_score <= f_avg: status = "🔄 적정권"
                                if status:
                                    rec_data.append({
                                        "모집단위 (추천 학과)": d_name,
                                        "지원 전략": status,
                                        "기준 평균": f"{f_avg:.2f}",
                                        "기준 최고": f"{f_max:.2f}"
                                    })
                            except: pass
                
                if rec_data:
                    rec_df = pd.DataFrame(rec_data).sort_values(by=["지원 전략", "기준 평균"], ascending=[True, True]).reset_index(drop=True)
                    rec_df.index = rec_df.index + 1
                    st.dataframe(rec_df.style.set_properties(**{'text-align': 'center'}), use_container_width=True)
                else:
                    st.info(f"현재 점수로 **{selected_track}** 내에서 안정/적정권에 해당하는 타 학과가 없습니다. 소신/상향 지원 전략을 고려해보세요.")

with col_right:
    if (calc_clicked or manual_score > 0) and selected_dept != "데이터 로딩 실패" and selected_dept != "데이터 없음":
        import altair as alt
        
        with st.container(border=True):
            st.markdown("### 📊 입시 결과 추이 분석")
            
            def safe_float(val):
                try:
                    v = str(val).strip()
                    if pd.isna(val) or v in ["", "-", "nan", "NaN"]: return None
                    cleaned = re.sub(r'[^\d.]', '', v)
                    return float(cleaned) if cleaned else None
                except: return None

            def build_safe_row(m_val, a_val, c_val):
                m = safe_float(m_val)
                a = safe_float(a_val)
                c = safe_float(c_val)
                
                valid = [v for v in [m, a, c] if v is not None]
                if valid:
                    fallback = valid[-1]
                    if m is None: m = fallback
                    if a is None: a = fallback
                    if c is None: c = fallback
                    return m, a, c
                return None, None, None

            def get_tooltip_str(val):
                v = str(val).strip()
                if pd.isna(val) or v in ["", "-", "nan", "NaN"]: return "-"
                try:
                    f_val = float(re.sub(r'[^\d.]', '', v))
                    if f_val.is_integer(): return str(int(f_val))
                    return f"{f_val:.2f}"
                except: return v

            m24_f, a24_f, c24_f = build_safe_row(max_24, avg_24, cut_24)
            m25_f, a25_f, c25_f = build_safe_row(max_25, avg_25, cut_25)
            m26_f, a26_f, c26_f = build_safe_row(max_26, avg_26, cut_26)

            def get_render_bounds(m, c):
                if m is None or c is None: return None, None
                if m == c:
                    return m - 0.05, c + 0.05 
                return m, c

            m24_r, c24_r = get_render_bounds(m24_f, c24_f)
            m25_r, c25_r = get_render_bounds(m25_f, c25_f)
            m26_r, c26_r = get_render_bounds(m26_f, c26_f)

# [1] 데이터프레임 선언부 (이 부분이 지워졌을 확률이 높습니다. 복구 완료)
            df_grade = pd.DataFrame({
                "연도": ["2024년", "2025년", "2026년"],
                "최고_렌더": [m24_r, m25_r, m26_r],
                "최저_렌더": [c24_r, c25_r, c26_r],
                "평균": [a24_f, a25_f, a26_f],
                "최고등급": [get_tooltip_str(max_24), get_tooltip_str(max_25), get_tooltip_str(max_26)],
                "평균등급": [get_tooltip_str(avg_24), get_tooltip_str(avg_25), get_tooltip_str(avg_26)],
                "최저등급": [get_tooltip_str(cut_24), get_tooltip_str(cut_25), get_tooltip_str(cut_26)]
            })
            
            comp_chart_data = pd.DataFrame({
                "연도": ["2024년", "2025년", "2026년"],
                "경쟁률": [safe_float(comp_24), safe_float(comp_25), safe_float(comp_26)]
            }).set_index("연도")

            # [2] 첫 번째 차트 렌더링 (글자 세우기 + 수치 고정 패치 적용)
            if not df_grade[["최고_렌더", "최저_렌더", "평균"]].isna().all().all():
                st.markdown("📈 **3개년 입시 결과 등급 스펙트럼 차트**")
                
                bar = alt.Chart(df_grade).mark_bar(size=45, color='#00308F', opacity=0.55, cornerRadius=4).encode(
                    x=alt.X('연도:N', title=None, axis=alt.Axis(labelAngle=0, labelFontSize=12, labelFontWeight='bold')),
                    y=alt.Y('최고_렌더:Q', scale=alt.Scale(zero=False, reverse=True), 
                            axis=alt.Axis(title='등급', titleAngle=0, titlePadding=20, titleAlign='right')), 
                    y2='최저_렌더:Q',
                    tooltip=[
                        alt.Tooltip('연도:N'), alt.Tooltip('최고등급:N'), 
                        alt.Tooltip('평균등급:N'), alt.Tooltip('최저등급:N')
                    ]
                )
                tick = alt.Chart(df_grade).mark_tick(color='#ff4b4b', thickness=4.5, size=45).encode(x='연도:N', y='평균:Q')
                
                text_max = alt.Chart(df_grade).mark_text(dy=-15, fontSize=12, fontWeight='bold', color='#00308F').encode(
                    x='연도:N', y='최고_렌더:Q', text='최고등급:N'
                )
                text_avg = alt.Chart(df_grade).mark_text(dx=35, fontSize=12, fontWeight='bold', color='#ff4b4b').encode(
                    x='연도:N', y='평균:Q', text='평균등급:N'
                )
                text_min = alt.Chart(df_grade).mark_text(dy=15, fontSize=12, fontWeight='bold', color='#00308F').encode(
                    x='연도:N', y='최저_렌더:Q', text='최저등급:N'
                )

                st.altair_chart(alt.layer(bar, tick, text_max, text_avg, text_min).properties(height=275), use_container_width=True)
    
# [3] 두 번째 차트 렌더링 (세련된 모던 UI 적용)
            if not comp_chart_data.isna().all().all():
                st.write("---")
                st.markdown("🔥 **3개년 경쟁률 추이 그래프**")
                df_comp_long = comp_chart_data.reset_index()
                df_comp_long['레이블'] = df_comp_long['경쟁률'].apply(lambda x: f"{x:.2f}:1" if pd.notna(x) else "")
                
                # ① Y축 그리드를 연한 점선으로 세팅하여 세련미 추가 & 불필요한 테두리 제거
                base = alt.Chart(df_comp_long).encode(
                    x=alt.X('연도:N', axis=alt.Axis(
                        labelAngle=0, grid=False, labelFontSize=12, labelFontWeight='bold', 
                        domainColor='#cbd5e1', tickColor='#cbd5e1'
                    )),
                    y=alt.Y('경쟁률:Q', scale=alt.Scale(zero=False), axis=alt.Axis(
                        title='경쟁률', grid=True, gridDash=[5, 5], gridColor='#e2e8f0', 
                        titleAngle=0, titlePadding=20, titleAlign='right', 
                        domain=False, ticks=False
                    ))
                )
                
                # ② 그라데이션 영역 (위는 진하게, 아래는 흰색으로 자연스럽게 페이드아웃)
                area = base.mark_area(
                    color=alt.Gradient(
                        gradient='linear',
                        stops=[alt.GradientStop(color='#ff4b4b', offset=0),
                               alt.GradientStop(color='white', offset=1)],
                        x1=1, x2=1, y1=1, y2=0
                    ),
                    opacity=0.6, 
                    interpolate='monotone'
                )
                
                # ③ 선 굵기를 정돈하여 샤프하게 유지
                line = base.mark_line(color='#ff4b4b', size=3.5, interpolate='monotone')
                
                # ④ 모던 UI 스타일 포인트 (테두리는 붉은색, 내부는 흰색으로 타공)
                points = base.mark_point(color='#ff4b4b', size=140, fill='white', strokeWidth=3, opacity=1)
                
                # ⑤ 텍스트 가독성 조정 (완전 블랙이 아닌 짙은 그레이로 눈을 편안하게)
                text = base.mark_text(dy=-22, fontSize=13, fontWeight='bold', color='#334155').encode(text='레이블:N')
                
                st.altair_chart(alt.layer(area, line, points, text).properties(height=275), use_container_width=True)
                
# --- 7. 전체 학과 입시 결과 요약표 ---
st.write("---")
st.markdown(f"### 📋 [{selected_track}] 전체 학과 3개년 입시 결과 종합표")
st.caption("※ 현재 상담 중인 **선택 학과**는 노란색으로 표시됩니다.")

if db[selected_track].empty or "모집단위" not in db[selected_track].columns:
    st.warning("데이터가 없어 전체 표를 구성할 수 없습니다.")
else:
    all_dept_data = db[selected_track]
    table_rows = []
    for dept in dept_list: 
        d_data = all_dept_data[all_dept_data["모집단위"] == dept]
        if d_data.empty: continue
        
        def get_d_val(col_keywords):
            for col in d_data.columns:
                if all(kw in str(col).replace(" ", "") for kw in col_keywords):
                    v = d_data.iloc[0][col]
                    return v if pd.notna(v) else "-"
            return "-"
        def fmt(val):
            if val == "-": return val
            try:
                f_val = float(val)
                if f_val.is_integer(): return str(int(f_val))
                return f"{f_val:.2f}"
            except: return str(val)
        def get_yr(y_full, y_short):
            avg = get_d_val([y_full, "최종합격", "평균"])
            if avg == "-": avg = get_d_val([y_full, "평균"])
            if avg == "-": avg = get_d_val([y_short, "평균"])
            cut = get_d_val([y_full, "최종합격", "최저"])
            if cut == "-": cut = get_d_val([y_full, "최저"])
            if cut == "-": cut = get_d_val([y_short, "최저"])
            mx = get_d_val([y_full, "최종합격", "최고"])
            if mx == "-": mx = get_d_val([y_full, "최고"])
            if mx == "-": mx = get_d_val([y_short, "최고"])
            return fmt(mx), fmt(avg), fmt(cut)

        m26, a26, c26 = get_yr("2026", "26")
        m25, a25, c25 = get_yr("2025", "25")
        m24, a24, c24 = get_yr("2024", "24")
        table_rows.append({
            "모집단위": dept, "2026 최고": m26, "2026 평균": a26, "2026 최저": c26,
            "2025 최고": m25, "2025 평균": a25, "2025 최저": c25, "2024 최고": m24, "2024 평균": a24, "2024 최저": c24,
        })

    if table_rows:
        all_df = pd.DataFrame(table_rows).set_index("모집단위")
        def apply_custom_styles(row):
            styles = []
            is_selected = (row.name == selected_dept)
            for col in row.index:
                if is_selected: styles.append('background-color: #ffeb3b; color: black; font-weight: bold;')
                elif "2026" in col: styles.append('background-color: rgba(173, 216, 230, 0.25);')
                elif "2025" in col: styles.append('background-color: rgba(144, 238, 144, 0.25);')
                elif "2024" in col: styles.append('background-color: rgba(255, 228, 196, 0.35);')
                else: styles.append('')
            return styles
        st.dataframe(all_df.style.apply(apply_custom_styles, axis=1).set_properties(**{'text-align': 'center'}), use_container_width=True)
