import { AlertTriangle, BarChart3 } from "lucide-react";
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

export function ReportView({ report, isStale }: ReportViewProps) {
  if (!report) {
    return (
      <section className="emptyReport" id="report">
        <BarChart3 size={42} />
        <h2>No report generated yet</h2>
        <p>Choose a risk level and month, then run a simulation to generate the dashboard.</p>
      </section>
    );
  }

  const durationResultLabel = report.requestedDurationMonths && report.requestedDurationMonths !== report.durationMonths
    ? `${report.durationMonths} plotted months from ${report.requestedDurationMonths} requested`
    : `${report.durationMonths} plotted months`;
  const simulatorLabel = report.simulatorMode === "monthly_rebalance" ? "Monthly rebalance" : "Single allocation";
  const isMonthlyRebalance = report.simulatorMode === "monthly_rebalance";

  return (
    <section className="reportSurface" id="report">
      <div className="reportHeader">
        <div>
          <h2>Simulation report</h2>
          <p>{report.thesisSafeSummary}</p>
        </div>
        <div className="reportMeta">
          <span>{report.month}</span>
          <span>{durationResultLabel}</span>
          <span>{simulatorLabel}</span>
          <span>{labelRisk(report.riskLevel)}</span>
          {report.questionnaireInference && <span>{report.questionnaireInference.riskLabel} questionnaire</span>}
        </div>
      </div>

      {isStale && (
        <div className="warningBanner">
          <AlertTriangle size={18} />
          Controls changed after this report was generated. Run the simulation again to refresh the dashboard.
        </div>
      )}

      <Metrics rows={report.comparison} />
      <p className="ratioNote">
        Return, Sharpe, and Sortino are secondary economic diagnostics. Sharpe/Sortino use no-risk-free arithmetic
        annualization and may appear as n/a when the selected duration is too short or has too few negative months.
      </p>
      <section className="resultPanel">
        <h3>{isMonthlyRebalance ? "Period-level risk and return map" : "Risk and return comparison"}</h3>
        <p className="panelNote">
          Each point compares cumulative return against annualized volatility for the selected historical period.
          {isMonthlyRebalance ? " Use the Monthly Rebalance Intelligence panel above for selected-month drilldown." : ""}
        </p>
        <RiskReturnScatter rows={report.comparison} />
      </section>

      {!isMonthlyRebalance && (
        <section className="resultPanel">
          <h3>Cumulative return comparison</h3>
          <p className="panelNote">
            All lines start at 0% before the first realized month, then compound through the selected period.
            Portfolio rows keep the start-month selection and weights.
            The x-axis labels show the month and calendar days since the previous plotted point.
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
