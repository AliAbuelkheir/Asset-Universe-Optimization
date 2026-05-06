import { percent } from "../format";
import type { RawRiskComponentRow } from "../types";

const COMPONENTS = [
  { key: "annualizedVolatility", label: "Annualized volatility" },
  { key: "annualizedDownsideDeviation", label: "Annualized downside deviation" },
  { key: "maxDrawdown", label: "Max drawdown" }
] as const;

export function RawRiskDiagnostics({ rows }: { rows: RawRiskComponentRow[] }) {
  return (
    <div className="rawRiskGrid">
      {rows.map((row) => (
        <article className="rawRiskCard" key={row.id}>
          <h4>{row.label}</h4>
          <dl>
            {COMPONENTS.map((component) => (
              <div key={component.key}>
                <dt>{component.label}</dt>
                <dd>{percent(row.components[component.key])}</dd>
              </div>
            ))}
            <div>
              <dt>Daily observations</dt>
              <dd>{row.components.observations}</dd>
            </div>
          </dl>
        </article>
      ))}
    </div>
  );
}
