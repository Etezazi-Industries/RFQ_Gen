import pandas as pd
import pytest
from pprint import pprint
from pathlib import Path

from src.rfq_gen.app.excel_parser import create_dict_from_excel_new


# Helper function: write a DataFrame to a temporary Excel file.
def create_excel_file(tmp_path: Path, df: pd.DataFrame) -> str:
    file = tmp_path / "test.xlsx"
    df.to_excel(file, index=False)
    return str(file)


def test_valid_excel(tmp_path: Path):
    """
    Test that a correctly formatted Excel file returns the expected dictionary.
    We create two rows:
    - One main part (AssyFor is empty)
    - One assembly (AssyFor references the main part)
    """
    data = {
        "Part": ["P001", "A001"],
        "DESCRIPTION": ["Test part", "Assembly part"],
        "PartLength": ["5", "2"],
        "Thickness": ["0.5", "0.2"],
        "PartWidth": ["3", "1"],
        "Weight": ["1", "0.5"],
        "Material": ["Steel", "Aluminum"],
        "FinishCode": ["F1", "F2"],
        "HeatTreat": ["HT1", "HT2"],
        "DrawingNumber": ["D001", "D002"],
        "DrawingRevision": ["Rev1", "Rev2"],
        "QuantityRequired": ["10", "5"],
        "PLRevision": ["PL1", "PL2"],
        "AssyFor": ["", "P001"],  # Main part has empty string; assembly references it.
        "Hardware/Tooling": ["", ""],
        "StockLength": ["5", "2"],
        "StockWidth": ["3", "1"],
        "StockThickness": ["0.5", "0.2"],
    }
    df = pd.DataFrame(data)
    file_path = create_excel_file(tmp_path, df)

    result = create_dict_from_excel_new(file_path)

    # Check that we have two entries.
    assert len(result) == 2
    # Verify that the main part and assembly keys exist.
    assert "P001" in result
    assert "A001" in result
    # Verify numeric conversion: length should be a float and quantity an int.
    assert isinstance(result["P001"]["length"], float)
    assert result["P001"]["length"] == 5.0
    assert isinstance(result["P001"]["quantity_required"], int)
    assert result["P001"]["quantity_required"] == 10


def test_missing_required_columns(tmp_path: Path):
    """
    Test that a ValueError is raised if the Excel file is missing one or more required columns.
    Here, we omit the 'Part' column.
    """
    data = {
        # "Part": ["P001"],  # Omit the Part column intentionally.
        "DESCRIPTION": ["Test part"],
        "PartLength": ["5"],
        "Thickness": ["0.5"],
        "PartWidth": ["3"],
        "Weight": ["1"],
        "Material": ["Steel"],
        "FinishCode": ["F1"],
        "HeatTreat": ["HT1"],
        "DrawingNumber": ["D001"],
        "DrawingRevision": ["Rev1"],
        "QuantityRequired": ["10"],
        "PLRevision": ["PL1"],
        "AssyFor": [""],
        "Hardware/Tooling": [""],
        "StockLength": ["5"],
        "StockWidth": ["3"],
        "StockThickness": ["0.5"],
    }
    df = pd.DataFrame(data)
    file_path = create_excel_file(tmp_path, df)

    with pytest.raises(ValueError, match="Missing required columns: Part"):
        create_dict_from_excel_new(file_path)


def test_main_part_missing(tmp_path: Path):
    """
    Test that a ValueError is raised when no row is marked as the main part.
    The function expects at least one row with an empty 'AssyFor' column.
    """
    data = {
        "Part": ["P001", "A001"],
        "DESCRIPTION": ["Test part", "Assembly part"],
        "PartLength": ["5", "2"],
        "Thickness": ["0.5", "0.2"],
        "PartWidth": ["3", "1"],
        "Weight": ["1", "0.5"],
        "Material": ["Steel", "Aluminum"],
        "FinishCode": ["F1", "F2"],
        "HeatTreat": ["HT1", "HT2"],
        "DrawingNumber": ["D001", "D002"],
        "DrawingRevision": ["Rev1", "Rev2"],
        "QuantityRequired": ["10", "5"],
        "PLRevision": ["PL1", "PL2"],
        "AssyFor": ["Some", "P001"],  # Neither row has an empty AssyFor.
        "Hardware/Tooling": ["", ""],
        "StockLength": ["5", "2"],
        "StockWidth": ["3", "1"],
        "StockThickness": ["0.5", "0.2"],
    }
    df = pd.DataFrame(data)
    file_path = create_excel_file(tmp_path, df)

    with pytest.raises(
        ValueError,
        match="Main Part number missing from excel sheet. Check Assy for column.",
    ):
        create_dict_from_excel_new(file_path)


def test_duplicate_part_numbers(tmp_path: Path):
    """
    Test that duplicate part numbers are handled correctly.
    When the same part number appears more than once, the function should
    append a unique suffix (e.g., '_____' followed by a number) to subsequent duplicates.
    """
    data = {
        "Part": ["P001", "P001"],  # Duplicate part numbers.
        "DESCRIPTION": ["Test part 1", "Test part 2"],
        "PartLength": ["5", "5"],
        "Thickness": ["0.5", "0.5"],
        "PartWidth": ["3", "3"],
        "Weight": ["1", "1"],
        "Material": ["Steel", "Steel"],
        "FinishCode": ["F1", "F1"],
        "HeatTreat": ["HT1", "HT1"],
        "DrawingNumber": ["D001", "D001"],
        "DrawingRevision": ["Rev1", "Rev1"],
        "QuantityRequired": ["10", "10"],
        "PLRevision": ["PL1", "PL1"],
        "AssyFor": ["", ""],  # Both rows are treated as main parts.
        "Hardware/Tooling": ["", ""],
        "StockLength": ["5", "5"],
        "StockWidth": ["3", "3"],
        "StockThickness": ["0.5", "0.5"],
    }
    df = pd.DataFrame(data)
    file_path = create_excel_file(tmp_path, df)

    result = create_dict_from_excel_new(file_path)

    # We expect the dictionary to contain one entry as "P001" and the duplicate to have a suffix.
    assert "P001" in result
    # Check that the second key has been modified to ensure uniqueness.
    duplicate_key = "P001_____1"
    assert duplicate_key in result


def test_stop_on_blank_row(tmp_path: Path):
    """
    Test that parsing stops when 3 consecutive blank rows are encountered.
    
    The Excel file is simulated with:
      - 2 valid rows (with a non-empty 'Part' column)
      - 3 consecutive blank rows (empty 'Part' column)
      - 2 valid rows afterward (which should not be processed)
      
    Expected result: Only the 2 valid rows before the blank rows are parsed.
    """
    # Define two valid rows
    valid_row1 = {
        "Part": "P001",
        "DESCRIPTION": "Valid part 1",
        "PartLength": "5",
        "Thickness": "0.5",
        "PartWidth": "3",
        "Weight": "1",
        "Material": "Steel",
        "FinishCode": "F1",
        "HeatTreat": "HT1",
        "DrawingNumber": "D001",
        "DrawingRevision": "Rev1",
        "QuantityRequired": "10",
        "PLRevision": "PL1",
        "AssyFor": "",
        "Hardware/Tooling": "",
        "StockLength": "5",
        "StockWidth": "3",
        "StockThickness": "0.5",
    }
    valid_row2 = valid_row1.copy()
    valid_row2["Part"] = "P002"
    valid_row2["DESCRIPTION"] = "Valid part 2"

    # Create three blank rows (all fields empty)
    blank_row = {key: "" for key in valid_row1.keys()}

    # Two more valid rows after the blank block (which should be ignored)
    valid_row3 = valid_row1.copy()
    valid_row3["Part"] = "P003"
    valid_row3["DESCRIPTION"] = "Valid part 3"
    
    valid_row4 = valid_row1.copy()
    valid_row4["Part"] = "P004"
    valid_row4["DESCRIPTION"] = "Valid part 4"

    # Assemble the rows: 2 valid rows, 3 blank rows, then 2 valid rows
    rows = [valid_row1, valid_row2, blank_row, blank_row, blank_row, valid_row3, valid_row4]
    columns = list(valid_row1.keys())
    df = pd.DataFrame(rows, columns=pd.Index(columns))
    file_path = create_excel_file(tmp_path, df)

    result = create_dict_from_excel_new(file_path)
    
    # Since parsing stops on the 3rd consecutive blank row,
    # only the first two valid rows should be parsed.
    pprint(result)
    assert len(result) == 2
    assert "P001" in result
    assert "P002" in result
    # P003 and P004 should not be present because they come after the stopping point.
    assert "P003" not in result
    assert "P004" not in result
