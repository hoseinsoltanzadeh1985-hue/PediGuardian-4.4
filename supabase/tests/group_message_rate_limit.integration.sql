-- Local PostgreSQL integration contract for the flood-control migration.
-- Run with: psql -v ON_ERROR_STOP=1 -f supabase/tests/group_message_rate_limit.integration.sql
create table if not exists public.groups (
  id bigint primary key
);

do $$
begin
  if not exists (select 1 from pg_catalog.pg_roles where rolname = 'anon') then
    create role anon nologin;
  end if;
  if not exists (select 1 from pg_catalog.pg_roles where rolname = 'authenticated') then
    create role authenticated nologin;
  end if;
  if not exists (select 1 from pg_catalog.pg_roles where rolname = 'service_role') then
    create role service_role nologin bypassrls;
  end if;
end
$$;

\ir ../migrations/20261124190000_group_message_rate_limit.sql

insert into public.groups(id) values (992470501), (992470502)
on conflict (id) do nothing;
delete from public.group_message_rate_limits
where group_id in (992470501, 992470502)
  and telegram_user_id in (992470501, 992470502, 992470503);

do $$
declare
  i integer;
begin
  for i in 1..8 loop
    if public.consume_group_message_rate_limit(992470501, 992470501, 10, 8) is not true then
      raise exception 'message % should be accepted inside configured limit', i;
    end if;
  end loop;

  if public.consume_group_message_rate_limit(992470501, 992470501, 10, 8) is not false then
    raise exception 'message 9 should be rejected after the configured limit';
  end if;

  if public.consume_group_message_rate_limit(992470501, 992470502, 10, 8) is not true then
    raise exception 'a different user must have an independent rate bucket';
  end if;

  if public.consume_group_message_rate_limit(992470502, 992470501, 10, 8) is not true then
    raise exception 'a different group must have an independent rate bucket';
  end if;

  -- The function clamps the minimum limit to three, even if a caller asks for one.
  for i in 1..3 loop
    if public.consume_group_message_rate_limit(992470502, 992470503, 10, 1) is not true then
      raise exception 'clamped minimum allowance should accept message %', i;
    end if;
  end loop;
  if public.consume_group_message_rate_limit(992470502, 992470503, 10, 1) is not false then
    raise exception 'clamped minimum allowance should reject message 4';
  end if;

  if has_function_privilege('anon',
       'public.consume_group_message_rate_limit(bigint,bigint,integer,integer)', 'EXECUTE') then
    raise exception 'anon must not execute the rate-limit RPC';
  end if;
  if has_function_privilege('authenticated',
       'public.consume_group_message_rate_limit(bigint,bigint,integer,integer)', 'EXECUTE') then
    raise exception 'authenticated must not execute the rate-limit RPC';
  end if;
  if not has_function_privilege('service_role',
       'public.consume_group_message_rate_limit(bigint,bigint,integer,integer)', 'EXECUTE') then
    raise exception 'service_role must execute the rate-limit RPC';
  end if;

  if not (select relrowsecurity from pg_catalog.pg_class
          where oid = 'public.group_message_rate_limits'::regclass) then
    raise exception 'RLS must be enabled on group_message_rate_limits';
  end if;
end
$$;

select 'PASS: flood-control migration integration contract';
