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
from config.settings import GOOGLE_CALENDAR_API_KEY, GOOGLE_CALENDAR_ID

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


@login_required
def custom_logout(request):
    logout(request)
    return redirect('/')


@login_required
def board_calendar(request):
    return render(request, 'dashboard/calendar.html')


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
    # 1) 주별 통계 (4주) + wpage
    # -----------------------
    wpage = request.GET.get('wpage', '0')
    try:
        wpage = int(wpage)
    except:
        wpage = 0

    today = date.today()
    this_week_monday = get_monday(today)
    this_week_sunday = this_week_monday + timedelta(days=6)

    # wpage만큼 과거/미래로 이동 (4주=28일)
    shift_days = wpage * 28
    end_sunday = this_week_sunday - timedelta(days=shift_days)
    start_monday = end_sunday - timedelta(days=27)  # 4주(28일) 범위 시작

    earliest_monday = start_monday
    latest_sunday   = end_sunday

    # 4주(주단위) 리스트
    week_ranges = []
    curr_monday = earliest_monday
    for i in range(4):
        w_start = curr_monday
        w_end   = w_start + timedelta(days=6)
        week_ranges.append((w_start, w_end))
        curr_monday += timedelta(weeks=1)

    # 주별 데이터 조회
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

        # 해당팀 질문 수
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

    # 이전/다음 버튼
    prev_available = (wpage >= 0)   # 예시 로직
    next_available = (wpage > 0)
    wpage_plus_1  = wpage + 1
    wpage_minus_1 = wpage - 1

    # -----------------------
    # 2) 반려 질문, 직원목록, 키워드
    # -----------------------
    default_year  = today.year
    default_month = today.month

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

    # 현재 달 기준 넘어가면 비활성화
    if (k_next_year > default_year) or (k_next_year == default_year and k_next_month > default_month):
        next_k_disabled = True
    else:
        next_k_disabled = False

    # 직원 목록
    dev_members = (
        hrdatabase_teammanagement.objects
        .filter(team_id__in=team_ids)
        .select_related('employee_id')
    )

    processed_ids = set()
    employee_data = []
    for member in dev_members:
        emp = member.employee_id
        if emp.employee_id in processed_ids:
            continue
        processed_ids.add(emp.employee_id)

        attendance = hrdatabase_attendancemanagement.objects.filter(employee_id=emp).first()
        team_label = TEAM_MAP.get(member.team_id, member.team_id)
        rank_label = RANK_MAP.get(emp.employee_level, emp.employee_level)

        row_data = {
            'employee_id': emp.employee_id,
            'name': emp.employee_name,
            'rank': rank_label,
            'phone_number': emp.phone_number,
            'email': emp.email,
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

    # 서버 사이드 정렬
    sort_col = request.GET.get('sort_col')
    sort_dir = request.GET.get('sort_dir', 'none')

    FIELD_MAP = {
        '7':  'monthly_late_days',
        '8':  'total_late_days',
        '9':  'total_absence_days',
        '10': 'remaining_annual_leave',
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

    # 키워드: Top5, Top10
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

    # Top5
    top5 = counter.most_common(5)
    top5_labels = [x[0] for x in top5]
    top5_values = [x[1] for x in top5]

    # Top10
    top10 = counter.most_common(10)
    top10_labels = [x[0] for x in top10]
    top10_values = [x[1] for x in top10]

    context = {
        # --- 주별 통계(4주) ---
        'labels': weekly_labels,
        'team_questions': weekly_team_questions,
        'other_questions': weekly_other_questions,

        # 주별 통계 버튼
        'prev_available': prev_available,
        'next_available': next_available,
        'wpage_plus_1':  wpage_plus_1,
        'wpage_minus_1': wpage_minus_1,
        'wpage': wpage,

        # 반려 질문
        'rejected_questions': cleaned_rejected,
        'this_year': year,
        'this_month': month,

        # 직원 목록
        'page_obj': page_obj,

        # 키워드 차트 (Top5 & Top10)
        'kyear':  kyear,
        'kmonth': kmonth,
        'keyword_labels_top5':  top5_labels,
        'keyword_values_top5':  top5_values,
        'keyword_labels_top10': top10_labels,
        'keyword_values_top10': top10_values,
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
def board_calendar(request):
    context = {
        'google_calendar_api_key': GOOGLE_CALENDAR_API_KEY,
        'google_calendar_id': GOOGLE_CALENDAR_ID,
    }
    return render(request, 'dashboard/calendar.html', context)

