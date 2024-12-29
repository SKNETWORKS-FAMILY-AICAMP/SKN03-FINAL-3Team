from django.db import models


# 공통 코드
class CommonCode(models.Model):
    code = models.CharField(max_length=10, primary_key=True)
    parent_code = models.CharField(max_length=10, null=True, blank=True)
    code_name = models.CharField(max_length=100)
    code_description = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.code_name


# 직원 정보
class Employee(models.Model):
    employee_id = models.AutoField(primary_key=True)
    slack_id = models.CharField(max_length=100, null=True, blank=True)  # Slack ID
    name = models.CharField(max_length=100)
    rank = models.CharField(max_length=50, null=True, blank=True)  # 직급
    employment_type = models.CharField(
        max_length=50, null=True, blank=True
    )  # 고용 형태
    email = models.EmailField(null=True, blank=True)
    password = models.CharField(max_length=100, null=True, blank=True)  # 비밀번호
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    hire_date = models.DateField(null=True, blank=True)  # 입사일
    tenure = models.IntegerField(null=True, blank=True)  # 근속 기간
    age = models.IntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10, null=True, blank=True)  # 성별 코드
    reserve_military = models.CharField(
        max_length=10, null=True, blank=True
    )  # 예비군/민방위 코드
    family_info = models.CharField(
        max_length=10, null=True, blank=True
    )  # 결혼 여부 코드
    child_info = models.IntegerField(null=True, blank=True)  # 자녀 수
    child_age = models.JSONField(null=True, blank=True)  # 자녀 나이 (JSON 형식)
    home_ownership = models.CharField(
        max_length=10, null=True, blank=True
    )  # 자택 보유 여부 코드

    def __str__(self):
        return self.name


# 복지 혜택 관리
class WelfareBenefitsManagement(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    childcare_used = models.BooleanField(default=False)
    childcare_date = models.IntegerField(null=True, blank=True)  # 보육시설 이용 기간
    company_housing = models.BooleanField(default=False)  # 기숙사 여부
    housing_funding = models.BooleanField(default=False)  # 주택자금 지원 여부
    student_aid = models.IntegerField(null=True, blank=True)  # 학자금 지원액
    student_loan = models.BooleanField(default=False)  # 학자금 공제 여부

    def __str__(self):
        return f"Welfare for {self.employee.name}"


# 복지 포인트 관리
class WelfarePointsManagement(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    total_points = models.IntegerField(default=0)
    used_points = models.IntegerField(default=0)
    remaining_points = models.IntegerField(default=0)
    point_date = models.DateField(null=True, blank=True)
    expiration_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Points for {self.employee.name}"


# 근태 관리
class AttendanceManagement(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    total_late_days = models.IntegerField(default=0)  # 총 지각 일수
    monthly_late_days = models.IntegerField(default=0)  # 월별 지각 일수
    monthly_total_late_time = models.IntegerField(default=0)  # 월별 지각 시간 합계(분)
    average_late_time = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.0
    )  # 평균 지각 시간(분)
    total_absence_days = models.IntegerField(default=0)  # 결근 일수
    total_annual_leave = models.IntegerField(default=0)  # 총 연차 일수
    remaining_annual_leave = models.IntegerField(default=0)  # 잔여 연차 일수

    def __str__(self):
        return f"Attendance for {self.employee.name}"


# 출퇴근 기록
class AttendanceRecord(models.Model):
    record_id = models.AutoField(primary_key=True)  # INT 타입, Primary Key
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)  # 직원 ID와 연결
    date = models.DateField()  # 근무 날짜
    scheduled_check_in_date = models.DateTimeField(
        null=True, blank=True
    )  # 예정된 출근 일시
    actual_check_in_date = models.DateTimeField(null=True, blank=True)  # 실제 출근 일시
    scheduled_check_out_date = models.DateTimeField(
        null=True, blank=True
    )  # 예정된 퇴근 일시
    actual_check_out_date = models.DateTimeField(
        null=True, blank=True
    )  # 실제 퇴근 일시
    late_minutes = models.IntegerField(null=True, blank=True)  # 지각 시간
    is_late = models.BooleanField(default=False)  # 지각 여부
    is_absent = models.BooleanField(default=False)  # 결근 여부
    late_or_absent_reason = models.CharField(
        max_length=255, null=True, blank=True
    )  # 지각/결근 사유

    def __str__(self):
        return f"{self.record_id} - {self.employee.name} ({self.date})"


class TeamManagement(models.Model):
    team_id = models.CharField(max_length=50)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    department_id = models.CharField(max_length=50, null=True, blank=True)
    team_leader = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["team_id", "employee"], name="unique_team_employee"
            )
        ]
