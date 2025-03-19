from typing import ValuesView
from mie_trak_api.utils import with_db_conn, create_pydantic_model
from base_logger import getlogger
import pyodbc


LOGGER = getlogger("MT Item")

item_model = create_pydantic_model("item")


@with_db_conn(commit=True)
def get_or_create_item(cursor: pyodbc.Cursor, **item_data):
    """
    [TODO:description]

    :param cursor: [TODO:description]
    :raises ValueError: [TODO:description]
    :raises ValueError: [TODO:description]
    :raises ValueError: [TODO:description]
    """

    part_number = item_data.get("PartNumber", "")
    cursor.execute("SELECT ItemPK FROM Item WHERE PartNumber = ?", (part_number,))
    result = cursor.fetchone()

    if result:
        LOGGER.info(f"PartNumber: {part_number} found. (PK: {result[0]})")
        return result[0]

    validated_data = item_model(**item_data).model_dump(exclude_unset=True)

    cursor.execute("INSERT INTO ItemInventory (QuantityOnHand) Values (0.000)")
    cursor.execute("SELECT SCOPE_IDENTITY()")
    item_inventory_pk = cursor.fetchone()

    if not item_inventory_pk:
        raise ValueError("ItemPK was not returned.")

    validated_data["ItemInventoryFK"] = int(item_inventory_pk[0])

    columns = ", ".join(validated_data.keys())
    placeholders = ", ".join(["?"] * len(validated_data))
    values = tuple(validated_data.values())

    query = f"INSERT INTO Item ({columns}) VALUES ({placeholders})"

    cursor.execute(query, values)
    cursor.execute("SELECT IDENT_CURRENT('Item')")
    result = cursor.fetchone()

    if result and result[0]:
        LOGGER.info(f"Inserted new ItemPK: {result[0]}")
        return result[0]
    else:
        LOGGER.critical("SELECT IDENT failed in get_or_create_item")
        raise ValueError(
            "`SELECT SCOPE` did not return anything. Item might not be inserted."
        )


@with_db_conn()
def get_item(cursor: pyodbc.Cursor, **item_data) -> int | None:
    """
    [TODO:description]

    :param cursor: [TODO:description]
    :return: [TODO:description]
    :raises ValueError: [TODO:description]
    """
    if not item_data:
        raise ValueError("At least one condition must be provided to get an item.")

    where_conditions = " AND ".join([f"{key} = ?" for key in item_data.keys()])
    query = f"SELECT ItemPK FROM Item WHERE {where_conditions};"

    values = tuple(item_data.values())

    cursor.execute(query, values)
    result = cursor.fetchone()

    return result[0] if result else None


@with_db_conn(commit=True)
def update_item(cursor, itempk: int, **item_data) -> None:
    if not item_data:
        raise ValueError("At least one condition must be provided to get an item.")

    set_string = ", ".join([f"{key} = '{value}'" for key, value in item_data.items()])
    query = f"UPDATE Item SET {set_string} WHERE ItemPK = {itempk};"

    LOGGER.debug(query)
    cursor.execute(query)
    LOGGER.info(f"Updated ItemPK: {itempk}.")


@with_db_conn(commit=True)
def get_or_create_tooling(cursor: pyodbc.Cursor, description) -> int:
    search_query = f"Select ItemPK from Item Where Description='{description}' AND PartNumber LIKE '05-%'"
    return 0


@with_db_conn(commit=True)
def insert_part_details_in_item(
    cursor: pyodbc.Cursor, item_pk: int, part_number: str, values: dict, item_type=None
):
    """
    Updates an item in the database with additional part details based on its type.

    This function updates the `Item` table by setting attributes such as dimensions,
    weight, and drawing details. If the item is classified as "Material," specific
    attributes related to purchasing and shipping are set. Otherwise, drawing-related
    attributes and vendor details are updated.

    :param cursor: Database cursor for executing queries.
    :param item_pk: The primary key of the item to be updated.
    :param part_number: The vendor part number associated with the item.
    :param values: A dictionary containing field-value pairs for item attributes.
    :param item_type: The type of the item ("Material" or other types).
    """

    # Common fields for all items
    update_values = {
        "StockLength": values.get("stock_length", ""),
        "Thickness": values.get("stock_thickness", ""),
        "StockWidth": values.get("stock_width", ""),
        "Weight": values.get("weight", ""),
        "PartLength": values.get("length", ""),
        "PartWidth": values.get("width", ""),
    }

    if item_type == "Material":
        po_comment = f" Dimensions (L x W x T): {values.get('stock_length', '')} x {values.get('stock_width', '')} x {values.get('stock_thickness', '')}"
        update_values.update(
            {
                "PurchaseOrderComment": po_comment,
                "ManufacturedItem": 0,
                "Purchase": 1,
                "ShipLoose": 0,
                "BulkShip": 0,
            }
        )
    else:
        update_values.update(
            {
                "DrawingNumber": values.get("drawing_number", ""),
                "DrawingRevision": values.get("drawing_revision", ""),
                "Revision": values.get("pl_revision", ""),
                "VendorPartNumber": part_number,
            }
        )

    set_clause = ", ".join([f"{col} = ?" for col in update_values.keys()])
    query = f"UPDATE Item SET {set_clause} WHERE ItemPK = ?"

    cursor.execute(query, tuple(update_values.values()) + (item_pk,))

    LOGGER.info(
        f"Updated item {item_pk} ({'Material' if item_type == 'Material' else 'Standard'})."
    )


@with_db_conn(commit=True)
def check_and_create_tooling(cursor: pyodbc.Cursor, user_des: str):
    """
    Checks if a tooling item with the given description exists in the database.
    If it does not exist, it creates a new tooling item with a unique PartNumber.

    :param cursor: Database cursor for executing queries.
    :param user_des: The description of the tooling item.
    :return: The primary key (ItemPK) of the existing or newly created tooling item.
    """

    search_query = """
        SELECT ItemPK FROM Item 
        WHERE Description = ? AND PartNumber LIKE '05-%'
    """
    cursor.execute(search_query, (user_des,))
    result = cursor.fetchone()

    if result:
        LOGGER.info(
            f"Existing tooling found: ItemPK={result[0]}, Description='{user_des}'"
        )
        return result[0]

    part_name_query = """
        SELECT PartNumber FROM Item 
        WHERE PartNumber LIKE '05-%' AND PartNumber LIKE '%[0-9]'
    """
    cursor.execute(part_name_query)
    result = cursor.fetchall()

    numbers = []
    for part in result:
        try:
            number_str = part[0].split("05-")[1]
            numbers.append(int(number_str))
        except (IndexError, ValueError):
            continue  # Skip malformed PartNumbers

    new_part_number = f"05-{max(numbers) + 1}" if numbers else "05-1"

    insert_query = """
        INSERT INTO Item 
        (PartNumber, Description, CalculationTypeFK, PurchaseGeneralLedgerAccountFK, SalesCogsAccountFK, 
        MPSItem, ForecastOnMRP, MPSOnMRP, ServiceItem, ShipLoose, BulkShip, CertificationsRequiredBySupplier, ItemTypeFK)
        VALUES (?, ?, 12, 130, 130, 0, 0, 0, 0, 0, 0, 1, 3)
    """
    cursor.execute(insert_query, (new_part_number, user_des))

    cursor.execute("SELECT IDENT_CURRENT('Item')")
    result = cursor.fetchone()

    if result and result[0]:
        LOGGER.info(
            f"New tooling created: ItemPK={result[0]}, PartNumber='{new_part_number}', Description='{user_des}'"
        )
        return result[0]
    else:
        raise ValueError(
            f"Failed to retrieve ItemPK after inserting new tooling: PartNumber='{new_part_number}', Description='{user_des}'"
        )
