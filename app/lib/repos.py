from typing import Optional, List, Dict, Tuple
import streamlit as st

from app.lib.supabase_client import get_supabase, authed_postgrest


# =========================
# Core DB helpers
# =========================
def _sb(access_token: str):
    """Always use an authed PostgREST client."""
    return authed_postgrest(get_supabase(), access_token)


def _as_tuple_ids(ids: List[str] | Tuple[str, ...]) -> Tuple[str, ...]:
    """Streamlit cache hashing is more reliable with tuples."""
    if not ids:
        return tuple()
    return tuple(sorted([str(x) for x in ids if x]))


def _mask_token(tok: str) -> str:
    if not tok:
        return "<empty>"
    return tok[:12] + "..." + tok[-6:]


def _raise_clean(where: str, e: Exception):
    """
    Raise a non-redacted error message (safe) so Streamlit shows useful info.
    PostgREST errors are often redacted by Streamlit Cloud unless you re-raise cleanly.
    """
    raise RuntimeError(f"{where} failed: {type(e).__name__}: {e}") from e


# =========================
# Profiles / roles
# =========================
def get_my_role(access_token: str, user_id: str) -> str:
    sb = _sb(access_token)
    try:
        res = (
            sb.table("profiles")
            .select("role")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
    except Exception as e:
        _raise_clean("get_my_role", e)

    rows = res.data or []
    if rows:
        return rows[0].get("role") or "reader"
    return "reader"


def ensure_my_profile(access_token: str, user_id: str) -> None:
    sb = _sb(access_token)

    try:
        existing = (
            sb.table("profiles")
            .select("id")
            .eq("id", user_id)
            .maybe_single()
            .execute()
        )
    except Exception as e:
        _raise_clean("ensure_my_profile(select)", e)

    if existing.data:
        return

    try:
        sb.table("profiles").insert({"id": user_id, "role": "reader"}).execute()
    except Exception as e:
        _raise_clean("ensure_my_profile(insert)", e)


def set_my_role(access_token: str, user_id: str, role: str) -> bool:
    sb = _sb(access_token)
    try:
        sb.table("profiles").update({"role": role}).eq("id", user_id).execute()
    except Exception as e:
        _raise_clean("set_my_role", e)
    return True


def list_profiles_by_ids(access_token: str, user_ids: List[str]) -> List[Dict]:
    """
    Fetch profiles for a set of user ids (UUIDs).
    Returns rows like: {id, first_name, last_name, role}
    """
    ids = _as_tuple_ids(user_ids)
    if not ids:
        return []

    sb = _sb(access_token)
    try:
        res = (
            sb.table("profiles")
            .select("id,first_name,last_name,role")
            .in_("id", list(ids))
            .execute()
        )
    except Exception as e:
        _raise_clean("list_profiles_by_ids", e)

    return res.data or []


def map_creator_ids_to_names(access_token: str, creator_ids: List[str]) -> Dict[str, str]:
    profiles = list_profiles_by_ids(access_token, creator_ids)
    id_to_name = {}
    for p in profiles:
        fn = (p.get("first_name") or "").strip()
        ln = (p.get("last_name") or "").strip()
        full = (fn + " " + ln).strip()
        id_to_name[p["id"]] = full if full else "Unknown"
    return id_to_name


# =========================
# Ingredients
# =========================
def list_ingredients(access_token: str) -> List[Dict]:
    sb = _sb(access_token)
    try:
        res = sb.table("ingredients").select("id,name").order("name").execute()
    except Exception as e:
        _raise_clean("list_ingredients", e)
    return res.data or []


def create_ingredient(access_token: str, name: str) -> Dict:
    sb = _sb(access_token)
    try:
        res = sb.table("ingredients").insert({"name": name}).execute()
    except Exception as e:
        _raise_clean("create_ingredient", e)
    return res.data[0] if res.data else {}


def find_ingredient_by_name(access_token: str, name: str) -> Optional[Dict]:
    sb = _sb(access_token)
    try:
        res = (
            sb.table("ingredients")
            .select("id,name")
            .eq("name", name)
            .maybe_single()
            .execute()
        )
    except Exception as e:
        _raise_clean("find_ingredient_by_name", e)
    return res.data


# =========================
# Recipes
# =========================
def create_recipe(access_token: str, payload: Dict) -> Dict:
    sb = _sb(access_token)
    try:
        res = sb.table("recipes").insert(payload).execute()
    except Exception as e:
        _raise_clean("create_recipe", e)
    return res.data[0] if res.data else {}


def update_recipe(access_token: str, recipe_id: str, patch: Dict) -> Dict:
    sb = _sb(access_token)
    allowed = {k: v for k, v in patch.items() if k in {
        "name", "servings", "prep_minutes", "cook_minutes", "instructions", "notes"
    }}
    try:
        res = sb.table("recipes").update(allowed).eq("id", recipe_id).execute()
    except Exception as e:
        _raise_clean("update_recipe", e)
    return res.data[0] if res.data else {}


def delete_recipe(access_token: str, recipe_id: str) -> bool:
    sb = _sb(access_token)
    try:
        sb.table("recipes").delete().eq("id", recipe_id).execute()
    except Exception as e:
        _raise_clean("delete_recipe", e)
    return True


def list_recipes(access_token: str) -> List[Dict]:
    sb = _sb(access_token)
    try:
        res = (
            sb.table("recipes")
            .select(
                "id,name,servings,prep_minutes,cook_minutes,total_minutes,created_by,"
                "instructions,notes"
            )
            .order("name", desc=False)
            .execute()
        )
    except Exception as e:
        _raise_clean("list_recipes", e)
    return res.data or []


def list_my_recipes(access_token: str, user_id: str) -> List[Dict]:
    sb = _sb(access_token)
    try:
        res = (
            sb.table("recipes")
            .select(
                "id,name,servings,prep_minutes,cook_minutes,total_minutes,created_by,"
                "instructions,notes,created_at,updated_at"
            )
            .eq("created_by", user_id)
            .order("created_at", desc=True)
            .execute()
        )
    except Exception as e:
        _raise_clean(
            f"list_my_recipes(user_id={user_id}, token={_mask_token(access_token)})",
            e,
        )
    return res.data or []


# =========================
# Recipe <-> ingredients links
# =========================
def add_recipe_ingredient(access_token: str, payload: Dict) -> Dict:
    sb = _sb(access_token)
    try:
        res = sb.table("recipe_ingredients").insert(payload).execute()
    except Exception as e:
        _raise_clean("add_recipe_ingredient", e)
    return res.data[0] if res.data else {}


def get_recipe_ingredients(access_token: str, recipe_id: str) -> List[Dict]:
    sb = _sb(access_token)
    try:
        res = (
            sb.table("recipe_ingredients")
            .select("ingredient_id,quantity,unit,comment,ingredients(name)")
            .eq("recipe_id", recipe_id)
            .execute()
        )
    except Exception as e:
        _raise_clean("get_recipe_ingredients", e)
    return res.data or []


def list_recipe_ingredients(access_token: str) -> List[Dict]:
    sb = _sb(access_token)
    try:
        res = (
            sb.table("recipe_ingredients")
            .select("recipe_id,quantity,unit,comment,ingredients(name)")
            .execute()
        )
    except Exception as e:
        _raise_clean("list_recipe_ingredients", e)
    return res.data or []


def delete_recipe_ingredient_link(access_token: str, recipe_id: str, ingredient_id: str) -> bool:
    sb = _sb(access_token)
    try:
        sb.table("recipe_ingredients").delete().eq("recipe_id", recipe_id).eq("ingredient_id", ingredient_id).execute()
    except Exception as e:
        _raise_clean("delete_recipe_ingredient_link", e)
    return True


def update_recipe_ingredient_link(access_token: str, recipe_id: str, ingredient_id: str, patch: Dict) -> bool:
    sb = _sb(access_token)
    allowed = {k: v for k, v in patch.items() if k in {"quantity", "unit", "comment"}}
    try:
        sb.table("recipe_ingredients").update(allowed).eq("recipe_id", recipe_id).eq("ingredient_id", ingredient_id).execute()
    except Exception as e:
        _raise_clean("update_recipe_ingredient_link", e)
    return True


# =========================
# Seasons (Option A join table)
# =========================
def list_recipe_seasons(access_token: str) -> List[Dict]:
    sb = _sb(access_token)
    try:
        res = sb.table("recipe_seasons").select("recipe_id,season").execute()
    except Exception as e:
        _raise_clean("list_recipe_seasons", e)
    return res.data or []


def get_recipe_seasons(access_token: str, recipe_id: str) -> List[str]:
    sb = _sb(access_token)
    try:
        res = sb.table("recipe_seasons").select("season").eq("recipe_id", recipe_id).execute()
    except Exception as e:
        _raise_clean("get_recipe_seasons", e)
    rows = res.data or []
    return sorted({r.get("season") for r in rows if r.get("season")})


def set_recipe_seasons(access_token: str, recipe_id: str, seasons: List[str]) -> bool:
    sb = _sb(access_token)

    seasons = sorted({s for s in (seasons or []) if s})

    try:
        sb.table("recipe_seasons").delete().eq("recipe_id", recipe_id).execute()
    except Exception as e:
        _raise_clean("set_recipe_seasons(delete)", e)

    if seasons:
        rows = [{"recipe_id": recipe_id, "season": s} for s in seasons]
        try:
            sb.table("recipe_seasons").insert(rows).execute()
        except Exception as e:
            _raise_clean("set_recipe_seasons(insert)", e)

    return True


# =========================
# Caching (token-aware, TTL, safe hashing)
# =========================
@st.cache_data(ttl=60, show_spinner=False)
def cached_list_recipes(access_token: str) -> List[Dict]:
    return list_recipes(access_token)


@st.cache_data(ttl=60, show_spinner=False)
def cached_list_recipe_ingredients(access_token: str) -> List[Dict]:
    return list_recipe_ingredients(access_token)


@st.cache_data(ttl=300, show_spinner=False)
def cached_list_ingredients(access_token: str) -> List[Dict]:
    return list_ingredients(access_token)


@st.cache_data(ttl=300, show_spinner=False)
def cached_list_profiles_by_ids(access_token: str, user_ids: Tuple[str, ...]) -> List[Dict]:
    # IMPORTANT: accept tuple for reliable hashing
    return list_profiles_by_ids(access_token, list(user_ids))


@st.cache_data(ttl=60, show_spinner=False)
def cached_list_my_recipes(access_token: str, user_id: str) -> List[Dict]:
    # Keep short TTL because tokens can expire / rotate
    return list_my_recipes(access_token, user_id)


@st.cache_data(ttl=60, show_spinner=False)
def cached_get_recipe_ingredients(access_token: str, recipe_id: str) -> List[Dict]:
    return get_recipe_ingredients(access_token, recipe_id)


@st.cache_data(ttl=60, show_spinner=False)
def cached_list_recipe_seasons(access_token: str) -> List[Dict]:
    return list_recipe_seasons(access_token)


@st.cache_data(ttl=60, show_spinner=False)
def cached_get_recipe_seasons(access_token: str, recipe_id: str) -> List[str]:
    return get_recipe_seasons(access_token, recipe_id)
