// API client — typed fetch wrappers for the FastAPI backend

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

import type { Novel, Screenplay } from "@/types";

export type ExportFormat = "txt" | "docx" | "yaml";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      ...(options?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(error.detail ?? `HTTP ${response.status}`);
  }

  return response.json();
}

/** Upload a novel TXT file and get parsed chapters. */
export async function uploadNovel(file: File): Promise<Novel> {
  const formData = new FormData();
  formData.append("file", file);
  return request<Novel>("/api/novels/upload", {
    method: "POST",
    body: formData,
  });
}

/** Get novel detail by ID. */
export async function getNovel(id: string): Promise<Novel> {
  return request<Novel>(`/api/novels/${id}`);
}

/** Generate a screenplay from a novel. */
export async function generateScreenplay(novelId: string): Promise<Screenplay> {
  return request<Screenplay>(`/api/screenplay/generate`, {
    method: "POST",
    body: JSON.stringify({ novel_id: novelId }),
  });
}

/** Get a generated screenplay by ID. */
export async function getScreenplay(id: string): Promise<Screenplay> {
  return request<Screenplay>(`/api/screenplay/${id}`);
}

/** Build the export download URL. */
export function exportUrl(id: string, format: ExportFormat): string {
  return `${BASE_URL}/api/export/${id}?format=${format}`;
}
