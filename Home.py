import sys
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[0]  # Home.py sits at repo root
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
import altair as alt

from app.lib.session import init_session, is_logged_in
from app.lib.auth_ui import auth_sidebar
from app.lib.repos import (
    get_my_role,
    ensure_my_profile,
    set_my_role,
    cached_list_recipes,
    cached_list_recipe_ingredients,
    cached_list_profiles_by_ids,
    cached_list_recipe_seasons,
)
from app.lib.ui import load_css, set_full_page_background
from app.lib.brand import sidebar_brand


# =========================
# Page config
# =========================
st.set_page_config(
    page_title="Les recettes de la Madre",
    page_icon="🍋",
    layout="wide",
    initial_sidebar_state="expanded",
)

set_full_page_background("app/static/bg_home.jpg")
init_session()
load_css()
sidebar_brand()

# Sidebar auth
auth_sidebar()


# =========================
# Pretty Home analytics CSS
# =========================
st.markdown(
    """
    <style>
      /* Analytics section spacing */
      .home-analytics-title{
        margin-top: .25rem;
        margin-bottom: .75rem;
        font-size: 1.35rem;
        font-weight: 900;
      }

      /* KPI grid cards */
      .kpi-card{
        background: rgba(255,255,255,.92);
        border: 1px solid rgba(0,0,0,.08);
        border-radius: 18px;
        padding: 14px 16px;
        box-shadow: 0 12px 28px rgba(0,0,0,.10);
      }
      .kpi-top{
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap: 12px;
      }
      .kpi-value{
        font-size: 1.65rem;
        font-weight: 900;
        line-height: 1;
        margin: 0;
      }
      .kpi-label{
        margin: 6px 0 0;
        font-size: .95rem;
        color: rgba(0,0,0,.62);
        font-weight: 600;
      }
      .kpi-icon{
        width: 38px;
        height: 38px;
        border-radius: 14px;
        display:flex;
        align-items:center;
        justify-content:center;
        background: linear-gradient(135deg, rgba(255,107,107,.95), rgba(255,183,3,.95));
        color: #fff;
        font-weight: 900;
        box-shadow: 0 10px 22px rgba(255,77,109,.20);
        flex: 0 0 auto;
      }

      /* Pretty HTML tables (instead of st.dataframe) */
      table.pretty{
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        overflow: hidden;
        border: 1px solid rgba(0,0,0,.08);
        border-radius: 14px;
        background: rgba(255,255,255,.92);
        box-shadow: 0 10px 24px rgba(0,0,0,.08);
      }
      table.pretty th{
        text-align: left;
        font-size: .9rem;
        padding: 10px 12px;
        background: rgba(255,183,3,.16);
        color: rgba(0,0,0,.78);
        font-weight: 800;
        border-bottom: 1px solid rgba(0,0,0,.08);
      }
      table.pretty td{
        padding: 10px 12px;
        font-size: .95rem;
        border-bottom: 1px solid rgba(0,0,0,.06);
        color: rgba(0,0,0,.80);
      }
      table.pretty tr:last-child td{ border-bottom: none; }
      table.pretty tbody tr:hover td{
        background: rgba(255,107,107,.08);
      }

      /* Make sure charts are on a clean background */
      .stVegaLiteChart, .stAltairChart{
        background: transparent !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================
# HERO
# =========================
st.markdown(
    """
    <div class="hero">
      <h1 style="margin:0">🍋 La cuisine de la Madre</h1>
      <p style="margin:8px 0 0; color:rgba(0,0,0,.65); font-size: 1.02rem">
        Le carnet de recettes de la Tribue Erbland (et plus)
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.info(
    "Welcome to **La cuisine de la Madre** 👋\n\n"
    "- This is the **family cookbook**, where recipes are shared, explored, and curated.\n"
    "- Use **Browse** to explore recipes by **season** and **ingredients**.\n"
    "- Your **role** defines what you can do:\n"
    "  - **Reader** → browse and view recipes.\n"
    "  - **Editor** → create, edit, and delete recipes.\n"
    "- If you’re a reader and have the **editor code**, you can upgrade your role directly from this page.\n\n"
    "Use the **left navigation** to move between Browse, Add Recipe, and My Space."
)

st.write("")


# =========================
# Not logged in
# =========================
if not is_logged_in():
    st.info("Log in using the sidebar to start.")
    c1, c2 = st.columns([1, 1])

    with c1:
        st.markdown(
            "<div class='card'><h3>✨ Browse</h3><p>Explore recipes by season and ingredients.</p></div>",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            "<div class='card'><h3>🔐 Create an account</h3><p>Sign up in the sidebar to join the family cookbook.</p></div>",
            unsafe_allow_html=True,
        )

    st.stop()


# =========================
# Logged-in content
# =========================
token = st.session_state.session.access_token
user_id = st.session_state.session.user.id

ensure_my_profile(token, user_id)
st.session_state.role = get_my_role(token, user_id)

role = (st.session_state.role or "reader")
is_editor = (role == "editor")

st.markdown(
    f"<span class='badge'>Authenticated ✅</span>"
    f"<span class='badge'>Role: {role}</span>",
    unsafe_allow_html=True,
)

st.write("")


def get_secret(name: str, default: str = "") -> str:
    try:
        return str(st.secrets.get(name, default))
    except Exception:
        return os.getenv(name, default)


EDITOR_CODE = get_secret("EDITOR_INVITE_CODE", "")

# Show editor upgrade UI only for non-editors
if role != "editor":
    with st.expander("🔑 Become an editor"):
        st.write("If you have the family editor code, enter it to unlock recipe editing.")
        code = st.text_input("Editor code", type="password", key="home_editor_code")

        if st.button("Upgrade to editor", use_container_width=True, key="home_upgrade_btn"):
            if not EDITOR_CODE:
                st.error("Editor code is not configured on the server (missing EDITOR_INVITE_CODE).")
                st.stop()

            if code.strip() != EDITOR_CODE:
                st.error("Wrong code.")
                st.stop()

            set_my_role(token, user_id, "editor")
            st.session_state.role = "editor"
            st.cache_data.clear()
            st.success("Upgraded to editor ✅")
            st.rerun()


# =========================
# Feature cards
# =========================
c1, c2, c3 = st.columns(3)

with c1:
    st.markdown(
        "<div class='card'><h3>📚 Browse</h3>"
        "<p>Filter by season, creator, and ingredients — then open full details.</p></div>",
        unsafe_allow_html=True,
    )

with c2:
    if is_editor:
        st.markdown(
            "<div class='card'><h3>✍️ Add Recipe</h3>"
            "<p>Create a new recipe and link ingredients cleanly.</p></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div class='card'><h3>✍️ Add Recipe</h3>"
            "<p>You need the <b>editor</b> role to create/edit recipes.</p></div>",
            unsafe_allow_html=True,
        )

with c3:
    st.markdown(
        "<div class='card'><h3>👤 My Space</h3>"
        "<p>See your recipes and manage them (edit / delete if editor).</p></div>",
        unsafe_allow_html=True,
    )

st.write("")
st.caption("Use the pages in the left navigation to browse recipes and manage your space.")


# =========================
# Cookbook analytics
# =========================
st.divider()
st.markdown('<div class="home-analytics-title">📊 Cookbook analytics</div>', unsafe_allow_html=True)


@st.cache_data(ttl=60, show_spinner=False)
def _load_home_stats(access_token: str):
    recipes_ = cached_list_recipes(access_token)
    links_ = cached_list_recipe_ingredients(access_token)
    seasons_ = cached_list_recipe_seasons(access_token)
    return recipes_ or [], links_ or [], seasons_ or []


with st.spinner("Loading cookbook stats…"):
    recipes, links, seasons_rows = _load_home_stats(token)

df_recipes = pd.DataFrame(recipes)
df_links = pd.DataFrame(links)
df_seasons = pd.DataFrame(seasons_rows)

# Ensure columns exist
for col in ["id", "name", "total_minutes", "created_by", "created_at"]:
    if col not in df_recipes.columns:
        df_recipes[col] = None

# Creator names
creator_ids = tuple(sorted(df_recipes["created_by"].dropna().unique().tolist()))
profiles = cached_list_profiles_by_ids(token, creator_ids)

id_to_name = {}
for p in (profiles or []):
    fn = (p.get("first_name") or "").strip()
    ln = (p.get("last_name") or "").strip()
    full = (fn + " " + ln).strip()
    id_to_name[p["id"]] = full if full else "Unknown"

df_recipes["creator_name"] = df_recipes["created_by"].map(lambda uid: id_to_name.get(uid, "Unknown"))

# KPIs
total_recipes = int(len(df_recipes))
total_links = int(len(df_links))

unique_ingredients = 0
if not df_links.empty and "ingredients" in df_links.columns:
    ing_names = df_links["ingredients"].apply(lambda x: (x or {}).get("name", "")).replace("", pd.NA).dropna()
    unique_ingredients = int(ing_names.nunique())

t = pd.to_numeric(df_recipes["total_minutes"], errors="coerce").dropna()
avg_time = int(t.mean()) if not t.empty else 0


def kpi(icon: str, value: str, label: str):
    st.markdown(
        f"""
        <div class="kpi-card">
          <div class="kpi-top">
            <div>
              <div class="kpi-value">{value}</div>
              <div class="kpi-label">{label}</div>
            </div>
            <div class="kpi-icon">{icon}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


k1, k2, k3, k4 = st.columns(4)
with k1:
    kpi("📚", str(total_recipes), "Total recipes")
with k2:
    kpi("🧂", str(unique_ingredients), "Unique ingredients")
with k3:
    kpi("🧾", str(total_links), "Ingredient lines")
with k4:
    kpi("⏱️", f"{avg_time} min", "Avg total time")

st.write("")

# Charts
left, right = st.columns([1.15, 1.0], gap="large")

with left:
    with st.container(border=True):
        st.markdown("### Most used ingredients")
        if df_links.empty or "ingredients" not in df_links.columns:
            st.info("No ingredient usage data yet.")
        else:
            ing_names = df_links["ingredients"].apply(lambda x: (x or {}).get("name", "")).replace("", pd.NA).dropna()
            top_ing = ing_names.value_counts().head(12).reset_index()
            top_ing.columns = ["ingredient", "count"]

            chart = (
                alt.Chart(top_ing)
                .mark_bar()
                .encode(
                    x=alt.X("count:Q", title="Uses"),
                    y=alt.Y("ingredient:N", sort="-x", title=None),
                    tooltip=["ingredient:N", "count:Q"],
                )
                .properties(height=320)
                .configure_view(strokeOpacity=0)
            )
            st.altair_chart(chart, use_container_width=True)

    with st.container(border=True):
        st.markdown("### Recipes by creator")
        if df_recipes.empty:
            st.info("No recipes yet.")
        else:
            top_creators = (
                df_recipes["creator_name"]
                .fillna("Unknown")
                .value_counts()
                .head(10)
                .reset_index()
            )
            top_creators.columns = ["creator", "count"]

            chart = (
                alt.Chart(top_creators)
                .mark_bar()
                .encode(
                    x=alt.X("count:Q", title="Recipes"),
                    y=alt.Y("creator:N", sort="-x", title=None),
                    tooltip=["creator:N", "count:Q"],
                )
                .properties(height=280)
                .configure_view(strokeOpacity=0)
            )
            st.altair_chart(chart, use_container_width=True)

with right:
    with st.container(border=True):
        st.markdown("### Recipes by season")
        ALL_SEASONS = ["winter", "spring", "summer", "fall"]

        if df_seasons.empty or "season" not in df_seasons.columns:
            st.info("No season links yet.")
        else:
            season_counts = (
                df_seasons["season"]
                .value_counts()
                .reindex(ALL_SEASONS)
                .fillna(0)
                .astype(int)
                .reset_index()
            )
            season_counts.columns = ["season", "count"]

            chart = (
                alt.Chart(season_counts)
                .mark_bar()
                .encode(
                    x=alt.X("season:N", sort=ALL_SEASONS, title=None),
                    y=alt.Y("count:Q", title="Recipes"),
                    tooltip=["season:N", "count:Q"],
                )
                .properties(height=220)
                .configure_view(strokeOpacity=0)
            )
            st.altair_chart(chart, use_container_width=True)

    with st.container(border=True):
        st.markdown("### Total time buckets")
        if t.empty:
            st.info("No time data yet.")
        else:
            bins = [0, 10, 20, 30, 45, 60, 90, 10_000]
            labels = ["0–10", "10–20", "20–30", "30–45", "45–60", "60–90", "90+"]

            bucket = pd.cut(t, bins=bins, labels=labels, include_lowest=True)
            bucket_counts = (
                bucket.value_counts()
                .reindex(labels)
                .fillna(0)
                .astype(int)
                .reset_index()
            )
            bucket_counts.columns = ["bucket", "count"]

            chart = (
                alt.Chart(bucket_counts)
                .mark_bar()
                .encode(
                    x=alt.X("bucket:N", sort=labels, title=None),
                    y=alt.Y("count:Q", title="Recipes"),
                    tooltip=["bucket:N", "count:Q"],
                )
                .properties(height=220)
                .configure_view(strokeOpacity=0)
            )
            st.altair_chart(chart, use_container_width=True)

# Pretty HTML tables
st.write("")
st.markdown("### Highlights")


def html_table(df_small: pd.DataFrame) -> str:
    if df_small is None or df_small.empty:
        return "<div style='color:rgba(0,0,0,.6)'><i>No data.</i></div>"
    df_safe = df_small.copy()
    for c in df_safe.columns:
        df_safe[c] = df_safe[c].astype(str)
    return df_safe.to_html(index=False, classes="pretty", border=0, escape=True)


tmp = df_recipes.copy()
tmp["total_m"] = pd.to_numeric(tmp["total_minutes"], errors="coerce")
tmp = tmp.dropna(subset=["total_m"])

h1, h2 = st.columns(2)

with h1:
    with st.container(border=True):
        st.markdown("#### ⚡ Fastest recipes")
        fastest = (
            tmp.sort_values("total_m")
            .head(6)[["name", "total_m", "creator_name"]]
            .rename(columns={"name": "Recipe", "total_m": "Total (min)", "creator_name": "Creator"})
        )
        st.markdown(html_table(fastest), unsafe_allow_html=True)

with h2:
    with st.container(border=True):
        st.markdown("#### 🕰️ Longest recipes")
        slowest = (
            tmp.sort_values("total_m", ascending=False)
            .head(6)[["name", "total_m", "creator_name"]]
            .rename(columns={"name": "Recipe", "total_m": "Total (min)", "creator_name": "Creator"})
        )
        st.markdown(html_table(slowest), unsafe_allow_html=True)

with st.container(border=True):
    st.markdown("#### 🆕 Recently added")
    if "created_at" not in df_recipes.columns or df_recipes["created_at"].isna().all():
        st.markdown("<i>No created_at available.</i>", unsafe_allow_html=True)
    else:
        recent = df_recipes.copy()
        recent["created_at_dt"] = pd.to_datetime(recent["created_at"], errors="coerce")
        recent = (
            recent.dropna(subset=["created_at_dt"])
            .sort_values("created_at_dt", ascending=False)
            .head(10)[["name", "creator_name", "created_at_dt"]]
            .rename(columns={"name": "Recipe", "creator_name": "Creator", "created_at_dt": "Created"})
        )
        recent["Created"] = recent["Created"].dt.strftime("%Y-%m-%d %H:%M")
        st.markdown(html_table(recent), unsafe_allow_html=True)
