-- Anavah Institute platform schema. Run once in Supabase: SQL Editor > New query > paste > Run.
-- The app connects as the database owner via DATABASE_URL, so RLS (enabled, no policies) simply
-- blocks the public anon/authenticated API keys from reading any of these tables directly.

create extension if not exists btree_gist;

create table if not exists clients (
  id uuid primary key default gen_random_uuid(),
  first_name text not null default '',
  last_name text not null default '',
  email text,
  phone text,
  status text not null default 'lead' check (status in ('lead','active','inactive','archived')),
  source text not null default 'manual',
  tags jsonb not null default '[]'::jsonb,
  notes text not null default '',
  email_consent boolean not null default false,
  sms_consent boolean not null default false,
  do_not_contact boolean not null default false,
  ghl_contact_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create unique index if not exists clients_email_uq on clients (lower(email)) where email is not null and email <> '';
create index if not exists clients_status_ix on clients (status);

create table if not exists client_notes (
  id uuid primary key default gen_random_uuid(),
  client_id uuid not null references clients(id) on delete cascade,
  body text not null,
  created_by text,
  created_at timestamptz not null default now()
);
create index if not exists client_notes_client_ix on client_notes (client_id, created_at desc);

create table if not exists appointment_types (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  slug text not null unique,
  description text not null default '',
  audience text not null default 'patient' check (audience in ('patient','provider')),
  duration_min int not null default 30 check (duration_min between 5 and 480),
  buffer_after_min int not null default 0 check (buffer_after_min between 0 and 240),
  mode text not null default 'either' check (mode in ('telehealth','in_person','either')),
  active boolean not null default true,
  sort int not null default 0
);

-- weekday: Monday = 0 ... Sunday = 6. Times are wall-clock in the practice timezone.
create table if not exists availability_rules (
  id uuid primary key default gen_random_uuid(),
  weekday int not null check (weekday between 0 and 6),
  start_time text not null,
  end_time text not null,
  active boolean not null default true
);

create table if not exists time_off (
  id uuid primary key default gen_random_uuid(),
  start_at timestamptz not null,
  end_at timestamptz not null check (end_at > start_at),
  reason text not null default ''
);

create table if not exists appointments (
  id uuid primary key default gen_random_uuid(),
  client_id uuid not null references clients(id) on delete restrict,
  type_id uuid references appointment_types(id) on delete set null,
  type_name text not null default '',
  start_at timestamptz not null,
  end_at timestamptz not null,
  blocked_until timestamptz not null,       -- end_at + buffer; what the calendar treats as busy
  status text not null default 'confirmed' check (status in ('pending','confirmed','cancelled','completed','no_show')),
  mode text not null default 'telehealth' check (mode in ('telehealth','in_person')),
  notes text not null default '',           -- internal only; never put clinical details here
  client_message text not null default '',
  manage_token text not null unique,
  source text not null default 'web',
  reminder_sent_at timestamptz,
  cancelled_at timestamptz,
  created_at timestamptz not null default now(),
  check (end_at > start_at and blocked_until >= end_at)
);
create index if not exists appointments_start_ix on appointments (start_at);
create index if not exists appointments_client_ix on appointments (client_id);
-- Database-level guarantee that two live appointments can never overlap (single-practitioner calendar).
alter table appointments drop constraint if exists appointments_no_overlap;
alter table appointments add constraint appointments_no_overlap
  exclude using gist (tstzrange(start_at, blocked_until, '[)') with &&)
  where (status in ('pending','confirmed'));

create table if not exists prospects (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  organization text not null default '',
  role text not null default '',
  category text not null default 'provider' check (category in ('provider','attorney','pt','pcp','organization','other')),
  email text,
  phone text,
  status text not null default 'new' check (status in ('new','contacted','replied','meeting','won','lost')),
  notes text not null default '',
  do_not_contact boolean not null default false,
  ghl_contact_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists prospects_status_ix on prospects (status);

create table if not exists templates (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  channel text not null check (channel in ('email','sms')),
  subject text not null default '',
  body text not null,
  created_at timestamptz not null default now()
);

create table if not exists messages (
  id uuid primary key default gen_random_uuid(),
  client_id uuid references clients(id) on delete set null,
  prospect_id uuid references prospects(id) on delete set null,
  appointment_id uuid references appointments(id) on delete set null,
  channel text not null check (channel in ('email','sms')),
  kind text not null default 'outreach',    -- outreach | reminder | confirmation | cancellation
  to_address text not null default '',
  subject text not null default '',
  body text not null default '',
  status text not null default 'queued',    -- queued | sent | failed | dry_run | blocked
  error text not null default '',
  provider_id text,
  created_at timestamptz not null default now()
);
create index if not exists messages_created_ix on messages (created_at desc);

create table if not exists unsubscribes (
  address text primary key,                 -- lower-cased email or phone
  channel text not null,
  created_at timestamptz not null default now()
);

create table if not exists settings (
  key text primary key,
  value jsonb not null
);

-- Lock the tables away from Supabase's public API keys. The app uses the owner connection and is unaffected.
alter table clients enable row level security;
alter table client_notes enable row level security;
alter table appointment_types enable row level security;
alter table availability_rules enable row level security;
alter table time_off enable row level security;
alter table appointments enable row level security;
alter table prospects enable row level security;
alter table templates enable row level security;
alter table messages enable row level security;
alter table unsubscribes enable row level security;
alter table settings enable row level security;
