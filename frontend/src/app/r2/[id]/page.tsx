"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import type { Novel, R2ScanResult, SceneElementType } from "@/types";
import { getNovel, r2Scan } from "@/lib/api";

const TYPE_STYLES: Record<SceneElementType, string> = {
  action: "text-stone-900 leading-relaxed",
  character: "text-center font-bold text-stone-900 tracking-wider mt-4 text-sm",
  dialogue: "mx-10 leading-relaxed text-stone-900/90",
  parenthetical: "mx-14 text-sm text-stone-500 italic",
};

export default function R2Page() {
  const params = useParams();
  const novelId = params.id as string;

  const [novel, setNovel] = useState<Novel | null>(null);
  const [result, setResult] = useState<R2ScanResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
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
    getNovel(novelId).then((n) => { setNovel(n); setError(null); }).catch((e) => setError(e instanceof Error ? e.message : "Failed to load novel")).finally(() => setLoading(false));
  }

  async function handleScan() {
    setScanning(true);
    setError(null);
    try {
      const r = await r2Scan(novelId);
      setResult(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "R2 scan failed");
    } finally {
      setScanning(false);
    }
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
          <button onClick={handleRetry} className="mt-5 text-red-600 underline underline-offset-4 hover:text-red-800 transition-colors text-sm">重试</button>
        </div>
      </main>
    );
  }

  return (
    <main className="flex flex-1 flex-col px-4 py-10 max-w-3xl mx-auto w-full">
      <header className="mb-8">
        <Link href={`/screenplay/${novelId}`} className="text-sm text-amber-700 hover:text-amber-700/70 mb-2 inline-block transition-colors">
          ← 返回剧本
        </Link>
        <h1 className="text-2xl font-bold text-stone-900">R2 滑动窗口改写预览</h1>
        <p className="text-stone-400 text-sm mt-1">{novel?.title} · {novel?.chapters.length} 个章节</p>
      </header>

      {!result ? (
        <div className="rounded-2xl border border-stone-200 bg-white p-10 text-center">
          <p className="text-stone-500 mb-2 text-lg">R2 滑动窗口扫描引擎</p>
          <p className="text-stone-400 text-sm mb-3">窗口 4000 字符，重叠 800 字符，逐块 LLM 改写</p>
          <p className="text-stone-400 text-xs mb-8">相邻窗口自动去重合并，确保场景连贯</p>
          <button
            onClick={handleScan}
            disabled={scanning}
            className="rounded-xl bg-amber-700 px-8 py-3.5 text-sm font-semibold text-white hover:bg-amber-800 disabled:opacity-50 transition-all duration-200 hover:shadow-lg active:scale-[0.98]"
          >
            {scanning ? "R2 正在扫描改写..." : "开始 R2 扫描"}
          </button>
          {error && <p className="mt-5 text-sm text-red-600">{error}</p>}
        </div>
      ) : (
        <>
          <div className="rounded-2xl border border-stone-200 bg-white p-5 mb-6">
            <div className="flex flex-wrap justify-center gap-x-6 gap-y-1 text-sm text-stone-500">
              <span>{result.scenes.length} 个场景</span>
              <span>{result.window_count} 个窗口</span>
            </div>
          </div>

          <div className="space-y-6">
            {result.scenes.map((scene) => (
              <section key={scene.index} className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
                <h3 className="text-sm font-bold text-stone-900 border-b border-stone-200 pb-3 mb-4 flex items-baseline gap-2">
                  <span className="text-stone-400 font-mono text-xs">#{scene.index}</span>
                  {scene.setting && <span>{scene.setting}</span>}
                </h3>
                {scene.characters.length > 0 && (
                  <div className="text-xs text-stone-400 mb-4">🎭 {scene.characters.join("、")}</div>
                )}
                <div className="space-y-1">
                  {scene.elements.map((elem, i) => {
                    const cls = TYPE_STYLES[elem.type] ?? "text-stone-900";
                    if (elem.type === "parenthetical") return <p key={i} className={cls}>({elem.content})</p>;
                    return <p key={i} className={cls}>{elem.content}</p>;
                  })}
                </div>
              </section>
            ))}
          </div>

          {result.scenes.length === 0 && (
            <div className="rounded-2xl border border-stone-200 bg-white p-10 text-center">
              <p className="text-stone-400">R2 未生成场景，请确认小说内容不为空</p>
            </div>
          )}
        </>
      )}
    </main>
  );
}
