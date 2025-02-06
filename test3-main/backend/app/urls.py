from django.urls import path
from . import views

urlpatterns = [
    path('fetch-video/', views.fetch_video_data, name='fetch_video'),  # Fetch video metadata
    path('download-video/', views.download_video, name='download_video'),  # Download video
    path('process_short_form_video/', views.process_short_form_video, name='process_video'),  # Process short-form video
    path('seo/', views.seo, name='seo'),  # SEO endpoint
    path('optimize_shortform/', views.optimize_shortform, name='optimize_shortform'),
    path('check-resolution/', views.check_resolution, name='check-resolution'),  # Check resolution endpoint
    path('fetch-data/', views.fetch_data, name='fetch_data'),
]
