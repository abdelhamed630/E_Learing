"""
أمر Django لمسح الملفات غير المستخدمة من media/
"""
from django.core.management.base import BaseCommand
from django.conf import settings
import os


class Command(BaseCommand):
    help = 'مسح الملفات غير المستخدمة من مجلد media'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='عرض الملفات التي سيتم حذفها بدون حذفها فعلياً',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('وضع التجربة: لن يتم حذف أي ملفات'))
        
        media_root = settings.MEDIA_ROOT
        
        # TODO: منطق الحذف
        # هنا يمكن إضافة منطق للتحقق من الملفات المستخدمة في قاعدة البيانات
        # ومقارنتها مع الملفات الموجودة في media/
        
        self.stdout.write(
            self.style.SUCCESS('تم الانتهاء من فحص الملفات')
        )
