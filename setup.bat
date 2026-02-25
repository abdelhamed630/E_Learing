@echo off
REM E_Learning - تثبيت وضبط المشروع 100%

echo ======================================
echo 🚀 بدء إعداد مشروع E_Learning
echo ======================================

REM التحقق من Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python غير مثبت. يرجى تثبيت Python 3.8+ أولاً
    pause
    exit /b 1
)

echo ✅ Python موجود

echo.
echo ======================================
echo 📦 تثبيت المكتبات المطلوبة
echo ======================================

REM إنشاء requirements.txt
(
echo Django==5.1.5
echo djangorestframework==3.15.2
echo djangorestframework-simplejwt==5.4.1
echo django-filter==24.3
echo django-cors-headers==4.6.0
echo Pillow==11.0.0
echo celery==5.4.0
echo redis==5.2.1
) > requirements.txt

pip install -r requirements.txt

echo.
echo ======================================
echo 📁 إنشاء المجلدات المطلوبة
echo ======================================

mkdir media 2>nul
mkdir static 2>nul
mkdir media\avatars 2>nul
mkdir media\students\avatars 2>nul
mkdir media\instructors\avatars 2>nul
mkdir media\categories\icons 2>nul
mkdir media\courses\thumbnails 2>nul
mkdir media\videos\thumbnails 2>nul
mkdir media\videos\attachments 2>nul
mkdir media\exams\questions 2>nul
mkdir media\certificates 2>nul

echo ✅ تم إنشاء مجلدات Media

echo.
echo ======================================
echo 🗄️ إعداد قاعدة البيانات
echo ======================================

REM نسخة احتياطية
if exist db.sqlite3 (
    move db.sqlite3 db.sqlite3.backup.%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
    echo ✅ تم إنشاء نسخة احتياطية
)

REM حذف migrations القديمة
for /r %%i in (*\migrations\0*.py) do del "%%i" 2>nul
echo ✅ تم حذف migrations القديمة

echo.
echo ======================================
echo 🔧 إنشاء Migrations
echo ======================================

python manage.py makemigrations accounts
python manage.py makemigrations students
python manage.py makemigrations instructors
python manage.py makemigrations courses
python manage.py makemigrations enrollments
python manage.py makemigrations exams
python manage.py makemigrations payments
python manage.py makemigrations notifications

echo.
echo ======================================
echo 💾 تطبيق Migrations
echo ======================================

python manage.py migrate

echo.
echo ======================================
echo 👤 إنشاء Superuser
echo ======================================

python manage.py createsuperuser

echo.
echo ======================================
echo 🎨 جمع Static Files
echo ======================================

python manage.py collectstatic --noinput

echo.
echo ======================================
echo ✅ اكتمل الإعداد بنجاح!
echo ======================================

echo.
echo 📋 الخطوات التالية:
echo 1️⃣ تشغيل السيرفر:
echo    python manage.py runserver
echo.
echo 2️⃣ فتح Admin Panel:
echo    http://localhost:8000/admin/
echo.
echo 3️⃣ اختبار الـ API:
echo    POST http://localhost:8000/api/accounts/register/
echo.
echo 🎉 المشروع جاهز للعمل!

pause
