from django.db import models
import pymysql
import pandas as pd
import os
from config.settings import get_parameter


class DatabaseConnection:

    # MySQL 데이터베이스 연결 및 데이터 조회 클래스
    def __init__(self):
        self.connection = pymysql.connect(
            host=get_parameter('/mega/oh-db-info/DB_HOST'),
            user=get_parameter('/mega/oh-db-info/DB_USER'),
            password=get_parameter('/mega/oh-db-info/DB_PASSWORD'),
            db=get_parameter('/mega/oh-db-info/DB_NAME'),
            port=int(get_parameter('/mega/oh-db-info/DB_PORT')), 
            charset='utf8'
        )
        self.cursor = self.connection.cursor(pymysql.cursors.DictCursor)

    # 특정 테이블 데이터를 pandas DataFrame으로 반환
    def fetch_table_as_dataframe(self, table_name):
        query = f"SELECT * FROM {table_name}"
        self.cursor.execute(query)
        rows = self.cursor.fetchall()
        return pd.DataFrame(rows)

    # 연결 종료
    def close(self):
        self.cursor.close()
        self.connection.close()


# hrdata_employee 테이블 데이터를 DataFrame으로 반환
def fetch_hrdata_employee():
    db = DatabaseConnection()
    try:
        return db.fetch_table_as_dataframe('hrdata_employee')
    finally:
        db.close()

# hrdata_teammanagements 테이블 데이터를 DataFrame으로 반환
def fetch_hrdata_teammanagements():
    db = DatabaseConnection()
    try:
        return db.fetch_table_as_dataframe('hrdata_teammanagements')
    finally:
        db.close()
