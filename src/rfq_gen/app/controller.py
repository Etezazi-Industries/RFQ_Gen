import re
import os
from typing import Dict, Any
from base_logger import getlogger
from mie_trak_api import request_for_quote, quote, item, router
from app.gui.utils import transfer_file_to_folder


LOGGER = getlogger("Controller")


def create_rfq(
    quote_pk_dict,
    item_pk_dict,
    rfq_pk,
    info_dict: Dict[str, Dict[str, Any]],
    parent_quote_fk=None,
    i=1,
):
    """
    Creates RFQ line items and quote assemblies based on the provided parts and associated data.
    This function analyzes the given parts dictionary (info_dict) to create line items for RFQ,
    handle assemblies, and link sub-assemblies or child parts appropriately.

    :param quote_pk_dict: Dictionary mapping part numbers to their corresponding Quote PKs.
    :type quote_pk_dict: dict
    :param item_pk_dict: Dictionary mapping part numbers to their corresponding Item PKs.
    :type item_pk_dict: dict
    :param rfq_pk: The primary key of the RFQ where line items are being added.
    :type rfq_pk: int
    :param info_dict: Dictionary containing part numbers as keys and associated data as values.
    :type info_dict: Dict[str, Dict[str, Any]]
    :param parent_quote_fk: Optional parent Quote FK for nested assemblies.
    :type parent_quote_fk: int, optional
    :param i: Starting index for RFQ line items, defaults to 1.
    :type i: int, optional
    :raises ValueError: If necessary main part or quote data is missing for assembly creation.
    :raises KeyError: If required parent assembly information is not found when expected.
    """

    main_part_number = None
    main_quote_pk = None

    LOGGER.info("Starting RFQ line item and assembly creation.")

    parent_quote_assembly_pk_dict = {}
    for new_key, value in info_dict.items():
        if re.search(r"_____\d+$", new_key) is None:
            key = new_key
        else:
            key = new_key.split("_____")[0]

        part_number = key
        assy_for = value.get("assy_for", None)
        quote_pk = quote_pk_dict.get(part_number)
        item_pk = item_pk_dict.get(part_number)

        if not assy_for:
            LOGGER.info(f"Creating RFQ line item for part: {part_number}")
            request_for_quote.create_rfq_line_item_with_qty(
                item_pk,
                rfq_pk,
                i,
                quote_pk,
                quantity=value.get("quantity_required"),
            )
            i += 1
            main_quote_pk = quote_pk
            main_part_number = part_number
            LOGGER.info(
                f"Line item created for part {part_number}, linked to QuotePK {quote_pk}"
            )

        elif assy_for and not value.get("hardware_or_supplies"):
            LOGGER.info(
                f"Handling assembly for part: {part_number}, assembly for: {assy_for}"
            )
            if not main_part_number or not main_quote_pk:
                raise ValueError("Data from excel sheet is not proper bruh.")

            if assy_for == main_part_number:
                quote_fk = main_quote_pk
                parent_quote_assembly_pk = quote.create_assy_quote(
                    quote_pk, quote_fk, value.get("quantity_required", "")
                )
                parent_quote_assembly_pk_dict[part_number] = parent_quote_assembly_pk
                LOGGER.info(
                    f"Assembly quote created for part {part_number}, linked to main QuotePK {quote_fk}"
                )

            else:
                parent_quote_fk = quote_pk_dict[assy_for]
                if assy_for not in parent_quote_assembly_pk_dict:
                    raise KeyError(
                        f"Key '{assy_for}' not found in parent_quote_assembly_pk_dict"
                    )
                parent_quote_assembly_pk_new = parent_quote_assembly_pk_dict[assy_for]
                parent_quote_assembly_pk = quote.create_assy_quote(
                    quote_pk,
                    main_quote_pk,
                    value.get("quantity_required", 1),
                    parent_quote_fk=parent_quote_fk,
                    parent_quote_asembly=parent_quote_assembly_pk_new,
                )
                parent_quote_assembly_pk_dict[part_number] = parent_quote_assembly_pk
                LOGGER.info(
                    f"Sub-assembly quote created for part {part_number}, parent assembly: {assy_for}"
                )


def create_finish_router(finish_description: str, item_fin_pk: int, part_num: str):
    "Adds a router for every finish"
    finish_code = finish_description.split("\n")
    finish_pks = []

    if finish_code:
        for code in finish_code:
            finish_codes_pk = item.get_or_create_item(
                **{
                    "PartNumber": code[:100],
                    "Description": code[
                        :490
                    ],  # TODO: Fix this as its crossing the limit, add this to the comments.
                    "Inventoriable": 0,
                    "ItemTypeFK": 5,
                    "CertificationsRequiredBySupplier": 1,
                    "CanNotCreateWorkOrder": 1,
                    "CanNotInvoice": 1,
                    "PurchaseGeneralLedgerAccountFK": 125,
                    "SalesCogsAccountFK": 125,
                    "CalculationTypeFK": 17,
                    "Comment": code,
                }
            )
            finish_pks.append(finish_codes_pk)

    router_pk = router.create_router(item_fin_pk, part_num)
    LOGGER.debug(f"Created Router PK: {router_pk}")

    for idx, pk in enumerate(finish_pks, start=1):
        router.create_router_work_center(pk, router_pk, idx)


def transfer_and_categorize_files(file_list, destination_path):
    """
    Transfers files to the specified destination and categorizes them based on file name patterns.

    :param file_list: List of file paths to transfer.
    :type file_list: list
    :param destination_path: Destination directory where files will be copied.
    :type destination_path: str
    :return: Dictionary mapping transferred file paths to their document group PKs (or None if uncategorized).
    :rtype: dict
    """
    result_dict = {}

    for file in file_list:
        # Copy file to destination folder (folder is created if not exists)
        file_path_to_add_to_rfq = transfer_file_to_folder(destination_path, file)
        path = file_path_to_add_to_rfq.lower()

        # Categorize based on file name pattern
        if (
            "_pl_" in path
            or "spdl" in path
            or "psdl" in path
            or "pl" in os.path.basename(path)
        ):
            result_dict[file_path_to_add_to_rfq] = 26
        elif "dwg" in path or "drw" in path:
            result_dict[file_path_to_add_to_rfq] = 27
        elif "step" in path or "stp" in path:
            result_dict[file_path_to_add_to_rfq] = 30
        elif "zsp" in path or "speco" in path:
            result_dict[file_path_to_add_to_rfq] = 33
        elif ".cat" in path:
            result_dict[file_path_to_add_to_rfq] = 16
        else:
            result_dict[file_path_to_add_to_rfq] = None  # Unmatched pattern

    return result_dict
