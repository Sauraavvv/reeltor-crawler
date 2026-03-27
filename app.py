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

st.set_page_config(
    page_title="SEO Site Auditor",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
    [data-testid="stSidebarCollapseButton"] { display: none !important; }

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

for key, default in [
    ("data", []),
    ("output_json_bytes", None),
    ("last_run_log", ""),
    ("analysis_done", False),
]:
    if key not in st.session_state:
        st.session_state[key] = default

def badge(val, kind="gray"):
    return f'<span class="badge badge-{kind}">{val}</span>'

def bool_badge(val):
    if val is True or val == "YES":
        return badge("Yes")
    if val is False or val == "NO":
        return badge("No")
    return badge(str(val))

def row(key, val_html):
    return (f'<div class="seo-row">'
            f'<span class="seo-key">{key}</span>'
            f'<span class="seo-val">{val_html}</span>'
            f'</div>')

def plain(val):
    if val is None or val == "":
        return badge("—")
    return f'<span>{val}</span>'

def status_badge(code):
    try:
        c = int(code)
        if 200 <= c < 300:
            return badge(c)
        if 300 <= c < 400:
            return badge(c)
        return badge(c)
    except Exception:
        return badge(str(code))

def length_badge(length, good_min, good_max):
    try:
        l = int(length)
        if good_min <= l <= good_max:
            return badge(f"{l} chars")
        return badge(f"{l} chars")
    except Exception:
        return badge(str(length))

def mcard(col, label, value, color=""):
    col.markdown(
        f'<div class="metric-card">'
        f'<div class="label">{label}</div>'
        f'<div class="value {color}">{value}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

PROJECT_DIR        = os.path.dirname(os.path.abspath(__file__))
SPIDER_PATH        = os.path.join(PROJECT_DIR, "reeltor_seo_from_txt.py")
SITEMAP_INDEX_URL  = "https://www.reeltor.com/sitemap-index.xml"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SEOAuditor/1.0)"}

def fetch_sitemap_index() -> tuple[list[str], str]:
    """Fetch all sitemap locs from sitemap-index.xml."""
    try:
        resp = requests.get(SITEMAP_INDEX_URL, timeout=15, headers=HEADERS)
        if resp.status_code != 200:
            return [], f"HTTP {resp.status_code} fetching sitemap index"
        root = ET.fromstring(resp.content)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        locs = [loc.text.strip() for loc in root.findall(".//sm:loc", ns) if loc.text]
        return locs, ""
    except ET.ParseError:
        return [], "Sitemap index could not be parsed as XML."
    except Exception as exc:
        return [], str(exc)

def fetch_urls_from_sitemap(sitemap_url: str) -> tuple[list[str], str]:
    """Fetch page URLs from a single sitemap XML. Returns (urls, error_message)."""
    try:
        resp = requests.get(sitemap_url, timeout=15, headers=HEADERS)
        if resp.status_code == 404:
            return [], f"404 — {sitemap_url}"
        if resp.status_code != 200:
            return [], f"HTTP {resp.status_code} fetching {sitemap_url}"
        root = ET.fromstring(resp.content)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        urls = [loc.text.strip() for loc in root.findall(".//sm:loc", ns) if loc.text]
        if not urls:
            return [], f"No <loc> URLs in {sitemap_url}"
        return urls, ""
    except ET.ParseError:
        return [], f"Could not parse XML from {sitemap_url}"
    except Exception as exc:
        return [], str(exc)

def run_spider(urls_file: str, output_file: str, total_urls: int = 0) -> tuple[bool, str]:
    cmd = [
        sys.executable, "-m", "scrapy", "runspider",
        SPIDER_PATH,
        "-a", f"urls_file={urls_file}",
        "-O", output_file,
        "--logfile", "-",
    ]
    log_lines: list[str] = []
    log_lock = threading.Lock()

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=PROJECT_DIR,
        )

        prog_placeholder = st.empty()
        log_placeholder  = st.empty()
        done_count = 0

        for line in iter(process.stdout.readline, ""):
            line = line.rstrip()
            with log_lock:
                log_lines.append(line)
                if "Crawled (" in line:
                    done_count += 1
                visible = "\n".join(log_lines[-12:])

            if total_urls > 0:
                pct       = min(done_count / total_urls, 1.0)
                filled    = int(pct * 30)
                bar_html  = (
                    f'<div style="background:#21262d;border-radius:6px;height:10px;'
                    f'overflow:hidden;margin:6px 0 4px 0">'
                    f'<div style="background:#1f6feb;width:{int(pct*100)}%;height:100%;'
                    f'border-radius:6px;transition:width 0.3s"></div></div>'
                )
                prog_placeholder.markdown(
                    f'<div style="font-size:12px;color:#8b949e">'
                    f'Crawled <b style="color:#e6edf3">{done_count}</b> / '
                    f'<b style="color:#e6edf3">{total_urls}</b> URLs '
                    f'<b style="color:#58a6ff">({int(pct*100)}%)</b>'
                    f'</div>{bar_html}',
                    unsafe_allow_html=True,
                )

            log_placeholder.markdown(
                f'<div class="log-box">{visible}</div>',
                unsafe_allow_html=True,
            )

        process.wait()
        prog_placeholder.empty()
        log_placeholder.empty()
        return process.returncode == 0, "\n".join(log_lines)

    except Exception as exc:
        return False, str(exc)

for key, default in [
    ("sitemap_index", []),
    ("sitemap_urls", []),
    ("input_mode", "Sitemap"),
]:
    if key not in st.session_state:
        st.session_state[key] = default

with st.sidebar:
    st.markdown("## SEO Auditor")
    st.markdown("---")

    input_mode = st.radio(
        "Input mode",
        ["Sitemap", "Single URL"],
        horizontal=True,
        label_visibility="collapsed",
    )

    url_count = 0
    urls_preview: list[str] = []

    if input_mode == "Sitemap":
        st.markdown("**Step 1 — Load Sitemaps**")

        fetch_index_btn = st.button("Fetch Available Sitemaps", use_container_width=True)
        if fetch_index_btn:
            with st.spinner("Fetching sitemap index…"):
                index_locs, err = fetch_sitemap_index()
            if err:
                st.error(err)
                st.session_state["sitemap_index"] = []
            else:
                st.session_state["sitemap_index"] = index_locs

        sitemap_index = st.session_state.get("sitemap_index", [])

        if sitemap_index:
            import re
            from collections import defaultdict

            grouped: dict[str, list[tuple]] = defaultdict(list)
            for u in sitemap_index:
                m_cat = re.search(r"/sitemap/([^/]+)/(\d+)\.xml", u)
                m_num = re.search(r"/sitemap/(\d+)\.xml", u)
                if m_cat:
                    grouped[m_cat.group(1)].append((int(m_cat.group(2)), u))
                elif m_num:
                    grouped["main"].append((int(m_num.group(1)), u))
                else:
                    grouped["__standalone__"].append((None, u))

            for cat in grouped:
                grouped[cat].sort(key=lambda x: (x[0] is None, x[0]))

            cat_ranges: dict[str, tuple[int, int]] = {}
            cat_enabled: dict[str, bool] = {}

            numbered_cats = [c for c in grouped if c != "__standalone__"]
            if numbered_cats:
                st.markdown("**Select sitemap categories & range**")
                for cat in sorted(numbered_cats):
                    nums   = [n for n, _ in grouped[cat]]
                    min_n, max_n = min(nums), max(nums)
                    label  = "Main pages" if cat == "main" else cat.capitalize()
                    enabled = st.checkbox(
                        f"{label}  ({min_n}–{max_n})",
                        value=False,
                        key=f"cb_{cat}",
                    )
                    cat_enabled[cat] = enabled
                    if enabled and min_n < max_n:
                        rng = st.slider(
                            f"Range — {label}",
                            min_value=min_n,
                            max_value=max_n,
                            value=(min_n, max_n),
                            step=1,
                            label_visibility="collapsed",
                            key=f"rng_{cat}",
                        )
                        cat_ranges[cat] = rng
                    elif enabled:
                        cat_ranges[cat] = (min_n, max_n)

            fetch_btn = st.button("Fetch Selected Sitemaps", use_container_width=True)
            if fetch_btn:
                selected_urls: list[str] = []
                errors_list: list[str] = []

                for cat, (lo, hi) in cat_ranges.items():
                    for num, su in grouped[cat]:
                        if lo <= num <= hi:
                            u, e = fetch_urls_from_sitemap(su)
                            selected_urls.extend(u)
                            if e:
                                errors_list.append(e)

                if errors_list:
                    st.warning("\n".join(errors_list))
                if selected_urls:
                    st.session_state["sitemap_urls"] = selected_urls
                else:
                    st.error("No URLs fetched. Select at least one sitemap above.")

        if st.session_state.get("sitemap_urls"):
            all_urls = st.session_state["sitemap_urls"]
            total_available = len(all_urls)
            st.success(f"{total_available} URL{'s' if total_available != 1 else ''} loaded")

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

    else:
        st.markdown("**Paste a URL to analyse**")
        single_url = st.text_input(
            "URL",
            placeholder="https://www.reeltor.com/...",
            label_visibility="collapsed",
        ).strip()
        if single_url:
            if not single_url.startswith("http"):
                st.error("URL must start with http:// or https://")
            else:
                urls_preview = [single_url]
                url_count = 1
                st.success("1 URL ready")

    st.markdown("---")
    st.markdown("**Step 2 — Run Analysis**")

    analyze_btn = st.button(
        f"Analyze {url_count} URL{'s' if url_count != 1 else ''}",
        type="primary",
        disabled=(url_count == 0),
    )

    data = st.session_state.data
    if data:
        st.markdown("---")
        st.markdown("**Filters**")

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

    else:
        sel_status = []
        sel_index  = "All"
        sel_error  = "— show all —"

if analyze_btn and url_count > 0:
    tmp_urls = tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    )
    tmp_urls.write("\n".join(urls_preview))
    tmp_urls.close()

    tmp_out = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    tmp_out.close()
    output_path = tmp_out.name

    st.markdown(
        f'<div class="run-info">Analysing <b>{url_count}</b> URL(s) — '
        f'this may take a while depending on page count and network speed.</div>',
        unsafe_allow_html=True,
    )

    success, log_text = run_spider(tmp_urls.name, output_path, total_urls=url_count)

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

    try:
        os.unlink(tmp_urls.name)
        os.unlink(output_path)
    except Exception:
        pass

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

c1, c2, c3, c4, c5, c6, c7 = st.columns(7)

total_f       = len(filtered)
ok_2xx        = sum(1 for d in filtered if str(d.get("status_code", "")).startswith("2"))
idx           = sum(1 for d in filtered if d.get("is_indexable"))
missing_title = sum(1 for d in filtered if not d.get("title"))
missing_desc  = sum(1 for d in filtered if not d.get("meta_description"))
missing_h1    = sum(1 for d in filtered if not d.get("has_h1"))
cache_hits    = sum(
    1 for d in filtered
    if str(d.get("x_vercel_cache", "")).upper() == "HIT"
    or str(d.get("cf_cache_status", "")).upper() == "HIT"
)

mcard(c1, "Total URLs",    total_f,       "")
mcard(c2, "2xx OK",        ok_2xx)
mcard(c3, "Indexable",     idx)
mcard(c4, "Missing Title", missing_title, "red" if missing_title else "green")
mcard(c5, "Missing Meta",  missing_desc,  "red" if missing_desc  else "green")
mcard(c6, "Missing H1",    missing_h1,    "red" if missing_h1    else "green")
mcard(c7, "Cache HITs",    cache_hits,    "green" if cache_hits else "yellow")

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("---")

tab1, tab2, tab5, tab4, tab3 = st.tabs(["All Pages", "Page Inspector", "URL Inspector", "Analytics Dashboard", "Last Run Log"])

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

    with left:

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

        with st.expander("Links"):
            html = ""
            html += row("Total Links",    plain(page.get("total_links", 0)))
            html += row("Internal Links", badge(page.get("internal_links", 0)))
            html += row("External Links", plain(page.get("external_links", 0)))
            html += row("Other Links",    plain(len(page.get("other_links_list", []))))
            html += row("Nofollow Links", plain(page.get("nofollow_links", 0)))
            html += row("Rel Next",       plain(page.get("rel_next", "")))
            html += row("Rel Prev",       plain(page.get("rel_prev", "")))
            st.markdown(html, unsafe_allow_html=True)

            int_links  = page.get("internal_links_list", [])
            ext_links  = page.get("external_links_list", [])
            oth_links  = page.get("other_links_list", [])

            link_tab_i, link_tab_e, link_tab_o = st.tabs([
                f"Internal ({len(int_links)})",
                f"External ({len(ext_links)})",
                f"Other ({len(oth_links)})",
            ])

            def _render_links(tab, links, color):
                with tab:
                    if not links:
                        st.caption("None found.")
                    else:
                        items_html = "".join(
                            f'<div style="padding:5px 0;border-bottom:1px solid #21262d;'
                            f'font-size:12px;color:{color};word-break:break-all">{l}</div>'
                            for l in links
                        )
                        st.markdown(
                            f'<div style="max-height:250px;overflow-y:auto">{items_html}</div>',
                            unsafe_allow_html=True,
                        )

            _render_links(link_tab_i, int_links, "#3fb950")
            _render_links(link_tab_e, ext_links, "#58a6ff")
            _render_links(link_tab_o, oth_links, "#8b949e")

        with st.expander("Images"):
            na = page.get("images_without_alt", 0)
            html = ""
            html += row("Total Images",        plain(page.get("total_images", 0)))
            html += row("Images Without Alt",  badge(na, "red" if na else "green"))
            html += row("Lazy Load Images",    plain(page.get("images_with_lazy_load", 0)))
            html += row("Images with W & H",   plain(page.get("images_with_width_height", 0)))
            html += row("WebP Images",         plain(page.get("webp_images", 0)))
            st.markdown(html, unsafe_allow_html=True)

            img_urls      = page.get("image_urls", [])
            lazy_urls     = page.get("lazy_image_urls", [])
            webp_urls     = page.get("webp_image_urls", [])
            wh_urls       = page.get("wh_image_urls", [])

            if img_urls:
                def _img_grid(tab, urls):
                    with tab:
                        if not urls:
                            st.caption("None found.")
                            return
                        cols_per_row = 3
                        for i in range(0, len(urls), cols_per_row):
                            chunk = urls[i:i + cols_per_row]
                            cols = st.columns(cols_per_row)
                            for col, url in zip(cols, chunk):
                                try:
                                    col.image(url, use_container_width=True)
                                except Exception:
                                    col.markdown(
                                        f'<div style="font-size:11px;color:#f85149;'
                                        f'word-break:break-all">Could not load:<br>{url}</div>',
                                        unsafe_allow_html=True,
                                    )

                t_all, t_lazy, t_webp, t_wh = st.tabs([
                    f"All ({len(img_urls)})",
                    f"Lazy ({len(lazy_urls)})",
                    f"WebP ({len(webp_urls)})",
                    f"W & H ({len(wh_urls)})",
                ])
                _img_grid(t_all,  img_urls)
                _img_grid(t_lazy, lazy_urls)
                _img_grid(t_webp, webp_urls)
                _img_grid(t_wh,   wh_urls)

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
            st.markdown(html, unsafe_allow_html=True)

        with st.expander("Cache"):
            import re as _re

            def _cache_hit_badge(val):
                v = str(val).upper()
                if v == "HIT":    return badge("HIT")
                if v == "MISS":   return badge("MISS")
                if v == "BYPASS": return badge("BYPASS")
                if v == "STALE":  return badge("STALE")
                if v == "REVALIDATED": return badge("REVALIDATED")
                return badge(val or "—")

            cc = page.get("cache_control", "")
            max_age_days = None
            ma_match = _re.search(r"max-age=(\d+)", cc)
            if ma_match:
                secs = int(ma_match.group(1))
                max_age_days = round(secs / 86400, 2)

            age_raw = page.get("age_seconds", "")
            age_display = ""
            if age_raw:
                try:
                    age_display = f"{int(age_raw)}s (~{round(int(age_raw)/3600, 1)}h)"
                except ValueError:
                    age_display = age_raw

            html = ""
            html += row("Cache-Control",      plain(cc))
            html += row("max-age",            badge(f"{max_age_days} days") if max_age_days is not None else badge("—"))
            html += row("Age (time in cache)", plain(age_display))
            html += row("X-Vercel-Cache",     _cache_hit_badge(page.get("x_vercel_cache", "")))
            html += row("CF-Cache-Status",    _cache_hit_badge(page.get("cf_cache_status", "")))
            html += row("CDN-Cache-Control",  plain(page.get("cdn_cache_control", "")))
            sk_raw = page.get("surrogate_key", "")
            if sk_raw:
                sk_items = sk_raw.split()
                sk_html = "".join(
                    f'<div style="padding:3px 0;font-size:12px;color:#8b949e">'
                    f'<span style="color:#58a6ff;margin-right:6px">v{i}.</span>{tag}</div>'
                    for i, tag in enumerate(sk_items, 1)
                )
                sk_val = f'<div style="text-align:left">{sk_html}</div>'
            else:
                sk_val = badge("—")
            html += row("Surrogate-Key", sk_val)
            html += row("Pragma",             plain(page.get("pragma", "")))
            st.markdown(html, unsafe_allow_html=True)

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

        with st.expander("Schema & Structured Data"):
            html = ""
            html += row("Schema JSON-LD",    bool_badge(page.get("schema_json_ld") == "YES"))
            html += row("Schema Count",      plain(page.get("schema_count", 0)))
            types = page.get("schema_types", [])
            types_html = " ".join(badge(t) for t in types) if types else badge("None")
            html += row("Schema Types",      types_html)
            html += row("FAQ Schema",        bool_badge(page.get("has_faq_schema")))
            html += row("Breadcrumb Schema", bool_badge(page.get("has_breadcrumb_schema")))
            html += row("Real Estate Schema",bool_badge(page.get("has_real_estate_schema")))
            st.markdown(html, unsafe_allow_html=True)

        with st.expander("Real Estate Signals"):
            html = ""
            html += row("Has Price",     bool_badge(page.get("has_price")))
            html += row("Has Map",       bool_badge(page.get("has_map")))
            lc = page.get("listing_count", 0)
            html += row("Listing Count", badge(lc, "green" if lc > 0 else "gray"))
            st.markdown(html, unsafe_allow_html=True)

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

with tab4:
    try:
        import plotly.graph_objects as go
    except ImportError:
        st.error("Plotly is required for the Analytics Dashboard. Run: pip install plotly")
        st.stop()

    if not filtered:
        st.info("No data to analyse. Run the spider first.")
        st.stop()

    N = len(filtered)

    CHART_BG   = "#0d1117"
    PAPER_BG   = "#161b22"
    FONT_COLOR = "#e6edf3"
    GRID_COLOR = "#21262d"

    def _layout(fig, title="", height=320):
        fig.update_layout(
            title=dict(text=title, font=dict(color=FONT_COLOR, size=13), x=0),
            paper_bgcolor=PAPER_BG,
            plot_bgcolor=CHART_BG,
            font=dict(color=FONT_COLOR, size=11),
            margin=dict(l=12, r=12, t=36 if title else 12, b=12),
            height=height,
            legend=dict(bgcolor=PAPER_BG, bordercolor=GRID_COLOR, borderwidth=1),
        )
        fig.update_xaxes(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR)
        fig.update_yaxes(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR)
        return fig

    st.markdown("---")
    st.markdown('<div class="section-title">Site Health Score</div>', unsafe_allow_html=True)

    issues_weight = {
        "4xx/5xx errors":        (sum(1 for d in filtered if str(d.get("status_code",""))[:1] in ("4","5")), 20),
        "Not indexable":         (sum(1 for d in filtered if not d.get("is_indexable")),                    15),
        "Missing title":         (sum(1 for d in filtered if not d.get("title")),                           12),
        "Missing meta desc":     (sum(1 for d in filtered if not d.get("meta_description")),                10),
        "Missing H1":            (sum(1 for d in filtered if not d.get("has_h1")),                          8),
        "No self-canonical":     (sum(1 for d in filtered if not d.get("has_self_canonical")),              8),
        "No OG tags":            (sum(1 for d in filtered if not d.get("og_present")),                      7),
        "No schema":             (sum(1 for d in filtered if d.get("schema_json_ld") != "YES"),             6),
        "Images w/o alt":        (sum(1 for d in filtered if (d.get("images_without_alt") or 0) > 0),       5),
        "Slow pages (>2s)":      (sum(1 for d in filtered if (d.get("response_time_ms") or 0) > 2000),      5),
        "Title too long/short":  (sum(1 for d in filtered if not (30 <= (d.get("title_length") or 0) <= 60)), 4),
    }

    penalty = 0
    for _, (count, weight) in issues_weight.items():
        penalty += (count / N) * weight

    health_score = max(0, round(100 - penalty))
    score_color = "#3fb950" if health_score >= 80 else "#d29922" if health_score >= 50 else "#f85149"

    hs_col, breakdown_col = st.columns([1, 2])

    with hs_col:
        gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=health_score,
            domain={"x": [0, 1], "y": [0, 1]},
            number={"font": {"color": score_color, "size": 48}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": FONT_COLOR},
                "bar":  {"color": score_color},
                "bgcolor": CHART_BG,
                "steps": [
                    {"range": [0, 50],  "color": "#3a1a1a"},
                    {"range": [50, 80], "color": "#3a2e0a"},
                    {"range": [80, 100],"color": "#1a3a22"},
                ],
                "threshold": {"line": {"color": score_color, "width": 3}, "thickness": 0.75, "value": health_score},
            },
        ))
        _layout(gauge, "Health Score", height=280)
        st.plotly_chart(gauge, use_container_width=True)

    with breakdown_col:
        issue_names  = list(issues_weight.keys())
        issue_counts = [issues_weight[k][0] for k in issue_names]
        issue_pcts   = [round(c / N * 100, 1) for c in issue_counts]
        colors_bar   = ["#ef233c" if issues_weight[k][1] >= 10 else "#f8961e" if issues_weight[k][1] >= 6 else "#4cc9f0"
                        for k in issue_names]

        bar_fig = go.Figure(go.Bar(
            x=issue_counts,
            y=issue_names,
            orientation="h",
            marker_color=colors_bar,
            text=[f"{c}  ({p}%)" for c, p in zip(issue_counts, issue_pcts)],
            textposition="outside",
            textfont=dict(size=11, color=FONT_COLOR),
        ))
        _layout(bar_fig, "Issues Breakdown (count & % of URLs)", height=320)
        bar_fig.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(bar_fig, use_container_width=True)

    st.markdown("---")

    col_a, col_b = st.columns(2)

    with col_a:
        from collections import Counter
        sc_raw    = [str(d.get("status_code", "unknown")) for d in filtered]
        sc_counts = Counter(sc_raw)

        def _sc_group(code):
            if code.startswith("2"): return "2xx OK"
            if code.startswith("3"): return "3xx Redirect"
            if code.startswith("4"): return "4xx Client Error"
            if code.startswith("5"): return "5xx Server Error"
            return "Unknown"

        grouped_sc = Counter(_sc_group(c) for c in sc_raw)
        sc_colors  = {"2xx OK": "#06d6a0", "3xx Redirect": "#f9c74f",
                      "4xx Client Error": "#f8961e", "5xx Server Error": "#ef233c", "Unknown": "#4361ee"}

        pie_sc = go.Figure(go.Pie(
            labels=list(grouped_sc.keys()),
            values=list(grouped_sc.values()),
            marker_colors=[sc_colors.get(k, "#8b949e") for k in grouped_sc.keys()],
            hole=0.5,
            textinfo="label+percent",
            textfont=dict(size=11),
        ))
        _layout(pie_sc, "HTTP Status Code Distribution", height=300)
        st.plotly_chart(pie_sc, use_container_width=True)

    with col_b:
        idx_yes = sum(1 for d in filtered if d.get("is_indexable"))
        idx_no  = N - idx_yes

        pie_idx = go.Figure(go.Pie(
            labels=["Indexable", "Non-indexable"],
            values=[idx_yes, idx_no],
            marker_colors=["#06d6a0", "#ef233c"],
            hole=0.5,
            textinfo="label+value+percent",
            textfont=dict(size=11),
        ))
        _layout(pie_idx, "Indexability", height=300)
        st.plotly_chart(pie_idx, use_container_width=True)

    st.markdown("---")

    st.markdown('<div class="section-title">Performance Distribution</div>', unsafe_allow_html=True)

    col_c, col_d = st.columns(2)

    with col_c:
        rt_vals = [d.get("response_time_ms") or 0 for d in filtered]

        def _rt_bucket(ms):
            if ms < 500:   return "< 500ms"
            if ms < 1000:  return "500ms – 1s"
            if ms < 2000:  return "1s – 2s"
            return "> 2s"

        rt_buckets = Counter(_rt_bucket(v) for v in rt_vals)
        bucket_order = ["< 500ms", "500ms – 1s", "1s – 2s", "> 2s"]
        rt_colors    = ["#06d6a0", "#4cc9f0", "#f8961e", "#ef233c"]

        bar_rt = go.Figure(go.Bar(
            x=bucket_order,
            y=[rt_buckets.get(b, 0) for b in bucket_order],
            marker_color=rt_colors,
            text=[rt_buckets.get(b, 0) for b in bucket_order],
            textposition="outside",
        ))
        _layout(bar_rt, "Response Time Buckets", height=280)
        st.plotly_chart(bar_rt, use_container_width=True)

    with col_d:
        sz_vals = [d.get("page_size_kb") or 0 for d in filtered]

        def _sz_bucket(kb):
            if kb < 100:  return "< 100 KB"
            if kb < 500:  return "100 – 500 KB"
            return "> 500 KB"

        sz_buckets = Counter(_sz_bucket(v) for v in sz_vals)
        sz_order   = ["< 100 KB", "100 – 500 KB", "> 500 KB"]
        sz_colors  = ["#06d6a0", "#f8961e", "#ef233c"]

        bar_sz = go.Figure(go.Bar(
            x=sz_order,
            y=[sz_buckets.get(b, 0) for b in sz_order],
            marker_color=sz_colors,
            text=[sz_buckets.get(b, 0) for b in sz_order],
            textposition="outside",
        ))
        _layout(bar_sz, "Page Size Buckets", height=280)
        st.plotly_chart(bar_sz, use_container_width=True)

    st.markdown("---")

    st.markdown('<div class="section-title">Content Quality</div>', unsafe_allow_html=True)

    col_e, col_f = st.columns(2)

    with col_e:
        def _title_bucket(l):
            if not l or l == 0: return "Missing"
            if l < 30:          return "Too Short (<30)"
            if l <= 60:         return "Optimal (30–60)"
            return "Too Long (>60)"

        tl_buckets = Counter(_title_bucket(d.get("title_length") or 0) for d in filtered)
        tl_order   = ["Missing", "Too Short (<30)", "Optimal (30–60)", "Too Long (>60)"]
        tl_colors  = ["#ef233c", "#f8961e", "#06d6a0", "#f9c74f"]

        bar_tl = go.Figure(go.Bar(
            x=tl_order,
            y=[tl_buckets.get(b, 0) for b in tl_order],
            marker_color=tl_colors,
            text=[tl_buckets.get(b, 0) for b in tl_order],
            textposition="outside",
        ))
        _layout(bar_tl, "Title Length Distribution", height=280)
        st.plotly_chart(bar_tl, use_container_width=True)

    with col_f:
        def _desc_bucket(l):
            if not l or l == 0: return "Missing"
            if l < 120:         return "Too Short (<120)"
            if l <= 160:        return "Optimal (120–160)"
            return "Too Long (>160)"

        dl_buckets = Counter(_desc_bucket(d.get("meta_description_length") or 0) for d in filtered)
        dl_order   = ["Missing", "Too Short (<120)", "Optimal (120–160)", "Too Long (>160)"]
        dl_colors  = ["#ef233c", "#f8961e", "#06d6a0", "#f9c74f"]

        bar_dl = go.Figure(go.Bar(
            x=dl_order,
            y=[dl_buckets.get(b, 0) for b in dl_order],
            marker_color=dl_colors,
            text=[dl_buckets.get(b, 0) for b in dl_order],
            textposition="outside",
        ))
        _layout(bar_dl, "Meta Description Length Distribution", height=280)
        st.plotly_chart(bar_dl, use_container_width=True)

    wc_vals = [d.get("word_count") or 0 for d in filtered]

    def _wc_bucket(w):
        if w == 0:    return "0 words"
        if w < 100:   return "1–99"
        if w < 300:   return "100–299"
        if w < 600:   return "300–599"
        if w < 1000:  return "600–999"
        return "1000+"

    wc_buckets = Counter(_wc_bucket(v) for v in wc_vals)
    wc_order   = ["0 words", "1–99", "100–299", "300–599", "600–999", "1000+"]
    wc_colors  = ["#ef233c", "#f8961e", "#f9c74f", "#06d6a0", "#06d6a0", "#06d6a0"]

    bar_wc = go.Figure(go.Bar(
        x=wc_order,
        y=[wc_buckets.get(b, 0) for b in wc_order],
        marker_color=wc_colors,
        text=[wc_buckets.get(b, 0) for b in wc_order],
        textposition="outside",
    ))
    _layout(bar_wc, "Word Count Distribution", height=260)
    st.plotly_chart(bar_wc, use_container_width=True)

    st.markdown("---")

    st.markdown('<div class="section-title">Link Profile</div>', unsafe_allow_html=True)

    total_int  = sum(d.get("internal_links", 0) or 0 for d in filtered)
    total_ext  = sum(d.get("external_links", 0) or 0 for d in filtered)
    total_nf   = sum(d.get("nofollow_links", 0) or 0 for d in filtered)
    avg_int    = round(total_int / N, 1)
    avg_ext    = round(total_ext / N, 1)

    lm1, lm2, lm3, lm4, lm5 = st.columns(5)
    mcard(lm1, "Total Int. Links",  total_int)
    mcard(lm2, "Total Ext. Links",  total_ext,  "")
    mcard(lm3, "Total Nofollow",    total_nf)
    mcard(lm4, "Avg Int / Page",    avg_int)
    mcard(lm5, "Avg Ext / Page",    avg_ext,    "")

    st.markdown("<br>", unsafe_allow_html=True)

    from collections import defaultdict
    link_target_counts: dict = defaultdict(int)
    for d in filtered:
        for lnk in (d.get("internal_links_list") or []):
            link_target_counts[lnk] += 1

    if link_target_counts:
        top10 = sorted(link_target_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        top10_urls, top10_counts = zip(*top10)

        bar_links = go.Figure(go.Bar(
            x=top10_counts,
            y=[u[-60:] + "…" if len(u) > 60 else u for u in top10_urls],
            orientation="h",
            marker_color="#4361ee",
            text=top10_counts,
            textposition="outside",
        ))
        _layout(bar_links, "Top 10 Most Linked-to Internal Pages", height=320)
        bar_links.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(bar_links, use_container_width=True)

    st.markdown("---")

    st.markdown('<div class="section-title">Image Audit</div>', unsafe_allow_html=True)

    total_imgs   = sum(d.get("total_images", 0) or 0 for d in filtered)
    no_alt_imgs  = sum(d.get("images_without_alt", 0) or 0 for d in filtered)
    lazy_imgs    = sum(d.get("images_with_lazy_load", 0) or 0 for d in filtered)
    webp_imgs    = sum(d.get("webp_images", 0) or 0 for d in filtered)
    with_alt     = total_imgs - no_alt_imgs

    im1, im2, im3, im4, im5 = st.columns(5)
    mcard(im1, "Total Images",   total_imgs,  "")
    mcard(im2, "With Alt Text",  with_alt)
    mcard(im3, "Missing Alt",    no_alt_imgs, "red" if no_alt_imgs else "green")
    mcard(im4, "Lazy Loaded",    lazy_imgs)
    mcard(im5, "WebP Format",    webp_imgs)

    if total_imgs > 0:
        st.markdown("<br>", unsafe_allow_html=True)
        col_img1, col_img2 = st.columns(2)

        with col_img1:
            pie_alt = go.Figure(go.Pie(
                labels=["With Alt", "Missing Alt"],
                values=[with_alt, no_alt_imgs],
                marker_colors=["#06d6a0", "#ef233c"],
                hole=0.5,
                textinfo="label+value+percent",
            ))
            _layout(pie_alt, "Alt Text Coverage", height=260)
            st.plotly_chart(pie_alt, use_container_width=True)

        with col_img2:
            other_imgs = total_imgs - webp_imgs
            pie_webp = go.Figure(go.Pie(
                labels=["WebP", "Other Formats"],
                values=[webp_imgs, other_imgs],
                marker_colors=["#4361ee", "#30363d"],
                hole=0.5,
                textinfo="label+value+percent",
            ))
            _layout(pie_webp, "WebP Adoption", height=260)
            st.plotly_chart(pie_webp, use_container_width=True)

    st.markdown("---")

    st.markdown('<div class="section-title">Schema & Social Coverage</div>', unsafe_allow_html=True)

    has_schema  = sum(1 for d in filtered if d.get("schema_json_ld") == "YES")
    has_og      = sum(1 for d in filtered if d.get("og_present"))
    has_twitter = sum(1 for d in filtered if d.get("twitter_card"))
    has_faq_s   = sum(1 for d in filtered if d.get("has_faq_schema"))
    has_bread   = sum(1 for d in filtered if d.get("has_breadcrumb_schema"))

    cov_labels = ["Schema JSON-LD", "Open Graph", "Twitter Card", "FAQ Schema", "Breadcrumb Schema"]
    cov_vals   = [has_schema, has_og, has_twitter, has_faq_s, has_bread]
    cov_pcts   = [round(v / N * 100, 1) for v in cov_vals]
    cov_colors = ["#06d6a0" if p >= 80 else "#f9c74f" if p >= 40 else "#ef233c" for p in cov_pcts]

    bar_cov = go.Figure(go.Bar(
        x=cov_vals,
        y=cov_labels,
        orientation="h",
        marker_color=cov_colors,
        text=[f"{v}  ({p}%)" for v, p in zip(cov_vals, cov_pcts)],
        textposition="outside",
    ))
    _layout(bar_cov, f"Coverage out of {N} pages", height=280)
    bar_cov.update_layout(yaxis=dict(autorange="reversed"))
    st.plotly_chart(bar_cov, use_container_width=True)

    all_types: list = []
    for d in filtered:
        for t in (d.get("schema_types") or []):
            all_types.append(t)

    if all_types:
        type_counts = Counter(all_types).most_common(10)
        t_labels, t_vals = zip(*type_counts)
        bar_types = go.Figure(go.Bar(
            x=t_vals,
            y=t_labels,
            orientation="h",
            marker_color="#7209b7",
            text=t_vals,
            textposition="outside",
        ))
        _layout(bar_types, "Top Schema Types Found", height=max(240, len(t_labels) * 28))
        bar_types.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(bar_types, use_container_width=True)

    st.markdown("---")

    st.markdown('<div class="section-title">URL Structure</div>', unsafe_allow_html=True)

    col_u1, col_u2 = st.columns(2)

    with col_u1:
        depths = [d.get("url_depth") or 0 for d in filtered]

        def _depth_label(dep):
            if dep <= 1: return "Depth 1"
            if dep == 2: return "Depth 2"
            if dep == 3: return "Depth 3"
            return "Depth 4+"

        depth_counts = Counter(_depth_label(dep) for dep in depths)
        d_order = ["Depth 1", "Depth 2", "Depth 3", "Depth 4+"]

        bar_depth = go.Figure(go.Bar(
            x=d_order,
            y=[depth_counts.get(b, 0) for b in d_order],
            marker_color=["#06d6a0", "#4cc9f0", "#f8961e", "#ef233c"],
            text=[depth_counts.get(b, 0) for b in d_order],
            textposition="outside",
        ))
        _layout(bar_depth, "URL Depth Distribution", height=280)
        st.plotly_chart(bar_depth, use_container_width=True)

    with col_u2:
        https_yes = sum(1 for d in filtered if d.get("url_has_https"))
        https_no  = N - https_yes

        pie_https = go.Figure(go.Pie(
            labels=["HTTPS", "HTTP (insecure)"],
            values=[https_yes, https_no],
            marker_colors=["#06d6a0", "#ef233c"],
            hole=0.5,
            textinfo="label+value+percent",
        ))
        _layout(pie_https, "HTTPS Adoption", height=280)
        st.plotly_chart(pie_https, use_container_width=True)

    ul_vals = [d.get("url_length") or 0 for d in filtered]
    avg_ul  = round(sum(ul_vals) / N, 1) if N else 0

    uc1, uc2 = st.columns(2)
    mcard(uc1, "Avg URL Length (chars)", avg_ul, "green" if avg_ul < 100 else "yellow")
    mcard(uc2, "HTTPS Pages", https_yes)

with tab5:
    if not filtered:
        st.info("No data yet. Run the spider first.")
        st.stop()

    def _url_block(urls: list[str]) -> str:
        """Render a scrollable list of URLs."""
        items = "".join(
            f'<div style="padding:5px 0;border-bottom:1px solid #21262d;'
            f'font-size:12px;color:#58a6ff;word-break:break-all">{u}</div>'
            for u in urls
        )
        return f'<div style="max-height:260px;overflow-y:auto;padding:4px 0">{items}</div>'

    def _csv(urls: list[str]) -> bytes:
        return ("url\n" + "\n".join(urls)).encode("utf-8")

    def _section_header(title: str, total: int, icon: str = "", suffix: str = "URLs affected"):
        colour = "#f85149" if total > 0 else "#3fb950"
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:10px;'
            f'padding:10px 0 6px 0;border-bottom:2px solid #30363d;margin-bottom:12px">'
            f'<span style="font-size:16px">{icon}</span>'
            f'<span style="font-size:15px;font-weight:700;color:#e6edf3">{title}</span>'
            f'<span style="margin-left:auto;background:#21262d;color:{colour};'
            f'font-size:12px;font-weight:600;padding:2px 10px;border-radius:12px;'
            f'border:1px solid {colour}">{total} {suffix}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    def _group_expander(label: str, urls: list[str], dl_key: str):
        if not urls:
            return
        with st.expander(
            f"{label}  —  {len(urls)} URL{'s' if len(urls) != 1 else ''}",
            expanded=False,
        ):
            st.markdown(_url_block(urls), unsafe_allow_html=True)
            st.download_button(
                label=f"Download {len(urls)} URL{'s' if len(urls) != 1 else ''} as CSV",
                data=_csv(urls),
                file_name=f"{dl_key}.csv",
                mime="text/csv",
                key=f"dl_{dl_key}_{len(urls)}",
            )

    from collections import defaultdict as _dd

    _sc_errors = sum(1 for d in filtered if not str(d.get("status_code", "")).startswith("2"))
    _section_header("Status Codes", _sc_errors, "", suffix="errors")

    sc_groups: dict = _dd(list)
    for d in filtered:
        sc_groups[str(d.get("status_code", "unknown"))].append(d.get("url", ""))

    for code in sorted(sc_groups.keys()):
        urls_sc = sc_groups[code]
        c = code
        if c.startswith("2"):   icon = "🟢"
        elif c.startswith("3"): icon = "🟡"
        elif c.startswith("4"): icon = "🔴"
        elif c.startswith("5"): icon = "🔴"
        else:                   icon = "⚪"
        _group_expander(f"{icon}  HTTP {code}", urls_sc, f"status_{code}")

    st.markdown("<br>", unsafe_allow_html=True)

    cache_affected = [d for d in filtered if d.get("x_vercel_cache") or d.get("cf_cache_status")]
    _section_header("Cache Status", len(cache_affected), "")

    vc_groups: dict = _dd(list)
    for d in filtered:
        v = str(d.get("x_vercel_cache") or "").upper() or "NOT SET"
        vc_groups[v].append(d.get("url", ""))

    st.markdown('<div class="section-title" style="margin-top:8px">X-Vercel-Cache</div>', unsafe_allow_html=True)
    for status in sorted(vc_groups.keys()):
        bc = "green" if status == "HIT" else "red" if status == "MISS" else "yellow" if status in ("BYPASS","STALE") else "gray"
        _group_expander(f"Vercel — {status}", vc_groups[status], f"vercel_{status.lower()}")

    cf_groups: dict = _dd(list)
    for d in filtered:
        v = str(d.get("cf_cache_status") or "").upper() or "NOT SET"
        cf_groups[v].append(d.get("url", ""))

    st.markdown('<div class="section-title" style="margin-top:8px">CF-Cache-Status</div>', unsafe_allow_html=True)
    for status in sorted(cf_groups.keys()):
        bc = "green" if status == "HIT" else "red" if status == "MISS" else "yellow" if status in ("BYPASS","STALE") else "gray"
        _group_expander(f"Cloudflare — {status}", cf_groups[status], f"cf_{status.lower()}")

    st.markdown("<br>", unsafe_allow_html=True)

    _idx_issues = {
        "Not Indexable":          [d.get("url","") for d in filtered if not d.get("is_indexable")],
        "No Self-Canonical":      [d.get("url","") for d in filtered if not d.get("has_self_canonical")],
        "Canonical Mismatch":     [d.get("url","") for d in filtered
                                   if d.get("canonical_url") and d.get("canonical_url") != d.get("url","")],
        "Has Nosnippet":          [d.get("url","") for d in filtered if d.get("has_nosnippet")],
        "Has Noarchive":          [d.get("url","") for d in filtered if d.get("has_noarchive")],
    }
    _idx_total = sum(len(v) for v in _idx_issues.values())
    _section_header("Indexability Issues", _idx_total, "")

    for label, urls in _idx_issues.items():
        _group_expander(label, urls, f"idx_{label.lower().replace(' ','_').replace('-','_')}")

    st.markdown("<br>", unsafe_allow_html=True)

    _op_issues = {
        "Missing Title":               [d.get("url","") for d in filtered if not d.get("title")],
        "Title Too Short (<30 chars)": [d.get("url","") for d in filtered
                                        if d.get("title") and (d.get("title_length") or 0) < 30],
        "Title Too Long (>60 chars)":  [d.get("url","") for d in filtered
                                        if (d.get("title_length") or 0) > 60],
        "Missing Meta Description":    [d.get("url","") for d in filtered if not d.get("meta_description")],
        "Meta Desc Too Short (<120)":  [d.get("url","") for d in filtered
                                        if d.get("meta_description") and (d.get("meta_description_length") or 0) < 120],
        "Meta Desc Too Long (>160)":   [d.get("url","") for d in filtered
                                        if (d.get("meta_description_length") or 0) > 160],
        "Missing H1":                  [d.get("url","") for d in filtered if not d.get("has_h1")],
        "Multiple H1s":                [d.get("url","") for d in filtered if (d.get("h1_count") or 0) > 1],
    }
    _op_total = sum(len(v) for v in _op_issues.values())
    _section_header("On-Page Issues", _op_total, "")

    for label, urls in _op_issues.items():
        bc = "red" if "Missing" in label else "yellow"
        _group_expander(label, urls, f"op_{label.lower().replace(' ','_').replace('<','lt').replace('>','gt').replace('(','').replace(')','').replace('/','')}")

    st.markdown("<br>", unsafe_allow_html=True)

    _perf_issues = {
        "Slow Response (>2s)":      [d.get("url","") for d in filtered if (d.get("response_time_ms") or 0) > 2000],
        "Very Slow (>4s)":          [d.get("url","") for d in filtered if (d.get("response_time_ms") or 0) > 4000],
        "Large Page (>500 KB)":     [d.get("url","") for d in filtered if (d.get("page_size_kb") or 0) > 500],
        "Very Large Page (>1 MB)":  [d.get("url","") for d in filtered if (d.get("page_size_kb") or 0) > 1024],
    }
    _perf_total = sum(len(v) for v in _perf_issues.values())
    _section_header("Performance Issues", _perf_total, "")

    for label, urls in _perf_issues.items():
        bc = "red" if "Very" in label else "yellow"
        _group_expander(label, urls, f"perf_{label.lower().replace(' ','_').replace('>','gt').replace('(','').replace(')','').replace('/','')}")

    st.markdown("<br>", unsafe_allow_html=True)

    _content_issues = {
        "Thin Content (<100 words)":    [d.get("url","") for d in filtered if (d.get("word_count") or 0) < 100],
        "Low Content (100–299 words)":  [d.get("url","") for d in filtered
                                         if 100 <= (d.get("word_count") or 0) < 300],
        "No Paragraphs":                [d.get("url","") for d in filtered if not (d.get("number_of_paragraphs") or 0)],
        "No H2 Headings":               [d.get("url","") for d in filtered if not (d.get("h2_count") or 0)],
    }
    _section_header("Content Issues", sum(len(v) for v in _content_issues.values()), "")

    for label, urls in _content_issues.items():
        bc = "red" if "Thin" in label or "No" in label else "yellow"
        _group_expander(label, urls, f"content_{label.lower().replace(' ','_').replace('<','lt').replace('>','gt').replace('(','').replace(')','').replace('–','-').replace('/','')}")

    st.markdown("<br>", unsafe_allow_html=True)

    _img_issues = {
        "Images Missing Alt Text":  [d.get("url","") for d in filtered if (d.get("images_without_alt") or 0) > 0],
        "No WebP Images":           [d.get("url","") for d in filtered
                                     if (d.get("total_images") or 0) > 0 and not (d.get("webp_images") or 0)],
        "No Lazy-Loaded Images":    [d.get("url","") for d in filtered
                                     if (d.get("total_images") or 0) > 0 and not (d.get("images_with_lazy_load") or 0)],
    }
    _img_total = sum(len(v) for v in _img_issues.values())
    _section_header("Image Issues", _img_total, "")

    for label, urls in _img_issues.items():
        _group_expander(label, urls, f"img_{label.lower().replace(' ','_').replace('-','_')}")

    st.markdown("<br>", unsafe_allow_html=True)

    _schema_issues = {
        "No Schema at All":       [d.get("url","") for d in filtered if d.get("schema_json_ld") != "YES"],
        "No FAQ Schema":          [d.get("url","") for d in filtered if not d.get("has_faq_schema")],
        "No Breadcrumb Schema":   [d.get("url","") for d in filtered if not d.get("has_breadcrumb_schema")],
    }
    _schema_total = sum(len(v) for v in _schema_issues.values())
    _section_header("Schema Issues", _schema_total, "")

    for label, urls in _schema_issues.items():
        bc = "red" if "No Schema" in label else "yellow"
        _group_expander(label, urls, f"schema_{label.lower().replace(' ','_')}")

    schema_type_groups: dict = _dd(list)
    for d in filtered:
        for t in (d.get("schema_types") or []):
            schema_type_groups[t].append(d.get("url",""))

    if schema_type_groups:
        st.markdown('<div class="section-title" style="margin-top:8px">Pages by Schema Type</div>', unsafe_allow_html=True)
        for stype in sorted(schema_type_groups.keys()):
            _group_expander(stype, schema_type_groups[stype], f"schematype_{stype.lower().replace(' ','_')}")

    st.markdown("<br>", unsafe_allow_html=True)

    _social_issues = {
        "No Open Graph Tags":          [d.get("url","") for d in filtered if not d.get("og_present")],
        "No Twitter Card":             [d.get("url","") for d in filtered if not d.get("twitter_card")],
        "OG Present but No OG Image":  [d.get("url","") for d in filtered
                                        if d.get("og_present") and not d.get("og_image")],
        "OG Present but No OG Desc":   [d.get("url","") for d in filtered
                                        if d.get("og_present") and not d.get("og_description")],
    }
    _social_total = sum(len(v) for v in _social_issues.values())
    _section_header("Social / OG Issues", _social_total, "")

    for label, urls in _social_issues.items():
        bc = "red" if "No Open Graph" in label else "yellow"
        _group_expander(label, urls, f"social_{label.lower().replace(' ','_').replace('/','').replace('(','').replace(')','')}")

    st.markdown("<br>", unsafe_allow_html=True)

    _url_issues = {
        "HTTP (Non-HTTPS)":       [d.get("url","") for d in filtered if not d.get("url_has_https")],
        "URL Depth 4+":           [d.get("url","") for d in filtered if (d.get("url_depth") or 0) >= 4],
        "URL Too Long (>100)":    [d.get("url","") for d in filtered if (d.get("url_length") or 0) > 100],
        "Has Redirect Chain":     [d.get("url","") for d in filtered if d.get("redirect_chain")],
    }
    _url_total = sum(len(v) for v in _url_issues.values())
    _section_header("URL Structure Issues", _url_total, "")

    for label, urls in _url_issues.items():
        bc = "red" if "HTTP" in label or "Redirect" in label else "yellow"
        _group_expander(label, urls, f"url_{label.lower().replace(' ','_').replace('(','').replace(')','').replace('+','plus').replace('>','gt').replace('/','')}")

    st.markdown("<br>", unsafe_allow_html=True)
