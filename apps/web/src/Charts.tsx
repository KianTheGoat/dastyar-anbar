import { useEffect, useId, useState, type ReactNode } from "react";
import { ChartBar, ChartDonut, ChartLineUp } from "@phosphor-icons/react";
import { api, dateText, number, type Analytics } from "./api";
import { ErrorNotice, stateText } from "./ui";

export function Charts({ query, refresh }: { query: string; refresh: number }) {
  const [data, setData] = useState<Analytics | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(true);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const abort = new AbortController();
    setBusy(true);
    setError(null);
    api<Analytics>(`/v1/analytics?${query}`, { signal: abort.signal })
      .then(setData)
      .catch((e) => {
        if (!abort.signal.aborted) setError(e);
      })
      .finally(() => {
        if (!abort.signal.aborted) setBusy(false);
      });
    return () => abort.abort();
  }, [query, refresh, retry]);
  if (error)
    return (
      <section className="panel chart-error">
        <ErrorNotice error={error} />
        <button onClick={() => setRetry((v) => v + 1)}>تلاش دوباره</button>
      </section>
    );
  return (
    <section
      className="charts"
      aria-label="نمودارهای فروش و موجودی"
      aria-busy={busy}
    >
      <article className="panel chart-panel trend-panel">
        <ChartHeading
          icon={<ChartLineUp size={20} />}
          title="روند فروش ثبت‌شده"
          detail={
            data
              ? `${dateText(data.period_start)} تا ${dateText(data.period_end)}`
              : "در حال دریافت اطلاعات"
          }
        />
        {data ? <Trend data={data} /> : <Loading />}
      </article>
      <article className="panel chart-panel">
        <ChartHeading
          icon={<ChartDonut size={20} />}
          title="تصویر موجودی"
          detail="تعداد ترکیب‌های رنگ و سایز"
        />
        {data ? <Donut data={data} /> : <Loading />}
      </article>
      <article className="panel chart-panel sellers-panel">
        <ChartHeading
          icon={<ChartBar size={20} />}
          title="پرفروش‌های این بازه"
          detail="بر اساس تعداد فروش خالص ثبت‌شده"
        />
        {data ? <Sellers data={data} /> : <Loading />}
      </article>
    </section>
  );
}

function ChartHeading({
  icon,
  title,
  detail,
}: {
  icon: ReactNode;
  title: string;
  detail: string;
}) {
  return (
    <div className="chart-heading">
      <span className="chart-symbol" aria-hidden="true">
        {icon}
      </span>
      <div>
        <h2>{title}</h2>
        <p>{detail}</p>
      </div>
    </div>
  );
}
function Loading() {
  return (
    <p className="chart-empty" role="status">
      در حال خواندن اطلاعات…
    </p>
  );
}
function NoSales() {
  return (
    <div className="chart-empty">
      <p>هنوز گزارش فروش ثبت نشده است.</p>
      <a href="/sources">ورود اطلاعات فروش</a>
    </div>
  );
}

function Donut({ data }: { data: Analytics }) {
  const id = useId();
  const total = data.total_variants;
  const circumference = 2 * Math.PI * 66;
  let offset = 0;
  return (
    <>
      <div className="donut-layout">
        <svg
          viewBox="0 0 184 184"
          role="img"
          aria-labelledby={`${id}-title ${id}-desc`}
          className="donut-svg"
        >
          <title id={`${id}-title`}>
            وضعیت موجودی {number(total)} ترکیب کالا
          </title>
          <desc id={`${id}-desc`}>
            {Object.entries(data.counts)
              .map(
                ([key, value]) =>
                  `${stateText[key as keyof typeof stateText]}: ${number(value)}`,
              )
              .join("، ")}
          </desc>
          <circle
            cx="92"
            cy="92"
            r="66"
            fill="none"
            className="donut-track"
            strokeWidth="16"
          />
          {(["low", "normal", "high"] as const).map((key) => {
            const length = total
              ? (data.counts[key] / total) * circumference
              : 0;
            const before = offset;
            offset += length;
            return (
              <circle
                key={key}
                cx="92"
                cy="92"
                r="66"
                fill="none"
                className={`donut-segment chart-${key}`}
                strokeWidth="16"
                strokeDasharray={`${length} ${circumference - length}`}
                strokeDashoffset={-before}
                transform="rotate(-90 92 92)"
              />
            );
          })}
          <text x="92" y="91" textAnchor="middle" className="donut-total">
            {number(total)}
          </text>
          <text x="92" y="116" textAnchor="middle" className="donut-label">
            ترکیب کالا
          </text>
        </svg>
        <dl className="chart-legend">
          {(["low", "normal", "high"] as const).map((key) => (
            <div key={key}>
              <dt>
                <span
                  className={`legend-dot chart-${key}`}
                  aria-hidden="true"
                />
                {stateText[key]}
              </dt>
              <dd>{number(data.counts[key])}</dd>
            </div>
          ))}
        </dl>
      </div>
      {!total && (
        <p className="muted chart-note">برای این فیلتر کالایی ثبت نشده است.</p>
      )}
    </>
  );
}

function Sellers({ data }: { data: Analytics }) {
  if (!data.has_sales) return <NoSales />;
  if (!data.top_sellers.length)
    return (
      <p className="chart-empty">
        در این بازه و فیلتر، فروش خالص مثبتی ثبت نشده است.
      </p>
    );
  const max = Math.max(...data.top_sellers.map((r) => r.net_units));
  return (
    <ol className="seller-bars">
      {data.top_sellers.map((row, index) => (
        <li key={row.sku}>
          <div className="seller-label">
            <span className="seller-rank">{number(index + 1)}</span>
            <div>
              <strong>{row.name}</strong>
              <small>
                {row.color} · سایز <bdi>{row.size}</bdi> · <bdi>{row.sku}</bdi>
              </small>
            </div>
            <span className="numeric">{number(row.net_units)}</span>
          </div>
          <svg
            viewBox="0 0 300 7"
            role="img"
            aria-label={`${row.name} ${row.color} سایز ${row.size}: ${number(row.net_units)} فروش خالص`}
            className="seller-bar"
          >
            <rect width="300" height="7" rx="3.5" className="bar-track" />
            <rect
              width={(row.net_units / max) * 300}
              height="7"
              rx="3.5"
              className="bar-value"
            />
          </svg>
        </li>
      ))}
    </ol>
  );
}

function Trend({ data }: { data: Analytics }) {
  const id = useId();
  const [selected, setSelected] = useState<number | null>(null);
  useEffect(() => setSelected(null), [data]);
  if (!data.has_sales) return <NoSales />;
  if (data.sales_mode === "aggregate")
    return (
      <div className="chart-empty">
        <p>این گزارش، فروش تجمیعی دارد.</p>
        <small>
          برای نمایش روند روزانه، ردیف‌های تاریخ‌دار فروش را وارد کنید.
        </small>
      </div>
    );
  if (!data.daily.length)
    return <p className="chart-empty">داده‌ای برای این بازه وجود ندارد.</p>;
  const points = data.daily;
  const max = Math.max(1, ...points.map((p) => p.units));
  const x = (i: number) =>
    36 + (points.length === 1 ? 0.5 : i / (points.length - 1)) * 424;
  const y = (units: number) => 172 - (units / max) * 142;
  const line = points
    .map((p, i) => `${i ? "L" : "M"} ${x(i)} ${y(p.units)}`)
    .join(" ");
  const area = `${line} L ${x(points.length - 1)} 172 L ${x(0)} 172 Z`;
  const active = selected !== null ? points[selected] : null;
  return (
    <>
      <div className="trend-stat">
        <strong>{number(data.net_units ?? 0)}</strong>
        <span>عدد فروش خالص</span>
      </div>
      <svg
        className="trend-svg"
        viewBox="0 0 480 204"
        role="img"
        aria-labelledby={`${id}-title ${id}-description`}
      >
        <title id={`${id}-title`}>روند تعداد فروش خالص روزانه</title>
        <desc id={`${id}-description`}>
          فروش ثبت‌شده در بازهٔ انتخابی. جزئیات هر روز در جدول زیر نمودار قابل
          دسترسی است.
        </desc>
        {[0, 0.5, 1].map((part) => (
          <g key={part}>
            <line
              x1="36"
              x2="460"
              y1={y(max * part)}
              y2={y(max * part)}
              className="chart-grid-line"
            />
            <text
              x="26"
              y={y(max * part) + 4}
              textAnchor="end"
              className="chart-axis-label"
            >
              {number(max * part)}
            </text>
          </g>
        ))}
        <path d={area} className="trend-area" />
        <path d={line} className="trend-line" />
        {points.map((p, i) => (
          <circle
            key={p.date}
            cx={x(i)}
            cy={y(p.units)}
            r={selected === i ? 5 : 3}
            className="trend-dot"
            onMouseEnter={() => setSelected(i)}
            onMouseLeave={() => setSelected(null)}
          >
            <title>
              {dateText(p.date)}: {number(p.units)} فروش خالص
            </title>
          </circle>
        ))}
        <text x="36" y="199" className="chart-axis-label">
          {new Intl.DateTimeFormat("fa-IR", {
            month: "short",
            day: "numeric",
            timeZone: "Asia/Tehran",
          }).format(new Date(points[0].date + "T12:00:00Z"))}
        </text>
        <text x="460" y="199" textAnchor="end" className="chart-axis-label">
          {new Intl.DateTimeFormat("fa-IR", {
            month: "short",
            day: "numeric",
            timeZone: "Asia/Tehran",
          }).format(new Date(points.at(-1)!.date + "T12:00:00Z"))}
        </text>
      </svg>
      <div className="trend-inspect" aria-live="polite">
        {active
          ? `${dateText(active.date)}: ${number(active.units)} فروش خالص`
          : "برای جزئیات، یک روز را انتخاب کنید."}
      </div>
      <div className="trend-slider">
        <label htmlFor={`${id}-day`}>روز نمودار</label>
        <input
          id={`${id}-day`}
          type="range"
          min="0"
          max={points.length - 1}
          value={selected ?? points.length - 1}
          onChange={(e) => setSelected(Number(e.target.value))}
          aria-valuetext={`${dateText(points[selected ?? points.length - 1].date)}: ${number(points[selected ?? points.length - 1].units)} فروش خالص`}
        />
      </div>
      <details className="chart-data">
        <summary>جدول داده‌های نمودار</summary>
        <div className="chart-data-scroll">
          <table>
            <thead>
              <tr>
                <th scope="col">تاریخ</th>
                <th scope="col">فروش خالص ثبت‌شده</th>
              </tr>
            </thead>
            <tbody>
              {points.map((p) => (
                <tr key={p.date}>
                  <th scope="row">{dateText(p.date)}</th>
                  <td>{number(p.units)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </>
  );
}
