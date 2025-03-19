import tkinter as tk
from tkinter import StringVar, Listbox, Scrollbar
from tkinter import messagebox
from typing import Callable, Dict
from mie_trak_api import party
from src.gui.utils import gui_error_handler, center_window
from base_logger import getlogger


LOGGER = getlogger("Cust Selection")


class CustomerSelectionGUI(tk.Toplevel):
    def __init__(self, callback: Callable):
        super().__init__()

        self.callback = callback  # Function to update GUI once selection is made.
        self.party_data: Dict[int, str] = party.get_all_party_data()
        self.party_display_data = (
            self.party_data
        )  # we keep a copy to update when the user searches.

        self.title("Customer Selection")
        self.geometry("500x350")

        self.create_widgets()
        center_window(self, height=750, width=1000)

    def create_widgets(self):
        tk.Label(
            self, text="Customer and Buyer Selection", font=("Segoe UI", 14, "bold")
        ).pack(pady=5)

        # Frame for layout
        frame = tk.Frame(self)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Party Section (Left)
        party_frame = tk.Frame(frame)
        party_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        tk.Label(party_frame, text="Search Party:", font=("Segoe UI", 10)).pack(
            anchor="w"
        )
        self.party_search_var = StringVar()
        party_search_entry = tk.Entry(
            party_frame, textvariable=self.party_search_var, font=("Segoe UI", 10)
        )
        party_search_entry.pack(fill=tk.X, padx=5, pady=2)
        party_search_entry.bind("<KeyRelease>", self.update_party_listbox)

        tk.Label(party_frame, text="Parties", font=("Segoe UI", 10, "bold")).pack()

        self.party_listbox = Listbox(
            party_frame, font=("Segoe UI", 10), exportselection=0
        )
        self.party_listbox.pack(fill=tk.BOTH, expand=True)

        self.party_listbox.bind("<<ListboxSelect>>", self.update_buyer_listbox)

        # Buyer Section (Right)
        buyer_frame = tk.Frame(frame)
        buyer_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)

        tk.Label(buyer_frame, text="Search Buyer:", font=("Segoe UI", 10)).pack(
            anchor="w"
        )
        self.buyer_search_var = StringVar()
        buyer_search_entry = tk.Entry(
            buyer_frame, textvariable=self.buyer_search_var, font=("Segoe UI", 10)
        )
        buyer_search_entry.pack(fill=tk.X, padx=5, pady=2)
        buyer_search_entry.bind("<KeyRelease>", self.update_buyer_listbox_search)

        tk.Label(buyer_frame, text="Buyers", font=("Segoe UI", 10, "bold")).pack()

        self.buyer_listbox = Listbox(buyer_frame, font=("Segoe UI", 10))
        self.buyer_listbox.pack(fill=tk.BOTH, expand=True)

        confirm_button = tk.Button(
            self,
            text="Confirm Selection",
            font=("Segoe UI", 10, "bold"),
            command=self.confirm_selection,
        )
        confirm_button.pack(pady=10)

        # Populate initial party list
        self.update_party_listbox()

    def update_party_listbox(self, event=None):
        """Updates the party listbox based on the search input."""
        self.party_display_data = {}  # reset the display data
        search_term = self.party_search_var.get().lower()
        self.party_listbox.delete(0, tk.END)

        for party_id, party_name in self.party_data.items():
            if search_term in party_name.lower():
                self.party_display_data[party_id] = (
                    party_name  # update the display data
                )
                self.party_listbox.insert(tk.END, party_name)

    def update_buyer_listbox(self, event):
        """Updates the buyer listbox based on selected party."""
        selection = self.party_listbox.curselection()
        if not selection:
            return
        selected_party_pk = list(self.party_display_data.keys())[selection[0]]

        try:
            self.buyers = party.get_all_buyers_for_party(selected_party_pk)
            self.buyer_display_data = self.buyers
        except ValueError as e:
            LOGGER.error(e)
            self.buyer_display_data = {}

        self.buyer_listbox.delete(0, tk.END)

        for _, buyer_name in self.buyer_display_data.items():
            self.buyer_listbox.insert(tk.END, buyer_name)

    def update_buyer_listbox_search(self, event=None):
        """Filters the buyer listbox based on the search input."""
        self.buyer_display_data = {}
        search_term = self.buyer_search_var.get().lower()

        self.buyer_listbox.delete(0, tk.END)

        for buyer_id, buyer_name in self.buyers.items():
            if search_term in buyer_name.lower():
                self.buyer_display_data[buyer_id] = buyer_name
                self.buyer_listbox.insert(tk.END, buyer_name)

    @gui_error_handler
    def confirm_selection(self):
        """Callback function when the confirm button is clicked."""
        selected_party_idx = self.party_listbox.curselection()
        selected_buyer_idx = self.buyer_listbox.curselection()

        if not selected_party_idx:
            messagebox.showerror(
                title="Customer selection error",
                message="Please select a customer before proceeding or close the window by clicking the cross on the top right.",
            )
            return

        party_pk = list(self.party_display_data.keys())[selected_party_idx[0]]
        party_short_name, party_email = party.get_party_shortname_email(party_pk)
        party_data = {
            "party_pk": party_pk,
            "party_email": party_email,
            "party_name": self.party_display_data.get(party_pk),
        }

        if selected_buyer_idx:
            buyer_pk = list(self.buyer_display_data.keys())[selected_buyer_idx[0]]
            buyer_short_name, buyer_email = party.get_party_shortname_email(buyer_pk)
            party_data["buyer_pk"] = buyer_pk
            party_data["buyer_name"] = buyer_short_name
            party_data["buyer_email"] = buyer_email

        self.callback(party_data)
        self.destroy()


# TODO: add this in the customer/buyer selection GUI

# class AddBuyerScreen(tk.Toplevel):
#     """Display window when user tries to add a buyer"""
#
#     def __init__(self, master, party_pk, party_name):
#         super().__init__(master)
#         self.title(f"Add Buyer for Customer: {party_name}, PartyPK: {party_pk}")
#         self.geometry("500x300")
#         self.attributes("-topmost", True)
#         self.grab_set()
#         tk.Label(self, text="Name: ").grid(row=0, column=0)
#         self.buyer_name_box = tk.Entry(self, width=20)
#         self.buyer_name_box.grid(row=0, column=1)
#         tk.Label(self, text="Short Name: ").grid(row=1, column=0)
#         self.short_name_box = tk.Entry(self, width=20)
#         self.short_name_box.grid(row=1, column=1)
#         tk.Label(self, text="Email: ").grid(row=2, column=0)
#         self.email_id_box = tk.Entry(self, width=20)
#         self.email_id_box.grid(row=2, column=1)
#         tk.Label(self, text="Phone Number: ").grid(row=3, column=0)
#         self.phone_number_box = tk.Entry(self, width=20)
#         self.phone_number_box.grid(row=3, column=1)
#         tk.Label(self, text="Title: ").grid(row=4, column=0)
#         self.title_box = tk.Entry(self, width=20)
#         self.title_box.grid(row=4, column=1)
#         save_button = tk.Button(
#             self, text="Save", command=lambda: self.save_buyer_info(party_pk)
#         )
#         save_button.grid(row=5, column=1)
#
#     def save_buyer_info(self, party_pk):
#         """Inserts the buyers data in the database"""
#         if self.buyer_name_box.get():
#             buyer_info_dict = {
#                 "Name": self.buyer_name_box.get(),
#                 "Email": self.email_id_box.get(),
#                 "Phone": self.phone_number_box.get(),
#                 "ShortName": self.short_name_box.get(),
#                 "Title": self.title_box.get(),
#                 "Buyer": 1,
#                 "HardwareCertificationFK": 1,
#                 "MaterialCertificationFK": 1,
#                 "OutsideProcessingCertificationFK": 1,
#                 "QualityLevelFK": 2,
#                 "KeepDocumentOnFile": 1,
#                 "FirstArticleFK": 1,
#             }
#             buyer_pk = MieTrak().create_buyer(buyer_info_dict, party_pk)
#             messagebox.showinfo(
#                 "Success", f"Buyer created successfully! BuyerPK: {buyer_pk}"
#             )
#             self.master.update_buyer_combobox()  # TODO: this should be a callback
#             self.destroy()
#         else:
#             messagebox.showerror("ERROR", "Please Enter Name")
