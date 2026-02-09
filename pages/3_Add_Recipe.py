import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from app.lib.session import init_session, is_logged_in
from app.lib.repos import (
    get_my_role,
    list_ingredients,
    create_ingredient,
    find_ingredient_by_name,
    create_recipe,
    add_recipe_ingredient,
    # Option A (join table)
    set_recipe_seasons,
)
from app.lib.ui import set_full_page_background, load_css
from app.lib.brand import sidebar_brand


# =========================
# Helpers
# =========================
def normalize_single_row(obj):
    """Supabase/PostgREST sometimes returns a list of rows. Normalize to dict."""
    if isinstance(obj, list):
        return obj[0] if obj else {}
    return obj or {}


def validate_before_create(recipe_name: str, seasons: list, ingredient_lines: list) -> list[str]:
    """Return a list of human-readable problems. Empty list = ok."""
    problems = []

    if not (recipe_name or "").strip():
        problems.append("Recipe name is required.")

    if not seasons:
        problems.append("Please select at least one season.")

    if not ingredient_lines:
        problems.append("Add at least one ingredient line.")
    else:
        bad = [
            i for i, ln in enumerate(ingredient_lines, start=1)
            if not (ln.get("name") or "").strip()
        ]
        if bad:
            problems.append(f"Ingredient line(s) missing a name: {', '.join(map(str, bad))}.")

    return problems


# =========================
# Page setup
# =========================
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

# Flash success (survives rerun)
if st.session_state.get("flash_success"):
    st.success(st.session_state.pop("flash_success"))

st.info(
    "How it works:\n"
    "- Fill in the **recipe details** (name, seasons, servings, times, instructions).\n"
    "- Add your **ingredients line by line** (quantity + unit + optional comment).\n"
    "- For each ingredient, you can either **select an existing one** from the list, "
    "or **create a new ingredient** if it doesn’t exist yet.\n"
    "- When you click **Create recipe now**, the recipe is saved, seasons are linked, "
    "and ingredients are automatically created (if needed) and attached to the recipe."
)

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


# =========================
# 1) Recipe form
# =========================
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

# ✅ Servings + Prep + Cook in one row
colS, colP, colK = st.columns(3)
with colS:
    servings = st.number_input("Servings", min_value=1, step=1, value=4)
with colP:
    prep = st.number_input("Prep time (minutes)", min_value=0, step=5, value=0)
with colK:
    cook = st.number_input("Cook time (minutes)", min_value=0, step=5, value=0)

instructions = st.text_area("Instructions", height=180)
notes = st.text_area("Notes", height=100)

st.divider()

# =========================
# 2) Ingredients UI
# =========================
st.subheader("2) Ingredients (add lines)")

ingredients = list_ingredients(token)
existing_names = [i["name"] for i in ingredients]
name_to_id = {i["name"]: i["id"] for i in ingredients}

left, right = st.columns([2, 1])

with left:
    mode = st.radio(
        "Choose ingredient input mode",
        ["Select existing", "Create new"],
        horizontal=True
    )

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

# =========================
# 3) Create (server-side writes)
# =========================
st.subheader("3) Create")

create_btn = st.button("✅ Create recipe now")

if create_btn:
    # 0) Validate BEFORE any DB writes
    problems = validate_before_create(name, seasons, st.session_state.ingredient_lines)
    if problems:
        st.warning("Please fix the following before creating the recipe:")
        for p in problems:
            st.write(f"- {p}")
        st.stop()

    created_recipe_id = None
    seasons_set = False
    linked_ingredients = []

    # 1) Create recipe
    try:
        recipe = create_recipe(token, {
            "name": name.strip(),
            "servings": int(servings),  # ✅ NEW
            "prep_minutes": int(prep),
            "cook_minutes": int(cook),
            "instructions": instructions.strip() or None,
            "notes": notes.strip() or None,
            "created_by": user_id,  # required by your RLS policy
        })
    except Exception as e:
        st.error("Could not create the recipe (database error).")
        st.exception(e)
        st.stop()

    recipe = normalize_single_row(recipe)
    created_recipe_id = recipe.get("id")

    if not created_recipe_id:
        st.error("Recipe creation failed: no recipe id returned.")
        st.code(repr(recipe))
        st.stop()

    # 2) Set seasons (Option A join table)
    try:
        set_recipe_seasons(token, created_recipe_id, seasons)
        seasons_set = True
    except Exception as e:
        st.error("Recipe was created, but setting seasons failed.")
        st.write("Nothing was deleted automatically.")
        st.write(f"- Recipe record: ✅ created (id: {created_recipe_id})")
        st.write("- Seasons: ❌ not set")
        st.write("- Ingredient links: 0")
        st.exception(e)
        st.info("You can fix this in **My Space** by editing the recipe seasons.")
        st.stop()

    # 3) Ensure ingredients exist, then link
    cached_ids = dict(name_to_id)

    try:
        for line in st.session_state.ingredient_lines:
            ing_name = (line.get("name") or "").strip()
            if not ing_name:
                raise RuntimeError("One ingredient line is missing a name.")

            ing_id = cached_ids.get(ing_name)
            if not ing_id:
                try:
                    created = create_ingredient(token, ing_name)
                    created = normalize_single_row(created)
                    ing_id = created.get("id")
                except Exception:
                    existing = find_ingredient_by_name(token, ing_name)
                    existing = normalize_single_row(existing)
                    ing_id = existing.get("id") if existing else None

                if not ing_id:
                    raise RuntimeError(f"Could not create or find ingredient: '{ing_name}'")

                cached_ids[ing_name] = ing_id

            add_recipe_ingredient(token, {
                "recipe_id": created_recipe_id,
                "ingredient_id": ing_id,
                "quantity": line.get("quantity"),
                "unit": line.get("unit"),
                "comment": line.get("comment"),
            })
            linked_ingredients.append(ing_name)

    except Exception as e:
        st.error("Recipe creation did not fully complete (ingredients step).")
        st.write("Nothing was deleted automatically. Here’s what succeeded:")
        st.write(f"- Recipe record: ✅ created (id: {created_recipe_id})")
        st.write(f"- Seasons: {'✅ set' if seasons_set else '❌ not set'}")
        st.write(f"- Ingredient links created: {len(linked_ingredients)}")
        if linked_ingredients:
            st.write(f"  - Linked: {', '.join(linked_ingredients)}")
        st.write("Error details:")
        st.exception(e)
        st.info("Fix the issue and edit the recipe in **My Space** to finish linking ingredients.")
        st.stop()

    # Success
    st.cache_data.clear()
    st.session_state.flash_success = "Recipe created ✅"
    reset_ingredient_lines()
    st.rerun()
