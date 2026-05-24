import { AlertTriangle, PieChart, Sparkles, TrendingUp } from "lucide-react";
import { percent } from "../format";
import type { PipelineAsset, SimulationReport } from "../types";

interface PipelinePlaybackProps {
  report: SimulationReport | null;
  isStale: boolean;
}

function topHoldings(assets: PipelineAsset[], limit = 10) {
  return [...assets]
    .sort((left, right) => (right.optimizedWeight ?? 0) - (left.optimizedWeight ?? 0))
    .slice(0, limit);
}

export function PipelinePlayback({ report, isStale }: PipelinePlaybackProps) {
  const pipeline = report?.pipeline;

  if (!report || !pipeline || report.simulatorMode !== "single") {
    return null;
  }

  const holdings = topHoldings(pipeline.selectedAssets);
  const maxWeight = Math.max(0.01, ...holdings.map((asset) => asset.optimizedWeight ?? 0));
  const largestHolding = holdings[0];

  return (
    <section
      className={isStale ? "pipelinePanel stale t-panel-slide" : "pipelinePanel t-panel-slide"}
      data-open="true"
      id="pipeline-replay"
      aria-label="Portfolio allocation review"
    >
      <div className="pipelineHeader">
        <div>
          <span>Allocation review</span>
          <h2>Opening allocation</h2>
          <p>Holdings and weights used through this historical window.</p>
        </div>
        <div className="allocationSpotlight">
          <TrendingUp size={16} />
          <span>Largest holding</span>
          <strong>{largestHolding ? `${largestHolding.assetId} ${percent(largestHolding.optimizedWeight ?? 0)}` : "n/a"}</strong>
        </div>
      </div>

      {isStale && (
        <div className="pipelineStaleNote">
          <AlertTriangle size={16} />
          This allocation belongs to the last generated report. Run again to refresh it with the current controls.
        </div>
      )}

      <div className="allocationReviewGrid">
        <section className="allocationListPanel">
          <div className="detailSectionHeader">
            <PieChart size={16} />
            <h3>Holdings</h3>
          </div>
          <div className="allocationList">
            {holdings.map((asset) => {
              const weight = asset.optimizedWeight ?? 0;
              return (
                <article className="allocationRow" key={asset.assetId}>
                  <div>
                    <strong>{asset.assetId}</strong>
                    <span>{asset.assetName}</span>
                  </div>
                  <i><b style={{ width: `${Math.max((weight / maxWeight) * 100, 3)}%` }} /></i>
                  <em>{percent(weight)}</em>
                </article>
              );
            })}
          </div>
        </section>

        <aside className="allocationNarrative">
          <Sparkles size={17} />
          <h3>Historical diagnostic</h3>
          <p>
            The allocation is evaluated against the selected historical return path and benchmark series. The result
            describes this period only.
          </p>
        </aside>
      </div>
    </section>
  );
}
