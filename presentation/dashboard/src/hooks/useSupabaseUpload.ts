import { createClient } from '@supabase/supabase-js';

const supabase = createClient(import.meta.env.VITE_SUPABASE_URL || '', import.meta.env.VITE_SUPABASE_ANON_KEY || '');

export async function uploadFile(bucket: string, path: string, file: File): Promise<string> {
  const { error } = await supabase.storage.from(bucket).upload(path, file);
  if (error) throw error;
  const { data } = supabase.storage.from(bucket).getPublicUrl(path);
  return data.publicUrl;
}
