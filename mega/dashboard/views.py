from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from allauth.socialaccount.models import SocialAccount
from .models import fetch_hrdata_employee, fetch_hrdata_teammanagements
from django.contrib.auth import logout  # 한 번에 로그아웃
from django.conf import settings

@login_required
def login_check(request):
    try:
        # 현재 로그인한 사용자의 소셜 계정 정보 가져오기
        social_account = SocialAccount.objects.get(user=request.user, provider='google')
        user_email = social_account.extra_data.get('email')

        # hrdata_employee 테이블에서 이메일 확인
        df_employee = fetch_hrdata_employee()
        employee = df_employee[df_employee['email'] == user_email]

        # 데이터베이스에 이메일이 없는 경우 -> 직원이 아닌 경우
        if employee.empty:
            return render(request, 'dashboard/error.html', {'error_message': '등록되지 않은 직원입니다.'})

        # 직원의 ID 가져오기
        employee_id = employee.iloc[0]['employee_id']

        # hrdata_teammanagements 테이블에서 부서 확인
        df_team_management = fetch_hrdata_teammanagements()
        team_info = df_team_management[df_team_management['employee_id'] == employee_id]

        if team_info.empty:
            # 부서 정보가 없을 경우
            return render(request, 'dashboard/error.html', {'error_message': '부서 정보가 없습니다.'})

        # 인사팀(TEAM01) 권한
        department = team_info.iloc[0].get('team_id')
        if department == 'TEAM01':
            # FullCalendar API 키와 캘린더 ID를 템플릿에 전달
            context = {
                'google_calendar_api_key': settings.GOOGLE_CALENDAR_API_KEY,
                'google_calendar_id': settings.GOOGLE_CALENDAR_ID,
            }
            return render(request, 'dashboard/board_dev.html', context)  # 대시보드 렌더링

        return render(request, 'dashboard/error.html', {'error_message': '권한 없음: 해당 부서가 아닙니다.'})

    except SocialAccount.DoesNotExist:
        # 소셜 계정 정보가 없는 경우
        return render(request, 'dashboard/error.html', {'error_message': '소셜 계정 정보를 찾을 수 없습니다.'})

    except KeyError as e:
        # 키 에러 처리
        return render(request, 'dashboard/error.html', {'error_message': f"필드 누락: {str(e)}"})

    except Exception as e:
        # 기타 예외 처리
        return render(request, 'dashboard/error.html', {'error_message': f"알 수 없는 오류: {str(e)}"})

@login_required
def board_dev(request):
    return render(request, 'dashboard/board_dev.html')

@login_required
def board_hr(request):
    return render(request, 'dashboard/board_hr.html')

@login_required
def board_accounting(request):
    return render(request, 'dashboard/board_accounting.html')

@login_required
def board_marketing(request):
    return render(request, 'dashboard/board_marketing.html')

@login_required
def board_sales(request):
    return render(request, 'dashboard/board_sales.html')

@login_required
def board_support(request):
    return render(request, 'dashboard/board_support.html')


def custom_logout(request):
    logout(request)
    return redirect('/')  # 로그인 화면으로 리디렉션
