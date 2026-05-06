import { percent } from "../format";
import type { RiskComponentRow } from "../types";

const COMPONENTS = [
  { key: "realizedVol", label: "Realized volatility rank", color: "#0f766e" },
  { key: "realizedDownsideDev", label: "Downside deviation rank", color: "#d97706" },
  { key: "realizedMaxDrawdown", label: "Max drawdown rank", color: "#be123c" }
] as const;

export function RiskComponentChart({ rows }: { rows: RiskComponentRow[] }) {
  const maxValue = Math.max(
    0.01,
    ...rows.flatMap((row) => COMPONENTS.map((component) => row.components[component.key]))
  );

  return (
    <div className="riskComponentGrid">
      {rows.map((row) => (
        <article className="riskComponentCard" key={row.id}>
          <h4>{row.label}</h4>
          <div className="componentBars">
            {COMPONENTS.map((component) => {
              const value = row.components[component.key];
              return (
                <div className="componentBar" key={component.key}>
                  <div className="componentBarHeader">
                    <span>{component.label}</span>
                    <strong>{percent(value)}</strong>
                  </div>
                  <div className="barTrack">
                    <i style={{ width: `${Math.max(2, (value / maxValue) * 100)}%`, background: component.color }} />
                  </div>
                </div>
              );
            })}
          </div>
        </article>
      ))}
    </div>
  );
}
