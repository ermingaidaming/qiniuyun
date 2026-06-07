// API client — typed fetch wrappers for the FastAPI backend

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

import type { CausalGraph, HARReport, Novel, PipelineRunResult, R2ScanResult, Screenplay } from "@/types";

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

/** Health check. */
export async function getHealth(): Promise<{ status: string }> {
  return request<{ status: string }>("/api/health");
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

/** Download a screenplay export file (triggers browser download). */
export async function exportFile(id: string, format: ExportFormat): Promise<void> {
  const url = exportUrl(id, format);
  const response = await fetch(url);
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Export failed" }));
    throw new Error(error.detail ?? `HTTP ${response.status}`);
  }
  const blob = await response.blob();
  const blobUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = blobUrl;
  a.download = `screenplay.${format === "yaml" ? "yaml" : format}`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(blobUrl);
}

/** Build CPC causal graph from a novel. */
export async function buildCpc(novelId: string): Promise<CausalGraph> {
  return request<CausalGraph>("/api/cpc/build", {
    method: "POST",
    body: JSON.stringify({ novel_id: novelId }),
  });
}

/** Get CPC causal graph by novel ID. */
export async function getCpcGraph(novelId: string): Promise<CausalGraph> {
  return request<CausalGraph>(`/api/cpc/${novelId}/graph`);
}

/** Run R2 sliding window scan on a novel. */
export async function r2Scan(novelId: string): Promise<R2ScanResult> {
  return request<R2ScanResult>("/api/r2/scan", {
    method: "POST",
    body: JSON.stringify({ novel_id: novelId }),
  });
}

/** Get R2 scan result by novel ID. */
export async function getR2Result(novelId: string): Promise<R2ScanResult> {
  return request<R2ScanResult>(`/api/r2/${novelId}/result`);
}

/** Run HAR hallucination detection and correction on a novel. */
export async function harRefine(novelId: string): Promise<HARReport> {
  return request<HARReport>("/api/har/refine", {
    method: "POST",
    body: JSON.stringify({ novel_id: novelId }),
  });
}

/** Get HAR correction report by novel ID. */
export async function getHarReport(novelId: string): Promise<HARReport> {
  return request<HARReport>(`/api/har/${novelId}/report`);
}

/** Execute the full CPC → R2 → HAR → ScreenYAML pipeline. */
export async function runPipeline(novelId: string): Promise<PipelineRunResult> {
  return request<PipelineRunResult>("/api/pipeline/run", {
    method: "POST",
    body: JSON.stringify({ novel_id: novelId }),
  });
}
