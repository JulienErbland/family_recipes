import streamlit as st
import pandas as pd

from app.lib.session import init_session, is_logged_in
from app.lib.repos import (
    list_recipes,
    list_recipe_ingredients,
    list_profiles_by_ids,
)

st.set_page_config(page_title="Browse", page_icon="📚", layout="wide")
init_session()
st.title("📚 Browse recipes")

if not is_logged_in():
    st.warning("Please log in via Home.")
    st.stop()

token = st.session_state.session.access_token

# =========================
# Load data (efficiently)
# =========================
recipes = list_recipes(token)
links = list_recipe_ingredients(token)

if not recipes:
    st.info("No recipes yet.")
    st.stop()

df_recipes = pd.DataFrame(recipes)

# --- Ensure columns exist even if empty / older schema ---
for col in ["season", "servings", "prep_minutes", "cook_minutes", "total_minutes", "created_by", "instructions", "notes"]:
    if col not in df_recipes.columns:
        df_recipes[col] = None

# =========================
# Creator names: id -> "First Last"
# =========================
creator_ids = sorted(df_recipes["created_by"].dropna().unique().tolist())
profiles = list_profiles_by_ids(token, creator_ids)

id_to_name = {}
for p in profiles:
    fn = (p.get("first_name") or "").strip()
    ln = (p.get("last_name") or "").strip()
    full = (fn + " " + ln).strip()
    id_to_name[p["id"]] = full if full else p["id"]

df_recipes["creator_name"] = df_recipes["created_by"].map(lambda uid: id_to_name.get(uid, uid))

# =========================
# Ingredients aggregation
# =========================
df_links = pd.DataFrame(links)

if not df_links.empty:
    # Nested ingredient name from PostgREST: ingredients(name)
    df_links["ingredient_name"] = df_links["ingredients"].apply(lambda x: (x or {}).get("name", ""))
else:
    df_links = pd.DataFrame(columns=["recipe_id", "ingredient_name"])

ingredients_by_recipe = (
    df_links.groupby("recipe_id")["ingredient_name"]
    .apply(lambda s: sorted(set([x for x in s if x])))
    .to_dict()
)

df_recipes["ingredients"] = df_recipes["id"].map(lambda rid: ingredients_by_recipe.get(rid, []))
df_recipes["ingredients_str"] = df_recipes["ingredients"].map(lambda xs: ", ".join(xs))

# =========================
# Filters UI
# =========================
st.sidebar.header("Filters")

# Season filter
seasons_present = sorted([s for s in df_recipes["season"].dropna().unique().tolist()])
all_seasons = ["all"] + [s for s in seasons_present if s != "all"]
season_choice = st.sidebar.selectbox("Season", ["(any)"] + all_seasons)

# Creator filter (by name)
creator_names = sorted(df_recipes["creator_name"].dropna().unique().tolist())
creator_choice = st.sidebar.selectbox("Creator", ["(any)"] + creator_names)

# Ingredient filter
all_ingredients = sorted(df_links["ingredient_name"].dropna().unique().tolist())
chosen_ingredients = st.sidebar.multiselect("Ingredients", all_ingredients)
match_mode = st.sidebar.radio("Ingredient match", ["Contains ANY", "Contains ALL"])

# =========================
# Apply filters
# =========================
df = df_recipes.copy()

if season_choice != "(any)":
    df = df[df["season"] == season_choice]

if creator_choice != "(any)":
    df = df[df["creator_name"] == creator_choice]

if chosen_ingredients:
    chosen_set = set(chosen_ingredients)

    def matches(ing_list):
        ing_set = set(ing_list or [])
        if match_mode == "Contains ANY":
            return len(ing_set & chosen_set) > 0
        return chosen_set.issubset(ing_set)

    df = df[df["ingredients"].apply(matches)]

# =========================
# Table view
# =========================
st.subheader(f"Recipes ({len(df)} shown)")

cols = [
    "name",
    "season",
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
    "season": "Season",
    "servings": "Servings",
    "prep_minutes": "Prep (min)",
    "cook_minutes": "Cook (min)",
    "total_minutes": "Total (min)",
    "creator_name": "Creator",
    "ingredients_str": "Ingredients",
})

st.dataframe(df_display, width="stretch", hide_index=True)

# =========================
# Details panel
# =========================
st.divider()
st.subheader("Details")

# Use recipe ID to disambiguate duplicates
label_to_id = {f"{row['name']} ({row['id'][:8]})": row["id"] for _, row in df.iterrows()}
selected_label = st.selectbox("Select a recipe", ["(none)"] + list(label_to_id.keys()))

if selected_label != "(none)":
    recipe_id = label_to_id[selected_label]
    row = df[df["id"] == recipe_id].iloc[0].to_dict()

    st.markdown(f"### {row.get('name')}")
    st.write(f"Creator: **{row.get('creator_name','')}**")
    st.write(
        f"Season: **{row.get('season','all')}** | "
        f"Servings: **{row.get('servings', 1)}**"
    )
    st.write(
        f"Prep: **{row.get('prep_minutes',0)}** | "
        f"Cook: **{row.get('cook_minutes',0)}** | "
        f"Total: **{row.get('total_minutes',0)}**"
    )

    st.write("**Ingredients:**")
    for ing in row.get("ingredients", []):
        st.write(f"- {ing}")

    instructions = row.get("instructions")
    if instructions:
        st.write("**Instructions**")
        st.write(instructions)
    else:
        st.info("No instructions provided for this recipe.")

    notes = row.get("notes")
    if notes:
        st.write("**Notes**")
        st.write(notes)
