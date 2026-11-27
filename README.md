# Iran Academic Search MCP

یک سرور [MCP](https://modelcontextprotocol.io/) برای جستجوی فراداده و خواندن متن عمومیِ قابل‌مشاهده در چهار پایگاه علمی فارسی:

- پرتال جامع علوم انسانی (Ensani)
- نورمگز (Noormags)
- SID
- مگیران (Magiran)

این پروژه با Python و مرورگر Camoufox اجرا می‌شود. سایت‌ها ممکن است ساختار خود را تغییر دهند یا به حساب کاربری/اشتراک نیاز داشته باشند؛ ابزار خطای هر منبع را جداگانه گزارش می‌کند.

## ابزارهای MCP

- `list_sources`: نام و کلید منابع و محدودیت‌ها.
- `search_academic(topic, sources?, max_results_per_site?)`: جستجوی موضوع در منابع انتخاب‌شده یا هر چهار سایت.
- `read_public_page(url, source?, max_chars?)`: خواندن متن عمومیِ یک صفحه در دامنه‌های مجاز.

خروجی ابزار جستجو برای هر سایت یکی از وضعیت‌های `ok`، `needs_review` یا `error` دارد. `needs_review` یعنی صفحه باز شده، اما نتیجه‌های مقاله با اطمینان شناسایی نشده‌اند؛ در این حالت ابزار وانمود نمی‌کند که جستجو موفق بوده است.

## اجرا در ویندوز با venv موجود Camoufox

PowerShell:

```powershell
cd C:\Users\DESKTOP\Desktop\law_mcp
& 'C:\Programs\comoufox\.venv\Scripts\python.exe' -m pip install -e .
& 'C:\Programs\comoufox\.venv\Scripts\iran-academic-search.exe'
```

فرمان آخر سرور MCP با انتقال استاندارد ورودی/خروجی را اجرا می‌کند؛ آن را در ترمینال جداگانه برای استفاده‌ی تعاملی اجرا نکنید. برنامه‌ی MCP میزبان باید فرمان را اجرا کند.

برای نصب مستقل و قابل‌بازتولید:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

Camoufox باید فایل‌های مرورگر موردنیاز خود را در اولین اجرا داشته باشد. مرورگر در حالت headless اجرا می‌شود.

## تنظیم در Codex

پس از نصب پروژه، این بخش را به فایل پیکربندی MCP کلاینت اضافه کنید (در Codex تنظیم MCP کاربر معمولاً در `~/.codex/config.toml` است):

```toml
[mcp_servers.iran-academic-search]
command = "C:\\Programs\\comoufox\\.venv\\Scripts\\iran-academic-search.exe"
args = []
startup_timeout_sec = 45
tool_timeout_sec = 90
```

اگر فایل اجرایی در دسترس نیست یا پروژه را editable نصب نکرده‌اید، مسیر پایتون venv را مستقیماً اجرا کنید:

```toml
[mcp_servers.iran-academic-search]
command = "C:\\Programs\\comoufox\\.venv\\Scripts\\python.exe"
args = ["-m", "iran_academic_search.server"]
startup_timeout_sec = 45
tool_timeout_sec = 90
```

پس از ذخیره، MCP client را دوباره بارگذاری کنید و ابزارهای `list_sources` و سپس `search_academic` را امتحان کنید.

### ورود اختیاری به مگیران

برای استفاده از نشست حساب مگیران، اعتبارنامه‌ها را در فایل `.env` ریشهٔ پروژه (این فایل در Git نادیده گرفته می‌شود) یا در متغیرهای محیطی `MAGIRAN_USERNAME` و `MAGIRAN_PASSWORD` قرار دهید. سپس کلاینت MCP را دوباره راه‌اندازی و ابزار `magiran_login` را اجرا کنید. نشست تا زمان بسته‌شدن سرور باقی می‌ماند. ورود فقط از فرم رسمی سایت انجام می‌شود و اشتراک پولی، CAPTCHA یا محدودیت دسترسی را دور نمی‌زند.

قالب فایل محلی:

```dotenv
MAGIRAN_USERNAME=your-email@example.com
MAGIRAN_PASSWORD="your-password"
```

## تنظیم در کلاینت‌های دیگر

کلاینت باید یک MCP server محلی با transport نوع `stdio` اجرا کند. فرمان پیشنهادی:

```text
command: C:\Programs\comoufox\.venv\Scripts\iran-academic-search.exe
arguments: (none)
```

یا از `python.exe -m iran_academic_search.server` همراه مسیر Python همان venv استفاده کنید.

## استفاده‌ی مسئولانه و محدودیت‌ها

- صفحات عمومی خوانده می‌شوند؛ نشست مگیران را می‌توان با ابزار `magiran_login` و اعتبارنامهٔ محلی فعال کرد.
- این ابزار CAPTCHA، paywall، سهمیه یا محدودیت ضدربات را دور نمی‌زند.
- متن بازگشتی ممکن است فقط چکیده/فراداده یا پیش‌نمایش باشد. برای استفاده از متن کامل، از لینک و مجوز رسمی خود پایگاه استفاده کنید.
- برای هر صفحه متن محدود و برای هر سایت فاصله‌ی حداقلی بین درخواست‌ها اعمال می‌شود. `IRAN_MCP_NAV_DELAY` (ثانیه، پیش‌فرض `1.2`) و `IRAN_MCP_MAX_TEXT` (نویسه، پیش‌فرض `30000`) قابل تنظیم‌اند.
- محتوای صفحات وب ورودی غیرقابل‌اعتماد است؛ کلاینت هوش مصنوعی باید آن را به‌عنوان داده بخواند، نه دستور.
- پیاده‌سازی فعلی در صورت تغییر فرم جستجو ممکن است `needs_review` بدهد. selectorهای سایت را فقط بر پایه‌ی دسترسی مجاز و با رعایت شرایط استفاده‌ی آن به‌روز کنید.
- URLهای ابزار خواندن به دامنه‌های چهار پایگاه محدودند؛ انتقال به دامنه‌ی بیرونی پذیرفته نمی‌شود.

## توسعه و انتشار

```powershell
python -m pip install build
python -m build
```

برای انتشار در PyPI، مالک پروژه باید نام بسته را بررسی/رزرو کند، wheel را بسازد و مطابق فرایند رسمی PyPI بارگذاری کند. سپس مخزن Git عمومی را همراه مجوز MIT و راهنمای بالا منتشر کند. سرور محلی `stdio` به‌خودی‌خود یک سرویس میزبانی‌شده یا فهرست‌شده در MCP Registry نیست؛ برای Registry، اطلاعات مالک/مخزن و روش نصب پایدار لازم است.

پروژه با مجوز MIT منتشر می‌شود. متن مجوز در فایل `LICENSE` است.
