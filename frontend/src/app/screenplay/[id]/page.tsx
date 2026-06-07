"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import type { Novel, Screenplay, SceneElementType } from "@/types";
import { exportFile, generateScreenplay, getNovel } from "@/lib/api";
import type { ExportFormat } from "@/lib/api";

const TYPE_STYLES: Record<SceneElementType, string> = {
  action: "text-ink leading-relaxed",
  character: "text-center font-bold text-ink tracking-wider mt-4 text-sm",
  dialogue: "mx-10 leading-relaxed text-ink/90",
  parenthetical: "mx-14 text-sm text-ink-muted italic",
};

const TYPE_BADGES: Record<SceneElementType, { label: string; cls: string }> = {
  action:    { label: "动作", cls: "bg-blue-50 text-blue-600 border-blue-200" },
  character: { label: "角色", cls: "bg-amber-50 text-amber-600 border-amber-200" },
  dialogue:  { label: "对话", cls: "bg-emerald-50 text-emerald-600 border-emerald-200" },
  parenthetical: { label: "提示", cls: "bg-purple-50 text-purple-500 border-purple-200" },
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
        <div className="flex items-center gap-2 text-ink-faint">
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-accent-soft animate-bounce" style={{ animationDelay: "0ms" }} />
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-accent-soft animate-bounce" style={{ animationDelay: "150ms" }} />
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-accent-soft animate-bounce" style={{ animationDelay: "300ms" }} />
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
        <Link href="/" className="text-sm text-accent hover:text-accent/70 mb-2 inline-block transition-colors">
          ← 返回上传
        </Link>
        <h1 className="text-2xl font-bold text-ink">{novel?.title}</h1>
        <p className="text-ink-faint text-sm mt-1">
          {novel?.chapters.length} 个章节 · {novel?.filename}
        </p>
      </header>

      {!screenplay ? (
        <div className="rounded-2xl border border-border bg-card p-10 text-center">
          <p className="text-ink-muted mb-8 text-lg">
            AI 将为您的小说生成结构化剧本
          </p>
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="rounded-xl bg-accent px-8 py-3.5 text-sm font-semibold text-white hover:bg-accent/85 disabled:opacity-50 transition-all duration-200 hover:shadow-lg active:scale-[0.98]"
          >
            {generating ? "AI 正在生成剧本..." : "生成剧本"}
          </button>
          {error && <p className="mt-5 text-sm text-red-600">{error}</p>}
        </div>
      ) : (
        <>
          {/* Screenplay metadata */}
          <div className="rounded-2xl border border-border bg-card p-6 mb-6">
            <h2 className="text-xl font-bold text-center text-ink mb-4">
              {screenplay.title}
            </h2>
            <div className="flex flex-wrap justify-center gap-x-6 gap-y-1 text-sm text-ink-muted">
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
                className="rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-medium text-ink-muted hover:border-accent-soft hover:text-accent transition-all duration-200"
              >
                R2 改写预览 →
              </Link>
              <Link
                href={`/har/${novelId}`}
                className="rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-medium text-ink-muted hover:border-accent-soft hover:text-accent transition-all duration-200"
              >
                HAR 幻觉审核 →
              </Link>
            </div>
            <div className="flex gap-2">
              <button onClick={() => handleExport("txt")} className="rounded-lg border border-border bg-card px-3.5 py-1.5 text-xs font-medium text-ink-muted hover:border-accent-soft hover:text-accent transition-all duration-200">TXT</button>
              <button onClick={() => handleExport("docx")} className="rounded-lg border border-border bg-card px-3.5 py-1.5 text-xs font-medium text-ink-muted hover:border-accent-soft hover:text-accent transition-all duration-200">Word</button>
              <button onClick={() => handleExport("yaml")} className="rounded-lg border border-accent-soft bg-accent-soft/10 px-3.5 py-1.5 text-xs font-semibold text-accent hover:bg-accent-soft/20 transition-all duration-200">YAML</button>
            </div>
            <span className="text-xs text-ink-faint w-full text-right">{screenplay.scenes.length} 个场景</span>
          </div>

          {/* Scene list */}
          <div className="space-y-6">
            {screenplay.scenes.map((scene) => (
              <section key={scene.index} className="rounded-2xl border border-border bg-card p-6 shadow-sm">
                <h3 className="text-sm font-bold text-ink border-b border-border pb-3 mb-4 flex items-baseline gap-2">
                  <span className="text-ink-faint font-mono text-xs">#{scene.index}</span>
                  {scene.setting && <span>{scene.setting}</span>}
                </h3>

                <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-faint mb-4">
                  {scene.location && <span>📍 {scene.location}</span>}
                  {scene.time_of_day && <span>{TIME_ICONS[scene.time_of_day] ?? "🕐"} {scene.time_of_day}</span>}
                  {scene.source_chapter > 0 && <span>📖 第 {scene.source_chapter} 章</span>}
                  {scene.characters.length > 0 && <span>🎭 {scene.characters.join("、")}</span>}
                </div>

                <div className="space-y-2">
                  {scene.elements.map((elem, i) => {
                    const badge = TYPE_BADGES[elem.type] ?? TYPE_BADGES.action;
                    const chip = (
                      <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border shrink-0 select-none w-10 text-center ${badge.cls}`}>
                        {badge.label}
                      </span>
                    );
                    if (elem.type === "character") {
                      return (
                        <div key={i} className="flex items-center gap-2.5">
                          {chip}
                          <span className="font-bold text-ink text-sm tracking-wide">{elem.content}</span>
                        </div>
                      );
                    }
                    if (elem.type === "dialogue") {
                      return (
                        <div key={i} className="flex items-start gap-2.5">
                          {chip}
                          <span className="text-ink/90 leading-relaxed">
                            <span className="font-semibold text-ink/70">{elem.character || "?"}</span>
                            <span className="text-ink/30 select-none">：「</span>
                            {elem.content}
                            <span className="text-ink/30 select-none">」</span>
                          </span>
                        </div>
                      );
                    }
                    if (elem.type === "parenthetical") {
                      return (
                        <div key={i} className="flex items-center gap-2.5">
                          {chip}
                          <span className="text-sm text-ink-muted italic">（{elem.content}）</span>
                        </div>
                      );
                    }
                    return (
                      <div key={i} className="flex items-start gap-2.5">
                        {chip}
                        <span className="text-ink leading-relaxed">{elem.content}</span>
                      </div>
                    );
                  })}
                </div>
              </section>
            ))}
          </div>

          {screenplay.scenes.length === 0 && (
            <div className="rounded-2xl border border-border bg-card p-10 text-center">
              <p className="text-ink-faint">暂无场景内容</p>
            </div>
          )}
        </>
      )}
    </main>
  );
}
