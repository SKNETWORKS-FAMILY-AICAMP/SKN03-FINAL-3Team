# agent/services/sql_service.py

import logging
import MySQLdb
import re
import sqlparse
import tabulate

from MySQLdb import Error as MySQLError
from difflib import get_close_matches
from typing import Dict, Any, List, Tuple, Optional
from sqlparse.sql import (
    Comparison,
    Identifier,
    IdentifierList,
    Parenthesis,
    Statement,
    TokenList,
    Where,
)
from sqlparse.tokens import DML, Keyword, Punctuation, Whitespace

logger = logging.getLogger("agent")


###############################
# MySQL 에러 코드 (mysqlclient용)
###############################
ER_SYNTAX_ERROR = 1064  # SQL 문법 오류
ER_BAD_FIELD_ERROR = 1054  # Unknown column
ER_NO_SUCH_TABLE = 1146  # Table doesn't exist


def restrict_sql_query_by_access(
    sql_query: str, user_info: Dict[str, Any], access_level: str
) -> str:
    """
    1) 권한별 안내 문구 출력(or logger 사용)
    2) 필요 시 WHERE 절 추가
    3) 권한이 없는 경우 ""(빈 문자열) 리턴 (접근 거부)

    ※ 'DEPARTMENT_ACCESS' 일 때, hrdatabase_employee 테이블을
    hrdatabase_teammanagement 와 JOIN 해서, t.department=? 조건을 거는 예시.
    """
    if access_level == "ALL_ACCESS":
        print("모든 정보에 접근 가능합니다. (WHERE 조건 없음)")
        return sql_query

    elif access_level == "DEPARTMENT_ACCESS":
        print("같은 부서 정보에 한해 접근 가능합니다.")
        department_name = user_info.get("department_name")

        # (A) 만약 기존에 FROM hrdatabase_employee가 있으면 -> JOIN 구문으로 치환
        #     naive(단순) 치환: "FROM hrdatabase_employee" →
        #        "FROM hrdatabase_employee e JOIN hrdatabase_teammanagement t ON e.employee_id = t.employee_id"
        joined_query = sql_query.replace(
            "FROM hrdatabase_employee",
            "FROM hrdatabase_employee e JOIN hrdatabase_teammanagement t ON e.employee_id = t.employee_id",
        )

        # (B) WHERE 절은 "t.department='...'"
        return append_where_condition_sqlparse(
            joined_query, f"t.department='{department_name}'"
        )

    elif access_level == "TEAM_ACCESS":
        print("같은 팀 정보에 한해 접근 가능합니다.")
        team_name = user_info.get("team_name")

        # 팀 정보도 teammanagement에 있다고 가정해,
        # hrdatabase_employee → JOIN hrdatabase_teammanagement
        joined_query = sql_query.replace(
            "FROM hrdatabase_employee",
            "FROM hrdatabase_employee e JOIN hrdatabase_teammanagement t ON e.employee_id = t.employee_id",
        )

        return append_where_condition_sqlparse(joined_query, f"t.team_id='{team_name}'")

    elif access_level == "SELF_ONLY":
        print("본인 정보만 접근 가능합니다.")
        employee_id = user_info.get("employee_id", 0)
        return append_where_condition_sqlparse(sql_query, f"employee_id={employee_id}")

    else:
        print("접근 권한이 없습니다.")
        return ""


def append_where_condition_sqlparse(query: str, condition: str) -> str:
    """
    sqlparse를 사용해, 멀티 스테이트먼트, CTE, SubQuery 등을 다소 고려한
    WHERE 절 추가 로직 예시.

    - 멀티 스테이트먼트: ';'로 구분된 여러 쿼리를 각각 처리
    - CTE (WITH ... AS ...): 우선 CTE 부분은 건드리지 않고, 메인 쿼리에 WHERE 추가
    - SubQuery: 재귀적으로 찾아내서 WHERE 추가 가능 (샘플로 간단 예시만 처리)
    - 이미 WHERE가 있으면 'AND <condition>' 삽입
    - WHERE가 없으면 적절한 위치(GROUP/ORDER/HAVING/LIMIT 앞, 혹은 끝)에 'WHERE <condition>' 삽입

    * 실제로는 훨씬 더 많은 예외 케이스를 고려해야 함.
    """

    statements = sqlparse.parse(query)
    if not statements:
        return query

    new_statements = []
    for stmt in statements:
        # stmt는 sqlparse.sql.Statement
        if _is_select_statement(stmt):
            new_stmt_str = _process_select_statement(stmt, condition)
            new_statements.append(new_stmt_str)
        else:
            # SELECT가 아닌 DML(INSERT, UPDATE, DELETE) or 다른 구문일 수도 있으므로
            # 여기서는 단순히 원본 그대로 추가
            new_statements.append(str(stmt).strip())

    # 여러 스테이트먼트를 '; '로 다시 합침 (마지막은 세미콜론 없이)
    final_sql = "; ".join(s for s in new_statements if s)
    return final_sql.strip() + ";"


def _is_select_statement(stmt: Statement) -> bool:
    """
    stmt(Statement)가 SELECT 구문인지 간단히 판단.
    - 첫 토큰이 SELECT(DML)인지, 혹은 WITH(Keyword)인지 확인.
    - WITH (CTE)로 시작하는 것도 SELECT 류로 취급.
    """
    for token in stmt.tokens:
        if token.ttype == DML and token.value.upper() == "SELECT":
            return True
        if token.ttype == Keyword and token.value.upper() == "WITH":
            # WITH로 시작하면 CTE -> 보통 SELECT
            return True
        if token.is_whitespace:
            continue
        # 첫 번째 유의미한 토큰을 본 뒤, break
        break
    return False


def _process_select_statement(stmt: Statement, condition: str) -> str:
    """
    SELECT 또는 WITH (CTE)로 시작하는 Statement에 대해
    WHERE 절 추가 or 'AND' <condition> 추가.
    """

    # 1) SubQuery(괄호) 안에 있는 SELECT도 재귀적으로 처리
    #    예: SELECT * FROM (SELECT ... FROM table) sub ...
    #    간단 예시: Parenthesis 토큰을 찾으면 재귀 파싱
    _handle_subqueries_recursive(stmt, condition)

    # 2) 이제 메인 레벨의 WHERE 찾기
    where_token = _find_where_token(stmt)
    if where_token:
        # 이미 WHERE가 존재 -> "WHERE <...> AND condition" 식으로 붙이기
        new_where_str = str(where_token).rstrip(" ;") + f" AND {condition}"
        statement_str = str(stmt)
        new_statement_str = statement_str.replace(str(where_token), new_where_str, 1)
        # 포맷팅
        formatted = sqlparse.format(
            new_statement_str, reindent=True, keyword_case="upper"
        )
        return formatted.strip()
    else:
        # WHERE가 없음 -> GROUP/ORDER/HAVING/LIMIT 등 위치 찾아서 삽입
        statement_str = _insert_where_clause(stmt, condition)
        formatted = sqlparse.format(statement_str, reindent=True, keyword_case="upper")
        return formatted.strip()


def _handle_subqueries_recursive(token_list: TokenList, condition: str):
    """
    Parenthesis( ) 안에 SELECT 구문이 있으면, 재귀적으로 _process_select_statement를 적용.
    """
    for idx, token in enumerate(token_list.tokens):
        if isinstance(token, Parenthesis):
            # 괄호 안에 SELECT가 있는지 다시 파싱
            inner_sql = token.value.strip("() \t\n;")
            inner_stmts = sqlparse.parse(inner_sql)
            if not inner_stmts:
                continue
            # 보통 SubQuery는 1개 Statement일 때가 많지만, 여러 개일 수도 있음
            new_stmts = []
            for inner_stmt in inner_stmts:
                if _is_select_statement(inner_stmt):
                    # 재귀 적용
                    processed = _process_select_statement(inner_stmt, condition)
                    new_stmts.append(processed)
                else:
                    # SELECT 아닌 경우는 그대로
                    new_stmts.append(str(inner_stmt))

            # 다시 괄호로 감싼 문자열 만들기
            replaced_sql = f"({'; '.join(new_stmts)})"
            # Token 교체
            token_list.tokens[idx] = sqlparse.sql.Token(token.ttype, replaced_sql)
        elif isinstance(token, TokenList):
            # 토큰 리스트 내부에 또 SubQuery가 있을 수 있으므로 재귀
            _handle_subqueries_recursive(token, condition)


def _find_where_token(stmt: Statement):
    """
    stmt 내부에서 WHERE 토큰(Where 객체)을 찾아 반환
    """
    for token in stmt.tokens:
        if isinstance(token, Where):
            return token
    return None


def _insert_where_clause(stmt: Statement, condition: str) -> str:
    """
    stmt(Statement) 내에 WHERE 구문이 없을 때,
    GROUP BY / ORDER BY / HAVING / LIMIT 등 키워드 앞에 'WHERE condition'을 삽입.
    없으면 문장 끝에 삽입.
    """
    tokens = list(stmt.tokens)
    insert_idx = None

    # (A) GROUP/ORDER/HAVING/LIMIT 등 키워드 앞을 찾아본다
    for i, token in enumerate(tokens):
        # 대소문자 무시하고 Keyword인지 확인
        if token.ttype == Keyword and token.value.upper() in [
            "GROUP",
            "ORDER",
            "HAVING",
            "LIMIT",
        ]:
            insert_idx = i
            break

    statement_str = str(stmt).rstrip("; ")

    if insert_idx is not None:
        # 해당 키워드 바로 앞에 "WHERE <condition>" 삽입
        # 간단하게 문자열 치환으로는 위치 파악이 애매하므로,
        # TokenList 재구성 or string split 등 방법 필요
        # 여기서는 string 기반으로 한번 더 시도 (아직 완벽치 않음)
        target_token_str = str(tokens[insert_idx])
        splitted = statement_str.split(target_token_str, 1)
        if len(splitted) == 2:
            before = splitted[0]
            after = splitted[1]
            new_statement_str = f"{before} WHERE {condition} {target_token_str}{after}"
            return new_statement_str
        else:
            # 못 찾으면 그냥 문장 끝에 붙이기
            return f"{statement_str} WHERE {condition}"
    else:
        # (B) GROUP/ORDER/HAVING/LIMIT 없으므로 문장 끝에 삽입
        return f"{statement_str} WHERE {condition}"


###############################
# 1) DB 스키마 로딩 & 오탈자 탐색
###############################


def load_db_schema(connection_params: dict, db_name: str):
    """
    information_schema에서 테이블/컬럼 목록을 로딩해 (all_tables, all_columns) 튜플로 반환.
    all_tables: [table_name, ...]
    all_columns: [(table_name, column_name), ...]
    """
    conn = MySQLdb.connect(
        host=connection_params["host"],
        user=connection_params["user"],
        passwd=connection_params["password"],
        db=db_name,
        port=connection_params.get("port", 3306),
    )
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = %s
        """,
        (db_name,),
    )
    all_tables = [row[0] for row in cursor.fetchall()]

    cursor.execute(
        """
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE table_schema = %s
        """,
        (db_name,),
    )
    all_columns = cursor.fetchall()

    cursor.close()
    conn.close()
    return all_tables, all_columns


def find_similar_table(table_name: str, tables: List[str], cutoff=0.6) -> Optional[str]:
    """
    테이블명 오탈자 추정: difflib.get_close_matches를 사용
    """
    matches = get_close_matches(table_name, tables, n=1, cutoff=cutoff)
    return matches[0] if matches else None


def find_similar_column(
    column_name: str, columns: List[Tuple[str, str]], cutoff=0.6
) -> Optional[Tuple[str, str]]:
    """
    컬럼명 오탈자 추정: 가장 근접한 컬럼명 + 해당 컬럼이 속한 테이블명을 함께 리턴
    """
    col_names = list(set(col[1] for col in columns))
    matches = get_close_matches(column_name, col_names, n=1, cutoff=cutoff)
    if not matches:
        return None
    matched_col = matches[0]
    # 어느 테이블에 속해 있는지도 찾기
    for tbl, coln in columns:
        if coln == matched_col:
            return (matched_col, tbl)
    return None


###############################
# 2) 자동 수정용 헬퍼
###############################


def extract_unknown_column(error_message: str) -> Optional[str]:
    """
    MySQL 에러 메시지: "Unknown column 'xxx' in 'field list'"
    """
    match = re.search(r"Unknown column '([^']+)'", error_message)
    if match:
        return match.group(1)
    return None


def extract_unknown_table(error_message: str) -> Optional[str]:
    """
    MySQL 에러 메시지: "Table 'my_db.xxx' doesn't exist"
    """
    match = re.search(r"Table '.*?\.(.*?)' doesn't exist", error_message)
    if match:
        return match.group(1)
    return None


def auto_fix_sql_query(
    sql_query: str,
    unknown_table: Optional[str],
    new_table: Optional[str],
    unknown_col: Optional[str],
    new_col: Optional[str],
) -> str:
    """
    매우 단순한 문자열 치환으로 테이블/컬럼명을 자동 교정.
    - 대소문자, alias, 백틱(`테이블명`) 등은 고려하지 않은 데모용
    """
    fixed = sql_query

    if unknown_table and new_table:
        logger.info(f"[auto_fix_sql_query] Table: '{unknown_table}' -> '{new_table}'")
        # \b 경계 정규식 등을 쓸 수도 있음
        pattern_table = rf"\b{re.escape(unknown_table)}\b"
        fixed = re.sub(pattern_table, new_table, fixed)

    if unknown_col and new_col:
        logger.info(f"[auto_fix_sql_query] Column: '{unknown_col}' -> '{new_col}'")
        pattern_col = rf"\b{re.escape(unknown_col)}\b"
        fixed = re.sub(pattern_col, new_col, fixed)

    return fixed


###############################
# 3) SQL 실행 & 에러 처리 + 재시도
###############################


def format_rows_as_markdown_table(rows, cursor) -> str:
    """
    SELECT 결과를 Markdown Table 형태로 변환
    """
    if not rows:
        return "결과가 없습니다."
    col_names = [desc[0] for desc in cursor.description]
    return tabulate.tabulate(rows, headers=col_names, tablefmt="github")


def parse_mysql_error(err_code: int, err_msg: str, sql_query: str) -> str:
    """
    MySQLdb.Error에서 code, msg를 추출하여 메시지 생성
    """
    if err_code == ER_SYNTAX_ERROR:
        return (
            f"SQL 문법 오류입니다.\n" f"오류 메시지: {err_msg}\n" f"쿼리: {sql_query}"
        )
    elif err_code == ER_BAD_FIELD_ERROR:
        return (
            f"존재하지 않는 컬럼으로 인해 오류가 발생했습니다.\n"
            f"오류 메시지: {err_msg}\n"
            f"쿼리: {sql_query}"
        )
    elif err_code == ER_NO_SUCH_TABLE:
        return (
            f"존재하지 않는 테이블로 인해 오류가 발생했습니다.\n"
            f"오류 메시지: {err_msg}\n"
            f"쿼리: {sql_query}"
        )
    else:
        return (
            f"DB 오류(에러코드={err_code})가 발생했습니다.\n"
            f"오류 메시지: {err_msg}\n"
            f"쿼리: {sql_query}"
        )


def run_sql_with_auto_fix(
    sql_query: str,
    connection_params: dict,
    db_tables: List[str],
    db_columns: List[Tuple[str, str]],
    max_retries=1,
) -> str:
    attempts = 0
    current_sql = sql_query

    while attempts <= max_retries:
        try:
            conn = MySQLdb.connect(
                host=connection_params["host"],
                user=connection_params["user"],
                passwd=connection_params["password"],
                db=connection_params["database"],
                port=connection_params.get("port", 3306),
            )
            cursor = conn.cursor()

            cursor.execute(current_sql)

            if current_sql.strip().lower().startswith("select"):
                rows = cursor.fetchall()
                result_str = format_rows_as_markdown_table(rows, cursor)
            else:
                conn.commit()
                result_str = f"쿼리 실행 성공 ({cursor.rowcount} 행 영향을 받았습니다.)"

            cursor.close()
            conn.close()
            return result_str

        except MySQLError as e:
            err_code = e.args[0] if e.args else None
            err_msg = str(e)

            # 오탈자 자동 수정 가능 여부
            if err_code in (ER_NO_SUCH_TABLE, ER_BAD_FIELD_ERROR):
                if attempts < max_retries:
                    unknown_tbl = extract_unknown_table(err_msg)
                    unknown_col = extract_unknown_column(err_msg)

                    new_tbl = (
                        find_similar_table(unknown_tbl, db_tables)
                        if unknown_tbl
                        else None
                    )
                    col_suggestion = None
                    if unknown_col:
                        col_suggestion = find_similar_column(unknown_col, db_columns)
                    new_col = col_suggestion[0] if col_suggestion else None

                    if (unknown_tbl and new_tbl) or (unknown_col and new_col):
                        fixed_sql = auto_fix_sql_query(
                            current_sql,
                            unknown_table=unknown_tbl,
                            new_table=new_tbl,
                            unknown_col=unknown_col,
                            new_col=new_col,
                        )
                        current_sql = fixed_sql
                        attempts += 1
                        continue
                    else:
                        return parse_mysql_error(err_code, err_msg, current_sql)
                else:
                    return parse_mysql_error(err_code, err_msg, current_sql)
            else:
                return parse_mysql_error(err_code, err_msg, current_sql)
        except Exception as ex:
            return f"알 수 없는 오류가 발생했습니다: {str(ex)}"

    return "쿼리 실행 중 알 수 없는 문제가 발생했습니다."
