import { displayComparisonLabel } from "../comparisonLabels";
import { number, percent } from "../format";
import type { ComparisonRow } from "../types";

export function Metrics({ rows }: { rows: ComparisonRow[] }) {
  return (
    <div className="metricsGrid">
      {rows.map((row) => (
        <article className="metricCard" key={row.id}>
          <span>{displayComparisonLabel(row)}</span>
          <strong>{percent(row.metrics.cumulativeReturn)}</strong>
          <dl>
            <div><dt>Volatility</dt><dd>{percent(row.metrics.annualizedVolatility)}</dd></div>
            <div><dt>Sharpe</dt><dd title={row.metrics.ratioNotes.sharpe || undefined}>{number(row.metrics.sharpe)}</dd></div>
            <div><dt>Sortino</dt><dd title={row.metrics.ratioNotes.sortino || undefined}>{number(row.metrics.sortino)}</dd></div>
            <div><dt>Max drawdown</dt><dd>{percent(row.metrics.maxDrawdown)}</dd></div>
          </dl>
        </article>
      ))}
    </div>
  );
}
