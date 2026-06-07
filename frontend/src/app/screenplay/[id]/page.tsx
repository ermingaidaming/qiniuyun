"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import type { Novel, Screenplay, SceneElementType } from "@/types";
import { exportFile, generateScreenplay, getNovel } from "@/lib/api";
import type { ExportFormat } from "@/lib/api";

const TYPE_STYLES: Record<SceneElementType, string> = {
  action: "text-stone-900 leading-relaxed",
  character: "text-center font-bold text-stone-900 tracking-wider mt-4 text-sm",
  dialogue: "mx-10 leading-relaxed text-stone-900/90",
  parenthetical: "mx-14 text-sm text-stone-500 italic",
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
        <div className="flex items-center gap-2 text-stone-400">
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-amber-200 animate-bounce" style={{ animationDelay: "0ms" }} />
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-amber-200 animate-bounce" style={{ animationDelay: "150ms" }} />
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-amber-200 animate-bounce" style={{ animationDelay: "300ms" }} />
        </div>
      </main>
    );
  }

  if (error && !novel) {
    return (
      <main className="flex flex-1 items-center justify-center px-4">
        <div className="rounded-2xl border border-red-200 bg-red-50/80 p-8 text-sm text-red-700 max-w-md text-center">
          <p className="font-semibold mb-2 text-base">加载失败</p>
          <p>{error}</p>
          <button
            onClick={handleRetry}
            className="mt-5 text-red-600 underline underline-offset-4 hover:text-red-800 transition-colors text-sm"
          >
            重试
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className="flex flex-1 flex-col px-4 py-10 max-w-3xl mx-auto w-full">
      {/* Header */}
      <header className="mb-8">
        <Link href="/" className="text-sm text-amber-700 hover:text-amber-700/70 mb-2 inline-block transition-colors">
          ← 返回上传
        </Link>
        <h1 className="text-2xl font-bold text-stone-900">{novel?.title}</h1>
        <p className="text-stone-400 text-sm mt-1">
          {novel?.chapters.length} 个章节 · {novel?.filename}
        </p>
      </header>

      {!screenplay ? (
        <div className="rounded-2xl border border-stone-200 bg-white p-10 text-center">
          <p className="text-stone-500 mb-8 text-lg">
            AI 将为您的小说生成结构化剧本
          </p>
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="rounded-xl bg-amber-700 px-8 py-3.5 text-sm font-semibold text-white hover:bg-amber-800 disabled:opacity-50 transition-all duration-200 hover:shadow-lg active:scale-[0.98]"
          >
            {generating ? "AI 正在生成剧本..." : "生成剧本"}
          </button>
          {error && <p className="mt-5 text-sm text-red-600">{error}</p>}
        </div>
      ) : (
        <>
          {/* Screenplay metadata */}
          <div className="rounded-2xl border border-stone-200 bg-white p-6 mb-6">
            <h2 className="text-xl font-bold text-center text-stone-900 mb-4">
              {screenplay.title}
            </h2>
            <div className="flex flex-wrap justify-center gap-x-6 gap-y-1 text-sm text-stone-500">
              {screenplay.source_novel && <span>原著：{screenplay.source_novel}</span>}
              {screenplay.novel_author && <span>作者：{screenplay.novel_author}</span>}
              <span>共 {screenplay.total_chapters || "?"} 章</span>
              {screenplay.generated_by && <span>引擎：{screenplay.generated_by}</span>}
            </div>
          </div>

          {/* Pipeline + Export toolbar */}
          <div className="flex flex-wrap items-center gap-2 mb-6">
            <div className="flex gap-2 mr-auto">
              <Link
                href={`/r2/${novelId}`}
                className="rounded-lg border border-stone-200 bg-white px-3 py-1.5 text-xs font-medium text-stone-500 hover:border-amber-300 hover:text-amber-700 transition-all duration-200"
              >
                R2 改写预览 →
              </Link>
              <Link
                href={`/har/${novelId}`}
                className="rounded-lg border border-stone-200 bg-white px-3 py-1.5 text-xs font-medium text-stone-500 hover:border-amber-300 hover:text-amber-700 transition-all duration-200"
              >
                HAR 幻觉审核 →
              </Link>
            </div>
            <div className="flex gap-2">
              <button onClick={() => handleExport("txt")} className="rounded-lg border border-stone-200 bg-white px-3.5 py-1.5 text-xs font-medium text-stone-500 hover:border-amber-300 hover:text-amber-700 transition-all duration-200">TXT</button>
              <button onClick={() => handleExport("docx")} className="rounded-lg border border-stone-200 bg-white px-3.5 py-1.5 text-xs font-medium text-stone-500 hover:border-amber-300 hover:text-amber-700 transition-all duration-200">Word</button>
              <button onClick={() => handleExport("yaml")} className="rounded-lg border border-amber-300 bg-amber-100 px-3.5 py-1.5 text-xs font-semibold text-amber-700 hover:bg-amber-100 transition-all duration-200">YAML</button>
            </div>
            <span className="text-xs text-stone-400 w-full text-right">{screenplay.scenes.length} 个场景</span>
          </div>

          {/* Scene list */}
          <div className="space-y-6">
            {screenplay.scenes.map((scene) => (
              <section key={scene.index} className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
                <h3 className="text-sm font-bold text-stone-900 border-b border-stone-200 pb-3 mb-4 flex items-baseline gap-2">
                  <span className="text-stone-400 font-mono text-xs">#{scene.index}</span>
                  {scene.setting && <span>{scene.setting}</span>}
                </h3>

                <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-stone-400 mb-4">
                  {scene.location && <span>📍 {scene.location}</span>}
                  {scene.time_of_day && <span>{TIME_ICONS[scene.time_of_day] ?? "🕐"} {scene.time_of_day}</span>}
                  {scene.source_chapter > 0 && <span>📖 第 {scene.source_chapter} 章</span>}
                  {scene.characters.length > 0 && <span>🎭 {scene.characters.join("、")}</span>}
                </div>

                <div className="space-y-1">
                  {scene.elements.map((elem, i) => {
                    const cls = TYPE_STYLES[elem.type] ?? "text-stone-900";
                    if (elem.type === "parenthetical") {
                      return <p key={i} className={cls}>({elem.content})</p>;
                    }
                    return <p key={i} className={cls}>{elem.content}</p>;
                  })}
                </div>
              </section>
            ))}
          </div>

          {screenplay.scenes.length === 0 && (
            <div className="rounded-2xl border border-stone-200 bg-white p-10 text-center">
              <p className="text-stone-400">暂无场景内容</p>
            </div>
          )}
        </>
      )}
    </main>
  );
}
