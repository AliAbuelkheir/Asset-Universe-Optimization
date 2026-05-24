import { Sparkles } from "lucide-react";
import { number, percent, signedPercent } from "../format";
import type { RebalanceTimelinePoint, SimulationReport } from "../types";

interface RebalanceTimelineProps {
  report: SimulationReport | null;
  isStale: boolean;
}

function topAllocations(snapshot: RebalanceTimelinePoint) {
  return [...snapshot.selectedAssets]
    .sort((left, right) => (right.optimizedWeight ?? 0) - (left.optimizedWeight ?? 0))
    .slice(0, 4);
}

export function RebalanceTimeline({ report, isStale }: RebalanceTimelineProps) {
  if (!report || report.simulatorMode !== "monthly_rebalance") {
    return null;
  }

  const timeline = report.rebalanceTimeline;
  const finalValue = timeline[timeline.length - 1]?.endingValue ?? 1;

  return (
    <section
      className={isStale ? "rebalancePanel stale" : "rebalancePanel"}
      id="rebalance-timeline"
      aria-label="Monthly allocation timeline"
    >
      <div className="pipelineHeader">
        <div>
          <h2>Monthly allocation timeline</h2>
          <p>
            Each month shows the allocation view used before compounding realized returns.
          </p>
        </div>
        <div className="pipelineSummary">
          <span>{number(finalValue)} final value</span>
          <span>{percent(finalValue - 1)} cumulative</span>
        </div>
      </div>

      {isStale && (
        <div className="pipelineStaleNote">
          <Sparkles size={16} />
          This timeline belongs to the last generated report. Run again to refresh it with the current controls.
        </div>
      )}

      <div className="rebalanceGrid">
        {timeline.map((snapshot) => {
          const allocations = topAllocations(snapshot);
          return (
            <article className="rebalanceCard" key={snapshot.month}>
              <div className="rebalanceCardHeader">
                <div>
                  <h3>{snapshot.month}</h3>
                  <p>Portfolio return {signedPercent(snapshot.monthlyReturn)}</p>
                </div>
                <span>{signedPercent(snapshot.monthlyReturn)}</span>
              </div>
              <dl className="rebalanceStats">
                <div><dt>Start value</dt><dd>{number(snapshot.startingValue)}</dd></div>
                <div><dt>End value</dt><dd>{number(snapshot.endingValue)}</dd></div>
              </dl>
              <div className="rebalanceAllocations">
                <span>Top allocations</span>
                {allocations.map((asset) => (
                  <div className="rebalanceAllocation" key={asset.assetId}>
                    <strong>{asset.assetId}</strong>
                    <em>{percent(asset.optimizedWeight ?? 0)}</em>
                  </div>
                ))}
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
