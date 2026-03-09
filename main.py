import io
import os
import re
import tempfile
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import streamlit as st
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt


# =========================================================
# Models
# =========================================================

@dataclass
class Block:
    kind: str  # scene_heading, action, character, dialogue, parenthetical, transition
    text: str


@dataclass
class Scene:
    heading: str
    blocks: List[Block] = field(default_factory=list)


# =========================================================
# Constants
# =========================================================

APP_TITLE = "Screenplay Converter"
DEFAULT_OUTPUT_NAME = "converted_hollywood_screenplay.docx"

META_PATTERNS = [
    r"^\s*beat\s*\d+",
    r"^\s*\d+막\s*[—\-]",
    r"^\s*act\s*\d+",
    r"^\s*theme stated",
    r"^\s*setup",
    r"^\s*catalyst",
    r"^\s*debate",
    r"^\s*break into two",
    r"^\s*b[- ]?story",
    r"^\s*fun and games",
    r"^\s*midpoint",
    r"^\s*bad guys close in",
    r"^\s*all is lost",
    r"^\s*dark night of the soul",
    r"^\s*break into three",
    r"^\s*finale",
    r"^\s*voice check",
    r"^\s*summary\s*$",
    r"^\s*요약\s*$",
    r"^\s*보이스 점검",
    r"^\s*작법",
]

DIVIDER_PATTERNS = [
    r"^[=\-─═_]{3,}$",
    r"^[#]{3,}$",
    r"^[·•\*]{3,}$",
]

SCENE_PATTERNS = [
    r"^\s*(INT\.|EXT\.|INT/EXT\.|I/E\.)",
    r"^\s*S#?\s*\d+",
    r"^\s*SCENE\s+\d+",
]

TRANSITION_PATTERNS = [
    r"^\s*CUT TO:\s*$",
    r"^\s*MATCH CUT TO:\s*$",
    r"^\s*SMASH CUT TO:\s*$",
    r"^\s*DISSOLVE TO:\s*$",
    r"^\s*FADE IN:\s*$",
    r"^\s*FADE OUT\.?\s*$",
]

TIME_WORDS = [
    "DAY", "NIGHT", "MORNING", "EVENING", "DAWN", "DUSK", "LATER",
    "낮", "밤", "아침", "새벽", "저녁", "그날", "잠시 후", "다음날", "다음 날"
]

LOCATION_CUE_WORDS = [
    "옥상", "복도", "병실", "사무실", "주차장", "골목", "거리", "부엌", "주방",
    "거실", "방", "학교", "교실", "경찰서", "병원", "엘리베이터", "화장실",
    "ROOFTOP", "HALLWAY", "OFFICE", "PARKING", "ALLEY", "STREET",
    "KITCHEN", "LIVING ROOM", "BEDROOM", "CLASSROOM", "POLICE STATION",
    "HOSPITAL", "ELEVATOR", "BATHROOM"
]


# =========================================================
# Text helpers
# =========================================================

def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00A0", " ")
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace("‘", "'").replace("’", "'")
    return text


def normalize_line(line: str) -> str:
    line = normalize_text(line)
    line = re.sub(r"[ \t]+", " ", line)
    return line.strip()


def looks_like_divider(line: str) -> bool:
    s = normalize_line(line)
    if not s:
        return False
    return any(re.match(p, s, flags=re.IGNORECASE) for p in DIVIDER_PATTERNS)


def looks_like_meta(line: str) -> bool:
    s = normalize_line(line)
    if not s:
        return False
    return any(re.match(p, s, flags=re.IGNORECASE) for p in META_PATTERNS)


def looks_like_transition(line: str) -> bool:
    s = normalize_line(line)
    return any(re.match(p, s, flags=re.IGNORECASE) for p in TRANSITION_PATTERNS)


def looks_like_scene_heading(line: str) -> bool:
    s = normalize_line(line)
    if not s:
        return False

    if any(re.match(p, s, flags=re.IGNORECASE) for p in SCENE_PATTERNS):
        return True

    if any(word in s for word in LOCATION_CUE_WORDS):
        if any(t in s.upper() for t in TIME_WORDS) or " - " in s or " / " in s:
            return True

    return False


def strip_scene_number_prefix(line: str) -> str:
    s = normalize_line(line)
    s = re.sub(r"^\s*S#?\s*\d+\.?\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"^\s*SCENE\s+\d+\.?\s*", "", s, flags=re.IGNORECASE)
    return s.strip()


def canonical_scene_heading(line: str) -> str:
    s = strip_scene_number_prefix(line)
    s = s.upper()
    s = re.sub(r"\s+", " ", s)
    return s


def looks_like_parenthetical(line: str) -> bool:
    s = normalize_line(line)
    return bool(re.match(r"^\(.*\)$", s))


def is_probable_character_name(line: str) -> bool:
    s = normalize_line(line)
    if not s:
        return False
    if len(s) > 30:
        return False
    if looks_like_scene_heading(s) or looks_like_transition(s) or looks_like_meta(s):
        return False
    if re.search(r"[.!?]", s):
        return False

    if s.upper() == s and re.search(r"[A-Z]", s):
        return True

    if re.fullmatch(r"[가-힣A-Za-z0-9# ]{1,12}", s):
        return True

    return False


def split_lines_from_text(text: str) -> List[str]:
    text = normalize_text(text)
    raw_lines = text.split("\n")
    lines: List[str] = []
    blank_streak = 0

    for raw in raw_lines:
        line = normalize_line(raw)
        if not line:
            blank_streak += 1
            if blank_streak <= 1:
                lines.append("")
            continue
        blank_streak = 0
        lines.append(line)

    while lines and lines[0] == "":
        lines.pop(0)
    while lines and lines[-1] == "":
        lines.pop()

    return lines


# =========================================================
# Input readers
# =========================================================

def read_txt_file(uploaded_file) -> List[str]:
    uploaded_file.seek(0)
    content = uploaded_file.read().decode("utf-8", errors="ignore")
    return split_lines_from_text(content)


def read_docx_file(uploaded_file) -> List[str]:
    uploaded_file.seek(0)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name

    try:
        doc = Document(tmp_path)
        paragraphs = [normalize_line(p.text) for p in doc.paragraphs]
        text = "\n".join(paragraphs)
        return split_lines_from_text(text)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# =========================================================
# Cleaning
# =========================================================

def remove_meta_and_noise(lines: List[str]) -> List[str]:
    cleaned: List[str] = []
    for line in lines:
        if line == "":
            cleaned.append(line)
            continue
        if looks_like_divider(line):
            continue
        if looks_like_meta(line):
            continue
        cleaned.append(line)

    collapsed: List[str] = []
    prev_blank = False
    for line in cleaned:
        is_blank = line == ""
        if is_blank and prev_blank:
            continue
        collapsed.append(line)
        prev_blank = is_blank

    while collapsed and collapsed[0] == "":
        collapsed.pop(0)
    while collapsed and collapsed[-1] == "":
        collapsed.pop()

    return collapsed


# =========================================================
# Classification and structure
# =========================================================

def classify_lines(lines: List[str]) -> List[Block]:
    blocks: List[Block] = []
    mode: Optional[str] = None

    for i, line in enumerate(lines):
        if not line:
            mode = None
            continue

        next_line = lines[i + 1] if i + 1 < len(lines) else ""

        if looks_like_transition(line):
            blocks.append(Block("transition", normalize_line(line).upper()))
            mode = None
            continue

        if looks_like_scene_heading(line):
            heading = canonical_scene_heading(line)
            blocks.append(Block("scene_heading", heading))
            mode = None
            continue

        if is_probable_character_name(line) and next_line and not looks_like_scene_heading(next_line):
            blocks.append(Block("character", normalize_line(line).upper()))
            mode = "dialogue"
            continue

        if looks_like_parenthetical(line):
            blocks.append(Block("parenthetical", normalize_line(line)))
            continue

        if mode == "dialogue":
            blocks.append(Block("dialogue", normalize_line(line)))
            continue

        blocks.append(Block("action", normalize_line(line)))
        mode = None

    return merge_adjacent_blocks(blocks)


def merge_adjacent_blocks(blocks: List[Block]) -> List[Block]:
    if not blocks:
        return []

    merged: List[Block] = []
    for block in blocks:
        if not merged:
            merged.append(block)
            continue

        prev = merged[-1]

        if prev.kind == "action" and block.kind == "action":
            prev.text = f"{prev.text} {block.text}".strip()
            continue

        if prev.kind == "dialogue" and block.kind == "dialogue":
            prev.text = f"{prev.text} {block.text}".strip()
            continue

        merged.append(block)

    return merged


def blocks_to_scenes(blocks: List[Block]) -> List[Scene]:
    scenes: List[Scene] = []
    current_scene: Optional[Scene] = None

    def ensure_default_scene():
        nonlocal current_scene
        if current_scene is None:
            current_scene = Scene(heading="INT. UNKNOWN LOCATION - DAY")
            scenes.append(current_scene)

    for block in blocks:
        if block.kind == "scene_heading":
            current_scene = Scene(heading=block.text)
            scenes.append(current_scene)
            continue

        ensure_default_scene()
        current_scene.blocks.append(block)

    return scenes


# =========================================================
# DOCX Export
# =========================================================

def try_load_template(template_path: str) -> Document:
    if os.path.exists(template_path):
        return Document(template_path)
    return Document()


def clear_document_body(doc: Document) -> None:
    body = doc._element.body
    for child in list(body):
        if child.tag.endswith("sectPr"):
            continue
        body.remove(child)


def set_document_defaults(doc: Document) -> None:
    try:
        section = doc.sections[0]
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.5)
        section.right_margin = Inches(1.0)
    except IndexError:
        pass

    style = doc.styles["Normal"]
    style.font.name = "Courier New"
    style.font.size = Pt(12)


def add_paragraph(
    doc: Document,
    text: str,
    *,
    align=None,
    left_indent: float = 0.0,
    right_indent: float = 0.0,
    first_line_indent: Optional[float] = None,
    space_before: float = 0.0,
    space_after: float = 0.0,
    keep_with_next: bool = False,
    bold: bool = False,
):
    p = doc.add_paragraph()
    p.alignment = align if align is not None else WD_ALIGN_PARAGRAPH.LEFT
    pf = p.paragraph_format
    pf.left_indent = Inches(left_indent)
    pf.right_indent = Inches(right_indent)
    if first_line_indent is not None:
        pf.first_line_indent = Inches(first_line_indent)
    pf.space_before = Pt(space_before)
    pf.space_after = Pt(space_after)
    pf.keep_with_next = keep_with_next

    run = p.add_run(text)
    run.bold = bold
    run.font.name = "Courier New"
    run.font.size = Pt(12)
    return p


def export_scenes_to_docx(
    scenes: List[Scene],
    template_path: str = "template.docx",
) -> bytes:
    doc = try_load_template(template_path)
    clear_document_body(doc)
    set_document_defaults(doc)

    add_paragraph(
        doc,
        "SCREENPLAY",
        align=WD_ALIGN_PARAGRAPH.CENTER,
        space_before=18,
        space_after=18,
        bold=True,
    )
    add_paragraph(
        doc,
        "Converted Draft",
        align=WD_ALIGN_PARAGRAPH.CENTER,
        space_after=24,
    )
    doc.add_page_break()

    for scene in scenes:
        add_paragraph(
            doc,
            scene.heading,
            bold=True,
            space_before=6,
            space_after=6,
            keep_with_next=True,
        )

        for block in scene.blocks:
            if block.kind == "action":
                add_paragraph(
                    doc,
                    block.text,
                    space_after=6,
                )

            elif block.kind == "character":
                add_paragraph(
                    doc,
                    block.text,
                    left_indent=2.2,
                    space_before=6,
                    space_after=0,
                    keep_with_next=True,
                )

            elif block.kind == "parenthetical":
                add_paragraph(
                    doc,
                    block.text,
                    left_indent=1.8,
                    right_indent=2.0,
                    space_after=0,
                    keep_with_next=True,
                )

            elif block.kind == "dialogue":
                add_paragraph(
                    doc,
                    block.text,
                    left_indent=1.4,
                    right_indent=1.6,
                    space_after=3,
                )

            elif block.kind == "transition":
                add_paragraph(
                    doc,
                    block.text,
                    align=WD_ALIGN_PARAGRAPH.RIGHT,
                    space_before=6,
                    space_after=6,
                    bold=True,
                )

        add_paragraph(doc, "", space_after=6)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


# =========================================================
# Preview helpers
# =========================================================

def build_preview_text(scenes: List[Scene]) -> str:
    parts: List[str] = []
    for scene in scenes:
        parts.append(scene.heading)
        parts.append("")
        for block in scene.blocks:
            parts.append(block.text)
            parts.append("")
    return "\n".join(parts).strip()


def process_uploaded_file(uploaded_file) -> Tuple[List[str], List[str], List[Block], List[Scene]]:
    ext = os.path.splitext(uploaded_file.name)[1].lower()

    if ext == ".txt":
        raw_lines = read_txt_file(uploaded_file)
    elif ext == ".docx":
        raw_lines = read_docx_file(uploaded_file)
    else:
        raise ValueError("지원하지 않는 파일 형식입니다. .txt 또는 .docx 파일을 업로드하세요.")

    cleaned_lines = remove_meta_and_noise(raw_lines)
    blocks = classify_lines(cleaned_lines)
    scenes = blocks_to_scenes(blocks)
    return raw_lines, cleaned_lines, blocks, scenes


# =========================================================
# Streamlit UI
# =========================================================

def main():
    st.set_page_config(
        page_title="Screenplay Converter",
        layout="wide",
        initial_sidebar_state="collapsed"
    )

    st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    @import url('https://cdn.jsdelivr.net/gh/projectnoonnu/2408-3@latest/Paperlogy.css');
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&display=swap');

    :root {
        --navy: #191970; --y: #FFCB05; --bg: #F7F7F5;
        --card: #FFFFFF; --card-border: #E2E2E0; --t: #1A1A2E;
        --dim: #8E8E99; --light-bg: #EEEEF6;
        --display: 'Playfair Display', 'Paperlogy', 'Georgia', serif;
        --body: 'Pretendard', -apple-system, sans-serif;
        --heading: 'Paperlogy', 'Pretendard', sans-serif;
    }

    html, body, [class*="css"] {
        font-family: var(--body);
        color: var(--t);
        -webkit-font-smoothing: antialiased;
    }

    .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"],
    [data-testid="stMainBlockContainer"], [data-testid="stHeader"],
    [data-testid="stBottom"] {
        background-color: var(--bg) !important;
        color: var(--t) !important;
    }

    section[data-testid="stSidebar"] { display: none !important; }

    .block-container {
        padding-top: 2.2rem !important;
        padding-bottom: 3rem !important;
        max-width: 1200px !important;
    }

    .header {
        font-size: 0.85rem;
        font-weight: 700;
        color: var(--navy);
        letter-spacing: 0.15em;
        font-family: var(--heading);
        margin-bottom: 0.35rem;
    }

    .brand-title {
        font-size: 2.7rem;
        font-weight: 900;
        color: var(--navy);
        font-family: var(--display);
        letter-spacing: -0.02em;
        position: relative;
        display: inline-block;
        margin-bottom: 0.2rem;
    }

    .brand-title::after {
        content: '';
        position: absolute;
        bottom: 2px;
        left: 0;
        width: 100%;
        height: 4px;
        background: var(--y);
        border-radius: 2px;
    }

    .sub {
        font-size: 0.74rem;
        color: var(--dim);
        letter-spacing: 0.15em;
        margin-top: 0.35rem;
        margin-bottom: 1.3rem;
    }

    .callout {
        background: var(--light-bg);
        border-left: 4px solid var(--navy);
        padding: 0.95rem 1.1rem;
        margin: 0.65rem 0 1.2rem 0;
        border-radius: 0 8px 8px 0;
        font-size: 0.92rem;
        color: var(--t);
    }

    .section-header {
        background: var(--y);
        color: var(--navy);
        padding: 0.68rem 1rem;
        border-radius: 6px;
        font-weight: 800;
        font-size: 1rem;
        font-family: var(--heading);
        margin: 1.4rem 0 0.85rem 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .section-header .en {
        font-family: var(--display);
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        opacity: 0.7;
    }

    .small-meta {
        font-size: 0.8rem;
        color: var(--dim);
        margin-top: -0.15rem;
        margin-bottom: 0.5rem;
    }

    .meta-chip-wrap {
        display: flex;
        gap: 0.6rem;
        flex-wrap: wrap;
        margin: 0.4rem 0 1rem 0;
    }

    .meta-chip {
        display: inline-block;
        padding: 0.36rem 0.75rem;
        border-radius: 999px;
        background: var(--card);
        border: 1px solid var(--card-border);
        color: var(--t);
        font-size: 0.8rem;
        font-weight: 700;
    }

    .status-note {
        font-size: 0.83rem;
        color: var(--dim);
        margin: 0.45rem 0 1rem 0;
    }

    .stTextArea textarea {
        background-color: var(--card) !important;
        color: var(--t) !important;
        border: 1.5px solid var(--card-border) !important;
        border-radius: 8px !important;
        font-family: var(--body) !important;
        font-size: 0.92rem !important;
        line-height: 1.55 !important;
    }

    .stDownloadButton > button {
        color: var(--navy) !important;
        border: 1.5px solid var(--y) !important;
        background-color: var(--y) !important;
        border-radius: 8px !important;
        font-family: var(--body) !important;
        font-weight: 800 !important;
        font-size: 0.92rem !important;
        padding: 0.62rem 1.25rem !important;
    }
    </style>
    """, unsafe_allow_html=True)

    template_exists = os.path.exists("template.docx")

    st.markdown('<div class="header">BLUE JEANS SCREENPLAY TOOLS</div>', unsafe_allow_html=True)
    st.markdown('<div class="brand-title">Screenplay Converter</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub">TXT / DOCX → HOLLYWOOD SCREENPLAY FORMAT DOCX</div>', unsafe_allow_html=True)

    st.markdown(
        """
        <div class="callout">
            원고 파일을 업로드하면 개발용 메타 텍스트를 제거하고,
            씬 / 지문 / 인물명 / 대사를 정리해 헐리우드 표준에 가까운 DOCX로 변환합니다.
        </div>
        """,
        unsafe_allow_html=True
    )

    chip_text = "TEMPLATE READY" if template_exists else "NO TEMPLATE"
    st.markdown(
        f"""
        <div class="meta-chip-wrap">
            <div class="meta-chip">OUTPUT: DOCX</div>
            <div class="meta-chip">STYLE: HOLLYWOOD</div>
            <div class="meta-chip">{chip_text}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="section-header"><span>원고 업로드</span><span class="en">INPUT</span></div>',
        unsafe_allow_html=True
    )
    st.markdown('<div class="small-meta">지원 형식: .txt, .docx</div>', unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "원고 파일 업로드",
        type=["txt", "docx"],
        label_visibility="collapsed"
    )

    if not uploaded_file:
        st.info("파일을 업로드하면 변환 결과와 DOCX 다운로드 버튼이 표시됩니다.")
        return

    try:
        raw_lines, cleaned_lines, blocks, scenes = process_uploaded_file(uploaded_file)
    except Exception as e:
        st.error(f"처리 중 오류가 발생했습니다: {e}")
        return

    st.markdown(
        '<div class="section-header"><span>변환 미리보기</span><span class="en">PREVIEW</span></div>',
        unsafe_allow_html=True
    )

    st.markdown(
        f"""
        <div class="status-note">
            원문 {len(raw_lines)}줄 → 정리 {len(cleaned_lines)}줄 ·
            블록 {len(blocks)}개 · 씬 {len(scenes)}개 감지
        </div>
        """,
        unsafe_allow_html=True
    )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**원문 추출**")
        st.text_area(
            "원문 추출",
            value="\n".join(raw_lines),
            height=560,
            label_visibility="collapsed"
        )

    with col2:
        st.markdown("**구조화 결과**")
        st.text_area(
            "구조화 결과",
            value=build_preview_text(scenes),
            height=560,
            label_visibility="collapsed"
        )

    st.markdown(
        '<div class="section-header"><span>출력 파일</span><span class="en">EXPORT</span></div>',
        unsafe_allow_html=True
    )

    try:
        output_bytes = export_scenes_to_docx(scenes, template_path="template.docx")
    except Exception as e:
        st.error(f"DOCX 생성 중 오류가 발생했습니다: {e}")
        return

    st.download_button(
        label="DOCX 다운로드",
        data=output_bytes,
        file_name=DEFAULT_OUTPUT_NAME,
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


if __name__ == "__main__":
    main()
