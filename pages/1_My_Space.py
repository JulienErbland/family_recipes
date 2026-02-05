import streamlit as st
import pandas as pd

from app.lib.session import init_session, is_logged_in
from app.lib.repos import (
    get_my_role,
    cached_list_my_recipes,
    update_recipe,
    delete_recipe,
    cached_list_ingredients,
    find_ingredient_by_name,
    create_ingredient,
    cached_get_recipe_ingredients,
    add_recipe_ingredient,
    delete_recipe_ingredient_link,
    update_recipe_ingredient_link,
    # NEW (Option A)
    cached_list_recipe_seasons,
    set_recipe_seasons,
)
from app.lib.ui import set_full_page_background, load_css
from app.lib.brand import sidebar_brand

# -----------------------------
# Page config + styling
# -----------------------------
st.set_page_config(
    page_title="My Space",
    page_icon="👤",
    layout="wide",
    initial_sidebar_state="expanded",
)
set_full_page_background("app/static/bg_my_space.jpg")
init_session()
load_css()
sidebar_brand()

st.title("👤 My Space")

if not is_logged_in():
    st.warning("Please log in via Home.")
    st.stop()

token = st.session_state.session.access_token
user = st.session_state.session.user
user_id = user.id

# Role (use session_state if already set)
if st.session_state.get("role") is None:
    st.session_state.role = get_my_role(token, user_id)

role = st.session_state.role
can_edit = (role == "editor")

# -----------------------------
# Header badges
# -----------------------------
st.markdown(
    f"<span class='badge'>Signed in as: {user.email}</span> "
    f"<span class='badge'>Role: {role}</span>",
    unsafe_allow_html=True,
)

if not can_edit:
    st.info("You are a **reader**. You can browse recipes, but only **editors** can edit or delete.")

# -----------------------------
# Load data
# -----------------------------
recipes = cached_list_my_recipes(token, user_id)

if not recipes:
    st.info("You don't have any recipes yet. Go to **Add Recipe** to create one.")
    st.stop()

df = pd.DataFrame(recipes)

# Ensure columns exist (Option A: no 'season' column anymore)
for col in ["id","name","servings","prep_minutes","cook_minutes","total_minutes","instructions","notes","created_at","updated_at"]:
    if col not in df.columns:
        df[col] = None

# -----------------------------
# Load seasons (Option A)
# -----------------------------
season_rows = cached_list_recipe_seasons(token)
df_seasons = pd.DataFrame(season_rows)

if df_seasons.empty:
    seasons_by_recipe = {}
else:
    seasons_by_recipe = (
        df_seasons.groupby("recipe_id")["season"]
        .apply(lambda s: sorted(set(s.tolist())))
        .to_dict()
    )

# For display
df["seasons"] = df["id"].map(lambda rid: seasons_by_recipe.get(rid, []))
df["seasons_str"] = df["seasons"].map(lambda xs: ", ".join(xs) if xs else "—")

# Stats
total = len(df)
avg_time = (
    int(df["total_minutes"].dropna().astype(int).mean())
    if "total_minutes" in df.columns and not df["total_minutes"].dropna().empty
    else 0
)

# -----------------------------
# Top dashboard row
# -----------------------------
top1, top2, top3 = st.columns([2, 2, 1])
with top1:
    st.markdown(
        f"""
        <div class="card">
          <h3 style="margin:0">📚 {total}</h3>
          <p style="margin:6px 0 0">My recipes</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
with top2:
    st.markdown(
        f"""
        <div class="card">
          <h3 style="margin:0">⏱️ {avg_time} min</h3>
          <p style="margin:6px 0 0">Average total time</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
with top3:
    if st.button("🔄 Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.divider()

# -----------------------------
# Two-column main layout
# -----------------------------
left, right = st.columns([1.15, 1.85], gap="large")

# ===== Left: Recipe picker + quick preview =====
with left:
    st.subheader("Your recipes")

    # Search + select
    df["name_clean"] = df["name"].fillna("").astype(str)
    search = st.text_input("Search", value="", placeholder="Type to filter…")

    df_pick = df.copy()
    if search.strip():
        df_pick = df_pick[df_pick["name_clean"].str.lower().str.contains(search.strip().lower())]

    names = sorted(df_pick["name_clean"].unique().tolist())
    if not names:
        st.info("No match.")
        st.stop()

    selected_name = st.selectbox("Select a recipe", names)

    candidates = df_pick[df_pick["name_clean"] == selected_name].copy()
    candidates["created_date"] = candidates["created_at"].astype(str).str[:10].fillna("")

    if len(candidates) > 1:
        selected_date = st.selectbox("Pick version (date)", candidates["created_date"].unique().tolist())
        chosen = candidates[candidates["created_date"] == selected_date].iloc[0]
    else:
        chosen = candidates.iloc[0]

    recipe_id = chosen["id"]
    row = chosen.to_dict()

    # Quick preview card
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown(f"### {row.get('name','')}")
    st.write(f"Seasons: **{row.get('seasons_str','—')}**")
    st.write(f"Servings: **{row.get('servings',1)}**")
    st.write(f"Total: **{row.get('total_minutes',0)} min**")
    st.caption(f"Created: {str(row.get('created_at'))[:19]}")
    st.caption(f"Updated: {str(row.get('updated_at'))[:19]}")
    st.markdown("</div>", unsafe_allow_html=True)

# ===== Right: Tabs (Edit / Ingredients / Danger) =====
with right:
    tab_edit, tab_ings, tab_danger = st.tabs(["✍️ Edit", "🧂 Ingredients", "⚠️ Danger zone"])

    # -------- Edit tab --------
    with tab_edit:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("Edit recipe")
        st.caption("Changes are saved to Supabase. Total minutes is computed automatically.")

        name = st.text_input("Name", value=row.get("name") or "", disabled=not can_edit)

        ALL_SEASONS = ["winter", "spring", "summer", "fall"]

        current_seasons = seasons_by_recipe.get(recipe_id, [])

        # Safety: drop any unexpected values
        current_seasons = [s for s in current_seasons if s in ALL_SEASONS]

        seasons = st.multiselect(
            "Seasons",
            ALL_SEASONS,
            default=current_seasons,
            disabled=not can_edit,
        )
        c1, c2, c3 = st.columns(3)
        with c1:
            servings = st.number_input("Servings", min_value=1, value=int(row.get("servings") or 1), step=1, disabled=not can_edit)
        with c2:
            prep = st.number_input("Prep (min)", min_value=0, value=int(row.get("prep_minutes") or 0), step=5, disabled=not can_edit)
        with c3:
            cook = st.number_input("Cook (min)", min_value=0, value=int(row.get("cook_minutes") or 0), step=5, disabled=not can_edit)

        st.caption(f"Total: **{int(prep) + int(cook)} min** (auto-computed in DB)")

        instructions = st.text_area("Instructions", value=row.get("instructions") or "", height=220, disabled=not can_edit)
        notes = st.text_area("Notes", value=row.get("notes") or "", height=120, disabled=not can_edit)

        if can_edit and st.button("💾 Save changes", use_container_width=True):
            update_recipe(token, recipe_id, {
                "name": name,
                "servings": int(servings),
                "prep_minutes": int(prep),
                "cook_minutes": int(cook),
                "instructions": instructions,
                "notes": notes,
            })
            set_recipe_seasons(token, recipe_id, seasons)

            st.cache_data.clear()
            st.success("Saved ✅")
            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("Preview")
        if row.get("instructions"):
            st.markdown("**Instructions**")
            st.markdown((row["instructions"] or "").replace("\n", "  \n"))
        if row.get("notes"):
            st.markdown("**Notes**")
            st.markdown((row["notes"] or "").replace("\n", "  \n"))
        st.markdown("</div>", unsafe_allow_html=True)

    # -------- Ingredients tab --------
    with tab_ings:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("Ingredients")
        links = cached_get_recipe_ingredients(token, recipe_id)

        if not links:
            st.info("No ingredients linked yet.")
            df_links = pd.DataFrame(columns=["ingredient_id", "name", "quantity", "unit", "comment"])
        else:
            rows_links = []
            for link in links:
                rows_links.append({
                    "ingredient_id": link.get("ingredient_id"),
                    "name": (link.get("ingredients") or {}).get("name", ""),
                    "quantity": link.get("quantity") or "",
                    "unit": link.get("unit") or "",
                    "comment": link.get("comment") or "",
                })
            df_links = pd.DataFrame(rows_links)

        st.dataframe(df_links[["name","quantity","unit","comment"]], hide_index=True, width="stretch")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("Update / remove")
        st.caption("Pick one ingredient line to edit.")

        if df_links.empty:
            st.info("Nothing to edit yet.")
        else:
            pick = st.selectbox("Ingredient", df_links["name"].tolist())
            line = df_links[df_links["name"] == pick].iloc[0].to_dict()
            ing_id = line["ingredient_id"]

            q = st.text_input("Quantity", value=line.get("quantity",""), disabled=not can_edit)
            u = st.text_input("Unit", value=line.get("unit",""), disabled=not can_edit)
            c = st.text_input("Comment", value=line.get("comment",""), disabled=not can_edit)

            b1, b2 = st.columns(2)
            with b1:
                if can_edit and st.button("Save ingredient line", use_container_width=True):
                    update_recipe_ingredient_link(token, recipe_id, ing_id, {"quantity": q, "unit": u, "comment": c})
                    st.cache_data.clear()
                    st.success("Updated ✅")
                    st.rerun()
            with b2:
                if can_edit and st.button("Remove ingredient", use_container_width=True):
                    delete_recipe_ingredient_link(token, recipe_id, ing_id)
                    st.cache_data.clear()
                    st.success("Removed ✅")
                    st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("➕ Add ingredient")
        all_ings = cached_list_ingredients(token)
        ing_names = [x["name"] for x in all_ings]

        mode = st.radio("Pick mode", ["Choose existing", "Create new"], horizontal=True)

        if mode == "Choose existing":
            chosen_ing = st.selectbox("Ingredient", ["(select)"] + ing_names, index=0)
            new_name = ""
        else:
            new_name = st.text_input("New ingredient name", value="")
            chosen_ing = "(select)"

        colx, coly, colz = st.columns(3)
        with colx:
            qty = st.text_input("Quantity (optional)", value="")
        with coly:
            unit = st.text_input("Unit (optional)", value="")
        with colz:
            comment = st.text_input("Comment (optional)", value="")

        if can_edit and st.button("Add to recipe", use_container_width=True):
            if mode == "Choose existing":
                if chosen_ing == "(select)":
                    st.error("Please select an ingredient.")
                    st.stop()
                ing = find_ingredient_by_name(token, chosen_ing)
                ing_id = ing["id"]
            else:
                clean = (new_name or "").strip()
                if not clean:
                    st.error("Please type a name for the new ingredient.")
                    st.stop()
                created = create_ingredient(token, clean)
                ing_id = created["id"]

            add_recipe_ingredient(token, {
                "recipe_id": recipe_id,
                "ingredient_id": ing_id,
                "quantity": qty or None,
                "unit": unit or None,
                "comment": comment or None,
            })
            st.cache_data.clear()
            st.success("Added ✅")
            st.rerun()

        if not can_edit:
            st.caption("Only editors can edit ingredients.")

        st.markdown("</div>", unsafe_allow_html=True)

    # -------- Danger tab --------
    with tab_danger:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("Delete recipe")

        if not can_edit:
            st.info("Only editors can delete recipes.")
        else:
            confirm = st.checkbox("I understand this is permanent.")
            if st.button("🗑️ Delete recipe", disabled=not confirm, use_container_width=True):
                delete_recipe(token, recipe_id)
                st.cache_data.clear()
                st.success("Deleted ✅")
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)
