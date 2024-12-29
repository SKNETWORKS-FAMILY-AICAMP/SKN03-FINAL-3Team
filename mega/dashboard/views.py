import ast
from collections import Counter
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import logout
from django.core.paginator import Paginator
from django.db.models import Count, Q
from datetime import datetime, timedelta, date
import calendar

from .models import (
    hrdatabase_employee,
    hrdatabase_teammanagement,
    hrdatabase_attendancemanagement,
    hrdatabase_chatbotconversations
)

@login_required
def login_check(request):
    try:
        social_account = SocialAccount.objects.filter(
            user=request.user, provider='google'
        ).first()
        if not social_account:
            return render(request, 'dashboard/error.html', {'error_message': '소셜 계정 정보를 찾을 수 없습니다.'})

        user_email = social_account.extra_data.get('email')
        employee = hrdatabase_employee.objects.filter(email=user_email).first()
        if not employee:
            return render(request, 'dashboard/error.html', {'error_message': '등록되지 않은 직원입니다.'})

        team_info = hrdatabase_teammanagement.objects.filter(employee_id=employee)
        if not team_info.exists():
            return render(request, 'dashboard/error.html', {'error_message': '부서 정보가 없습니다.'})

        # 예시: 인사팀(TEAM01)이면 board_dev로
        if team_info.filter(team_id='TEAM01').exists():
            return redirect('board_dev')

        return render(request, 'dashboard/error.html', {'error_message': '권한 없음: 해당 부서가 아닙니다.'})

    except KeyError as e:
        return render(request, 'dashboard/error.html', {'error_message': f"필드 누락: {str(e)}"})
    except Exception as e:
        return render(request, 'dashboard/error.html', {'error_message': f"알 수 없는 오류: {str(e)}"})


TEAM_ID_MAP = {
    'dev':       ["TEAM04","TEAM05","TEAM06"],   
    'marketing': ["TEAM07","TEAM08","TEAM09"],   
    'sales':     ["TEAM10","TEAM11","TEAM12"],   
    'support':   ["TEAM02","TEAM03"],            
    'accounting':["TEAM13","TEAM14","TEAM15"],   
}

TEAM_MAP = {
    "TEAM04": "개발1팀", "TEAM05": "개발2팀", "TEAM06": "개발3팀",
    "TEAM07": "기획팀",  "TEAM08": "전략팀",  "TEAM09": "디지털마케팅팀",
    "TEAM10": "국내영업팀", "TEAM11": "해외영업팀", "TEAM12": "B2B영업팀",
    "TEAM02": "지원팀",   "TEAM03": "후생관리팀",
    "TEAM13": "회계팀",   "TEAM14": "재무기획팀", "TEAM15": "예산관리팀",
}
RANK_MAP = {
    "RANK01": "사원", "RANK02": "주임", "RANK03": "대리",
    "RANK04": "과장", "RANK05": "차장", "RANK06": "부장",
}

def get_monday(d: date) -> date:
    """주어진 날짜 d가 속한 주의 월요일을 반환"""
    while d.weekday() != 0:  # 0=Monday, 6=Sunday
        d -= timedelta(days=1)
    return d

@login_required
def board_common(request, dept_slug):
    # -----------------------
    # 부서 체크
    # -----------------------
    if dept_slug not in TEAM_ID_MAP:
        return render(request, 'dashboard/error.html', {'error_message': '잘못된 부서 slug 입니다.'})
    team_ids = TEAM_ID_MAP[dept_slug]

    # -----------------------
    # 0) 오늘 날짜
    # -----------------------
    now_date = date.today()

    # -----------------------
    # 1) 최근 8주 주별 질문 통계
    # -----------------------
    this_monday = get_monday(now_date)   # 이번 주 월요일
    week_ranges = []
    for i in reversed(range(8)):  # 과거 8주(0..7)를 오래된 순부터
        week_start = this_monday - timedelta(weeks=i)
        week_end   = week_start + timedelta(days=6)  # 월~일
        week_ranges.append((week_start, week_end))

    earliest_monday = week_ranges[0][0]
    latest_sunday   = week_ranges[-1][1]

    # DB에서 범위 내 질문 전부 조회
    all_qs = (
        hrdatabase_chatbotconversations.objects
        .filter(question_date__range=(earliest_monday, latest_sunday))
        .values('question_date', 'team_id__team_id')
    )

    weekly_labels = []
    weekly_team_questions = []
    weekly_other_questions = []

    for (w_start, w_end) in week_ranges:
        label_start = w_start.strftime('%y/%m/%d')
        label_end   = w_end.strftime('%y/%m/%d')
        label = f"{label_start} ~ {label_end}"

        # 개발부(또는 해당 dept_slug) 팀들 질문 수
        team_count = sum(
            1 for q in all_qs
            if w_start <= q['question_date'] <= w_end and q['team_id__team_id'] in team_ids
        )
        # 전체 질문 수
        total_count = sum(
            1 for q in all_qs
            if w_start <= q['question_date'] <= w_end
        )
        other_count = total_count - team_count

        weekly_labels.append(label)
        weekly_team_questions.append(team_count)
        weekly_other_questions.append(other_count)

    # 최신 5주만
    weekly_labels         = weekly_labels[-5:]
    weekly_team_questions = weekly_team_questions[-5:]
    weekly_other_questions= weekly_other_questions[-5:]

    # -----------------------
    # 2) 반려 질문, 직원목록, 키워드
    # -----------------------
    now_date = datetime.now().date()
    default_year  = now_date.year
    default_month = now_date.month

    year  = request.GET.get('year', default_year)
    month = request.GET.get('month', default_month)
    try:
        year  = int(year)
        month = int(month)
        if not (1 <= month <= 12):
            raise ValueError
    except:
        year  = default_year
        month = default_month

    start_of_month = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end_of_month = date(year, month, last_day)

    # 키워드용
    kyear  = request.GET.get('kyear', default_year)
    kmonth = request.GET.get('kmonth', default_month)
    try:
        kyear  = int(kyear)
        kmonth = int(kmonth)
        if not (1 <= kmonth <= 12):
            raise ValueError
    except:
        kyear  = default_year
        kmonth = default_month

    k_start = date(kyear, kmonth, 1)
    k_last_day = calendar.monthrange(kyear, kmonth)[1]
    k_end = date(kyear, kmonth, k_last_day)

    if kmonth == 1:
        k_prev_year  = kyear - 1
        k_prev_month = 12
    else:
        k_prev_year  = kyear
        k_prev_month = kmonth - 1
    if kmonth == 12:
        k_next_year  = kyear + 1
        k_next_month = 1
    else:
        k_next_year  = kyear
        k_next_month = kmonth + 1
    next_k_disabled = False

    # -----------------------
    # 직원 조회 & 중복 제거
    # -----------------------
    dev_members = hrdatabase_teammanagement.objects.filter(team_id__in=team_ids).select_related('employee_id')

    processed_ids = set()  # 이미 추가한 employee_id를 저장
    employee_data = []

    for member in dev_members:
        emp = member.employee_id
        if emp.employee_id in processed_ids:
            # 이미 추가된 직원이면 스킵
            continue
        processed_ids.add(emp.employee_id)

        # 근태 정보
        attendance = hrdatabase_attendancemanagement.objects.filter(employee_id=emp).first()

        # 팀명, 직급명 매핑
        team_label = TEAM_MAP.get(member.team_id, member.team_id)
        rank_label = RANK_MAP.get(emp.employee_level, emp.employee_level)

        row_data = {
            'employee_id': emp.employee_id,
            'name': emp.employee_name,
            'rank': rank_label,
            'phone_number': emp.phone_number,
            'email': emp.email,
            # 첫 번째 팀만 표시 (여러 팀이면 member.team_id가 중복될 수 있음)
            'team_id': team_label,
        }
        if attendance:
            row_data['monthly_late_days']   = attendance.monthly_late_days
            row_data['total_late_days']     = attendance.total_late_days
            row_data['total_absence_days']  = attendance.total_absence_days
            row_data['remaining_annual_leave'] = attendance.remaining_annual_leave
            row_data['total_annual_leave']  = attendance.total_annual_leave
        else:
            row_data['monthly_late_days']   = None
            row_data['total_late_days']     = None
            row_data['total_absence_days']  = None
            row_data['remaining_annual_leave'] = None
            row_data['total_annual_leave']  = None

        employee_data.append(row_data)

    # -----------------------
    # 2-1) 서버 사이드 정렬 로직
    # -----------------------
    sort_col = request.GET.get('sort_col')  # "7", "8", "9", "10" 등
    sort_dir = request.GET.get('sort_dir', 'none')  # "desc", "asc", "none"

    FIELD_MAP = {
        '7':  'monthly_late_days',      # Tardies_Month
        '8':  'total_late_days',        # Tardies
        '9':  'total_absence_days',     # Absences
        '10': 'remaining_annual_leave', # Leave_Left
    }

    if sort_col in FIELD_MAP and sort_dir in ['asc', 'desc']:
        field_name = FIELD_MAP[sort_col]
        employee_data.sort(
            key=lambda x: x[field_name] if x[field_name] is not None else 0,
            reverse=(sort_dir == 'desc')
        )

    # 페이지네이션
    paginator = Paginator(employee_data, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    # 반려 질문 목록
    rejected_qs = (
        hrdatabase_chatbotconversations.objects
        .filter(
            answer="해당 질문은 대답할 수 없습니다.",
            team_id__team_id__in=team_ids,
            question_date__range=(start_of_month, end_of_month)
        )
        .order_by('-question_date')
    )
    cleaned_rejected = []
    for obj in rejected_qs:
        q_text = obj.question.lstrip() if obj.question else ""
        cleaned_rejected.append({
            'conversation_id': obj.conversation_id,
            'question': q_text,
            'question_date': obj.question_date,
        })

    # 키워드 (kyear/kmonth)
    keyword_qs = (
        hrdatabase_chatbotconversations.objects
        .filter(
            team_id__team_id__in=team_ids,
            question_date__range=(k_start, k_end)
        )
        .exclude(keyword__isnull=True)
        .exclude(keyword__exact="")
    )
    all_keywords = []
    for obj in keyword_qs:
        try:
            parsed = ast.literal_eval(obj.keyword)
            if isinstance(parsed, list):
                all_keywords.extend(parsed)
        except:
            pass
    counter = Counter(all_keywords)
    top5 = counter.most_common(5)
    top5_labels = [x[0] for x in top5]
    top5_values = [x[1] for x in top5]

    # -----------------------
    # 컨텍스트 구성 & 렌더
    # -----------------------
    context = {
        # 주별 통계
        'labels': weekly_labels,
        'team_questions': weekly_team_questions,
        'other_questions': weekly_other_questions,

        # 반려 질문
        'rejected_questions': cleaned_rejected,
        'this_year': year,
        'this_month': month,

        # 직원 목록
        'page_obj': page_obj,

        # 키워드 차트
        'kyear':  kyear,
        'kmonth': kmonth,
        'keyword_labels': top5_labels,
        'keyword_values': top5_values,
        'k_prev_year':  k_prev_year,
        'k_prev_month': k_prev_month,
        'k_next_year':  k_next_year,
        'k_next_month': k_next_month,
        'next_k_disabled': next_k_disabled,

        # 정렬 파라미터
        'sort_col': sort_col,
        'sort_dir': sort_dir,
    }
    return render(request, f'dashboard/board_{dept_slug}.html', context)


@login_required
def custom_logout(request):
    logout(request)
    return redirect('/')


@login_required
def board_calendar(request):
    return render(request, 'dashboard/calendar.html')
