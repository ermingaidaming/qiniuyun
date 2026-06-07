"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import type { Novel, Screenplay, SceneElementType } from "@/types";
import { exportFile, generateScreenplay, getNovel } from "@/lib/api";
import type { ExportFormat } from "@/lib/api";

const TIME_ICONS: Record<string, string> = {
  "日": "☀️",
  "夜": "🌙",
  "黄昏": "🌅",
  "黎明": "🌄",
};

function SceneElementView({ elem }: { elem: { type: SceneElementType; content: string; character: string | null } }) {
  switch (elem.type) {
    // ── 动作描述：左对齐叙事性文字 ──
    case "action":
      return <p className="text-stone-700 leading-relaxed text-[15px]">{elem.content}</p>;

    // ── 角色出场：居中大字，剧本标准大写风格 ──
    case "character":
      return (
        <p className="text-center text-base font-bold text-stone-900 tracking-[0.3em] mt-6 mb-1">
          {elem.content}
        </p>
      );

    // ── 括号提示：居中斜体 ──
    case "parenthetical":
      return (
        <p className="text-center text-sm text-stone-500 italic mt-1 mb-1">
          （{elem.content}）
        </p>
      );

    // ── 对话：居中窄栏，标注说话人 ──
    case "dialogue":
      return (
        <div className="flex flex-col items-center mt-1 mb-2">
          <span className="text-xs text-stone-400 mb-0.5">{elem.character}</span>
          <p className="max-w-md text-center text-stone-800 leading-relaxed">
            {elem.content}
          </p>
        </div>
      );

    default:
      return <p className="text-stone-700">{elem.content}</p>;
  }
}

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
        if (!cancelled) { setNovel(n); setError(null); }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load novel");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [novelId]);

  function handleRetry() {
    setLoading(true);
    getNovel(novelId)
      .then((n) => { setNovel(n); setError(null); })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load novel"))
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

  // ── Loading ──
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

  // ── Error ──
  if (error && !novel) {
    return (
      <main className="flex flex-1 items-center justify-center px-4">
        <div className="rounded-2xl border border-red-200 bg-red-50/80 p-8 text-sm text-red-700 max-w-md text-center">
          <p className="font-semibold mb-2 text-base">加载失败</p>
          <p>{error}</p>
          <button onClick={handleRetry} className="mt-5 text-red-600 underline underline-offset-4 hover:text-red-800 transition-colors text-sm">
            重试
          </button>
        </div>
      </main>
    );
  }

  // ── Main ──
  return (
    <main className="flex flex-1 flex-col px-4 py-10 max-w-4xl mx-auto w-full">
      {/* Header */}
      <header className="mb-10">
        <Link href="/" className="text-sm text-amber-700 hover:text-amber-700/70 mb-2 inline-block transition-colors">
          ← 返回上传
        </Link>
        <h1 className="text-2xl font-bold text-stone-900">{novel?.title}</h1>
        <p className="text-stone-400 text-sm mt-1">
          {novel?.chapters.length} 个章节 · {novel?.filename}
        </p>
      </header>

      {!screenplay ? (
        <div className="rounded-2xl border border-stone-200 bg-white p-12 text-center">
          <p className="text-stone-500 mb-8 text-lg">AI 将为您的小说生成结构化剧本</p>
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
          {/* ── 剧本片头 ── */}
          <div className="text-center mb-12 py-8">
            <h2 className="text-3xl font-bold text-stone-900 tracking-wide">{screenplay.title}</h2>
            <div className="flex flex-wrap justify-center gap-x-6 gap-y-1 mt-4 text-sm text-stone-500">
              {screenplay.source_novel && <span>原著：《{screenplay.source_novel}》</span>}
              {screenplay.novel_author && <span>作者：{screenplay.novel_author}</span>}
              <span>全 {screenplay.total_chapters || "?"} 章</span>
              {screenplay.generated_by && <span>由 {screenplay.generated_by} 生成</span>}
            </div>
          </div>

          {/* ── 工具栏 ── */}
          <div className="flex flex-wrap items-center gap-2 mb-10 sticky top-2 z-10">
            <div className="flex gap-2 mr-auto">
              <Link href={`/r2/${novelId}`} className="rounded-lg border border-stone-200 bg-white px-3 py-1.5 text-xs font-medium text-stone-500 hover:border-amber-300 hover:text-amber-700 transition-all duration-200">
                R2 改写预览 →
              </Link>
              <Link href={`/har/${novelId}`} className="rounded-lg border border-stone-200 bg-white px-3 py-1.5 text-xs font-medium text-stone-500 hover:border-amber-300 hover:text-amber-700 transition-all duration-200">
                HAR 幻觉审核 →
              </Link>
            </div>
            <div className="flex gap-2">
              <button onClick={() => handleExport("txt")} className="rounded-lg border border-stone-200 bg-white px-3.5 py-1.5 text-xs font-medium text-stone-500 hover:border-amber-300 hover:text-amber-700 transition-all duration-200">TXT</button>
              <button onClick={() => handleExport("docx")} className="rounded-lg border border-stone-200 bg-white px-3.5 py-1.5 text-xs font-medium text-stone-500 hover:border-amber-300 hover:text-amber-700 transition-all duration-200">Word</button>
              <button onClick={() => handleExport("yaml")} className="rounded-lg border border-amber-300 bg-amber-100 px-3.5 py-1.5 text-xs font-semibold text-amber-700 hover:bg-amber-200 transition-all duration-200">YAML</button>
            </div>
            <span className="text-xs text-stone-400 w-full text-right">{screenplay.scenes.length} 个场景</span>
          </div>

          {/* ── 场景列表 ── */}
          <div className="space-y-12">
            {screenplay.scenes.map((scene) => (
              <section key={scene.index} className="group">

                {/* 场景标题行 */}
                <div className="flex items-baseline gap-3 mb-4 pb-3 border-b border-stone-200">
                  <span className="text-lg font-bold text-amber-700 tabular-nums">
                    第{scene.index}场
                  </span>
                  <span className="text-stone-700 font-medium">
                    {scene.setting}
                  </span>
                  <span className="ml-auto text-xs text-stone-400 flex items-center gap-2">
                    {scene.location && <>📍 {scene.location}</>}
                    {scene.time_of_day && <>{TIME_ICONS[scene.time_of_day] ?? ""} {scene.time_of_day}</>}
                  </span>
                </div>

                {/* 出场角色标签 */}
                {scene.characters.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mb-4">
                    {scene.characters.map((ch) => (
                      <span key={ch} className="inline-block text-xs bg-stone-100 text-stone-600 rounded-full px-2.5 py-0.5">
                        {ch}
                      </span>
                    ))}
                  </div>
                )}

                {/* 剧本元素：按 screenplay-industry 视觉规范 */}
                <div className="space-y-3">
                  {scene.elements.map((elem, i) => (
                    <SceneElementView key={i} elem={elem} />
                  ))}
                </div>
              </section>
            ))}
          </div>

          {screenplay.scenes.length === 0 && (
            <div className="rounded-2xl border border-stone-200 bg-white p-12 text-center">
              <p className="text-stone-400 text-lg">暂无场景内容</p>
            </div>
          )}
        </>
      )}
    </main>
  );
}
