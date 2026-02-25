# 🐳 دليل Docker - E-Learning

## 📋 الملفات المطلوبة

```
✅ Dockerfile
✅ docker-compose.yml
✅ .env
✅ .dockerignore
✅ requirements.txt
```

---

## 🚀 التشغيل السريع

### 1️⃣ تأكد من وجود Docker

```bash
docker --version
docker-compose --version
```

### 2️⃣ ضع الملفات في مجلد المشروع

```
E_Learing/src/
├── Dockerfile
├── docker-compose.yml
├── .env
├── .dockerignore
├── requirements.txt
├── manage.py
└── ... (باقي الملفات)
```

### 3️⃣ شغل المشروع

```bash
# في مجلد src/
docker-compose up -d --build
```

---

## 📦 الـ Services

| Service | الوصف | Port |
|---------|-------|------|
| **db** | PostgreSQL Database | 5432 |
| **redis** | Redis Cache | 6379 |
| **web** | Django App | 8000 |
| **celery** | Background Tasks | - |
| **celery-beat** | Scheduled Tasks | - |

---

## 🎯 أوامر Docker المهمة

### تشغيل المشروع:
```bash
docker-compose up -d --build
```

### إيقاف المشروع:
```bash
docker-compose down
```

### عرض الـ Logs:
```bash
# كل الـ services
docker-compose logs -f

# service معين
docker-compose logs -f web
docker-compose logs -f celery
```

### إعادة بناء الـ Images:
```bash
docker-compose build --no-cache
```

### تنفيذ أوامر داخل الـ container:
```bash
# Migrations
docker-compose exec web python manage.py migrate

# Create Superuser
docker-compose exec web python manage.py createsuperuser

# Collect Static
docker-compose exec web python manage.py collectstatic --noinput

# Shell
docker-compose exec web python manage.py shell
```

### عرض الـ Containers:
```bash
docker-compose ps
```

### حذف كل شيء (Volumes + Containers):
```bash
docker-compose down -v
```

---

## 🔧 الإعداد الأول

بعد تشغيل `docker-compose up`:

```bash
# 1. انتظر حتى يجهز كل شيء (30-60 ثانية)

# 2. تطبيق Migrations
docker-compose exec web python manage.py migrate

# 3. إنشاء Superuser
docker-compose exec web python manage.py createsuperuser

# 4. جمع Static Files
docker-compose exec web python manage.py collectstatic --noinput

# 5. اختبار
curl http://localhost:8000/admin/
```

---

## 🌐 الوصول للتطبيق

```
Admin:     http://localhost:8000/admin/
API:       http://localhost:8000/api/
Database:  localhost:5432
Redis:     localhost:6379
```

---

## 📝 تعديل الإعدادات

### في `.env`:
```env
# غير الـ SECRET_KEY في الإنتاج!
SECRET_KEY=your-secret-key-here

# للإنتاج
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
```

---

## 🐛 استكشاف الأخطاء

### ❌ `no configuration file provided`
```bash
# تأكد من وجود docker-compose.yml
ls -la docker-compose.yml

# تأكد من المسار الصحيح
cd /path/to/E_Learing/src/
```

### ❌ `port already in use`
```bash
# غير الـ Port في docker-compose.yml
ports:
  - "8001:8000"  # بدل 8000
```

### ❌ `database connection failed`
```bash
# انتظر حتى يجهز PostgreSQL
docker-compose logs db

# أعد المحاولة
docker-compose restart web
```

### ❌ `no such table`
```bash
# نفذ migrations
docker-compose exec web python manage.py migrate
```

---

## 🔄 إعادة بناء المشروع

إذا غيرت الكود أو requirements.txt:

```bash
# أوقف كل شيء
docker-compose down

# أعد البناء
docker-compose up -d --build

# طبق Migrations
docker-compose exec web python manage.py migrate
```

---

## 📊 مراقبة الأداء

```bash
# استهلاك الموارد
docker stats

# Disk Usage
docker system df

# تنظيف الملفات غير المستخدمة
docker system prune -a
```

---

## 🚀 للإنتاج

استخدم `docker-compose.production.yml`:

```bash
docker-compose -f docker-compose.production.yml up -d --build
```

يحتوي على:
- ✅ Nginx Reverse Proxy
- ✅ Gunicorn بدل runserver
- ✅ SSL/HTTPS Ready
- ✅ Static Files Serving

---

## 🔐 النسخ الاحتياطي

### Database Backup:
```bash
docker-compose exec db pg_dump -U postgres elearning_db > backup.sql
```

### Database Restore:
```bash
cat backup.sql | docker-compose exec -T db psql -U postgres elearning_db
```

### Media Files:
```bash
docker cp elearning_web:/app/media ./media_backup
```

---

## 📄 ملف docker-compose.yml البسيط

إذا لم تحتج Celery أو Redis:

```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: elearning_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres123
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  web:
    build: .
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    depends_on:
      - db

volumes:
  postgres_data:
```

---

**جاهز للتشغيل! 🐳**
