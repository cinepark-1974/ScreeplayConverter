import io
import os
import re
import tempfile
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import streamlit as st
from docx import Document

from ui_style import APP_CSS


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
DEFAULT_OUTPUT_NAME = "converted_korean_screenplay.docx"

STYLE_SCENE = "S#1. 씬번호"
STYLE_ACTION = "각본지문"
STYLE_DIALOGUE = "각본대사"

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
    r"^\s*장르\s*[:：]",
    r"^\s*genre\s*[:：]",
    r"^\s*writer engine",
    r"^\s*blue jeans pictures",
    r"^\s*blue jeans screenplay",
    r"^\s*version\s*[:：]?",
    r"^\s*v\d+(\.\d+)?",
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
    "낮", "밤", "아침", "새벽", "저녁", "그날", "잠시 후", "다음날", "다음 날",
    "현재", "과거", "3년 전", "현재시점"
]

LOCATION_CUE_WORDS = [
    "옥상", "복도", "병실", "사무실", "주차장", "골목", "거리", "부엌", "주방",
    "거실", "방", "학교", "교실", "경찰서", "병원", "엘리베이터", "화장실",
    "수면", "호수", "창고", "지하", "계단", "로비", "운동장", "마당",
    "펜션", "식당", "독", "선착장", "저수지", "창가", "차 안", "차안",
    "ROOFTOP", "HALLWAY", "OFFICE", "PARKING", "ALLEY", "STREET",
    "KITCHEN", "LIVING ROOM", "BEDROOM", "CLASSROOM", "POLICE STATION",
    "HOSPITAL", "ELEVATOR", "BATHROOM", "LAKE", "WAREHOUSE", "BASEMENT",
    "STAIRS", "LOBBY", "YARD", "DOCK", "DINING", "PENSION"
]

HEADER_NOISE_PATTERNS = [
    r"^\s*blue jeans pictures\s*$",
    r"^\s*writer engine\s*$",
    r"^\s*장르\s*[:：].*$",
    r"^\s*genre\s*[:：].*$",
    r"^\s*\d+막\s*[—\-]\s*beat\s*\d+.*$",
    r"^\s*beat\s*\d+\.\s*.*$",
    r"^\s*beat\s*\d+\s*.*$",
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


def looks_like_header_noise(line: str) -> bool:
    s = normalize_line(line)
    if not s:
        return False
    return any(re.match(p, s, flags=re.IGNORECASE) for p in HEADER_NOISE_PATTERNS)


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
        if any(t in s.upper() for t in TIME_WORDS) or " - " in s or " / " in s or "—" in s:
            return True

    return False


def strip_scene_number_prefix(line: str) -> str:
    s = normalize_line(line)
    s = re.sub(r"^\s*S#?\s*\d+\.?\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"^\s*SCENE\s+\d+\.?\s*", "", s, flags=re.IGNORECASE)
    return s.strip()


def canonical_scene_heading(line: str) -> str:
    s = strip_scene_number_prefix(line)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


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
    seen_first_scene = False

    for line in lines:
        if line == "":
            cleaned.append(line)
            continue

        if looks_like_divider(line):
            continue

        if not seen_first_scene:
            if looks_like_header_noise(line) or looks_like_meta(line):
                continue

        if looks_like_scene_heading(line):
            seen_first_scene = True

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
            blocks.append(Block("transition", normalize_line(line)))
            mode = None
            continue

        if looks_like_scene_heading(line):
            heading = canonical_scene_heading(line)
            blocks.append(Block("scene_heading", heading))
            mode = None
            continue

        if is_probable_character_name(line) and next_line and not looks_like_scene_heading(next_line):
            blocks.append(Block("character", normalize_line(line)))
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
            current_scene = Scene(heading="장소 미상")
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
# DOCX style helpers
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


def style_exists(doc: Document, style_name: str) -> bool:
    try:
        _ = doc.styles[style_name]
        return True
    except KeyError:
        return False


def add_styled_paragraph(doc: Document, text: str, preferred_style: str):
    p = doc.add_paragraph(text)
    if style_exists(doc, preferred_style):
        p.style = preferred_style
    return p


# =========================================================
# Dialogue formatter
# =========================================================

def build_dialogue_line(character: str, dialogue: str) -> str:
    character = normalize_line(character)
    dialogue = normalize_line(dialogue)
    return f"{character}\t\t{dialogue}"


def scene_to_korean_blocks(scene: Scene) -> List[Tuple[str, str]]:
    """
    Returns list of (style_name, text)
    style_name is one of:
    - S#1. 씬번호
    - 각본지문
    - 각본대사
    """
    results: List[Tuple[str, str]] = []

    # scene heading: code writes only heading text; Word style handles scene numbering
    results.append((STYLE_SCENE, scene.heading))

    pending_character: Optional[str] = None
    pending_parenthetical: Optional[str] = None

    for block in scene.blocks:
        if block.kind == "action":
            if pending_character:
                # character without spoken line: flush name only
                results.append((STYLE_DIALOGUE, pending_character))
                pending_character = None
                pending_parenthetical = None
            results.append((STYLE_ACTION, block.text))

        elif block.kind == "character":
            if pending_character:
                results.append((STYLE_DIALOGUE, pending_character))
            pending_character = block.text
            pending_parenthetical = None

        elif block.kind == "parenthetical":
            # user said parenthetical is rare and can be handled manually.
            # keep temporarily and append inline if a dialogue line follows.
            pending_parenthetical = block.text

        elif block.kind == "dialogue":
            if pending_character:
                if pending_parenthetical:
                    dialogue_text = f"{pending_parenthetical} {block.text}".strip()
                else:
                    dialogue_text = block.text
                results.append((STYLE_DIALOGUE, build_dialogue_line(pending_character, dialogue_text)))
                pending_character = None
                pending_parenthetical = None
            else:
                # fallback: dialogue line without explicit speaker
                results.append((STYLE_DIALOGUE, block.text))

        elif block.kind == "transition":
            if pending_character:
                results.append((STYLE_DIALOGUE, pending_character))
                pending_character = None
                pending_parenthetical = None
            results.append((STYLE_ACTION, block.text))

    if pending_character:
        results.append((STYLE_DIALOGUE, pending_character))

    return results


# =========================================================
# DOCX Export
# =========================================================

def export_scenes_to_docx(
    scenes: List[Scene],
    template_path: str = "template.docx",
) -> bytes:
    doc = try_load_template(template_path)
    clear_document_body(doc)

    for scene in scenes:
        styled_blocks = scene_to_korean_blocks(scene)

        for style_name, text in styled_blocks:
            add_styled_paragraph(doc, text, style_name)

        # scene spacing: rely on style if possible, but keep one blank paragraph
        doc.add_paragraph("")

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

        pending_character: Optional[str] = None
        pending_parenthetical: Optional[str] = None

        for block in scene.blocks:
            if block.kind == "action":
                if pending_character:
                    parts.append(pending_character)
                    parts.append("")
                    pending_character = None
                    pending_parenthetical = None
                parts.append(block.text)
                parts.append("")

            elif block.kind == "character":
                if pending_character:
                    parts.append(pending_character)
                    parts.append("")
                pending_character = block.text
                pending_parenthetical = None

            elif block.kind == "parenthetical":
                pending_parenthetical = block.text

            elif block.kind == "dialogue":
                if pending_character:
                    if pending_parenthetical:
                        combined = f"{pending_parenthetical} {block.text}".strip()
                    else:
                        combined = block.text
                    parts.append(build_dialogue_line(pending_character, combined))
                    parts.append("")
                    pending_character = None
                    pending_parenthetical = None
                else:
                    parts.append(block.text)
                    parts.append("")

            elif block.kind == "transition":
                if pending_character:
                    parts.append(pending_character)
                    parts.append("")
                    pending_character = None
                    pending_parenthetical = None
                parts.append(block.text)
                parts.append("")

        if pending_character:
            parts.append(pending_character)
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

    st.markdown(APP_CSS, unsafe_allow_html=True)

    template_exists = os.path.exists("template.docx")

    st.markdown(
        """
        <div class="brand-wrap">
            <div class="header">BLUE JEANS SCREENPLAY TOOLS</div>
            <div class="brand-title">Screenplay Converter</div>
            <div class="sub">TXT / DOCX → KOREAN SCREENPLAY FORMAT DOCX</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="callout">
            원고 파일을 업로드하면 개발용 메타 텍스트를 제거하고,
            씬 / 지문 / 대사를 한국형 시나리오 DOCX 작업본으로 정리합니다.
        </div>
        """,
        unsafe_allow_html=True
    )

    chip_text = "TEMPLATE READY" if template_exists else "NO TEMPLATE"
    st.markdown(
        f"""
        <div class="meta-chip-wrap">
            <div class="meta-chip">OUTPUT: DOCX</div>
            <div class="meta-chip">STYLE: KOREAN SCREENPLAY</div>
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

    col1, col2 = st.columns([1, 1.15])

    with col1:
        st.markdown("**원문 추출**")
        st.text_area(
            "원문 추출",
            value="\n".join(raw_lines),
            height=640,
            label_visibility="collapsed"
        )

    with col2:
        st.markdown("**구조화 결과**")
        st.text_area(
            "구조화 결과",
            value=build_preview_text(scenes),
            height=640,
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
