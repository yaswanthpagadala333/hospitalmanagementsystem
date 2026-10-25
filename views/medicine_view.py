"""
medicine_view.py
=================
Pharmacy inventory screen: CRUD for medicines, stock adjustment, a
low-stock/expiry alert panel, and the threaded Wikipedia drug-info
lookup (demonstrates BeautifulSoup + requests + threading end-to-end
from the GUI without freezing the interface).
"""

from __future__ import annotations

import customtkinter as ctk

from controllers.medicine_controller import MedicineController
from models.medicine import Medicine
from models.user import User
from scraping.drug_info_scraper import DrugInfoScraper, DrugInfo
from utils.exporter import export_to_csv, export_to_json
from utils.logger import get_logger
from views.widgets.data_table import DataTable
from views.widgets.dialogs import FieldSpec, FormDialog, confirm, show_error, show_info

logger = get_logger(__name__)

_COLUMNS = ["Code", "Name", "Category", "Price", "Stock", "Reorder Lvl", "Expiry"]
_COLUMN_WIDTHS = [90, 190, 130, 80, 70, 90, 100]


def _medicine_to_row(m: Medicine) -> dict:
    return {
        "id": m.id, "Code": m.medicine_code, "Name": m.name, "Category": m.category,
        "Price": f"${m.unit_price:,.2f}", "Stock": m.stock_quantity,
        "Reorder Lvl": m.reorder_level, "Expiry": m.expiry_date or "—",
    }


class MedicineView(ctk.CTkFrame):

    def __init__(self, master, user: User, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.user = user
        self._scraper = DrugInfoScraper()
        self._build_ui()
        self.refresh()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(20, 8))
        ctk.CTkLabel(header, text="Pharmacy Inventory", font=ctk.CTkFont(size=22, weight="bold")).pack(side="left")

        button_bar = ctk.CTkFrame(header, fg_color="transparent")
        button_bar.pack(side="right")
        ctk.CTkButton(button_bar, text="+ New Medicine", command=self._open_add_dialog, width=130).pack(side="right", padx=4)
        ctk.CTkButton(button_bar, text="Delete", command=self._delete_selected, width=90,
                      fg_color="#C0392B", hover_color="#922B21").pack(side="right", padx=4)
        ctk.CTkButton(button_bar, text="Adjust Stock", command=self._open_stock_dialog, width=110,
                      fg_color="gray50", hover_color="gray40").pack(side="right", padx=4)
        ctk.CTkButton(button_bar, text="Drug Info Lookup", command=self._open_lookup_dialog, width=140,
                      fg_color="#8E44AD", hover_color="#6C3483").pack(side="right", padx=4)
        ctk.CTkButton(button_bar, text="Export CSV", command=lambda: self._export("csv"), width=100,
                      fg_color="gray50", hover_color="gray40").pack(side="right", padx=4)

        alert_bar = ctk.CTkFrame(self, fg_color="transparent")
        alert_bar.pack(fill="x", padx=24, pady=(0, 10))
        self.alert_label = ctk.CTkLabel(alert_bar, text="", font=ctk.CTkFont(size=12, weight="bold"), text_color="#C0392B")
        self.alert_label.pack(side="left")

        search_bar = ctk.CTkFrame(self, fg_color="transparent")
        search_bar.pack(fill="x", padx=24, pady=(0, 10))
        self.search_entry = ctk.CTkEntry(search_bar, placeholder_text="Search by name, code or category...", width=380)
        self.search_entry.pack(side="left")
        self.search_entry.bind("<KeyRelease>", lambda _e: self.refresh())

        table_frame = ctk.CTkFrame(self, fg_color="transparent")
        table_frame.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        self.table = DataTable(table_frame, columns=_COLUMNS, column_widths=_COLUMN_WIDTHS,
                               on_double_click=lambda _r: self._open_edit_dialog())
        self.table.pack(fill="both", expand=True)

    # ------------------------------------------------------------------
    def on_show(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        term = self.search_entry.get().strip()
        meds = MedicineController.search(term) if term else MedicineController.list_all()
        self.table.load_rows([_medicine_to_row(m) for m in meds])

        low_stock = MedicineController.low_stock_items()
        expiring = MedicineController.expiring_soon(60)
        parts = []
        if low_stock:
            parts.append(f"⚠ {len(low_stock)} item(s) low on stock")
        if expiring:
            parts.append(f"⏰ {len(expiring)} item(s) expiring within 60 days")
        self.alert_label.configure(text="   ".join(parts))

    def _selected_medicine(self) -> Medicine | None:
        record = self.table.get_selected()
        if not record:
            show_error("No selection", "Please select a medicine first.")
            return None
        return MedicineController.get_by_id(record["id"])

    # ------------------------------------------------------------------
    def _open_add_dialog(self) -> None:
        fields = [
            FieldSpec("name", "Medicine Name"),
            FieldSpec("category", "Category"),
            FieldSpec("manufacturer", "Manufacturer", required=False),
            FieldSpec("unit_price", "Unit Price"),
            FieldSpec("stock_quantity", "Initial Stock", initial="0"),
            FieldSpec("reorder_level", "Reorder Level", initial="20"),
            FieldSpec("batch_number", "Batch Number", required=False),
            FieldSpec("expiry_date", "Expiry Date (YYYY-MM-DD)", required=False),
        ]

        def on_submit(values: dict) -> None:
            try:
                price = float(values["unit_price"])
                stock = int(values["stock_quantity"])
                reorder = int(values["reorder_level"])
            except ValueError:
                raise ValueError("Price, stock and reorder level must be numeric.")
            medicine = Medicine(
                name=values["name"], category=values["category"], manufacturer=values.get("manufacturer") or None,
                unit_price=price, stock_quantity=stock, reorder_level=reorder,
                batch_number=values.get("batch_number") or None, expiry_date=values.get("expiry_date") or None,
            )
            MedicineController.create(medicine)
            self.refresh()
            show_info("Medicine Added", f"{medicine.name} added as {medicine.medicine_code}.")

        FormDialog(self, "Add New Medicine", fields, on_submit)

    def _open_edit_dialog(self) -> None:
        med = self._selected_medicine()
        if not med:
            return
        fields = [
            FieldSpec("name", "Medicine Name", initial=med.name),
            FieldSpec("category", "Category", initial=med.category),
            FieldSpec("manufacturer", "Manufacturer", required=False, initial=med.manufacturer or ""),
            FieldSpec("unit_price", "Unit Price", initial=str(med.unit_price)),
            FieldSpec("reorder_level", "Reorder Level", initial=str(med.reorder_level)),
            FieldSpec("batch_number", "Batch Number", required=False, initial=med.batch_number or ""),
            FieldSpec("expiry_date", "Expiry Date (YYYY-MM-DD)", required=False, initial=med.expiry_date or ""),
        ]

        def on_submit(values: dict) -> None:
            try:
                price = float(values["unit_price"])
                reorder = int(values["reorder_level"])
            except ValueError:
                raise ValueError("Price and reorder level must be numeric.")
            med.name = values["name"]
            med.category = values["category"]
            med.manufacturer = values.get("manufacturer") or None
            med.unit_price = price
            med.reorder_level = reorder
            med.batch_number = values.get("batch_number") or None
            med.expiry_date = values.get("expiry_date") or None
            MedicineController.update(med)
            self.refresh()
            show_info("Medicine Updated", f"{med.name} was updated.")

        FormDialog(self, f"Edit Medicine — {med.medicine_code}", fields, on_submit)

    def _open_stock_dialog(self) -> None:
        med = self._selected_medicine()
        if not med:
            return
        fields = [
            FieldSpec("delta", "Adjustment (+in / -out)", initial="0"),
            FieldSpec("reason", "Reason", required=False),
        ]

        def on_submit(values: dict) -> None:
            try:
                delta = int(values["delta"])
            except ValueError:
                raise ValueError("Adjustment must be a whole number, e.g. 50 or -10.")
            MedicineController.adjust_stock(med.id, delta, values.get("reason") or "")
            self.refresh()
            show_info("Stock Updated", f"{med.name} stock adjusted by {delta:+d}.")

        FormDialog(self, f"Adjust Stock — {med.name} (current: {med.stock_quantity})", fields, on_submit)

    def _delete_selected(self) -> None:
        med = self._selected_medicine()
        if not med:
            return
        if confirm("Delete Medicine", f"Permanently delete {med.name} ({med.medicine_code})? "
                                       f"This cannot be undone."):
            try:
                MedicineController.delete(med.id)
            except Exception as exc:
                show_error("Delete Failed", str(exc))
                return
            self.refresh()
            show_info("Medicine Deleted", f"{med.name} was removed from inventory.")

    def _export(self, fmt: str) -> None:
        meds = MedicineController.list_all()
        if not meds:
            show_error("Nothing to export", "There is no inventory data yet.")
            return
        rows = [m.to_dict() for m in meds]
        try:
            path = export_to_csv(rows, "medicines") if fmt == "csv" else export_to_json(rows, "medicines")
        except Exception as exc:
            show_error("Export Failed", str(exc))
            return
        show_info("Export Complete", f"Exported {len(rows)} medicines to:\n{path}")

    # ------------------------------------------------------------------
    # Drug information lookup (threaded network call)
    # ------------------------------------------------------------------
    def _open_lookup_dialog(self) -> None:
        window = ctk.CTkToplevel(self)
        window.title("Drug Information Lookup")
        window.geometry("480x420")
        window.transient(self)
        window.grab_set()

        ctk.CTkLabel(window, text="Drug Information Lookup", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(16, 4), padx=20, anchor="w")
        ctk.CTkLabel(window, text="Looks up a public reference summary (source: Wikipedia).",
                     font=ctk.CTkFont(size=11), text_color=("gray40", "gray60")).pack(padx=20, anchor="w")

        entry_row = ctk.CTkFrame(window, fg_color="transparent")
        entry_row.pack(fill="x", padx=20, pady=(12, 4))
        search_entry = ctk.CTkEntry(entry_row, placeholder_text="e.g. Amoxicillin", width=280)
        search_entry.pack(side="left")
        selected_med = self._selected_medicine()
        if selected_med:
            search_entry.insert(0, selected_med.name.split()[0])

        status_label = ctk.CTkLabel(window, text="", font=ctk.CTkFont(size=11), text_color=("gray40", "gray60"))
        status_label.pack(padx=20, anchor="w")

        result_box = ctk.CTkTextbox(window, height=220, wrap="word")
        result_box.pack(fill="both", expand=True, padx=20, pady=(8, 8))
        result_box.configure(state="disabled")

        search_button = ctk.CTkButton(entry_row, text="Search", width=90)
        search_button.pack(side="left", padx=8)

        def _set_result_text(text: str) -> None:
            result_box.configure(state="normal")
            result_box.delete("1.0", "end")
            result_box.insert("1.0", text)
            result_box.configure(state="disabled")

        def _on_success(info: DrugInfo) -> None:
            def _apply() -> None:
                cache_note = " (from cache)" if info.from_cache else ""
                status_label.configure(text=f"Source: {info.source_url}{cache_note}")
                body = f"{info.title}\n\n"
                if info.drug_class:
                    body += f"Drug class: {info.drug_class}\n\n"
                body += info.summary
                _set_result_text(body)
                search_button.configure(state="normal", text="Search")
            if window.winfo_exists():
                window.after(0, _apply)

        def _on_error(exc: Exception) -> None:
            def _apply() -> None:
                status_label.configure(text="")
                _set_result_text(f"Lookup failed: {exc}\n\n"
                                  f"(This requires internet access to en.wikipedia.org.)")
                search_button.configure(state="normal", text="Search")
            if window.winfo_exists():
                window.after(0, _apply)

        def _run_search() -> None:
            term = search_entry.get().strip()
            if not term:
                return
            search_button.configure(state="disabled", text="Searching...")
            status_label.configure(text="Looking up reference information...")
            _set_result_text("")
            self._scraper.fetch_async(term, on_success=_on_success, on_error=_on_error)

        search_button.configure(command=_run_search)
        search_entry.bind("<Return>", lambda _e: _run_search())
