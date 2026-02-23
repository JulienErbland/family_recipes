import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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
from app.lib.fr_trans import season_label_fr, seasons_label_fr, role_label_fr

# -----------------------------
# Page config + styling
# -----------------------------
st.set_page_config(
    page_title="Mon espace",
    page_icon="👤",
    layout="wide",
    initial_sidebar_state="expanded",
)
set_full_page_background("app/static/bg_my_space.jpg")
init_session()
load_css()
sidebar_brand()

st.title("👤 Mon espace")

st.info(
    "Comment fonctionne **Mon espace** :\n"
    "- Cette page affiche **uniquement tes propres recettes**.\n"
    "- Utilise **Recherche** pour retrouver rapidement une recette, puis sélectionne-la pour ouvrir l’éditeur.\n"
    "- Tu as trois onglets :\n"
    "  - **✍️ Modifier** : mettre à jour la recette (nom, saisons, portions, temps, instructions, notes).\n"
    "  - **🧂 Ingrédients** : voir toutes les lignes, **modifier/supprimer** une ligne existante, ou **en ajouter** une.\n"
    "  - **⚠️ Zone dangereuse** : supprimer définitivement la recette (confirmation requise).\n"
    "- Les rôles comptent :\n"
    "  - Les **éditeurs** peuvent enregistrer, modifier les ingrédients et supprimer des recettes.\n"
    "  - Les **lecteurs** peuvent tout consulter mais ne peuvent rien modifier.\n"
    "- Après un enregistrement ou une suppression, la page se rafraîchit automatiquement pour afficher les dernières données."
)

st.caption(
    "Astuce : les noms d’ingrédients doivent correspondre exactement — "
    "« Tomate » et « Tomates » seront considérés comme deux ingrédients différents."
)

if not is_logged_in():
    st.warning("Merci de te connecter via **Accueil**.")
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
    f"<span class='badge'>Connecté : {user.email}</span> "
    f"<span class='badge'>Rôle : {role_label_fr(role)}</span>",
    unsafe_allow_html=True,
)

if not can_edit:
    st.info("Tu es **lecteur**. Tu peux consulter les recettes, mais seuls les **éditeurs** peuvent modifier ou supprimer.")

# -----------------------------
# Load data
# -----------------------------
recipes = cached_list_my_recipes(token, user_id)
if not recipes:
    st.info("Tu n’as pas encore de recettes. Va sur **Ajouter une recette** pour en créer une.")
    st.stop()

df = pd.DataFrame(recipes)

# Ensure columns exist (Option A: no 'season' column anymore)
for col in [
    "id", "name", "servings", "prep_minutes", "cook_minutes", "total_minutes",
    "instructions", "notes", "created_at", "updated_at"
]:
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
        .apply(lambda s: sorted(set([x for x in s.tolist() if x])))
        .to_dict()
    )

df["seasons"] = df["id"].map(lambda rid: seasons_by_recipe.get(rid, []))
# ✅ UI: afficher en FR dans les résumés/tableaux
df["seasons_str"] = df["seasons"].map(lambda xs: seasons_label_fr(xs) if xs else "—")

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
          <p style="margin:6px 0 0">Mes recettes</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
with top2:
    st.markdown(
        f"""
        <div class="card">
          <h3 style="margin:0">⏱️ {avg_time} min</h3>
          <p style="margin:6px 0 0">Temps total moyen</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
with top3:
    if st.button("🔄 Rafraîchir", width="stretch"):
        st.cache_data.clear()
        st.rerun()

st.divider()

# -----------------------------
# Two-column main layout
# -----------------------------
left, right = st.columns([1.15, 1.85], gap="large")

# ===== Left: Recipe picker + quick preview =====
with left:
    st.subheader("Tes recettes")

    df["name_clean"] = df["name"].fillna("").astype(str)
    search = st.text_input("Recherche", value="", placeholder="Tape pour filtrer…")

    df_pick = df.copy()
    if search.strip():
        df_pick = df_pick[df_pick["name_clean"].str.lower().str.contains(search.strip().lower())]

    names = sorted(df_pick["name_clean"].unique().tolist())
    if not names:
        st.info("Aucun résultat.")
        st.stop()

    selected_name = st.selectbox("Sélectionner une recette", names)

    candidates = df_pick[df_pick["name_clean"] == selected_name].copy()
    candidates["created_date"] = candidates["created_at"].astype(str).str[:10].fillna("")

    if len(candidates) > 1:
        selected_date = st.selectbox(
            "Choisir la version (date de création)",
            candidates["created_date"].unique().tolist()
        )
        chosen = candidates[candidates["created_date"] == selected_date].iloc[0]
    else:
        chosen = candidates.iloc[0]

    recipe_id = chosen["id"]
    row = chosen.to_dict()

    with st.container(border=True):
        st.markdown(f"### {row.get('name','')}")
        st.write(f"Saisons : **{seasons_label_fr(row.get('seasons', [])) or '—'}**")
        st.write(f"Portions : **{row.get('servings', 1)}**")
        st.write(f"Temps total : **{row.get('total_minutes', 0)} min**")
        st.caption(f"Créée : {str(row.get('created_at'))[:19]}")
        st.caption(f"Modifiée : {str(row.get('updated_at'))[:19]}")

# ===== Right: Tabs (Edit / Ingredients / Danger) =====
with right:
    tab_edit, tab_ings, tab_danger = st.tabs(["✍️ Modifier", "🧂 Ingrédients", "⚠️ Zone dangereuse"])

    # -------- Edit tab --------
    with tab_edit:
        with st.container(border=True):
            st.subheader("Modifier la recette")
            st.caption("Les changements sont enregistrés dans Supabase. Le temps total est calculé automatiquement.")

            name = st.text_input("Nom", value=row.get("name") or "", disabled=not can_edit)

            ALL_SEASONS = ["winter", "spring", "summer", "fall"]
            current_seasons = seasons_by_recipe.get(recipe_id, [])
            current_seasons = [s for s in current_seasons if s in ALL_SEASONS]

            seasons = st.multiselect(
                "Saisons",
                ALL_SEASONS,
                default=current_seasons,
                format_func=season_label_fr,
                disabled=not can_edit,
            )

            c1, c2, c3 = st.columns(3)
            with c1:
                servings = st.number_input(
                    "Portions",
                    min_value=1,
                    value=int(row.get("servings") or 1),
                    step=1,
                    disabled=not can_edit,
                )
            with c2:
                prep = st.number_input(
                    "Préparation (min)",
                    min_value=0,
                    value=int(row.get("prep_minutes") or 0),
                    step=5,
                    disabled=not can_edit,
                )
            with c3:
                cook = st.number_input(
                    "Cuisson (min)",
                    min_value=0,
                    value=int(row.get("cook_minutes") or 0),
                    step=5,
                    disabled=not can_edit,
                )

            st.caption(f"Temps total : **{int(prep) + int(cook)} min** (calculé automatiquement en base)")

            instructions = st.text_area(
                "Instructions",
                value=row.get("instructions") or "",
                height=220,
                disabled=not can_edit,
            )
            notes = st.text_area(
                "Notes",
                value=row.get("notes") or "",
                height=120,
                disabled=not can_edit,
            )

            if can_edit and st.button("💾 Enregistrer", width="stretch"):
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
                st.success("Enregistré ✅")
                st.rerun()

        with st.container(border=True):
            st.subheader("Aperçu")
            if row.get("instructions"):
                st.markdown("**Instructions**")
                st.markdown((row["instructions"] or "").replace("\n", "  \n"))
            if row.get("notes"):
                st.markdown("**Notes**")
                st.markdown((row["notes"] or "").replace("\n", "  \n"))

    # -------- Ingredients tab --------
    with tab_ings:
        with st.container(border=True):
            st.subheader("Ingrédients")
            links = cached_get_recipe_ingredients(token, recipe_id)

            if not links:
                st.info("Aucun ingrédient associé pour le moment.")
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

            st.dataframe(df_links[["name", "quantity", "unit", "comment"]], hide_index=True, width="stretch")

        with st.container(border=True):
            st.subheader("Modifier ou supprimer une ligne")
            st.caption("Choisis une ligne d’ingrédient à modifier.")

            if df_links.empty:
                st.info("Rien à modifier pour l’instant.")
            else:
                pick = st.selectbox("Ligne d’ingrédient", df_links["name"].tolist())
                line = df_links[df_links["name"] == pick].iloc[0].to_dict()
                ing_id = line["ingredient_id"]

                q = st.text_input("Quantité", value=line.get("quantity", ""), disabled=not can_edit)
                u = st.text_input("Unité", value=line.get("unit", ""), disabled=not can_edit)
                c = st.text_input("Commentaire (optionnel)", value=line.get("comment", ""), disabled=not can_edit)

                b1, b2 = st.columns(2)
                with b1:
                    if can_edit and st.button("Enregistrer la modification", width="stretch"):
                        update_recipe_ingredient_link(
                            token, recipe_id, ing_id,
                            {"quantity": q, "unit": u, "comment": c}
                        )
                        st.cache_data.clear()
                        st.success("Mis à jour ✅")
                        st.rerun()
                with b2:
                    if can_edit and st.button("Supprimer cette ligne", width="stretch"):
                        delete_recipe_ingredient_link(token, recipe_id, ing_id)
                        st.cache_data.clear()
                        st.success("Supprimé ✅")
                        st.rerun()

        with st.container(border=True):
            st.subheader("➕ Ajouter un ingrédient")
            all_ings = cached_list_ingredients(token)
            ing_names = [x["name"] for x in all_ings]

            mode = st.radio(
                "Mode",
                ["Choisir un ingrédient existant", "Créer un nouvel ingrédient"],
                horizontal=True
            )

            if mode == "Choisir un ingrédient existant":
                chosen_ing = st.selectbox("Ingrédient", ["(sélectionner)"] + ing_names, index=0)
                new_name = ""
            else:
                new_name = st.text_input("Nom du nouvel ingrédient", value="")
                chosen_ing = "(sélectionner)"

            colx, coly, colz = st.columns(3)
            with colx:
                qty = st.text_input(
                    "Quantité (optionnel)",
                    value="",
                    key=f"add_ing_qty_{recipe_id}",
                )
            with coly:
                unit = st.text_input(
                    "Unité (optionnel)",
                    value="",
                    key=f"add_ing_unit_{recipe_id}",
                )
            with colz:
                comment = st.text_input(
                    "Commentaire (optionnel)",
                    value="",
                    key=f"add_ing_comment_{recipe_id}",
                )

            if can_edit and st.button("Ajouter à la recette", width="stretch"):
                if mode == "Choisir un ingrédient existant":
                    if chosen_ing == "(sélectionner)":
                        st.error("Merci de sélectionner un ingrédient.")
                        st.stop()
                    ing = find_ingredient_by_name(token, chosen_ing)
                    ing_id = ing["id"]
                else:
                    clean = (new_name or "").strip()
                    if not clean:
                        st.error("Merci de saisir un nom pour le nouvel ingrédient.")
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
                st.success("Ajouté ✅")
                st.rerun()

            if not can_edit:
                st.caption("Seuls les éditeurs peuvent modifier les ingrédients.")

    # -------- Danger tab --------
    with tab_danger:
        with st.container(border=True):
            st.subheader("Supprimer la recette")

            if not can_edit:
                st.info("Seuls les éditeurs peuvent supprimer des recettes.")
            else:
                confirm = st.checkbox("Je comprends que cette action est définitive.")
                if st.button("🗑️ Supprimer la recette", disabled=not confirm, width="stretch"):
                    delete_recipe(token, recipe_id)
                    st.cache_data.clear()
                    st.success("Supprimé ✅")
                    st.rerun()