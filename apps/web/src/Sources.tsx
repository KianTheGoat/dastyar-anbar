import { useEffect, useState, type FormEvent } from "react";
import {
  ArrowDown,
  ArrowLeft,
  CheckCircle,
  FileCsv,
  Link,
  UploadSimple,
} from "@phosphor-icons/react";
import { api, dateText, json, number } from "./api";
import { ErrorNotice, Modal, Success } from "./ui";

type Kind = "inventory" | "sales" | "aggregate";
type Headers = {
  headers: string[];
  mapping: Record<string, string>;
  fields: string[];
  row_count: number;
  status_values: string[];
  status_mapping: Record<string, string>;
};
type Preview = {
  id?: string;
  kind: string;
  row_count: number;
  sample?: Record<string, unknown>[];
  errors?: { row: number; field: string; code: string }[];
  changes_sales_mode?: boolean;
  expires_at?: string;
  inventory_rows?: number;
  sales_rows?: number;
};
export const fieldText: Record<string, string> = {
  sku: "کد کالا",
  name: "نام کالا",
  category: "دسته‌بندی",
  color: "رنگ",
  size: "سایز",
  available: "موجودی قابل فروش",
  source: "منبع فروش",
  order_id: "شماره سفارش",
  line_id: "شناسه ردیف سفارش",
  sold_at: "تاریخ فروش",
  quantity: "تعداد فروش",
  status: "وضعیت سفارش",
  returned_quantity: "تعداد مرجوعی",
  net_units: "فروش خالص",
  period_start: "شروع بازه",
  period_end: "پایان بازه",
};
const statuses: Record<string, string> = {
  preparing: "آماده‌سازی، فروش محسوب شود",
  shipping: "ارسال، فروش محسوب شود",
  completed: "تکمیل، فروش محسوب شود",
  pending: "در انتظار، محاسبه نشود",
  cancelled: "لغو، محاسبه نشود",
  refunded: "مرجوعی کامل، محاسبه نشود",
};

export function Sources() {
  const [kind, setKind] = useState<Kind>("inventory");
  const [file, setFile] = useState<File | null>(null);
  const [info, setInfo] = useState<Headers | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [statusMap, setStatusMap] = useState<Record<string, string>>({});
  const [calendar, setCalendar] = useState("gregorian");
  const [finalized, setFinalized] = useState(false);
  const [sheet, setSheet] = useState("");
  const [snapshot, setSnapshot] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [success, setSuccess] = useState("");
  const [preview, setPreview] = useState<Preview | null>(null);
  const [history, setHistory] = useState<
    { kind: string; row_count: number; applied: boolean; created_at: string }[]
  >([]);
  function loadHistory() {
    api<typeof history>("/v1/imports").then(setHistory).catch(setError);
  }
  useEffect(loadHistory, []);
  function formData() {
    const form = new FormData();
    if (file) form.set("file", file);
    form.set("kind", kind);
    form.set("sheet", sheet);
    return form;
  }
  async function readHeaders(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setSuccess("");
    setPreview(null);
    try {
      const form = formData();
      if (mapping.status) form.set("status_column", mapping.status);
      const result = await api<Headers>("/v1/imports/headers", {
        method: "POST",
        body: form,
      });
      setInfo(result);
      setMapping((previous) =>
        Object.keys(previous).length ? previous : result.mapping,
      );
      setStatusMap(result.status_mapping);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  async function inspect() {
    setBusy(true);
    setError(null);
    setSuccess("");
    try {
      const form = formData();
      form.set(
        "mapping",
        json(Object.fromEntries(Object.entries(mapping).filter(([, v]) => v))),
      );
      form.set("status_mapping", json(statusMap));
      form.set("calendar", calendar);
      form.set("timezone", "Asia/Tehran");
      form.set("finalized", String(finalized));
      if (kind === "inventory") {
        if (!snapshot || !confirmed)
          throw new Error("زمان ثبت موجودی را انتخاب و تأیید کنید.");
        form.set("snapshot_at", new Date(snapshot).toISOString());
      }
      setPreview(
        await api<Preview>("/v1/imports/preview", {
          method: "POST",
          body: form,
        }),
      );
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  async function apply() {
    if (!preview?.id) return;
    setBusy(true);
    setError(null);
    try {
      const value = await api<{ row_count: number }>(
        `/v1/imports/${preview.id}/apply`,
        { method: "POST" },
      );
      setPreview(null);
      setInfo(null);
      setSuccess(`${number(value.row_count)} ردیف اعمال شد.`);
      loadHistory();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <div className="page-heading">
        <p className="eyeline">اطلاعات شما، تصمیم روشن‌تر</p>
        <h1>ورود و اتصال اطلاعات</h1>
        <p>
          ابتدا موجودی، سپس فروش را وارد کنید. پیش‌نمایش را پیش از اعمال بررسی
          کنید.
        </p>
      </div>
      <ErrorNotice error={error} />
      {success && <Success>{success}</Success>}
      <div className="sources-layout">
        <section className="panel">
          <div className="section-heading">
            <h2>
              <UploadSimple size={22} aria-hidden="true" />
              ورود فایل
            </h2>
            <span className="muted">CSV یا XLSX</span>
          </div>
          <form onSubmit={readHeaders}>
            <div className="field">
              <label htmlFor="import-kind">نوع اطلاعات</label>
              <select
                id="import-kind"
                value={kind}
                onChange={(e) => {
                  setKind(e.target.value as Kind);
                  setInfo(null);
                  setMapping({});
                  setPreview(null);
                  setStatusMap({});
                }}
              >
                <option value="inventory">موجودی فعلی انبار</option>
                <option value="sales">ردیف‌های سفارش و فروش</option>
                <option value="aggregate">گزارش فروش تجمیعی</option>
              </select>
            </div>
            <div className="upload-zone">
              <FileCsv size={36} aria-hidden="true" />
              <label htmlFor="import-file">فایل اطلاعات را انتخاب کنید</label>
              <input
                id="import-file"
                type="file"
                accept=".csv,.xlsx"
                required
                onChange={(e) => {
                  setFile(e.target.files?.[0] || null);
                  setInfo(null);
                  setMapping({});
                  setPreview(null);
                }}
              />
              <small>
                حداکثر ۵ مگابایت و ۱۰٬۰۰۰ ردیف. فرمول‌ها را به مقدار ثابت تبدیل
                کنید.
              </small>
            </div>
            <div className="actions">
              <a
                href={`/api/templates/${kind}.csv`}
                className="button secondary"
              >
                <ArrowDown size={18} aria-hidden="true" />
                قالب خالی CSV
              </a>
              <button className="button" disabled={busy || !file}>
                {busy ? "در حال خواندن…" : "خواندن ستون‌ها"}
                <ArrowLeft size={18} aria-hidden="true" />
              </button>
            </div>
            <details className="advanced">
              <summary>نام برگ Excel</summary>
              <div className="field">
                <label htmlFor="excel-sheet">
                  نام برگ (خالی یعنی اولین برگ)
                </label>
                <input
                  id="excel-sheet"
                  value={sheet}
                  onChange={(e) => setSheet(e.target.value)}
                  maxLength={100}
                />
              </div>
            </details>
          </form>
          {info && (
            <div className="mapping">
              <h3>ستون‌ها را تطبیق دهید</h3>
              <p>
                {number(info.row_count)} ردیف خوانده شد. فقط ستون‌های انتخابی
                نگهداری می‌شوند.
              </p>
              <div className="mapping-grid">
                {info.fields.map((field) => (
                  <div className="field" key={field}>
                    <label htmlFor={`map-${field}`}>{fieldText[field]}</label>
                    <select
                      id={`map-${field}`}
                      value={mapping[field] || ""}
                      onChange={(e) =>
                        setMapping((v) => ({ ...v, [field]: e.target.value }))
                      }
                    >
                      <option value="">انتخاب نشده</option>
                      {info.headers.map((h) => (
                        <option key={h} value={h}>
                          {h}
                        </option>
                      ))}
                    </select>
                  </div>
                ))}
              </div>
              {kind !== "inventory" && (
                <div className="field">
                  <label htmlFor="calendar">تقویم تاریخ‌های فایل</label>
                  <select
                    id="calendar"
                    value={calendar}
                    onChange={(e) => setCalendar(e.target.value)}
                  >
                    <option value="gregorian">میلادی، YYYY-MM-DD</option>
                    <option value="jalali">
                      شمسی، YYYY-MM-DD یا YYYY/MM/DD
                    </option>
                  </select>
                  <small>
                    ساعت‌های بدون منطقهٔ زمانی، به وقت تهران خوانده می‌شوند.
                  </small>
                </div>
              )}
              {kind === "inventory" && (
                <>
                  <div className="field">
                    <label htmlFor="snapshot">
                      تاریخ و ساعت ثبت موجودی (زمان دستگاه)
                    </label>
                    <input
                      id="snapshot"
                      type="datetime-local"
                      value={snapshot}
                      onChange={(e) => {
                        setSnapshot(e.target.value);
                        setConfirmed(false);
                      }}
                    />
                    <small>
                      زمان واقعی گزارش را وارد کنید تا فایل قدیمی جای دادهٔ جدید
                      را نگیرد.
                    </small>
                  </div>
                  <label className="checkbox">
                    <input
                      type="checkbox"
                      checked={confirmed}
                      onChange={(e) => setConfirmed(e.target.checked)}
                    />
                    موجودی فایل مربوط به همین زمان است.
                  </label>
                </>
              )}
              {kind === "sales" && (
                <>
                  <label className="checkbox">
                    <input
                      type="checkbox"
                      checked={finalized}
                      onChange={(e) => setFinalized(e.target.checked)}
                    />
                    گزارش فروش نهایی است و ستون وضعیت ندارد.
                  </label>
                  {!finalized && info.status_values.length > 0 && (
                    <fieldset>
                      <legend>معنای وضعیت‌ها</legend>
                      {info.status_values.map((label) => (
                        <div className="field" key={label}>
                          <label htmlFor={`status-${label}`}>{label}</label>
                          <select
                            id={`status-${label}`}
                            value={statusMap[label] || ""}
                            onChange={(e) =>
                              setStatusMap((v) => ({
                                ...v,
                                [label]: e.target.value,
                              }))
                            }
                          >
                            <option value="">انتخاب کنید</option>
                            {Object.entries(statuses).map(([key, text]) => (
                              <option key={key} value={key}>
                                {text}
                              </option>
                            ))}
                          </select>
                        </div>
                      ))}
                    </fieldset>
                  )}
                </>
              )}
              {kind === "aggregate" && (
                <p className="notice">
                  این گزارش، مبنای فروش بازهٔ خودش می‌شود و با سفارش‌های جزئی
                  ترکیب نمی‌شود.
                </p>
              )}
              <button className="button" disabled={busy} onClick={inspect}>
                {busy ? "در حال بررسی…" : "ساخت پیش‌نمایش"}
              </button>
            </div>
          )}
          <p className="secure-note">
            نام، تلفن، نشانی و اطلاعات پرداخت مشتری را از فایل کنار بگذارید.
          </p>
        </section>
        <div>
          <Sheets onApplied={loadHistory} />
          <section className="panel compact-panel">
            <h2>راهنمای ورود</h2>
            <p>
              کد یک رنگ و سایز باید در هر دو جدول یکسان باشد. کدها را در Excel
              به‌صورت متن نگه دارید تا صفر ابتدایی حذف نشود.
            </p>
            <p>
              موجودی، جایگزین تعداد همان کد می‌شود؛ کالاهای غایب تغییر نمی‌کنند.
              تغییر وضعیت سفارش، فروش تازه ایجاد نمی‌کند.
            </p>
            <a href="/guide">
              راهنمای کامل
              <ArrowLeft size={18} aria-hidden="true" />
            </a>
          </section>
        </div>
      </div>
      <section className="panel history">
        <h2>دریافت‌های اخیر</h2>
        {history.length === 0 ? (
          <p>هنوز فایلی بررسی نشده است.</p>
        ) : (
          <ul>
            {history.map((item, index) => (
              <li key={index}>
                <span>
                  {
                    (
                      {
                        inventory: "موجودی",
                        sales: "فروش سفارش‌ها",
                        aggregate: "فروش تجمیعی",
                        bundle: "گوگل‌شیت",
                      } as Record<string, string>
                    )[item.kind]
                  }
                </span>
                <span>{number(item.row_count)} ردیف</span>
                <span
                  className={item.applied ? "state normal" : "state neutral"}
                >
                  {item.applied ? "اعمال شده" : "پیش‌نمایش"}
                </span>
                <time>{dateText(item.created_at)}</time>
              </li>
            ))}
          </ul>
        )}
      </section>
      <PreviewModal
        preview={preview}
        close={() => setPreview(null)}
        apply={apply}
        busy={busy}
      />
    </>
  );
}

function PreviewModal({
  preview,
  close,
  apply,
  busy,
}: {
  preview: Preview | null;
  close: () => void;
  apply: () => void;
  busy: boolean;
}) {
  return (
    <Modal
      open={!!preview}
      title="بررسی پیش از اعمال"
      close={() => {
        if (!busy) close();
      }}
    >
      {preview && (
        <>
          {preview.errors?.length ? (
            <>
              <p>خطاها را در فایل اصلاح کنید. هیچ ردیفی اعمال نشده است.</p>
              <ul className="error-list">
                {preview.errors.map((e, i) => (
                  <li key={i}>
                    ردیف {number(e.row)}، {fieldText[e.field] || e.field}: مقدار
                    یا ساختار معتبر نیست.
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <>
              <p>{number(preview.row_count)} ردیف آمادهٔ اعمال است.</p>
              {preview.kind === "bundle" && (
                <p>
                  {number(preview.inventory_rows || 0)} ردیف موجودی و{" "}
                  {number(preview.sales_rows || 0)} ردیف فروش با هم و در یک
                  تراکنش اعمال می‌شوند.
                </p>
              )}
              {preview.changes_sales_mode && (
                <p className="notice">
                  مبنای گزارش فروش به نوع فایل انتخابی تغییر می‌کند.
                </p>
              )}
              {preview.kind === "inventory" && (
                <p>
                  تعداد کدهای فایل جایگزین می‌شود. کدهای غایب تغییر نمی‌کنند.
                  دسته‌های تازه با مرز کمبود ۳ و موجودی زیاد ۵ ساخته می‌شوند و
                  در تنظیمات قابل تغییرند.
                </p>
              )}
              {preview.sample && (
                <div
                  className="table-region"
                  role="region"
                  tabIndex={0}
                  aria-label="نمونهٔ ردیف‌های پیش‌نمایش"
                >
                  <table>
                    <thead>
                      <tr>
                        {Object.keys(preview.sample[0] || {}).map((k) => (
                          <th key={k}>{fieldText[k] || k}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {preview.sample.map((row, i) => (
                        <tr key={i}>
                          {Object.values(row).map((v, j) => (
                            <td key={j}>{String(v)}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              <p className="muted">
                اعتبار پیش‌نمایش: {dateText(preview.expires_at || null)}
              </p>
              <button className="button" disabled={busy} onClick={apply}>
                {busy ? "در حال اعمال…" : "تأیید و اعمال اطلاعات"}
                <CheckCircle size={20} aria-hidden="true" />
              </button>
            </>
          )}
          <button disabled={busy} onClick={close}>
            بازگشت
          </button>
        </>
      )}
    </Modal>
  );
}

type ConnectionData = {
  configured: boolean;
  service_account_email: string | null;
  connection: {
    spreadsheet_id: string;
    inventory_range: string;
    sales_range: string;
    sales_kind: "sales" | "aggregate";
    calendar: string;
    finalized: boolean;
    inventory_mapping: Record<string, string>;
    sales_mapping: Record<string, string>;
    status_mapping: Record<string, string>;
  } | null;
  last_synced_at: string | null;
};
function Sheets({ onApplied }: { onApplied: () => void }) {
  const [info, setInfo] = useState<ConnectionData | null>(null);
  const [id, setId] = useState("");
  const [invTab, setInvTab] = useState("inventory");
  const [salesTab, setSalesTab] = useState("sales");
  const [kind, setKind] = useState<"sales" | "aggregate">("sales");
  const [calendar, setCalendar] = useState("gregorian");
  const [finalized, setFinalized] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [success, setSuccess] = useState("");
  const [invMap, setInvMap] = useState("{}");
  const [salesMap, setSalesMap] = useState("{}");
  const [statusMap, setStatusMap] = useState("{}");
  function load() {
    api<ConnectionData>("/v1/sheets/connection")
      .then((value) => {
        setInfo(value);
        const c = value.connection;
        if (c) {
          setId(c.spreadsheet_id);
          setKind(c.sales_kind);
          setCalendar(c.calendar);
          setFinalized(c.finalized);
          setInvTab(c.inventory_range.split("!")[0].replace(/^'|'$/g, ""));
          setSalesTab(c.sales_range.split("!")[0].replace(/^'|'$/g, ""));
          setInvMap(json(c.inventory_mapping));
          setSalesMap(json(c.sales_mapping));
          setStatusMap(json(c.status_mapping));
        }
      })
      .catch(setError);
  }
  useEffect(load, []);
  async function connect(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setSuccess("");
    try {
      const spreadsheetId =
        id.match(/\/spreadsheets\/d\/([a-zA-Z0-9_-]+)/)?.[1] || id.trim();
      await api("/v1/sheets/connect", {
        method: "POST",
        body: json({
          spreadsheet_id: spreadsheetId,
          inventory_range: `'${invTab.replaceAll("'", "''")}'!A1:Z10001`,
          sales_range: `'${salesTab.replaceAll("'", "''")}'!A1:Z10001`,
          sales_kind: kind,
          calendar,
          finalized,
          inventory_mapping: JSON.parse(invMap),
          sales_mapping: JSON.parse(salesMap),
          status_mapping: JSON.parse(statusMap),
        }),
      });
      setSuccess("اتصال ثبت شد. اطلاعات را دریافت و پیش‌نمایش را بررسی کنید.");
      load();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  async function sync() {
    setBusy(true);
    setError(null);
    try {
      setPreview(await api<Preview>("/v1/sheets/sync", { method: "POST" }));
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  async function apply() {
    if (!preview?.id) return;
    setBusy(true);
    setError(null);
    try {
      await api(`/v1/imports/${preview.id}/apply`, { method: "POST" });
      setPreview(null);
      setSuccess("اطلاعات شیت اعمال شد.");
      load();
      onApplied();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  async function disconnect() {
    setBusy(true);
    setError(null);
    try {
      await api("/v1/sheets/connection", { method: "DELETE" });
      setSuccess("اتصال قطع شد. داده‌های قبلی انبار نگه داشته شدند.");
      load();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel sheets-panel">
      <h2>
        <Link size={22} aria-hidden="true" />
        گوگل‌شیت خصوصی
      </h2>
      <ErrorNotice error={error} />
      {success && <Success>{success}</Success>}
      {!info ? (
        <p role="status">در حال بررسی اتصال…</p>
      ) : !info.configured ? (
        <>
          <p>
            ارائه‌دهنده باید حساب اختصاصی گوگل‌شیت این فروشگاه را آماده کند. تا
            آن زمان می‌توانید Excel یا CSV وارد کنید.
          </p>
          <a href="/guide#google">راهنمای آماده‌سازی اتصال</a>
        </>
      ) : (
        <>
          <p>
            فقط شیت‌هایی خوانده می‌شوند که با حساب اختصاصی زیر به اشتراک
            بگذارید. دسترسی نوشتن درخواست نمی‌شود.
          </p>
          <p className="service-email">
            <bdi>{info.service_account_email}</bdi>
          </p>
          <form onSubmit={connect}>
            <div className="field">
              <label htmlFor="sheet-id">پیوند یا شناسهٔ شیت</label>
              <input
                id="sheet-id"
                value={id}
                onChange={(e) => setId(e.target.value)}
                required
                maxLength={250}
                dir="ltr"
              />
            </div>
            <div className="mapping-grid">
              <div className="field">
                <label htmlFor="inventory-tab">نام برگ موجودی</label>
                <input
                  id="inventory-tab"
                  value={invTab}
                  onChange={(e) => setInvTab(e.target.value)}
                  required
                  maxLength={70}
                />
              </div>
              <div className="field">
                <label htmlFor="sales-tab">نام برگ فروش</label>
                <input
                  id="sales-tab"
                  value={salesTab}
                  onChange={(e) => setSalesTab(e.target.value)}
                  required
                  maxLength={70}
                />
              </div>
            </div>
            <div className="field">
              <label htmlFor="sheet-kind">نوع فروش</label>
              <select
                id="sheet-kind"
                value={kind}
                onChange={(e) =>
                  setKind(e.target.value as "sales" | "aggregate")
                }
              >
                <option value="sales">ردیف‌های سفارش</option>
                <option value="aggregate">گزارش تجمیعی</option>
              </select>
            </div>
            <div className="field">
              <label htmlFor="sheet-calendar">تقویم تاریخ‌های شیت</label>
              <select
                id="sheet-calendar"
                value={calendar}
                onChange={(e) => setCalendar(e.target.value)}
              >
                <option value="gregorian">میلادی</option>
                <option value="jalali">شمسی</option>
              </select>
            </div>
            {kind === "sales" && (
              <label className="checkbox">
                <input
                  type="checkbox"
                  checked={finalized}
                  onChange={(e) => setFinalized(e.target.checked)}
                />
                فروش نهایی است و ستون وضعیت ندارد.
              </label>
            )}
            <details className="advanced">
              <summary>تطبیق ستون‌های متفاوت</summary>
              <p>
                برای ستون‌های مطابق قالب، این بخش خالی بماند. نمونهٔ تطبیق نام
                ستون: {`{"sku":"کد محصول"}`}.
              </p>
              <div className="field">
                <label htmlFor="sheet-inv-map">ستون‌های موجودی</label>
                <textarea
                  id="sheet-inv-map"
                  dir="ltr"
                  value={invMap}
                  onChange={(e) => setInvMap(e.target.value)}
                  maxLength={4000}
                />
              </div>
              <div className="field">
                <label htmlFor="sheet-sale-map">ستون‌های فروش</label>
                <textarea
                  id="sheet-sale-map"
                  dir="ltr"
                  value={salesMap}
                  onChange={(e) => setSalesMap(e.target.value)}
                  maxLength={4000}
                />
              </div>
              <div className="field">
                <label htmlFor="sheet-status-map">
                  وضعیت‌ها، نمونه: {`{"ارسال شده":"shipping"}`}
                </label>
                <textarea
                  id="sheet-status-map"
                  dir="ltr"
                  value={statusMap}
                  onChange={(e) => setStatusMap(e.target.value)}
                  maxLength={4000}
                />
              </div>
            </details>
            <button className="button" disabled={busy}>
              ثبت اتصال
            </button>
          </form>
          {info.connection && (
            <div className="connection-actions">
              <p>آخرین اعمال شیت: {dateText(info.last_synced_at)}</p>
              <button disabled={busy} onClick={sync}>
                دریافت و پیش‌نمایش
              </button>
              <button
                disabled={busy}
                className="text-button danger-text"
                onClick={disconnect}
              >
                قطع اتصال
              </button>
            </div>
          )}
        </>
      )}
      <PreviewModal
        preview={preview}
        close={() => setPreview(null)}
        apply={apply}
        busy={busy}
      />
    </section>
  );
}
