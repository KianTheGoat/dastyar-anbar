import { useEffect, useState, type FormEvent } from "react";
import {
  ArrowDown,
  LockKey,
  SlidersHorizontal,
  Trash,
} from "@phosphor-icons/react";
import {
  api,
  dateText,
  json,
  number,
  type Category,
  type Owner,
  type Session,
} from "./api";
import { Empty, ErrorNotice, Modal, Success } from "./ui";

export function SettingsPage() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(true);
  useEffect(() => {
    api<Category[]>("/v1/categories")
      .then(setCategories)
      .catch(setError)
      .finally(() => setBusy(false));
  }, []);
  return (
    <>
      <div className="page-heading">
        <p className="eyeline">قانون هر دسته</p>
        <h1>حدهای موجودی</h1>
        <p>
          حدها برای دسته‌بندی تعیین می‌شوند و روی هر رنگ و سایز آن اعمال
          می‌شوند.
        </p>
      </div>
      <ErrorNotice error={error} />
      {busy ? (
        <p role="status">در حال خواندن دسته‌ها…</p>
      ) : categories.length === 0 ? (
        <section className="panel">
          <Empty
            title="هنوز دسته‌بندی ندارید"
            action={
              <a className="button" href="/sources">
                ورود موجودی
              </a>
            }
          >
            دسته‌های فایل موجودی به‌صورت خودکار ساخته می‌شوند. سپس حدهایشان را
            اینجا تنظیم کنید.
          </Empty>
        </section>
      ) : (
        <div className="category-grid">
          {categories.map((c) => (
            <CategoryCard key={c.id} category={c} />
          ))}
        </div>
      )}
    </>
  );
}
function CategoryCard({ category }: { category: Category }) {
  const [low, setLow] = useState(String(category.low_max));
  const [high, setHigh] = useState(String(category.high_min));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [saved, setSaved] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setSaved(false);
    try {
      if (Number(high) <= Number(low))
        throw new Error("مرز موجودی زیاد باید از مرز کمبود بزرگ‌تر باشد.");
      await api(`/v1/categories/${category.id}`, {
        method: "PATCH",
        body: json({ low_max: Number(low), high_min: Number(high) }),
      });
      setSaved(true);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel category-card">
      <h2>
        <SlidersHorizontal size={22} aria-hidden="true" />
        {category.name}
      </h2>
      <ErrorNotice error={error} />
      {saved && <Success>حدهای این دسته ذخیره شد.</Success>}
      <form onSubmit={submit}>
        <div className="mapping-grid">
          <div className="field">
            <label htmlFor={`low-${category.id}`}>کمبود تا چند عدد؟</label>
            <input
              id={`low-${category.id}`}
              type="number"
              min={0}
              max={1000000}
              step={1}
              value={low}
              onChange={(e) => {
                setLow(e.target.value);
                setSaved(false);
              }}
              required
            />
          </div>
          <div className="field">
            <label htmlFor={`high-${category.id}`}>
              موجودی زیاد از چند عدد؟
            </label>
            <input
              id={`high-${category.id}`}
              type="number"
              min={1}
              max={1000000}
              step={1}
              value={high}
              onChange={(e) => {
                setHigh(e.target.value);
                setSaved(false);
              }}
              required
            />
          </div>
        </div>
        <p className="threshold-explanation">
          {number(Number(low) || 0)} و کمتر: کمبود · {number(Number(high) || 0)}{" "}
          و بیشتر: زیاد. مقدار بین این دو، مناسب است.
        </p>
        <button className="button" disabled={busy}>
          {busy ? "در حال ذخیره…" : "ذخیرهٔ حدها"}
        </button>
      </form>
    </section>
  );
}

export function AccountPage({
  owner,
  onSession,
  onDeleted,
}: {
  owner: Owner;
  onSession: (value: Session) => void;
  onDeleted: () => void;
}) {
  const [current, setCurrent] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [success, setSuccess] = useState("");
  const [open, setOpen] = useState(false);
  const [deletionPassword, setDeletionPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [activity, setActivity] = useState<
    { action: string; row_count: number | null; created_at: string }[]
  >([]);
  useEffect(() => {
    api<typeof activity>("/v1/activity").then(setActivity).catch(setError);
  }, []);
  async function changePassword(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setSuccess("");
    try {
      const result = await api<Session>("/v1/auth/password/change", {
        method: "POST",
        body: json({ current_password: current, password }),
      });
      onSession(result);
      setCurrent("");
      setPassword("");
      setSuccess("رمز تغییر کرد. نشست‌های دیگر بسته شدند.");
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  async function deleteAccount(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api("/v1/account", {
        method: "DELETE",
        body: json({ password: deletionPassword, confirmation }),
      });
      setOpen(false);
      onDeleted();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  const labels: Record<string, string> = {
    account_registered: "ساخت حساب",
    login: "ورود",
    password_changed: "تغییر رمز",
    password_reset: "بازیابی رمز",
    email_verified: "تأیید ایمیل",
    import_inventory: "ورود موجودی",
    import_sales: "ورود فروش",
    import_aggregate: "ورود فروش تجمیعی",
    category_thresholds_changed: "تغییر حدهای دسته",
    replenishment_changed: "تغییر وضعیت تأمین",
    csv_export: "خروجی CSV",
    account_export: "خروجی کامل",
    sheet_connected: "اتصال شیت",
    sheet_disconnected: "قطع شیت",
    sheet_sync: "اعمال گوگل‌شیت",
  };
  return (
    <>
      <div className="page-heading">
        <p className="eyeline">کنترل حساب و اطلاعات</p>
        <h1>حساب فروشگاه</h1>
        <p>
          {owner.workspace_name} · <bdi>{owner.email}</bdi>
        </p>
      </div>
      <ErrorNotice error={error} />
      {success && <Success>{success}</Success>}
      <div className="account-grid">
        <section className="panel">
          <h2>
            <LockKey size={22} aria-hidden="true" />
            تغییر رمز ورود
          </h2>
          <form onSubmit={changePassword}>
            <div className="field">
              <label htmlFor="current-password">رمز فعلی</label>
              <input
                id="current-password"
                type="password"
                autoComplete="current-password"
                value={current}
                onChange={(e) => setCurrent(e.target.value)}
                required
                maxLength={128}
              />
            </div>
            <div className="field">
              <label htmlFor="new-password">رمز تازه</label>
              <input
                id="new-password"
                type="password"
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={12}
                maxLength={128}
                aria-describedby="new-password-help"
              />
              <small id="new-password-help">
                حداقل ۱۲ نویسه. همهٔ نشست‌های قبلی با تغییر رمز بسته می‌شوند.
              </small>
            </div>
            <button className="button" disabled={busy}>
              {busy ? "در حال ثبت…" : "ثبت رمز تازه"}
            </button>
          </form>
        </section>
        <section className="panel">
          <h2>اطلاعات در اختیار شماست</h2>
          <p>
            نسخهٔ کامل کالاها، دسته‌ها و فروش را در قالب JSON دریافت کنید. خروجی
            شامل رمز، نشست یا کلید اتصال نیست.
          </p>
          <a className="button secondary" href="/api/v1/account/export">
            <ArrowDown size={20} aria-hidden="true" />
            دریافت اطلاعات فروشگاه
          </a>
          <p className="muted">
            برای راه‌اندازی حساب گوگل‌شیت، شناسهٔ فروشگاه را به ارائه‌دهنده
            بدهید:
          </p>
          <code className="workspace-id">
            <bdi>{owner.workspace_id}</bdi>
          </code>
        </section>
      </div>
      <section className="panel history">
        <h2>فعالیت‌های اخیر</h2>
        {activity.length === 0 ? (
          <p>فعالیتی ثبت نشده است.</p>
        ) : (
          <ul>
            {activity.map((item, i) => (
              <li key={i}>
                <span>{labels[item.action] || "به‌روزرسانی اطلاعات"}</span>
                <span>
                  {item.row_count !== null
                    ? `${number(item.row_count)} ردیف`
                    : ""}
                </span>
                <time>{dateText(item.created_at)}</time>
              </li>
            ))}
          </ul>
        )}
      </section>
      <section className="panel danger-zone">
        <h2>حذف حساب و اطلاعات</h2>
        <p>
          حساب، موجودی، فروش، پیش‌نمایش‌ها و اتصال شیت حذف می‌شوند. ابتدا خروجی
          کامل بگیرید. حذف از نسخه‌های پشتیبان طبق دورهٔ نگهداری اعلام‌شده انجام
          می‌شود.
        </p>
        <button
          className="danger-button"
          onClick={() => {
            setError(null);
            setOpen(true);
          }}
        >
          <Trash size={20} aria-hidden="true" />
          حذف حساب فروشگاه
        </button>
      </section>
      <Modal
        open={open}
        title="حذف حساب فروشگاه"
        close={() => {
          if (!busy) setOpen(false);
        }}
      >
        <p>
          این کار قابل بازگشت نیست. حساب و داده‌های همین فروشگاه حذف می‌شوند.
        </p>
        <ErrorNotice error={error} />
        <form onSubmit={deleteAccount}>
          <div className="field">
            <label htmlFor="delete-password">رمز فعلی</label>
            <input
              id="delete-password"
              type="password"
              autoComplete="current-password"
              value={deletionPassword}
              onChange={(e) => setDeletionPassword(e.target.value)}
              required
              maxLength={128}
            />
          </div>
          <div className="field">
            <label htmlFor="delete-confirmation">
              برای تأیید، «حذف حساب» را بنویسید
            </label>
            <input
              id="delete-confirmation"
              value={confirmation}
              onChange={(e) => setConfirmation(e.target.value)}
              required
            />
          </div>
          <button
            className="danger-button"
            disabled={busy || confirmation !== "حذف حساب"}
          >
            {busy ? "در حال حذف…" : "حذف دائمی حساب"}
          </button>
        </form>
        <button disabled={busy} onClick={() => setOpen(false)}>
          انصراف
        </button>
      </Modal>
    </>
  );
}
