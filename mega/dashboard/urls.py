from django.urls import path
from .views import *

urlpatterns = [
    path('', login_check, name='login_check'),
    path('logout/', custom_logout, name='logout'),  # 커스텀 로그아웃 URL
    path('board/dev/', board_common, {'dept_slug': 'dev'}, name='board_dev'),
    path('board/accounting/', board_common, {'dept_slug': 'accounting'}, name='board_accounting'),
    path('board/marketing/', board_common, {'dept_slug': 'marketing'}, name='board_marketing'),
    path('board/sales/', board_common, {'dept_slug': 'sales'}, name='board_sales'),
    path('board/support/', board_common, {'dept_slug': 'support'}, name='board_support'),
    path('calendar/', board_calendar, name='board_calendar'),
]
