import streamlit as st
import anthropic
import json
import os
from datetime import datetime
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# 파일 경로
SYSTEM_PROMPT_FILE = "system_prompt.txt"
MEMORY_FILE = "memory.json"
USER_FILE = "user.json"
HISTORY_FILE = "chat_history.json"

# Anthropic 클라이언트
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# 테마 색상 정의
themes = {
    "다크": {
        "bg": "#0e1117",
        "sidebar": "#262730",
        "text": "#ffffff",
        "input": "#262730",
    },
    "화이트": {
        "bg": "#ffffff",
        "sidebar": "#f0f2f6",
        "text": "#000000",
        "input": "#ffffff",
    },
    "회색": {
        "bg": "#2b2b2b",
        "sidebar": "#3a3a3a",
        "text": "#e0e0e0",
        "input": "#3a3a3a",
    },
    "연두": {
        "bg": "#2d3b2d",
        "sidebar": "#3a4f3a",
        "text": "#d4e8d4",
        "input": "#3a4f3a",
    },
    "노랑": {
        "bg": "#2b2800",
        "sidebar": "#3d3a00",
        "text": "#fff8c0",
        "input": "#3d3a00",
    },
    "하늘": {
        "bg": "#0d2137",
        "sidebar": "#1a3350",
        "text": "#c8e6ff",
        "input": "#1a3350",
    }
}

def load_theme():
    if os.path.exists("theme.json"):
        with open("theme.json", "r") as f:
            return json.load(f).get("theme", "다크")
    return "다크"

def save_theme(theme_name):
    with open("theme.json", "w") as f:
        json.dump({"theme": theme_name}, f)

def apply_theme(theme_name):
    t = themes[theme_name]
    st.markdown(f"""
    <style>
        /* 전체 배경 */
        .stApp {{
            background-color: {t['bg']};
            color: {t['text']};
        }}
        /* 헤더 영역 */
        header[data-testid="stHeader"] {{
            background-color: {t['bg']};
        }}
        /* 사이드바 */
        section[data-testid="stSidebar"] {{
            background-color: {t['sidebar']};
            transform: none !important;
            min-width: 250px !important;
            width: 250px !important;
        }}
        /* 사이드바 접기 버튼 숨기기 */
        [data-testid="collapsedControl"] {{
            display: none !important;
        }}
        /* 입력창 */
        .stChatInput textarea {{
            background-color: {t['bg']};
            color: {t['text']};
            border: none;
        }}
        .stChatInput textarea::placeholder {{
            color: {t['text']};
            opacity: 0.6;
        }}
        /* 입력창 테두리 */
        .stChatInput > div {{
            border: 1px solid {t['text']}60;
            border-radius: 8px;
            background-color: {t['bg']};
        }}
        .stChatInput > div:focus-within {{
            border: 1px solid {t['text']}cc;
        }}
        /* 텍스트 */
        p, h1, h2, h3, h4, label, span {{
            color: {t['text']} !important;
        }}
        /* 버튼 */
        .stButton button {{
            background-color: {t['sidebar']};
            color: {t['text']};
            border: 1px solid {t['text']}40;
        }}
        .stButton button:hover {{
            background-color: {t['input']};
            color: {t['text']};
            border: 1px solid {t['text']}80;
        }}
        /* 셀렉트박스 */
        .stSelectbox div[data-baseweb="select"] {{
            background-color: {t['input']};
            color: {t['text']};
        }}
        .stSelectbox div[data-baseweb="select"] * {{
            background-color: {t['input']};
            color: {t['text']};
        }}
        /* 하단 입력 영역 전체 */
        .stBottom, .stBottom > div, .stBottom > div > div {{
            background-color: {t['bg']} !important;
        }}
        [data-testid="stBottom"], [data-testid="stBottom"] > div {{
            background-color: {t['bg']} !important;
        }}
        div[class*="floating"], div[class*="Floating"] {{
            background-color: {t['bg']} !important;
        }}
        div[class*="bottom"], div[class*="Bottom"] {{
            background-color: {t['bg']} !important;
        }}
        .stChatInput, .stChatInput > div, .stChatInput > div > div {{
            background-color: {t['bg']} !important;
        }}
        div[data-testid="stChatInputContainer"] {{
            background-color: {t['bg']} !important;
        }}
        div[data-testid="stChatInputContainer"] > div {{
            background-color: {t['bg']} !important;
        }}
        /* 채팅 응답 내 헤더 크기 축소 */
        .stChatMessage h1 {{
            font-size: 1.2rem !important;
            font-weight: 600 !important;
        }}
        .stChatMessage h2 {{
            font-size: 1.0rem !important;
            font-weight: 600 !important;
        }}
        .stChatMessage h3 {{
            font-size: 0.95rem !important;
            font-weight: 600 !important;
        }}
    </style>
    """, unsafe_allow_html=True)

def load_system_prompt():
    with open(SYSTEM_PROMPT_FILE, "r", encoding="utf-8") as f:
        return f.read()

def load_memory():
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_memory(memory):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)

def load_chat_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_chat_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def load_user():
    if os.path.exists(USER_FILE):
        with open(USER_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if data.get("name", "").strip():
                return data
    return None

def save_user(name):
    with open(USER_FILE, "w", encoding="utf-8") as f:
        json.dump({"name": name}, f, ensure_ascii=False)

def build_system_prompt():
    base_prompt = load_system_prompt()
    memory = load_memory()

    memory_section = f"""
---

# 누적 대화 요약

마지막 업데이트: {memory.get('last_updated', '없음')}

발견된 패턴:
{json.dumps(memory.get('discovered_patterns', []), ensure_ascii=False, indent=2)}

업데이트된 프로필:
{json.dumps(memory.get('updated_profile', []), ensure_ascii=False, indent=2)}

미해결 질문:
{json.dumps(memory.get('unresolved_questions', []), ensure_ascii=False, indent=2)}

세션 요약:
{json.dumps(memory.get('session_summaries', []), ensure_ascii=False, indent=2)}
"""
    return base_prompt + memory_section

def get_ai_response(messages):
    system_prompt = build_system_prompt()

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4096,
        system=system_prompt,
        messages=messages
    )

    return response.content[0].text

def auto_summarize_and_save(messages):
    if not messages:
        return False

    conversation_text = ""
    for msg in messages:
        role = "사용자" if msg["role"] == "user" else "AI"
        content = msg["content"]
        # 이미지가 포함된 메시지는 텍스트만 추출
        if isinstance(content, list):
            text_parts = [item["text"] for item in content if item.get("type") == "text"]
            content = " ".join(text_parts)
            conversation_text += f"{role}: [이미지 첨부] {content}\n\n"
        else:
            conversation_text += f"{role}: {content}\n\n"

    summary_prompt = f"""아래 대화를 분석해서 JSON 형식으로만 응답해줘.
마크다운 코드블록 없이, 순수 JSON만 출력해야 해.
앞뒤에 어떤 텍스트도 붙이지 마.

대화 내용:
{conversation_text}

반드시 아래 형식의 JSON만 출력해:
{{
  "session_summary": "이번 세션의 핵심 내용 2-3문장 요약",
  "discovered_patterns": ["새로 발견된 패턴1", "새로 발견된 패턴2"],
  "updated_profile": ["프로필에 추가할 내용1", "프로필에 추가할 내용2"],
  "unresolved_questions": ["다음 세션에서 이어갈 질문1", "질문2"]
}}"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            messages=[{"role": "user", "content": summary_prompt}]
        )

        raw_text = response.content[0].text.strip()

        # 마크다운 코드블록 제거
        if raw_text.startswith("```"):
            lines = raw_text.split("\n")
            lines = [l for l in lines if not l.startswith("```")]
            raw_text = "\n".join(lines).strip()

        # JSON 부분만 추출 (앞뒤 텍스트 제거)
        start = raw_text.find("{")
        end = raw_text.rfind("}") + 1
        if start != -1 and end > start:
            raw_text = raw_text[start:end]

        summary_data = json.loads(raw_text)

        memory = load_memory()
        memory["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")

        memory["session_summaries"].append({
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "summary": summary_data.get("session_summary", "")
        })

        existing_patterns = set(memory.get("discovered_patterns", []))
        new_patterns = summary_data.get("discovered_patterns", [])
        for pattern in new_patterns:
            if pattern not in existing_patterns:
                memory["discovered_patterns"].append(pattern)

        existing_profile = set(memory.get("updated_profile", []))
        new_profile = summary_data.get("updated_profile", [])
        for item in new_profile:
            if item not in existing_profile:
                memory["updated_profile"].append(item)

        memory["unresolved_questions"] = summary_data.get("unresolved_questions", [])

        save_memory(memory)

        # 대화 원문 저장 (이미지 데이터 제거)
        clean_messages = []
        for msg in messages:
            content = msg["content"]
            if isinstance(content, list):
                clean_content = []
                for item in content:
                    if item.get("type") == "text":
                        clean_content.append(item)
                    elif item.get("type") == "image":
                        clean_content.append({
                            "type": "text",
                            "text": "[이미지 첨부됨]"
                        })
                clean_messages.append({"role": msg["role"], "content": clean_content})
            else:
                clean_messages.append(msg)

        history = load_chat_history()
        history.append({
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "messages": clean_messages
        })
        save_chat_history(history)

        return True
    except Exception as e:
        st.error(f"오류 내용: {str(e)}")
        print(f"오류 내용: {str(e)}")
        return False

# Streamlit UI
st.set_page_config(
    page_title="나우",
    page_icon="💭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 기본 메뉴 및 사이드바 고정
st.markdown("""
<style>
    [data-testid="stToolbar"] {
        display: none;
    }
    section[data-testid="stSidebar"] {
        transform: none !important;
        min-width: 250px !important;
        width: 250px !important;
    }
    [data-testid="collapsedControl"] {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

# 사용자 이름 확인
user_data = load_user()

# 처음 사용자라면 이름 입력 화면
if user_data is None:
    st.title("💭 나우")
    st.write("")
    st.subheader("처음 오셨군요. 이름을 입력해주세요.")

    with st.form("name_form"):
        name_input = st.text_input("이름", placeholder="이름을 입력해줘")
        submitted = st.form_submit_button("시작하기")

        if submitted:
            if name_input.strip():
                save_user(name_input.strip())
                st.rerun()
            else:
                st.warning("이름을 입력해줘.")

else:
    user_name = user_data["name"]
    current_theme = load_theme()

    # 테마 먼저 적용
    apply_theme(current_theme)

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "view_history" not in st.session_state:
        st.session_state.view_history = None
    if "editing_title" not in st.session_state:
        st.session_state.editing_title = None

    with st.sidebar:
        st.header("테마")
        selected_theme = st.selectbox(
            "",
            list(themes.keys()),
            index=list(themes.keys()).index(current_theme),
            label_visibility="collapsed"
        )
        if selected_theme != current_theme:
            save_theme(selected_theme)
            st.rerun()

        st.divider()

        st.header("세션 관리")

        if st.button("대화 종료 및 저장"):
            if st.session_state.messages:
                with st.spinner("대화 내용 자동 요약 중..."):
                    success = auto_summarize_and_save(st.session_state.messages)
                if success:
                    st.success("저장 완료!")
                    st.session_state.messages = []
                    st.session_state.view_history = None
                    st.rerun()
                else:
                    st.error("저장 중 오류가 생겼어. 다시 시도해줘.")
            else:
                st.warning("대화 내용이 없어.")

        if st.button("저장 없이 초기화"):
            st.session_state.messages = []
            st.session_state.view_history = None
            st.rerun()

        st.divider()

        memory = load_memory()
        st.header("누적 메모리 현황")
        st.write(f"마지막 업데이트: {memory.get('last_updated', '없음')}")
        st.write(f"세션 수: {len(memory.get('session_summaries', []))}")
        st.write(f"발견된 패턴 수: {len(memory.get('discovered_patterns', []))}")

        # 이전 대화 기록 목록
        history = load_chat_history()
        if history:
            st.divider()
            st.header("이전 대화 기록")
            for i, session in enumerate(reversed(history)):
                actual_index = len(history) - 1 - i
                label = session.get("title", session["date"])
                col_a, col_b = st.columns([4, 1])
                with col_a:
                    if st.button(label, key=f"history_{i}"):
                        st.session_state.view_history = actual_index
                        st.session_state.editing_title = None
                        st.rerun()
                with col_b:
                    if st.button("🖊️", key=f"edit_{i}"):
                        st.session_state.editing_title = actual_index
                        st.session_state.view_history = None
                        st.rerun()

        if memory.get('unresolved_questions'):
            st.divider()
            st.header("이어갈 질문들")
            for q in memory.get('unresolved_questions', []):
                st.write(f"• {q}")
    # 제목 수정 모드
    if st.session_state.editing_title is not None:
        edit_idx = st.session_state.editing_title
        history = load_chat_history()
        if edit_idx < len(history):
            st.title("🖊️ 제목 수정")
            current_title = history[edit_idx].get("title", history[edit_idx]["date"])
            new_title = st.text_input("새 제목을 입력해줘", value=current_title)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("저장"):
                    history[edit_idx]["title"] = new_title
                    save_chat_history(history)
                    st.session_state.editing_title = None
                    st.rerun()
            with col2:
                if st.button("취소"):
                    st.session_state.editing_title = None
                    st.rerun()
    # 이전 대화 보기 모드
    elif st.session_state.view_history is not None:
        history = load_chat_history()
        selected = history[st.session_state.view_history]

        st.title(f"💭 {selected['date']} 대화 기록")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("← 현재 대화로 돌아가기"):
                st.session_state.view_history = None
                st.rerun()
        with col2:
            if st.button("↩ 이 대화 이어하기"):
                st.session_state.messages = selected["messages"].copy()
                st.session_state.view_history = None
                st.rerun()

        st.divider()

        for message in selected["messages"]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    else:
        st.title(f"💭 안녕하세요, {user_name}님.")
        st.subheader("나우가 무엇을 도와드릴까요?")

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                content = message["content"]
                if isinstance(content, list):
                    for item in content:
                        if item.get("type") == "image":
                            import base64
                            image_bytes = base64.b64decode(item["source"]["data"])
                            st.image(image_bytes, width=300)
                        elif item.get("type") == "text":
                            st.markdown(item["text"])
                else:
                    st.markdown(content)

        # 이미지 업로드
        if "uploader_key" not in st.session_state:
            st.session_state.uploader_key = 0

        uploaded_image = st.file_uploader(
            "이미지 첨부 (선택)",
            type=["jpg", "jpeg", "png", "gif", "webp"],
            label_visibility="collapsed",
            key=f"uploader_{st.session_state.uploader_key}"
        )

        if prompt := st.chat_input("여기에 입력해줘"):
            if uploaded_image is not None:
                import base64
                image_bytes = uploaded_image.read()
                image_data = base64.standard_b64encode(image_bytes).decode("utf-8")
                media_type = uploaded_image.type
                user_message = {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
                # 화면에는 이미지 미리보기 + 텍스트만 표시
                with st.chat_message("user"):
                    st.image(image_bytes, width=300)
                    st.markdown(prompt)
            else:
                user_message = {"role": "user", "content": prompt}
                with st.chat_message("user"):
                    st.markdown(prompt)

            st.session_state.messages.append(user_message)
            # 이미지 초기화
            st.session_state.uploader_key += 1

            with st.chat_message("assistant"):
                with st.spinner("생각 중..."):
                    response = get_ai_response(st.session_state.messages)
                st.markdown(response)

            st.session_state.messages.append({"role": "assistant", "content": response})