from utils import with_db_conn
from typing import Dict, List


@with_db_conn()
def get_user_data(cursor, enabled: bool = True) -> Dict[int, List[str]]:
    """
    Retrieves user data filtered by enabled status.

    Returns a dictionary mapping user IDs to their first and last names.

    :param cursor: Database cursor.
    :type cursor: pyodbc.Cursor
    :param enabled: Whether to fetch only enabled users.
    :type enabled: bool
    :return: Mapping of UserPK to [FirstName, LastName].
    :rtype: Dict[int, List[str]]
    :raises ValueError: If no users are found.
    """
    query = "SELECT UserPK, FirstName, LastName FROM [User] WHERE Enabled=?"

    user_dict = {}
    cursor.execute(query, (1 if enabled else 0,))
    users = cursor.fetchall()

    if not users:
        raise ValueError("Mie Trak did not return any values. Check last query.")

    for x in users:
        if x:
            user_dict[x[0]] = [x[1], x[2]]

    return user_dict


@with_db_conn()
def get_user_first_last(cursor, userpk: int) -> List[str]:
    """
    Retrieves the first and last name of a user given their primary key.

    :param cursor: A database cursor used to execute the query.
    :param userpk: The primary key of the user.
    :return: A list containing the user's first name and last name.
    :raises ValueError: If no user with the given primary key is found.
    """
    query = "SELECT FirstName, LastName FROM [User] WHERE UserPK = ?"
    cursor.execute(query, (userpk,))
    result = cursor.fetchone()

    if not result:
        raise ValueError("Database did not return any value")

    return [result[0], result[1]]


@with_db_conn()
def login_user(cursor, username: str, password: str) -> bool:
    query = "SELECT Code, Password FROM [User] WHERE Code = ?"
    cursor.execute(query, (username,))
    results = cursor.fetchall()

    if not results:
        raise ValueError("Database did not return anything")

    for _, mt_password in results:
        if password.casefold() == mt_password.casefold():
            return True

    return False
