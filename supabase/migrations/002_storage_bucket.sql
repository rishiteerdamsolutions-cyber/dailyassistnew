-- AHA Vault — Supabase Storage bucket
-- Run this in Supabase Dashboard → SQL Editor (after 001_initial_schema.sql)

-- Create private bucket for vault media
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
    'aha-vault',
    'aha-vault',
    false,
    52428800,   -- 50 MB per file
    array[
        'image/png', 'image/jpeg', 'image/webp', 'image/gif',
        'video/mp4', 'video/quicktime', 'video/webm',
        'text/plain'
    ]
)
on conflict (id) do nothing;

-- Storage RLS: users can only access their own folder ({uid}/...)
create policy "vault_storage_select_own" on storage.objects
    for select using (
        bucket_id = 'aha-vault'
        and (storage.foldername(name))[1] = current_setting('request.jwt.claims', true)::json->>'sub'
    );

create policy "vault_storage_insert_own" on storage.objects
    for insert with check (
        bucket_id = 'aha-vault'
        and (storage.foldername(name))[1] = current_setting('request.jwt.claims', true)::json->>'sub'
    );

create policy "vault_storage_update_own" on storage.objects
    for update using (
        bucket_id = 'aha-vault'
        and (storage.foldername(name))[1] = current_setting('request.jwt.claims', true)::json->>'sub'
    );

create policy "vault_storage_delete_own" on storage.objects
    for delete using (
        bucket_id = 'aha-vault'
        and (storage.foldername(name))[1] = current_setting('request.jwt.claims', true)::json->>'sub'
    );
