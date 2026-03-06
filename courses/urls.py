"""
URLs للكورسات
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryViewSet, CourseViewSet, VideoViewSet,
    InstructorCourseViewSet, InstructorContentViewSet,
    get_video_token, stream_video
)

app_name = 'courses'

router = DefaultRouter()
router.register(r'categories',          CategoryViewSet,         basename='category')
router.register(r'courses',             CourseViewSet,           basename='course')
router.register(r'videos',              VideoViewSet,            basename='video')
router.register(r'instructor-courses',  InstructorCourseViewSet, basename='instructor-course')

urlpatterns = [
    path('', include(router.urls)),

    # ─── Sections ───────────────────────────────────────────
    path('instructor-content/<int:course_pk>/sections/',
         InstructorContentViewSet.as_view({'get': 'list_sections'}),
         name='sections-list'),
    path('instructor-content/<int:course_pk>/sections/add/',
         InstructorContentViewSet.as_view({'post': 'add_section'}),
         name='sections-add'),
    path('instructor-content/<int:course_pk>/sections/<int:section_pk>/edit/',
         InstructorContentViewSet.as_view({'patch': 'edit_section'}),
         name='sections-edit'),
    path('instructor-content/<int:course_pk>/sections/<int:section_pk>/delete/',
         InstructorContentViewSet.as_view({'delete': 'delete_section'}),
         name='sections-delete'),
    path('instructor-content/<int:course_pk>/sections/reorder/',
         InstructorContentViewSet.as_view({'post': 'reorder_sections'}),
         name='sections-reorder'),

    # ─── Videos ─────────────────────────────────────────────
    path('instructor-content/<int:course_pk>/videos/',
         InstructorContentViewSet.as_view({'post': 'add_video'}),
         name='videos-add'),
    path('instructor-content/<int:course_pk>/videos/<int:video_pk>/edit/',
         InstructorContentViewSet.as_view({'patch': 'edit_video'}),
         name='videos-edit'),
    path('instructor-content/<int:course_pk>/videos/<int:video_pk>/delete/',
         InstructorContentViewSet.as_view({'delete': 'delete_video'}),
         name='videos-delete'),
    path('instructor-content/<int:course_pk>/videos/reorder/',
         InstructorContentViewSet.as_view({'post': 'reorder_videos'}),
         name='videos-reorder'),

    # ─── Course Actions ──────────────────────────────────────
    path('instructor-content/<int:course_pk>/toggle-publish/',
         InstructorContentViewSet.as_view({'post': 'toggle_publish'}),
         name='course-toggle-publish'),
    path('instructor-content/<int:course_pk>/stats/',
         InstructorContentViewSet.as_view({'get': 'course_stats'}),
         name='course-stats'),
    path('instructor-content/<int:course_pk>/students/',
         InstructorContentViewSet.as_view({'get': 'course_students'}),
         name='course-students'),

    # ─── Video Token ─────────────────────────────────────────
    path('video-token/<int:video_id>/',
         get_video_token,
         name='video-token'),
    path('video-token/<int:video_id>/stream/',
         stream_video,
         name='video-stream'),
]
