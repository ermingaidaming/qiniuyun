"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import type { Novel, Screenplay, SceneElementType } from "@/types";
import { exportUrl, generateScreenplay, getNovel, getScreenplay } from "@/lib/api";

const TYPE_STYLES: Record<SceneElementType, string> = {
  action: "text-zinc-700 leading-relaxed",
  character: "text-center font-bold text-zinc-900 uppercase tracking-wide mt-4",
  dialogue: "mx-8 leading-relaxed text-zinc-800",
  parenthetical: "mx-12 text-sm text-zinc-500 italic",
};

export default function ScreenplayPage() {
  const params = useParams();
  const novelId = params.id as string;

  const [novel, setNovel] = useState<Novel | null>(null);
  const [screenplay, setScreenplay] = useState<Screenplay | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load novel and check for existing screenplay
  const load = useCallback(async () => {
    try {
      const n = await getNovel(novelId);
      setNovel(n);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load novel");
    } finally {
      setLoading(false);
    }
  }, [novelId]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleGenerate() {
    setGenerating(true);
    setError(null);
    try {
      const sp = await generateScreenplay(novelId);
      setScreenplay(sp);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setGenerating(false);
    }
  }

  async function handleExport(format: "txt" | "docx") {
    if (!screenplay) return;
    window.open(exportUrl(screenplay.id, format), "_blank");
  }

  if (loading) {
    return (
      <main className="flex flex-1 items-center justify-center">
        <div className="animate-pulse text-zinc-400">加载中...</div>
      </main>
    );
  }

  if (error && !novel) {
    return (
      <main className="flex flex-1 items-center justify-center px-4">
        <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-sm text-red-700 max-w-md text-center">
          <p className="font-semibold mb-2">加载失败</p>
          <p>{error}</p>
          <button
            onClick={load}
            className="mt-4 text-red-600 underline hover:text-red-800"
          >
            重试
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className="flex flex-1 flex-col px-4 py-8 max-w-3xl mx-auto w-full">
      {/* Header */}
      <header className="mb-8">
        <a href="/" className="text-sm text-teal-600 hover:text-teal-700 mb-2 inline-block">
          ← 返回上传
        </a>
        <h1 className="text-2xl font-bold text-zinc-900">{novel?.title}</h1>
        <p className="text-sm text-zinc-500 mt-1">
          {novel?.chapters.length} 个章节 · {novel?.filename}
        </p>
      </header>

      {!screenplay ? (
        /* Generate prompt */
        <div className="rounded-xl border border-zinc-200 bg-white p-8 text-center">
          <p className="text-zinc-600 mb-6">
            点击下方按钮，AI 将把小说转化为剧本格式
          </p>
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="rounded-lg bg-teal-600 px-8 py-3 text-sm font-semibold text-white hover:bg-teal-700 disabled:opacity-50 transition-colors"
          >
            {generating ? "AI 正在生成剧本..." : "生成剧本"}
          </button>
          {error && (
            <p className="mt-4 text-sm text-red-600">{error}</p>
          )}
        </div>
      ) : (
        <>
          {/* Export toolbar */}
          <div className="flex gap-3 mb-6">
            <button
              onClick={() => handleExport("txt")}
              className="rounded-lg border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50 transition-colors"
            >
              导出 TXT
            </button>
            <button
              onClick={() => handleExport("docx")}
              className="rounded-lg border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50 transition-colors"
            >
              导出 Word
            </button>
            <span className="text-xs text-zinc-400 self-center ml-auto">
              {screenplay.scenes.length} 个场景
            </span>
          </div>

          {/* Screenplay content */}
          <div className="rounded-xl border border-zinc-200 bg-white p-8 space-y-10">
            <h2 className="text-xl font-bold text-center text-zinc-900">
              {screenplay.title}
            </h2>

            {screenplay.scenes.map((scene) => (
              <section key={scene.index} className="space-y-2">
                <h3 className="text-sm font-bold text-zinc-900 border-b border-zinc-100 pb-2">
                  场景 {scene.index}: {scene.setting}
                </h3>

                {scene.elements.map((elem, i) => {
                  const baseStyle = TYPE_STYLES[elem.type] ?? "text-zinc-700";
                  if (elem.type === "character") {
                    return (
                      <p key={i} className={baseStyle}>
                        {elem.content}
                      </p>
                    );
                  }
                  if (elem.type === "dialogue") {
                    return (
                      <p key={i} className={baseStyle}>
                        {elem.content}
                      </p>
                    );
                  }
                  if (elem.type === "parenthetical") {
                    return (
                      <p key={i} className={baseStyle}>
                        ({elem.content})
                      </p>
                    );
                  }
                  return (
                    <p key={i} className={baseStyle}>
                      {elem.content}
                    </p>
                  );
                })}
              </section>
            ))}

            {screenplay.scenes.length === 0 && (
              <p className="text-center text-zinc-400">暂无场景内容</p>
            )}
          </div>
        </>
      )}
    </main>
  );
}
