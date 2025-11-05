
import sqlite3
from pathlib import Path
import time

import pandas as pd
import streamlit as st
from PIL import Image
import extra_streamlit_components as stx
from datetime import datetime, timedelta


# ===============================
# Paths & App Config
# ===============================
APP_TITLE = "انتخابات اتحاد الشاغلين – مدينة الملاحة الجوية"

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
IMG_DIR = BASE_DIR / "images"
DB_PATH = DATA_DIR / "data.db"
CANDIDATES_CSV = DATA_DIR / "candidates.csv"
PROGRAMS_DIR = DATA_DIR / "programs"

REACTIONS = [
    ("love", "❤️"),
    ("like", "👍"),
    ("support", "🤝"),
    ("innovative", "💡"),
]

SUPPORTED_IMG_EXTS = [".jpg", ".jpeg", ".png", ".webp"]

# ===============================
# Styling (RTL + refined theme)
# ===============================
def inject_css():
    st.markdown(
        """
        <style>
        html, body, .stApp {
            direction: rtl;
            text-align: right;
            background: linear-gradient(160deg, #f6f8ff 0%, #ffffff 40%, #f8fbff 100%) fixed;
            font-family: 'Cairo', Tahoma, Arial, sans-serif;
        }
        /* Centered page title */
        .title-badge {
            background: linear-gradient(90deg,#274690,#4ea5ff);
            color: #ffffff;
            padding: 16px 24px;
            border-radius: 14px;
            font-weight: 900;
            font-size: 1.6rem; /* bigger title */
            text-align: center;
            display: block;
            width: fit-content;
            margin: 20px auto 30px auto; /* centered */
            box-shadow: 0 8px 24px rgba(39,70,144,0.22);
            letter-spacing: .3px;
        }
        /* Cards */
        .soft-card {
            border-radius: 16px;
            padding: 16px;
            background: #ffffff;
            box-shadow: 0 10px 28px rgba(0,0,0,.06);
            border: 1px solid rgba(0,0,0,.05);
            margin-bottom: 14px;
        }
        /* Pills (labels) — higher contrast */
        .pill {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 999px;
            background: #eef4ff;
            color: #163a70;
            margin-left: 6px;
            font-size: 0.95rem;
            border: 1px solid #d6e4ff;
        }
        /* Buttons */
        .stButton > button {
            border-radius: 12px !important;
            padding: .5rem .9rem !important;
            font-weight: 700 !important;
            border: 1px solid rgba(0,0,0,.08) !important;
            box-shadow: 0 6px 14px rgba(0,0,0,.07) !important;
        }
        /* Reaction colors */
        .btn-love button { background: #ffe3ec !important; }
        .btn-like button { background: #e7f5ff !important; }
        .btn-supp button { background: #e6fcf5 !important; }
        .btn-inno button { background: #fff9db !important; }
        /* Top back button container spacing */
        .back-top { margin: 6px 0 12px 0; }
        </style>
        """,
        unsafe_allow_html=True,
    )

# ===============================
# Cookies (to limit to one reaction per browser)
# ===============================
def cm():
    if "cm" not in st.session_state:
        st.session_state.cm = stx.CookieManager()
    return st.session_state.cm

def set_reacted_cookie(candidate_id: str, value: str):
    expires = datetime.utcnow() + timedelta(days=180)
    cm().set(f"reacted_{candidate_id}", value, expires_at=expires)

def get_reacted_cookie(candidate_id: str) -> str | None:
    return cm().get(f"reacted_{candidate_id}")

# ===============================
# DB Helpers
# ===============================
def get_conn():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reactions (
            candidate_id TEXT NOT NULL,
            react_type   TEXT NOT NULL,
            count        INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (candidate_id, react_type)
        )
        """
    )
    return conn

def bootstrap_reactions(conn, candidate_ids):
    cur = conn.cursor()
    for cid in candidate_ids:
        for rkey, _ in REACTIONS:
            cur.execute(
                "INSERT OR IGNORE INTO reactions(candidate_id, react_type, count) VALUES (?, ?, 0)",
                (cid, rkey),
            )
    conn.commit()

def get_reaction_counts(conn, candidate_id) -> dict:
    cur = conn.cursor()
    cur.execute(
        "SELECT react_type, count FROM reactions WHERE candidate_id = ?",
        (candidate_id,),
    )
    return {rt: c for rt, c in cur.fetchall()}

# ===============================
# Data Loading
# ===============================
def load_candidates() -> pd.DataFrame:
    if not CANDIDATES_CSV.exists():
        st.error(f"Missing candidates file: {CANDIDATES_CSV}")
        st.stop()
    df = pd.read_csv(CANDIDATES_CSV, dtype=str).fillna("")
    required = ["id", "name", "building", "floor", "apt", "image", "program_file"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        st.error(f"Missing columns in candidates.csv: {missing}")
        st.stop()
    return df

# ===============================
# Helpers
# ===============================
def find_image_case_insensitive(filename: str):
    if not filename:
        return None
    name = filename.strip()
    direct = IMG_DIR / name
    if direct.exists():
        return direct
    stem = Path(name).stem.lower()
    for p in IMG_DIR.glob("*"):
        if p.is_file() and p.suffix.lower() in SUPPORTED_IMG_EXTS and p.stem.lower() == stem:
            return p
    for p in IMG_DIR.glob("*"):
        if p.is_file() and p.name.lower() == name.lower():
            return p
    return None

# ===============================
# UI
# ===============================
def candidate_card(cand_row):
    with st.container():
        st.markdown('<div class="soft-card">', unsafe_allow_html=True)
        cols = st.columns([2, 1])  # RTL info right

        with cols[1]:
            img_path = find_image_case_insensitive(cand_row.get("image", ""))
            if img_path and img_path.exists():
                st.image(str(img_path), use_container_width=True)
            else:
                st.image(Image.new("RGB", (400, 400), color=(235, 235, 235)), caption="لا توجد صورة", use_container_width=True)

        with cols[0]:
            st.markdown(
                f"""
                <h3 style="margin-top:0">{cand_row['name']}</h3>
                <div>
                    <span class="pill">🏢 العقار: {cand_row['building']}</span>
                    <span class="pill">⬆️ الدور: {cand_row['floor']}</span>
                    <span class="pill">🚪 الشقة: {cand_row['apt']}</span>
                    <span class="pill">🆔 {cand_row['id']}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("عرض البرنامج الانتخابي →", key=f"open_{cand_row['id']}"):
                st.query_params.update({"view": "profile", "id": cand_row["id"]})
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

def list_view(df: pd.DataFrame):
    st.subheader("قائمة المرشحين")
    with st.expander("---  تصفيات / بحث"):
        q = st.text_input("ابحث بالاسم أو الكود", "").strip()
        c1, c2, c3 = st.columns(3)
        with c1:
            f_building = st.text_input("العقار", "").strip()
        with c2:
            f_floor = st.text_input("الدور", "").strip()
        with c3:
            f_apt = st.text_input("الشقة", "").strip()

    fdf = df.copy()
    if q:
        fdf = fdf[fdf.apply(lambda r: q.lower() in (r["name"] + r["id"]).lower(), axis=1)]
    if f_building:
        fdf = fdf[fdf["building"].str.contains(f_building, case=False, na=False)]
    if f_floor:
        fdf = fdf[fdf["floor"].str.contains(f_floor, case=False, na=False)]
    if f_apt:
        fdf = fdf[fdf["apt"].str.contains(f_apt, case=False, na=False)]

    if fdf.empty:
        st.info("لا توجد نتائج مطابقة.")
        return

    for _, row in fdf.iterrows():
        candidate_card(row)

def profile_view(df: pd.DataFrame, candidate_id: str):
    match = df[df["id"] == candidate_id]
    if match.empty:
        st.error("لم يتم العثور على المرشح المطلوب.")
        if st.button("العودة للقائمة"):
            st.query_params.clear()
            st.rerun()
        return

    cand = match.iloc[0]

    # Top back button (better UX)
    st.markdown('<div class="back-top">', unsafe_allow_html=True)
    if st.button("← الرجوع إلى قائمة المرشحين", key=f"back_top_{cand['id']}"):
        st.query_params.clear()
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(f"<div class='title-badge'>الصفحة التعريفية — {cand['name']}</div>", unsafe_allow_html=True)
    st.caption(f"🏢 {cand['building']}  •  ⬆️ {cand['floor']}  •  🚪 {cand['apt']}  •  🆔 {cand['id']}")

    cols = st.columns([2, 1])
    img_path = find_image_case_insensitive(cand.get("image", ""))

    with cols[1]:
        if img_path and img_path.exists():
            st.image(str(img_path), use_container_width=True)
        else:
            st.image(Image.new("RGB", (400, 400), color=(235, 235, 235)), use_container_width=True)

        # Reactions (emoji only + cookies limit)
        conn = get_conn()
        counts = get_reaction_counts(conn, cand["id"]) or {}

        reacted_value = get_reacted_cookie(cand["id"])
        disabled = reacted_value is not None

        b1, b2, b3, b4 = st.columns(4)
        for idx, (rkey, emoji) in enumerate(REACTIONS):
            container_class = ["btn-love","btn-like","btn-supp","btn-inno"][idx]
            with [b1,b2,b3,b4][idx]:
                st.markdown(f'<div class="{container_class}">', unsafe_allow_html=True)
                label = f"{emoji} {counts.get(rkey, 0)}"
                if st.button(label, key=f"react_{rkey}_{cand['id']}", disabled=disabled):
                    if reacted_value is None:
                        cur = conn.cursor()
                        cur.execute(
                            "UPDATE reactions SET count = count + 1 WHERE candidate_id = ? AND react_type = ?",
                            (cand["id"], rkey),
                        )
                        conn.commit()
                        set_reacted_cookie(cand["id"], rkey)
                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

    with cols[0]:
        st.markdown("### البرنامج الانتخابي")
        prog_file = cand.get("program_file", "").strip()
        ppath = PROGRAMS_DIR / prog_file if prog_file else None
        if ppath and ppath.exists():
            st.markdown(ppath.read_text(encoding="utf-8"))
        else:
            st.info("لا يوجد برنامج انتخابي مرفوع بعد.")

    st.divider()
    if st.button("← الرجوع إلى قائمة المرشحين", key=f"back_bottom_{cand['id']}"):
        st.query_params.clear()
        st.rerun()

def main():
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    inject_css()

    # Centered title only
    st.markdown(f"<div class='title-badge'>{APP_TITLE}</div>", unsafe_allow_html=True)

    df = load_candidates()
    conn = get_conn()
    bootstrap_reactions(conn, df["id"].tolist())

    qp = st.query_params.to_dict()
    view = qp.get("view", "list")

    if view == "profile":
        candidate_id = qp.get("id")
        if not candidate_id:
            st.warning("معرّف المرشح مفقود.")
            list_view(df)
        else:
            profile_view(df, candidate_id)
    else:
        list_view(df)

if __name__ == "__main__":
    main()
