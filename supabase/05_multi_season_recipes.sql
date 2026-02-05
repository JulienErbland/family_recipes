-- 1) Create link table
create table if not exists public.recipe_seasons (
  recipe_id uuid not null references public.recipes(id) on delete cascade,
  season public.season_enum not null,
  primary key (recipe_id, season)
);

create index if not exists idx_recipe_seasons_recipe_id on public.recipe_seasons(recipe_id);
create index if not exists idx_recipe_seasons_season on public.recipe_seasons(season);

-- 2) (Optional) Migrate existing single season data
insert into public.recipe_seasons (recipe_id, season)
select id, season
from public.recipes
where season is not null;

-- 3) Drop the old column
alter table public.recipes drop column if exists season;