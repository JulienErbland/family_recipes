import streamlit as st
import pandas as pd



from app.lib.session import init_session, is_logged_in
from app.lib.repos import (
    get_my_role,
    list_my_recipes,
    update_recipe,
    delete_recipe,
    list_ingredients,
    find_ingredient_by_name,
    create_ingredient,
    get_recipe_ingredients,
    add_recipe_ingredient,
    delete_recipe_ingredient_link,
    update_recipe_ingredient_link,
)
from app.lib.ui import set_page_background, set_full_page_background

st.set_page_config(
    page_title="My Space",
    page_icon="👤",
    layout="wide",
    initial_sidebar_state="expanded",
)
set_full_page_background("app/static/bg_my_space.png")
init_session()

from app.lib.ui import load_css
load_css()

from app.lib.brand import sidebar_brand
sidebar_brand()


st.title("👤 My Space")
if not is_logged_in():
    st.warning("Please log in via Home.")
    st.stop()


st.write("")

token = st.session_state.session.access_token
user = st.session_state.session.user
user_id = user.id

role = st.session_state.role = get_my_role(token, user_id)
can_edit = (role == "editor")

st.markdown(f"<span class='badge'>Signed in as: {user.email}</span> <span class='badge'>Role: {role}</span>", unsafe_allow_html=True)
st.write("")

if not can_edit:
    st.info("You are a **reader**. You can browse recipes, but only **editors** can edit or delete.")
    # Still show their recipes read-only


# --------------------------------------------

@st.cache_data(ttl=20)
def load_my_recipes(tok: str, uid: str):
    return list_my_recipes(tok, uid)

recipes = load_my_recipes(token, user_id)

df_stats = pd.DataFrame(recipes)
total = len(df_stats)

avg_time = (
    int(df_stats["total_minutes"].dropna().astype(int).mean())
    if "total_minutes" in df_stats and not df_stats["total_minutes"].dropna().empty
    else 0
)

st.markdown(
    f"""
    <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(180px,1fr)); gap:14px; margin-bottom:18px;">
        <div class="card">
            <h3 style="margin:0">📚 {total}</h3>
            <p style="margin:4px 0 0">My recipes</p>
        </div>
        <div class="card">
            <h3 style="margin:0">⏱️ {avg_time} min</h3>
            <p style="margin:4px 0 0">Average total time</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)



top_left, top_right = st.columns([3, 1])
with top_left:
    st.subheader(f"My recipes ({len(recipes)})")
with top_right:
    if st.button("🔄 Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

if not recipes:
    st.info("You don't have any recipes yet. Go to **Add Recipe** to create one.")
    st.stop()

df = pd.DataFrame(recipes)
for col in ["id","name","season","servings","prep_minutes","cook_minutes","total_minutes","instructions","notes","created_at","updated_at"]:
    if col not in df.columns:
        df[col] = None

# Select recipe (disambiguate duplicates)
# Select recipe (no IDs shown)
df["name_clean"] = df["name"].fillna("")

# First selector: recipe name only
selected_name = st.selectbox(
    "Select a recipe to manage:",
    sorted(df["name_clean"].unique().tolist())
)

candidates = df[df["name_clean"] == selected_name]

# If duplicates exist, disambiguate by date (still no IDs)
if len(candidates) > 1:
    candidates = candidates.copy()
    candidates["created_date"] = candidates["created_at"].astype(str).str[:10].fillna("")

    selected_date = st.selectbox(
        "Pick the version (by creation date):",
        candidates["created_date"].unique().tolist()
    )

    chosen = candidates[candidates["created_date"] == selected_date].iloc[0]
else:
    chosen = candidates.iloc[0]

recipe_id = chosen["id"]
row = chosen.to_dict()


st.divider()

left, right = st.columns([3, 2])

# -----------------------
# EDIT PANEL
# -----------------------
with left:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("✍️ Edit recipe")

    st.caption("Fields are saved to Supabase. Total minutes is computed automatically.")

    name = st.text_input("Name", value=row.get("name") or "", disabled=not can_edit)
    season = st.selectbox(
        "Season",
        ["all", "winter", "spring", "summer", "fall"],
        index=["all","winter","spring","summer","fall"].index(row.get("season") or "all"),
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
            "season": season,
            "servings": int(servings),
            "prep_minutes": int(prep),
            "cook_minutes": int(cook),
            "instructions": instructions,
            "notes": notes,
        })
        st.cache_data.clear()
        st.success("Recipe updated ✅")
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    st.write("")

    # -----------------------
    # INGREDIENT MANAGEMENT
    # -----------------------
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("🧂 Ingredients (manage)")

    links = get_recipe_ingredients(token, recipe_id)

    if not links:
        st.info("No ingredients linked yet.")
    else:
        for link in links:
            ing_name = (link.get("ingredients") or {}).get("name", "")
            ing_id = link.get("ingredient_id")

            with st.expander(f"{ing_name}"):
                q = st.text_input("Quantity", value=link.get("quantity") or "", key=f"q_{recipe_id}_{ing_id}", disabled=not can_edit)
                u = st.text_input("Unit", value=link.get("unit") or "", key=f"u_{recipe_id}_{ing_id}", disabled=not can_edit)
                c = st.text_input("Comment", value=link.get("comment") or "", key=f"c_{recipe_id}_{ing_id}", disabled=not can_edit)

                b1, b2 = st.columns(2)
                with b1:
                    if can_edit and st.button("Update", key=f"upd_{recipe_id}_{ing_id}", use_container_width=True):
                        update_recipe_ingredient_link(token, recipe_id, ing_id, {"quantity": q, "unit": u, "comment": c})
                        st.success("Updated ✅")
                        st.rerun()
                with b2:
                    if can_edit and st.button("Remove", key=f"del_{recipe_id}_{ing_id}", use_container_width=True):
                        delete_recipe_ingredient_link(token, recipe_id, ing_id)
                        st.success("Removed ✅")
                        st.rerun()

    st.divider()
    st.subheader("➕ Add ingredient")

    all_ings = list_ingredients(token)
    ing_names = [x["name"] for x in all_ings]

    mode = st.radio("Pick mode", ["Choose existing", "Create new"], horizontal=True)

    if mode == "Choose existing":
        chosen = st.selectbox("Ingredient", ["(select)"] + ing_names, index=0)
        new_name = None
    else:
        new_name = st.text_input("New ingredient name", value="")

    colx, coly, colz = st.columns(3)
    with colx:
        qty = st.text_input("Quantity (optional)", value="")
    with coly:
        unit = st.text_input("Unit (optional)", value="")
    with colz:
        comment = st.text_input("Comment (optional)", value="")

    if can_edit and st.button("Add ingredient to recipe", use_container_width=True):
        if mode == "Choose existing":
            if chosen == "(select)":
                st.error("Please select an ingredient.")
                st.stop()
            ing = find_ingredient_by_name(token, chosen)
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
        st.success("Ingredient linked ✅")
        st.rerun()

    if not can_edit:
        st.caption("Only editors can edit ingredients.")

    st.markdown("</div>", unsafe_allow_html=True)

# -----------------------
# SIDE PANEL: DELETE + PREVIEW
# -----------------------
with right:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("🧹 Manage")

    st.write("**Info**")
    st.write(f"- Created: {str(row.get('created_at'))[:19]}")
    st.write(f"- Updated: {str(row.get('updated_at'))[:19]}")
    st.write(f"- Total: {row.get('total_minutes', 0)} min")

    st.divider()
    st.subheader("⚠️ Delete recipe")

    if not can_edit:
        st.info("Only editors can delete recipes.")
    else:
        confirm = st.checkbox("I understand this is permanent.")
        if st.button("🗑️ Delete", disabled=not confirm, use_container_width=True):
            delete_recipe(token, recipe_id)
            st.cache_data.clear()
            st.success("Recipe deleted ✅")
            st.rerun()

    st.divider()
    st.subheader("👀 Preview")
    st.markdown(f"### {row.get('name','')}")
    st.write(f"Season: **{row.get('season','all')}**")
    st.write(f"Servings: **{row.get('servings',1)}**")
    st.write(f"Prep: **{row.get('prep_minutes',0)}** | Cook: **{row.get('cook_minutes',0)}** | Total: **{row.get('total_minutes',0)}**")

    if row.get("instructions"):
        st.markdown("**Instructions**")
        st.markdown(row["instructions"].replace("\n", "  \n"))
    if row.get("notes"):
        st.markdown("**Notes**")
        st.write(row["notes"])

    st.markdown("</div>", unsafe_allow_html=True)
