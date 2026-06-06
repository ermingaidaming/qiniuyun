"use client";

import { useState } from "react";

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{
    novelId: string;
    title: string;
    chapterCount: number;
  } | null>(null);

  async function handleUpload() {
    if (!file) return;
    setUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch("http://localhost:8000/api/novels/upload", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Upload failed");
      }

      const data = await response.json();
      setResult({
        novelId: data.id,
        title: data.title,
        chapterCount: data.chapters.length,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setUploading(false);
    }
  }

  return (
    <main className="flex flex-1 flex-col items-center justify-center px-4">
      <div className="w-full max-w-lg">
        <header className="text-center mb-10">
          <h1 className="text-3xl font-bold tracking-tight text-zinc-900">
            AI 小说转剧本
          </h1>
          <p className="mt-2 text-zinc-500">
            上传小说 TXT 文件，自动生成结构化剧本
          </p>
        </header>

        {/* Upload area */}
        <div className="rounded-xl border-2 border-dashed border-zinc-300 bg-white p-10 text-center transition-colors hover:border-zinc-400">
          {result ? (
            /* Success state */
            <div className="space-y-3">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-green-100">
                <svg className="h-6 w-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <p className="text-lg font-semibold text-zinc-900">{result.title}</p>
              <p className="text-sm text-zinc-500">
                共 {result.chapterCount} 个章节
              </p>
              <div className="flex gap-3 justify-center pt-2">
                <button
                  onClick={() => {
                    window.location.href = `/screenplay/${result.novelId}`;
                  }}
                  className="rounded-lg bg-teal-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-teal-700 transition-colors"
                >
                  生成剧本
                </button>
                <button
                  onClick={() => {
                    setResult(null);
                    setFile(null);
                  }}
                  className="rounded-lg border border-zinc-300 px-5 py-2.5 text-sm font-semibold text-zinc-700 hover:bg-zinc-50 transition-colors"
                >
                  重新上传
                </button>
              </div>
            </div>
          ) : (
            /* Upload prompt */
            <div className="space-y-4">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-zinc-100">
                <svg className="h-6 w-6 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                </svg>
              </div>
              <label className="block cursor-pointer">
                <span className="text-sm font-semibold text-teal-600 hover:text-teal-700">
                  {file ? file.name : "点击选择 TXT 文件"}
                </span>
                <input
                  type="file"
                  accept=".txt"
                  className="hidden"
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) {
                      setFile(f);
                      setError(null);
                    }
                  }}
                />
              </label>
              <p className="text-xs text-zinc-400">或拖拽文件到此处，最大 500KB</p>
            </div>
          )}
        </div>

        {file && !result && (
          <button
            onClick={handleUpload}
            disabled={uploading}
            className="mt-4 w-full rounded-lg bg-teal-600 py-3 text-sm font-semibold text-white hover:bg-teal-700 disabled:opacity-50 transition-colors"
          >
            {uploading ? "解析中..." : "上传并解析"}
          </button>
        )}

        {error && (
          <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {error}
          </div>
        )}
      </div>
    </main>
  );
}
