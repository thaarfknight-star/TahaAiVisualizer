# TahaAi Visualizer — نسخه‌ی پایتون

بازنویسی کامل ویژولایزر صوتی با **پایتون + PySide6 (Qt)** — با ۹ حالت نمایش، شخصی‌سازی
گسترده‌تر نسبت به نسخه‌ی وب/الکترون، و پایپ‌لاین آماده برای ساخت فایل اجرایی روی گیت‌هاب.

## امکانات

- **۹ حالت ویژولایزر:** Spectrum، Mirrored Bars، Waveform، Circular، Radial، Particles،
  Dot Matrix، Spiral، Kaleidoscope.
- **منابع صدا:** حالت Demo (بدون نیاز به صدا)، پخش فایل صوتی محلی (mp3/wav/ogg/flac/m4a/aac)،
  و دریافت خروجی صدای سیستم (System audio loopback).
- **شخصی‌سازی کامل:**
  - پالت رنگ آماده + انتخاب‌گر رنگ دلخواه (Color Picker)
  - پس‌زمینه: Solid / Gradient / Transparent / تصویر دلخواه
  - حالت‌های Mirror: None / Vertical / Both
  - Sensitivity، Smoothing، Detail count، Thickness، Opacity، Glow
  - Bass boost، Motion trails، Demo mode
  - نرخ فریم قابل تنظیم (24/30/60/120 FPS)
  - Always on top
  - تم روشن/تیره (Light/Dark)
  - ۶ پریست آماده (Neon، Minimal، Pulse، Ocean، Sunset، Monochrome)
  - ذخیره و بارگذاری تنظیمات به‌صورت فایل JSON
- **رابط کاربری:** منوی کناری قابل بستن با یک دکمه (و دکمه‌ی شناور برای بازکردن دوباره)،
  و حالت Fullscreen واقعی که تمام کادرها/دکمه‌ها را مخفی می‌کند و با کلید **ESC** خارج می‌شود.

## اجرا روی سیستم شما

```bash
python -m venv .venv
source .venv/bin/activate      # ویندوز: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

> **نکته:** قابلیت «System audio» (دریافت مستقیم خروجی صدای سیستم) روی ویندوز با WASAPI
> loopback به بهترین شکل کار می‌کند. کتابخانه `soundcard` روی مک و لینوکس هم کار می‌کند اما
> ممکن است نیاز به تنظیمات اضافه‌ی صوتی (مثلاً PulseAudio monitor) داشته باشد.

## ساخت فایل اجرایی (Build) به‌صورت محلی

```bash
pip install -r requirements-build.txt
pyinstaller build.spec
```

خروجی در پوشه‌ی `dist/` قرار می‌گیرد (`TahaAiVisualizer.exe` روی ویندوز).

## ساخت خودکار روی GitHub

این پروژه یک workflow آماده در مسیر `.github/workflows/build.yml` دارد که:

1. با هر Push یا Pull Request روی برنچ `main`، برنامه را روی ویندوز، مک و لینوکس می‌سازد
   و خروجی را به‌عنوان Artifact آپلود می‌کند.
2. با هر تگ نسخه به شکل `v*` (مثلاً `v1.0.0`)، فایل‌های ساخته‌شده را در قالب یک
   **GitHub Release** جدید منتشر می‌کند.

برای انتشار نسخه‌ی جدید:

```bash
git tag v1.0.0
git push origin v1.0.0
```

## ساختار پروژه

```
tahaai-visualizer-python/
├── main.py                  # نقطه‌ی ورود برنامه
├── app/
│   ├── config.py             # مدل تنظیمات، پالت رنگ، پریست‌ها
│   ├── audio_engine.py       # موتور صدا (Demo / فایل / System audio)
│   ├── visualizer_widget.py  # بوم رسم تمام حالت‌های ویژولایزر
│   ├── sidebar.py            # پنل کناری و تمام کنترل‌های شخصی‌سازی
│   ├── main_window.py        # پنجره‌ی اصلی، Fullscreen، بستن/بازکردن منو
│   └── styles.py             # استایل‌های تیره/روشن (QSS)
├── assets/                   # آیکون برنامه
├── build.spec                # فایل PyInstaller برای ساخت exe
├── requirements.txt
├── requirements-build.txt
└── .github/workflows/build.yml
```

## کلیدهای میان‌بر

| کلید | عملکرد |
|---|---|
| کلیک روی دکمه‌ی ✕ در منو | بستن سایدبار و نمایش تمام‌صفحه‌ی ویژولایزر |
| کلیک روی ☰ شناور | بازکردن دوباره‌ی سایدبار |
| دکمه‌ی Fullscreen | ورود به حالت تمام‌صفحه‌ی واقعی (مخفی‌شدن همه‌ی کادرها) |
| ESC | خروج از حالت Fullscreen |

## مجوز

MIT — به دلخواه استفاده، تغییر و توزیع کنید.
