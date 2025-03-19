from utils import with_db_conn
from typing import Dict


@with_db_conn()
def get_all_dashboards(cursor) -> Dict[str, str]:
    """
    Fetches all dashboards.

    Returns a dictionary mapping Dashboard primary keys to their descriptions.

    :param cursor: Database cursor.
    :type cursor: pyodbc.Cursor
    :return: Mapping of DashboardPK to descriptions.
    :rtype: Dict[str, str]
    """
    query = "SELECT DashboardPK, Description FROM Dashboard;"
    cursor.execute(query)
    results = cursor.fetchall()

    return {
        str(dashboard_pk): description
        for dashboard_pk, description in results
        if description
    }


@with_db_conn()
def get_user_dashboards(cursor, userpk: int) -> Dict[str, str]:
    """
    Fetches dashboards assigned to a user.

    Returns a dictionary mapping Dashboard primary keys to their descriptions.

    :param cursor: Database cursor.
    :type cursor: pyodbc.Cursor
    :param userpk: User's primary key.
    :type userpk: int
    :return: Mapping of DashboardPK to descriptions.
    :rtype: Dict[str, str]
    """
    query = """
        SELECT d.DashboardPK, d.Description
        FROM DashboardUser du
        JOIN Dashboard d ON du.DashboardFK = d.DashboardPK
        WHERE du.UserFK = ?;
    """
    cursor.execute(query, (userpk,))
    results = cursor.fetchall()

    return {
        str(dashboard_pk): description
        for dashboard_pk, description in results
        if description
    }


@with_db_conn(commit=True)
def add_dashboard_to_user(cursor, dashboard_pk: str, user_fk: int) -> None:
    """
    Adds a dashboard-user relationship if it does not already exist.

    Checks if an entry with the given `dashboard_pk` and `user_fk` exists in the
    `DashboardUser` table. If it does, returns the existing primary key.
    Otherwise, inserts a new record and returns the generated primary key.

    :param cursor: Database cursor.
    :type cursor: pyodbc.Cursor
    :param dashboard_pk: Primary key of the dashboard.
    :type dashboard_pk: str
    :param user_fk: Primary key of the user.
    :type user_fk: int
    :return: Primary key of the DashboardUser record.
    :rtype: int
    """
    query_check = """
        SELECT DashboardUserPK 
        FROM DashboardUser 
        WHERE DashboardFK = ? AND UserFK = ?;
    """
    cursor.execute(query_check, (dashboard_pk, user_fk))
    result = cursor.fetchone()

    if result:
        return result[0]  # Return existing primary key if found

    query_insert = """
        INSERT INTO DashboardUser (DashboardFK, UserFK) 
        VALUES (?, ?);
    """
    cursor.execute(query_insert, (dashboard_pk, user_fk))


@with_db_conn(commit=True)
def delete_dashboard_from_user(cursor, userpk: int, dashboardpk: int) -> None:
    """
    Revokes a user's access to a specific dashboard.

    This function removes the association between a user and a dashboard in
    the `DashboardUser` table, effectively revoking the user's access to it.

    :param cursor: Database cursor passed by the decorator.
    :type cursor: pyodbc.Cursor
    :param userpk: Primary key of the user whose access is being revoked.
    :type userpk: int
    :param dashboardpk: Primary key of the dashboard to be removed from the user's access.
    :type dashboardpk: int
    :return: None
    """
    query = "DELETE FROM DashboardUser WHERE UserFK = ? AND DashboardFK = ?;"
    cursor.execute(query, (userpk, dashboardpk))
