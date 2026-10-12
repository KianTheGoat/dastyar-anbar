import { useRef, type ReactNode } from 'react';

function Article({ title, children }: { title: string; children: ReactNode }) {
  return <article className="article"><h1>{title}</h1>{children}<a href="/">بازگشت به انبار</a></article>;
}

function Privacy() {
  return <Article title="حریم خصوصی و کوکی‌ها">
    <p className="notice">این اطلاعیه مربوط به نسخهٔ پایهٔ پروژه است. دریافت اطلاعات فروشگاه هنوز فعال نیست.</p>
    <h2>اطلاعات در نسخهٔ فعلی</h2>
    <p>این رابط، فرم ثبت‌نام، بارگذاری فایل یا اتصال فعال به گوگل‌شیت ندارد و اطلاعات کالا، سفارش یا مشتری را ذخیره نمی‌کند. هیچ داده‌ای به مدل هوش مصنوعی ارسال نمی‌شود.</p>
    <h2>کوکی‌ها و خدمات جانبی</h2>
    <p>کد این نسخه کوکی، ابزار تبلیغاتی، تحلیل رفتار یا ضبط نشست ایجاد نمی‌کند. فونت از دستگاه شما خوانده می‌شود. نشانی اینترنتی و زمان درخواست ممکن است توسط میزبان ثبت شوند؛ هنگام راه‌اندازی، تنظیمات و مدت نگهداری میزبان باید مشخص شوند.</p>
    <h2>پیش از فعال‌شدن سرویس</h2>
    <p>نام و اطلاعات تماس گرداننده، محل نگهداری داده، خدمات جانبی، زمان حذف و مسیر درخواست دریافت یا حذف اطلاعات باید در همین اطلاعیه منتشر شوند. اطلاعیهٔ کامل باید پیش از دریافت اطلاعات در دسترس باشد.</p>
    <p>دادهٔ موردنیاز محصول، اطلاعات کالا، موجودی و تعداد فروش است. نام، نشانی، شمارهٔ تماس و اطلاعات پرداخت مشتریان برای این کار لازم نیستند.</p>
    <h2>کوکی ورود در نسخهٔ سرویس</h2>
    <p>پس از پیاده‌سازی ورود، کوکی ضروری نشست و مدت اعتبار آن در این صفحه توضیح داده می‌شود. هر ابزار اختیاری باید با انتخاب آگاهانه و امکان رد و لغو فعال شود.</p>
  </Article>;
}

function Terms() {
  return <Article title="شرایط استفاده">
    <p className="notice">این نسخه، پایهٔ توسعهٔ دستیار انبار است و سرویس تجاری فعال محسوب نمی‌شود.</p>
    <h2>کاربرد پیشنهادها</h2>
    <p>اولویت تأمین بر مبنای موجودی ثبت‌شده، تعداد فروش و حدهای دسته‌بندی محاسبه می‌شود. تصمیم نهایی تولید یا خرید با مسئول فروشگاه است؛ فروش آینده تضمین نمی‌شود.</p>
    <h2>درستی اطلاعات</h2>
    <p>زمان و منبع اطلاعات باید کنار گزارش نمایش داده شوند. دادهٔ ناقص یا قدیمی می‌تواند نتیجه را تغییر دهد. واردکننده باید مجاز به استفاده از اطلاعات فروشگاه باشد.</p>
    <h2>راه‌اندازی تجاری</h2>
    <p>هویت ارائه‌دهنده، قیمت و شرایط پرداخت، پشتیبانی، فسخ، حذف حساب و قانون قابل اعمال باید پیش از ثبت‌نام مشتری مشخص و منتشر شوند. این متن، قرارداد کامل سرویس آینده نیست.</p>
  </Article>;
}

function Guide() {
  return <Article title="آماده‌سازی اطلاعات انبار">
    <p className="notice">این راهنما قالب موردنیاز نسخهٔ اول را توضیح می‌دهد. ورود فایل و اتصال گوگل‌شیت در مرحلهٔ توسعهٔ بعد فعال می‌شوند.</p>
    <h2>جدول موجودی</h2>
    <p>هر ردیف یک رنگ و سایز از کالا است: کد ثابت کالا، نام، دسته‌بندی، رنگ، سایز و موجودی قابل فروش. کد کالا را به صورت متن نگه دارید تا صفر ابتدایی آن حذف نشود.</p>
    <h2>جدول فروش</h2>
    <p>کد کالا، تاریخ، تعداد، شناسهٔ سفارش و ردیف، وضعیت و تعداد مرجوعی را آماده کنید. آماده‌سازی، ارسال و تکمیل، وضعیت‌های قابل محاسبه هستند. تغییر وضعیت، فروش تازه محسوب نمی‌شود.</p>
    <h2>حدهای دسته‌بندی</h2>
    <p>برای هر دسته، مرز کمبود و مرز موجودی زیاد تعیین می‌شود. مثلاً برای کفش، ۳ عدد و کمتر کمبود، ۴ عدد مناسب و ۵ عدد و بیشتر موجودی زیاد است.</p>
    <h2>اطلاعات مشتری</h2>
    <p>نام، شمارهٔ تماس، نشانی و اطلاعات پرداخت مشتری را از فایل کنار بگذارید. برای تحلیل موجودی به آن‌ها نیازی نیست.</p>
  </Article>;
}

function Dashboard() {
  const assistant = useRef<HTMLDetailsElement>(null);
  function closeAssistant(restoreFocus = true) {
    if (!assistant.current) return;
    assistant.current.open = false;
    if (restoreFocus) assistant.current.querySelector('summary')?.focus();
  }
  return <>
    <div className="page-heading"><p className="context">نمای موجودی</p><h1>انبارتان را روشن‌تر ببینید.</h1><p>هر رنگ و سایز را بررسی کنید و پرفروش‌های کم‌موجودی را زودتر تأمین کنید.</p></div>
    <p className="notice">نسخهٔ پایه: هنوز اطلاعات فروشگاهی وارد نشده و اتصال منابع فعال نیست.</p>
    <section className="summary" aria-label="خلاصهٔ وضعیت موجودی">
      <div><span className="state low">کمبود</span><strong>بدون داده</strong><p>کمتر یا برابر حد دسته‌بندی</p></div>
      <div><span className="state normal">موجودی مناسب</span><strong>بدون داده</strong><p>بین دو مرز تعیین‌شده</p></div>
      <div><span className="state high">موجودی زیاد</span><strong>بدون داده</strong><p>بیشتر یا برابر حد دسته‌بندی</p></div>
    </section>
    <section className="inventory"><h2>اولویت تأمین</h2><div className="empty-state"><h3>با اطلاعات واقعی شروع کنید</h3><p>پس از ورود موجودی و فروش، رنگ و سایزهای کم‌موجودی به ترتیب تعداد فروش اینجا دیده می‌شوند.</p><a className="button" href="/guide">مشاهدهٔ راهنمای اطلاعات</a></div></section>
    <details ref={assistant} className="assistant" onKeyDown={(event) => {
      if (event.key === 'Escape') closeAssistant();
    }} onBlur={(event) => {
      if (!event.currentTarget.contains(event.relatedTarget)) closeAssistant(false);
    }}><summary>دستیار انبار</summary><div><h2>اولویت چگونه تعیین می‌شود؟</h2><p>ابتدا کالاهای دارای کمبود انتخاب می‌شوند؛ فروش بیشتر اولویت بالاتری دارد. در فروش برابر، موجودی کمتر جلوتر قرار می‌گیرد.</p><p>تا ورود اطلاعات، پیشنهاد محصولی نمایش داده نمی‌شود.</p><button type="button" onClick={() => closeAssistant()}>بستن دستیار</button></div></details>
  </>;
}

export function App() {
  const path = window.location.pathname;
  const content = path === '/' ? <Dashboard /> : path === '/privacy' ? <Privacy />
    : path === '/terms' ? <Terms /> : path === '/guide' ? <Guide />
    : <Article title="صفحه پیدا نشد"><p>از پیوند زیر به نمای انبار برگردید.</p></Article>;
  return <>
    <a className="skip-link" href="#main">رفتن به محتوای اصلی</a>
    <header className="header"><a className="brand" href="/">دستیار انبار</a><nav aria-label="ناوبری اصلی"><a href="/" aria-current={path === '/' ? 'page' : undefined}>نمای انبار</a><a href="/guide" aria-current={path === '/guide' ? 'page' : undefined}>راهنمای اطلاعات</a></nav></header>
    <main id="main" className="content">{content}</main>
    <footer><span>دستیار انبار</span><nav aria-label="قوانین و حریم خصوصی"><a href="/privacy">حریم خصوصی و کوکی‌ها</a><a href="/terms">شرایط استفاده</a></nav></footer>
  </>;
}
