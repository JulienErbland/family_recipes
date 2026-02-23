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
from app.lib.fr_trans import season_label_fr

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
        problems.append("Le nom de la recette est obligatoire.")

    if not seasons:
        problems.append("Merci de sélectionner au moins une saison.")

    if not ingredient_lines:
        problems.append("Ajoute au moins une ligne d’ingrédient.")
    else:
        bad = [
            i for i, ln in enumerate(ingredient_lines, start=1)
            if not (ln.get("name") or "").strip()
        ]
        if bad:
            problems.append(f"Ligne(s) d’ingrédient sans nom : {', '.join(map(str, bad))}.")

    return problems


def remove_ingredient_line(idx: int):
    """Remove one ingredient line by its 0-based index."""
    if 0 <= idx < len(st.session_state.ingredient_lines):
        st.session_state.ingredient_lines.pop(idx)


# =========================
# Page setup
# =========================
st.set_page_config(
    page_title="Ajouter une recette",
    page_icon="➕",
    layout="wide",
    initial_sidebar_state="expanded",
)
set_full_page_background("app/static/bg_add_recipe.jpg")
init_session()
load_css()
sidebar_brand()

st.title("➕ Ajouter une recette")

# Flash success (survives rerun)
if st.session_state.get("flash_success"):
    st.success(st.session_state.pop("flash_success"))

st.info(
    "Comment ça marche :\n"
    "- Remplis les **détails de la recette** (nom, saisons, portions, temps, instructions).\n"
    "- Ajoute les **ingrédients ligne par ligne** (quantité + unité + commentaire optionnel).\n"
    "- Pour chaque ingrédient, tu peux soit **en choisir un existant** dans la liste, "
    "soit **en créer un nouveau** s’il n’existe pas encore.\n"
    "- Quand tu cliques sur **Créer la recette**, la recette est enregistrée, les saisons sont liées, "
    "et les ingrédients sont automatiquement créés (si besoin) puis associés à la recette."
)

if not is_logged_in():
    st.warning("Merci de te connecter via Accueil.")
    st.stop()

token = st.session_state.session.access_token
user_id = st.session_state.session.user.id

# Load role if needed
if "role" not in st.session_state or st.session_state.role is None:
    st.session_state.role = get_my_role(token, user_id)

if st.session_state.role != "editor":
    st.error("Tu es en lecture seule (lecteur). Tu ne peux pas ajouter de recettes.")
    st.stop()

# ---------- Session state for ingredient lines ----------
st.session_state.setdefault("ingredient_lines", [])  # list[dict]


def reset_ingredient_lines():
    st.session_state.ingredient_lines = []


# =========================
# 1) Recipe form
# =========================
st.subheader("1) Détails de la recette")

colA, colB, colC = st.columns([2, 1, 1])

with colA:
    name = st.text_input("Nom de la recette *")

with colB:
    ALL_SEASONS = ["winter", "spring", "summer", "fall"]
    seasons = st.multiselect(
        "Saisons *",
        ALL_SEASONS,
        default=[],
        format_func=season_label_fr,  # UI en FR (valeurs DB en EN)
    )

with colC:
    st.caption("Le temps total est calculé automatiquement (prépa + cuisson).")

# Servings + Prep + Cook
colS, colP, colK = st.columns(3)
with colS:
    servings = st.number_input("Portions", min_value=1, step=1, value=4)
with colP:
    prep = st.number_input("Temps de préparation (minutes)", min_value=0, step=5, value=0)
with colK:
    cook = st.number_input("Temps de cuisson (minutes)", min_value=0, step=5, value=0)

instructions = st.text_area("Instructions", height=180)
notes = st.text_area("Notes", height=100)

st.divider()

# =========================
# 2) Ingredients UI
# =========================
st.subheader("2) Ingrédients")

ingredients = list_ingredients(token)
existing_names = [i["name"] for i in ingredients]
name_to_id = {i["name"]: i["id"] for i in ingredients}

left, right = st.columns([2, 1])

with left:
    mode = st.radio(
        "Mode d’ajout",
        ["Choisir un ingrédient existant", "Créer un nouvel ingrédient"],
        horizontal=True
    )

    if mode == "Choisir un ingrédient existant":
        if not existing_names:
            st.info("Aucun ingrédient pour l’instant. Passe sur « Créer un nouvel ingrédient » pour ajouter les premiers.")
            selected_name = None
        else:
            selected_name = st.selectbox("Ingrédient", existing_names, index=0)
        new_name = None
    else:
        selected_name = None
        new_name = st.text_input("Nom du nouvel ingrédient")

    qty = st.text_input("Quantité (ex. 200, 1/2)", key="qty")
    unit = st.text_input("Unité (ex. g, mL, cuillère)", key="unit")
    comment = st.text_input("Commentaire (optionnel)", key="comment")

    add_line = st.button("➕ Ajouter l’ingrédient")

with right:
    st.markdown("### Ingrédients ajoutés")
    if not st.session_state.ingredient_lines:
        st.write("_Aucun pour l’instant_")
    else:
        for idx, line in enumerate(st.session_state.ingredient_lines):
            q = (line.get("quantity") or "")
            u = (line.get("unit") or "")
            c = line.get("comment")
            c_txt = f" ({c})" if c else ""

            col_text, col_btn = st.columns([8, 2])
            with col_text:
                st.write(f"**{idx+1}. {line['name']}** {q} {u}{c_txt}")
            with col_btn:
                if st.button("🗑️ Retirer", key=f"rm_ing_line_{idx}", width="stretch"):
                    remove_ingredient_line(idx)
                    st.rerun()

        st.write("")
        if st.button("🧹 Tout vider", key="clear_all_ing_lines", width="stretch"):
            reset_ingredient_lines()
            st.rerun()

# Handle adding an ingredient line (client-side only)
if add_line:
    if mode == "Choisir un ingrédient existant":
        if not selected_name:
            st.error("Sélectionne d’abord un ingrédient.")
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
            st.error("Le nom du nouvel ingrédient est obligatoire.")
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
st.subheader("3) Création")

create_btn = st.button("✅ Créer la recette")

if create_btn:
    # 0) Validate BEFORE any DB writes
    problems = validate_before_create(name, seasons, st.session_state.ingredient_lines)
    if problems:
        st.warning("Merci de corriger les points suivants avant de créer la recette :")
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
            "servings": int(servings),
            "prep_minutes": int(prep),
            "cook_minutes": int(cook),
            "instructions": instructions.strip() or None,
            "notes": notes.strip() or None,
            "created_by": user_id,  # required by your RLS policy
        })
    except Exception as e:
        st.error("Impossible de créer la recette (erreur base de données).")
        st.exception(e)
        st.stop()

    recipe = normalize_single_row(recipe)
    created_recipe_id = recipe.get("id")

    if not created_recipe_id:
        st.error("Échec de la création : aucun identifiant de recette n’a été renvoyé.")
        st.code(repr(recipe))
        st.stop()

    # 2) Set seasons (Option A join table)
    try:
        set_recipe_seasons(token, created_recipe_id, seasons)
        seasons_set = True
    except Exception as e:
        st.error("La recette a été créée, mais l’association des saisons a échoué.")
        st.write("Rien n’a été supprimé automatiquement.")
        st.write(f"- Recette : ✅ créée (id : {created_recipe_id})")
        st.write("- Saisons : ❌ non définies")
        st.write("- Associations d’ingrédients : 0")
        st.exception(e)
        st.info("Tu peux corriger ça dans **Mon espace** en modifiant les saisons de la recette.")
        st.stop()

    # 3) Ensure ingredients exist, then link
    cached_ids = dict(name_to_id)

    try:
        for line in st.session_state.ingredient_lines:
            ing_name = (line.get("name") or "").strip()
            if not ing_name:
                raise RuntimeError("Une ligne d’ingrédient n’a pas de nom.")

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
                    raise RuntimeError(f"Impossible de créer ou de trouver l’ingrédient : '{ing_name}'")

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
        st.error("La création de la recette ne s’est pas terminée correctement (étape ingrédients).")
        st.write("Rien n’a été supprimé automatiquement. Voici ce qui a réussi :")
        st.write(f"- Recette : ✅ créée (id : {created_recipe_id})")
        st.write(f"- Saisons : {'✅ définies' if seasons_set else '❌ non définies'}")
        st.write(f"- Associations d’ingrédients créées : {len(linked_ingredients)}")
        if linked_ingredients:
            st.write(f"  - Associés : {', '.join(linked_ingredients)}")
        st.write("Détails de l’erreur :")
        st.exception(e)
        st.info("Corrige le problème puis modifie la recette dans **Mon espace** pour terminer l’association des ingrédients.")
        st.stop()

    # Success
    st.cache_data.clear()
    st.session_state.flash_success = "Recette créée ✅"
    reset_ingredient_lines()
    st.rerun()