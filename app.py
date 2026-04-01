"""
DocDiff Pro — Streamlit Document Comparison Tool
Futuristic dark-theme UI with word-level diff highlighting.
"""
import base64
import io
import logging
import sys
from pathlib import Path
from typing import Optional

import streamlit as st

# ── path so local modules are importable ────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))

from diff_routes import CompareRequest, processor
from diff_service import (
    DiffResult,
    WordChange,
    get_pdf_page_count,
    inject_html_highlights,
    render_pdf_page_with_highlights,
)

logging.basicConfig(level=logging.WARNING)

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DocDiff Pro",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ───────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
/* ── Base ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* ── Background ── */
.stApp {
    background: linear-gradient(135deg, #0a0e1a 0%, #0d1421 50%, #0a1628 100%);
    background-attachment: fixed;
}

/* ── Hide default Streamlit elements ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.5rem; padding-bottom: 2rem; }

/* ── Logo / title bar ── */
.logo-bar {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 18px 0 6px 0;
    margin-bottom: 8px;
}
.logo-icon {
    font-size: 2.4rem;
    filter: drop-shadow(0 0 12px #00d4ff88);
}
.logo-title {
    font-size: 2rem;
    font-weight: 700;
    background: linear-gradient(90deg, #00d4ff, #7b61ff, #00ff9d);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -0.5px;
}
.logo-sub {
    font-size: 0.82rem;
    color: #4a6a8a;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-top: -4px;
}

/* ── Upload cards ── */
.upload-card {
    background: linear-gradient(145deg, #111827, #0f1f2e);
    border: 1px solid #1e3a5f;
    border-radius: 16px;
    padding: 24px 20px;
    transition: border-color 0.3s, box-shadow 0.3s;
}
.upload-card:hover {
    border-color: #00d4ff55;
    box-shadow: 0 0 24px #00d4ff18;
}
.upload-label {
    font-size: 0.75rem;
    font-weight: 600;
    color: #00d4ff;
    letter-spacing: 2.5px;
    text-transform: uppercase;
    margin-bottom: 10px;
}
.file-badge {
    background: linear-gradient(90deg, #0d1f35, #0a1628);
    border: 1px solid #1e3a5f88;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 0.83rem;
    color: #a0c4e0;
    margin-top: 10px;
    display: flex;
    align-items: center;
    gap: 8px;
}

/* ── Compare button ── */
.stButton > button {
    background: linear-gradient(135deg, #00d4ff22, #7b61ff22) !important;
    border: 1.5px solid #00d4ff !important;
    border-radius: 10px !important;
    color: #00d4ff !important;
    font-weight: 600 !important;
    font-size: 1rem !important;
    padding: 12px 40px !important;
    transition: all 0.25s !important;
    letter-spacing: 1px !important;
    text-transform: uppercase !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #00d4ff44, #7b61ff44) !important;
    box-shadow: 0 0 24px #00d4ff66 !important;
    transform: translateY(-1px) !important;
}
.stButton > button:active { transform: translateY(0) !important; }

/* ── Section divider ── */
.section-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, #1e3a5f, #00d4ff44, #1e3a5f, transparent);
    margin: 24px 0;
}

/* ── Doc panel headers ── */
.doc-panel-header {
    background: linear-gradient(90deg, #0d1f35, #111827);
    border: 1px solid #1e3a5f;
    border-radius: 10px 10px 0 0;
    padding: 10px 16px;
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 1.5px;
    text-transform: uppercase;
}
.doc1-header { color: #ff6b6b; border-color: #ff6b6b44; }
.doc2-header { color: #6bff9e; border-color: #6bff9e44; }

/* ── Doc content pane ── */
.doc-pane {
    background: #080e18;
    border: 1px solid #1e3a5f;
    border-top: none;
    border-radius: 0 0 10px 10px;
    padding: 0;
    overflow: hidden;
    min-height: 500px;
}

/* ── Analytics bubbles (rendered via HTML) ── */
.bubble-row {
    display: flex;
    flex-direction: column;
    gap: 14px;
    padding: 8px 4px;
}
.bubble {
    border-radius: 14px;
    padding: 14px 16px;
    display: flex;
    align-items: center;
    gap: 14px;
    border: 1px solid transparent;
}
.bubble-total {
    background: linear-gradient(135deg, #1a2744, #0f1f35);
    border-color: #2a4a7f;
}
.bubble-added {
    background: linear-gradient(135deg, #0d2d1a, #0a2016);
    border-color: #1a6b36;
}
.bubble-removed {
    background: linear-gradient(135deg, #2d1010, #200a0a);
    border-color: #6b2020;
}
.bubble-modified {
    background: linear-gradient(135deg, #2d1e08, #201408);
    border-color: #6b4a10;
}
.bubble-images {
    background: linear-gradient(135deg, #0e1a2d, #0a1428);
    border-color: #1a4a6b;
}
.bubble-count {
    font-size: 2rem;
    font-weight: 700;
    line-height: 1;
    font-family: 'JetBrains Mono', monospace;
}
.bubble-label {
    font-size: 0.72rem;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    opacity: 0.75;
}

/* ── Page navigator ── */
.page-nav {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 12px;
    padding: 12px 0 4px;
    font-size: 0.82rem;
    color: #4a6a8a;
}

/* ── Legend ── */
.legend-row {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    padding: 10px 0;
}
.legend-item {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.75rem;
    color: #7a9ab5;
}
.legend-dot {
    width: 14px;
    height: 14px;
    border-radius: 3px;
    flex-shrink: 0;
}

/* ── Selectbox / number input ── */
div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div {
    background: #0d1421 !important;
    border-color: #1e3a5f !important;
    color: #a0c4e0 !important;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #080e18, #0a1220) !important;
    border-right: 1px solid #1e3a5f;
}
section[data-testid="stSidebar"] > div {
    padding-top: 1.5rem;
}

/* ── Spinner ── */
.stSpinner > div > div { border-top-color: #00d4ff !important; }

/* ── Alert / info ── */
.stAlert { border-radius: 10px !important; }

/* ── Iframe wrapper ── */
.iframe-wrap {
    border-radius: 0 0 10px 10px;
    overflow: hidden;
}

/* ── Scrollable html pane ── */
.html-scroll {
    max-height: 600px;
    overflow-y: auto;
    background: #080e18;
    color: #cdd9e5;
    padding: 20px;
    font-family: 'Inter', sans-serif;
    font-size: 14px;
    line-height: 1.7;
}
.html-scroll::-webkit-scrollbar { width: 6px; }
.html-scroll::-webkit-scrollbar-track { background: #0a1220; }
.html-scroll::-webkit-scrollbar-thumb { background: #1e3a5f; border-radius: 3px; }
</style>
""",
    unsafe_allow_html=True,
)


# ── Helpers ─────────────────────────────────────────────────────────────────

def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def _file_icon(name: str) -> str:
    ext = Path(name).suffix.lower()
    icons = {
        '.pdf': '📄', '.docx': '📝', '.doc': '📝',
        '.txt': '📃', '.md': '📋',
        '.py': '🐍', '.cpp': '⚙️', '.java': '☕', '.js': '🟨',
        '.ts': '🔷', '.html': '🌐', '.json': '🗂️',
        '.xml': '🗃️', '.csv': '📊',
    }
    return icons.get(ext, '📁')


def _fmt_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size/1024:.1f} KB"
    return f"{size/(1024*1024):.1f} MB"


def _render_html_pane(html: str, height: int = 600) -> None:
    """Render HTML inside a self-contained dark iframe (styles included inline)."""
    doc = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{
  background:#080e18;color:#cdd9e5;
  font-family:'Segoe UI',Inter,Arial,sans-serif;
  font-size:14px;line-height:1.75;
  padding:16px 20px;
}}
p,li{{margin:0.4em 0}}
h1{{font-size:1.5em;color:#e0f0ff;margin:0.8em 0 0.3em}}
h2{{font-size:1.25em;color:#c0d8f0;margin:0.7em 0 0.3em}}
h3,h4,h5,h6{{font-size:1em;color:#a0c4e0;margin:0.6em 0 0.2em}}
a{{color:#00d4ff}}
ul,ol{{padding-left:1.4em;margin:0.4em 0}}
table{{border-collapse:collapse;width:100%;margin:0.5em 0}}
th{{background:#0d1f35;color:#a0c4e0;padding:7px 12px;border:1px solid #1e3a5f;text-align:left}}
td{{padding:6px 12px;border:1px solid #1e3a5f}}
code{{background:#0d1421;border-radius:3px;padding:1px 5px;
      font-family:'JetBrains Mono',Consolas,monospace;font-size:12px}}
pre{{background:#0d1117;border-radius:6px;padding:12px;overflow-x:auto;margin:0.5em 0}}
pre code{{padding:0;background:none}}
mark{{border-radius:3px;padding:1px 3px}}
::-webkit-scrollbar{{width:6px;height:6px}}
::-webkit-scrollbar-track{{background:#0a1220}}
::-webkit-scrollbar-thumb{{background:#1e3a5f;border-radius:3px}}
::-webkit-scrollbar-thumb:hover{{background:#2a5a8f}}
</style></head><body>
{html}
</body></html>"""
    st.components.v1.html(doc, height=height, scrolling=True)


def _render_pdf_scrollable(
    pdf_bytes: bytes,
    changes,
    side: str,
    height: int = 640,
) -> None:
    """
    Render ALL PDF pages (up to 20) with highlights stacked in a
    single scrollable dark container — no page-flip needed.
    """
    page_count = get_pdf_page_count(pdf_bytes)
    cap = min(page_count, 20)

    parts: list[str] = []
    for pn in range(1, cap + 1):
        png = render_pdf_page_with_highlights(pdf_bytes, pn, changes, side, zoom=1.3)
        if png:
            b64 = _b64(png)
            parts.append(
                f'<div style="margin-bottom:6px">'
                f'<div style="font-size:11px;color:#4a6a8a;padding:3px 8px;'
                f'background:#0d1421;border-bottom:1px solid #1e3a5f">Page {pn} / {page_count}</div>'
                f'<img src="data:image/png;base64,{b64}" '
                f'style="width:100%;display:block;vertical-align:top"/>'
                f'</div>'
            )

    footer = (
        f'<p style="color:#4a6a8a;text-align:center;font-size:11px;padding:10px 0">'
        f'Showing first {cap} of {page_count} pages</p>'
        if page_count > cap else ''
    )

    container = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#080e18;padding:0}}
::-webkit-scrollbar{{width:6px}}
::-webkit-scrollbar-track{{background:#0a1220}}
::-webkit-scrollbar-thumb{{background:#1e3a5f;border-radius:3px}}
::-webkit-scrollbar-thumb:hover{{background:#2a5a8f}}
</style></head><body>
{''.join(parts)}
{footer}
</body></html>"""
    st.components.v1.html(container, height=height, scrolling=True)


def _analytics_html(summary: dict) -> str:
    total = summary.get('total_changes', 0)
    added = summary.get('words_added', 0)
    removed = summary.get('words_removed', 0)
    modified = summary.get('words_replaced', 0)
    imgs = summary.get('images_added', 0) + summary.get('images_removed', 0)

    def bubble(cls, icon, count, label, count_color):
        return f"""
        <div class="bubble {cls}">
            <span style="font-size:1.6rem">{icon}</span>
            <div>
                <div class="bubble-count" style="color:{count_color}">{count}</div>
                <div class="bubble-label" style="color:{count_color}88">{label}</div>
            </div>
        </div>"""

    return f"""
    <div class="bubble-row">
        {bubble('bubble-total',   '🔍', total,    'Total Differences', '#00d4ff')}
        {bubble('bubble-added',   '➕', added,    'Words Added',       '#3cff7a')}
        {bubble('bubble-removed', '➖', removed,  'Words Removed',     '#ff5050')}
        {bubble('bubble-modified','✏️', modified, 'Words Modified',    '#ffaa00')}
        {bubble('bubble-images',  '🖼️', imgs,     'Image Changes',     '#7b9fff')}
    </div>
    """


def _legend_html() -> str:
    items = [
        ('#ff5050', 'Removed'),
        ('#3cff7a', 'Added'),
        ('#ffaa00', 'Modified (old)'),
        ('#3cb4ff', 'Modified (new)'),
    ]
    dots = "".join(
        f'<div class="legend-item">'
        f'<div class="legend-dot" style="background:{c}"></div>'
        f'<span>{lbl}</span></div>'
        for c, lbl in items
    )
    return f'<div class="legend-row">{dots}</div>'


# ── Session state keys ────────────────────────────────────────────────────────
SS_RESULT = "diff_result"


def _init_state():
    if SS_RESULT not in st.session_state:
        st.session_state[SS_RESULT] = None


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    _init_state()

    # ── Logo ─────────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div class="logo-bar">
            <span class="logo-icon">🔍</span>
            <div>
                <div class="logo-title">DocDiff Pro</div>
                <div class="logo-sub">Intelligent Document Comparison</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(
            '<p style="color:#00d4ff;font-size:0.7rem;letter-spacing:2px;'
            'text-transform:uppercase;font-weight:600;margin-bottom:8px">'
            '📊 Analytics</p>',
            unsafe_allow_html=True,
        )

        result: Optional[DiffResult] = st.session_state[SS_RESULT]

        if result is not None:
            st.components.v1.html(
                _analytics_html(result.summary), height=370, scrolling=False
            )
            st.markdown("<hr style='border-color:#1e3a5f;margin:16px 0'>",
                        unsafe_allow_html=True)
            st.components.v1.html(_legend_html(), height=70, scrolling=False)

            # Change list
            with st.expander("📋 Change details", expanded=False):
                changes = result.word_changes
                if not changes:
                    st.info("No word-level changes found.")
                else:
                    for i, ch in enumerate(changes[:100], 1):
                        if ch.change_type == 'added':
                            st.markdown(
                                f"<span style='color:#3cff7a'>➕ {ch.new_text}</span>",
                                unsafe_allow_html=True)
                        elif ch.change_type == 'removed':
                            st.markdown(
                                f"<span style='color:#ff5050'>➖ {ch.old_text}</span>",
                                unsafe_allow_html=True)
                        else:
                            st.markdown(
                                f"<span style='color:#ffaa00'>✏️ "
                                f"<s>{ch.old_text}</s> → {ch.new_text}</span>",
                                unsafe_allow_html=True)
                    if len(changes) > 100:
                        st.caption(f"… and {len(changes)-100} more changes")
        else:
            st.markdown(
                '<p style="color:#2a4a6a;font-size:0.85rem;margin-top:24px;'
                'text-align:center">Upload two files and click Compare to see analytics.</p>',
                unsafe_allow_html=True,
            )

        st.markdown(
            '<hr style="border-color:#1e3a5f;margin:20px 0">'
            '<p style="color:#1e3a5f;font-size:0.68rem;text-align:center">'
            'DocDiff Pro · Streamlit Cloud</p>',
            unsafe_allow_html=True,
        )

    # ── Upload section ────────────────────────────────────────────────────────
    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown('<div class="upload-label">📄 Document 1 — Original</div>',
                    unsafe_allow_html=True)
        file1 = st.file_uploader(
            "Drop file 1 here",
            key="uploader1",
            label_visibility="collapsed",
            help="PDF, DOCX, DOC, TXT, MD, or code files up to 50 MB",
        )
        if file1:
            st.markdown(
                f'<div class="file-badge">'
                f'{_file_icon(file1.name)} '
                f'<strong style="color:#e0f0ff">{file1.name}</strong>'
                f'<span style="margin-left:auto;color:#4a6a8a">{_fmt_size(file1.size)}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    with col2:
        st.markdown('<div class="upload-label">📄 Document 2 — Revised</div>',
                    unsafe_allow_html=True)
        file2 = st.file_uploader(
            "Drop file 2 here",
            key="uploader2",
            label_visibility="collapsed",
            help="PDF, DOCX, DOC, TXT, MD, or code files up to 50 MB",
        )
        if file2:
            st.markdown(
                f'<div class="file-badge">'
                f'{_file_icon(file2.name)} '
                f'<strong style="color:#e0f0ff">{file2.name}</strong>'
                f'<span style="margin-left:auto;color:#4a6a8a">{_fmt_size(file2.size)}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ── Compare button ────────────────────────────────────────────────────────
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    btn_col = st.columns([1, 2, 1])[1]
    with btn_col:
        compare_clicked = st.button(
            "⚡  Compare Documents",
            use_container_width=True,
            disabled=(file1 is None or file2 is None),
        )

    if file1 is None or file2 is None:
        st.markdown(
            '<p style="text-align:center;color:#2a4a6a;font-size:0.82rem;margin-top:8px">'
            'Upload both documents to enable comparison.</p>',
            unsafe_allow_html=True,
        )

    # ── Run comparison ────────────────────────────────────────────────────────
    if compare_clicked and file1 and file2:
        with st.spinner("Analysing documents…"):
            try:
                req = CompareRequest(
                    file1_bytes=file1.read(),
                    file1_name=file1.name,
                    file2_bytes=file2.read(),
                    file2_name=file2.name,
                )
                st.session_state[SS_RESULT] = processor.compare(req)
            except ValueError as e:
                st.error(str(e))
                st.session_state[SS_RESULT] = None
            except Exception as e:
                st.error(f"Comparison failed: {e}")
                st.session_state[SS_RESULT] = None

    # ── Results ───────────────────────────────────────────────────────────────
    result: Optional[DiffResult] = st.session_state[SS_RESULT]

    if result is not None:
        total = result.summary.get('total_changes', 0)

        # ── Summary bar ──────────────────────────────────────────────────────
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

        metric_cols = st.columns(5)
        metrics = [
            ("Total", total, "#00d4ff"),
            ("Added", result.summary['words_added'], "#3cff7a"),
            ("Removed", result.summary['words_removed'], "#ff5050"),
            ("Modified", result.summary['words_replaced'], "#ffaa00"),
            ("Images", result.summary['images_added'] + result.summary['images_removed'], "#7b9fff"),
        ]
        for col, (label, val, color) in zip(metric_cols, metrics):
            with col:
                st.markdown(
                    f'<div style="background:#0d1421;border:1px solid {color}55;border-radius:12px;'
                    f'padding:14px 12px;text-align:center">'
                    f'<div style="font-size:1.9rem;font-weight:700;color:{color};'
                    f'font-family:JetBrains Mono,monospace;line-height:1">{val}</div>'
                    f'<div style="font-size:0.78rem;color:{color};opacity:0.85;letter-spacing:1px;'
                    f'text-transform:uppercase;margin-top:6px;font-weight:600">{label}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        st.markdown("<br>", unsafe_allow_html=True)

        if total == 0:
            st.success("✅ No differences found — the documents are identical!")
        else:
            # ── Two-column document viewer ────────────────────────────────────
            left_col, right_col = st.columns(2, gap="medium")

            # ── DOC 1 ─────────────────────────────────────────────────────────
            with left_col:
                st.markdown(
                    f'<div class="doc-panel-header doc1-header">'
                    f'🔴 {_file_icon(result.doc1_name)} '
                    f'<span>{result.doc1_name or "Document 1"}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                if result.doc1_type == 'pdf' and result.doc1_pdf_bytes:
                    with st.spinner("Rendering pages…"):
                        _render_pdf_scrollable(
                            result.doc1_pdf_bytes, result.word_changes, 'doc1'
                        )

                else:
                    highlighted = inject_html_highlights(
                        result.doc1_html or "", result.word_changes, 'doc1'
                    )
                    _render_html_pane(highlighted)

            # ── DOC 2 ─────────────────────────────────────────────────────────
            with right_col:
                st.markdown(
                    f'<div class="doc-panel-header doc2-header">'
                    f'🟢 {_file_icon(result.doc2_name)} '
                    f'<span>{result.doc2_name or "Document 2"}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                if result.doc2_type == 'pdf' and result.doc2_pdf_bytes:
                    with st.spinner("Rendering pages…"):
                        _render_pdf_scrollable(
                            result.doc2_pdf_bytes, result.word_changes, 'doc2'
                        )

                else:
                    highlighted = inject_html_highlights(
                        result.doc2_html or "", result.word_changes, 'doc2'
                    )
                    _render_html_pane(highlighted)

            # ── Legend ────────────────────────────────────────────────────────
            st.markdown("<br>", unsafe_allow_html=True)
            st.components.v1.html(_legend_html(), height=60, scrolling=False)


if __name__ == "__main__":
    main()
