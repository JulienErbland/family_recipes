import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
import re

from app.lib.session import init_session, is_logged_in
from app.lib.repos import (
    cached_list_recipes,
    cached_list_recipe_ingredients,
    cached_list_profiles_by_ids,
    # NEW (Option A)
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
      /* A readable "glass" panel for the details section */
      .details-card {
        background: rgba(255, 255, 255, 0.90);
        backdrop-filter: blur(6px);
        -webkit-backdrop-filter: blur(6px);
        border: 1px solid rgba(0,0,0,0.08);
        border-radius: 18px;
        padding: 1.2rem 1.4rem;
        box-shadow: 0 10px 28px rgba(0,0,0,0.18);
        color: #111 !important;
      }

      /* Force text inside to be dark and readable */
      .details-card * {
        color: #111 !important;
      }

      /* Improve spacing + readability */
      .details-meta {
        margin-top: 0.25rem;
        margin-bottom: 0.75rem;
        font-size: 0.98rem;
        line-height: 1.35;
      }

      .details-section-title {
        margin-top: 1.0rem;
        margin-bottom: 0.4rem;
        font-weight: 700;
      }

      /* Make bullets slightly bigger */
      .details-card ul {
        margin-top: 0.25rem;
        margin-bottom: 0.75rem;
      }
      .details-card li {
        margin-bottom: 0.25rem;
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


def render_multiline(text: str):
    """Preserve user newlines in Streamlit (Markdown line breaks)."""
    if not text:
        return
    st.markdown(text.replace("\n", "  \n"))


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

# --- Ensure columns exist even if empty / older schema ---
# Option A: recipes no longer has 'season'
for col in ["servings", "prep_minutes", "cook_minutes", "total_minutes", "created_by", "instructions", "notes"]:
    if col not in df_recipes.columns:
        df_recipes[col] = None

# Clean recipe names (in case old data contains "(id)" suffix)
df_recipes["name"] = df_recipes["name"].astype(str).apply(strip_trailing_id)

# =========================
# Seasons aggregation (Option A)
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
# Creator names: id -> "First Last" (no UID fallback)
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
    # for filtering
    df_links["ingredient_name"] = df_links["ingredients"].apply(
        lambda x: strip_trailing_id((x or {}).get("name", ""))
    )
    # for display
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

# Seasons filter (Option A: multi-season)
ALL_SEASONS = ["winter", "spring", "summer", "fall"]
chosen_seasons = st.sidebar.multiselect("Seasons", ALL_SEASONS)
season_match_mode = st.sidebar.radio("Season match", ["Contains ANY", "Contains ALL"], horizontal=False)

# Creator filter (by name)
creator_names = sorted(df_recipes["creator_name"].dropna().unique().tolist())
creator_choice = st.sidebar.selectbox("Creator", ["(any)"] + creator_names)

# Ingredient filter
all_ingredients = sorted(df_links["ingredient_name"].dropna().unique().tolist())
chosen_ingredients = st.sidebar.multiselect("Ingredients", all_ingredients)
ingredient_match_mode = st.sidebar.radio("Ingredient match", ["Contains ANY", "Contains ALL"])

# Search + sort
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
# Details panel (readable, no IDs shown)
# =========================
st.divider()
st.subheader("Details")

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
        row = candidates[candidates["created_by"] == chosen_uid].iloc[0].to_dict()
    else:
        row = candidates.iloc[0].to_dict()

    # ✅ open wrapper
    st.markdown("<div class='details-panel'>", unsafe_allow_html=True)

    st.markdown(f"### {row.get('name','')}")
    st.write(f"Creator: **{row.get('creator_name','')}**")
    st.write(f"Seasons: **{seasons_label(row.get('seasons', []))}**")
    st.write(f"Servings: **{row.get('servings', 1)}**")
    st.write(
        f"Prep: **{row.get('prep_minutes',0)}** | "
        f"Cook: **{row.get('cook_minutes',0)}** | "
        f"Total: **{row.get('total_minutes',0)}**"
    )

    st.write("**Ingredients:**")
    for line in row.get("ingredients_lines", []) or []:
        st.write(f"- {line}")

    instructions = row.get("instructions")
    if instructions:
        st.write("**Instructions**")
        render_multiline(instructions)
    else:
        st.info("No instructions provided for this recipe.")

    notes = row.get("notes")
    if notes:
        st.write("**Notes**")
        render_multiline(notes)

    # ✅ close wrapper
    st.markdown("</div>", unsafe_allow_html=True)

