-- Mi Despensa: cuentas Google, despensas personales y colaboración por correo
-- Ejecuta este archivo completo en Supabase > SQL Editor > New query.
create extension if not exists pgcrypto;

create table if not exists public.pantries (
  id uuid primary key default gen_random_uuid(),
  name text not null default 'Mi despensa',
  owner_id uuid not null references auth.users(id) on delete cascade,
  created_at timestamptz not null default now()
);

create table if not exists public.pantry_members (
  pantry_id uuid not null references public.pantries(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null default 'member' check (role in ('owner','member')),
  joined_at timestamptz not null default now(),
  primary key (pantry_id,user_id)
);

create table if not exists public.pantry_items (
  pantry_id uuid primary key references public.pantries(id) on delete cascade,
  items jsonb not null default '[]'::jsonb,
  updated_at timestamptz not null default now()
);

create table if not exists public.pantry_invitations (
  id uuid primary key default gen_random_uuid(),
  pantry_id uuid not null references public.pantries(id) on delete cascade,
  email text not null,
  invited_by uuid not null references auth.users(id) on delete cascade,
  created_at timestamptz not null default now(),
  unique (pantry_id,email)
);

alter table public.pantries enable row level security;
alter table public.pantry_members enable row level security;
alter table public.pantry_items enable row level security;
alter table public.pantry_invitations enable row level security;

drop policy if exists pantry_members_can_read_pantries on public.pantries;
create policy pantry_members_can_read_pantries on public.pantries for select to authenticated
using (exists(select 1 from public.pantry_members m where m.pantry_id=id and m.user_id=auth.uid()));

drop policy if exists pantry_members_can_read_members on public.pantry_members;
create policy pantry_members_can_read_members on public.pantry_members for select to authenticated
using (exists(select 1 from public.pantry_members m where m.pantry_id=pantry_id and m.user_id=auth.uid()));

drop policy if exists pantry_members_can_read_items on public.pantry_items;
create policy pantry_members_can_read_items on public.pantry_items for select to authenticated
using (exists(select 1 from public.pantry_members m where m.pantry_id=pantry_id and m.user_id=auth.uid()));

revoke all on public.pantries, public.pantry_members, public.pantry_items, public.pantry_invitations from anon, authenticated;
grant select on public.pantries, public.pantry_members, public.pantry_items to authenticated;

create or replace function public.get_my_pantries()
returns jsonb language plpgsql security definer set search_path=public,auth as $$
declare v_uid uuid:=auth.uid(); v_email text; v_result jsonb;
begin
 if v_uid is null then raise exception 'Debes iniciar sesión'; end if;
 select email into v_email from auth.users where id=v_uid;
 insert into public.pantries(name,owner_id)
 select 'Mi despensa',v_uid
 where not exists(select 1 from public.pantry_members where user_id=v_uid and role='owner');
 insert into public.pantry_members(pantry_id,user_id,role)
 select p.id,v_uid,'owner' from public.pantries p
 where p.owner_id=v_uid on conflict do nothing;
 insert into public.pantry_items(pantry_id,items)
 select p.id,'[]'::jsonb from public.pantries p
 join public.pantry_members m on m.pantry_id=p.id
 where m.user_id=v_uid on conflict do nothing;
 if v_email is not null then
   insert into public.pantry_members(pantry_id,user_id,role)
   select i.pantry_id,v_uid,'member' from public.pantry_invitations i
   where lower(i.email)=lower(v_email)
   on conflict do nothing;
   delete from public.pantry_invitations where lower(email)=lower(v_email);
 end if;
 select coalesce(jsonb_agg(jsonb_build_object('id',p.id,'name',p.name,'role',m.role) order by (m.role='owner') desc,p.created_at), '[]'::jsonb)
 into v_result from public.pantries p join public.pantry_members m on m.pantry_id=p.id
 where m.user_id=v_uid;
 return v_result;
end $$;

create or replace function public.load_pantry(p_pantry_id uuid)
returns jsonb language plpgsql security definer set search_path=public,auth as $$
declare v_items jsonb; v_name text;
begin
 if auth.uid() is null or not exists(select 1 from public.pantry_members where pantry_id=p_pantry_id and user_id=auth.uid()) then
   raise exception 'No tienes acceso a esta despensa';
 end if;
 select name into v_name from public.pantries where id=p_pantry_id;
 select items into v_items from public.pantry_items where pantry_id=p_pantry_id;
 return jsonb_build_object('id',p_pantry_id,'name',v_name,'items',coalesce(v_items,'[]'::jsonb));
end $$;

create or replace function public.save_pantry(p_pantry_id uuid,p_items jsonb)
returns timestamptz language plpgsql security definer set search_path=public,auth as $$
declare v_time timestamptz;
begin
 if auth.uid() is null or not exists(select 1 from public.pantry_members where pantry_id=p_pantry_id and user_id=auth.uid()) then
   raise exception 'No tienes acceso para modificar esta despensa';
 end if;
 if jsonb_typeof(p_items) <> 'array' then raise exception 'El inventario debe ser una lista'; end if;
 insert into public.pantry_items(pantry_id,items,updated_at) values(p_pantry_id,p_items,now())
 on conflict(pantry_id) do update set items=excluded.items,updated_at=now()
 returning updated_at into v_time;
 return v_time;
end $$;

create or replace function public.invite_to_pantry(p_pantry_id uuid,p_email text)
returns void language plpgsql security definer set search_path=public,auth as $$
declare v_email text:=lower(trim(p_email));
begin
 if auth.uid() is null then raise exception 'Debes iniciar sesión'; end if;
 if not exists(select 1 from public.pantries where id=p_pantry_id and owner_id=auth.uid()) then
   raise exception 'Solo el propietario puede invitar a otras cuentas';
 end if;
 if v_email is null or v_email !~ '^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$' then
   raise exception 'Introduce un correo electrónico válido';
 end if;
 insert into public.pantry_invitations(pantry_id,email,invited_by)
 values(p_pantry_id,v_email,auth.uid())
 on conflict(pantry_id,email) do update set invited_by=excluded.invited_by,created_at=now();
end $$;

grant execute on function public.get_my_pantries() to authenticated;
grant execute on function public.load_pantry(uuid) to authenticated;
grant execute on function public.save_pantry(uuid,jsonb) to authenticated;
grant execute on function public.invite_to_pantry(uuid,text) to authenticated;
