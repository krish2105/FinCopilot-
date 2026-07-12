// Optional Supabase client. When env vars are absent, auth is "demo mode":
// the app is fully usable without a login (great for the portfolio demo).
import { createClient, type SupabaseClient } from "@supabase/supabase-js";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
const anon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

export const isAuthConfigured = Boolean(url && anon);

let client: SupabaseClient | null = null;

export function getSupabase(): SupabaseClient | null {
  if (!isAuthConfigured) return null;
  if (!client) client = createClient(url!, anon!);
  return client;
}
