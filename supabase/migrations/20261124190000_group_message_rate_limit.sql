-- Atomic per-group/per-user fixed-window flood control.
-- Only trusted server-side webhook code may call the RPC.
create table if not exists public.group_message_rate_limits (
  group_id bigint not null references public.groups(id) on delete cascade,
  telegram_user_id bigint not null,
  window_started_at timestamptz not null default pg_catalog.now(),
  message_count integer not null default 1 check (message_count >= 1),
  primary key (group_id, telegram_user_id)
);

create index if not exists group_message_rate_limits_window_idx
  on public.group_message_rate_limits (window_started_at);

alter table public.group_message_rate_limits enable row level security;

create or replace function public.consume_group_message_rate_limit(
  p_group_id bigint,
  p_telegram_user_id bigint,
  p_window_seconds integer default 10,
  p_max_messages integer default 8
)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_window_seconds integer := greatest(5, least(coalesce(p_window_seconds, 10), 60));
  v_max_messages integer := greatest(3, least(coalesce(p_max_messages, 8), 30));
  v_message_count integer;
begin
  if p_group_id is null or p_group_id <= 0
     or p_telegram_user_id is null or p_telegram_user_id <= 0 then
    return false;
  end if;

  insert into public.group_message_rate_limits as current_limit
    (group_id, telegram_user_id, window_started_at, message_count)
  values
    (p_group_id, p_telegram_user_id, pg_catalog.now(), 1)
  on conflict (group_id, telegram_user_id) do update
    set window_started_at = case
          when current_limit.window_started_at <=
               pg_catalog.now() - pg_catalog.make_interval(secs => v_window_seconds)
          then pg_catalog.now()
          else current_limit.window_started_at
        end,
        message_count = case
          when current_limit.window_started_at <=
               pg_catalog.now() - pg_catalog.make_interval(secs => v_window_seconds)
          then 1
          else current_limit.message_count + 1
        end
  returning message_count into v_message_count;

  return v_message_count <= v_max_messages;
end;
$$;

revoke execute on function public.consume_group_message_rate_limit(bigint, bigint, integer, integer)
  from public, anon, authenticated;
grant execute on function public.consume_group_message_rate_limit(bigint, bigint, integer, integer)
  to service_role;
