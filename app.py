import streamlit as st
import pandas as pd
import json
import os
import subprocess
import sys
import tempfile
import threading
import requests
import xml.etree.ElementTree as ET

# ─── page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SEO Site Auditor",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── styles ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #0d1117; color: #e6edf3; }
    [data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #30363d; }

    .metric-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 16px 20px;
        text-align: center;
    }
    .metric-card .label {
        font-size: 11px;
        color: #8b949e;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        margin-bottom: 6px;
    }
    .metric-card .value {
        font-size: 26px;
        font-weight: 700;
        color: #e6edf3;
    }
    .metric-card .value.green  { color: #3fb950; }
    .metric-card .value.red    { color: #f85149; }
    .metric-card .value.yellow { color: #d29922; }

    .section-title {
        font-size: 12px;
        font-weight: 600;
        color: #8b949e;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        margin-bottom: 12px;
        padding-bottom: 6px;
        border-bottom: 1px solid #21262d;
    }

    .seo-row {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        padding: 9px 0;
        border-bottom: 1px solid #21262d;
        font-size: 13px;
    }
    .seo-row:last-child { border-bottom: none; }
    .seo-key { color: #8b949e; min-width: 220px; flex-shrink: 0; }
    .seo-val { color: #e6edf3; font-weight: 500; text-align: right; word-break: break-all; }

    .badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 600;
    }
    .badge-green  { background: #1a3a22; color: #3fb950; border: 1px solid #3fb950; }
    .badge-red    { background: #3a1a1a; color: #f85149; border: 1px solid #f85149; }
    .badge-yellow { background: #3a2e0a; color: #d29922; border: 1px solid #d29922; }
    .badge-blue   { background: #0d2137; color: #58a6ff; border: 1px solid #58a6ff; }
    .badge-gray   { background: #21262d; color: #8b949e; border: 1px solid #30363d; }

    [data-testid="stExpander"] {
        background: #161b22 !important;
        border: 1px solid #30363d !important;
        border-radius: 8px !important;
        margin-bottom: 8px !important;
    }
    [data-testid="stExpander"] summary {
        font-size: 14px !important;
        font-weight: 600 !important;
        color: #e6edf3 !important;
        padding: 12px 16px !important;
    }
    [data-testid="stExpander"] summary:hover { background: #1c2128 !important; }

    [data-testid="stDataFrame"] { border: 1px solid #30363d; border-radius: 8px; }

    .stTabs [data-baseweb="tab-list"] { background: #161b22; border-bottom: 1px solid #30363d; }
    .stTabs [data-baseweb="tab"] { color: #8b949e; font-size: 14px; }
    .stTabs [aria-selected="true"] { color: #e6edf3 !important; border-bottom: 2px solid #58a6ff !important; }

    [data-testid="stSelectbox"] > div > div {
        background: #161b22 !important;
        border: 1px solid #30363d !important;
        color: #e6edf3 !important;
    }

    .url-chip {
        background: #0d2137;
        border: 1px solid #1f6feb;
        border-radius: 6px;
        padding: 8px 14px;
        font-size: 13px;
        color: #58a6ff;
        word-break: break-all;
        margin-bottom: 16px;
    }

    .log-box {
        background: #010409;
        border: 1px solid #30363d;
        border-radius: 6px;
        padding: 12px 14px;
        font-family: monospace;
        font-size: 12px;
        color: #8b949e;
        max-height: 200px;
        overflow-y: auto;
        white-space: pre-wrap;
        word-break: break-all;
    }

    .run-info {
        background: #0d2137;
        border: 1px solid #1f6feb;
        border-radius: 6px;
        padding: 10px 14px;
        font-size: 13px;
        color: #58a6ff;
        margin-bottom: 12px;
    }

    h1, h2, h3 { color: #e6edf3 !important; }
    p, li { color: #c9d1d9; }

    #MainMenu { visibility: hidden; }
    footer    { visibility: hidden; }
    header    { visibility: hidden; }

    div[data-testid="stDownloadButton"] button {
        background: #1f6feb !important;
        color: #fff !important;
        border: none !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
    }
    div[data-testid="stDownloadButton"] button:hover {
        background: #388bfd !important;
    }
</style>
""", unsafe_allow_html=True)


# ─── session state ────────────────────────────────────────────────────────────
for key, default in [
    ("data", []),
    ("output_json_bytes", None),
    ("last_run_log", ""),
    ("analysis_done", False),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ─── helpers ─────────────────────────────────────────────────────────────────
def badge(val, kind="gray"):
    return f'<span class="badge badge-{kind}">{val}</span>'

def bool_badge(val):
    if val is True or val == "YES":
        return badge("Yes", "green")
    if val is False or val == "NO":
        return badge("No", "red")
    return badge(str(val), "gray")

def row(key, val_html):
    return (f'<div class="seo-row">'
            f'<span class="seo-key">{key}</span>'
            f'<span class="seo-val">{val_html}</span>'
            f'</div>')

def plain(val):
    if val is None or val == "":
        return badge("—", "gray")
    return f'<span>{val}</span>'

def status_badge(code):
    try:
        c = int(code)
        if 200 <= c < 300:
            return badge(c, "green")
        if 300 <= c < 400:
            return badge(c, "yellow")
        return badge(c, "red")
    except Exception:
        return badge(str(code), "red")

def length_badge(length, good_min, good_max):
    try:
        l = int(length)
        if good_min <= l <= good_max:
            return badge(f"{l} chars", "green")
        return badge(f"{l} chars", "yellow")
    except Exception:
        return badge(str(length), "gray")

def mcard(col, label, value, color=""):
    col.markdown(
        f'<div class="metric-card">'
        f'<div class="label">{label}</div>'
        f'<div class="value {color}">{value}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

PROJECT_DIR  = os.path.dirname(os.path.abspath(__file__))
SPIDER_PATH  = os.path.join(PROJECT_DIR, "reeltor_seo_from_txt.py")
SITEMAP_BASE = "https://www.reeltor.com/sitemap/{}.xml"


def fetch_sitemap_urls(number: int) -> tuple[list[str], str]:
    """Fetch URLs from reeltor sitemap. Returns (urls, error_message)."""
    url = SITEMAP_BASE.format(number)
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 404:
            return [], f"No sitemap found at {url} (404)"
        if resp.status_code != 200:
            return [], f"HTTP {resp.status_code} fetching {url}"
        root = ET.fromstring(resp.content)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        urls = [loc.text.strip() for loc in root.findall(".//sm:loc", ns) if loc.text]
        if not urls:
            return [], "Sitemap found but contains no <loc> URLs."
        return urls, ""
    except requests.exceptions.ConnectionError:
        return [], f"Could not connect to {url}"
    except ET.ParseError:
        return [], "Sitemap response could not be parsed as XML."
    except Exception as exc:
        return [], str(exc)


def run_spider(urls_file: str, output_file: str) -> tuple[bool, str]:
    """Run the scrapy spider and return (success, log_text)."""
    cmd = [
        sys.executable, "-m", "scrapy", "runspider",
        SPIDER_PATH,
        "-a", f"urls_file={urls_file}",
        "-O", output_file,          # -O overwrites output file
        "--logfile", "-",           # log to stdout/stderr
    ]
    log_lines: list[str] = []
    log_lock = threading.Lock()

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,   # merge stderr into stdout
            text=True,
            cwd=PROJECT_DIR,
        )

        log_placeholder = st.empty()

        for line in iter(process.stdout.readline, ""):
            line = line.rstrip()
            with log_lock:
                log_lines.append(line)
                # Show last 12 lines live
                visible = "\n".join(log_lines[-12:])
            log_placeholder.markdown(
                f'<div class="log-box">{visible}</div>',
                unsafe_allow_html=True,
            )

        process.wait()
        log_placeholder.empty()
        return process.returncode == 0, "\n".join(log_lines)

    except Exception as exc:
        return False, str(exc)


# ─── sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## SEO Auditor")
    st.markdown("---")

    st.markdown("**Step 1 — Sitemap Number**")
    st.markdown(
        '<span style="font-size:12px;color:#8b949e">reeltor.com/sitemap/<b style="color:#58a6ff">N</b>.xml</span>',
        unsafe_allow_html=True,
    )
    sitemap_number = st.number_input(
        "Sitemap number",
        min_value=1,
        step=1,
        value=1,
        label_visibility="collapsed",
    )
    fetch_btn = st.button("Fetch Sitemap", use_container_width=True)

    url_count = 0
    urls_preview: list[str] = []

    if fetch_btn:
        with st.spinner(f"Fetching sitemap {int(sitemap_number)}…"):
            fetched_urls, err = fetch_sitemap_urls(int(sitemap_number))
        if err:
            st.error(err)
            st.session_state["sitemap_urls"] = []
        else:
            st.session_state["sitemap_urls"] = fetched_urls
            st.session_state["sitemap_number"] = int(sitemap_number)

    if st.session_state.get("sitemap_urls"):
        all_urls = st.session_state["sitemap_urls"]
        total_available = len(all_urls)
        st.success(f"{total_available} URL{'s' if total_available != 1 else ''} from sitemap {st.session_state.get('sitemap_number', '')}")

        url_limit = st.slider(
            "How many URLs to process",
            min_value=1,
            max_value=total_available,
            value=min(50, total_available),
            step=1,
        )
        urls_preview = all_urls[:url_limit]
        url_count = len(urls_preview)

        with st.expander("Preview URLs"):
            for u in urls_preview[:20]:
                st.markdown(
                    f'<span style="font-size:12px;color:#58a6ff">{u}</span>',
                    unsafe_allow_html=True,
                )
            if url_count > 20:
                st.caption(f"… and {url_count - 20} more")

    st.markdown("---")
    st.markdown("**Step 2 — Run Analysis**")

    analyze_btn = st.button(
        f"Analyze {url_count} URL{'s' if url_count != 1 else ''}",
        type="primary",
        disabled=(url_count == 0),
    )

    # ── Filters (shown only after data is loaded) ──────────────────────────
    data = st.session_state.data
    if data:
        st.markdown("---")
        st.markdown("**Filters**")

        # Build status code options with counts
        from collections import Counter
        status_counts = Counter(str(d.get("status_code", "")) for d in data)
        status_options = sorted(status_counts.keys())
        status_labels  = [f"{s} ({status_counts[s]}x)" for s in status_options]
        label_to_code  = {lbl: code for lbl, code in zip(status_labels, status_options)}

        sel_status_labels = st.multiselect(
            "Status codes",
            options=status_labels,
            default=status_labels,
        )
        sel_status = [label_to_code[l] for l in sel_status_labels]

        sel_index = st.radio("Indexable", ["All", "Yes", "No"], horizontal=True)

        st.markdown("---")
        st.markdown("**SEO Errors — click to filter**")

        error_filters = {
            "Missing Title":       lambda d: not d.get("title"),
            "Missing Meta Desc":   lambda d: not d.get("meta_description"),
            "Missing H1":          lambda d: not d.get("has_h1"),
            "No Schema":           lambda d: d.get("schema_json_ld") != "YES",
            "Not Indexable":       lambda d: not d.get("is_indexable"),
            "No Self Canonical":   lambda d: not d.get("has_self_canonical"),
            "Images w/o Alt":      lambda d: (d.get("images_without_alt") or 0) > 0,
            "No OG Tags":          lambda d: not d.get("og_present"),
            "4xx / 5xx Errors":    lambda d: str(d.get("status_code", ""))[:1] in ("4", "5"),
            "Slow (>2s)":          lambda d: (d.get("response_time_ms") or 0) > 2000,
            "Title Too Short":     lambda d: 0 < (d.get("title_length") or 0) < 30,
            "Title Too Long":      lambda d: (d.get("title_length") or 0) > 60,
            "Desc Too Short":      lambda d: 0 < (d.get("meta_description_length") or 0) < 120,
            "Desc Too Long":       lambda d: (d.get("meta_description_length") or 0) > 160,
        }

        sel_error = st.selectbox(
            "Filter by issue",
            options=["— show all —"] + list(error_filters.keys()),
            index=0,
        )

        st.markdown("---")
        st.markdown("**Quick Stats**")
        total     = len(data)
        indexable = sum(1 for d in data if d.get("is_indexable"))
        errors    = sum(1 for d in data if str(d.get("status_code", ""))[:1] in ("4", "5"))
        st.metric("Total URLs", total)
        st.metric("Indexable",  indexable)
        st.metric("4xx/5xx",    errors)
    else:
        sel_status = []
        sel_index  = "All"
        sel_error  = "— show all —"


# ─── run spider when button clicked ──────────────────────────────────────────
if analyze_btn and url_count > 0:
    tmp_urls = tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    )
    tmp_urls.write("\n".join(urls_preview))
    tmp_urls.close()

    tmp_out = tempfile.NamedTemporaryFile(
        suffix=".json", delete=False
    )
    tmp_out.close()
    output_path = tmp_out.name

    st.markdown(
        f'<div class="run-info">Analysing <b>{url_count}</b> URL(s) — '
        f'this may take a while depending on page count and network speed.</div>',
        unsafe_allow_html=True,
    )

    with st.spinner("Spider running…"):
        success, log_text = run_spider(tmp_urls.name, output_path)

    st.session_state.last_run_log = log_text

    if success and os.path.exists(output_path) and os.path.getsize(output_path) > 2:
        with open(output_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        st.session_state.data = result if isinstance(result, list) else [result]
        with open(output_path, "rb") as f:
            st.session_state.output_json_bytes = f.read()
        st.session_state.analysis_done = True
        st.success(f"Done! {len(st.session_state.data)} page(s) analysed.")
        st.rerun()
    else:
        st.error("Spider did not produce output. Check the log below.")
        st.markdown(
            f'<div class="log-box">{log_text[-3000:]}</div>',
            unsafe_allow_html=True,
        )

    # clean up temp files
    try:
        os.unlink(tmp_urls.name)
        os.unlink(output_path)
    except Exception:
        pass


# ─── main area ────────────────────────────────────────────────────────────────
st.markdown("# SEO Site Audit")

data = st.session_state.data

if not data:
    st.info(
        "Enter a sitemap number in the sidebar and click **Fetch Sitemap**, "
        "then click **Analyze** to run the SEO spider."
    )
    st.markdown("""
**What you get for each URL:**
- HTTP status, response time, page size
- Title, meta description, H1–H6 headings, word count
- Canonicals, robots directives, indexability
- Open Graph & Twitter Card tags
- Structured data / Schema.org types
- Image audit (alt text, lazy load, WebP)
- Internal / external / nofollow link counts
- Technical signals: HTTPS, AMP, favicon, hreflang, viewport
- Real-estate signals: price, map, listing count
""")
    st.stop()

# ─── apply filters ────────────────────────────────────────────────────────────
filtered = data
if sel_status:
    filtered = [d for d in filtered if str(d.get("status_code", "")) in sel_status]
if sel_index == "Yes":
    filtered = [d for d in filtered if d.get("is_indexable")]
elif sel_index == "No":
    filtered = [d for d in filtered if not d.get("is_indexable")]
if sel_error != "— show all —":
    fn = error_filters[sel_error]
    filtered = [d for d in filtered if fn(d)]

# ─── summary cards ────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5, c6, c7 = st.columns(7)

total_f       = len(filtered)
ok_2xx        = sum(1 for d in filtered if str(d.get("status_code", "")).startswith("2"))
idx           = sum(1 for d in filtered if d.get("is_indexable"))
missing_title = sum(1 for d in filtered if not d.get("title"))
missing_desc  = sum(1 for d in filtered if not d.get("meta_description"))
missing_h1    = sum(1 for d in filtered if not d.get("has_h1"))
no_schema     = sum(1 for d in filtered if d.get("schema_json_ld") != "YES")

mcard(c1, "Total URLs",       total_f,       "")
mcard(c2, "2xx OK",           ok_2xx,        "green")
mcard(c3, "Indexable",        idx,           "green")
mcard(c4, "Missing Title",    missing_title, "red" if missing_title else "green")
mcard(c5, "Missing Meta",     missing_desc,  "red" if missing_desc  else "green")
mcard(c6, "Missing H1",       missing_h1,    "red" if missing_h1    else "green")
mcard(c7, "No Schema",        no_schema,     "red" if no_schema     else "green")

st.markdown("<br>", unsafe_allow_html=True)

# ─── download JSON ────────────────────────────────────────────────────────────
if st.session_state.output_json_bytes:
    st.download_button(
        label="Download JSON Report",
        data=st.session_state.output_json_bytes,
        file_name="seo_report.json",
        mime="application/json",
    )

st.markdown("---")

# ─── tabs ─────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["All Pages", "Page Inspector", "Last Run Log"])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — overview table
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    cols_map = {
        "URL":           lambda d: d.get("url", ""),
        "Status":        lambda d: d.get("status_code", ""),
        "Indexable":     lambda d: "Yes" if d.get("is_indexable") else "No",
        "Title":         lambda d: d.get("title", ""),
        "Title Len":     lambda d: d.get("title_length", 0),
        "Desc Len":      lambda d: d.get("meta_description_length", 0),
        "H1":            lambda d: d.get("h1", ""),
        "Words":         lambda d: d.get("word_count", 0),
        "Resp (ms)":     lambda d: d.get("response_time_ms", 0),
        "Size (KB)":     lambda d: d.get("page_size_kb", 0),
        "Int Links":     lambda d: d.get("internal_links", 0),
        "Ext Links":     lambda d: d.get("external_links", 0),
        "Images":        lambda d: d.get("total_images", 0),
        "No-Alt Imgs":   lambda d: d.get("images_without_alt", 0),
        "Schema":        lambda d: d.get("schema_json_ld", ""),
        "Canonical":     lambda d: d.get("canonical_url", ""),
        "HTTPS":         lambda d: "Yes" if d.get("url_has_https") else "No",
        "URL Depth":     lambda d: d.get("url_depth", 0),
    }

    rows_list = [{k: fn(d) for k, fn in cols_map.items()} for d in filtered]
    df = pd.DataFrame(rows_list)

    st.dataframe(
        df,
        use_container_width=True,
        height=450,
        column_config={
            "URL":       st.column_config.TextColumn(width="large"),
            "Title Len": st.column_config.NumberColumn(format="%d"),
            "Desc Len":  st.column_config.NumberColumn(format="%d"),
            "Words":     st.column_config.NumberColumn(format="%d"),
            "Resp (ms)": st.column_config.NumberColumn(format="%.0f ms"),
            "Size (KB)": st.column_config.NumberColumn(format="%.1f KB"),
        },
    )

    col_csv, col_json2 = st.columns([1, 1])
    col_csv.download_button(
        "Download CSV",
        df.to_csv(index=False).encode("utf-8"),
        file_name="seo_report.csv",
        mime="text/csv",
    )
    if st.session_state.output_json_bytes:
        col_json2.download_button(
            "Download JSON",
            data=st.session_state.output_json_bytes,
            file_name="seo_report.json",
            mime="application/json",
        )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — page inspector
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    urls_list = [d.get("url", "") for d in filtered]
    if not urls_list:
        st.info("No URLs match the current filters.")
        st.stop()

    selected_url = st.selectbox("Select a URL to inspect", urls_list)
    page = next((d for d in filtered if d.get("url") == selected_url), None)

    if not page:
        st.warning("Page data not found.")
        st.stop()

    st.markdown(f'<div class="url-chip">{selected_url}</div>', unsafe_allow_html=True)

    left, right = st.columns([3, 1])

    # ── right: quick signals panel ──────────────────────────────────────────
    with right:
        st.markdown('<div class="section-title">Quick Signals</div>', unsafe_allow_html=True)
        signals = {
            "Indexable":          page.get("is_indexable"),
            "Has H1":             page.get("has_h1"),
            "HTTPS":              page.get("url_has_https"),
            "OG Tags":            page.get("og_present"),
            "Schema":             page.get("schema_json_ld") == "YES",
            "Self Canonical":     page.get("has_self_canonical"),
            "Has Favicon":        page.get("has_favicon"),
            "FAQ Schema":         page.get("has_faq_schema"),
            "Breadcrumb Schema":  page.get("has_breadcrumb_schema"),
            "Has AMP":            page.get("has_amp"),
            "Has Video":          page.get("has_video"),
            "Has Price":          page.get("has_price"),
            "Has Map":            page.get("has_map"),
        }
        for label, val in signals.items():
            sa, sb = st.columns([2, 1])
            sa.markdown(
                f'<span style="color:#8b949e;font-size:13px">{label}</span>',
                unsafe_allow_html=True,
            )
            sb.markdown(bool_badge(val), unsafe_allow_html=True)

    # ── left: detail expanders ───────────────────────────────────────────────
    with left:

        # 1. Page Overview
        with st.expander("Page Overview", expanded=True):
            html = ""
            html += row("Status Code",   status_badge(page.get("status_code", "")))
            html += row("Final URL",     plain(page.get("final_url", "")))
            rt = page.get("response_time_ms", 0)
            html += row("Response Time", badge(f"{rt} ms", "green" if rt < 2000 else "yellow"))
            sz = page.get("page_size_kb", 0)
            html += row("Page Size",     badge(f"{sz} KB", "green" if sz < 500 else "yellow"))
            ul = page.get("url_length", 0)
            html += row("URL Length",    badge(f"{ul} chars", "green" if ul < 100 else "yellow"))
            html += row("URL Depth",     plain(page.get("url_depth", "")))
            chain = page.get("redirect_chain", [])
            html += row("Redirect Chain", badge(f"{len(chain)} redirect(s)", "yellow" if chain else "green"))
            html += row("Content Type",  plain(page.get("content_type", "")))
            st.markdown(html, unsafe_allow_html=True)

        # 2. Title & Meta
        with st.expander("Title & Meta Tags"):
            html = ""
            html += row("Title",              plain(page.get("title", "")))
            html += row("Title Length",       length_badge(page.get("title_length", 0), 30, 60))
            html += row("Meta Description",   plain(page.get("meta_description", "")))
            html += row("Desc Length",        length_badge(page.get("meta_description_length", 0), 120, 160))
            html += row("Meta Keywords",      plain(page.get("meta_keywords", "")))
            html += row("Meta Robots",        plain(page.get("meta_robots", "")))
            html += row("X-Robots-Tag",       plain(page.get("x_robots_tag", "")))
            html += row("Canonical URL",      plain(page.get("canonical_url", "")))
            html += row("Has Self Canonical", bool_badge(page.get("has_self_canonical")))
            html += row("Noindex",            bool_badge(not page.get("is_indexable")))
            html += row("Nosnippet",          bool_badge(page.get("has_nosnippet")))
            html += row("Noarchive",          bool_badge(page.get("has_noarchive")))
            st.markdown(html, unsafe_allow_html=True)

        # 3. Headings & Content
        with st.expander("Headings & Content"):
            html = ""
            html += row("H1 Text",       plain(page.get("h1", "")))
            hc = page.get("h1_count", 0)
            html += row("H1 Count",      badge(hc, "green" if hc == 1 else "red"))
            html += row("H2 Count",      plain(page.get("h2_count", 0)))
            html += row("H3 Count",      plain(page.get("h3_count", 0)))
            html += row("H4 Count",      plain(page.get("h4_count", 0)))
            html += row("H5 Count",      plain(page.get("h5_count", 0)))
            html += row("H6 Count",      plain(page.get("h6_count", 0)))
            wc = page.get("word_count", 0)
            html += row("Word Count",    badge(wc, "green" if wc >= 300 else "yellow"))
            html += row("Paragraphs",    plain(page.get("number_of_paragraphs", 0)))
            html += row("UL Lists",      plain(page.get("ul_count", 0)))
            html += row("OL Lists",      plain(page.get("ol_count", 0)))
            html += row("Tables",        plain(page.get("table_count", 0)))
            html += row("Has FAQ Section", bool_badge(page.get("has_faq_section")))
            st.markdown(html, unsafe_allow_html=True)

            h2_texts = page.get("h2_texts", [])
            if h2_texts:
                st.markdown(
                    '<div class="section-title" style="margin-top:12px">H2 Headings</div>',
                    unsafe_allow_html=True,
                )
                for i, h in enumerate(h2_texts, 1):
                    st.markdown(
                        f'<div style="padding:6px 0;border-bottom:1px solid #21262d;font-size:13px;color:#c9d1d9">'
                        f'<span style="color:#58a6ff;margin-right:8px">{i}.</span>{h}</div>',
                        unsafe_allow_html=True,
                    )

        # 4. Links
        with st.expander("Links"):
            html = ""
            html += row("Total Links",    plain(page.get("total_links", 0)))
            html += row("Internal Links", badge(page.get("internal_links", 0), "green"))
            html += row("External Links", plain(page.get("external_links", 0)))
            html += row("Nofollow Links", plain(page.get("nofollow_links", 0)))
            html += row("Rel Next",       plain(page.get("rel_next", "")))
            html += row("Rel Prev",       plain(page.get("rel_prev", "")))
            st.markdown(html, unsafe_allow_html=True)

        # 5. Images
        with st.expander("Images"):
            na = page.get("images_without_alt", 0)
            html = ""
            html += row("Total Images",        plain(page.get("total_images", 0)))
            html += row("Images Without Alt",  badge(na, "red" if na else "green"))
            html += row("Lazy Load Images",    plain(page.get("images_with_lazy_load", 0)))
            html += row("Images with W & H",   plain(page.get("images_with_width_height", 0)))
            html += row("WebP Images",         plain(page.get("webp_images", 0)))
            st.markdown(html, unsafe_allow_html=True)

        # 6. Technical SEO
        with st.expander("Technical SEO"):
            html = ""
            html += row("HTTPS",        bool_badge(page.get("url_has_https")))
            html += row("Viewport",     plain(page.get("viewport", "")))
            html += row("HTML Lang",    plain(page.get("html_lang", "")))
            hl = page.get("hreflang", [])
            html += row("Hreflang",     plain(", ".join(hl) if hl else "—"))
            html += row("Has AMP",      bool_badge(page.get("has_amp")))
            html += row("AMP URL",      plain(page.get("amp_url", "")))
            html += row("Has Favicon",  bool_badge(page.get("has_favicon")))
            html += row("Has Video",    bool_badge(page.get("has_video")))
            html += row("Last Modified", plain(page.get("last_modified", "")))
            html += row("Server",       plain(page.get("server", "")))
            html += row("Cache Control", plain(page.get("cache_control", "")))
            st.markdown(html, unsafe_allow_html=True)

        # 7. Open Graph & Social
        with st.expander("Open Graph & Social"):
            html = ""
            html += row("OG Present",          bool_badge(page.get("og_present")))
            html += row("OG Title",            plain(page.get("og_title", "")))
            html += row("OG Description",      plain(page.get("og_description", "")))
            html += row("OG Image",            plain(page.get("og_image", "")))
            html += row("OG URL",              plain(page.get("og_url", "")))
            html += row("OG Type",             plain(page.get("og_type", "")))
            html += row("OG Site Name",        plain(page.get("og_site_name", "")))
            html += row("Twitter Card",        plain(page.get("twitter_card", "")))
            html += row("Twitter Title",       plain(page.get("twitter_title", "")))
            html += row("Twitter Description", plain(page.get("twitter_description", "")))
            html += row("Twitter Image",       plain(page.get("twitter_image", "")))
            st.markdown(html, unsafe_allow_html=True)

        # 8. Schema / Structured Data
        with st.expander("Schema & Structured Data"):
            html = ""
            html += row("Schema JSON-LD",    bool_badge(page.get("schema_json_ld") == "YES"))
            html += row("Schema Count",      plain(page.get("schema_count", 0)))
            types = page.get("schema_types", [])
            types_html = " ".join(badge(t, "blue") for t in types) if types else badge("None", "gray")
            html += row("Schema Types",      types_html)
            html += row("FAQ Schema",        bool_badge(page.get("has_faq_schema")))
            html += row("Breadcrumb Schema", bool_badge(page.get("has_breadcrumb_schema")))
            html += row("Real Estate Schema",bool_badge(page.get("has_real_estate_schema")))
            st.markdown(html, unsafe_allow_html=True)

        # 9. Real Estate Signals
        with st.expander("Real Estate Signals"):
            html = ""
            html += row("Has Price",     bool_badge(page.get("has_price")))
            html += row("Has Map",       bool_badge(page.get("has_map")))
            lc = page.get("listing_count", 0)
            html += row("Listing Count", badge(lc, "green" if lc > 0 else "gray"))
            st.markdown(html, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — last run log
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    log = st.session_state.last_run_log
    if log:
        st.markdown(
            f'<div class="log-box" style="max-height:500px">{log}</div>',
            unsafe_allow_html=True,
        )
        st.download_button(
            "Download Log",
            data=log.encode("utf-8"),
            file_name="spider_log.txt",
            mime="text/plain",
        )
    else:
        st.info("No spider run yet. Upload a URL file and click Analyze.")
