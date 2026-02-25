"""
أمر Django لإنشاء بيانات تجريبية
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'إنشاء بيانات تجريبية للتطوير'

    def add_arguments(self, parser):
        parser.add_argument(
            '--users',
            type=int,
            default=10,
            help='عدد المستخدمين (افتراضي: 10)',
        )

    def handle(self, *args, **options):
        count = options['users']
        
        self.stdout.write('جاري إنشاء بيانات تجريبية...')
        
        # إنشاء مستخدمين
        created_count = 0
        for i in range(count):
            username = f'user{i+1}'
            email = f'user{i+1}@test.com'
            
            if not User.objects.filter(username=username).exists():
                User.objects.create_user(
                    username=username,
                    email=email,
                    password='pass123',
                    role='student'
                )
                created_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'تم إنشاء {created_count} مستخدم بنجاح')
        )
