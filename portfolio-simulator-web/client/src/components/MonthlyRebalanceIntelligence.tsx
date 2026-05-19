import {
  ArrowLeft,
  ArrowRight,
  BarChart3,
  CheckCircle2,
  LineChart,
  PieChart,
  ShieldCheck,
  Sparkles,
  TrendingDown,
  TrendingUp
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { comparisonLabels } from "../comparisonLabels";
import { number, percent, signedPercent } from "../format";
import { cumulativeReturns, visibleReturnSeries, type ReturnSeriesKey } from "../returnSeries";
import type { ComparisonRow, MonthlyReturnPoint, RebalanceTimelinePoint, SimulationReport } from "../types";
import { ReturnChart } from "./ReturnChart";

interface MonthlyRebalanceIntelligenceProps {
  report: SimulationReport | null;
  isStale: boolean;
}

type DetailTab = "snapshot" | "risk" | "holdings";

const detailTabs: Array<{ id: DetailTab; label: string; icon: typeof BarChart3 }> = [
  { id: "snapshot", label: "Snapshot", icon: BarChart3 },
  { id: "risk", label: "Risk", icon: ShieldCheck },
  { id: "holdings", label: "Holdings", icon: PieChart }
];

function topAllocations(snapshot: RebalanceTimelinePoint, limit = 8) {
  return [...snapshot.selectedAssets]
    .sort((left, right) => (right.optimizedWeight ?? 0) - (left.optimizedWeight ?? 0))
    .slice(0, limit);
}

function compactLabel(row: ComparisonRow) {
  const compactLabels: Record<ComparisonRow["id"], string> = {
    optimizedPortfolio: "Optimized portfolio",
    assignedRiskBucket: "Equal-weight bucket",
    optimizedRawUniverse: "Full universe",
    egx30: "EGX30"
  };
  if (row.label.toLowerCase().includes("monthly")) {
    return compactLabels[row.id];
  }
  const label = row.label || comparisonLabels[row.id];
  return label
    .replace("Monthly rebalanced ", "")
    .replace("Monthly reselected ", "")
    .replace(" with optimized weights", "")
    .replace(" with equal weights", "");
}

function heatCellColor(value: number) {
  const alpha = Math.min(0.36, 0.06 + Math.abs(value) * 5.8);
  return value >= 0 ? `rgba(var(--heat-positive), ${alpha})` : `rgba(var(--heat-negative), ${alpha})`;
}

function reportSeriesRows(report: SimulationReport, enabledSeries: ReturnSeriesKey[]) {
  const comparisonById = new Map(report.comparison.map((row) => [row.id, row]));
  return visibleReturnSeries(true, report.comparison)
    .filter((series) => comparisonById.has(series.key))
    .map((series) => ({
      ...series,
      row: comparisonById.get(series.key),
      enabled: enabledSeries.includes(series.key)
    }));
}

export function MonthlyRebalanceIntelligence({ report, isStale }: MonthlyRebalanceIntelligenceProps) {
  const timeline = report?.simulatorMode === "monthly_rebalance" ? report.rebalanceTimeline : [];
  const months = useMemo(() => timeline.map((snapshot) => snapshot.month), [timeline]);
  const [selectedMonth, setSelectedMonth] = useState(months[0] ?? "");
  const selectedMonthButtonRef = useRef<HTMLButtonElement | null>(null);
  const [activeTab, setActiveTab] = useState<DetailTab>("snapshot");
  const availableSeries = useMemo(
    () => (report ? visibleReturnSeries(true, report.comparison).map((series) => series.key) : []),
    [report]
  );
  const [enabledSeries, setEnabledSeries] = useState<ReturnSeriesKey[]>(availableSeries);

  useEffect(() => {
    setSelectedMonth((current) => (current && months.includes(current) ? current : months[0] ?? ""));
  }, [months]);

  useEffect(() => {
    setEnabledSeries((current) => {
      const kept = current.filter((key) => availableSeries.includes(key));
      return kept.length > 0 ? kept : availableSeries;
    });
  }, [availableSeries]);

  useEffect(() => {
    const selectedButton = selectedMonthButtonRef.current;
    if (typeof selectedButton?.scrollIntoView === "function") {
      selectedButton.scrollIntoView({ block: "nearest", inline: "center" });
    }
  }, [selectedMonth]);

  if (!report || report.simulatorMode !== "monthly_rebalance" || timeline.length === 0) {
    return null;
  }

  const selectedIndex = Math.max(0, report.monthlyReturns.findIndex((point) => point.month === selectedMonth));
  const selectedPoint = report.monthlyReturns[selectedIndex] ?? report.monthlyReturns[0];
  const selectedSnapshot = timeline.find((snapshot) => snapshot.month === selectedPoint?.month) ?? timeline[0];
  const selectedMonthValue = selectedPoint?.month ?? selectedSnapshot.month;
  const finalValue = timeline[timeline.length - 1]?.endingValue ?? 1;
  const selectedCumulative = cumulativeReturns(report.monthlyReturns, "optimizedPortfolio")[selectedIndex]?.cumulativeReturn
    ?? selectedSnapshot.endingValue - 1;
  const chartComparison = report.comparison.filter((row) => enabledSeries.includes(row.id));
  const seriesRows = reportSeriesRows(report, enabledSeries);
  const monthlyBenchmarkRows = seriesRows.map((series) => {
    const monthlyReturn = Number(selectedPoint?.[series.key] ?? 0);
    const cumulativeReturn = cumulativeReturns(report.monthlyReturns, series.key)[selectedIndex]?.cumulativeReturn ?? 0;
    return {
      ...series,
      monthlyReturn,
      cumulativeReturn,
      deltaToPortfolio: Number(selectedPoint?.optimizedPortfolio ?? 0) - monthlyReturn
    };
  });
  const sortedMonthly = [...monthlyBenchmarkRows].sort((left, right) => right.monthlyReturn - left.monthlyReturn);
  const leader = sortedMonthly[0];
  const portfolioRank = sortedMonthly.findIndex((row) => row.key === "optimizedPortfolio") + 1;
  const outperformed = monthlyBenchmarkRows.filter(
    (row) => row.key !== "optimizedPortfolio" && Number(selectedPoint?.optimizedPortfolio ?? 0) > row.monthlyReturn
  ).length;
  const allocations = topAllocations(selectedSnapshot);
  const maxWeight = Math.max(0.01, ...allocations.map((asset) => asset.optimizedWeight ?? 0));

  function selectRelativeMonth(direction: -1 | 1) {
    const nextMonth = months[selectedIndex + direction];
    if (nextMonth) {
      setSelectedMonth(nextMonth);
    }
  }

  function toggleSeries(key: ReturnSeriesKey) {
    setEnabledSeries((current) => {
      if (current.includes(key)) {
        return current.length > 1 ? current.filter((candidate) => candidate !== key) : current;
      }
      return [...current, key];
    });
  }

  return (
    <section
      className={isStale ? "rebalanceIntelligence stale" : "rebalanceIntelligence"}
      id="rebalance-timeline"
      aria-label="Monthly Rebalance Intelligence"
    >
      <div className="intelligenceHeader">
        <div>
          <span className="diagnosticLabel"><Sparkles size={15} />Historical diagnostic</span>
          <h2>Monthly Rebalance Intelligence</h2>
          <p>
            Select a realized month to inspect the portfolio snapshot, benchmark deltas, and allocation diagnostics.
          </p>
        </div>
        <div className="intelligenceSummary">
          <span>{timeline.length} rebalance months</span>
          <span>{number(finalValue)} final value</span>
          <span>{percent(finalValue - 1)} cumulative</span>
        </div>
      </div>

      {isStale && (
        <div className="pipelineStaleNote">
          <Sparkles size={16} />
          This intelligence view belongs to the last generated report. Run again to refresh it with the current controls.
        </div>
      )}

      <div className="intelligenceChartPanel">
        <div className="chartPanelHeader">
          <div>
            <span>Cumulative return</span>
            <h3>Click a month on the chart or rail</h3>
          </div>
          <div className="seriesToggles" aria-label="Benchmark series toggles">
            {seriesRows.map((series) => (
              <button
                type="button"
                key={series.key}
                className={series.enabled ? "seriesToggle selected" : "seriesToggle"}
                aria-pressed={series.enabled}
                onClick={() => toggleSeries(series.key)}
              >
                <i style={{ background: series.color }} />
                {series.row ? compactLabel(series.row) : series.label}
              </button>
            ))}
          </div>
        </div>

        <ReturnChart
          points={report.monthlyReturns}
          intervals={report.chartIntervals}
          comparison={chartComparison}
          showOptimizer={true}
          selectedMonth={selectedMonthValue}
          onMonthSelect={setSelectedMonth}
          height={360}
          showLegend={false}
          interactive
        />
      </div>

      <div className="monthRailWrap" aria-label="Selectable rebalance months">
        <button
          type="button"
          className="railArrow"
          onClick={() => selectRelativeMonth(-1)}
          disabled={selectedIndex <= 0}
          aria-label="Select previous month"
        >
          <ArrowLeft size={18} />
        </button>
        <div className="monthRail">
          {report.monthlyReturns.map((point) => {
            const isSelected = point.month === selectedMonthValue;
            const positive = point.optimizedPortfolio >= 0;
            const TrendIcon = positive ? TrendingUp : TrendingDown;
            return (
              <button
                type="button"
                key={point.month}
                ref={isSelected ? selectedMonthButtonRef : undefined}
                className={isSelected ? "monthChip selected" : "monthChip"}
                aria-pressed={isSelected}
                onClick={() => setSelectedMonth(point.month)}
              >
                <strong>{point.month}</strong>
                <span>{point.split} split</span>
                <em className={positive ? "positive" : "negative"}>
                  <TrendIcon size={13} />
                  {signedPercent(point.optimizedPortfolio)}
                </em>
              </button>
            );
          })}
        </div>
        <button
          type="button"
          className="railArrow"
          onClick={() => selectRelativeMonth(1)}
          disabled={selectedIndex >= months.length - 1}
          aria-label="Select next month"
        >
          <ArrowRight size={18} />
        </button>
      </div>

      <div className="detailToolbar">
        <div className="detailTabs" role="tablist" aria-label="Selected month detail views">
          {detailTabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                type="button"
                role="tab"
                key={tab.id}
                className={activeTab === tab.id ? "detailTab selected" : "detailTab"}
                aria-selected={activeTab === tab.id}
                onClick={() => setActiveTab(tab.id)}
              >
                <Icon size={16} />
                {tab.label}
              </button>
            );
          })}
        </div>
        <div className="selectedMonthControls">
          <span>Selected month</span>
          <strong>{selectedMonthValue}</strong>
        </div>
      </div>

      <div className="monthDetailPanel" key={`${selectedMonthValue}-${activeTab}`}>
        {activeTab === "snapshot" && (
          <div className="snapshotGrid">
            <section className="snapshotStats" aria-label="Portfolio snapshot">
              <div className="detailSectionHeader">
                <LineChart size={18} />
                <h3>Portfolio snapshot</h3>
              </div>
              <dl>
                <div><dt>Monthly return</dt><dd className={selectedSnapshot.monthlyReturn >= 0 ? "positive" : "negative"}>{signedPercent(selectedSnapshot.monthlyReturn)}</dd></div>
                <div><dt>Cumulative return</dt><dd>{percent(selectedCumulative)}</dd></div>
                <div><dt>Starting value</dt><dd>{number(selectedSnapshot.startingValue)}</dd></div>
                <div><dt>Ending value</dt><dd>{number(selectedSnapshot.endingValue)}</dd></div>
                <div><dt>Active universe count</dt><dd>{selectedSnapshot.activeUniverseCount}</dd></div>
                <div><dt>Selected asset count</dt><dd>{selectedSnapshot.selectedAssetCount}</dd></div>
                <div><dt>Optimizer weight sum</dt><dd>{percent(selectedSnapshot.optimizerWeightSum)}</dd></div>
                <div><dt>Decision date</dt><dd>{selectedSnapshot.optimizerDecisionDate}</dd></div>
              </dl>
            </section>

            <section className="allocationPreview" aria-label="Top allocations">
              <div className="detailSectionHeader">
                <PieChart size={18} />
                <h3>Top allocations</h3>
              </div>
              {allocations.slice(0, 6).map((asset) => {
                const weight = asset.optimizedWeight ?? 0;
                return (
                  <div className="allocationBar" key={asset.assetId}>
                    <span>
                      <strong>{asset.assetId}</strong>
                      <em>{asset.assetGroup}</em>
                    </span>
                    <i><b style={{ width: `${(weight / maxWeight) * 100}%` }} /></i>
                    <small>{percent(weight)}</small>
                  </div>
                );
              })}
            </section>

            <section className="riskPreviewTable" aria-label="Risk comparison">
              <div className="detailSectionHeader">
                <ShieldCheck size={18} />
                <h3>Risk comparison</h3>
              </div>
              <table>
                <thead>
                  <tr>
                    <th>Series</th>
                    <th>Vol</th>
                    <th>Sharpe</th>
                    <th>Drawdown</th>
                  </tr>
                </thead>
                <tbody>
                  {report.comparison.map((row) => (
                    <tr key={row.id}>
                      <td>{compactLabel(row)}</td>
                      <td>{percent(row.metrics.annualizedVolatility)}</td>
                      <td>{number(row.metrics.sharpe)}</td>
                      <td>{percent(row.metrics.maxDrawdown)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>

            <section className="benchmarkDelta" aria-label="Benchmark delta">
              <div className="detailSectionHeader">
                <BarChart3 size={18} />
                <h3>Benchmark delta</h3>
              </div>
              <div className="leaderCard">
                <span>Leader</span>
                <strong>{leader?.row ? compactLabel(leader.row) : leader?.label}</strong>
                <em>{signedPercent(leader?.monthlyReturn ?? 0)}</em>
              </div>
              {monthlyBenchmarkRows.filter((row) => row.key !== "optimizedPortfolio").map((row) => (
                <div className="deltaRow" key={row.key}>
                  <span>vs {row.row ? compactLabel(row.row) : row.label}</span>
                  <strong className={row.deltaToPortfolio >= 0 ? "positive" : "negative"}>
                    {signedPercent(row.deltaToPortfolio)}
                  </strong>
                </div>
              ))}
              <p>
                Outperformed {outperformed} of {Math.max(0, monthlyBenchmarkRows.length - 1)} benchmarks
                {portfolioRank > 0 ? `, rank ${portfolioRank} of ${monthlyBenchmarkRows.length}.` : "."}
              </p>
            </section>
          </div>
        )}

        {activeTab === "risk" && (
          <div className="riskDetailGrid">
            <section className="riskMatrix">
              <div className="detailSectionHeader">
                <ShieldCheck size={18} />
                <h3>Risk comparison vs benchmarks</h3>
              </div>
              <table>
                <thead>
                  <tr>
                    <th>Metric</th>
                    {report.comparison.map((row) => <th key={row.id}>{compactLabel(row)}</th>)}
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>Annualized volatility</td>
                    {report.comparison.map((row) => <td key={`${row.id}-vol`}>{percent(row.metrics.annualizedVolatility)}</td>)}
                  </tr>
                  <tr>
                    <td>Sharpe</td>
                    {report.comparison.map((row) => <td key={`${row.id}-sharpe`} title={row.metrics.ratioNotes.sharpe || undefined}>{number(row.metrics.sharpe)}</td>)}
                  </tr>
                  <tr>
                    <td>Sortino</td>
                    {report.comparison.map((row) => <td key={`${row.id}-sortino`} title={row.metrics.ratioNotes.sortino || undefined}>{number(row.metrics.sortino)}</td>)}
                  </tr>
                  <tr>
                    <td>Max drawdown</td>
                    {report.comparison.map((row) => <td key={`${row.id}-drawdown`}>{percent(row.metrics.maxDrawdown)}</td>)}
                  </tr>
                  <tr>
                    <td>Best month</td>
                    {report.comparison.map((row) => <td key={`${row.id}-best`}>{percent(row.metrics.bestMonth)}</td>)}
                  </tr>
                  <tr>
                    <td>Worst month</td>
                    {report.comparison.map((row) => <td key={`${row.id}-worst`}>{percent(row.metrics.worstMonth)}</td>)}
                  </tr>
                </tbody>
              </table>
            </section>

            <section className="monthRanking">
              <div className="detailSectionHeader">
                <BarChart3 size={18} />
                <h3>{selectedMonthValue} return ranking</h3>
              </div>
              {sortedMonthly.map((row, index) => (
                <div className="rankingRow" key={row.key}>
                  <span>{index + 1}</span>
                  <strong>{row.row ? compactLabel(row.row) : row.label}</strong>
                  <em className={row.monthlyReturn >= 0 ? "positive" : "negative"}>{signedPercent(row.monthlyReturn)}</em>
                </div>
              ))}
            </section>
          </div>
        )}

        {activeTab === "holdings" && (
          <section className="holdingsDetail">
            <div className="detailSectionHeader">
              <PieChart size={18} />
              <h3>Selected portfolio holdings</h3>
              <span>{selectedSnapshot.selectedAssetCount} selected assets</span>
            </div>
            <div className="holdingsGrid">
              {topAllocations(selectedSnapshot, selectedSnapshot.selectedAssets.length).map((asset) => {
                const weight = asset.optimizedWeight ?? 0;
                return (
                  <article className="holdingCard" key={asset.assetId}>
                    <div>
                      <strong>{asset.assetId}</strong>
                      <span>{asset.assetName}</span>
                      <em>{asset.assetGroup}</em>
                    </div>
                    <small>{percent(weight)}</small>
                    <i><b style={{ width: `${(weight / maxWeight) * 100}%` }} /></i>
                  </article>
                );
              })}
            </div>
          </section>
        )}
      </div>

      <section className="returnHeatStrip" aria-label="Historical diagnostic monthly returns">
        <div className="detailSectionHeader">
          <CheckCircle2 size={18} />
          <h3>Historical diagnostic monthly returns</h3>
        </div>
        <div className="heatScroller">
          <table>
            <thead>
              <tr>
                <th>Series</th>
                {report.monthlyReturns.map((point) => <th key={point.month}>{point.month}</th>)}
              </tr>
            </thead>
            <tbody>
              {seriesRows.map((series) => (
                <tr key={series.key}>
                  <td><i style={{ background: series.color }} />{series.row ? compactLabel(series.row) : series.label}</td>
                  {report.monthlyReturns.map((point: MonthlyReturnPoint) => {
                    const value = Number(point[series.key] ?? 0);
                    return (
                      <td
                        key={`${series.key}-${point.month}`}
                        className={point.month === selectedMonthValue ? "selected" : ""}
                        style={{ backgroundColor: heatCellColor(value) }}
                      >
                        {percent(value)}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p>Returns are historical simulation diagnostics for the plotted months, not future performance guarantees.</p>
      </section>
    </section>
  );
}
