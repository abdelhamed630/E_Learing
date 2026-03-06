from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0002_video_video_file_alter_video_video_url'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='section',
            unique_together=set(),
        ),
    ]
