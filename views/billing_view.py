"""
billing_view.py
================
Invoicing screen: list of past bills, a "New Bill" workflow that lets
staff add multiple line items (consultation, medicine, test, procedure)
before saving atomically, payment recording, and one-click PDF invoice
generation/export.
"""

from __future__ import annotations

import os
import platform
import subprocess

import customtkinter as ctk

from controllers.billing_controller import BillingController
from controllers.medicine_controller import MedicineController
from controllers.patient_controller import PatientController
from models.billing import Bill, BillItem, VALID_ITEM_TYPES, VALID_PAYMENT_METHODS
from models.user import User
from reports.pdf_generator import generate_invoice_pdf
from utils.helpers import format_currency
from utils.logger import get_logger
from views.widgets.data_table import DataTable
from views.widgets.dialogs import FieldSpec, FormDialog, show_error, show_info

logger = get_logger(__name__)

_COLUMNS = ["Bill No.", "Patient", "Date", "Total", "Status", "Method"]
_COLUMN_WIDTHS = [190, 160, 150, 100, 110, 90]


def _bill_to_row(b: Bill) -> dict:
    return {
        "id": b.id, "Bill No.": b.bill_number, "Patient": b.patient_name,
        "Date": (b.bill_date or "")[:16], "Total": format_currency(b.total_amount),
        "Status": b.payment_status, "Method": b.payment_method or "—",
    }


def _open_file(path) -> None:
    try:
        if platform.system() == "Windows":
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif platform.system() == "Darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
    except Exception as exc:
        logger.info("Could not auto-open file (%s); it was still saved to disk.", exc)


class BillingView(ctk.CTkFrame):

    def __init__(self, master, user: User, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.user = user
        self._pending_items: list[BillItem] = []
        self._build_ui()
        self.refresh()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(20, 8))
        ctk.CTkLabel(header, text="Billing", font=ctk.CTkFont(size=22, weight="bold")).pack(side="left")

        button_bar = ctk.CTkFrame(header, fg_color="transparent")
        button_bar.pack(side="right")
        ctk.CTkButton(button_bar, text="+ New Bill", command=self._open_new_bill_dialog, width=110).pack(side="right", padx=4)
        ctk.CTkButton(button_bar, text="Record Payment", command=self._record_payment, width=130,
                      fg_color="#28B463", hover_color="#1E8449").pack(side="right", padx=4)
        ctk.CTkButton(button_bar, text="Print Invoice (PDF)", command=self._print_invoice, width=150,
                      fg_color="gray50", hover_color="gray40").pack(side="right", padx=4)

        filter_bar = ctk.CTkFrame(self, fg_color="transparent")
        filter_bar.pack(fill="x", padx=24, pady=(0, 10))
        ctk.CTkButton(filter_bar, text="All Bills", width=90, command=self._show_all).pack(side="left", padx=(0, 6))
        ctk.CTkButton(filter_bar, text="Unpaid Only", width=110, command=self._show_unpaid).pack(side="left")
        self.summary_label = ctk.CTkLabel(filter_bar, text="", font=ctk.CTkFont(size=12), text_color=("gray30", "gray70"))
        self.summary_label.pack(side="right")

        table_frame = ctk.CTkFrame(self, fg_color="transparent")
        table_frame.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        self.table = DataTable(table_frame, columns=_COLUMNS, column_widths=_COLUMN_WIDTHS)
        self.table.pack(fill="both", expand=True)

        self._showing_unpaid_only = False

    # ------------------------------------------------------------------
    def on_show(self) -> None:
        self.refresh()

    def _show_all(self) -> None:
        self._showing_unpaid_only = False
        self.refresh()

    def _show_unpaid(self) -> None:
        self._showing_unpaid_only = True
        self.refresh()

    def refresh(self) -> None:
        bills = BillingController.list_unpaid() if self._showing_unpaid_only else BillingController.list_all()
        self.table.load_rows([_bill_to_row(b) for b in bills])
        revenue = BillingController.total_revenue()
        outstanding = BillingController.total_outstanding()
        self.summary_label.configure(
            text=f"Collected: {format_currency(revenue)}   |   Outstanding: {format_currency(outstanding)}"
        )

    def _selected_bill(self) -> Bill | None:
        record = self.table.get_selected()
        if not record:
            show_error("No selection", "Please select a bill first.")
            return None
        return BillingController.get_by_id(record["id"])

    # ------------------------------------------------------------------
    def _record_payment(self) -> None:
        bill = self._selected_bill()
        if not bill:
            return
        fields = [
            FieldSpec("payment_status", "Payment Status", kind="dropdown",
                      options=("Paid", "Partially Paid", "Unpaid", "Refunded"), initial=bill.payment_status),
            FieldSpec("payment_method", "Payment Method", kind="dropdown",
                      options=VALID_PAYMENT_METHODS, initial=bill.payment_method or VALID_PAYMENT_METHODS[0]),
        ]

        def on_submit(values: dict) -> None:
            BillingController.record_payment(bill.id, values["payment_status"], values["payment_method"])
            self.refresh()
            show_info("Payment Recorded", f"Bill {bill.bill_number} marked as {values['payment_status']}.")

        FormDialog(self, f"Record Payment — {bill.bill_number}", fields, on_submit)

    def _print_invoice(self) -> None:
        bill = self._selected_bill()
        if not bill:
            return
        patient = PatientController.get_by_id(bill.patient_id)
        if not patient:
            show_error("Error", "The patient for this bill could not be found.")
            return
        try:
            path = generate_invoice_pdf(bill, patient)
        except Exception as exc:
            show_error("PDF Generation Failed", str(exc))
            return
        show_info("Invoice Generated", f"Saved to:\n{path}")
        _open_file(path)

    # ------------------------------------------------------------------
    # New bill workflow: a dedicated builder window rather than the
    # generic FormDialog, since line items need their own add/remove UI.
    # ------------------------------------------------------------------
    def _open_new_bill_dialog(self) -> None:
        patients = PatientController.list_all()
        if not patients:
            show_error("Cannot Create Bill", "Please register a patient first.")
            return

        self._pending_items = []
        window = ctk.CTkToplevel(self)
        window.title("Create New Bill")
        window.geometry("620x620")
        window.transient(self)
        window.grab_set()

        patient_lookup = {f"{p.full_name} ({p.patient_code})": p.id for p in patients}

        ctk.CTkLabel(window, text="New Bill", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", padx=20, pady=(16, 8))

        top_row = ctk.CTkFrame(window, fg_color="transparent")
        top_row.pack(fill="x", padx=20)
        ctk.CTkLabel(top_row, text="Patient", width=90, anchor="w").pack(side="left")
        patient_var = ctk.StringVar(value=next(iter(patient_lookup)))
        ctk.CTkOptionMenu(top_row, values=list(patient_lookup.keys()), variable=patient_var, width=350).pack(side="left")

        tax_row = ctk.CTkFrame(window, fg_color="transparent")
        tax_row.pack(fill="x", padx=20, pady=(8, 0))
        ctk.CTkLabel(tax_row, text="Tax %", width=90, anchor="w").pack(side="left")
        tax_entry = ctk.CTkEntry(tax_row, width=100)
        tax_entry.insert(0, "5")
        tax_entry.pack(side="left")
        ctk.CTkLabel(tax_row, text="Discount", width=70, anchor="w").pack(side="left", padx=(20, 0))
        discount_entry = ctk.CTkEntry(tax_row, width=100)
        discount_entry.insert(0, "0")
        discount_entry.pack(side="left")

        ctk.CTkLabel(window, text="Line Items", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20, pady=(16, 4))

        items_frame = ctk.CTkScrollableFrame(window, height=200)
        items_frame.pack(fill="both", expand=True, padx=20)

        total_label = ctk.CTkLabel(window, text="Total: $0.00", font=ctk.CTkFont(size=15, weight="bold"))

        def _refresh_items_ui() -> None:
            for child in items_frame.winfo_children():
                child.destroy()
            for idx, item in enumerate(self._pending_items):
                row = ctk.CTkFrame(items_frame, fg_color=("gray90", "gray20"))
                row.pack(fill="x", pady=2)
                ctk.CTkLabel(row, text=f"{item.description}  ×{item.quantity}  @ {format_currency(item.unit_price)}",
                             anchor="w").pack(side="left", padx=8, pady=6, fill="x", expand=True)
                ctk.CTkLabel(row, text=format_currency(item.amount), width=80).pack(side="left")
                ctk.CTkButton(row, text="✕", width=28, fg_color="#C0392B", hover_color="#922B21",
                              command=lambda i=idx: _remove_item(i)).pack(side="left", padx=6)
            subtotal = sum(i.amount for i in self._pending_items)
            total_label.configure(text=f"Subtotal: {format_currency(subtotal)}")

        def _remove_item(index: int) -> None:
            del self._pending_items[index]
            _refresh_items_ui()

        def _add_item() -> None:
            def on_item_submit(values: dict) -> None:
                try:
                    qty = int(values["quantity"])
                    price = float(values["unit_price"])
                except ValueError:
                    raise ValueError("Quantity and unit price must be numeric.")
                item = BillItem(description=values["description"], item_type=values["item_type"],
                                quantity=qty, unit_price=price)
                item.validate()
                self._pending_items.append(item)
                _refresh_items_ui()

            item_fields = [
                FieldSpec("item_type", "Type", kind="dropdown", options=VALID_ITEM_TYPES),
                FieldSpec("description", "Description"),
                FieldSpec("quantity", "Quantity", initial="1"),
                FieldSpec("unit_price", "Unit Price"),
            ]
            FormDialog(window, "Add Line Item", item_fields, on_item_submit)

        def _add_medicine_item() -> None:
            medicines = [m for m in MedicineController.list_all() if m.stock_quantity > 0]
            if not medicines:
                show_error("No Stock Available", "There are no medicines with stock on hand.")
                return
            medicine_lookup = {
                f"{m.name} — {format_currency(m.unit_price)} (Stock: {m.stock_quantity})": m for m in medicines
            }

            def on_medicine_submit(values: dict) -> None:
                try:
                    qty = int(values["quantity"])
                except ValueError:
                    raise ValueError("Quantity must be a whole number.")
                medicine = medicine_lookup[values["medicine"]]
                if qty <= 0:
                    raise ValueError("Quantity must be positive.")
                if qty > medicine.stock_quantity:
                    raise ValueError(f"Only {medicine.stock_quantity} units of {medicine.name} in stock.")
                item = BillItem(description=medicine.name, item_type="Medicine", quantity=qty,
                                unit_price=medicine.unit_price, medicine_id=medicine.id)
                item.validate()
                self._pending_items.append(item)
                _refresh_items_ui()

            medicine_fields = [
                FieldSpec("medicine", "Medicine", kind="dropdown", options=tuple(medicine_lookup.keys())),
                FieldSpec("quantity", "Quantity", initial="1"),
            ]
            FormDialog(window, "Add Medicine from Pharmacy", medicine_fields, on_medicine_submit)

        add_buttons_row = ctk.CTkFrame(window, fg_color="transparent")
        add_buttons_row.pack(anchor="w", padx=20, pady=(8, 0))
        ctk.CTkButton(add_buttons_row, text="+ Add Line Item", command=_add_item, width=160).pack(side="left")
        ctk.CTkButton(add_buttons_row, text="+ Add Medicine", command=_add_medicine_item, width=160,
                      fg_color="#28B463", hover_color="#1E8449").pack(side="left", padx=(8, 0))

        total_label.pack(anchor="e", padx=20, pady=(14, 4))

        error_label = ctk.CTkLabel(window, text="", text_color="#E74C3C")
        error_label.pack()

        def _save_bill() -> None:
            if not self._pending_items:
                error_label.configure(text="Add at least one line item.")
                return
            try:
                tax_percent = float(tax_entry.get() or 0)
                discount = float(discount_entry.get() or 0)
            except ValueError:
                error_label.configure(text="Tax and discount must be numeric.")
                return
            bill = Bill(
                patient_id=patient_lookup[patient_var.get()], items=self._pending_items,
                tax_percent=tax_percent, discount_amount=discount,
            )
            try:
                BillingController.create_bill(bill)
            except Exception as exc:
                error_label.configure(text=str(exc))
                return
            window.destroy()
            self.refresh()
            show_info("Bill Created", f"Bill {bill.bill_number} created — total {format_currency(bill.total_amount)}.")

        btn_row = ctk.CTkFrame(window, fg_color="transparent")
        btn_row.pack(pady=14)
        ctk.CTkButton(btn_row, text="Cancel", width=110, fg_color="gray50",
                      hover_color="gray40", command=window.destroy).pack(side="left", padx=6)
        ctk.CTkButton(btn_row, text="Save Bill", width=110, command=_save_bill).pack(side="left", padx=6)

        _refresh_items_ui()
