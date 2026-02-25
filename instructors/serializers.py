"""
Serializers للمدربين
"""
from rest_framework import serializers
from .models import Instructor


class InstructorSerializer(serializers.ModelSerializer):
    """Serializer للمدرب (عرض عام)"""
    full_name = serializers.CharField(source='full_name', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = Instructor
        fields = [
            'id', 'username', 'full_name', 'email',
            'bio', 'specialization', 'years_of_experience',
            'avatar', 'website', 'linkedin', 'github',
            'total_courses', 'total_students', 'average_rating',
            'is_featured', 'created_at'
        ]
        read_only_fields = [
            'id', 'total_courses', 'total_students',
            'average_rating', 'created_at'
        ]
