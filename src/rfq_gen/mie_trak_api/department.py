from utils import with_db_conn
from typing import Dict


@with_db_conn()
def get_all_departments(cursor) -> Dict[int, str]:
    """
    Fetches all departments.

    Returns a dictionary mapping department IDs to department names.

    :param cursor: Database cursor.
    :type cursor: pyodbc.Cursor
    :return: Mapping of DepartmentPK to department names.
    :rtype: Dict[int, str]
    """
    query = "SELECT DepartmentPK, Name FROM Department"

    cursor.execute(query)
    departments = cursor.fetchall()

    department_dict = {}
    if departments:
        for x in departments:
            if x[1]:
                department_dict[x[0]] = x[1]

    return department_dict


@with_db_conn()
def get_department_name(cursor, departmentpk: int) -> str:
    """
    Retrieves the name of a department given its primary key.

    :param cursor: A database cursor used to execute the query.
    :param departmentpk: The primary key of the department.
    :return: The name of the department.
    :raises ValueError: If no department with the given primary key is found.
    """
    query = "SELECT Name FROM Department WHERE DepartmentPK = ?"

    cursor.execute(query, (departmentpk,))
    result = cursor.fetchone()

    if not result:
        raise ValueError("Database did not return any value")

    return result[0]


@with_db_conn()
def get_users_in_department(cursor, departmentpk: int) -> Dict[int, tuple[str, str]]:
    query_users = (
        "SELECT UserPK, FirstName, LastName FROM [User] WHERE DepartmentFK = ?"
    )
    cursor.execute(query_users, (departmentpk,))
    department_users = cursor.fetchall()

    return {
        userpk: (firstname, lastname)
        for userpk, firstname, lastname in department_users
    }
