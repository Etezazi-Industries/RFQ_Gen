import pandas as pd
from typing import Optional, Dict, Any
from pydantic import BaseModel, ValidationError
from base_logger import getlogger
from mie_trak_api import item
import re


LOGGER = getlogger("Excel Parser")


class PartData(BaseModel):
    part_number: str
    description: Optional[str]
    length: float = 0.0
    thickness: float = 0.0
    width: float = 0.0
    weight: float = 0.0
    material: Optional[str]
    finish_code: Optional[str]
    heat_treat: Optional[str]
    drawing_number: Optional[str]
    drawing_revision: Optional[str]
    quantity_required: int
    pl_revision: Optional[str]
    assy_for: Optional[str]
    hardware_or_supplies: Optional[str]
    stock_length: float = 0.0
    stock_width: float = 0.0
    stock_thickness: float = 0.0


def sanitize_value(value, default=None):
    """Sanitizes NaN values and strips strings."""
    if pd.isna(value):  # More robust check than math.isnan
        return default
    if isinstance(value, str):
        return value.strip()
    return value


def create_dict_from_excel_new(filepath: str) -> Dict[str, Dict[str, Any]]:
    """
    Reads an Excel file and converts it into a dictionary where each part number is a key,
    and its corresponding data is stored as a dictionary.

    The function ensures that required columns exist, renames them for consistency,
    applies data sanitization, converts numeric fields, and validates each row using
    the `PartData` Pydantic model. If a part number is missing, a fallback name is generated.
    If a duplicate part number is found, a unique suffix is appended.

    :param filepath: Path to the Excel file to be processed.
    :return: A dictionary where keys are part numbers and values are dictionaries of part attributes.
    :raises ValueError: If required columns are missing in the Excel file.
    :raises ValueError: If data validation fails for one or more rows.
    """

    df = pd.read_excel(filepath, dtype=str).fillna("")

    required_columns = {
        "Part": "part_number",
        "DESCRIPTION": "description",
        "PartLength": "length",
        "Thickness": "thickness",
        "PartWidth": "width",
        "Weight": "weight",
        "Material": "material",
        "FinishCode": "finish_code",
        "HeatTreat": "heat_treat",
        "DrawingNumber": "drawing_number",
        "DrawingRevision": "drawing_revision",
        "QuantityRequired": "quantity_required",
        "PLRevision": "pl_revision",
        "AssyFor": "assy_for",
        "Hardware/Tooling": "hardware_or_supplies",
        "StockLength": "stock_length",
        "StockWidth": "stock_width",
        "StockThickness": "stock_thickness",
    }

    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

    df = df.rename(columns=required_columns)

    df = df.map(sanitize_value)

    numeric_fields = [
        "length",
        "thickness",
        "width",
        "weight",
        "stock_length",
        "stock_width",
        "stock_thickness",
    ]
    df[numeric_fields] = (
        df[numeric_fields].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    )

    df["quantity_required"] = (
        df["quantity_required"]
        .apply(pd.to_numeric, errors="coerce")
        .fillna(0)
        .astype(int)
    )

    my_dict = {}

    errors = []
    for idx, (_, row) in enumerate(df.iterrows(), start=1):
        part_number = row["part_number"] or f"Tool-{idx}"  # Fallback naming

        try:
            part_data = PartData(**row.to_dict())  # Validate with Pydantic
        except ValidationError as e:
            errors.append(f"Row {idx}: {e}")
            continue

        original_part_number = part_number
        suffix = 1
        while part_number in my_dict:
            part_number = f"{original_part_number}_____{suffix}"
            suffix += 1

        my_dict[part_number] = part_data.model_dump()

    if errors:
        raise ValueError(f"Data validation failed:\n" + "\n".join(errors))

    # check for a main part number.
    all_assy_for_data = [value.get("assy_for") for _, value in my_dict.items()]
    if not "" in all_assy_for_data:
        raise ValueError(
            f"Main Part number missing from excel sheet. Check Assy for column."
        )

    LOGGER.info("Excel File extracted successfully.")

    return my_dict


def generate_item_pks(info_dict: Dict[str, Dict[str, Any]]) -> Dict[str, tuple]:
    """
    Generates a dictionary mapping part numbers to their corresponding material, heat treatment, and finish primary keys.

    This function processes an input dictionary containing item details, checks if corresponding
    records exist in the database, and retrieves or creates primary keys (PKs) for materials, finishes,
    and heat treatments. It ensures unique part number keys in the returned dictionary.

    :param info_dict: A dictionary where each key is a part number and the value is a dictionary containing:
                      - "material": Material description
                      - "finish_code": Finish description
                      - "heat_treat": Heat treatment description
                      - "part_number": Part number for lookup
                      - "stock_length": Stock length for material lookup
                      - "stock_width": Stock width for material lookup
                      - "thickness": Thickness for material lookup
    :return: A dictionary mapping each unique part number to a tuple of:
             (material_pk, heat_treat_pk, finish_pk), where each PK is an integer or None if not found/created.
    """

    my_dict = {}
    for new_key, value_dict in info_dict.items():
        # Remove suffix if present
        key = (
            new_key.split("_____")[0]
            if bool(re.search(r"____\d+$", new_key))
            else new_key
        )

        # Initialize primary keys
        mat_pk = None
        fin_pk = None
        ht_pk = None

        # Fetch or create material PK
        if value_dict.get("material"):
            mat_pk = item.get_item(
                **{
                    "PartNumber": value_dict.get("part_number"),
                    "StockLength": value_dict.get("stock_length"),
                    "StockWidth": value_dict.get("stock_width"),
                    "Thickness": value_dict.get("thickness"),
                }
            )
            if not mat_pk:
                mat_pk = item.get_or_create_item(
                    **{
                        "PartNumber": value_dict.get("part_number"),
                        "ServiceItem": 0,
                        "Purchase": 1,
                        "Manufactureditem": 0,
                        "ItemTypeFK": 2,
                        "OnlyCreate": 1,
                        "BulkShip": 0,
                        "ShipLoose": 0,
                        "CertReqdBySupplier": 1,
                        "PurchaseAccountFK": 127,
                        "CogsAccFK": 127,
                        "CalculationTypeFK": 4,
                    }
                )

        # Fetch or create finish PK
        if value_dict.get("finish_code"):
            material = value_dict.get("material")
            comment = (
                f"Material: {material} \n{value_dict['finish_code']}"
                if material
                else value_dict["finish_code"]
            )

            fin_pk = item.get_or_create_item(
                **{
                    "PartNumber": f"{key} - OP Finish",
                    "ItemTypeFK": 5,
                    "Comment": comment,
                    "PurchaseOrderComment": comment,
                    "Inventoriable": 0,
                    "OnlyCreate": 1,
                    "CertReqdBySupplier": 1,
                    "CanNotCreateWorkOrder": 1,
                    "CanNotInvoice": 1,
                    "PurchaseAccountFK": 125,
                    "CogsAccFK": 125,
                    "CalculationTypeFK": 17,
                }
            )

        # Fetch or create heat treat PK
        if value_dict.get("heat_treat"):
            material = value_dict.get("material")
            comment = (
                f"Material: {material} \n{value_dict['heat_treat']}"
                if material
                else value_dict["heat_treat"]
            )

            ht_pk = item.get_or_create_item(
                **{
                    "PartNumber": f"{key} - OP HT",
                    "ItemTypeFK": 5,
                    "Description": value_dict.get("heat_treat"),
                    "Comment": comment,
                    "PurchaseOrderComment": comment,
                    "Inventoriable": 0,
                    "OnlyCreate": 1,
                    "CertReqdBySupplier": 1,
                    "CanNotCreateWorkOrder": 1,
                    "CanNotInvoice": 1,
                    "PurchaseAccountFK": 125,
                    "CogsAccFK": 125,
                    "CalculationTypeFK": 17,
                }
            )

        # Ensure unique key in dictionary
        original_key = key
        suffix = 1
        while key in my_dict:
            key = f"{original_key}_____{suffix}"
            suffix += 1

        my_dict[key] = (mat_pk, ht_pk, fin_pk)

    return my_dict
