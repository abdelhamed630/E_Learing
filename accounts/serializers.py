"""
Serializers للحسابات
"""
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, Profile, LoginHistory


class ProfileSerializer(serializers.ModelSerializer):
    """Serializer للملف التعريفي"""
    class Meta:
        model = Profile
        fields = [
            'birth_date', 'gender', 'country', 'city', 'address',
            'facebook_url', 'twitter_url', 'linkedin_url', 'website_url',
            'show_email', 'show_phone'
        ]


class UserSerializer(serializers.ModelSerializer):
    """Serializer للمستخدم"""
    profile = ProfileSerializer(read_only=True)
    full_name = serializers.SerializerMethodField()

    def get_full_name(self, obj):
        return obj.full_name
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'full_name', 'phone', 'avatar', 'bio', 'role',
            'is_verified', 'is_active', 'created_at', 'profile'
        ]
        read_only_fields = ['id', 'is_verified', 'created_at', 'role']


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer للتسجيل"""
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password2 = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password2',
            'first_name', 'last_name', 'phone', 'role'
        ]
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({
                "password": "كلمتا المرور غير متطابقتين"
            })
        return attrs
    
    def validate_role(self, value):
        """التحقق من الدور"""
        # فقط الطلاب يمكنهم التسجيل بأنفسهم
        if value not in ['student', 'instructor']:
            raise serializers.ValidationError("دور غير صالح")
        return value
    
    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        
        user = User.objects.create_user(
            password=password,
            **validated_data
        )
        return user


class LoginSerializer(serializers.Serializer):
    """Serializer لتسجيل الدخول"""
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            user = authenticate(
                request=self.context.get('request'),
                email=email,
                password=password
            )
            
            if not user:
                raise serializers.ValidationError(
                    'البريد الإلكتروني أو كلمة المرور غير صحيحة'
                )
            
            if not user.is_active:
                raise serializers.ValidationError(
                    'هذا الحساب غير نشط'
                )
        else:
            raise serializers.ValidationError(
                'يجب إدخال البريد الإلكتروني وكلمة المرور'
            )
        
        attrs['user'] = user
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer لتغيير كلمة المرور"""
    old_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password2 = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("كلمة المرور القديمة غير صحيحة")
        return value
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({
                "new_password": "كلمتا المرور الجديدة غير متطابقتين"
            })
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer لطلب إعادة تعيين كلمة المرور"""
    email = serializers.EmailField(required=True)
    
    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("هذا البريد الإلكتروني غير مسجل")
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer لتأكيد إعادة تعيين كلمة المرور"""
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password2 = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({
                "new_password": "كلمتا المرور غير متطابقتين"
            })
        return attrs


class UpdateProfileSerializer(serializers.ModelSerializer):
    """Serializer لتحديث المستخدم والملف"""
    profile = ProfileSerializer(required=False)
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone', 'avatar', 'bio', 'profile'
        ]
    
    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', None)
        
        # تحديث بيانات المستخدم
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # تحديث بيانات الملف
        if profile_data:
            profile, created = Profile.objects.get_or_create(user=instance)
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()
        
        return instance


class LoginHistorySerializer(serializers.ModelSerializer):
    """Serializer لسجل تسجيل الدخول"""
    class Meta:
        model = LoginHistory
        fields = ['ip_address', 'user_agent', 'location', 'is_successful', 'created_at']
        read_only_fields = ['created_at']
