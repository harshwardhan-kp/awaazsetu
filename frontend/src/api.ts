export const base =
  (import.meta as unknown as { env: Record<string, string> }).env
    .VITE_API_BASE_URL || "";
export async function api<T = any>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = sessionStorage.getItem("awaazsetu_token");
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData))
    headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const r = await fetch(`${base}/api${path}`, { ...options, headers });
  if (!r.ok) {
    let message = `Request failed (${r.status})`;
    try {
      const d = await r.json();
      message =
        typeof d.detail === "string" ? d.detail : JSON.stringify(d.detail || d);
    } catch {}
    if (r.status === 401) {
      sessionStorage.removeItem("awaazsetu_token");
      window.dispatchEvent(new Event("auth-expired"));
    }
    throw new Error(message);
  }
  return r.json();
}
export type Incident = {
  id: string;
  ticket_id: string;
  summary: string;
  incident_type: string;
  status: string;
  severity_score: number;
  severity_band: string;
  severity_reasons: { label: string; points: number }[];
  latitude: number | null;
  longitude: number | null;
  location_name: string;
  location_method: string;
  location_confidence: number;
  ward: string;
  needs_clarification: boolean;
  report_count: number;
  unique_reporters: number;
  languages: string[];
  channels: string[];
  created_at: string;
  updated_at: string;
  reports?: any[];
  history?: any[];
};
