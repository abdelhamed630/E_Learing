# 🎓 E-Learning Platform

منصة تعليمية متكاملة مبنية بـ Django و Django REST Framework

---

## ✨ المميزات

### 👥 إدارة المستخدمين
- ✅ تسجيل وتسجيل دخول بـ JWT
- ✅ 3 أدوار: طالب، مدرب، أدمن
- ✅ الطالب يتسجل تلقائياً
- ✅ المدرب يضيفه الأدمن

### 📚 الكورسات
- ✅ إنشاء وإدارة كورسات
- ✅ أقسام وفيديوهات
- ✅ ملفات مرفقة
- ✅ تقييمات ومراجعات

### 📝 التسجيل والتقدم
- ✅ تسجيل في الكورسات
- ✅ تتبع تقدم الفيديو
- ✅ ملاحظات الطالب
- ✅ شهادات إتمام

### 📋 الامتحانات
- ✅ 3 أنواع أسئلة
- ✅ تصحيح تلقائي
- ✅ محاولات متعددة
- ✅ نتائج فورية

### 💳 المدفوعات
- ✅ طرق دفع متعددة
- ✅ كوبونات خصم
- ✅ طلبات استرجاع

### 🔔 الإشعارات
- ✅ إشعارات داخل التطبيق
- ✅ إيميلات
- ✅ إعلانات عامة

---

## 🚀 التثبيت السريع

### Windows:
```cmd
# 1. فك ضغط المشروع
# 2. نفذ:
setup.bat
```

### Linux/Mac:
```bash
# 1. فك ضغط المشروع
# 2. نفذ:
chmod +x setup.sh
./setup.sh
```

### يدوياً:
```bash
# 1. تثبيت المكتبات
pip install -r requirements.txt

# 2. Migrations
python manage.py makemigrations
python manage.py migrate

# 3. إنشاء Superuser
python manage.py createsuperuser

# 4. تشغيل السيرفر
python manage.py runserver
```

---

## 📁 هيكل المشروع

```
E_Learning/
├── E_Learning/          # إعدادات المشروع
├── core/                # utilities مشتركة
├── accounts/            # المستخدمين والمصادقة
├── students/            # الطلاب
├── instructors/         # المدربين
├── courses/             # الكورسات
├── enrollments/         # التسجيل والتقدم
├── exams/               # الامتحانات
├── payments/            # المدفوعات
├── notifications/       # الإشعارات
├── media/               # الملفات المرفوعة
├── static/              # الملفات الثابتة
├── manage.py
├── requirements.txt
└── README.md
```

---

## 🎯 الاستخدام

### تسجيل طالب جديد:
```bash
POST /api/accounts/register/
{
  "username": "ahmed",
  "email": "ahmed@test.com",
  "password": "SecurePass123!",
  "password2": "SecurePass123!",
  "first_name": "أحمد",
  "last_name": "محمد",
  "role": "student"
}

# ✅ النتيجة: User + Profile + Student تلقائياً
```

### تسجيل دخول:
```bash
POST /api/accounts/login/
{
  "email": "ahmed@test.com",
  "password": "SecurePass123!"
}

# النتيجة: Access Token + Refresh Token
```

### التسجيل في كورس:
```bash
POST /api/enrollments/enrollments/enroll/
Headers: Authorization: Bearer {token}
{
  "course_id": 1
}
```

---

## 📡 API Endpoints

### Accounts:
```
POST   /api/accounts/register/
POST   /api/accounts/login/
POST   /api/accounts/logout/
GET    /api/accounts/profile/
PUT    /api/accounts/profile/update/
```

### Courses:
```
GET    /api/courses/courses/
GET    /api/courses/courses/{slug}/
GET    /api/courses/categories/
```

### Enrollments:
```
POST   /api/enrollments/enrollments/enroll/
GET    /api/enrollments/enrollments/
POST   /api/enrollments/progress/update_progress/
```

### Exams:
```
GET    /api/exams/
POST   /api/exams/{id}/start/
POST   /api/exams/attempts/{id}/submit/
GET    /api/exams/attempts/{id}/result/
```

---

## 🔑 Admin Panel

```
URL: http://localhost:8000/admin/
```

### الوصول:
1. استخدم بيانات الـ superuser
2. ستجد جميع الـ apps

### ملاحظات:
- **Students**: Read-Only (لا يمكن الإضافة)
- **Instructors**: يضاف يدوياً من Admin
- **Courses**: كامل الصلاحيات للمدرسين

---

## 🛠️ التطوير

### إضافة بيانات تجريبية:
```bash
python manage.py create_test_data --users 20
```

### جمع Static Files:
```bash
python manage.py collectstatic
```

### تشغيل Tests:
```bash
python manage.py test
```

---

## 📦 المكتبات المستخدمة

- **Django 5.1** - Backend Framework
- **DRF 3.15** - REST API
- **JWT** - Authentication
- **Pillow** - معالجة الصور
- **Celery** - Background Tasks (اختياري)
- **Redis** - Cache (اختياري)

---

## 🔒 الأمان

- ✅ JWT Authentication
- ✅ Password Hashing
- ✅ CORS Protection
- ✅ Input Validation
- ✅ File Type Validation

---

## 📝 ملاحظات مهمة

1. **الطلاب** يتسجلوا تلقائياً عند التسجيل
2. **المدربين** يضيفهم الأدمن من `/admin/`
3. **Media Files** بتتحفظ في `/media/`
4. **DEBUG = True** للتطوير فقط

---

## 🚀 النشر (Production)

```python
# في settings.py:
DEBUG = False
ALLOWED_HOSTS = ['yourdomain.com']

# استخدم PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        ...
    }
}

# استخدم S3/Cloudinary للـ Media Files
```

---

## 📧 الدعم

للمشاكل والاقتراحات:
- GitHub Issues
- Email: support@e-learning.com

---

## 📄 الترخيص

MIT License

---

**تم بناء المشروع بـ ❤️ في مصر 🇪🇬**
