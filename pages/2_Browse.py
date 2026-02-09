import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
import re
import html

from app.lib.session import init_session, is_logged_in
from app.lib.repos import (
    cached_list_recipes,
    cached_list_recipe_ingredients,
    cached_list_profiles_by_ids,
    cached_list_recipe_seasons,
)
from app.lib.ui import set_full_page_background, load_css
from app.lib.brand import sidebar_brand

st.set_page_config(
    page_title="Browse",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)
set_full_page_background("app/static/bg_browse.jpg")
init_session()
load_css()
sidebar_brand()

st.title("📚 Browse recipes")

# ---- Readability CSS for Details panel ----
st.markdown(
    """
    <style>
      /* Details header "chip" */
      .details-title{
        display: inline-block;
        background: rgba(255, 255, 255, 0.92);
        padding: 10px 16px;
        border-radius: 14px;
        font-size: 1.35rem;
        font-weight: 900;
        margin-bottom: 10px;
        box-shadow: 0 8px 20px rgba(0,0,0,.18);
        color: #1f1f1f;
      }

      /* The main details panel */
      .details-panel {
        background: rgba(255, 255, 255, 0.94);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        border: 1px solid rgba(0,0,0,0.10);
        border-radius: 22px;
        padding: 18px 20px;
        box-shadow: 0 16px 38px rgba(0,0,0,0.18);
      }

      /* Force readable text inside */
      .details-panel, .details-panel * {
        color: #1f1f1f !important;
        text-shadow: none !important;
      }

      .details-meta {
        margin-top: 0.25rem;
        margin-bottom: 0.75rem;
        font-size: 0.98rem;
        line-height: 1.35;
      }

      .details-section-title {
        margin-top: 1.0rem;
        margin-bottom: 0.4rem;
        font-weight: 800;
      }

      /* Lists inside details */
      .details-panel ul {
        margin-top: 0.25rem;
        margin-bottom: 0.75rem;
        padding-left: 1.2rem;
      }
      .details-panel li {
        margin-bottom: 0.25rem;
      }

      /* Make instruction lines breathe */
      .details-panel .steps li {
        margin-bottom: 0.45rem;
        line-height: 1.45;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

st.info(
    "How to browse recipes:\n"
    "- Use the **Filters** in the left sidebar to narrow down the list.\n"
    "- You can filter by **Seasons** (winter/spring/summer/fall) and choose how strict it is:\n"
    "  - **Contains ANY** → shows recipes that match *at least one* of the selected seasons.\n"
    "  - **Contains ALL** → shows recipes that match *every* selected season.\n"
    "- You can also filter by **Ingredients** the same way:\n"
    "  - **Contains ANY** → recipes containing *at least one* selected ingredient.\n"
    "  - **Contains ALL** → recipes containing *all* selected ingredients.\n"
    "- Use **Search** to find recipes by name, and **Sort** to order results.\n"
    "- Finally, pick a recipe in the **Details** section to view full ingredients + instructions."
)

if not is_logged_in():
    st.warning("Please log in via Home.")
    st.stop()

token = st.session_state.session.access_token


def strip_trailing_id(s: str) -> str:
    """Remove trailing ' (id)' patterns that might have been stored in names."""
    if not s:
        return ""
    return re.sub(r"\s*\(([0-9a-fA-F-]{6,})\)\s*$", "", s).strip()


# =========================
# Load data (efficiently)
# =========================
recipes = cached_list_recipes(token)
links = cached_list_recipe_ingredients(token)
season_rows = cached_list_recipe_seasons(token)

if not recipes:
    st.info("No recipes yet.")
    st.stop()

df_recipes = pd.DataFrame(recipes)

# Ensure columns exist
for col in ["servings", "prep_minutes", "cook_minutes", "total_minutes", "created_by", "instructions", "notes"]:
    if col not in df_recipes.columns:
        df_recipes[col] = None

df_recipes["name"] = df_recipes["name"].astype(str).apply(strip_trailing_id)

# =========================
# Seasons aggregation
# =========================
df_seasons = pd.DataFrame(season_rows)

if df_seasons.empty:
    seasons_by_recipe = {}
else:
    seasons_by_recipe = (
        df_seasons.groupby("recipe_id")["season"]
        .apply(lambda s: sorted(set([x for x in s.tolist() if x])))
        .to_dict()
    )

df_recipes["seasons"] = df_recipes["id"].map(lambda rid: seasons_by_recipe.get(rid, []))
df_recipes["seasons_str"] = df_recipes["seasons"].map(lambda xs: ", ".join(xs) if xs else "—")

# =========================
# Creator names
# =========================
creator_ids = tuple(sorted(df_recipes["created_by"].dropna().unique().tolist()))
profiles = cached_list_profiles_by_ids(token, creator_ids)

id_to_name = {}
for p in profiles:
    fn = (p.get("first_name") or "").strip()
    ln = (p.get("last_name") or "").strip()
    full = (fn + " " + ln).strip()
    id_to_name[p["id"]] = full if full else "Unknown"

df_recipes["creator_name"] = df_recipes["created_by"].map(lambda uid: id_to_name.get(uid, "Unknown"))

# =========================
# Ingredients aggregation
# =========================
df_links = pd.DataFrame(links)

def safe_str(x):
    return (x or "").strip() if isinstance(x, str) else x

def fmt_line(row) -> str:
    ing_name = strip_trailing_id(((row.get("ingredients") or {}).get("name", "")))
    qty = safe_str(row.get("quantity"))
    unit = safe_str(row.get("unit"))
    comment = safe_str(row.get("comment"))

    left = " ".join([str(x) for x in [qty, unit] if x not in [None, "", "None"]]).strip()
    base = f"{left} — {ing_name}" if left else ing_name
    if comment:
        base = f"{base} ({comment})"
    return base

if not df_links.empty:
    df_links["ingredient_name"] = df_links["ingredients"].apply(
        lambda x: strip_trailing_id((x or {}).get("name", ""))
    )
    df_links["ingredient_line"] = df_links.apply(fmt_line, axis=1)
else:
    df_links = pd.DataFrame(columns=["recipe_id", "ingredient_name", "ingredient_line"])

ingredients_by_recipe = (
    df_links.groupby("recipe_id")["ingredient_name"]
    .apply(lambda s: sorted(set([x for x in s if x])))
    .to_dict()
)

ingredient_lines_by_recipe = (
    df_links.groupby("recipe_id")["ingredient_line"]
    .apply(lambda s: [x for x in s.tolist() if x])
    .to_dict()
)

df_recipes["ingredients"] = df_recipes["id"].map(lambda rid: ingredients_by_recipe.get(rid, []))
df_recipes["ingredients_lines"] = df_recipes["id"].map(lambda rid: ingredient_lines_by_recipe.get(rid, []))
df_recipes["ingredients_str"] = df_recipes["ingredients"].map(lambda xs: ", ".join(xs))

# =========================
# Filters UI
# =========================
st.sidebar.header("Filters")

ALL_SEASONS = ["winter", "spring", "summer", "fall"]
chosen_seasons = st.sidebar.multiselect("Seasons", ALL_SEASONS)
season_match_mode = st.sidebar.radio("Season match", ["Contains ANY", "Contains ALL"], horizontal=False)

creator_names = sorted(df_recipes["creator_name"].dropna().unique().tolist())
creator_choice = st.sidebar.selectbox("Creator", ["(any)"] + creator_names)

all_ingredients = sorted(df_links["ingredient_name"].dropna().unique().tolist())
chosen_ingredients = st.sidebar.multiselect("Ingredients", all_ingredients)
ingredient_match_mode = st.sidebar.radio("Ingredient match", ["Contains ANY", "Contains ALL"])

search = st.sidebar.text_input("Search recipe name")
sort_choice = st.sidebar.selectbox("Sort by", ["Name (A→Z)", "Total time (low→high)", "Total time (high→low)"])

# =========================
# Apply filters
# =========================
df = df_recipes.copy()

if chosen_seasons:
    chosen_set = set(chosen_seasons)

    def season_matches(season_list):
        sset = set(season_list or [])
        if season_match_mode == "Contains ANY":
            return len(sset & chosen_set) > 0
        return chosen_set.issubset(sset)

    df = df[df["seasons"].apply(season_matches)]

if creator_choice != "(any)":
    df = df[df["creator_name"] == creator_choice]

if chosen_ingredients:
    chosen_set = set(chosen_ingredients)

    def ing_matches(ing_list):
        ing_set = set(ing_list or [])
        if ingredient_match_mode == "Contains ANY":
            return len(ing_set & chosen_set) > 0
        return chosen_set.issubset(ing_set)

    df = df[df["ingredients"].apply(ing_matches)]

if search.strip():
    df = df[df["name"].str.contains(search.strip(), case=False, na=False)]

if sort_choice == "Name (A→Z)":
    df = df.sort_values("name")
elif sort_choice == "Total time (low→high)":
    df = df.sort_values("total_minutes")
else:
    df = df.sort_values("total_minutes", ascending=False)

# =========================
# Table view
# =========================
st.subheader(f"Recipes ({len(df)} shown)")

def seasons_label(seasons):
    if set(seasons) == {"winter", "spring", "summer", "fall"}:
        return "All year"
    return ", ".join(seasons)

cols = [
    "name",
    "seasons_str",
    "servings",
    "prep_minutes",
    "cook_minutes",
    "total_minutes",
    "creator_name",
    "ingredients_str",
]
cols = [c for c in cols if c in df.columns]

df_display = df[cols].rename(columns={
    "name": "Recipe",
    "seasons_str": "Seasons",
    "servings": "Servings",
    "prep_minutes": "Prep (min)",
    "cook_minutes": "Cook (min)",
    "total_minutes": "Total (min)",
    "creator_name": "Creator",
    "ingredients_str": "Ingredients",
})

st.dataframe(df_display, width="stretch", hide_index=True)

# =========================
# Helpers for Details HTML
# =========================

import textwrap
import re

def esc(x):
    return html.escape(str(x)) if x is not None else ""

def to_lines(text: str):
    if not text:
        return []
    t = str(text).replace("\r\n", "\n").replace("\r", "\n")
    return [ln.strip() for ln in t.split("\n") if ln.strip()]

def render_text_or_bullets(text: str, css_class: str = "") -> str:
    lines = to_lines(text)
    if not lines:
        return ""

    bullet_like = all(re.match(r"^(\-|\*|•)\s+", ln) for ln in lines)
    if bullet_like:
        items = []
        for ln in lines:
            ln = re.sub(r"^(\-|\*|•)\s+", "", ln).strip()
            items.append(f"<li>{esc(ln)}</li>")
        cls = f' class="{css_class}"' if css_class else ""
        return f"<ul{cls}>" + "".join(items) + "</ul>"

    return "<div>" + "<br>".join(esc(ln) for ln in lines) + "</div>"
def reorder_ingredient(line: str) -> str:
    """
    Convert:
    '250 g — Crevettes (comment)'
    to:
    'Crevettes : 250 g (comment)'
    """
    if "—" not in line:
        return line.strip()

    left, right = [x.strip() for x in line.split("—", 1)]

    # Detect comments at the end: "(...)"
    comment = ""
    if right.endswith(")") and "(" in right:
        base, comment = right.rsplit("(", 1)
        right = base.strip()
        comment = " (" + comment

    name = right
    qty = left

    if qty:
        return f"{name} : {qty}{comment}"
    return f"{name}{comment}"

st.divider()
st.markdown('<div class="details-title">Details</div>', unsafe_allow_html=True)

recipe_names = df["name"].fillna("").tolist()
selected_name = st.selectbox("Select a recipe", ["(none)"] + sorted(set(recipe_names)))

if selected_name != "(none)":
    candidates = df[df["name"] == selected_name]

    if len(candidates) > 1:
        chosen_uid = st.selectbox(
            "Which one?",
            candidates["created_by"].tolist(),
            format_func=lambda uid: id_to_name.get(uid, "Unknown"),
        )
        row = candidates[candidates["created_by"] == chosen_uid].iloc[0]
    else:
        row = candidates.iloc[0]

    ingredients_html = "".join(
        f"<li>{esc(reorder_ingredient(line))}</li>"
        for line in (row.get("ingredients_lines") or [])
    ) or "<li><i>No ingredients."


    instructions_html = render_text_or_bullets(row.get("instructions") or "", css_class="steps")
    notes_html = render_text_or_bullets(row.get("notes") or "")

    html_block = f"""
    <div class="details-panel">
      <h3 style="margin-top:0;">{esc(row.get("name"))}</h3>

      <div class="details-meta">
        <b>Creator:</b> {esc(row.get("creator_name"))}<br>
        <b>Seasons:</b> {esc(seasons_label(row.get("seasons", [])))}<br>
        <b>Servings:</b> {esc(row.get("servings", 1))}<br>
        <b>Time:</b>
        Prep {esc(row.get("prep_minutes", 0))} min +
        Cook {esc(row.get("cook_minutes", 0))} min :
        Total {esc(row.get("total_minutes", 0))} min
      </div>

      <div class="details-section-title">Ingredients</div>
      <ul>{ingredients_html}</ul>
    """

    if instructions_html:
        html_block += f"""
      <div class="details-section-title">Instructions</div>
      {instructions_html}
        """

    if notes_html:
        html_block += f"""
      <div class="details-section-title">Notes</div>
      {notes_html}
        """

    html_block += """
    </div>
    """

    # ✅ CRITICAL: remove indentation so Markdown doesn't turn it into a code block
    html_block = textwrap.dedent(html_block).strip()

    st.markdown(html_block, unsafe_allow_html=True)

