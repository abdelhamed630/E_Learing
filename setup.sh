#!/bin/bash

# 🚀 E_Learning - تثبيت وضبط المشروع 100%
# يُنفذ في مجلد المشروع الرئيسي

echo "======================================"
echo "🚀 بدء إعداد مشروع E_Learning"
echo "======================================"

# التحقق من وجود Python
if ! command -v python &> /dev/null; then
    echo "❌ Python غير مثبت. يرجى تثبيت Python 3.8+ أولاً"
    exit 1
fi

echo "✅ Python موجود"

# التحقق من Django
if ! python -c "import django" 2>/dev/null; then
    echo "⚠️  Django غير مثبت. جاري التثبيت..."
    pip install Django djangorestframework djangorestframework-simplejwt django-filter django-cors-headers Pillow
fi

echo ""
echo "======================================"
echo "📦 تثبيت المكتبات المطلوبة"
echo "======================================"

# إنشاء requirements.txt إذا لم يكن موجود
cat > requirements.txt << 'EOF'
Django==5.1.5
djangorestframework==3.15.2
djangorestframework-simplejwt==5.4.1
django-filter==24.3
django-cors-headers==4.6.0
Pillow==11.0.0
celery==5.4.0
redis==5.2.1
EOF

pip install -r requirements.txt

echo ""
echo "======================================"
echo "📁 إنشاء المجلدات المطلوبة"
echo "======================================"

mkdir -p media
mkdir -p static
mkdir -p media/avatars
mkdir -p media/students/avatars
mkdir -p media/instructors/avatars
mkdir -p media/categories/icons
mkdir -p media/courses/thumbnails
mkdir -p media/videos/thumbnails
mkdir -p media/videos/attachments
mkdir -p media/exams/questions
mkdir -p media/certificates

echo "✅ تم إنشاء مجلدات Media"

echo ""
echo "======================================"
echo "🗄️  إعداد قاعدة البيانات"
echo "======================================"

# نسخ احتياطية إن وجدت
if [ -f "db.sqlite3" ]; then
    mv db.sqlite3 "db.sqlite3.backup.$(date +%Y%m%d_%H%M%S)"
    echo "✅ تم إنشاء نسخة احتياطية من قاعدة البيانات"
fi

# حذف migrations القديمة
find . -path "*/migrations/0*.py" -not -path "*/venv/*" -delete 2>/dev/null
echo "✅ تم حذف migrations القديمة"

echo ""
echo "======================================"
echo "🔧 إنشاء Migrations"
echo "======================================"

# ترتيب الـ migrations
python manage.py makemigrations accounts
python manage.py makemigrations students  
python manage.py makemigrations instructors
python manage.py makemigrations courses
python manage.py makemigrations enrollments
python manage.py makemigrations exams
python manage.py makemigrations payments
python manage.py makemigrations notifications

echo ""
echo "======================================"
echo "💾 تطبيق Migrations"
echo "======================================"

python manage.py migrate

echo ""
echo "======================================"
echo "👤 إنشاء Superuser"
echo "======================================"

echo "من فضلك أدخل بيانات Superuser:"
python manage.py createsuperuser

echo ""
echo "======================================"
echo "🎨 جمع Static Files"
echo "======================================"

python manage.py collectstatic --noinput

echo ""
echo "======================================"
echo "✅ اكتمل الإعداد بنجاح!"
echo "======================================"

echo ""
echo "📋 الخطوات التالية:"
echo "1️⃣  تشغيل السيرفر:"
echo "   python manage.py runserver"
echo ""
echo "2️⃣  فتح Admin Panel:"
echo "   http://localhost:8000/admin/"
echo ""
echo "3️⃣  اختبار الـ API:"
echo "   POST http://localhost:8000/api/accounts/register/"
echo ""
echo "🎉 المشروع جاهز للعمل!"
