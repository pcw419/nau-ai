import streamlit as st
import anthropic
import json
import os
import base64
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

# 환경변수 로드
load_dotenv()

# Anthropic 클라이언트
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Supabase 클라이언트
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

# 파일 경로 (로컬 폴백용)
SYSTEM_PROMPT_FILE = "system_prompt.txt"

# 테마 색상 정의
themes = {
    "다크": {"bg": "#0e1117", "sidebar": "#262730", "text": "#ffffff", "input": "#262730"},
    "화이트": {"bg": "#ffffff", "sidebar": "#f0f2f6", "text": "#000000", "input": "#ffffff"},
    "회색": {"bg": "#2b2b2b", "sidebar": "#3a3a3a", "text": "#e0e0e0", "input": "#3a3a3a"},
    "연두": {"bg": "#2d3b2d", "sidebar": "#3a4f3a", "text": "#d4e8d4", "input": "#3a4f3a"},
    "노랑": {"bg": "#2b2800", "sidebar": "#3d3a00", "text": "#fff8c0", "input": "#3d3a00"},
    "하늘": {"bg": "#0d2137", "sidebar": "#1a3350", "text": "#c8e6ff", "input": "#1a3350"}
}

# ── Supabase 데이터 함수 ──────────────────────────────────────

def get_or_create_user(name):
    res = supabase.table("users").select("*").eq("name", name).execute()
    if res.data:
        return res.data[0]
    res = supabase.table("users").insert({"name": name, "theme": "다크"}).execute()
    return res.data[0]

def load_user_by_name(name):
    res = supabase.table("users").select("*").eq("name", name).execute()
    return res.data[0] if res.data else None

def save_user_theme(user_id, theme_name):
    supabase.table("users").update({"theme": theme_name}).eq("id", user_id).execute()

def load_memory(user_id):
    res = supabase.table("memory").select("*").eq("user_id", user_id).execute()
    if res.data:
        return res.data[0].get("data", {})
    return {
        "last_updated": "",
        "discovered_patterns": [],
        "updated_profile": [],
        "unresolved_questions": [],
        "session_summaries": []
    }

def save_memory(user_id, memory_data):
    res = supabase.table("memory").select("id").eq("user_id", user_id).execute()
    if res.data:
        supabase.table("memory").update({
            "data": memory_data,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M")
        }).eq("user_id", user_id).execute()
    else:
        supabase.table("memory").insert({
            "user_id": user_id,
            "data": memory_data,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M")
        }).execute()

def load_chat_history(user_id):
    res = supabase.table("chat_history").select("*").eq("user_id", user_id).order("created_at").execute()
    return res.data if res.data else []

def save_chat_session(user_id, messages, date_str):
    supabase.table("chat_history").insert({
        "user_id": user_id,
        "date": date_str,
        "messages": messages
    }).execute()

def update_chat_title(session_id, title):
    supabase.table("chat_history").update({"title": title}).eq("id", session_id).execute()

# ── 시스템 프롬프트 ───────────────────────────────────────────

def load_system_prompt():
    with open(SYSTEM_PROMPT_FILE, "r", encoding="utf-8") as f:
        return f.read()

def build_system_prompt(user_id):
    base_prompt = load_system_prompt()
    memory = load_memory(user_id)

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

# ── AI 응답 ───────────────────────────────────────────────────

def get_ai_response(messages, user_id):
    system_prompt = build_system_prompt(user_id)
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4096,
        system=system_prompt,
        messages=messages
    )
    return response.content[0].text

# ── 자동 요약 및 저장 ─────────────────────────────────────────

def auto_summarize_and_save(messages, user_id):
    if not messages:
        return False

    conversation_text = ""
    for msg in messages:
        role = "사용자" if msg["role"] == "user" else "AI"
        content = msg["content"]
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

        if raw_text.startswith("```"):
            lines = raw_text.split("\n")
            lines = [l for l in lines if not l.startswith("```")]
            raw_text = "\n".join(lines).strip()

        start = raw_text.find("{")
        end = raw_text.rfind("}") + 1
        if start != -1 and end > start:
            raw_text = raw_text[start:end]

        try:
            summary_data = json.loads(raw_text)
        except json.JSONDecodeError:
            try:
                raw_text = raw_text.replace('\n', ' ').replace('\r', ' ')
                summary_data = json.loads(raw_text)
            except json.JSONDecodeError:
                # 최후 수단: 기본값으로 저장
                summary_data = {
                    "session_summary": "자동 요약 실패 - 수동 확인 필요",
                    "discovered_patterns": [],
                    "updated_profile": [],
                    "unresolved_questions": []
                }

        memory = load_memory(user_id)
        memory["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")

        memory["session_summaries"].append({
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "summary": summary_data.get("session_summary", "")
        })

        existing_patterns = set(memory.get("discovered_patterns", []))
        for pattern in summary_data.get("discovered_patterns", []):
            if pattern not in existing_patterns:
                memory["discovered_patterns"].append(pattern)

        existing_profile = set(memory.get("updated_profile", []))
        for item in summary_data.get("updated_profile", []):
            if item not in existing_profile:
                memory["updated_profile"].append(item)

        memory["unresolved_questions"] = summary_data.get("unresolved_questions", [])

        save_memory(user_id, memory)

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
                        clean_content.append({"type": "text", "text": "[이미지 첨부됨]"})
                clean_messages.append({"role": msg["role"], "content": clean_content})
            else:
                clean_messages.append(msg)

        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        save_chat_session(user_id, clean_messages, date_str)

        return True

    except Exception as e:
        st.error(f"오류 내용: {str(e)}")
        print(f"오류 내용: {str(e)}")
        return False

# ── 테마 ─────────────────────────────────────────────────────

def apply_theme(theme_name):
    t = themes[theme_name]
    st.markdown(f"""
    <style>
        .stApp {{ background-color: {t['bg']}; color: {t['text']}; }}
        header[data-testid="stHeader"] {{ background-color: {t['bg']}; }}
        section[data-testid="stSidebar"] {{
            background-color: {t['sidebar']};
            transform: none !important;
            min-width: 250px !important;
            width: 250px !important;
        }}
        [data-testid="collapsedControl"] {{ display: none !important; }}
        .stChatInput textarea {{ background-color: {t['bg']}; color: {t['text']}; border: none; }}
        .stChatInput textarea::placeholder {{ color: {t['text']}; opacity: 0.6; }}
        .stChatInput > div {{
            border: 1px solid {t['text']}60;
            border-radius: 8px;
            background-color: {t['bg']};
        }}
        .stChatInput > div:focus-within {{ border: 1px solid {t['text']}cc; }}
        p, h1, h2, h3, h4, label, span {{ color: {t['text']} !important; }}
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
        .stSelectbox div[data-baseweb="select"] {{ background-color: {t['input']}; color: {t['text']}; }}
        .stSelectbox div[data-baseweb="select"] * {{ background-color: {t['input']}; color: {t['text']}; }}
        .stBottom, .stBottom > div, .stBottom > div > div {{ background-color: {t['bg']} !important; }}
        [data-testid="stBottom"], [data-testid="stBottom"] > div {{ background-color: {t['bg']} !important; }}
        div[class*="floating"], div[class*="Floating"] {{ background-color: {t['bg']} !important; }}
        div[class*="bottom"], div[class*="Bottom"] {{ background-color: {t['bg']} !important; }}
        .stChatInput, .stChatInput > div, .stChatInput > div > div {{ background-color: {t['bg']} !important; }}
        div[data-testid="stChatInputContainer"] {{ background-color: {t['bg']} !important; }}
        div[data-testid="stChatInputContainer"] > div {{ background-color: {t['bg']} !important; }}
        .stChatMessage h1 {{ font-size: 1.2rem !important; font-weight: 600 !important; }}
        .stChatMessage h2 {{ font-size: 1.0rem !important; font-weight: 600 !important; }}
        .stChatMessage h3 {{ font-size: 0.95rem !important; font-weight: 600 !important; }}
    </style>
    """, unsafe_allow_html=True)

# ── Streamlit UI ──────────────────────────────────────────────

st.set_page_config(
    page_title="나우",
    page_icon="💭",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    [data-testid="stToolbar"] { display: none; }
    section[data-testid="stSidebar"] {
        transform: none !important;
        min-width: 250px !important;
        width: 250px !important;
    }
    [data-testid="collapsedControl"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

# ── 세션 상태 초기화 ──────────────────────────────────────────

if "user" not in st.session_state:
    st.session_state.user = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "view_history" not in st.session_state:
    st.session_state.view_history = None
if "editing_title" not in st.session_state:
    st.session_state.editing_title = None
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

# ── 이름 입력 화면 ────────────────────────────────────────────

if st.session_state.user is None:
    st.title("💭 나우")
    st.write("")
    st.subheader("처음 오셨군요. 이름을 입력해주세요.")

    with st.form("name_form"):
        name_input = st.text_input("이름", placeholder="이름을 입력해줘")
        submitted = st.form_submit_button("시작하기")

        if submitted:
            if name_input.strip():
                user = get_or_create_user(name_input.strip())
                st.session_state.user = user
                st.rerun()
            else:
                st.warning("이름을 입력해줘.")

else:
    user = st.session_state.user
    user_id = user["id"]
    user_name = user["name"]
    current_theme = user.get("theme", "다크")

    apply_theme(current_theme)

    with st.sidebar:
        st.header("테마")
        selected_theme = st.selectbox(
            "",
            list(themes.keys()),
            index=list(themes.keys()).index(current_theme),
            label_visibility="collapsed"
        )
        if selected_theme != current_theme:
            save_user_theme(user_id, selected_theme)
            st.session_state.user["theme"] = selected_theme
            st.rerun()

        st.divider()
        st.header("세션 관리")

        if st.button("대화 종료 및 저장"):
            if st.session_state.messages:
                with st.spinner("대화 내용 자동 요약 중..."):
                    success = auto_summarize_and_save(st.session_state.messages, user_id)
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
        memory = load_memory(user_id)
        st.header("누적 메모리 현황")
        st.write(f"마지막 업데이트: {memory.get('last_updated', '없음')}")
        st.write(f"세션 수: {len(memory.get('session_summaries', []))}")
        st.write(f"발견된 패턴 수: {len(memory.get('discovered_patterns', []))}")

        history = load_chat_history(user_id)
        if history:
            st.divider()
            st.header("이전 대화 기록")
            for i, session in enumerate(reversed(history)):
                actual_index = len(history) - 1 - i
                label = session.get("title") or session.get("date", f"대화 {i+1}")
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

    # ── 제목 수정 모드 ────────────────────────────────────────

    if st.session_state.editing_title is not None:
        edit_idx = st.session_state.editing_title
        history = load_chat_history(user_id)
        if edit_idx < len(history):
            st.title("🖊️ 제목 수정")
            session = history[edit_idx]
            current_title = session.get("title") or session.get("date", "")
            new_title = st.text_input("새 제목을 입력해줘", value=current_title)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("저장"):
                    update_chat_title(session["id"], new_title)
                    st.session_state.editing_title = None
                    st.rerun()
            with col2:
                if st.button("취소"):
                    st.session_state.editing_title = None
                    st.rerun()

    # ── 이전 대화 보기 모드 ───────────────────────────────────

    elif st.session_state.view_history is not None:
        history = load_chat_history(user_id)
        selected = history[st.session_state.view_history]
        title = selected.get("title") or selected.get("date", "대화 기록")

        st.title(f"💭 {title}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("← 현재 대화로 돌아가기"):
                st.session_state.view_history = None
                st.rerun()
        with col2:
            if st.button("↩ 이 대화 이어하기"):
                msgs = selected.get("messages", [])
                if isinstance(msgs, str):
                    msgs = json.loads(msgs)
                st.session_state.messages = msgs
                st.session_state.view_history = None
                st.rerun()

        st.divider()

        msgs = selected.get("messages", [])
        if isinstance(msgs, str):
            msgs = json.loads(msgs)

        for message in msgs:
            with st.chat_message(message["role"]):
                content = message["content"]
                if isinstance(content, list):
                    for item in content:
                        if item.get("type") == "text":
                            st.markdown(item["text"])
                else:
                    st.markdown(content)

    # ── 메인 대화 화면 ────────────────────────────────────────

    else:
        st.title(f"💭 안녕하세요, {user_name}님.")
        st.subheader("나우가 무엇을 도와드릴까요?")

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                content = message["content"]
                if isinstance(content, list):
                    for item in content:
                        if item.get("type") == "image":
                            image_bytes = base64.b64decode(item["source"]["data"])
                            st.image(image_bytes, width=300)
                        elif item.get("type") == "text":
                            st.markdown(item["text"])
                else:
                    st.markdown(content)

        # 마지막 응답 다시 생성
        if len(st.session_state.messages) >= 2:
            last_msg = st.session_state.messages[-1]
            if last_msg["role"] == "assistant":
                if st.button("🔄 마지막 답변 다시 생성"):
                    st.session_state.messages.pop()
                    with st.chat_message("assistant"):
                        with st.spinner("생각 중..."):
                            response = get_ai_response(st.session_state.messages, user_id)
                        st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    st.rerun()

        uploaded_image = st.file_uploader(
            "이미지 첨부 (선택)",
            type=["jpg", "jpeg", "png", "gif", "webp"],
            label_visibility="collapsed",
            key=f"uploader_{st.session_state.uploader_key}"
        )

        if prompt := st.chat_input("여기에 입력해줘"):
            if uploaded_image is not None:
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
                        {"type": "text", "text": prompt}
                    ]
                }
                with st.chat_message("user"):
                    st.image(image_bytes, width=300)
                    st.markdown(prompt)
            else:
                user_message = {"role": "user", "content": prompt}
                with st.chat_message("user"):
                    st.markdown(prompt)

            st.session_state.messages.append(user_message)
            st.session_state.uploader_key += 1

            with st.chat_message("assistant"):
                with st.spinner("생각 중..."):
                    response = get_ai_response(st.session_state.messages, user_id)
                st.markdown(response)

            st.session_state.messages.append({"role": "assistant", "content": response})