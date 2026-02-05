alter table public.recipes
add column if not exists servings integer not null default 1;

alter table public.recipes
add constraint recipes_servings_positive
check (servings > 0 and servings <= 100);
