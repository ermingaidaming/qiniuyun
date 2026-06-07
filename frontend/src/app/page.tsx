"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { uploadNovel } from "@/lib/api";

export default function Home() {
  const router = useRouter();
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
      const data = await uploadNovel(file);
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
    <main className="flex flex-1 flex-col items-center justify-center px-4 py-12">
      <div className="w-full max-w-xl">
        {/* Hero */}
        <header className="text-center mb-12">
          <h1 className="text-4xl font-bold tracking-tight text-stone-900">
            AI 小说
            <span className="text-amber-700">转</span>
            剧本
          </h1>
          <p className="mt-3 text-stone-500 text-lg">
            将文字淬炼为光影，小说一键转写结构化剧本
          </p>
        </header>

        {/* Upload card */}
        <div className="rounded-2xl border border-stone-200 bg-white p-10 shadow-sm transition-all duration-300 hover:shadow-md">
          {result ? (
            /* Success state */
            <div className="space-y-4 text-center">
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-amber-100">
                <svg className="h-7 w-7 text-amber-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <div>
                <p className="text-xl font-semibold text-stone-900">{result.title}</p>
                <p className="text-stone-400 mt-1">
                  共 {result.chapterCount} 个章节
                </p>
              </div>
              <div className="flex gap-3 justify-center pt-3">
                <button
                  onClick={() => router.push(`/screenplay/${result.novelId}`)}
                  className="rounded-xl bg-amber-700 px-6 py-3 text-sm font-semibold text-white hover:bg-amber-800 transition-all duration-200 hover:shadow-lg active:scale-[0.98]"
                >
                  生成剧本
                </button>
                <button
                  onClick={() => {
                    setResult(null);
                    setFile(null);
                  }}
                  className="rounded-xl border border-stone-200 px-6 py-3 text-sm font-semibold text-stone-500 hover:bg-stone-100 transition-all duration-200 active:scale-[0.98]"
                >
                  重新上传
                </button>
              </div>
            </div>
          ) : (
            /* Upload prompt */
            <div className="space-y-5 text-center">
              <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-stone-100">
                <svg className="h-8 w-8 text-stone-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
              </div>
              <div>
                <p className="text-stone-900 font-medium">将小说文件拖拽到此处</p>
                <p className="text-stone-400 text-sm mt-1">支持 .txt 格式，UTF-8 编码</p>
              </div>
              <label className="inline-block cursor-pointer">
                <span className="rounded-xl border border-stone-300 px-6 py-2.5 text-sm font-medium text-stone-500 hover:border-amber-300 hover:text-amber-700 transition-all duration-200">
                  {file ? file.name : "选择 TXT 文件"}
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
            </div>
          )}
        </div>

        {file && !result && (
          <button
            onClick={handleUpload}
            disabled={uploading}
            className="mt-5 w-full rounded-xl bg-amber-700 py-3.5 text-sm font-semibold text-white hover:bg-amber-800 disabled:opacity-50 transition-all duration-200 hover:shadow-lg active:scale-[0.98]"
          >
            {uploading ? "正在解析章节..." : "上传并解析"}
          </button>
        )}

        {error && (
          <div className="mt-4 rounded-xl border border-red-200 bg-red-50/80 p-4 text-sm text-red-700 text-center">
            {error}
          </div>
        )}
      </div>
    </main>
  );
}
