from typing import List
from datetime import datetime
from utils import with_db_conn, LOGGER


@with_db_conn()
def get_all_vacation_requests(cursor) -> List:
    """
    Fetch all pending vacation requests by joining the User table.

    This function retrieves all vacation requests that are not yet approved,
    including employee details such as first name and last name.

    :param cursor: Database cursor passed by the decorator.
    :type cursor: pyodbc.Cursor
    :return: A formatted list of vacation request records.
    :rtype: List
    :raises ValueError: If no records are returned from the query.
    """
    query = """
        SELECT v.VacationRequestPK, u.firstname, u.lastname, v.FromDate, v.ToDate, 
               v.StartTime, v.Hours, v.Reason, v.Approved
        FROM VacationRequest v
        JOIN [User] u ON v.EmployeeFK = u.UserPK 
        WHERE v.Approved = 0
        ORDER BY v.VacationRequestPK DESC;
    """

    cursor.execute(query)
    results = cursor.fetchall()

    if not results:
        LOGGER.error(f"MT did not return anything for: \n{query}")
        raise ValueError("Mie Trak did not return anything. Check Query.")

    return _format_results(results)


def _format_results(data):
    """
    Formats raw database query results into a structured list of dictionaries.

    Each dictionary represents a vacation request with properly formatted dates,
    times, and employee details.

    :param data: List of tuples containing raw database results.
    :type data: List[Tuple]
    :return: A list of formatted vacation request records.
    :rtype: List[Dict[str, Any]]
    """
    formatted_data = []
    for row in data:
        (
            vacation_id,
            first_name,
            last_name,
            from_date,
            to_date,
            start_time,
            hours,
            reason,
            approved,
        ) = row
        formatted_row = {
            "Vacation ID": vacation_id,
            "Employee": f"{first_name} {last_name}",
            "From Date": from_date.strftime("%Y-%m-%d") if from_date else "N/A",
            "To Date": to_date.strftime("%Y-%m-%d") if to_date else "N/A",
            "Start Time": datetime.strptime(start_time[:15], "%H:%M:%S.%f").strftime(
                "%I:%M %p"
            )
            if start_time
            else "N/A",
            "Hours": float(hours) if hours else "N/A",
            "Reason": reason,
            "Approved": approved,
        }
        formatted_data.append(formatted_row)
    return formatted_data


@with_db_conn(commit=True)
def approve_vacation_request(cursor, request_pk: int) -> None:
    """
    Marks a vacation request as approved.

    Updates the `Approved` field of the `VacationRequest` table for the given request.

    :param cursor: Database cursor.
    :type cursor: pyodbc.Cursor
    :param request_pk: Primary key of the vacation request to approve.
    :type request_pk: int
    :return: None
    """
    query = """
        UPDATE VacationRequest
        SET Approved = 1
        WHERE VacationRequestPK = ?
    """
    cursor.execute(query, (request_pk,))


@with_db_conn(commit=True)
def update_vacation_request_reason(cursor, vacation_request_pk: int, reason: str):
    """
    Adds a note to the vacation request.

    Appends the `Reason` field of the `VacationRequest` table with the reason string.
    Usually done when we want to keep track of what was disapproved in mie trak.

    NOTE: Reason should have a timestamp. For reasoning formatting see VacationRequestPK = 3;

    :param cursor: Database cursor.
    :type cursor: pyodbc.Cursor
    :param vacation_request_pk: Primary key of the vacation request to update.
    :type vacation_request_pk: int
    :param reason: The note to update the vacation request with.
    :type reason: str
    :raises RuntimeError: If parameters are None.
    """
    query = """
    UPDATE VacationRequest
    SET Reason = reason + CHAR(13) + CHAR(14) + CHAR(13) + CHAR(14) + ?
    WHERE VacationRequestPK = ?
    """
    cursor.execute(query, (reason, vacation_request_pk))


@with_db_conn()
def get_user_email_from_vacation_pk(cursor, pk: int) -> str:
    """
    Retrieves the email of the user associated with a given vacation request.

    :param cursor: Database cursor.
    :type cursor: pyodbc.Cursor
    :param pk: Primary key of the vacation request.
    :type pk: int
    :return: Email address of the user.
    :rtype: str
    :raises ValueError: If no matching record is found.
    """
    query = """
        SELECT u.Email
        FROM VacationRequest v
        JOIN [User] u ON v.EmployeeFK = u.UserPK
        WHERE v.VacationRequestPK = ?;
    """

    cursor.execute(query, (pk,))
    result = cursor.fetchone()

    if not result:
        LOGGER.error("Database did not return anything")
        raise ValueError("Database did not return anything")

    return result[0]
