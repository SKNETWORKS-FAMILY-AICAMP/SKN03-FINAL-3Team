import os
import csv
import zoneinfo
from django.core.management.base import BaseCommand
from agent.models import (
    hrdatabase_hrmastercode,
    hrdatabase_employee,
    hrdatabase_welfarebenefits,
    hrdatabase_welfarebenefits,
    hrdatabase_attendancemanagement,
    hrdatabase_attendancerecord,
    hrdatabase_teammanagement,
)
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


def open_csv_file(filepath):
    """파일을 열고 BOM 제거"""
    with open(filepath, "r", encoding="utf-8-sig") as csvfile:
        reader = csv.DictReader(csvfile)
        # 파일 핸들 유지 필요하므로 리스트로 반환
        return list(reader)


class Command(BaseCommand):
    help = "Import data from CSV files into the database"

    def handle(self, *args, **kwargs):
        base_csv_path = os.getenv("CSV_PATH", "/path/to/csv/")

        # 각 CSV 파일 경로 설정
        file_paths = {
            "common_code": os.path.join(base_csv_path, "공통코드.csv"),
            "hrdatabase_employee": os.path.join(base_csv_path, "직원정보.csv"),
            "welfare_points": os.path.join(base_csv_path, "복지포인트관리.csv"),
            "welfare_benefits": os.path.join(base_csv_path, "복지혜택관리.csv"),
            "attendance_management": os.path.join(base_csv_path, "근태관리.csv"),
            "attendance_record": os.path.join(base_csv_path, "출퇴근기록정보.csv"),
            "team_management": os.path.join(base_csv_path, "팀관리.csv"),
        }

        # 데이터베이스 삽입 함수 호출
        self.import_common_code(file_paths["common_code"])
        self.import_hrdatabase_employee(file_paths["employee"])
        self.import_welfare_points(file_paths["welfare_points"])
        self.import_welfare_benefits(file_paths["welfare_benefits"])
        self.import_attendance_management(file_paths["attendance_management"])
        self.import_attendance_record(file_paths["attendance_record"])
        self.import_team_management(file_paths["team_management"])

    def parse_date(self, date_string):
        if not date_string:
            return None
        try:
            return datetime.strptime(date_string, "%Y-%m-%d").date()
        except ValueError:
            return None

    def parse_datetime(self, datetime_string):
        if not datetime_string:
            return None
        try:
            naive_dt = datetime.strptime(datetime_string, "%Y-%m-%d %H:%M:%S")
            seoul_tz = zoneinfo.ZoneInfo("Asia/Seoul")
            return naive_dt.replace(tzinfo=seoul_tz)
        except ValueError:
            return None

    def import_common_code(self, filepath):
        reader = open_csv_file(filepath)
        for row in reader:
            hrdatabase_hrmastercode.objects.update_or_create(
                code=row["코드"],
                defaults={
                    "parent_code": row["상위코드"] or None,
                    "code_name": row["코드명칭"],
                    "code_description": row["코드 설명"] or None,
                },
            )
        self.stdout.write(self.style.SUCCESS("Imported hrdatabase_hrmastercode data."))

    def import_hrdatabase_employee(self, filepath):
        reader = open_csv_file(filepath)
        for row in reader:
            hrdatabase_employee.objects.update_or_create(
                employee_id=row["employee_id"],
                defaults={
                    "slack_id": row["slack_id"],
                    "name": row["name"],
                    "employee_level": row["employee_level"],
                    "employment_type": row["employment_type"],
                    "email": row["email"],
                    "password": row["password"],
                    "phone_number": row["phone_number"],
                    "address": row["address"],
                    "hire_date": self.parse_date(row["hire_date"]),
                    "tenure": row["tenure"],
                    "age": row["age"],
                    "gender": row["gender"],
                    "reserve_military": row["reserve_military"],
                    "family_info": row["family_info"],
                    "child_info": row["child_info"],
                    "child_age": row["child_age"],
                    "home_ownership": row["home_ownership"],
                },
            )
        self.stdout.write(self.style.SUCCESS("Imported hrdatabase_employee data."))

    def import_welfare_points(self, filepath):
        reader = open_csv_file(filepath)
        for row in reader:
            employee = hrdatabase_employee.objects.get(employee_id=row["employee_id"])
            hrdatabase_welfarebenefits.objects.update_or_create(
                employee=employee,
                point_date=self.parse_date(row["point_date"]),
                defaults={
                    "total_points": row["total_points"],
                    "used_points": row["used_points"],
                    "remaining_points": row["remaining_points"],
                    "expiration_date": self.parse_date(row["expiration_date"]),
                },
            )
        self.stdout.write(self.style.SUCCESS("Imported Welfare Points data."))

    def import_welfare_benefits(self, filepath):
        reader = open_csv_file(filepath)
        for row in reader:
            try:
                employee = hrdatabase_employee.objects.get(employee_id=row["employee_id"])
                hrdatabase_welfarebenefits.objects.update_or_create(
                    employee=employee,
                    defaults={
                        "childcare_used": row["childcare_used"],
                        "childcare_date": self.parse_date(row["childcare_date"]),
                        "company_housing": row["company_housing"],
                        "housing_funding": row["housing_funding"],
                        "student_aid": row["student_aid"],
                        "student_loan": row["student_loan"],
                    },
                )
            except hrdatabase_employee.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"hrdatabase_employee not found: {row['employee_id']}")
                )
                continue
        self.stdout.write(self.style.SUCCESS("Imported Welfare Benefits data."))

    def import_attendance_management(self, filepath):
        reader = open_csv_file(filepath)
        for row in reader:
            employee = hrdatabase_employee.objects.get(employee_id=row["employee_id"])
            hrdatabase_attendancemanagement.objects.update_or_create(
                employee=employee,
                defaults={
                    "total_late_days": row["total_late_days"],
                    "monthly_late_days": row["monthly_late_days"],
                    "monthly_total_late_time": row["monthly_total_late_time"],
                    "average_late_time": row["average_late_time"],
                    "total_absence_days": row["total_absence_days"],
                    "total_annual_leave": row["total_annual_leave"],
                    "remaining_annual_leave": row["remaining_annual_leave"],
                },
            )
        self.stdout.write(self.style.SUCCESS("Imported Attendance Management data."))

    def import_attendance_record(self, filepath):
        reader = open_csv_file(filepath)
        for row in reader:
            try:
                employee = hrdatabase_employee.objects.get(employee_id=row["employee_id"])
                hrdatabase_attendancerecord.objects.update_or_create(
                    record_id=int(row["record_id"]),
                    defaults={
                        "employee": employee,
                        "date": self.parse_date(row["date"]),
                        "scheduled_check_in_date": self.parse_datetime(
                            row["scheduled_check_in_date"]
                        ),
                        "actual_check_in_date": self.parse_datetime(
                            row["actual_check_in_date"]
                        ),
                        "scheduled_check_out_date": self.parse_datetime(
                            row["scheduled_check_out_date"]
                        ),
                        "actual_check_out_date": self.parse_datetime(
                            row["actual_check_out_date"]
                        ),
                        "late_minutes": (
                            int(row["late_minutes"]) if row["late_minutes"] else None
                        ),
                        "is_late": row["is_late"].strip().lower() == "true",
                        "is_absent": row["is_absent"].strip().lower() == "true",
                        "late_or_absent_reason": (
                            row["late_or_absent_reason"].strip()
                            if row["late_or_absent_reason"]
                            else None
                        ),
                    },
                )
            except hrdatabase_employee.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"Employee not found: {row['employee_id']}")
                )
                continue
        self.stdout.write(self.style.SUCCESS("Imported Attendance Record data."))

    def import_team_management(self, filepath):
        reader = open_csv_file(filepath)
        for row in reader:
            try:
                employee = hrdatabase_employee.objects.get(employee_id=row["employee_id"])
                hrdatabase_teammanagement.objects.update_or_create(
                    team_id=row["team_id"],  # team_id 필터 추가
                    employee=employee,  # employee 필터 추가
                    defaults={
                        "department_id": row["department_id"],
                        "team_leader": row["team_leader"].lower() == "true",
                    },
                )
            except hrdatabase_employee.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"Employee not found: {row['employee_id']}")
                )
                continue
        self.stdout.write(self.style.SUCCESS("Imported Team Management data."))
