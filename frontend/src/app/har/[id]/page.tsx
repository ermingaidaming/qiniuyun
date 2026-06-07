"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import type { HARCategory, HARReport, Novel, SceneElementType, Severity } from "@/types";
import { getNovel, harRefine } from "@/lib/api";

const SEVERITY_STYLES: Record<Severity, string> = {
  critical: "bg-red-100 text-red-700 border-red-200",
  major: "bg-orange-100 text-orange-700 border-orange-200",
  minor: "bg-yellow-100 text-yellow-700 border-yellow-200",
};

const SEVERITY_LABEL: Record<Severity, string> = {
  critical: "严重",
  major: "主要",
  minor: "轻微",
};

const CATEGORY_LABELS: Record<HARCategory, string> = {
  character: "角色",
  event: "事件",
  dialogue: "对话",
  setting: "场景",
  detail: "细节",
};

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

export default function HARPage() {
  const params = useParams();
  const novelId = params.id as string;

  const [novel, setNovel] = useState<Novel | null>(null);
  const [report, setReport] = useState<HARReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [refining, setRefining] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showCorrected, setShowCorrected] = useState(false);

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
    getNovel(novelId).then((n) => { setNovel(n); setError(null); }).catch((e) => setError(e instanceof Error ? e.message : "Failed to load novel")).finally(() => setLoading(false));
  }

  async function handleRefine() {
    setRefining(true);
    setError(null);
    try {
      const r = await harRefine(novelId);
      setReport(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "HAR refine failed");
    } finally {
      setRefining(false);
    }
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
          <button onClick={handleRetry} className="mt-5 text-red-600 underline underline-offset-4 hover:text-red-800 transition-colors text-sm">重试</button>
        </div>
      </main>
    );
  }

  return (
    <main className="flex flex-1 flex-col px-4 py-10 max-w-3xl mx-auto w-full">
      <header className="mb-8">
        <Link href={`/screenplay/${novelId}`} className="text-sm text-accent hover:text-accent/70 mb-2 inline-block transition-colors">
          ← 返回剧本
        </Link>
        <h1 className="text-2xl font-bold text-ink">HAR 幻觉校正审核</h1>
        <p className="text-ink-faint text-sm mt-1">{novel?.title} · {novel?.chapters.length} 个章节</p>
      </header>

      {!report ? (
        <div className="rounded-2xl border border-border bg-card p-10 text-center">
          <p className="text-ink-muted mb-2 text-lg">HAR 幻觉感知自校正引擎</p>
          <p className="text-ink-faint text-sm mb-1">5 类幻觉检测：角色 · 事件 · 对话 · 场景 · 细节</p>
          <p className="text-ink-faint text-xs mb-8">自校正循环：检测 → 文本替换修正 → 再验证（最多 2 轮）</p>
          <button
            onClick={handleRefine}
            disabled={refining}
            className="rounded-xl bg-accent px-8 py-3.5 text-sm font-semibold text-white hover:bg-accent/85 disabled:opacity-50 transition-all duration-200 hover:shadow-lg active:scale-[0.98]"
          >
            {refining ? "HAR 正在检测校正..." : "开始 HAR 检测"}
          </button>
          {error && <p className="mt-5 text-sm text-red-600">{error}</p>}
        </div>
      ) : (
        <>
          {/* Report overview */}
          <div className="rounded-2xl border border-border bg-card p-5 mb-6">
            <div className="flex flex-wrap justify-center gap-x-6 gap-y-1 text-sm">
              <span className="text-ink-muted">
                检查 <span className="font-semibold text-ink">{report.total_scenes}</span> 个场景
              </span>
              <span className={report.total_findings > 0 ? "text-red-600 font-semibold" : "text-green-600 font-semibold"}>
                发现 {report.total_findings} 处幻觉
              </span>
              <span className="text-ink-muted">
                自校正 <span className="font-semibold text-ink">{report.verification_rounds}</span> 轮
              </span>
            </div>
          </div>

          {/* Findings list */}
          {report.findings.length > 0 && (
            <div className="space-y-4 mb-6">
              <h2 className="text-lg font-bold text-ink">检测到的幻觉</h2>
              {report.findings.map((f, i) => (
                <div key={i} className="rounded-2xl border border-border bg-card p-5 shadow-sm">
                  <div className="flex items-center gap-2 mb-3">
                    <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full border ${SEVERITY_STYLES[f.severity]}`}>
                      {SEVERITY_LABEL[f.severity]}
                    </span>
                    <span className="text-xs text-ink-faint">
                      {CATEGORY_LABELS[f.category]} · 场景 {f.scene_index}
                    </span>
                  </div>
                  <p className="text-sm text-ink-muted mb-4">{f.description}</p>

                  {f.hallucinated_text && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
                      <div className="rounded-xl bg-red-50/70 border border-red-100 p-3.5">
                        <p className="text-xs text-red-500 mb-1.5 font-semibold">幻觉文本</p>
                        <p className="text-sm text-red-700 line-through">{f.hallucinated_text}</p>
                      </div>
                      <div className="rounded-xl bg-green-50/70 border border-green-100 p-3.5">
                        <p className="text-xs text-green-600 mb-1.5 font-semibold">建议修正</p>
                        <p className="text-sm text-green-800">{f.suggested_fix}</p>
                      </div>
                    </div>
                  )}

                  {f.source_evidence && (
                    <div className="rounded-xl bg-paper-dark/50 border border-border p-3.5">
                      <p className="text-xs text-ink-faint mb-1.5 font-semibold">原文依据</p>
                      <p className="text-sm text-ink-muted">{f.source_evidence}</p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {report.total_findings === 0 && (
            <div className="rounded-2xl border border-green-200 bg-green-50/80 p-8 text-center mb-6">
              <p className="text-green-700 font-semibold text-lg">✅ 未检测到幻觉</p>
              <p className="text-sm text-green-600 mt-1">剧本内容与原文一致，通过审核</p>
            </div>
          )}

          {/* Corrected scenes toggle */}
          {report.corrected_scenes.length > 0 && (
            <>
              <button
                onClick={() => setShowCorrected(!showCorrected)}
                className="rounded-xl border border-border bg-card px-5 py-2.5 text-sm font-medium text-ink-muted hover:border-accent-soft hover:text-accent transition-all duration-200 self-start mb-4"
              >
                {showCorrected ? "隐藏" : "查看"}修正后剧本 ({report.corrected_scenes.length} 个场景)
              </button>

              {showCorrected && (
                <div className="space-y-6">
                  {report.corrected_scenes.map((scene) => (
                    <section key={scene.index} className="rounded-2xl border border-border bg-card p-6 shadow-sm">
                      <h3 className="text-sm font-bold text-ink border-b border-border pb-3 mb-4 flex items-baseline gap-2">
                        <span className="text-ink-faint font-mono text-xs">#{scene.index}</span>
                        {scene.setting && <span>{scene.setting}</span>}
                      </h3>
                      <div className="space-y-2">
                        {scene.elements.map((elem, j) => {
                          const badge = TYPE_BADGES[elem.type] ?? TYPE_BADGES.action;
                          const chip = (
                            <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border shrink-0 select-none w-10 text-center ${badge.cls}`}>
                              {badge.label}
                            </span>
                          );
                          if (elem.type === "character") {
                            return (
                              <div key={j} className="flex items-center gap-2.5">
                                {chip}
                                <span className="font-bold text-ink text-sm tracking-wide">{elem.content}</span>
                              </div>
                            );
                          }
                          if (elem.type === "dialogue") {
                            return (
                              <div key={j} className="flex items-start gap-2.5">
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
                              <div key={j} className="flex items-center gap-2.5">
                                {chip}
                                <span className="text-sm text-ink-muted italic">（{elem.content}）</span>
                              </div>
                            );
                          }
                          return (
                            <div key={j} className="flex items-start gap-2.5">
                              {chip}
                              <span className="text-ink leading-relaxed">{elem.content}</span>
                            </div>
                          );
                        })}
                      </div>
                    </section>
                  ))}
                </div>
              )}
            </>
          )}
        </>
      )}
    </main>
  );
}
