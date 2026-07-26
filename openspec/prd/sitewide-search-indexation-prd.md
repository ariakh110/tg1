# PRD اجرایی: یکپارچه‌سازی ایندکس، canonical و صفحات فنی سایت

## مسئله

بررسی Search Console و HTML زنده نشان داد صفحات عمومی و عملیاتی سیاست یکسانی برای ایندکس ندارند. برخی صفحات مهم canonical یا متادیتای اختصاصی نداشتند، URLهای فیلتر خانواده با هاب دسته رقابت می‌کردند، مسیرهای خرید و حساب قابل ایندکس بودند و robots.txt جلوی مشاهده noindex را می‌گرفت.

## هدف

- هر صفحه عمومی مهم یک URL canonical روشن، عنوان و توضیح یکتا و HTML اولیه قابل خواندن داشته باشد.
- URLهای تکراری خانواده به صفحه دسته مرتبط تجمیع شوند.
- صفحات تراکنشی و خصوصی وارد نتایج جستجو نشوند.
- sitemap، robots.txt و meta robots با یکدیگر تناقض نداشته باشند.
- هاب دسته‌ها مقصد محتوایی واقعی باشند و فهرست محصول را مستقیم نشان دهند.

## دامنه

### صفحات عمومی

`/`، `/products`، `/categories`، `/blog`، `/barandaz`، `/orders`، `/sale-hall`، `/export`، `/faq`، `/about`، `/contact`، `/privacy` و `/terms` باید self-canonical، title، description، Open Graph و `index,follow` داشته باشند.

### URLهای فیلتر خانواده

شش خانواده اصلی `sheet`، `rebar`، `beam`، `pipe`، `profile` و `billet` و همچنین ریشه‌های فعال taxonomy در `/products?family=...` باید canonical را به `/category/<family>` بدهند. رابط فیلتر فعلاً حفظ می‌شود و 301 تا زمان برابری کامل قابلیت فیلتر هاب دسته به تعویق می‌افتد.

### صفحات غیرقابل ایندکس

- `/products/<id>/buy`: `noindex,follow`
- `/auth/*`، `/account/*`، `/admin/*`، `/cart`، `/checkout`، `/orders/<id>` و `/offers/*`: `noindex,nofollow`
- هیچ‌کدام از مسیرهای بالا در robots.txt مسدود نمی‌شوند؛ فقط `/api/` مسدود می‌ماند.

### هاب دسته محصول

صفحه `/category/<family>` باید محصولات همان خانواده را از API summary دریافت و بدون صفحه‌بندی نمایش دهد. هر ردیف حداقل نام، لینک محصول، گرید یا شهر موجود و قیمت فعال یا وضعیت استعلام را دارد. عبارت‌های محتوای ضعیف مانند «به‌زودی» در این صفحات استفاده نمی‌شود.

### sitemap

فقط URLهای هم‌دامنه، canonical، بدون query و قابل ایندکس وارد sitemap می‌شوند. URLهای تکراری حذف و مسیرهای خصوصی، خرید و حساب کنار گذاشته می‌شوند.

## معیار پذیرش

- HTML اولیه `/products` دارای H1 باشد.
- `/products?family=rebar` canonical برابر `/category/rebar` داشته باشد.
- `/sale-hall` title، description و self-canonical اختصاصی داشته باشد.
- مسیر خرید robots برابر `noindex,follow` و مسیر ورود/حساب برابر `noindex,nofollow` داشته باشد.
- robots.txt مسیرهای noindex را مسدود نکند و لینک sitemap را همیشه اعلام کند.
- sitemap هیچ query، مسیر خصوصی یا URL تکراری نداشته باشد.
- هاب‌های خانواده، محصول واقعی یا اقدام استعلام جاری نشان دهند و placeholder «به‌زودی» نداشته باشند.
- تست سیاست SEO، تست endpoint ربات، Django checks، migration check، build فرانت و اعتبارسنجی strict OpenSpec پاس شوند.

## عملیات پس از استقرار

1. در URL Inspection نمونه‌های `/products?family=rebar`، `/products/32/buy?intent=buy` و `/auth/login` با Live Test بررسی شوند.
2. پس از مشاهده canonical و noindex صحیح، Validate Fix در Search Console اجرا شود.
3. فقط برای صفحات دسته، محصول، مقاله و تالار فروش درخواست ایندکس ثبت شود.
4. لینک‌سازی خارجی فقط به URLهای canonical دسته، محصول، لندینگ و مقاله انجام شود.
