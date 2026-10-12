import { useEffect, useState } from "react";
import {
  ArrowClockwise,
  GearSix,
  Moon,
  Package,
  SignOut,
  Stack,
  Sun,
  UploadSimple,
  UserCircle,
} from "@phosphor-icons/react";
import { api, setSession, type Meta, type Session } from "./api";
import { Auth } from "./Auth";
import { Dashboard } from "./Dashboard";
import { Legal } from "./Legal";
import { Sources } from "./Sources";
import { AccountPage, SettingsPage } from "./Settings";
import { ErrorNotice } from "./ui";

export function App() {
  const path = window.location.pathname;
  const authLink = /(?:^|[&#])(reset|verify)=/.test(window.location.hash);
  const legal = ["/privacy", "/terms", "/cookies", "/guide"].includes(path);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [session, setCurrentSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [loggingOut, setLoggingOut] = useState(false);
  const [dark, setDark] = useState(
    document.documentElement.dataset.theme === "dark",
  );
  useEffect(() => {
    document.documentElement.dataset.theme = dark ? "dark" : "light";
  }, [dark]);
  function acceptSession(value: Session) {
    setSession(value);
    setCurrentSession(value);
  }
  async function boot() {
    setLoading(true);
    setError(null);
    try {
      const value = await api<Meta>("/meta");
      setMeta(value);
      if (!legal && value.configured)
        acceptSession(await api<Session>("/v1/auth/session"));
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    boot();
    const expired = () => {
      setCurrentSession(null);
      api<Session>("/v1/auth/session").then(acceptSession).catch(setError);
    };
    window.addEventListener("session-expired", expired);
    return () => window.removeEventListener("session-expired", expired);
  }, []);
  async function logout() {
    setLoggingOut(true);
    setError(null);
    try {
      await api("/v1/auth/logout", { method: "POST" });
      acceptSession(await api<Session>("/v1/auth/session"));
    } catch (e) {
      setError(e);
    } finally {
      setLoggingOut(false);
    }
  }
  function toggleTheme() {
    const next = !dark;
    setDark(next);
    try {
      sessionStorage.setItem("anbar-theme", next ? "dark" : "light");
    } catch {
      /* Disabled storage does not block appearance. */
    }
  }
  const owner = session?.account;
  const links = [
    ["/", "نمای انبار", Package],
    ["/sources", "ورود اطلاعات", UploadSimple],
    ["/settings", "حدهای دسته‌ها", GearSix],
    ["/account", "حساب فروشگاه", UserCircle],
  ] as const;
  return (
    <>
      <a className="skip-link" href="#main">
        رفتن به محتوای اصلی
      </a>
      <header className="header">
        <a className="brand" href="/">
          <Stack aria-hidden="true" size={24} />
          <span>
            دستیار انبار<small>از مجموعهٔ دستیار</small>
          </span>
        </a>
        <div className="header-actions">
          {owner && <span className="shop-name">{owner.workspace_name}</span>}
          <button
            className="icon-button"
            aria-label={dark ? "فعال‌کردن حالت روشن" : "فعال‌کردن حالت تیره"}
            onClick={toggleTheme}
          >
            {dark ? (
              <Sun size={22} aria-hidden="true" />
            ) : (
              <Moon size={22} aria-hidden="true" />
            )}
          </button>
          {owner && (
            <button className="logout" disabled={loggingOut} onClick={logout}>
              <SignOut size={20} aria-hidden="true" />
              خروج
            </button>
          )}
        </div>
      </header>
      {owner && !legal && (
        <nav className="main-nav" aria-label="ناوبری اصلی">
          {links.map(([href, label, Icon]) => (
            <a
              key={href}
              href={href}
              aria-current={path === href ? "page" : undefined}
            >
              <Icon aria-hidden="true" size={21} />
              {label}
            </a>
          ))}
        </nav>
      )}
      <main
        id="main"
        tabIndex={-1}
        className={`content ${(!owner || authLink) && !legal ? "auth-content" : ""}`}
      >
        <ErrorNotice error={error} />
        {loading ? (
          <p className="loading" role="status">
            در حال آماده‌سازی…
          </p>
        ) : legal ? (
          <Legal
            kind={path.slice(1) as "privacy" | "terms" | "cookies" | "guide"}
            meta={meta}
          />
        ) : !meta?.configured ? (
          <section className="panel setup-state">
            <h1>سرویس در انتظار راه‌اندازی است</h1>
            <p>
              اتصال دیتابیس و کلید امن باید توسط ارائه‌دهنده تنظیم شوند. هیچ
              اطلاعات حسابی در این وضعیت دریافت نمی‌شود.
            </p>
            <button onClick={boot}>
              <ArrowClockwise size={20} aria-hidden="true" />
              بررسی دوباره
            </button>
          </section>
        ) : !owner || authLink ? (
          <Auth meta={meta} onSession={acceptSession} />
        ) : path === "/sources" ? (
          <Sources />
        ) : path === "/settings" ? (
          <SettingsPage />
        ) : path === "/account" ? (
          <AccountPage
            owner={owner}
            onSession={acceptSession}
            onDeleted={boot}
          />
        ) : path === "/" ? (
          <Dashboard />
        ) : (
          <section className="panel">
            <h1>صفحه پیدا نشد</h1>
            <a href="/">بازگشت به انبار</a>
          </section>
        )}
      </main>
      <footer>
        <span>© ۲۰۲۶ مجموعهٔ دستیار. همهٔ حقوق محفوظ است.</span>
        <nav aria-label="قوانین و راهنما">
          <a href="/privacy">حریم خصوصی</a>
          <a href="/cookies">کوکی‌ها</a>
          <a href="/terms">شرایط استفاده</a>
          <a href="/guide">راهنما</a>
        </nav>
      </footer>
    </>
  );
}
