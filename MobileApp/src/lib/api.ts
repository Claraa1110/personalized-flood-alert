import { supabase } from './supabase';

const BASE = process.env.EXPO_PUBLIC_API_URL;

export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const { data: { session } } = await supabase.auth.getSession();
  const headers = new Headers(init.headers);
  if (session?.access_token) {
    headers.set('Authorization', `Bearer ${session.access_token}`);
  }
  return fetch(`${BASE}${path}`, { ...init, headers });
}
