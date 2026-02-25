"""
Serializers لتطبيق الطلاب
"""
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Student


class UserSerializer(serializers.ModelSerializer):
    """Serializer للمستخدم"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id']


class StudentSerializer(serializers.ModelSerializer):
    """Serializer للطالب"""
    user = UserSerializer(read_only=True)
    full_name = serializers.CharField(source='full_name', read_only=True)
    email = serializers.EmailField(source='email', read_only=True)
    
    class Meta:
        model = Student
        fields = [
            'id', 
            'user', 
            'full_name', 
            'email',
            'phone', 
            'birth_date', 
            'avatar', 
            'bio', 
            'is_active', 
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class StudentCreateSerializer(serializers.ModelSerializer):
    """Serializer لإنشاء طالب جديد"""
    username = serializers.CharField(write_only=True)
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    first_name = serializers.CharField(write_only=True, required=False)
    last_name = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = Student
        fields = [
            'username', 
            'email', 
            'password', 
            'first_name', 
            'last_name',
            'phone', 
            'birth_date', 
            'avatar', 
            'bio'
        ]
    
    def create(self, validated_data):
        # استخراج بيانات المستخدم
        username = validated_data.pop('username')
        email = validated_data.pop('email')
        password = validated_data.pop('password')
        first_name = validated_data.pop('first_name', '')
        last_name = validated_data.pop('last_name', '')
        
        # إنشاء المستخدم
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        
        # إنشاء الطالب
        student = Student.objects.create(user=user, **validated_data)
        return student


class StudentUpdateSerializer(serializers.ModelSerializer):
    """Serializer لتحديث بيانات الطالب"""
    class Meta:
        model = Student
        fields = ['phone', 'birth_date', 'avatar', 'bio']
