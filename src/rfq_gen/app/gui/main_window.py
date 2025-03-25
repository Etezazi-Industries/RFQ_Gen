import os
import datetime
import re
from pprint import pprint
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from tkcalendar import Calendar
from threading import Thread
from typing import Dict, Any
from app import controller
from app.gui.utils import center_window, gui_error_handler
from app.excel_parser import create_dict_from_excel_new, generate_item_pks
from app.gui.cust_buyer_selection_gui import CustomerSelectionGUI
from mie_trak_api import bom, item, party, request_for_quote, quote, router
from base_logger import getlogger


LOGGER = getlogger("Main")


class LoadingScreen(tk.Toplevel):
    """Class to display a loading screen whine generating the RFQ"""

    def __init__(self, master, max_progress):
        super().__init__(master)
        self.title("Generating RFQ")
        self.geometry("300x100")
        self.protocol("WM_DELETE_WINDOW", self.disable_close_button)
        self.attributes("-topmost", True)  # Ensure loading screen stays on top
        self.grab_set()
        self.progressbar = ttk.Progressbar(
            self,
            orient="horizontal",
            length=200,
            mode="determinate",
            maximum=max_progress,
        )
        self.progressbar.pack(pady=10)

    def set_progress(self, value):
        self.progressbar["value"] = value
        if value >= self.progressbar["maximum"]:
            self.destroy()

    def disable_close_button(self):
        """The RFQ gen process is not affected if user by mistake clicks on close button in the Loading screen"""
        pass


class RfqGen(tk.Tk):
    """Main class with main window and generate rfq function"""

    def __init__(self):
        super().__init__()
        self.title("RFQGen")
        center_window(self, height=650, width=750)

        self.files = {
            "Excel files": [],
            "Estimation files": [],
            "Parts Requested Files": [],
            "All Files": [],
        }
        self.party_details = None
        self.make_combobox()

    def make_combobox(self):
        """Updated Main Window GUI layout with Frames for better structure and flexibility using grid only."""

        for i in range(6):
            self.grid_columnconfigure(i, weight=1)

        self.grid_rowconfigure(3, weight=1)

        # --- Row 0: Heading ---
        heading_frame = tk.Frame(self)
        heading_frame.grid(row=0, column=0, columnspan=6, pady=10, sticky="ew")
        heading_frame.grid_columnconfigure(0, weight=1)
        self.heading_label = tk.Label(
            heading_frame, text="RFQ Gen", font=("Helvetica", 16, "bold")
        )
        self.heading_label.grid(row=0, column=0, sticky="ew")
        heading_separator = ttk.Separator(heading_frame, orient="horizontal")
        heading_separator.grid(row=1, column=0, sticky="ew", pady=(5, 0))

        # --- Row 1: Customer, Buyer, and RFQ# in one frame ---
        info_frame = tk.Frame(self)
        info_frame.grid(row=1, column=0, columnspan=6, pady=5, sticky="ew")
        for i in range(3):
            info_frame.grid_columnconfigure(i, weight=1)

        # Row 0: Customer and Buyer info with Add button.
        self.customer_info_label = tk.Label(
            info_frame,
            text="Customer:\nNot Selected",
            anchor="w",
            justify="left",
            wraplength=300,
            font=("Consolas", 12, "bold"),
        )
        self.customer_info_label.grid(row=0, column=0, padx=5, pady=2, sticky="ew")

        self.buyer_info_label = tk.Label(
            info_frame,
            text="Buyer:\nNot Selected",
            anchor="w",
            justify="left",
            wraplength=300,
            font=("Consolas", 12, "bold"),
        )
        self.buyer_info_label.grid(row=0, column=1, padx=(20, 5), pady=2, sticky="ew")

        self.add_button = tk.Button(
            info_frame, text="Add", command=self.open_add_buyer_screen
        )
        self.add_button.grid(row=0, column=2, padx=5, pady=2, sticky="e")

        info_frame.columnconfigure(0, weight=1)
        info_frame.columnconfigure(1, weight=1)
        info_frame.columnconfigure(2, weight=0)

        # Row 1: RFQ Number label and entry with extra top padding.
        rfq_frame = tk.Frame(info_frame)
        rfq_frame.grid(row=1, column=0, columnspan=3, padx=5, pady=(10, 2), sticky="ew")
        rfq_frame.columnconfigure(0, weight=0)  # Label column does not expand
        rfq_frame.columnconfigure(
            1, weight=1
        )  # Entry column expands to fill remaining space

        self.rfq_number_label = tk.Label(
            rfq_frame, text="Customer RFQ#:", font=("Consolas", 12, "bold")
        )
        self.rfq_number_label.grid(row=0, column=0, padx=(0, 5), pady=2, sticky="w")

        self.rfq_number_text = tk.Entry(rfq_frame)
        self.rfq_number_text.grid(row=0, column=1, padx=(0, 5), pady=2, sticky="ew")

        # --- Row 2: Separator between Info and File Upload Section ---
        sep1 = ttk.Separator(self, orient="horizontal")
        sep1.grid(row=2, column=0, columnspan=6, sticky="ew", pady=5)

        # --- Row 3: File Upload Section ---
        file_upload_frame = tk.Frame(self)
        file_upload_frame.grid(row=3, column=0, columnspan=6, pady=5, sticky="nsew")
        file_upload_frame.grid_columnconfigure(0, weight=1)
        file_upload_frame.grid_columnconfigure(1, weight=0)
        file_upload_frame.grid_columnconfigure(2, weight=1)
        file_upload_frame.grid_rowconfigure(0, weight=0)
        file_upload_frame.grid_rowconfigure(1, weight=0)
        file_upload_frame.grid_rowconfigure(2, weight=1)

        # File Upload Heading (centered).
        self.file_upload_heading = tk.Label(
            file_upload_frame,
            text="File Upload Section",
            font=("Helvetica", 12, "bold"),
        )
        self.file_upload_heading.grid(row=0, column=0, columnspan=3, pady=(10, 5))

        # Subframe for the Combobox, now centered.
        file_type_options_frame = tk.Frame(file_upload_frame)
        file_type_options_frame.grid(
            row=1, column=0, columnspan=3, pady=(5, 10), sticky="nsew"
        )
        # Use a 3-column grid to center the combobox.
        file_type_options_frame.grid_columnconfigure(0, weight=1)
        file_type_options_frame.grid_columnconfigure(1, weight=0)
        file_type_options_frame.grid_columnconfigure(2, weight=1)

        self.file_type_combo = ttk.Combobox(
            file_type_options_frame,
            values=[
                "Excel files",
                "Estimation files",
                "Parts Requested Files",
                "All Files",
            ],
            state="readonly",
            width=25,  # increased width
        )
        self.file_type_combo.set("Excel files")
        # Place the combobox in the center column.
        self.file_type_combo.grid(row=0, column=1, padx=5)
        self.file_type_combo.bind("<<ComboboxSelected>>", self.update_file_display)

        # Subframe for the File Display (Listbox) and bottom row widgets.
        file_display_upload_frame = tk.Frame(file_upload_frame)
        file_display_upload_frame.grid(
            row=2, column=0, columnspan=3, pady=(5, 10), sticky="nsew"
        )
        file_display_upload_frame.grid_columnconfigure(0, weight=1)
        file_display_upload_frame.grid_columnconfigure(1, weight=1)
        file_display_upload_frame.grid_rowconfigure(0, weight=1)

        self.file_path_PR_entry = tk.Listbox(
            file_display_upload_frame,
            font=("Consolas", 12),
            height=5,
            width=80,  # decreased width
        )
        self.file_path_PR_entry.grid(
            row=0, column=0, columnspan=2, padx=20, pady=5, sticky="ns"
        )

        # In the bottom row, place the ITAR checkbox on the left and the Upload button on the right.
        self.itar_restricted_var = tk.BooleanVar()
        self.itar_restricted_checkbox = tk.Checkbutton(
            file_display_upload_frame,
            text="ITAR RESTRICTED",
            variable=self.itar_restricted_var,
        )
        self.itar_restricted_checkbox.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        self.upload_button = tk.Button(
            file_display_upload_frame,
            text="Upload",
            command=lambda: self.browse_files_parts_requested(
                self.file_type_combo.get()
            ),
        )
        self.upload_button.grid(row=1, column=0, padx=5, pady=5, sticky="e")

        # --- Row 4: Separator between File Upload and Date Section ---
        sep2 = ttk.Separator(self, orient="horizontal")
        sep2.grid(row=4, column=0, columnspan=6, sticky="ew", pady=5)

        # --- Row 5: Date Section ---
        date_frame = tk.Frame(self)
        date_frame.grid(row=5, column=0, columnspan=6, pady=5, sticky="ew")
        for i in range(6):
            date_frame.grid_columnconfigure(i, weight=1)

        self.inquiry_date_label = tk.Label(
            date_frame, text="Inquiry Date:", font=("Consolas", 12, "bold")
        )
        self.inquiry_date_label.grid(row=0, column=0, padx=5, pady=2, sticky="w")

        # Empty label to reserve space.
        self.inquiry_date_value = tk.Label(date_frame, text="", width=20)
        self.inquiry_date_value.grid(row=0, column=1, padx=5, pady=2, sticky="nsew")

        self.inquiry_cal_button = tk.Button(
            date_frame, text="Cal", command=lambda: self.open_calendar("inquiry")
        )
        self.inquiry_cal_button.grid(row=0, column=2, padx=5, pady=2)

        self.due_date_label = tk.Label(
            date_frame, text="Due Date:", font=("Consolas", 12, "bold")
        )
        self.due_date_label.grid(row=0, column=3, padx=5, pady=2, sticky="w")

        # Empty label to reserve space.
        self.due_date_value = tk.Label(date_frame, text="", width=20)
        self.due_date_value.grid(row=0, column=4, padx=5, pady=2, sticky="nsew")

        self.due_cal_button = tk.Button(
            date_frame, text="Cal", command=lambda: self.open_calendar("due")
        )
        self.due_cal_button.grid(row=0, column=5, padx=5, pady=2)

        # --- Row 6: Action Buttons ---
        action_frame = tk.Frame(self)
        action_frame.grid(row=6, column=0, columnspan=6, pady=10, sticky="ew")
        for i in range(3):
            action_frame.grid_columnconfigure(i, weight=1)

        self.generate_button = tk.Button(
            action_frame,
            text="Generate RFQ",
            command=self.generate_rfq_with_loading_screen,
        )
        self.generate_button.grid(row=0, column=0, padx=5, pady=2, sticky="nsew")

        self.update_rfq_button = tk.Button(
            action_frame, text="Update RFQ", command=self.update_rfq
        )
        self.update_rfq_button.grid(row=0, column=1, padx=5, pady=2, sticky="nsew")

        self.reset_gui_btn = tk.Button(
            action_frame, text="Reset GUI", command=self.reset_gui
        )
        self.reset_gui_btn.grid(row=0, column=2, padx=5, pady=2, sticky="nsew")

    def reset_gui(self):
        """Resets the GUI elements to their default state."""
        self.customer_info_label.config(text="Customer:\nNot Selected")
        self.buyer_info_label.config(text="Buyer:\nNot Selected")
        self.rfq_number_text.delete(0, tk.END)

        self.file_path_PR_entry.delete(0, tk.END)
        self.file_type_combo.set("Excel files")

        self.inquiry_date_value.config(text="")
        self.due_date_value.config(text="")

        self.itar_restricted_var.set(False)
        self.party_details = None
        self.files = {
            "Excel files": [],
            "Estimation files": [],
            "Parts Requested Files": [],
            "All Files": [],
        }
        self.update_file_display(None)

    def update_file_display(self, event):
        """
        Updates the file display based on the selected file type.

        :param event: The event object triggered by the user interaction.
        """
        selected_file_type = self.file_type_combo.get()
        self.file_path_PR_entry.delete(0, tk.END)

        if selected_file_type == "All Files":
            self.files["All Files"].clear()
            self.files["All Files"] = sum(  # add all files.
                (
                    file_list
                    for key, file_list in self.files.items()
                    if key != "All Files"
                ),
                [],
            )

        for file in self.files.get(selected_file_type):  # type: ignore
            self.file_path_PR_entry.insert(tk.END, file)

    def open_calendar(self, date_type):
        """
        Opens a calendar popup for selecting a date.

        :param date_type: A string indicating which date field the selection applies to.
        """
        top = tk.Toplevel(self)
        center_window(top, height=300, width=300)
        top.grab_set()
        calendar = Calendar(top, selectmode="day", date_pattern="mm/dd/y")
        calendar.pack(padx=20, pady=20)

        top.bind(
            "<Double-1>", lambda event: self.get_selected_date(calendar, date_type, top)
        )

        btn = tk.Button(
            top,
            text="Get Selected Date",
            command=lambda: self.get_selected_date(calendar, date_type, top),
        )
        btn.pack(pady=10)

    def get_selected_date(self, calendar, date_type, top):
        """
        Retrieves the selected date from the calendar and updates the corresponding field.

        :param calendar: The Calendar widget from which to retrieve the selected date.
        :param date_type: A string indicating whether the selected date is for "inquiry" or "due".
        :param top: The top-level window that contains the calendar, which will be closed after selection.
        """
        selected_date = calendar.get_date()
        if date_type == "inquiry":
            self.inquiry_date_value.config(text=selected_date)
        elif date_type == "due":
            self.due_date_value.config(text=selected_date)

        top.destroy()

    def add_buyer_customer_callback(self, party_details_dict: Dict[str, Any]):
        """
        [TODO:description]

        :param party_details_dict: [TODO:description]
        """
        self.party_details = party_details_dict

        customer_update_text = f"Customer Name: {self.party_details.get('party_name')}\nCustomer Email: {self.party_details.get('party_email')}"
        buyer_update_text = f"Buyer Name: {self.party_details.get('buyer_name')}\nBuyer Email: {self.party_details.get('buyer_email')}"
        self.customer_info_label.config(text=customer_update_text)
        self.buyer_info_label.config(text=buyer_update_text)

    def open_add_buyer_screen(self):
        """
        [TODO:description]
        """
        CustomerSelectionGUI(self.add_buyer_customer_callback)

    def browse_files_parts_requested(self, filepath_dict_key):
        """
        Opens a file dialog for selecting files based on the specified file type key (e.g., "Excel files").
        Validates the selected files to ensure they are not from restricted directories (e.g., "PDM" or "Estimating").
        Displays the selected file names in the Listbox and stores the corresponding full file paths internally.

        :param filepath_dict_key: A key indicating the type of files to be selected (e.g., "Excel files", "Estimation files").
                                 This key is also used to store the selected file paths in the self.files dictionary.
                                 The accepted file types are dynamically adjusted based on this key.
        :type filepath_dict_key: str
        """
        if filepath_dict_key == "All Files":
            messagebox.showerror(
                title="Not Allowed",
                message="Uploading is not allowed in the All Files section.",
            )
            return

        if filepath_dict_key == "Excel files":
            param = (filepath_dict_key, "*.xlsx;*.xls")
        else:
            param = (filepath_dict_key, "*.*")

        try:
            filepaths = filedialog.askopenfilenames(
                title="Select Files", filetypes=(param,)
            )

            if not filepaths:
                return

            invalid_files = [
                path for path in filepaths if "PDM" in path or "Estimating" in path
            ]
            if invalid_files:
                messagebox.showerror(
                    "Error", "Dude! Files from PDM and Estimating can't be uploaded"
                )
                self.file_path_PR_entry.delete(0, tk.END)
                return

            self.file_path_PR_entry.delete(0, tk.END)
            self.files[filepath_dict_key] = []

            for path in filepaths:
                file_name = os.path.basename(path)
                self.file_path_PR_entry.insert(tk.END, file_name)
                self.files[filepath_dict_key].append(path)

        except FileNotFoundError as e:
            print(f"Error during file browse: {e}")
            messagebox.showerror(
                "File Browse Error",
                "An error occurred during file selection. Please try again.",
            )

    # -------------------------------------------------------------------------------------------------------------

    def generate_rfq_with_loading_screen(self):
        """
        [TODO:description]
        """
        self.loading_screen = LoadingScreen(self, max_progress=100)
        center_window(self.loading_screen, width=400, height=75)
        Thread(
            target=self.generate_rfq, args=(self.loading_screen,)
        ).start()  # Start RFQ generation in a separate thread

    @gui_error_handler
    def generate_rfq(self, loading_screen, update_rfq_pk=None):
        """Main function for generating RFQ, adding line items and creating a quote"""

        # TODO: self.cusotmer_select_box.get() should be partypk instead.
        if (
            not self.party_details or not self.files.get("Excel files")
        ):  # checking if user uploaded the part request excel file and selected the customer or not
            self.loading_screen.destroy()
            messagebox.showerror(
                "ERROR", "Select Customer/ Upload Parts Requested File"
            )
            self.reset_gui()
            return

        LOGGER.info("Extracting excel...")
        info_dict: Dict[str, Dict[str, Any]] = create_dict_from_excel_new(
            self.files.get("Excel files", [])[0]
        )

        if not info_dict:
            self.loading_screen.destroy()
            messagebox.showerror("ERROR", "Edit Excel File and try Again")
            self.reset_gui()
            return

        LOGGER.debug(info_dict)

        customer_rfq_number = self.rfq_number_text.get()  # user input

        # Getting current date, inquiry date and due date
        current_date = datetime.date.today()
        current_date_formatted = (
            f"{current_date.strftime('%m-%d-%Y')} 12:00:00 AM" if current_date else None
        )

        inquiry_date = self.inquiry_date_value.cget("text")
        inq_date = f"{inquiry_date} 12:00:00 AM" if inquiry_date else None

        due_date = self.due_date_value.cget("text")
        due_date_formated = f"{due_date} 12:00:00 AM" if due_date else None

        # we are doing this twice, once when the user makes a selection and second time when presses generate
        buyer_fk = self.party_details.get("buyer_pk", None)
        party_pk = self.party_details.get("party_pk")

        address_dict = party.get_party_address(party_pk)
        if update_rfq_pk:
            rfq_pk = update_rfq_pk
        else:  # for new rfqs
            rfq_pk = request_for_quote.insert_into_rfq(
                party_pk,
                address_dict,
                customer_rfq_number=customer_rfq_number,
                buyer_fk=buyer_fk,
                inquiry_date=inq_date,
                due_date=due_date_formated,
                create_date=current_date_formatted,
            )  # creating the rfq with selected customer details

        if not rfq_pk:
            messagebox.showerror(
                title="RFQ error",
                message="RFQ might not be generated, database did not return a value for the insertion. Check last RFQ in MT and regenerate.",
            )
            return None

        LOGGER.info(f"Created RFQ with pk: {rfq_pk}.")

        # dictionary with file path as key and the pk of the document group
        user_selected_file_paths = self.files.get("Parts Requested Files", [])
        estimation_folder_docs = list(
            self.files.get("Estimation files", []) + self.files.get("Excel files", [])
        )
        order_by_counter = 1

        LOGGER.info("Generating FIN, HT, MAT items for parts...")
        part_mat_ht_op_dict = generate_item_pks(info_dict)
        pprint(part_mat_ht_op_dict)

        self.loading_screen.set_progress(20)

        item_pk_dict = {}  # {"PartNumber": ItemPK}
        restricted = False
        quote_pk_dict = {}
        LOGGER.info("Starting loop to insert all parts...")
        for new_key, value in info_dict.items():
            key = (
                new_key.split("_____")[0] if self.ends_with_suffix(new_key) else new_key
            )
            LOGGER.info(f"Processing part: {key}")

            hardware_or_supplies = value.get("hardware_or_supplies", None)
            if (
                not hardware_or_supplies
                or hardware_or_supplies == "Tooling - Manufactured"
            ):  # if main part of tooling.
                # PREPARE DOCUMENTS ------------------------------

                if self.itar_restricted_var.get():  # checking if the user clicked on Restricted box or not and based on that destination path is decided
                    # pass
                    destination_path = rf"y:\PDM\Restricted\{self.party_details.get('party_name')}\{key}"
                    estimation_destinatoin_path = rf"y:\Estimating\Restricted\{self.party_details.get('party_name')}\{self.rfq_number_text.get()}"
                    restricted = True
                else:
                    destination_path = rf"y:\PDM\Non-restricted\{self.party_details.get('party_name')}\{key}"
                    estimation_destinatoin_path = rf"y:\Estimating\Non-restricted\{self.party_details.get('party_name')}\{self.rfq_number_text.get()}"

                path_dict = controller.transfer_and_categorize_files(
                    user_selected_file_paths, destination_path
                )
                estimation_path_dict = controller.transfer_and_categorize_files(
                    estimation_folder_docs, estimation_destinatoin_path
                )

                # Uploading documents to the RFQ with a counter so that the same document is not uploaded more than once
                # UPDATE: Counter removed: function checks if the file is inserted or not.
                for file, pk in estimation_path_dict.items():
                    # TODO; Use the estiamtion folder dict to upload here
                    request_for_quote.upload_documents_to_rfq_or_item(
                        file,
                        rfq_fk=rfq_pk,
                        document_type_fk=6,
                        secure_document=1 if restricted else 0,
                        document_group_pk=pk,
                    )

                # ---------------------------------------------------------

                # searching for the part on MIE Trak and returns the PK, if the part doesn't exist then it creates an item and returns the pk
                item_dict = {
                    "PartNumber": key,
                    "Description": value.get("description", ""),
                    "Purchase": 0,
                    "ServiceItem": 0,
                    "ManufacturedItem": 1,
                    "ItemTypeFK": 7
                    if hardware_or_supplies == "Tooling - Manufactured"
                    else None,
                }
                item_pk = item.get_or_create_item(**item_dict)
                item_pk_dict[key] = item_pk

                # uploading the documents of the item or part
                matching_paths = {
                    path: pk for path, pk in path_dict.items() if key in path
                }
                for url, pk in matching_paths.items():
                    if restricted:
                        request_for_quote.upload_documents_to_rfq_or_item(
                            url,
                            item_fk=item_pk,
                            document_type_fk=2,
                            secure_document=1,
                            document_group_pk=pk,
                        )
                    else:
                        request_for_quote.upload_documents_to_rfq_or_item(
                            url,
                            item_fk=item_pk,
                            document_type_fk=2,
                            document_group_pk=pk,
                        )

                # creating a quote for the Part and getting QuotePk
                quote_pk = quote.create_quote_new(party_pk, item_pk, 0, key)
                quote_pk_dict[key] = quote_pk
                quote.copy_operations_to_quote(quote_pk)

                # Sequence number in Operations for IssueMat, HT, FIN resp
                seq_nums = [6, 21, 22]

                # list of Quote Assembly pk in order MAT, HT, FIN
                quote_assembly_fks = [
                    quote.get_quote_assembly_pk(
                        **{"QuoteFK": quote_pk, "SequenceNumber": x}
                    )
                    for x in seq_nums
                ]

                # creating a Bill of Material for a quote
                mat_ht_fin_pks: tuple = part_mat_ht_op_dict[key]

                for pk, quote_ass_fk, num in zip(
                    mat_ht_fin_pks, quote_assembly_fks, seq_nums
                ):
                    if pk is not None:
                        bom.create_bom_quote(
                            quote_pk,
                            pk,
                            quote_ass_fk,
                            num,
                            order_by_counter,
                            PartLength=value.get("length", ""),
                            PartWidth=value.get("width", ""),
                            Thickness=value.get("thickness", ""),
                        )
                        order_by_counter += 1

                if mat_ht_fin_pks[2]:  # if OP finish is not none
                    op_finish_pk = mat_ht_fin_pks[2]
                    op_part_number = f"{key} - OP Finish"
                    finish_description = value.get("finish_code", "")
                    controller.create_finish_router(
                        finish_description, op_finish_pk, op_part_number
                    )

                # Inserting dimensional and other values to the item table for a part and attaching Document to OP, HT, FIN
                # if key in info_dict:
                item.insert_part_details_in_item(item_pk, key, value)
                pk_value = part_mat_ht_op_dict[key]
                for pk in pk_value[1:]:
                    if pk:
                        item.insert_part_details_in_item(pk, key, value)
                if pk_value[0]:
                    item.insert_part_details_in_item(
                        pk_value[0], key, value, item_type="Material"
                    )

            else:
                # if hardware or tooling then adding it to the BOM of its Assembly part accordingly
                part_num = value.get("assy_for")

                fk = quote_pk_dict.get(part_num)
                if value.get("hardware_or_supplies", "") == "Hardware":
                    quote_assembly_pk = quote.get_quote_assembly_pk(
                        **{"QuoteFK": fk, "SequenceNumber": 24}
                    )
                    item_fk = item.check_and_create_tooling(value.get("description"))
                    bom.create_bom_quote(
                        fk,
                        item_fk,
                        quote_assembly_pk,
                        24,
                        order_by_counter,
                        QuantityRequired=value.get("quantity_required", 1.00),
                    )
                    order_by_counter += 1
                elif value.get("hardware_or_supplies", "") == "Tooling":
                    quote_assembly_pk = quote.get_quote_assembly_pk(
                        "QuoteAssemblyPK", QuoteFK=fk, SequenceNumber=8
                    )
                    item_fk = item.get_or_create_item(
                        **{
                            "PartNumber": key,
                            "Description": value.get("description"),
                            "ItemTypeFK": 7,
                            "MpsItem": 0,
                            "Purchase": 0,
                            "ForecastOnMRP": 0,
                            "MpsOnMRP": 0,
                            "ServiceItem": 0,
                            "ShipLoose": 0,
                            "BulkShip": 0,
                            "CanNotCreateWorkOrder": 1,
                            "CanNotInvoice": 1,
                            "ManufacturedItem": 1,
                        }
                    )
                    bom.create_bom_quote(
                        fk,
                        item_fk,
                        quote_assembly_pk,
                        8,
                        order_by_counter,
                        QuantityRequired=value.get("quantity_required", 1.00),
                    )
                    order_by_counter += 1

        self.loading_screen.set_progress(40)

        controller.create_rfq(
            quote_pk_dict, item_pk_dict, rfq_pk, info_dict
        )  # checking if the Assy or Detail and creating the line item and adding quotes of assembly to the BOM of Assy Line Quotes

        self.loading_screen.set_progress(60)

        for value in quote_pk_dict.values():
            quote.create_quote_assembly_formula_variable(value)

        loading_screen.set_progress(100)
        messagebox.showinfo(
            "Success", f"RFQ generated successfully! RFQ Number: {rfq_pk}"
        )

        self.reset_gui()

    # -------------------------------------------------------------------------------------------------------------

    def update_rfq(self):
        """
        [TODO:description]
        """

        rfq_pk = simpledialog.askstring(
            title="Enter RFQ #", prompt="Enter the RFQ# you would like to update"
        )

        try:
            request_for_quote.reset_rfq(rfq_pk)
        except Exception as e:
            messagebox.showerror(
                title="RFQ could not reset",
                message=f"RFQ {rfq_pk} was not reset due to an error:\n\n{e}",
            )

        loading_screen = LoadingScreen(self, max_progress=100)
        Thread(
            target=self.generate_rfq,
            args=(loading_screen,),
            kwargs={"update_rfq_pk": rfq_pk},
        ).start()

    def ends_with_suffix(self, s):
        return re.search(r"_____\d+$", s) is not None
