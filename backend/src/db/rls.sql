-- FinCopilot — Postgres Row-Level Security (Phase 16, defense-in-depth).
--
-- Isolation lives in the DB, not just app code: even a bug in a query can't leak
-- another tenant's rows. Every request sets `app.current_org` (via the connection
-- pool; see src/db/database.py) and these policies filter to it.
--
-- HOW TO APPLY (once, in the Supabase SQL editor / psql, as the table owner):
--   1) Run this file.
--   2) Have the API connect as a NON-owner role (RLS is bypassed for owners /
--      superusers). Create and use `fincopilot_app`:
--        CREATE ROLE fincopilot_app LOGIN PASSWORD '...';
--        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO fincopilot_app;
--        ALTER DEFAULT PRIVILEGES IN SCHEMA public
--          GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO fincopilot_app;
--      Point DATABASE_URL at fincopilot_app.

-- Helper: the current request's org ('' when unset).
CREATE OR REPLACE FUNCTION app_current_org() RETURNS text
  LANGUAGE sql STABLE AS $$ SELECT current_setting('app.current_org', true) $$;

-- ----- org-scoped tables (have an org_id column) -----
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'orgs','users','workspaces','documents','conversations',
    'usage_events','feedback','api_keys','watchlists','audit'
  ] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', t);
    EXECUTE format('DROP POLICY IF EXISTS tenant_isolation ON %I', t);
    IF t = 'orgs' THEN
      EXECUTE format(
        'CREATE POLICY tenant_isolation ON %I USING (id = app_current_org())
           WITH CHECK (id = app_current_org())', t);
    ELSE
      EXECUTE format(
        'CREATE POLICY tenant_isolation ON %I USING (org_id = app_current_org())
           WITH CHECK (org_id = app_current_org())', t);
    END IF;
  END LOOP;
END $$;

-- ----- messages (keyed by conversation, not org) -----
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON messages;
CREATE POLICY tenant_isolation ON messages
  USING (conversation_id IN (
    SELECT id FROM conversations WHERE org_id = app_current_org()))
  WITH CHECK (conversation_id IN (
    SELECT id FROM conversations WHERE org_id = app_current_org()));

-- ----- chunks (vector store): public corpus is shared; private uploads are
-- readable only by their owning org, resolved through the workspaces table -----
ALTER TABLE chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE chunks FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON chunks;
CREATE POLICY tenant_isolation ON chunks
  USING (
    workspace_id = 'public'
    OR workspace_id IN (SELECT id FROM workspaces WHERE org_id = app_current_org())
  )
  WITH CHECK (
    workspace_id = 'public'
    OR workspace_id IN (SELECT id FROM workspaces WHERE org_id = app_current_org())
  );
