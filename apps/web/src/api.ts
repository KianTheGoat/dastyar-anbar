export type Owner = {
  email: string;
  workspace_name: string;
  workspace_id: string;
  verified: boolean;
};
export type Session = { csrf_token: string; account: Owner | null };
export type Meta = {
  configured: boolean;
  policy_version: string;
  operator_name: string;
  privacy_contact: string;
  operating_country: string;
  hosting_region: string;
  subprocessors: string;
  backup_retention_days: number;
  verification_required: boolean;
  password_recovery_available: boolean;
  cookie_name: string;
};
export type Category = {
  id: string;
  name: string;
  low_max: number;
  high_min: number;
};
export type Variant = {
  id: string;
  sku: string;
  name: string;
  category: string;
  color: string;
  size: string;
  available: number;
  net_units: number;
  state: "low" | "normal" | "high";
  priority: number | null;
  needs_review: boolean;
  low_max: number;
  high_min: number;
  replenishment: string;
  updated_at: string;
  stale: boolean;
};
export type Report = {
  rows: Variant[];
  total: number;
  page: number;
  counts: Record<"low" | "normal" | "high", number>;
  priorities: number;
  stale_count: number;
  sales_mode: string;
  period_start: string;
  period_end: string;
  data_updated_at: string | null;
  generated_at: string;
};
export type Analytics = {
  counts: Record<"low" | "normal" | "high", number>;
  total_variants: number;
  net_units: number | null;
  has_sales: boolean;
  sales_mode: string;
  period_start: string;
  period_end: string;
  daily: { date: string; units: number }[];
  top_sellers: Pick<Variant, "sku" | "name" | "color" | "size" | "net_units">[];
};
export const messages: Record<string, string> = {
  authentication_required: "نشست شما پایان یافته است. دوباره وارد شوید.",
  invalid_credentials: "ایمیل یا رمز درست نیست، یا ایمیل هنوز تأیید نشده است.",
  invalid_csrf: "صفحه را تازه کنید و دوباره تلاش کنید.",
  invalid_origin: "این درخواست مجاز نیست.",
  rate_limited: "تعداد درخواست‌ها زیاد است. چند دقیقه بعد دوباره تلاش کنید.",
  invalid_mapping:
    "ستون‌های ضروری را انتخاب کنید؛ هر ستون فقط به یک فیلد وصل می‌شود.",
  invalid_file:
    "فایل قابل خواندن نیست. CSV با UTF-8 یا Excel بدون فرمول وارد کنید.",
  csv_or_xlsx_required: "فایل باید CSV یا XLSX باشد.",
  file_too_large: "حداکثر اندازهٔ فایل ۵ مگابایت است.",
  request_too_large: "اندازهٔ درخواست از حد مجاز بیشتر است.",
  formula_not_allowed:
    "فرمول‌ها را به مقدار ثابت تبدیل کنید و فایل را دوباره وارد کنید.",
  unsafe_workbook: "فایل Excel دارای ساختار یا محتوای غیرمجاز است.",
  invalid_headers: "نام ستون‌ها باید مشخص، یکتا و حداکثر ۶۴ ستون باشد.",
  row_limit_or_empty: "فایل باید بین ۱ تا ۱۰٬۰۰۰ ردیف داده داشته باشد.",
  unknown_sku:
    "بعضی کدها در انبار نیستند. ابتدا موجودی همان کدها را وارد کنید.",
  stale_inventory: "زمان این موجودی قدیمی‌تر از اطلاعات فعلی است.",
  invalid_snapshot_time: "زمان موجودی معتبر نیست؛ زمان آینده انتخاب نکنید.",
  preview_expired: "پیش‌نمایش منقضی شده است. فایل را دوباره بررسی کنید.",
  preview_outdated: "اطلاعات یا تنظیمات تغییر کرده‌اند. پیش‌نمایش تازه بسازید.",
  invalid_thresholds: "مرز موجودی زیاد باید بزرگ‌تر از مرز کمبود باشد.",
  invalid_period: "بازه باید مرتب و حداکثر یک سال باشد.",
  sheet_not_provisioned:
    "حساب اختصاصی گوگل‌شیت این فروشگاه هنوز توسط ارائه‌دهنده تنظیم نشده است.",
  sheet_not_connected: "ابتدا اتصال گوگل‌شیت را ثبت کنید.",
  sheet_access_failed:
    "دسترسی به شیت برقرار نشد. اشتراک‌گذاری و محدوده‌ها را بررسی کنید.",
  sheet_credentials_invalid:
    "تنظیمات اتصال گوگل‌شیت نیاز به بررسی ارائه‌دهنده دارد.",
  sheet_connection_changed: "اتصال تغییر کرده است. دوباره شیت را دریافت کنید.",
  sheet_disconnected: "اتصال قطع شده است. این پیش‌نمایش قابل اعمال نیست.",
  invalid_status_mapping:
    "وضعیت‌ها را به یکی از وضعیت‌های شناخته‌شده وصل کنید.",
  invalid_or_expired_link:
    "پیوند معتبر نیست یا منقضی شده است. پیوند تازه درخواست کنید.",
  deletion_confirmation_invalid: "رمز یا عبارت تأیید حذف درست نیست.",
  policy_acceptance_required: "شرایط استفاده و حریم خصوصی فعلی را تأیید کنید.",
  workspace_variant_limit: "حد این نسخه ۱۰٬۰۰۰ رنگ و سایز است.",
  workspace_sale_limit: "حد این نسخه ۱۰۰٬۰۰۰ ردیف سفارش است.",
  not_found: "مورد پیدا نشد.",
  service_not_configured: "سرویس هنوز تنظیم نشده است.",
  data_conflict:
    "اطلاعات هم‌زمان تغییر کرده‌اند. تازه کنید و دوباره تلاش کنید.",
  network_unavailable:
    "ارتباط با سرویس برقرار نشد. اتصال را بررسی کنید و دوباره تلاش کنید.",
  invalid_response: "سرویس موقتاً پاسخ معتبر نداد. دوباره تلاش کنید.",
};
let csrf = "";
export function setSession(value: Session) {
  csrf = value.csrf_token;
}
export class ApiError extends Error {
  constructor(
    public code: string,
    public fields: { field: string; code: string }[] = [],
  ) {
    super(messages[code] || "درخواست انجام نشد. دوباره تلاش کنید.");
  }
}
export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData))
    headers.set("Content-Type", "application/json");
  if (options.method && options.method !== "GET")
    headers.set("X-CSRF-Token", csrf);
  let response: Response;
  try {
    response = await fetch("/api" + path, {
      ...options,
      headers,
      credentials: "same-origin",
    });
  } catch (error) {
    if (options.signal?.aborted) throw error;
    throw new ApiError("network_unavailable");
  }
  let data;
  try {
    data = await response.json();
  } catch {
    throw new ApiError(
      response.status >= 500 ? "network_unavailable" : "invalid_response",
    );
  }
  if (!response.ok) {
    if (data.detail === "authentication_required")
      window.dispatchEvent(new Event("session-expired"));
    throw new ApiError(
      typeof data.detail === "string" ? data.detail : "request_failed",
      data.errors || [],
    );
  }
  return data as T;
}
export const json = (value: unknown) => JSON.stringify(value);
export const number = (value: number) =>
  new Intl.NumberFormat("fa-IR").format(value);
export function dateText(value: string | null) {
  if (!value) return "هنوز دریافت نشده";
  return new Intl.DateTimeFormat("fa-IR", {
    dateStyle: "medium",
    ...(value.length > 10 ? { timeStyle: "short" as const } : {}),
    timeZone: "Asia/Tehran",
  }).format(new Date(value.length === 10 ? value + "T12:00:00Z" : value));
}
export function localToday() {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Tehran" }).format(
    new Date(),
  );
}
