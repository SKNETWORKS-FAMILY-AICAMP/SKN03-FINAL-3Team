from django.urls import path
from .views import *

urlpatterns = [
    path('', login_check, name='login_check'),
    path('logout/', custom_logout, name='logout'),  # 커스텀 로그아웃 URL
    path('board/dev/', board_dev, name='board_dev'),
    path('board/hr/', board_hr, name='board_hr'),
    path('board/accounting/', board_accounting, name='board_accounting'),
    path('board/marketing/', board_marketing, name='board_marketing'),
    path('board/sales/', board_sales, name='board_sales'),
    path('board/support/', board_support, name='board_support'),
]