alter table public.voice_order_requests
  add column if not exists action text not null default 'WHEEL',
  add column if not exists source_url text;

alter table public.voice_order_requests
  drop constraint if exists voice_order_requests_action_check;
alter table public.voice_order_requests
  add constraint voice_order_requests_action_check
  check (action in ('WHEEL','PLAY','PAUSE','RESUME','STOP'));

create index if not exists voice_order_requests_action_status_idx
  on public.voice_order_requests (action, status, created_at);
