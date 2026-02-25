"""
Views للحسابات
"""
from rest_framework import status, generics, viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import login, logout
from django.utils import timezone
from datetime import timedelta
import secrets
from .models import User, Profile, EmailVerification, PasswordReset, LoginHistory
from .serializers import (
    UserSerializer, RegisterSerializer, LoginSerializer,
    ChangePasswordSerializer, PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer, UpdateProfileSerializer,
    LoginHistorySerializer
)
from .tasks import send_verification_email, send_password_reset_email


def get_tokens_for_user(user):
    """الحصول على JWT tokens للمستخدم"""
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


def get_client_ip(request):
    """الحصول على IP المستخدم"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    """
    تسجيل مستخدم جديد
    """
    serializer = RegisterSerializer(data=request.data)
    
    if serializer.is_valid():
        user = serializer.save()
        
        # إرسال إيميل التوثيق
        send_verification_email.delay(user.id)
        
        # تسجيل الدخول تلقائياً
        tokens = get_tokens_for_user(user)
        
        # حفظ سجل تسجيل الدخول
        LoginHistory.objects.create(
            user=user,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            is_successful=True
        )
        
        return Response({
            'message': 'تم التسجيل بنجاح',
            'user': UserSerializer(user).data,
            'tokens': tokens
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    تسجيل الدخول
    """
    serializer = LoginSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        user = serializer.validated_data['user']
        
        # تحديث آخر تسجيل دخول
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
        
        # الحصول على التوكنز
        tokens = get_tokens_for_user(user)
        
        # حفظ سجل تسجيل الدخول
        LoginHistory.objects.create(
            user=user,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            is_successful=True
        )
        
        return Response({
            'message': 'تم تسجيل الدخول بنجاح',
            'user': UserSerializer(user).data,
            'tokens': tokens
        }, status=status.HTTP_200_OK)
    
    # حفظ محاولة فاشلة
    email = request.data.get('email')
    if email:
        try:
            user = User.objects.get(email=email)
            LoginHistory.objects.create(
                user=user,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                is_successful=False
            )
        except User.DoesNotExist:
            pass
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    تسجيل الخروج
    """
    try:
        refresh_token = request.data.get('refresh')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        
        return Response({
            'message': 'تم تسجيل الخروج بنجاح'
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'error': 'حدث خطأ أثناء تسجيل الخروج'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile_view(request):
    """
    عرض الملف الشخصي للمستخدم الحالي
    """
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_profile_view(request):
    """
    تحديث الملف الشخصي
    """
    serializer = UpdateProfileSerializer(
        request.user,
        data=request.data,
        partial=(request.method == 'PATCH')
    )
    
    if serializer.is_valid():
        serializer.save()
        return Response({
            'message': 'تم تحديث الملف الشخصي بنجاح',
            'user': UserSerializer(request.user).data
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password_view(request):
    """
    تغيير كلمة المرور
    """
    serializer = ChangePasswordSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if serializer.is_valid():
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        # الحصول على توكنز جديدة
        tokens = get_tokens_for_user(user)
        
        return Response({
            'message': 'تم تغيير كلمة المرور بنجاح',
            'tokens': tokens
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_request_view(request):
    """
    طلب إعادة تعيين كلمة المرور
    """
    serializer = PasswordResetRequestSerializer(data=request.data)
    
    if serializer.is_valid():
        email = serializer.validated_data['email']
        user = User.objects.get(email=email)
        
        # إنشاء رمز إعادة التعيين
        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(hours=24)
        
        PasswordReset.objects.create(
            user=user,
            token=token,
            expires_at=expires_at
        )
        
        # إرسال إيميل
        send_password_reset_email.delay(user.id, token)
        
        return Response({
            'message': 'تم إرسال رابط إعادة تعيين كلمة المرور إلى بريدك الإلكتروني'
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_confirm_view(request):
    """
    تأكيد إعادة تعيين كلمة المرور
    """
    serializer = PasswordResetConfirmSerializer(data=request.data)
    
    if serializer.is_valid():
        token = serializer.validated_data['token']
        
        try:
            reset = PasswordReset.objects.get(token=token)
            
            if not reset.is_valid():
                return Response({
                    'error': 'هذا الرابط منتهي الصلاحية أو مستخدم'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # تحديث كلمة المرور
            user = reset.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            
            # تحديث حالة الرمز
            reset.is_used = True
            reset.save()
            
            return Response({
                'message': 'تم إعادة تعيين كلمة المرور بنجاح'
            }, status=status.HTTP_200_OK)
        
        except PasswordReset.DoesNotExist:
            return Response({
                'error': 'رمز غير صالح'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_email_view(request):
    """
    توثيق البريد الإلكتروني
    """
    token = request.data.get('token')
    
    if not token:
        return Response({
            'error': 'يجب إدخال الرمز'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        verification = EmailVerification.objects.get(token=token)
        
        if not verification.is_valid():
            return Response({
                'error': 'هذا الرمز منتهي الصلاحية أو مستخدم'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # توثيق البريد
        user = verification.user
        user.is_verified = True
        user.save()
        
        # تحديث حالة الرمز
        verification.is_used = True
        verification.save()
        
        return Response({
            'message': 'تم توثيق البريد الإلكتروني بنجاح'
        }, status=status.HTTP_200_OK)
    
    except EmailVerification.DoesNotExist:
        return Response({
            'error': 'رمز غير صالح'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def login_history_view(request):
    """
    عرض سجل تسجيلات الدخول
    """
    history = LoginHistory.objects.filter(user=request.user)[:20]
    serializer = LoginHistorySerializer(history, many=True)
    return Response(serializer.data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_account_view(request):
    """
    حذف الحساب
    """
    password = request.data.get('password')
    
    if not password:
        return Response({
            'error': 'يجب إدخال كلمة المرور للتأكيد'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if not request.user.check_password(password):
        return Response({
            'error': 'كلمة المرور غير صحيحة'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # حذف الحساب
    user = request.user
    user.is_active = False
    user.save()
    
    # يمكن جدولة حذف نهائي بعد 30 يوم
    
    return Response({
        'message': 'تم تعطيل الحساب بنجاح'
    }, status=status.HTTP_200_OK)
