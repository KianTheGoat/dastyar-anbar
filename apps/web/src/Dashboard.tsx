import { useEffect, useRef, useState, type FormEvent } from "react";
import {
  ArrowClockwise,
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  MagnifyingGlass,
  Package,
  TrendUp,
  WarningCircle,
  ChatCircleDots,
  X,
} from "@phosphor-icons/react";
import {
  api,
  dateText,
  json,
  localToday,
  number,
  type Category,
  type Report,
  type Variant,
} from "./api";
import { Empty, ErrorNotice, productionText, stateText } from "./ui";

export function Dashboard() {
  const [data, setData] = useState<Report | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(true);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [state, setState] = useState("");
  const [priority, setPriority] = useState(false);
  const [start, setStart] = useState("");
  const [end, setEnd] = useState(localToday());
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [refresh, setRefresh] = useState(0);
  const [updating, setUpdating] = useState("");
  useEffect(() => {
    api<Category[]>("/v1/categories").then(setCategories).catch(setError);
  }, []);
  useEffect(() => {
    const abort = new AbortController();
    setBusy(true);
    setError(null);
    api<Report>(`/v1/variants?${query}&page=${page}`, { signal: abort.signal })
      .then((value) => {
        setData(value);
      })
      .catch((e) => {
        if (!abort.signal.aborted) setError(e);
      })
      .finally(() => {
        if (!abort.signal.aborted) setBusy(false);
      });
    return () => abort.abort();
  }, [query, page, refresh]);
  function filter(event?: FormEvent) {
    event?.preventDefault();
    const params = new URLSearchParams();
    if (search) params.set("search", search);
    if (category) params.set("category_id", category);
    if (state) params.set("state", state);
    if (priority) params.set("priority_only", "true");
    if (start) params.set("start", start);
    if (end) params.set("end", end);
    setQuery(params.toString());
    setPage(1);
  }
  async function replenish(row: Variant, value: string) {
    setUpdating(row.id);
    setError(null);
    try {
      await api(`/v1/variants/${row.id}/replenishment`, {
        method: "PATCH",
        body: json({ state: value }),
      });
      setRefresh((v) => v + 1);
    } catch (e) {
      setError(e);
    } finally {
      setUpdating("");
    }
  }
  return (
    <>
      <div className="page-heading row-heading">
        <div>
          <p className="eyeline">
            {data
              ? `${dateText(data.period_start)} تا ${dateText(data.period_end)}`
              : "نمای انبار"}
          </p>
          <h1>موجودی و اولویت تأمین</h1>
          <p>پرفروش‌های کم‌موجودی را زودتر ببینید.</p>
        </div>
        <div className="actions">
          <button onClick={() => setRefresh((v) => v + 1)} disabled={busy}>
            <ArrowClockwise aria-hidden="true" size={20} />
            تازه‌سازی
          </button>
          <a
            className="button secondary"
            href={`/api/v1/export.csv?${new URLSearchParams({ ...(start ? { start } : {}), ...(end ? { end } : {}) })}`}
          >
            <ArrowDown size={20} aria-hidden="true" />
            خروجی CSV
          </a>
        </div>
      </div>
      <ErrorNotice error={error} />
      {!!data?.stale_count && (
        <p className="notice" role="status">
          موجودی {number(data.stale_count)} ترکیب کالا بیش از ۲۴ ساعت به‌روز
          نشده است. پیش از تصمیم تولید، گزارش موجودی تازه وارد کنید.
        </p>
      )}
      {data?.sales_mode === "aggregate" && (
        <p className="notice">
          فروش از گزارش تجمیعی بازهٔ بالا خوانده می‌شود؛ با سفارش‌های جزئی ترکیب
          نمی‌شود.
        </p>
      )}
      <section className="summary" aria-label="خلاصهٔ انبار" aria-busy={busy}>
        {(["low", "normal", "high"] as const).map((key, index) => (
          <div className="metric" key={key}>
            <span className={`metric-icon ${key}`}>
              {index === 0 ? (
                <WarningCircle size={22} aria-hidden="true" />
              ) : (
                <Package size={22} aria-hidden="true" />
              )}
            </span>
            <span>{stateText[key]}</span>
            <strong>{data ? number(data.counts[key]) : "…"}</strong>
            <small>ترکیب رنگ و سایز</small>
          </div>
        ))}
        <div className="metric">
          <span className="metric-icon neutral">
            <TrendUp size={22} aria-hidden="true" />
          </span>
          <span>نیازمند تأمین</span>
          <strong>{data ? number(data.priorities) : "…"}</strong>
          <small>با فروش ثبت‌شده</small>
        </div>
      </section>
      <section className="panel inventory">
        <div className="section-heading">
          <h2>کالاهای انبار</h2>
          <span className="muted">
            آخرین موجودی: {dateText(data?.data_updated_at || null)}
          </span>
        </div>
        <form className="filters" onSubmit={filter}>
          <div className="field search-field">
            <label htmlFor="search">جست‌وجوی کالا</label>
            <div className="input-icon">
              <MagnifyingGlass size={20} aria-hidden="true" />
              <input
                id="search"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="نام، کد، رنگ یا سایز"
                maxLength={100}
              />
            </div>
          </div>
          <div className="field">
            <label htmlFor="category">دسته‌بندی</label>
            <select
              id="category"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            >
              <option value="">همهٔ دسته‌ها</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="stock-state">وضعیت موجودی</label>
            <select
              id="stock-state"
              value={state}
              onChange={(e) => setState(e.target.value)}
            >
              <option value="">همهٔ وضعیت‌ها</option>
              {Object.entries(stateText).map(([key, label]) => (
                <option value={key} key={key}>
                  {label}
                </option>
              ))}
            </select>
          </div>
          <button className="button" disabled={busy}>
            اعمال فیلتر
          </button>
          <details className="advanced">
            <summary>بازه و اولویت</summary>
            <div className="date-filters">
              <div className="field">
                <label htmlFor="start">از تاریخ (میلادی)</label>
                <input
                  id="start"
                  type="date"
                  value={start}
                  onChange={(e) => setStart(e.target.value)}
                  disabled={data?.sales_mode === "aggregate"}
                />
              </div>
              <div className="field">
                <label htmlFor="end">تا تاریخ (میلادی)</label>
                <input
                  id="end"
                  type="date"
                  value={end}
                  onChange={(e) => setEnd(e.target.value)}
                  disabled={data?.sales_mode === "aggregate"}
                />
              </div>
              <label className="checkbox">
                <input
                  type="checkbox"
                  checked={priority}
                  onChange={(e) => setPriority(e.target.checked)}
                />
                فقط اولویت‌های تأمین
              </label>
            </div>
          </details>
        </form>
        {busy && (
          <p className="loading" role="status">
            در حال خواندن اطلاعات…
          </p>
        )}
        {!busy && data && data.total === 0 && (
          <Empty
            title="موردی برای نمایش نیست"
            action={
              <a className="button" href="/sources">
                ورود اطلاعات انبار
                <ArrowLeft size={20} aria-hidden="true" />
              </a>
            }
          >
            اگر هنوز داده‌ای ندارید، ابتدا موجودی و سپس فروش را وارد کنید. در
            غیر این صورت فیلترها را بررسی کنید.
          </Empty>
        )}
        {data && data.rows.length > 0 && (
          <>
            <div
              className="table-region"
              tabIndex={0}
              role="region"
              aria-label="جدول موجودی، قابل پیمایش افقی"
            >
              <table>
                <thead>
                  <tr>
                    <th scope="col">کالا و ترکیب</th>
                    <th scope="col">دسته‌بندی</th>
                    <th scope="col">موجودی</th>
                    <th scope="col">فروش خالص</th>
                    <th scope="col">وضعیت</th>
                    <th scope="col">اولویت</th>
                    <th scope="col">وضعیت تأمین</th>
                  </tr>
                </thead>
                <tbody>
                  {data.rows.map((row) => (
                    <tr key={row.id}>
                      <td>
                        <strong>{row.name}</strong>
                        <small>
                          {row.color} · سایز <bdi>{row.size}</bdi>
                        </small>
                        <small>
                          <bdi>{row.sku}</bdi>
                        </small>
                        {row.stale && (
                          <small className="muted">
                            موجودی نیازمند به‌روزرسانی
                          </small>
                        )}
                        <details className="mobile-row-details">
                          <summary>جزئیات کالا</summary>
                          <p>
                            {row.category} · موجودی ثبت‌شده:{" "}
                            {dateText(row.updated_at)}
                          </p>
                          <label htmlFor={`mobile-s-${row.id}`}>
                            وضعیت تأمین
                          </label>
                          <select
                            id={`mobile-s-${row.id}`}
                            value={row.replenishment}
                            disabled={updating === row.id}
                            onChange={(e) => replenish(row, e.target.value)}
                          >
                            {Object.entries(productionText).map(
                              ([key, label]) => (
                                <option key={key} value={key}>
                                  {label}
                                </option>
                              ),
                            )}
                          </select>
                        </details>
                      </td>
                      <td>{row.category}</td>
                      <td className="numeric">{number(row.available)}</td>
                      <td className="numeric">{number(row.net_units)}</td>
                      <td>
                        <span className={`state ${row.state}`}>
                          {stateText[row.state]}
                        </span>
                      </td>
                      <td>
                        {row.priority !== null ? (
                          <span className="priority">
                            {number(row.priority)}
                          </span>
                        ) : row.needs_review ? (
                          "نیازمند بررسی"
                        ) : (
                          "بدون اولویت"
                        )}
                      </td>
                      <td>
                        <label className="sr-only" htmlFor={`s-${row.id}`}>
                          وضعیت تأمین {row.name} {row.color} {row.size}
                        </label>
                        <select
                          id={`s-${row.id}`}
                          value={row.replenishment}
                          disabled={updating === row.id}
                          onChange={(e) => replenish(row, e.target.value)}
                        >
                          {Object.entries(productionText).map(
                            ([key, label]) => (
                              <option value={key} key={key}>
                                {label}
                              </option>
                            ),
                          )}
                        </select>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="pagination">
              <span>
                {number(data.total)} مورد، صفحهٔ {number(page)}
              </span>
              <div>
                <button
                  aria-label="صفحهٔ قبل"
                  disabled={page <= 1 || busy}
                  onClick={() => setPage((v) => v - 1)}
                >
                  <ArrowRight size={18} aria-hidden="true" />
                </button>
                <button
                  aria-label="صفحهٔ بعد"
                  disabled={page * 50 >= data.total || busy}
                  onClick={() => setPage((v) => v + 1)}
                >
                  <ArrowLeft size={18} aria-hidden="true" />
                </button>
              </div>
            </div>
          </>
        )}
      </section>
      <Assistant start={data?.period_start} end={data?.period_end} />
    </>
  );
}

function Assistant({ start, end }: { start?: string; end?: string }) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [answer, setAnswer] = useState<{
    message: string;
    items: Variant[];
  } | null>(null);
  const [error, setError] = useState<unknown>(null);
  const ref = useRef<HTMLButtonElement>(null);
  async function ask(topic: string) {
    setBusy(true);
    setError(null);
    try {
      setAnswer(
        await api(
          `/v1/assistant?${new URLSearchParams({ topic, ...(start ? { start } : {}), ...(end ? { end } : {}) })}`,
        ),
      );
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  function close() {
    setOpen(false);
    ref.current?.focus();
  }
  return (
    <aside
      className="assistant"
      onKeyDown={(e) => {
        if (e.key === "Escape") close();
      }}
      onBlur={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget)) setOpen(false);
      }}
    >
      {open && (
        <section id="assistant-panel" aria-label="پرسش‌های دستیار">
          <div className="section-heading">
            <h2>دستیار انبار</h2>
            <button
              className="icon-button"
              onClick={close}
              aria-label="بستن دستیار"
            >
              <X size={20} aria-hidden="true" />
            </button>
          </div>
          <p className="muted">
            پیشنهادها از اطلاعات همین فروشگاه محاسبه می‌شوند.
          </p>
          <div className="questions">
            {[
              ["priorities", "چه کالاهایی تأمین شوند؟"],
              ["excess", "موجودی زیاد کدام‌هاست؟"],
              ["review", "چه مواردی بررسی شوند؟"],
              ["explain", "چرا این ترتیب؟"],
            ].map(([key, label]) => (
              <button
                key={key}
                aria-disabled={busy}
                aria-busy={busy}
                onClick={() => {
                  if (!busy) void ask(key);
                }}
              >
                {label}
              </button>
            ))}
          </div>
          <ErrorNotice error={error} />
          <div role="status" aria-live="polite">
            {busy
              ? "در حال بررسی…"
              : answer && (
                  <>
                    <p>{answer.message}</p>
                    {answer.items.map((item) => (
                      <div className="assistant-item" key={item.id}>
                        <strong>{item.name}</strong>
                        <span>
                          {item.color}، سایز <bdi>{item.size}</bdi>
                        </span>
                        <small>
                          {number(item.net_units)} فروش،{" "}
                          {number(item.available)} موجودی
                        </small>
                      </div>
                    ))}
                  </>
                )}
          </div>
        </section>
      )}
      <button
        ref={ref}
        className="assistant-trigger"
        aria-expanded={open}
        aria-controls="assistant-panel"
        onClick={() => setOpen((v) => !v)}
      >
        <ChatCircleDots aria-hidden="true" size={22} />
        دستیار انبار
      </button>
    </aside>
  );
}
