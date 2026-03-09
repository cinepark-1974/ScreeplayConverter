APP_CSS = """
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
    padding-top: 4.8rem !important;
    padding-bottom: 3.2rem !important;
    max-width: 1120px !important;
}

[data-testid="stAppViewContainer"] {
    padding-top: 0.5rem !important;
}

[data-testid="stHeader"] {
    background: transparent !important;
}

.brand-wrap {
    padding-top: 0.8rem;
    margin-bottom: 0.6rem;
}

.header {
    font-size: 0.82rem;
    font-weight: 700;
    color: var(--navy);
    letter-spacing: 0.15em;
    font-family: var(--heading);
    margin-top: 0.8rem;
    margin-bottom: 0.65rem;
    line-height: 1.5;
}

.brand-title {
    font-size: 2.45rem;
    font-weight: 900;
    color: var(--navy);
    font-family: var(--display);
    letter-spacing: -0.02em;
    position: relative;
    display: inline-block;
    line-height: 1.28;
    padding-top: 0.16em;
    padding-bottom: 0.16em;
    margin-top: 0.15rem;
    margin-bottom: 0.35rem;
    overflow: visible !important;
}

.header {
    font-size: 0.82rem;
    font-weight: 700;
    color: var(--navy);
    letter-spacing: 0.15em;
    font-family: var(--heading);
    margin-bottom: 0.5rem;
    line-height: 1.4;
}

.brand-title {
    font-size: 2.45rem;
    font-weight: 900;
    color: var(--navy);
    font-family: var(--display);
    letter-spacing: -0.02em;
    position: relative;
    display: inline-block;
    line-height: 1.18;
    padding-top: 0.08em;
    padding-bottom: 0.12em;
    margin-bottom: 0.28rem;
    overflow: visible !important;
}

.brand-title::after {
    content: '';
    position: absolute;
    bottom: 0px;
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
    margin-bottom: 1.2rem;
}

.callout {
    background: var(--light-bg);
    border-left: 4px solid var(--navy);
    padding: 0.95rem 1.1rem;
    margin: 0.65rem 0 1.05rem 0;
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
    margin: 1.15rem 0 0.7rem 0;
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
    font-size: 0.84rem;
    color: var(--dim);
    margin: 0.2rem 0 0.9rem 0;
    line-height: 1.55;
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
"""
