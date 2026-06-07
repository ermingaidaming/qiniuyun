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

const CATEGORY_LABELS: Record<HARCategory, string> = {
  character: "角色",
  event: "事件",
  dialogue: "对话",
  setting: "场景",
  detail: "细节",
};

const TYPE_STYLES: Record<SceneElementType, string> = {
  action: "text-zinc-700 leading-relaxed",
  character: "text-center font-bold text-zinc-900 uppercase tracking-wide mt-4",
  dialogue: "mx-8 leading-relaxed text-zinc-800",
  parenthetical: "mx-12 text-sm text-zinc-500 italic",
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
      <header className="mb-8">
        <Link href={`/screenplay/${novelId}`} className="text-sm text-teal-600 hover:text-teal-700 mb-2 inline-block">
          ← 返回剧本
        </Link>
        <h1 className="text-2xl font-bold text-zinc-900">HAR 幻觉校正审核</h1>
        <p className="text-sm text-zinc-500 mt-1">
          {novel?.title} · {novel?.chapters.length} 个章节
        </p>
      </header>

      {!report ? (
        <div className="rounded-xl border border-zinc-200 bg-white p-8 text-center">
          <p className="text-zinc-600 mb-2">
            HAR 将逐场景对比原文，检测 5 类幻觉并自动修正
          </p>
          <p className="text-xs text-zinc-400 mb-1">
            检测类型：角色错误、事件虚构、对话篡改、场景偏差、细节不一致
          </p>
          <p className="text-xs text-zinc-400 mb-6">
            自校正循环：检测 → 文本替换修正 → 再验证（最多 2 轮）
          </p>
          <button
            onClick={handleRefine}
            disabled={refining}
            className="rounded-lg bg-teal-600 px-8 py-3 text-sm font-semibold text-white hover:bg-teal-700 disabled:opacity-50 transition-colors"
          >
            {refining ? "HAR 正在检测校正..." : "开始 HAR 检测"}
          </button>
          {error && (
            <p className="mt-4 text-sm text-red-600">{error}</p>
          )}
        </div>
      ) : (
        <>
          {/* Report overview */}
          <div className="rounded-xl border border-zinc-200 bg-white p-6 mb-6">
            <div className="flex flex-wrap justify-center gap-x-6 gap-y-1 text-sm">
              <span className="text-zinc-500">
                检查 <span className="font-semibold text-zinc-900">{report.total_scenes}</span> 个场景
              </span>
              <span className={report.total_findings > 0 ? "text-red-500" : "text-green-500"}>
                发现 <span className="font-semibold">{report.total_findings}</span> 处幻觉
              </span>
              <span className="text-zinc-500">
                自校正 <span className="font-semibold text-zinc-900">{report.verification_rounds}</span> 轮
              </span>
            </div>
          </div>

          {/* Findings list */}
          {report.findings.length > 0 && (
            <div className="space-y-4 mb-6">
              <h2 className="text-lg font-bold text-zinc-900">检测到的幻觉</h2>
              {report.findings.map((f, i) => (
                <div key={i} className="rounded-xl border border-zinc-200 bg-white p-5">
                  <div className="flex items-center gap-2 mb-3">
                    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${SEVERITY_STYLES[f.severity]}`}>
                      {f.severity === "critical" ? "严重" : f.severity === "major" ? "主要" : "轻微"}
                    </span>
                    <span className="text-xs text-zinc-400">
                      {CATEGORY_LABELS[f.category]} · 场景 {f.scene_index}
                    </span>
                  </div>
                  <p className="text-sm text-zinc-700 mb-3">{f.description}</p>

                  {f.hallucinated_text && (
                    <div className="grid grid-cols-2 gap-3 mb-3">
                      <div className="rounded-lg bg-red-50 border border-red-100 p-3">
                        <p className="text-xs text-red-500 mb-1 font-semibold">幻觉文本</p>
                        <p className="text-sm text-red-700 line-through">{f.hallucinated_text}</p>
                      </div>
                      <div className="rounded-lg bg-green-50 border border-green-100 p-3">
                        <p className="text-xs text-green-500 mb-1 font-semibold">建议修正</p>
                        <p className="text-sm text-green-700">{f.suggested_fix}</p>
                      </div>
                    </div>
                  )}

                  {f.source_evidence && (
                    <div className="rounded-lg bg-zinc-50 border border-zinc-100 p-3">
                      <p className="text-xs text-zinc-400 mb-1 font-semibold">原文依据</p>
                      <p className="text-sm text-zinc-600">{f.source_evidence}</p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {report.total_findings === 0 && (
            <div className="rounded-xl border border-green-200 bg-green-50 p-6 text-center mb-6">
              <p className="text-green-700 font-semibold">✅ 未检测到幻觉</p>
              <p className="text-sm text-green-500 mt-1">剧本内容与原文一致</p>
            </div>
          )}

          {/* Corrected scenes toggle */}
          {report.corrected_scenes.length > 0 && (
            <>
              <button
                onClick={() => setShowCorrected(!showCorrected)}
                className="rounded-lg border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50 transition-colors self-start mb-4"
              >
                {showCorrected ? "隐藏" : "查看"}修正后剧本 ({report.corrected_scenes.length} 个场景)
              </button>

              {showCorrected && (
                <div className="space-y-8">
                  {report.corrected_scenes.map((scene) => (
                    <section key={scene.index} className="rounded-xl border border-zinc-200 bg-white p-6">
                      <h3 className="text-sm font-bold text-zinc-900 border-b border-zinc-100 pb-3 mb-4">
                        场景 {scene.index}
                        {scene.setting && <>: {scene.setting}</>}
                      </h3>

                      <div className="space-y-1">
                        {scene.elements.map((elem, j) => {
                          const baseStyle = TYPE_STYLES[elem.type] ?? "text-zinc-700";
                          if (elem.type === "parenthetical") {
                            return <p key={j} className={baseStyle}>({elem.content})</p>;
                          }
                          return <p key={j} className={baseStyle}>{elem.content}</p>;
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
