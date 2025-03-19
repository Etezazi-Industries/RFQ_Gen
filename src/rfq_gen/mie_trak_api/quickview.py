from utils import with_db_conn
from typing import Dict


@with_db_conn()
def get_all_quickviews(cursor) -> Dict[str, str]:
    """
    Fetches all QuickViews.

    Returns a dictionary mapping QuickView primary keys to their descriptions.

    :param cursor: Database cursor.
    :type cursor: pyodbc.Cursor
    :return: Mapping of QuickViewPK to descriptions.
    :rtype: Dict[str, str]
    """
    query = "SELECT QuickViewPK, Description FROM QuickView"
    cursor.execute(query)
    results = cursor.fetchall()

    return {
        str(quickview_pk): description
        for quickview_pk, description in results
        if description
    }


@with_db_conn()
def get_user_quick_view(cursor, userpk: int) -> Dict[str, str]:
    """
    Fetches QuickViews assigned to a user.

    Returns a dictionary mapping QuickView primary keys to their descriptions.

    :param cursor: Database cursor.
    :type cursor: pyodbc.Cursor
    :param userpk: User's primary key.
    :type userpk: int
    :return: Mapping of QuickViewPK to descriptions.
    :rtype: Dict[str, str]
    """
    query = """
        SELECT q.QuickViewPK, q.Description
        FROM QuickViewUser qu
        JOIN QuickView q ON qu.QuickViewFK = q.QuickViewPK
        WHERE qu.UserFK = ?;
    """
    cursor.execute(query, (userpk,))
    results = cursor.fetchall()

    return {
        str(quickview_pk): description
        for quickview_pk, description in results
        if description
    }


@with_db_conn(commit=True)
def add_quickview_to_user(cursor, quickview_pk: str, user_fk: int) -> None:
    """
    Adds a QuickView-user relationship if it does not already exist.

    Checks if an entry with the given `quickview_pk` and `user_fk` exists in the
    `QuickViewUser` table. If it exists, returns the existing primary key.
    Otherwise, inserts a new record and returns the generated primary key.

    :param cursor: Database cursor.
    :type cursor: pyodbc.Cursor
    :param quickview_pk: Primary key of the QuickView.
    :type quickview_pk: str
    :param user_fk: Primary key of the user.
    :type user_fk: int
    :return: Primary key of the QuickViewUser record.
    :rtype: int
    """
    query_check = """
        SELECT QuickViewUserPK 
        FROM QuickViewUser 
        WHERE QuickViewFK = ? AND UserFK = ?;
    """
    cursor.execute(query_check, (quickview_pk, user_fk))
    result = cursor.fetchone()

    # TODO: inform the user that this is already added.
    if result:
        return result[0]

    query_insert = """
        INSERT INTO QuickViewUser (QuickViewFK, UserFK) 
        VALUES (?, ?);
    """
    cursor.execute(query_insert, (quickview_pk, user_fk))


@with_db_conn(commit=True)
def delete_quickview_from_user(cursor, userpk: int, quickviewpk: int) -> None:
    """
    Revokes a user's access to a specific QuickView.

    This function removes the association between a user and a QuickView in
    the `QuickViewUser` table, preventing the user from accessing it.

    :param cursor: Database cursor passed by the decorator.
    :type cursor: pyodbc.Cursor
    :param userpk: Primary key of the user whose QuickView access is being revoked.
    :type userpk: int
    :param quickviewpk: Primary key of the QuickView to be removed from the user's access.
    :type quickviewpk: int
    :return: None
    """
    query = "DELETE FROM QuickViewUser WHERE UserFK = ? AND QuickViewFK = ?;"
    cursor.execute(query, (userpk, quickviewpk))
