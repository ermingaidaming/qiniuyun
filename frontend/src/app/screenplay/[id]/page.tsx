"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import type { Novel, Screenplay, SceneElementType } from "@/types";
import { exportFile, generateScreenplay, getNovel } from "@/lib/api";
import type { ExportFormat } from "@/lib/api";

const TYPE_STYLES: Record<SceneElementType, string> = {
  action: "text-zinc-700 leading-relaxed",
  character: "text-center font-bold text-zinc-900 uppercase tracking-wide mt-4",
  dialogue: "mx-8 leading-relaxed text-zinc-800",
  parenthetical: "mx-12 text-sm text-zinc-500 italic",
};

const TIME_ICONS: Record<string, string> = {
  "日": "☀️",
  "夜": "🌙",
  "黄昏": "🌅",
  "黎明": "🌄",
};

export default function ScreenplayPage() {
  const params = useParams();
  const novelId = params.id as string;

  const [novel, setNovel] = useState<Novel | null>(null);
  const [screenplay, setScreenplay] = useState<Screenplay | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setLoading(true);
        const n = await getNovel(novelId);
        if (!cancelled) {
          setNovel(n);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Failed to load novel");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [novelId]);

  function handleRetry() {
    setLoading(true);
    getNovel(novelId)
      .then((n) => {
        setNovel(n);
        setError(null);
      })
      .catch((e) => {
        setError(e instanceof Error ? e.message : "Failed to load novel");
      })
      .finally(() => setLoading(false));
  }

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

  async function handleExport(format: ExportFormat) {
    if (!screenplay) return;
    await exportFile(screenplay.id, format);
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
            onClick={handleRetry}
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
        <Link href="/" className="text-sm text-teal-600 hover:text-teal-700 mb-2 inline-block">
          ← 返回上传
        </Link>
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
          {/* Screenplay metadata */}
          <div className="rounded-xl border border-zinc-200 bg-white p-6 mb-6">
            <h2 className="text-xl font-bold text-center text-zinc-900 mb-4">
              {screenplay.title}
            </h2>
            <div className="flex flex-wrap justify-center gap-x-6 gap-y-1 text-sm text-zinc-500">
              {screenplay.source_novel && (
                <span>原著：{screenplay.source_novel}</span>
              )}
              {screenplay.novel_author && (
                <span>作者：{screenplay.novel_author}</span>
              )}
              <span>共 {screenplay.total_chapters || "?"} 章</span>
              {screenplay.generated_by && (
                <span>生成引擎：{screenplay.generated_by}</span>
              )}
            </div>
          </div>

          {/* Pipeline navigation */}
          <div className="flex gap-2 mb-4">
            <Link
              href={`/r2/${novelId}`}
              className="rounded-lg border border-zinc-200 px-3 py-1.5 text-xs font-medium text-zinc-500 hover:border-teal-300 hover:text-teal-600 transition-colors"
            >
              R2 改写预览 →
            </Link>
            <Link
              href={`/har/${novelId}`}
              className="rounded-lg border border-zinc-200 px-3 py-1.5 text-xs font-medium text-zinc-500 hover:border-teal-300 hover:text-teal-600 transition-colors"
            >
              HAR 幻觉审核 →
            </Link>
          </div>

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
            <button
              onClick={() => handleExport("yaml")}
              className="rounded-lg border border-teal-300 px-4 py-2 text-sm font-medium text-teal-700 hover:bg-teal-50 transition-colors"
            >
              导出 YAML
            </button>
            <span className="text-xs text-zinc-400 self-center ml-auto">
              {screenplay.scenes.length} 个场景
            </span>
          </div>

          {/* Scene list */}
          <div className="space-y-8">
            {screenplay.scenes.map((scene) => (
              <section key={scene.index} className="rounded-xl border border-zinc-200 bg-white p-6">
                {/* Scene header */}
                <h3 className="text-sm font-bold text-zinc-900 border-b border-zinc-100 pb-3 mb-4">
                  场景 {scene.index}
                  {scene.setting && <>: {scene.setting}</>}
                </h3>

                {/* Scene metadata */}
                <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-zinc-400 mb-4">
                  {scene.location && (
                    <span>📍 {scene.location}</span>
                  )}
                  {scene.time_of_day && (
                    <span>
                      {TIME_ICONS[scene.time_of_day] ?? "🕐"} {scene.time_of_day}
                    </span>
                  )}
                  {scene.source_chapter > 0 && (
                    <span>📖 第 {scene.source_chapter} 章</span>
                  )}
                  {scene.characters.length > 0 && (
                    <span>🎭 {scene.characters.join("、")}</span>
                  )}
                </div>

                {/* Scene elements */}
                <div className="space-y-1">
                  {scene.elements.map((elem, i) => {
                    const baseStyle = TYPE_STYLES[elem.type] ?? "text-zinc-700";
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
                </div>
              </section>
            ))}
          </div>

          {screenplay.scenes.length === 0 && (
            <div className="rounded-xl border border-zinc-200 bg-white p-8 text-center">
              <p className="text-zinc-400">暂无场景内容</p>
            </div>
          )}
        </>
      )}
    </main>
  );
}
