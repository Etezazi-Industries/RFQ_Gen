import pyodbc
from mie_trak_api.utils import with_db_conn
from base_logger import getlogger


LOGGER = getlogger("MT Router")


@with_db_conn(commit=True)
def create_router(cursor: pyodbc.Cursor, item_fk: int, part_number: str, division_fk=1, router_status_fk=2, router_type=0, default_router=1):
    query = f"""
    INSERT INTO Router (ItemFK, PartNumber, DivisionFK, RouterStatusFK, RouterType, DefaultRouter)
    VALUES (?, ?, ?, ?, ?, ?)
    """
    cursor.execute(query, (item_fk, part_number, division_fk, router_status_fk, router_type, default_router))
    cursor.execute("SELECT IDENT_CURRENT('Router')")
    result = cursor.fetchone()

    if result and result[0]:
        return result[0]
    else:
        raise ValueError("Error while inserting. Could not get back PK.")


@with_db_conn(commit=True)
def create_router_work_center(
    cursor: pyodbc.Cursor,
    item_fk,
    router_fk,
    order_by,
):
    """Creates the work center of a Finish router"""
    router_work_center_dict = {
        "ItemFK": item_fk,
        "RouterFK": router_fk,
        "OrderBy": order_by,
        "UnitOfMeasureSetFK": 1,
        "SequenceNumber": 1,
        "PartsPerBlank": 1.000,
        "PartsRequired": 1.000,
        "QuantityRequired": 1.000,
        "QuantityPerInverse": 1,
        "MinutesPerPart": 0,
        "VendorUnit": 1.00,
        "SetupTime": 0.00,
    }

    columns = ", ".join(router_work_center_dict.keys())
    placeholders = ", ".join(["?"] * len(router_work_center_dict))
    values = tuple(router_work_center_dict.values())

    query = f"INSERT INTO RouterWorkCenter ({columns}) VALUES ({placeholders});"

    cursor.execute(query, values)
