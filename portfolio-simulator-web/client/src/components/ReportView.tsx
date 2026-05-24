import { AlertTriangle, BarChart3, LineChart } from "lucide-react";
import { labelRisk } from "../format";
import type { SimulationReport } from "../types";
import { Metrics } from "./Metrics";
import { ReturnChart } from "./ReturnChart";
import { ReturnTable } from "./ReturnTable";
import { RiskReturnScatter } from "./RiskReturnScatter";

interface ReportViewProps {
  report: SimulationReport | null;
  isStale: boolean;
}

function plural(value: number, singular: string, pluralLabel = `${singular}s`) {
  return `${value} ${value === 1 ? singular : pluralLabel}`;
}

function ratioExplanations(report: SimulationReport) {
  const notes = new Set<string>();
  let hasUnavailableRatio = false;
  for (const row of report.comparison) {
    if (row.metrics.sharpe === null) {
      hasUnavailableRatio = true;
      const note = row.metrics.ratioNotes.sharpe.trim();
      if (note && note.toLowerCase() !== "n/a") {
        notes.add(note);
      }
    }
    if (row.metrics.sortino === null) {
      hasUnavailableRatio = true;
      const note = row.metrics.ratioNotes.sortino.trim();
      if (note && note.toLowerCase() !== "n/a") {
        notes.add(note);
      }
    }
  }
  if (notes.size === 0 && hasUnavailableRatio) {
    notes.add("Some ratios need more return variation in the selected months before they can be calculated.");
  }
  return [...notes];
}

export function ReportView({ report, isStale }: ReportViewProps) {
  if (!report) {
    return (
      <section className="emptyReport" id="report">
        <BarChart3 size={34} />
        <h2>Ready for a simulation</h2>
        <p>Choose the setup on the left, then run a historical diagnostic.</p>
      </section>
    );
  }

  const durationResultLabel = report.requestedDurationMonths && report.requestedDurationMonths !== report.durationMonths
    ? `${report.durationMonths} of ${report.requestedDurationMonths} months`
    : `${report.durationMonths} month${report.durationMonths === 1 ? "" : "s"}`;
  const simulatorLabel = report.simulatorMode === "monthly_rebalance" ? "Monthly review" : "Opening allocation";
  const isMonthlyRebalance = report.simulatorMode === "monthly_rebalance";
  const profileLabel = report.questionnaireInference
    ? report.questionnaireInference.riskLabel
    : labelRisk(report.riskLevel);
  const ratioNotes = ratioExplanations(report);
  const coverageLabel = `${plural(report.pipeline.selectedAssetCount, "holding")} from ${plural(
    report.pipeline.activeUniverseCount,
    "available asset"
  )}`;

  return (
    <section className="reportSurface t-panel-slide" data-open="true" id="report">
      <div className="reportHeader">
        <div>
          <span>Simulation report</span>
          <h2>Portfolio diagnostics</h2>
          <p>Historical simulation diagnostics for the selected period. Results are not future performance guarantees.</p>
        </div>
        <div className="reportMeta">
          <span>{report.month}</span>
          <span>{durationResultLabel}</span>
          <span>{simulatorLabel}</span>
          <span>{profileLabel} profile</span>
          <span>{coverageLabel}</span>
        </div>
      </div>

      {isStale && (
        <div className="warningBanner">
          <AlertTriangle size={16} />
          Controls changed after this report was generated. Run the simulation again to refresh the dashboard.
        </div>
      )}

      <Metrics rows={report.comparison} />
      <div className="reportNotes" aria-label="Report data notes">
        <p>
          These values describe the selected historical period only. They are diagnostics, not future performance guarantees.
        </p>
        {ratioNotes.length > 0 && (
          <p>
            <strong>n/a ratios:</strong> {ratioNotes.join(" ")}
          </p>
        )}
      </div>

      <section className="resultPanel">
        <div className="resultPanelHeader">
          <LineChart size={16} />
          <div>
            <span>{isMonthlyRebalance ? "Monthly profile" : "Opening profile"}</span>
            <h3>{isMonthlyRebalance ? "Risk and return map" : "Risk and return comparison"}</h3>
          </div>
        </div>
        <p className="panelNote">
          Each point compares cumulative return against annualized volatility for the selected historical window.
        </p>
        <RiskReturnScatter rows={report.comparison} />
      </section>

      {!isMonthlyRebalance && (
        <section className="resultPanel">
          <div className="resultPanelHeader">
            <BarChart3 size={16} />
            <div>
              <span>Return path</span>
              <h3>Cumulative return comparison</h3>
            </div>
          </div>
          <p className="panelNote">
            Lines start at 0% before the first realized month and compound through the selected period.
          </p>
          <ReturnChart
            points={report.monthlyReturns}
            intervals={report.chartIntervals}
            comparison={report.comparison}
            showOptimizer={true}
          />
          <ReturnTable
            points={report.monthlyReturns}
            intervals={report.chartIntervals}
            comparison={report.comparison}
            showOptimizer={true}
          />
        </section>
      )}
    </section>
  );
}
