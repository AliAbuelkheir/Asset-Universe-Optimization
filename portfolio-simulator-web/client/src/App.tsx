import { AlertTriangle, BarChart3, CheckCircle2, ClipboardList, Play, SlidersHorizontal } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { fetchMonths, fetchRiskLevels, runFastSimulation } from "./api";
import { Metrics } from "./components/Metrics";
import { RawRiskDiagnostics } from "./components/RawRiskDiagnostics";
import { ReturnChart } from "./components/ReturnChart";
import { ReturnTable } from "./components/ReturnTable";
import { RiskComponentChart } from "./components/RiskComponentChart";
import { labelRisk, percent } from "./format";
import type { MonthOption, RiskLevel, RiskLevelDefinition, SimulationReport } from "./types";
import "./styles.css";

const riskOrder: RiskLevel[] = ["low", "medium", "high"];
const durationOptions = [
  { label: "1 month", value: 1 },
  { label: "3 months", value: 3 },
  { label: "6 months", value: 6 },
  { label: "12 months", value: 12 },
  { label: "Max available", value: null }
];

function App() {
  const [months, setMonths] = useState<MonthOption[]>([]);
  const [levels, setLevels] = useState<RiskLevelDefinition[]>([]);
  const [month, setMonth] = useState("2025-03");
  const [riskLevel, setRiskLevel] = useState<RiskLevel>("medium");
  const [durationMonths, setDurationMonths] = useState<number | null>(6);
  const [report, setReport] = useState<SimulationReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([fetchMonths(), fetchRiskLevels()])
      .then(([monthPayload, levelPayload]) => {
        setMonths(monthPayload);
        setLevels(levelPayload);
        if (monthPayload.length > 0 && !monthPayload.some((candidate) => candidate.month === month)) {
          setMonth(monthPayload[0].month);
        }
      })
      .catch((cause: Error) => setError(cause.message));
  }, []);

  const selectedMonth = useMemo(() => months.find((candidate) => candidate.month === month), [months, month]);
  const showOptimizer = report?.optimizerMode === "external_model";
  const durationRequestLabel = durationMonths === null ? "max available" : `${durationMonths} month${durationMonths === 1 ? "" : "s"}`;
  const durationResultLabel = report
    ? report.requestedDurationMonths && report.requestedDurationMonths !== report.durationMonths
      ? `${report.durationMonths} plotted months from ${report.requestedDurationMonths} requested`
      : `${report.durationMonths} plotted months`
    : "";

  async function handleRun() {
    setLoading(true);
    setError(null);
    try {
      setReport(await runFastSimulation(month, riskLevel, durationMonths));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="appShell">
      <section className="workspace">
        <header className="topBar">
          <div>
            <h1>Egypt Risk-Bucket Historical Simulator</h1>
            <p>Fast-mode historical diagnostics over validation and test months.</p>
          </div>
          <div className="headerActions">
            <nav className="topNav" aria-label="Page sections">
              <a href="#simulation"><SlidersHorizontal size={16} />Simulation</a>
              <a href="#report"><BarChart3 size={16} />Report</a>
              <a href="#contracts"><ClipboardList size={16} />Model files</a>
            </nav>
            <div className="statusPill"><CheckCircle2 size={16} />Stateless MVP</div>
          </div>
        </header>

        <section className="workflow" id="simulation">
          <article className="stepPanel disabled">
            <div className="stepTitle"><span>1</span><h2>Questionnaire model</h2></div>
            <p>Blocked until the risk-tolerance model artifact, loader, input schema, and output mapping are received.</p>
          </article>

          <article className="stepPanel">
            <div className="stepTitle"><span>2</span><h2>Fast mode risk level</h2></div>
            <div className="segmented">
              {riskOrder.map((level) => (
                <button
                  key={level}
                  type="button"
                  className={riskLevel === level ? "selected" : ""}
                  onClick={() => setRiskLevel(level)}
                >
                  {labelRisk(level)}
                </button>
              ))}
            </div>
            <p>{levels.find((level) => level.id === riskLevel)?.description ?? "Select a risk band."}</p>
          </article>

          <article className="stepPanel">
            <div className="stepTitle"><span>3</span><h2>Month and duration</h2></div>
            <select value={month} onChange={(event) => setMonth(event.target.value)}>
              {months.map((candidate) => (
                <option value={candidate.month} key={candidate.month}>
                  {candidate.month} - {candidate.split} - {candidate.assetCount} assets
                </option>
              ))}
            </select>
            <select
              value={durationMonths ?? "max"}
              onChange={(event) => {
                setDurationMonths(event.target.value === "max" ? null : Number(event.target.value));
              }}
            >
              {durationOptions.map((option) => (
                <option value={option.value ?? "max"} key={option.label}>
                  {option.label}
                </option>
              ))}
            </select>
            <p>
              {selectedMonth
                ? `${selectedMonth.split} split, ${selectedMonth.assetCount} active assets, ${durationRequestLabel} requested.`
                : "Loading months."}
            </p>
          </article>

          <article className="stepPanel actionPanel">
            <div className="stepTitle"><span>4</span><h2>Run simulation</h2></div>
            <button className="primaryButton" type="button" onClick={handleRun} disabled={loading || months.length === 0}>
              <Play size={18} />{loading ? "Running..." : "Run fast simulation"}
            </button>
            <p>Asset selection is fixed at the selected month, then equal-weight benchmarks are evaluated for the chosen duration.</p>
          </article>
        </section>

        {error && <div className="errorBanner"><AlertTriangle size={18} />{error}</div>}

        {report ? (
          <section className="reportSurface" id="report">
            <div className="reportHeader">
              <div>
                <h2>Simulation report</h2>
                <p>{report.thesisSafeSummary}</p>
              </div>
              <div className="reportMeta">
                <span>{report.month}</span>
                <span>{durationResultLabel}</span>
                <span>{labelRisk(report.riskLevel)}</span>
                {showOptimizer && <span>External optimizer</span>}
              </div>
            </div>

            {!showOptimizer && (
              <div className="infoBanner">
                Portfolio-weight model results are unavailable until the external PPO weight model is connected. Current
                results show the selected risk bucket equal-weight baseline, all-universe equal weight, and EGX30 only.
              </div>
            )}

            <Metrics rows={report.comparison} />
            <p className="ratioNote">
              Sharpe or Sortino appears as n/a when the selected duration has too few months, zero return volatility,
              or too few negative-return months to estimate downside volatility.
            </p>

            <section className="resultPanel">
              <h3>Raw realized risk diagnostics at decision month</h3>
              <p className="panelNote">
                These values are computed from daily returns inside the selected decision month. For the low bucket,
                lower volatility, downside deviation, and drawdown are better.
              </p>
              <RawRiskDiagnostics rows={report.rawRiskComponents} />
            </section>

            <section className="resultPanel">
              <h3>Relative risk-rank components at decision month</h3>
              <p className="panelNote">
                These are cross-sectional rank positions inside the month, not raw risk magnitudes. The all-universe
                equal-weight row is expected to sit near 50% because it averages the full rank distribution.
              </p>
              <RiskComponentChart rows={report.riskComponents} />
            </section>

            <section className="resultPanel">
              <h3>Cumulative return comparison</h3>
              <p className="panelNote">
                All lines start at 0% before the first realized month, then compound forward from the selected decision month.
                The x-axis labels show the month and calendar days since the previous plotted point.
              </p>
              <ReturnChart points={report.monthlyReturns} intervals={report.chartIntervals} showOptimizer={showOptimizer} />
              <ReturnTable points={report.monthlyReturns} intervals={report.chartIntervals} showOptimizer={showOptimizer} />
            </section>

            <div className={showOptimizer ? "twoColumn" : ""}>
              <section className="resultPanel">
                <h3>Selected asset universe</h3>
                <div className="tableScroller">
                  <table>
                    <thead>
                      <tr>
                        <th>Asset</th>
                        <th>Group</th>
                        <th>Selection rank</th>
                        <th>Vol rank</th>
                        <th>Downside rank</th>
                        <th>Drawdown rank</th>
                      </tr>
                    </thead>
                    <tbody>
                      {report.selectedAssets.map((asset) => (
                        <tr key={asset.assetId}>
                          <td><strong>{asset.assetId}</strong><span>{asset.assetName}</span></td>
                          <td>{asset.assetGroup}</td>
                          <td>{percent(asset.predictedRankPct)}</td>
                          <td>{percent(asset.realizedVol)}</td>
                          <td>{percent(asset.realizedDownsideDev)}</td>
                          <td>{percent(asset.realizedMaxDrawdown)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>

              {showOptimizer && (
                <section className="resultPanel">
                  <h3>Optimizer weights</h3>
                  <div className="weightsList">
                    {report.selectedAssets.map((asset) => (
                      <div className="weightRow" key={asset.assetId}>
                        <span>{asset.assetId}</span>
                        <div><i style={{ width: `${Math.max(4, (asset.weight ?? 0) * 100)}%` }} /></div>
                        <strong>{percent(asset.weight ?? 0)}</strong>
                      </div>
                    ))}
                  </div>
                </section>
              )}
            </div>

            <section className="resultPanel">
              <h3>Simulation assumptions</h3>
              <ul className="assumptionList">{report.assumptions.map((item) => <li key={item}>{item}</li>)}</ul>
            </section>

            <section className="contractsPanel" id="contracts">
              <h3>Files needed from collaborators</h3>
              <div>
                <article>
                  <h4>Risk-tolerance model</h4>
                  <ul>{report.requiredExternalContracts.riskToleranceModel.map((item) => <li key={item}>{item}</li>)}</ul>
                </article>
                <article>
                  <h4>Weight optimizer PPO</h4>
                  <ul>{report.requiredExternalContracts.weightOptimizerModel.map((item) => <li key={item}>{item}</li>)}</ul>
                </article>
              </div>
            </section>
          </section>
        ) : (
          <section className="emptyReport">
            <BarChart3 size={42} />
            <h2>No report generated yet</h2>
            <p>Choose a risk level and month, then run fast simulation to generate the dashboard.</p>
          </section>
        )}
      </section>
    </main>
  );
}

export default App;
