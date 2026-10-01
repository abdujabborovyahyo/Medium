# MediumClone

Django asosidagi Medium'ga o'xshash blog platformasi: maqolalar (Quill editor), izohlar,
like/bookmark, o'qish ro'yxatlari, obuna (follow), bildirishnomalar va statistika.

## Talablar

- Python **3.12+** (Django 6.0 shuni talab qiladi)
- (ixtiyoriy) PostgreSQL — production uchun tavsiya etiladi

## Lokal ishga tushirish

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

cp .env.example .env               # Windows: copy .env.example .env
# .env ichida DJANGO_DEBUG=True bo'lishi kifoya

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Testlar:

```bash
python manage.py test
```

## Sozlamalar (environment variables)

Barcha sozlamalar `config/settings.py` da `django-environ` orqali o'qiladi.
To'liq ro'yxat — `.env.example` faylida.

| O'zgaruvchi | Vazifasi | Default |
|---|---|---|
| `DJANGO_DEBUG` | Debug rejimi | `False` |
| `DJANGO_SECRET_KEY` | Maxfiy kalit (production'da **majburiy**) | — |
| `DJANGO_ALLOWED_HOSTS` | Domenlar, vergul bilan | debug'da `localhost,127.0.0.1` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://domen.uz` ko'rinishida | bo'sh |
| `DATABASE_URL` | `sqlite:///...` yoki `postgres://...` | `db.sqlite3` |
| `DJANGO_SERVE_MEDIA` | Yuklangan fayllarni Django o'zi bersinmi | debug'da `True` |
| `DJANGO_USE_HTTPS` | HTTPS redirect, secure cookie, HSTS | `True` |

Yangi `SECRET_KEY` yaratish:

```bash
python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
```

## Deploy

Static fayllarni **WhiteNoise** beradi, ilovani **Gunicorn** ishga tushiradi.

1. Serverda/PaaS'da environment variables'ni o'rnating (`DJANGO_DEBUG=False`,
   `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, `DATABASE_URL`).
2. Build bosqichi: `./build.sh` (paketlar + `collectstatic` + `migrate`).
3. Start buyrug'i (`Procfile` da ham bor):

   ```bash
   gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
   ```

4. Tekshiruv: `python manage.py check --deploy`.

**Media fayllar** (avatar, cover rasmlar) haqida: kichik loyihada `DJANGO_SERVE_MEDIA=True`
qo'yib, `DJANGO_MEDIA_ROOT` ni doimiy diskka (persistent volume) yo'naltirish mumkin.
Kattaroq trafik uchun nginx yoki S3-ga o'xshash storage (`django-storages`) ishlating.
Ko'p PaaS'larda disk vaqtinchalik — SQLite va media fayllar har deploy'da o'chib ketadi,
shuning uchun production'da PostgreSQL ishlating.

## Loyiha tuzilishi

| Ilova | Vazifasi |
|---|---|
| `accounts` | Foydalanuvchi modeli, ro'yxatdan o'tish, login, profil |
| `articles` | Maqolalar, teglar, HTML tozalash (`sanitizers.py`), media yuklash |
| `comments` | Ichma-ich (threaded) izohlar |
| `interactions` | Like, bookmark, o'qish ro'yxatlari, kutubxona |
| `notifications` | Bildirishnomalar, follow, o'qish tarixi |
| `stats` | Kunlik statistika va grafiklar |
| `core` | Bosh sahifa, umumiy shablonlar |

Frontend kutubxonalari (Quill 1.3.7, Chart.js 4.5.1) `static/vendor/` ichida saqlanadi —
CDN'ga bog'liq emas.
