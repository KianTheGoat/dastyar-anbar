import { useState, type FormEvent } from "react";
import {
  ArrowLeft,
  CheckCircle,
  ShieldCheck,
  Stack,
} from "@phosphor-icons/react";
import { api, ApiError, json, type Meta, type Session } from "./api";
import { ErrorNotice, Success } from "./ui";

export function Auth({
  meta,
  onSession,
}: {
  meta: Meta;
  onSession: (value: Session) => void;
}) {
  const hash = new URLSearchParams(window.location.hash.slice(1));
  const [mode, setMode] = useState<
    "login" | "register" | "forgot" | "reset" | "verify"
  >(hash.has("reset") ? "reset" : hash.has("verify") ? "verify" : "login");
  const [token] = useState(hash.get("reset") || hash.get("verify") || "");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [accepted, setAccepted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [success, setSuccess] = useState("");
  const [fields, setFields] = useState<string[]>([]);
  const title = {
    login: "به انبارتان خوش آمدید",
    register: "فروشگاهتان را اضافه کنید",
    forgot: "بازیابی رمز ورود",
    reset: "رمز تازه انتخاب کنید",
    verify: "تأیید ایمیل",
  }[mode];
  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setFields([]);
    setSuccess("");
    try {
      if (mode === "forgot") {
        await api("/v1/auth/password/request", {
          method: "POST",
          body: json({ email }),
        });
        setSuccess(
          "اگر این ایمیل واجد شرایط باشد، پیوند بازیابی ارسال می‌شود.",
        );
      } else if (mode === "reset") {
        const result = await api<Session>("/v1/auth/password/reset", {
          method: "POST",
          body: json({ token, password }),
        });
        onSession(result);
        window.history.replaceState(null, "", "/");
        setMode("login");
        setPassword("");
        setSuccess("رمز تغییر کرد و نشست‌های قبلی بسته شدند. اکنون وارد شوید.");
      } else if (mode === "verify") {
        const result = await api<Session>("/v1/auth/verify", {
          method: "POST",
          body: json({
            token,
            password,
            accepted_policy: accepted,
            policy_version: meta.policy_version,
          }),
        });
        window.history.replaceState(null, "", "/");
        onSession(result);
      } else {
        const result = await api<Session & { verification_required?: boolean }>(
          `/v1/auth/${mode}`,
          {
            method: "POST",
            body: json(
              mode === "register"
                ? {
                    email,
                    password,
                    workspace_name: name,
                    accepted_policy: accepted,
                    policy_version: meta.policy_version,
                  }
                : { email, password },
            ),
          },
        );
        if (result.verification_required) {
          setMode("login");
          setPassword("");
          setSuccess(
            "درخواست ثبت شد. اگر آدرس واجد شرایط باشد، پیوند تأیید ارسال می‌شود.",
          );
        } else onSession(result);
      }
    } catch (e) {
      setError(e);
      if (e instanceof ApiError) setFields(e.fields.map((f) => f.field));
    } finally {
      setBusy(false);
    }
  }
  function changeMode(next: typeof mode) {
    setMode(next);
    setError(null);
    setSuccess("");
    setFields([]);
    setPassword("");
  }
  return (
    <div className="auth-layout">
      <section className="auth-story">
        <span className="brand-mark">
          <Stack size={28} aria-hidden="true" />
        </span>
        <p className="eyeline">دستیار انبار، از مجموعهٔ دستیار</p>
        <h1>
          هر رنگ و سایز،
          <br />
          در جای درست.
        </h1>
        <p>
          موجودی را ببینید، پرفروش‌ها را بشناسید و تأمین دوباره را با اطلاعات
          روشن شروع کنید.
        </p>
        <ul className="benefits">
          <li>
            <CheckCircle size={22} aria-hidden="true" />
            حد موجودی برای هر دسته‌بندی
          </li>
          <li>
            <CheckCircle size={22} aria-hidden="true" />
            ورود Excel، CSV و گوگل‌شیت خصوصی
          </li>
          <li>
            <ShieldCheck size={22} aria-hidden="true" />
            اطلاعات هر فروشگاه جدا و محفوظ
          </li>
        </ul>
      </section>
      <section className="auth-form panel">
        <h2>{title}</h2>
        <p>با حساب فروشگاهتان ادامه دهید.</p>
        <ErrorNotice error={error} />
        {success && <Success>{success}</Success>}
        <form onSubmit={submit}>
          {mode === "register" && (
            <div className="field">
              <label htmlFor="workspace_name">نام فروشگاه</label>
              <input
                id="workspace_name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                maxLength={120}
                autoComplete="organization"
                aria-invalid={fields.includes("workspace_name")}
                aria-describedby={
                  fields.includes("workspace_name")
                    ? "workspace-error"
                    : undefined
                }
              />
              {fields.includes("workspace_name") && (
                <small id="workspace-error">نام فروشگاه را بررسی کنید.</small>
              )}
            </div>
          )}
          {!["reset", "verify"].includes(mode) && (
            <div className="field">
              <label htmlFor="email">ایمیل</label>
              <input
                id="email"
                type="email"
                dir="ltr"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                maxLength={254}
                autoComplete="email"
                aria-invalid={fields.includes("email")}
                aria-describedby={
                  fields.includes("email")
                    ? "email-help email-error"
                    : "email-help"
                }
              />
              <small id="email-help">
                برای ورود و بازیابی حساب استفاده می‌شود.
              </small>
              {fields.includes("email") && (
                <small id="email-error">ایمیل معتبر وارد کنید.</small>
              )}
            </div>
          )}
          {mode !== "forgot" && (
            <div className="field">
              <label htmlFor="password">
                {["reset", "verify"].includes(mode) ? "رمز تازه" : "رمز ورود"}
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={mode === "login" ? 1 : 12}
                maxLength={128}
                autoComplete={
                  mode === "login" ? "current-password" : "new-password"
                }
                aria-invalid={fields.includes("password")}
                aria-describedby={
                  fields.includes("password")
                    ? "password-help password-error"
                    : "password-help"
                }
              />
              <small id="password-help">
                {mode === "login"
                  ? "می‌توانید از مدیر رمز مرورگر استفاده کنید."
                  : "حداقل ۱۲ نویسه؛ یک عبارت طولانی انتخاب کنید."}
              </small>
              {fields.includes("password") && (
                <small id="password-error">
                  طول و اعتبار رمز را بررسی کنید.
                </small>
              )}
            </div>
          )}
          {["register", "verify"].includes(mode) && (
            <label className="checkbox">
              <input
                id="accepted_policy"
                type="checkbox"
                checked={accepted}
                onChange={(e) => setAccepted(e.target.checked)}
                required
              />
              <span>
                <a href="/terms" target="_blank" rel="noreferrer">
                  شرایط استفاده
                </a>{" "}
                و{" "}
                <a href="/privacy" target="_blank" rel="noreferrer">
                  حریم خصوصی
                </a>{" "}
                را خوانده‌ام و می‌پذیرم.
              </span>
            </label>
          )}
          {mode === "verify" && (
            <p>با تأیید، مالکیت این ایمیل بررسی و حساب شما باز می‌شود.</p>
          )}
          <button className="button wide" disabled={busy} aria-busy={busy}>
            {busy
              ? "در حال انجام…"
              : {
                  login: "ورود به انبار",
                  register: "ساخت حساب فروشگاه",
                  forgot: "دریافت پیوند بازیابی",
                  reset: "ثبت رمز تازه",
                  verify: "تأیید و ورود",
                }[mode]}
            <ArrowLeft size={20} aria-hidden="true" />
          </button>
        </form>
        <div className="auth-links">
          {mode === "login" ? (
            <>
              <button
                className="text-button"
                onClick={() => changeMode("register")}
              >
                فروشگاه تازه دارید؟ ساخت حساب
              </button>
              {meta.password_recovery_available && (
                <button
                  className="text-button"
                  onClick={() => changeMode("forgot")}
                >
                  رمز را فراموش کرده‌ام
                </button>
              )}
            </>
          ) : (
            <button className="text-button" onClick={() => changeMode("login")}>
              بازگشت به ورود
            </button>
          )}
        </div>
        <p className="secure-note">
          <ShieldCheck size={18} aria-hidden="true" />
          تنها کوکی ضروری ورود استفاده می‌شود.{" "}
          <a href="/cookies">جزئیات کوکی‌ها</a>
        </p>
      </section>
    </div>
  );
}
