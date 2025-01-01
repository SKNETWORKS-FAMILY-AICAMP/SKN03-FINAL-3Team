# agent/services/utils.py

from django.conf import settings


def get_connection_params(db_alias="default"):
    """
    Django settings.DATABASES에서 db_alias (기본='default') DB 설정을 읽어,
    MySQL connector에 필요한 파라미터(host, user, password, database, port)를 구성해 반환.
    """
    db_config = settings.DATABASES[db_alias]
    return {
        "host": db_config["HOST"],
        "user": db_config["USER"],
        "password": db_config["PASSWORD"],
        "database": db_config["NAME"],
        "port": int(db_config["PORT"]) if db_config["PORT"] else 3306,
    }
