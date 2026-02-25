# 🛠️ Core App - دليل الاستخدام

الـ **core** هو app مساعد يحتوي على utilities و helpers مشتركة لكل المشروع.

---

## 📁 محتويات الـ App

```
core/
├── models.py              ← نماذج مجردة (TimeStamped, SoftDelete)
├── validators.py          ← validators للملفات
├── utils.py               ← دوال مساعدة
├── permissions.py         ← صلاحيات مخصصة
├── mixins.py              ← mixins للـ views
├── exceptions.py          ← استثناءات مخصصة
└── management/
    └── commands/          ← أوامر Django مخصصة
        ├── cleanup_media.py
        └── create_test_data.py
```

---

## 🎯 الاستخدامات

### 1️⃣ النماذج المجردة (Abstract Models)

```python
# في أي models.py
from core.models import TimeStampedModel, SoftDeleteModel

class MyModel(TimeStampedModel):
    """
    هيرث created_at و updated_at تلقائياً
    """
    name = models.CharField(max_length=100)

class Article(SoftDeleteModel):
    """
    حذف ناعم - بدل ما تحذف السجل، بس علمه كمحذوف
    """
    title = models.CharField(max_length=200)
    
    def delete(self):
        self.soft_delete()  # حذف ناعم
```

---

### 2️⃣ Validators للملفات

```python
# في serializers.py
from core.validators import validate_image_file, validate_document_file

class ProfileSerializer(serializers.ModelSerializer):
    def validate_avatar(self, value):
        return validate_image_file(value, max_size_mb=2)
    
    def validate_document(self, value):
        return validate_document_file(value, max_size_mb=10)
```

---

### 3️⃣ دوال مساعدة (Utils)

```python
from core.utils import (
    generate_unique_code,
    format_file_size,
    format_duration,
    get_client_ip,
    calculate_percentage
)

# توليد كود فريد
code = generate_unique_code('ORDER', 8)  # ORDER-A3F9K2B1

# تنسيق حجم الملف
size = format_file_size(1536000)  # "1.5 MB"

# تنسيق المدة
duration = format_duration(3665)  # "1h 1m"

# الحصول على IP
ip = get_client_ip(request)

# حساب النسبة
percent = calculate_percentage(75, 100)  # 75.0
```

---

### 4️⃣ صلاحيات مخصصة (Permissions)

```python
from core.permissions import (
    IsOwner,
    IsOwnerOrReadOnly,
    IsAdminOrReadOnly,
    IsVerifiedUser
)

class MyViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsOwner]
    # المستخدم يجب أن يكون مالك العنصر
```

---

### 5️⃣ Mixins للـ Views

```python
from core.mixins import (
    SuccessMessageMixin,
    CacheMixin,
    FilterByUserMixin,
    SoftDeleteMixin
)

class CourseViewSet(CacheMixin, FilterByUserMixin, viewsets.ModelViewSet):
    """
    - كاش تلقائي للـ list (5 دقائق)
    - فلترة تلقائية حسب المستخدم
    """
    cache_timeout = 600  # 10 دقائق
    user_field = 'instructor'  # اسم الحقل
```

---

### 6️⃣ استثناءات مخصصة

```python
from core.exceptions import (
    CustomValidationError,
    ResourceNotFound,
    PermissionDenied,
    AlreadyExists
)

# في views
if not course.is_published:
    raise ResourceNotFound('الكورس غير موجود')

if Enrollment.objects.filter(student=student, course=course).exists():
    raise AlreadyExists('أنت مسجل بالفعل في هذا الكورس')
```

---

### 7️⃣ أوامر Django مخصصة

```bash
# مسح الملفات غير المستخدمة
python manage.py cleanup_media --dry-run

# إنشاء بيانات تجريبية
python manage.py create_test_data --users 20
```

---

## ✅ التثبيت

```cmd
# 1. نسخ مجلد core

# 2. في settings.py
INSTALLED_APPS = [
    'core',  # ← في البداية
    # باقي الـ apps
]

# 3. لا يحتاج migrations (كله abstract models و utilities)
```

---

## 💡 نصائح

1. **استخدم TimeStampedModel** في كل الـ models اللي محتاجة created_at و updated_at
2. **استخدم validators** بدل ما تكرر نفس الكود في كل serializer
3. **استخدم utils** بدل ما تكتب نفس الـ functions في أماكن مختلفة
4. **استخدم Mixins** لإضافة features جاهزة للـ ViewSets
5. **استخدم Custom Exceptions** لرسائل خطأ واضحة وموحدة

---

## 🔗 أمثلة عملية

### مثال 1: Model مع TimeStamped و SoftDelete

```python
from core.models import TimeStampedModel, SoftDeleteModel

class BlogPost(TimeStampedModel, SoftDeleteModel):
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # الآن عندك:
    # - created_at, updated_at (من TimeStampedModel)
    # - is_deleted, deleted_at, soft_delete(), restore() (من SoftDeleteModel)
```

### مثال 2: ViewSet مع Cache و Filtering

```python
from core.mixins import CacheMixin, FilterByUserMixin

class MyCoursesViewSet(CacheMixin, FilterByUserMixin, viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    cache_timeout = 300  # 5 دقائق
    user_field = 'instructor'  # فلترة حسب المدرس
    
    # الآن:
    # - list مع كاش تلقائي
    # - فلترة تلقائية: المدرس يشوف كورساته فقط
```

### مثال 3: استخدام شامل

```python
from core.utils import generate_unique_code, get_client_ip
from core.exceptions import AlreadyExists
from core.permissions import IsOwner

class EnrollmentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsOwner]
    
    @action(detail=False, methods=['post'])
    def enroll(self, request):
        # توليد كود فريد
        code = generate_unique_code('ENR', 10)
        
        # الحصول على IP
        ip = get_client_ip(request)
        
        # التحقق
        if already_enrolled:
            raise AlreadyExists('أنت مسجل بالفعل')
        
        # ... الكود
```

---

**Core App جاهز للاستخدام! 🎉**
