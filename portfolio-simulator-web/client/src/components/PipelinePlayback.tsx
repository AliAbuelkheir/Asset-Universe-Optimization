import { CheckCircle2, Sparkles } from "lucide-react";
import { useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import { percent } from "../format";
import type { PipelineAsset, SimulationReport } from "../types";

type PipelinePhase = "universe" | "filter" | "weights";

interface PipelinePlaybackProps {
  report: SimulationReport | null;
  isStale: boolean;
}

function assetNodeClass(asset: PipelineAsset, phase: PipelinePhase) {
  const classes = ["assetNode"];
  if (phase !== "universe" && asset.selectedByFilter) {
    classes.push("selected");
  }
  if (phase !== "universe" && !asset.selectedByFilter) {
    classes.push("faded");
  }
  if (phase === "weights" && asset.selectedByFilter) {
    classes.push("weighted");
  }
  return classes.join(" ");
}

export function PipelinePlayback({ report, isStale }: PipelinePlaybackProps) {
  const [phase, setPhase] = useState<PipelinePhase>("universe");
  const [assetCardHeight, setAssetCardHeight] = useState<number | null>(null);
  const assetCardRef = useRef<HTMLDivElement>(null);
  const pipeline = report?.pipeline;

  useEffect(() => {
    if (!report) {
      return;
    }
    setPhase("universe");
    const filterTimer = window.setTimeout(() => setPhase("filter"), 1900);
    const weightTimer = window.setTimeout(() => setPhase("weights"), 4600);
    return () => {
      window.clearTimeout(filterTimer);
      window.clearTimeout(weightTimer);
    };
  }, [report?.simulationId]);

  const weightedAssets = useMemo(() => {
    if (!pipeline) {
      return [];
    }
    return [...pipeline.selectedAssets].sort(
      (left, right) => (right.optimizedWeight ?? 0) - (left.optimizedWeight ?? 0)
    );
  }, [pipeline]);

  const displayedUniverse = pipeline?.activeUniverse ?? [];

  useEffect(() => {
    const card = assetCardRef.current;
    if (!card) {
      return;
    }

    const updateHeight = () => {
      const nextHeight = Math.ceil(card.getBoundingClientRect().height);
      if (nextHeight <= 0) {
        return;
      }
      setAssetCardHeight((currentHeight) => {
        if (currentHeight !== null && Math.abs(currentHeight - nextHeight) < 2) {
          return currentHeight;
        }
        return nextHeight;
      });
    };

    updateHeight();

    if (typeof ResizeObserver === "function") {
      const observer = new ResizeObserver(updateHeight);
      observer.observe(card);
      return () => observer.disconnect();
    }

    window.addEventListener("resize", updateHeight);
    return () => window.removeEventListener("resize", updateHeight);
  }, [displayedUniverse.length, phase]);

  if (!report || !pipeline) {
    return null;
  }

  const topWeight = weightedAssets[0]?.optimizedWeight ?? 0;
  const pipelineBodyStyle = assetCardHeight
    ? ({ "--asset-card-height": `${assetCardHeight}px` } as CSSProperties)
    : undefined;

  return (
    <section
      className={isStale ? "pipelinePanel stale" : "pipelinePanel"}
      id="pipeline-replay"
      aria-label="Simulation pipeline replay"
    >
      <div className="pipelineHeader">
        <div>
          <h2>Pipeline replay</h2>
          <p>
            Active universe, PPO risk-bucket selection, and optimizer weights used for this historical diagnostic.
          </p>
        </div>
        <div className="pipelineSummary">
          <span>{pipeline.activeUniverseCount} active assets</span>
          <span>{pipeline.selectedAssetCount} selected</span>
          <span>{percent(pipeline.optimizerWeightSum)} weight sum</span>
        </div>
      </div>

      {isStale && (
        <div className="pipelineStaleNote">
          <Sparkles size={16} />
          This replay belongs to the last generated report. Run again to refresh it with the current controls.
        </div>
      )}

      <div className="pipelineBody" style={pipelineBodyStyle}>
        <div className="assetUniverseCard" ref={assetCardRef}>
          <div className="assetUniverseHeader">
            <div>
              <h3>Asset universe selection</h3>
              <p>
                Rank is the PPO predicted-risk percentile for {report.month}. Filtered assets move to the front before
                weights are assigned.
              </p>
            </div>
            <span>{phase === "universe" ? "Scanning" : phase === "filter" ? "Filtering" : "Weighted"}</span>
          </div>
          <div className="assetUniverseGrid">
            {displayedUniverse.map((asset) => (
              <div className={assetNodeClass(asset, phase)} key={asset.assetId} title={`${asset.assetName} (${asset.assetGroup})`}>
                <div className="assetNodeTop">
                  <strong>{asset.assetId}</strong>
                  {asset.selectedByFilter && phase !== "universe" && <CheckCircle2 size={15} />}
                </div>
                <span>{asset.assetGroup}</span>
                <small>Rank {percent(asset.predictedRankPct, 0)}</small>
                {phase === "weights" && asset.selectedByFilter && (
                  <em>{percent(asset.optimizedWeight ?? 0)} weight</em>
                )}
              </div>
            ))}
          </div>
        </div>

        <aside className="weightAssignmentCard">
          <div>
            <h3>Final selected-asset weights</h3>
            <p>
              These are the optimizer allocations for the PPO-filtered universe. Equal-weight baselines below skip this
              stage.
            </p>
          </div>
          <div className="weightRows">
            {weightedAssets.map((asset, index) => {
              const weightPct = topWeight > 0
                ? Math.max(((asset.optimizedWeight ?? 0) / topWeight) * 100, 3)
                : 0;
              const rowStyle = {
                "--weight-pct": weightPct,
                "--weight-delay": `${Math.min(index * 120, 1400)}ms`
              } as CSSProperties;
              return (
                <div className={phase === "weights" ? "weightRow assigned" : "weightRow"} key={asset.assetId}>
                  <div className="weightRowLabel">
                    <strong>{asset.assetId}</strong>
                    <span title={asset.assetName}>{asset.assetName}</span>
                  </div>
                  <div className="weightTrack" style={rowStyle}>
                    <i />
                  </div>
                  <b>{percent(asset.optimizedWeight ?? 0)}</b>
                </div>
              );
            })}
          </div>
          <div className="weightInsight">
            <span>Largest allocation</span>
            <strong>{weightedAssets[0] ? `${weightedAssets[0].assetId} at ${percent(topWeight)}` : "n/a"}</strong>
          </div>
        </aside>
      </div>
    </section>
  );
}
