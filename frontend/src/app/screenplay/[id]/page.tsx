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

/* ─── Element Block Grouper ─── */
function SceneContent({ elements }: { elements: { type: SceneElementType; content: string; character: string | null }[] }) {
  type Elem = { type: SceneElementType; content: string; character: string | null };
  const blocks: { speaker: string | null; items: Elem[] }[] = [];
  let currentSpeaker: string | null = null;
  let currentItems: Elem[] = [];

  function flush() {
    if (currentItems.length > 0) { blocks.push({ speaker: currentSpeaker, items: [...currentItems] }); currentItems = []; }
  }
  for (const e of elements) {
    if (e.type === "action") { flush(); blocks.push({ speaker: null, items: [e] }); }
    else if (e.type === "character") { flush(); currentSpeaker = e.content; }
    else { if (!currentSpeaker && e.character) currentSpeaker = e.character; currentItems.push(e); }
  }
  flush();

  return (
    <div className="space-y-5">
      {blocks.map((block, bi) =>
        block.speaker === null ? (
          <p key={bi} className="text-stone-600 leading-relaxed text-[15px] indent-8">
            {block.items[0]?.content}
          </p>
        ) : (
          <div key={bi} className="flex flex-col items-center mt-5">
            <p className="text-base font-bold text-stone-900 tracking-[0.2em] mb-1.5">{block.speaker}</p>
            {block.items.map((item, ii) =>
              item.type === "parenthetical" ? (
                <p key={ii} className="text-sm text-stone-500 italic mb-1">（{item.content}）</p>
              ) : (
                <p key={ii} className="max-w-md text-center text-stone-700 leading-relaxed mb-1.5">{item.content}</p>
              )
            )}
          </div>
        )
      )}
    </div>
  );
}

/* ─── Field Label (always visible) ─── */
function Field({ label, value, fallback }: { label: string; value?: string; fallback?: string }) {
  const display = value || fallback || "(无)";
  return (
    <span>
      <span className="mr-1 text-stone-400">{label}</span>
      <span className={value ? "text-stone-700" : "text-stone-300 italic"}>{display}</span>
    </span>
  );
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
      try { setLoading(true); const n = await getNovel(novelId); if (!cancelled) { setNovel(n); setError(null); } }
      catch (e) { if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load novel"); }
      finally { if (!cancelled) setLoading(false); }
    })();
    return () => { cancelled = true; };
  }, [novelId]);

  function handleRetry() {
    setLoading(true);
    getNovel(novelId).then((n) => { setNovel(n); setError(null); }).catch((e) => setError(e instanceof Error ? e.message : "Failed to load novel")).finally(() => setLoading(false));
  }

  async function handleGenerate() {
    setGenerating(true); setError(null);
    try { const sp = await generateScreenplay(novelId); setScreenplay(sp); }
    catch (e) { setError(e instanceof Error ? e.message : "Generation failed"); }
    finally { setGenerating(false); }
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
          <button onClick={handleRetry} className="mt-5 text-red-600 underline underline-offset-4 hover:text-red-800 transition-colors text-sm">重试</button>
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
          {/* ═══════════ Screenplay 元信息 ═══════════ */}
          <div className="rounded-2xl border border-stone-200 bg-white p-6 mb-8">
            <div className="text-center mb-4">
              <h2 className="text-3xl font-bold text-stone-900 tracking-wide">{screenplay.title}</h2>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-x-6 gap-y-2 text-sm">
              <Field label="剧本ID:" value={screenplay.id.slice(0, 8) + "..."} />
              <Field label="小说ID:" value={screenplay.novel_id.slice(0, 8) + "..."} />
              <Field label="原著:" value={screenplay.source_novel} />
              <Field label="作者:" value={screenplay.novel_author} fallback="佚名" />
              <Field label="总章节数:" value={String(screenplay.total_chapters || "")} fallback="未知" />
              <Field label="生成引擎:" value={screenplay.generated_by} />
              <Field label="场景数:" value={screenplay.scenes.length + " 场"} />
            </div>
          </div>

          {/* ═══════════ 工具栏 ═══════════ */}
          <div className="flex flex-wrap items-center gap-2 mb-10 sticky top-2 z-10">
            <div className="flex gap-2 mr-auto">
              <Link href={`/r2/${novelId}`} className="rounded-lg border border-stone-200 bg-white px-3 py-1.5 text-xs font-medium text-stone-500 hover:border-amber-300 hover:text-amber-700 transition-all duration-200">R2 改写预览 →</Link>
              <Link href={`/har/${novelId}`} className="rounded-lg border border-stone-200 bg-white px-3 py-1.5 text-xs font-medium text-stone-500 hover:border-amber-300 hover:text-amber-700 transition-all duration-200">HAR 幻觉审核 →</Link>
            </div>
            <div className="flex gap-2">
              <button onClick={() => handleExport("txt")} className="rounded-lg border border-stone-200 bg-white px-3.5 py-1.5 text-xs font-medium text-stone-500 hover:border-amber-300 hover:text-amber-700 transition-all duration-200">TXT</button>
              <button onClick={() => handleExport("docx")} className="rounded-lg border border-stone-200 bg-white px-3.5 py-1.5 text-xs font-medium text-stone-500 hover:border-amber-300 hover:text-amber-700 transition-all duration-200">Word</button>
              <button onClick={() => handleExport("yaml")} className="rounded-lg border border-amber-300 bg-amber-100 px-3.5 py-1.5 text-xs font-semibold text-amber-700 hover:bg-amber-200 transition-all duration-200">YAML</button>
            </div>
          </div>

          {/* ═══════════ 场景列表 ═══════════ */}
          <div className="space-y-12">
            {screenplay.scenes.map((scene) => (
              <section key={scene.index} className="group">
                {/* ── 场景标题 ── */}
                <div className="mb-5 pb-3 border-b border-stone-200">
                  <div className="flex items-baseline gap-3 mb-2">
                    <span className="text-lg font-bold text-amber-700 tabular-nums">第{scene.index}场</span>
                    <span className="text-stone-700 font-medium text-lg">{scene.setting || "(无场景标题)"}</span>
                  </div>
                  {/* 场景元信息：所有字段始终渲染 */}
                  <div className="flex flex-wrap items-center gap-x-4 gap-y-0.5 text-xs">
                    <span>
                      <span className="text-stone-400">地点: </span>
                      <span className={scene.location ? "text-stone-700" : "text-stone-300 italic"}>{scene.location || "(无)"}</span>
                    </span>
                    <span>
                      <span className="text-stone-400">时间: </span>
                      <span className={scene.time_of_day ? "text-stone-700" : "text-stone-300 italic"}>
                        {scene.time_of_day ? <>{TIME_ICONS[scene.time_of_day] ?? ""} {scene.time_of_day}</> : "(无)"}
                      </span>
                    </span>
                    <span>
                      <span className="text-stone-400">来源章节: </span>
                      <span className={scene.source_chapter > 0 ? "text-stone-700" : "text-stone-300 italic"}>
                        {scene.source_chapter > 0 ? `第 ${scene.source_chapter} 章` : "(无)"}
                      </span>
                    </span>
                    <span className="ml-auto text-stone-400">
                      {scene.elements.length} 元素
                    </span>
                  </div>
                </div>

                {/* ── 出场角色 ── */}
                <div className="flex flex-wrap items-center gap-1.5 mb-4">
                  <span className="text-xs text-stone-400 mr-1">出场:</span>
                  {scene.characters.length > 0
                    ? scene.characters.map((ch) => (
                        <span key={ch} className="inline-block text-xs bg-stone-100 text-stone-600 rounded-full px-2.5 py-0.5">{ch}</span>
                      ))
                    : <span className="text-xs text-stone-300 italic">(无)</span>
                  }
                </div>

                {/* ── 剧本正文 ── */}
                <SceneContent elements={scene.elements} />
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
