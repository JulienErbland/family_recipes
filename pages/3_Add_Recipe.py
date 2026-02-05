import streamlit as st

from app.lib.session import init_session, is_logged_in
from app.lib.repos import (
    get_my_role,
    list_ingredients,
    create_ingredient,
    find_ingredient_by_name,
    create_recipe,
    add_recipe_ingredient,
    # NEW (Option A)
    set_recipe_seasons,
)
from app.lib.ui import set_full_page_background, load_css
from app.lib.brand import sidebar_brand

st.set_page_config(
    page_title="Add Recipe",
    page_icon="➕",
    layout="wide",
    initial_sidebar_state="expanded",
)
set_full_page_background("app/static/bg_add_recipe.jpg")
init_session()
load_css()
sidebar_brand()

st.title("➕ Add a recipe")

if not is_logged_in():
    st.warning("Please log in via Home.")
    st.stop()

token = st.session_state.session.access_token
user_id = st.session_state.session.user.id

# Load role if needed
if "role" not in st.session_state or st.session_state.role is None:
    st.session_state.role = get_my_role(token, user_id)

if st.session_state.role != "editor":
    st.error("You are read-only (reader). You can't add recipes.")
    st.stop()

# ---------- Session state for ingredient lines ----------
st.session_state.setdefault("ingredient_lines", [])  # list[dict]

def reset_ingredient_lines():
    st.session_state.ingredient_lines = []

# ---------- Recipe form ----------
st.subheader("1) Recipe details")

colA, colB, colC = st.columns([2, 1, 1])

with colA:
    name = st.text_input("Recipe name *")

with colB:
    seasons = st.multiselect(
        "Seasons *",
        ["winter", "spring", "summer", "fall"],
        default=[],
    )

with colC:
    st.caption("Total time is computed automatically (prep + cook).")

col1, col2 = st.columns(2)
with col1:
    prep = st.number_input("Prep time (minutes)", min_value=0, step=5, value=0)
with col2:
    cook = st.number_input("Cook time (minutes)", min_value=0, step=5, value=0)

instructions = st.text_area("Instructions", height=180)
notes = st.text_area("Notes", height=100)

st.divider()

# ---------- Ingredients UI ----------
st.subheader("2) Ingredients (add lines)")

ingredients = list_ingredients(token)
existing_names = [i["name"] for i in ingredients]
name_to_id = {i["name"]: i["id"] for i in ingredients}

left, right = st.columns([2, 1])

with left:
    mode = st.radio("Choose ingredient input mode", ["Select existing", "Create new"], horizontal=True)

    if mode == "Select existing":
        if not existing_names:
            st.info("No ingredients yet. Switch to 'Create new' to add the first ones.")
            selected_name = None
        else:
            selected_name = st.selectbox("Ingredient", existing_names, index=0)
        new_name = None
    else:
        selected_name = None
        new_name = st.text_input("New ingredient name")

    qty = st.text_input("Quantity (e.g., 200, 1/2)", key="qty")
    unit = st.text_input("Unit (e.g., g, mL, spoon)", key="unit")
    comment = st.text_input("Comment (optional)", key="comment")

    add_line = st.button("➕ Add ingredient line")

with right:
    st.markdown("### Current ingredients")
    if not st.session_state.ingredient_lines:
        st.write("_None yet_")
    else:
        for idx, line in enumerate(st.session_state.ingredient_lines, start=1):
            q = (line.get("quantity") or "")
            u = (line.get("unit") or "")
            c = line.get("comment")
            c_txt = f" ({c})" if c else ""
            st.write(f"{idx}. **{line['name']}** {q} {u}{c_txt}")

        if st.button("🗑️ Clear ingredient list"):
            reset_ingredient_lines()
            st.rerun()

# Handle adding an ingredient line (client-side only)
if add_line:
    if mode == "Select existing":
        if not selected_name:
            st.error("Select an ingredient first.")
        else:
            st.session_state.ingredient_lines.append({
                "name": selected_name,
                "is_new": False,
                "quantity": qty.strip() or None,
                "unit": unit.strip() or None,
                "comment": comment.strip() or None,
            })
            st.rerun()
    else:
        nm = (new_name or "").strip()
        if not nm:
            st.error("New ingredient name is required.")
        else:
            st.session_state.ingredient_lines.append({
                "name": nm,
                "is_new": True,
                "quantity": qty.strip() or None,
                "unit": unit.strip() or None,
                "comment": comment.strip() or None,
            })
            st.rerun()

st.divider()

# ---------- Create recipe (server-side writes) ----------
st.subheader("3) Create")

create_btn = st.button("✅ Create recipe now")

if create_btn:
    if not name.strip():
        st.error("Recipe name is required.")
        st.stop()

    if not seasons:
        st.error("Please select at least one season.")
        st.stop()

    if len(st.session_state.ingredient_lines) == 0:
        st.error("Add at least one ingredient line.")
        st.stop()

    # 1) Create recipe (Option A: NO season field)
    recipe = create_recipe(token, {
        "name": name.strip(),
        "prep_minutes": int(prep),
        "cook_minutes": int(cook),
        "instructions": instructions.strip() or None,
        "notes": notes.strip() or None,
        "created_by": user_id,  # required by your RLS policy
    })

    recipe_id = recipe.get("id")
    if not recipe_id:
        st.error("Recipe creation failed (no recipe id returned).")
        st.stop()

    # 2) Set seasons (Option A join table)
    try:
        set_recipe_seasons(token, recipe_id, seasons)
    except Exception as e:
        st.error(f"Recipe created but setting seasons failed: {e}")
        st.stop()

    # 3) Ensure ingredients exist, then link
    cached_ids = dict(name_to_id)  # start with existing ids

    for line in st.session_state.ingredient_lines:
        ing_name = line["name"].strip()

        ing_id = cached_ids.get(ing_name)
        if not ing_id:
            # Try create; if already exists, fetch it
            try:
                created = create_ingredient(token, ing_name)
                ing_id = created.get("id")
            except Exception:
                existing = find_ingredient_by_name(token, ing_name)
                ing_id = existing.get("id") if existing else None

            if not ing_id:
                st.error(f"Could not create or find ingredient: {ing_name}")
                st.stop()

            cached_ids[ing_name] = ing_id

        add_recipe_ingredient(token, {
            "recipe_id": recipe_id,
            "ingredient_id": ing_id,
            "quantity": line.get("quantity"),
            "unit": line.get("unit"),
            "comment": line.get("comment"),
        })

    st.success("Recipe created ✅")
    st.cache_data.clear()
    reset_ingredient_lines()
    st.rerun()
