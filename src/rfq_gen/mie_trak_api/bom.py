import pyodbc
from mie_trak_api.utils import with_db_conn
from base_logger import getlogger


LOGGER = getlogger("MT BOM")


default_values = {
    "PartyFK": None,
    "UnitOfMeasureSetFK": 1,
    "CalculationTypeFK": 17,
    "Tool": 0,
    "StopSequence": 0,
    "UnattendedOperation": 0,
    "DoNotUseDeliverySchedule": 0,
    "VendorUnit": 1.00000,
    "GrainDirection": 0,
    "PartsPerBlank": 1.000,
    "AgainstGrain": 0,
    "DoubleSided": 0,
    "CertificationsRequired": 0,
    "NonAmortizedItem": 0,
    "Pull": 0,
    "NotIncludeInPiecePrice": 0,
    "Lock": 0,
    "Nestable": 0,
    "BulkShip": 0,
    "ShipLoose": 0,
    "CustomerSuppliedMaterial": 0,
    "SetupTime": 0.00,
    "ScrapRebate": 0.000,
    "PartWidth": 0.00,
    "PartLength": 0.000,
    "PartsRequired": 1.000,
    "QuantityRequired": 1.000,
    "MinimumPiecePrice": 0.00,
    "PartsPerBlankScrapPercentage": 0.000,
    "MarkupPercentage1": 9.999999,
    "PieceWeight": 0.000,
    "CustomPieceWeight": 0.0000,
    "PieceCost": 0.0000,
    "PiecePrice": 0.00000,
    "StockPieces": 0,
    "StockPiecesScrapPercentage": 0.000,
    "Thickness": 0.00,
}


# TODO: testing pending
@with_db_conn(commit=True)
def create_bom_quote(
    cursor: pyodbc.Cursor,
    quote_fk: int,
    item_fk: int,
    quote_assembly_seq_number_fk: int,
    sequence_number: int,
    order_by: int,
    **kwargs,
):
    """
    [TODO:description]

    :param cursor: [TODO:description]
    :param quote_fk: [TODO:description]
    :param item_fk: [TODO:description]
    :param quote_assembly_seq_number_fk: [TODO:description]
    :param sequence_number: [TODO:description]
    :param order_by: [TODO:description]
    """

    info_dict = {
        "QuoteFK": quote_fk,
        "ItemFK": item_fk,
        "QuoteAssemblySeqNumberFK": quote_assembly_seq_number_fk,
        "SequenceNumber": sequence_number,
        "OrderBy": order_by,
        **default_values,  # Default values
        **kwargs,  # User-provided values overwrite defaults
    }

    LOGGER.debug(f"Inserting dict: \n{info_dict}")

    columns = ", ".join(info_dict.keys())
    placeholders = ", ".join(["?"] * len(info_dict))
    values = tuple(info_dict.values())

    query = f"INSERT INTO QuoteAssembly ({columns}) VALUES ({placeholders});"

    cursor.execute(query, values)
