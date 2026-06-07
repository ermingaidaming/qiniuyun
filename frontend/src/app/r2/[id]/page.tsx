"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import type { Novel, R2ScanResult, SceneElementType } from "@/types";
import { getNovel, r2Scan } from "@/lib/api";

const TYPE_STYLES: Record<SceneElementType, string> = {
  action: "text-zinc-700 leading-relaxed",
  character: "text-center font-bold text-zinc-900 uppercase tracking-wide mt-4",
  dialogue: "mx-8 leading-relaxed text-zinc-800",
  parenthetical: "mx-12 text-sm text-zinc-500 italic",
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
        <h1 className="text-2xl font-bold text-zinc-900">R2 滑动窗口改写预览</h1>
        <p className="text-sm text-zinc-500 mt-1">
          {novel?.title} · {novel?.chapters.length} 个章节
        </p>
      </header>

      {!result ? (
        <div className="rounded-xl border border-zinc-200 bg-white p-8 text-center">
          <p className="text-zinc-600 mb-2">
            R2 使用滑动窗口（4000 字符/窗口，800 字符重叠）逐块将小说改写为剧本场景
          </p>
          <p className="text-xs text-zinc-400 mb-6">
            相邻窗口自动去重合并，确保场景连贯
          </p>
          <button
            onClick={handleScan}
            disabled={scanning}
            className="rounded-lg bg-teal-600 px-8 py-3 text-sm font-semibold text-white hover:bg-teal-700 disabled:opacity-50 transition-colors"
          >
            {scanning ? "R2 正在扫描改写..." : "开始 R2 扫描"}
          </button>
          {error && (
            <p className="mt-4 text-sm text-red-600">{error}</p>
          )}
        </div>
      ) : (
        <>
          <div className="rounded-xl border border-zinc-200 bg-white p-6 mb-6">
            <div className="flex flex-wrap justify-center gap-x-6 gap-y-1 text-sm text-zinc-500">
              <span>{result.scenes.length} 个场景</span>
              <span>{result.window_count} 个窗口</span>
            </div>
          </div>

          <div className="space-y-8">
            {result.scenes.map((scene) => (
              <section key={scene.index} className="rounded-xl border border-zinc-200 bg-white p-6">
                <h3 className="text-sm font-bold text-zinc-900 border-b border-zinc-100 pb-3 mb-4">
                  场景 {scene.index}
                  {scene.setting && <>: {scene.setting}</>}
                </h3>

                {scene.characters.length > 0 && (
                  <div className="text-xs text-zinc-400 mb-4">
                    🎭 {scene.characters.join("、")}
                  </div>
                )}

                <div className="space-y-1">
                  {scene.elements.map((elem, i) => {
                    const baseStyle = TYPE_STYLES[elem.type] ?? "text-zinc-700";
                    if (elem.type === "parenthetical") {
                      return <p key={i} className={baseStyle}>({elem.content})</p>;
                    }
                    return <p key={i} className={baseStyle}>{elem.content}</p>;
                  })}
                </div>
              </section>
            ))}
          </div>

          {result.scenes.length === 0 && (
            <div className="rounded-xl border border-zinc-200 bg-white p-8 text-center">
              <p className="text-zinc-400">R2 未生成场景，请确认小说内容不为空</p>
            </div>
          )}
        </>
      )}
    </main>
  );
}
