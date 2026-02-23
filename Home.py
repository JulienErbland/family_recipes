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
from app.lib.fr_trans import role_label_fr, season_label_fr  # ✅ add season_label_fr for FR chart labels

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
        Le carnet de recettes de la Tribu Erbland (et plus)
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.info(
    "Bienvenue sur **La cuisine de la Madre** 👋\n\n"
    "- Ici, c’est le **carnet de recettes de la famille** : on partage, on découvre et on garde les meilleures.\n"
    "- Utilise **Parcourir** pour explorer les recettes par **saison** et par **ingrédients**.\n"
    "- Ton **rôle** définit ce que tu peux faire :\n"
    "  - **Lecteur** → parcourir et consulter les recettes.\n"
    "  - **Éditeur** → créer, modifier et supprimer des recettes.\n"
    "- Si tu es lecteur et que tu as le **code éditeur**, tu peux passer éditeur directement depuis cette page.\n\n"
    "Utilise la **navigation à gauche** pour aller sur **Parcourir**, **Ajouter une recette** et **Mon espace**."
)

st.write("")


# =========================
# Not logged in
# =========================
if not is_logged_in():
    st.info("Connecte-toi via la barre latérale pour commencer.")
    c1, c2 = st.columns([1, 1])

    with c1:
        st.markdown(
            "<div class='card'><h3>✨ Parcourir</h3><p>Explore les recettes par saison et ingrédients.</p></div>",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            "<div class='card'><h3>🔐 Créer un compte</h3><p>Inscris-toi dans la barre latérale pour rejoindre le carnet de recettes.</p></div>",
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
    f"<span class='badge'>Connecté ✅</span>"
    f"<span class='badge'>Rôle : {role_label_fr(role)}</span>",
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
    with st.expander("🔑 Devenir éditeur"):
        st.write("Si tu as le code éditeur de la famille, saisis-le pour débloquer la modification des recettes.")
        code = st.text_input("Code éditeur", type="password", key="home_editor_code")

        if st.button("Passer en éditeur", width="stretch", key="home_upgrade_btn"):
            if not EDITOR_CODE:
                st.error("Le code éditeur n’est pas configuré sur le serveur (EDITOR_INVITE_CODE manquant).")
                st.stop()

            if code.strip() != EDITOR_CODE:
                st.error("Code incorrect.")
                st.stop()

            set_my_role(token, user_id, "editor")
            st.session_state.role = "editor"
            st.cache_data.clear()
            st.success("Tu es maintenant éditeur ✅")
            st.rerun()


# =========================
# Feature cards
# =========================
c1, c2, c3 = st.columns(3)

with c1:
    st.markdown(
        "<div class='card'><h3>📚 Parcourir</h3>"
        "<p>Filtre par saison, créateur et ingrédients — puis ouvre les détails.</p></div>",
        unsafe_allow_html=True,
    )

with c2:
    if is_editor:
        st.markdown(
            "<div class='card'><h3>✍️ Ajouter une recette</h3>"
            "<p>Crée une nouvelle recette et associe les ingrédients proprement.</p></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div class='card'><h3>✍️ Ajouter une recette</h3>"
            "<p>Il te faut le rôle <b>éditeur</b> pour créer/modifier des recettes.</p></div>",
            unsafe_allow_html=True,
        )

with c3:
    st.markdown(
        "<div class='card'><h3>👤 Mon espace</h3>"
        "<p>Retrouve tes recettes et gère-les (modifier / supprimer si éditeur).</p></div>",
        unsafe_allow_html=True,
    )

st.write("")
st.caption("Utilise les pages dans la navigation à gauche pour parcourir les recettes et gérer ton espace.")


# =========================
# Cookbook analytics
# =========================
st.divider()
st.markdown('<div class="home-analytics-title">📊 Statistiques du carnet</div>', unsafe_allow_html=True)


@st.cache_data(ttl=60, show_spinner=False)
def _load_home_stats(access_token: str):
    recipes_ = cached_list_recipes(access_token)
    links_ = cached_list_recipe_ingredients(access_token)
    seasons_ = cached_list_recipe_seasons(access_token)
    return recipes_ or [], links_ or [], seasons_ or []


with st.spinner("Chargement des statistiques…"):
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
    id_to_name[p["id"]] = full if full else "Inconnu"

df_recipes["creator_name"] = df_recipes["created_by"].map(lambda uid: id_to_name.get(uid, "Inconnu"))

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
    kpi("📚", str(total_recipes), "Nombre total de recettes")
with k2:
    kpi("🧂", str(unique_ingredients), "Ingrédients distincts")
with k3:
    kpi("🧾", str(total_links), "Lignes d’ingrédients (recettes)")
with k4:
    kpi("⏱️", f"{avg_time} min", "Temps total moyen")

st.write("")

# Charts
left, right = st.columns([1.15, 1.0], gap="large")

with left:
    with st.container(border=True):
        st.markdown("### Ingrédients les plus utilisés")
        if df_links.empty or "ingredients" not in df_links.columns:
            st.info("Pas encore de données d’utilisation des ingrédients.")
        else:
            ing_names = df_links["ingredients"].apply(lambda x: (x or {}).get("name", "")).replace("", pd.NA).dropna()
            top_ing = ing_names.value_counts().head(12).reset_index()
            top_ing.columns = ["ingredient", "count"]

            chart = (
                alt.Chart(top_ing)
                .mark_bar()
                .encode(
                    x=alt.X("count:Q", title="Utilisations"),
                    y=alt.Y("ingredient:N", sort="-x", title=None),
                    tooltip=["ingredient:N", "count:Q"],
                )
                .properties(height=320)
                .configure_view(strokeOpacity=0)
            )
            st.altair_chart(chart, width="stretch")

    with st.container(border=True):
        st.markdown("### Recettes par créateur")
        if df_recipes.empty:
            st.info("Aucune recette pour le moment.")
        else:
            top_creators = (
                df_recipes["creator_name"]
                .fillna("Inconnu")
                .value_counts()
                .head(10)
                .reset_index()
            )
            top_creators.columns = ["creator", "count"]

            chart = (
                alt.Chart(top_creators)
                .mark_bar()
                .encode(
                    x=alt.X("count:Q", title="Recettes"),
                    y=alt.Y("creator:N", sort="-x", title=None),
                    tooltip=["creator:N", "count:Q"],
                )
                .properties(height=280)
                .configure_view(strokeOpacity=0)
            )
            st.altair_chart(chart, width="stretch")

with right:
    with st.container(border=True):
        st.markdown("### Recettes par saison")
        ALL_SEASONS = ["winter", "spring", "summer", "fall"]

        if df_seasons.empty or "season" not in df_seasons.columns:
            st.info("Aucune association saison ↔ recette pour l’instant.")
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
            season_counts["season_label"] = season_counts["season"].map(season_label_fr)

            chart = (
                alt.Chart(season_counts)
                .mark_bar()
                .encode(
                    x=alt.X(
                        "season_label:N",
                        sort=[season_label_fr(s) for s in ALL_SEASONS],
                        title=None
                    ),
                    y=alt.Y("count:Q", title="Recettes"),
                    tooltip=["season_label:N", "count:Q"],
                )
                .properties(height=220)
                .configure_view(strokeOpacity=0)
            )
            st.altair_chart(chart, width="stretch")

    with st.container(border=True):
        st.markdown("### Répartition du temps total")
        if t.empty:
            st.info("Pas encore de données de temps.")
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
                    y=alt.Y("count:Q", title="Recettes"),
                    tooltip=["bucket:N", "count:Q"],
                )
                .properties(height=220)
                .configure_view(strokeOpacity=0)
            )
            st.altair_chart(chart, width="stretch")

# Pretty HTML tables
st.write("")
st.markdown("### Faits marquants")


def html_table(df_small: pd.DataFrame) -> str:
    if df_small is None or df_small.empty:
        return "<div style='color:rgba(0,0,0,.6)'><i>Aucune donnée.</i></div>"
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
        st.markdown("#### ⚡ Recettes les plus rapides")
        fastest = (
            tmp.sort_values("total_m")
            .head(6)[["name", "total_m", "creator_name"]]
            .rename(columns={"name": "Recette", "total_m": "Total (min)", "creator_name": "Créateur"})
        )
        st.markdown(html_table(fastest), unsafe_allow_html=True)

with h2:
    with st.container(border=True):
        st.markdown("#### 🕰️ Recettes les plus longues")
        slowest = (
            tmp.sort_values("total_m", ascending=False)
            .head(6)[["name", "total_m", "creator_name"]]
            .rename(columns={"name": "Recette", "total_m": "Total (min)", "creator_name": "Créateur"})
        )
        st.markdown(html_table(slowest), unsafe_allow_html=True)

with st.container(border=True):
    st.markdown("#### 🆕 Ajoutées récemment")
    if "created_at" not in df_recipes.columns or df_recipes["created_at"].isna().all():
        st.markdown("<i>Date de création indisponible.</i>", unsafe_allow_html=True)
    else:
        recent = df_recipes.copy()
        recent["created_at_dt"] = pd.to_datetime(recent["created_at"], errors="coerce")
        recent = (
            recent.dropna(subset=["created_at_dt"])
            .sort_values("created_at_dt", ascending=False)
            .head(10)[["name", "creator_name", "created_at_dt"]]
            .rename(columns={"name": "Recette", "creator_name": "Créateur", "created_at_dt": "Créée"})
        )
        recent["Créée"] = recent["Créée"].dt.strftime("%Y-%m-%d %H:%M")
        st.markdown(html_table(recent), unsafe_allow_html=True)