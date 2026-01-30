-- =========================
-- 0) ENUM TYPES (clean constraints)
-- =========================
do $$ begin
  create type public.role_enum as enum ('reader', 'editor');
exception
  when duplicate_object then null;
end $$;

do $$ begin
  create type public.season_enum as enum ('winter', 'spring', 'summer', 'fall', 'all');
exception
  when duplicate_object then null;
end $$;

-- =========================
-- 1) PROFILES (extra user info + role)
-- auth.users is managed by Supabase Auth
-- profiles.id == auth.users.id
-- =========================
create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  first_name text,
  last_name text,
  role public.role_enum not null default 'reader',
  created_at timestamptz not null default now()
);

-- =========================
-- 2) RECIPES
-- total_minutes computed automatically
-- =========================
create table if not exists public.recipes (
  id uuid primary key default gen_random_uuid(),

  name text not null,
  season public.season_enum not null default 'all',

  prep_minutes integer not null default 0 check (prep_minutes >= 0),
  cook_minutes integer not null default 0 check (cook_minutes >= 0),
  total_minutes integer generated always as (prep_minutes + cook_minutes) stored,

  instructions text,
  notes text,

  created_by uuid not null references auth.users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_recipes_total_minutes on public.recipes(total_minutes);
create index if not exists idx_recipes_created_by on public.recipes(created_by);

-- =========================
-- 3) INGREDIENTS
-- =========================
create table if not exists public.ingredients (
  id uuid primary key default gen_random_uuid(),
  name text not null unique
);

-- =========================
-- 4) RECIPE_INGREDIENTS (many-to-many link)
-- =========================
create table if not exists public.recipe_ingredients (
  recipe_id uuid not null references public.recipes(id) on delete cascade,
  ingredient_id uuid not null references public.ingredients(id) on delete restrict,

  quantity text,
  unit text,
  comment text,

  primary key (recipe_id, ingredient_id)
);

-- Add a normalized version of the ingredient name
alter table public.ingredients
add column if not exists name_norm text
generated always as (lower(trim(name))) stored;

-- Enforce uniqueness on normalized name
drop index if exists ingredients_name_norm_unique;
create unique index ingredients_name_norm_unique
on public.ingredients (name_norm);


create index if not exists idx_recipe_ingredients_recipe_id on public.recipe_ingredients(recipe_id);
create index if not exists idx_recipe_ingredients_ingredient_id on public.recipe_ingredients(ingredient_id);
