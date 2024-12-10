from django.urls import path
from .views import *

urlpatterns = [
    path('', login_check, name='login_check'),
    path('logout/', custom_logout, name='logout'),  # 커스텀 로그아웃 URL
]