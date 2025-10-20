"""
eCourts Cause List Downloader (PyQt5 GUI + Selenium)
-----------------------------------------------------

A GUI application to fetch and save District Court Cause Lists as PDF
from the official eCourts website.

Features:
    ✅ Interactive GUI using PyQt5
    ✅ Uses Selenium to control the eCourts website
    ✅ Automatically loads states, districts, complexes, etc.
    ✅ Captcha image display for manual input
    ✅ Generates formatted PDF cause lists using ReportLab

Usage:
    1. Install dependencies:
        pip install pyqt5 selenium webdriver-manager reportlab
    2. Run the script:
        python ecourts_pyqt_cause_list_ui.py
    3. Follow GUI prompts:
        - Load State → District → Complex → Establishment → Court
        - Enter captcha, choose date and type (Civil/Criminal)
        - Click “Fetch Cause List & Save PDF”

Author: Utkarsh Vats
"""

import sys
import time
import re
from datetime import date

# ------------------------ PyQt5 Imports ------------------------
from PyQt5 import QtWidgets, QtGui, QtCore

# ------------------------ Selenium Imports ------------------------
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ------------------------ PDF Tools (ReportLab) ------------------------
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch


# ======================================================================
#                               PDF CREATOR
# ======================================================================
def save_cause_list_pdf(data, output_path="Cause_List.pdf"):
    """
    Generate a neatly formatted PDF file from the scraped cause list table.

    Args:
        data (list[list[str]]): Table data (first row as headers)
        output_path (str): Output PDF filename
    """
    print(f"[PDF] Generating: {output_path}")
    pdf = SimpleDocTemplate(
        output_path,
        pagesize=landscape(A4),
        rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30,
    )
    styles = getSampleStyleSheet()
    normal_style = ParagraphStyle(
        'Wrapped',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=11,
        wordWrap='CJK'
    )

    # Add title
    elements = [Paragraph("<b>District Court Cause List</b>", styles['Title']), Spacer(1, 12)]

    # Wrap cells for text overflow
    wrapped_data = []
    for i, row in enumerate(data):
        wrapped_row = [
            Paragraph(f"<b>{c}</b>", normal_style) if i == 0 else Paragraph(str(c), normal_style)
            for c in row
        ]
        wrapped_data.append(wrapped_row)

    # Table formatting
    table = Table(wrapped_data, colWidths=[0.6 * inch, 3.2 * inch, 3.5 * inch, 2.8 * inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#003366")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f3f3f3")]),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))

    elements.append(table)
    pdf.build(elements)
    print(f"[PDF] Saved successfully: {output_path}")


# ======================================================================
#                           SELENIUM CONTROLLER
# ======================================================================
class SeleniumManager:
    """Handles all Selenium browser automation for eCourts site."""

    def __init__(self):
        opts = Options()
        # opts.add_argument("--headless")  # Uncomment to run headless
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")

        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
        self.wait = WebDriverWait(self.driver, 15)

    def open_cause_list_page(self):
        """Navigate to the eCourts cause list page."""
        self.driver.get("https://services.ecourts.gov.in/ecourtindia_v6/?p=cause_list/index")

    def get_select_options(self, select_css_selector):
        """Return (value, text) pairs from a <select> element."""
        try:
            el = self.driver.find_element(By.CSS_SELECTOR, select_css_selector)
            opts = el.find_elements(By.TAG_NAME, "option")
            return [(o.get_attribute("value"), o.text.strip()) for o in opts if o.get_attribute("value")]
        except Exception as e:
            print(f"[Error] get_select_options {select_css_selector}: {e}")
            return []

    def set_select_by_value(self, select_css_selector, value):
        """Set a dropdown selection by value."""
        try:
            el = self.driver.find_element(By.CSS_SELECTOR, select_css_selector)
            if not el.is_displayed():
                print(f"[Skip] {select_css_selector} hidden.")
                return False
            Select(el).select_by_value(value)
            time.sleep(0.3)
            return True
        except Exception as e:
            print(f"[Error] set_select_by_value {select_css_selector} = {value}: {e}")
            try:
                alert = self.driver.switch_to.alert
                print(f"Alert detected: {alert.text}")
                alert.accept()
            except Exception:
                pass
            return False

    def find_captcha_element(self):
        """Locate the captcha image element."""
        candidates = [
            "//img[@id='captcha_image']",
            "//img[contains(@src,'captcha')]",
            "//img[contains(@id,'captcha')]"
        ]
        for xp in candidates:
            try:
                return self.driver.find_element(By.XPATH, xp)
            except Exception:
                continue
        return None

    def screenshot_element_png(self, element):
        """Return PNG bytes for an element screenshot."""
        return element.screenshot_as_png

    def set_captcha_and_submit(self, captcha_value, cause_type="civ"):
        """Fill captcha, close modals if any, and click submit button."""
        try:
            # Fill captcha
            for cid in ["cause_list_captcha_code", "captcha", "txtCaptcha"]:
                try:
                    inp = self.driver.find_element(By.ID, cid)
                    inp.clear()
                    inp.send_keys(captcha_value)
                    break
                except Exception:
                    continue

            # Click button
            btn_xpath = f"//button[contains(@onclick, \"submit_causelist('{cause_type}')\")]"
            btn = self.driver.find_element(By.XPATH, btn_xpath)
            self.driver.execute_script("arguments[0].scrollIntoView(true);", btn)
            time.sleep(0.3)
            btn.click()
            return True
        except Exception as e:
            print(f"[Error] set_captcha_and_submit: {e}")
            return False

    def wait_for_table(self, table_id="dispTable", timeout=15):
        """Wait until the result table appears."""
        try:
            self.wait.until(EC.presence_of_element_located((By.ID, table_id)))
            return True
        except Exception:
            return False

    def scrape_table_dispTable(self):
        """Scrape the main cause list table into a Python list."""
        try:
            table = self.driver.find_element(By.ID, "dispTable")
            rows = table.find_elements(By.TAG_NAME, "tr")
        except Exception as e:
            print(f"[Error] scrape_table_dispTable: {e}")
            return []

        data = [["Sr No", "Case Info", "Party Name", "Advocate"]]
        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) < 4 or any(td.get_attribute("colspan") for td in cols):
                continue
            sr_no = cols[0].text.strip()
            case_text = re.sub(r"\s{2,}", " ", cols[1].text.strip())
            data.append([
                sr_no,
                case_text.replace("View", "").strip(),
                cols[2].text.strip(),
                cols[3].text.strip(),
            ])
        return data


# ======================================================================
#                           WORKER THREAD (QThread)
# ======================================================================
class WorkerThread(QtCore.QThread):
    """Runs Selenium actions without freezing the PyQt UI."""
    finished_signal = QtCore.pyqtSignal(object, str)

    def __init__(self, manager: SeleniumManager, action: str, params: dict):
        super().__init__()
        self.manager = manager
        self.action = action
        self.params = params

    def run(self):
        try:
            if self.action == "load_states":
                opts = self.manager.get_select_options("#sess_state_code")
                self.finished_signal.emit(opts, "states_loaded")
                return

            if self.action == "load_districts":
                val = self.params.get("state_val")
                self.manager.set_select_by_value("#sess_state_code", val)
                opts = self.manager.get_select_options("#sess_dist_code")
                self.finished_signal.emit(opts, "districts_loaded")
                return

            if self.action == "load_complexes":
                val = self.params.get("district_val")
                self.manager.set_select_by_value("#sess_dist_code", val)
                opts = self.manager.get_select_options("#court_complex_code")
                self.finished_signal.emit(opts, "complexes_loaded")
                return

            if self.action == "load_establishments":
                val = self.params.get("complex_val")
                self.manager.set_select_by_value("#court_complex_code", val)
                opts = self.manager.get_select_options("#court_est_code")
                self.finished_signal.emit(opts, "establishments_loaded")
                return

            if self.action == "load_courts":
                est_val = self.params.get("est_val")
                complex_val = self.params.get("complex_val")
                if est_val:
                    self.manager.set_select_by_value("#court_est_code", est_val)
                elif complex_val:
                    self.manager.set_select_by_value("#court_complex_code", complex_val)
                opts = self.manager.get_select_options("#CL_court_no")
                self.finished_signal.emit(opts, "courts_loaded")
                return

            if self.action == "get_captcha":
                el = self.manager.find_captcha_element()
                if not el:
                    self.finished_signal.emit(None, "captcha_not_found")
                    return
                png = self.manager.screenshot_element_png(el)
                self.finished_signal.emit(png, "captcha_image")
                return

            if self.action == "fetch_causelist":
                # --- Dropdown selection sequence ---
                sequence = [
                    ("#sess_state_code", self.params.get("state_val")),
                    ("#sess_dist_code", self.params.get("dist_val")),
                    ("#court_complex_code", self.params.get("complex_val")),
                    ("#court_est_code", self.params.get("est_val")),
                    ("#CL_court_no", self.params.get("court_val")),
                ]
                for sel, val in sequence:
                    if val:
                        try:
                            Select(self.manager.driver.find_element(By.CSS_SELECTOR, sel)).select_by_value(val)
                            time.sleep(0.3)
                        except Exception:
                            continue

                # --- Date setting ---
                try:
                    date_str = self.params.get("date_str")
                    date_input = self.manager.driver.find_element(By.ID, "causelist_date")
                    self.manager.driver.execute_script("arguments[0].scrollIntoView(true);", date_input)
                    date_input.click()
                    date_input.clear()
                    date_input.send_keys(date_str)
                    self.manager.driver.execute_script(
                        "arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", date_input
                    )
                except Exception as e:
                    print(f"[Error] Setting date: {e}")

                # --- Captcha + Submit ---
                captcha_val = self.params.get("captcha_text")
                cause_type = (self.params.get("cause_type") or "civ").strip().lower()
                if not self.manager.set_captcha_and_submit(captcha_val, cause_type):
                    self.finished_signal.emit(None, "submit_failed")
                    return

                if not self.manager.wait_for_table("dispTable", 25):
                    self.finished_signal.emit(None, "table_not_found")
                    return

                # --- Scrape + Save PDF ---
                data = self.manager.scrape_table_dispTable()
                filename = f"Cause_List_{date.today():%Y-%m-%d}.pdf"
                save_cause_list_pdf(data, filename)
                self.finished_signal.emit(filename, "done")

        except Exception as e:
            self.finished_signal.emit(None, f"error:{e}")


# ======================================================================
#                           MAIN WINDOW (PyQt5)
# ======================================================================
class MainWindow(QtWidgets.QWidget):
    """Main GUI window for eCourts Cause List Fetcher."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("eCourts Cause List - GUI")
        self.setGeometry(200, 200, 980, 600)

        self.manager = SeleniumManager()
        self.manager.open_cause_list_page()
        self._last_worker = None
        self.init_ui()

    def init_ui(self):
        """Create and arrange GUI widgets."""
        layout = QtWidgets.QVBoxLayout(self)
        grid = QtWidgets.QGridLayout()
        row = 0

        # --- Controls ---
        def add_label(text):
            grid.addWidget(QtWidgets.QLabel(text), row, len(grid.rowCount()))

        # Row 1: State / District
        self.load_states_btn = QtWidgets.QPushButton("Load States")
        self.load_states_btn.clicked.connect(self.load_states)
        grid.addWidget(self.load_states_btn, row, 0)
        self.state_cb = QtWidgets.QComboBox()
        grid.addWidget(QtWidgets.QLabel("State:"), row, 1)
        grid.addWidget(self.state_cb, row, 2)

        self.load_districts_btn = QtWidgets.QPushButton("Load Districts")
        self.load_districts_btn.clicked.connect(self.load_districts)
        grid.addWidget(self.load_districts_btn, row, 3)
        self.dist_cb = QtWidgets.QComboBox()
        grid.addWidget(QtWidgets.QLabel("District:"), row, 4)
        grid.addWidget(self.dist_cb, row, 5)

        # Row 2: Complex / Establishment
        row += 1
        self.load_complex_btn = QtWidgets.QPushButton("Load Complexes")
        self.load_complex_btn.clicked.connect(self.load_complexes)
        grid.addWidget(self.load_complex_btn, row, 0)
        self.complex_cb = QtWidgets.QComboBox()
        grid.addWidget(QtWidgets.QLabel("Complex:"), row, 1)
        grid.addWidget(self.complex_cb, row, 2)

        self.load_est_btn = QtWidgets.QPushButton("Load Establishments")
        self.load_est_btn.clicked.connect(self.load_establishments)
        grid.addWidget(self.load_est_btn, row, 3)
        self.est_cb = QtWidgets.QComboBox()
        grid.addWidget(QtWidgets.QLabel("Establishment:"), row, 4)
        grid.addWidget(self.est_cb, row, 5)

        # Row 3: Court / Date
        row += 1
        self.load_court_btn = QtWidgets.QPushButton("Load Courts")
        self.load_court_btn.clicked.connect(self.load_courts)
        grid.addWidget(self.load_court_btn, row, 0)
        self.court_cb = QtWidgets.QComboBox()
        grid.addWidget(QtWidgets.QLabel("Court Name:"), row, 1)
        grid.addWidget(self.court_cb, row, 2)

        self.date_edit = QtWidgets.QDateEdit(QtCore.QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        grid.addWidget(QtWidgets.QLabel("Cause List Date:"), row, 3)
        grid.addWidget(self.date_edit, row, 4)

        # Row 4: Captcha and Cause Type
        row += 1
        self.cause_type_cb = QtWidgets.QComboBox()
        self.cause_type_cb.addItem("Civil", "civ")
        self.cause_type_cb.addItem("Criminal", "cri")
        grid.addWidget(QtWidgets.QLabel("Cause Type:"), row, 0)
        grid.addWidget(self.cause_type_cb, row, 1)

        self.captcha_lbl = QtWidgets.QLabel()
        self.captcha_lbl.setFixedSize(220, 80)
        self.captcha_lbl.setStyleSheet("border: 1px solid #444;")
        grid.addWidget(QtWidgets.QLabel("Captcha:"), row, 2)
        grid.addWidget(self.captcha_lbl, row, 3)

        self.refresh_captcha_btn = QtWidgets.QPushButton("Refresh Captcha")
        self.refresh_captcha_btn.clicked.connect(self.load_captcha)
        grid.addWidget(self.refresh_captcha_btn, row, 4)
        self.captcha_input = QtWidgets.QLineEdit()
        grid.addWidget(self.captcha_input, row, 5)

        # Row 5: Fetch Button
        row += 1
        self.fetch_btn = QtWidgets.QPushButton("Fetch Cause List & Save PDF")
        self.fetch_btn.clicked.connect(self.fetch_causelist)
        grid.addWidget(self.fetch_btn, row, 5)

        layout.addLayout(grid)

        # Log Box
        self.log = QtWidgets.QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)
        self.setLayout(layout)

        # Load captcha initially
        QtCore.QTimer.singleShot(1000, self.load_captcha)

    # ------------------------------------------------------------------
    #                            HELPER METHODS
    # ------------------------------------------------------------------
    def log_msg(self, msg):
        """Append message to GUI log box."""
        self.log.append(msg)
        print(msg)

    def _selected_value(self, cb):
        """Return the selected value of a ComboBox."""
        idx = cb.currentIndex()
        return cb.itemData(idx) if idx >= 0 else None

    # ------------------------------------------------------------------
    #                            LOADERS
    # ------------------------------------------------------------------
    def load_states(self):
        self.log_msg("Loading states...")
        self.run_thread("load_states", {})

    def load_districts(self):
        state_val = self._selected_value(self.state_cb)
        if not state_val:
            return self.log_msg("Select a state first.")
        self.log_msg("Loading districts...")
        self.run_thread("load_districts", {"state_val": state_val})

    def load_complexes(self):
        dist_val = self._selected_value(self.dist_cb)
        if not dist_val:
            return self.log_msg("Select a district first.")
        self.log_msg("Loading complexes...")
        self.run_thread("load_complexes", {"district_val": dist_val})

    def load_establishments(self):
        complex_val = self._selected_value(self.complex_cb)
        if not complex_val:
            return self.log_msg("Select a court complex first.")
        self.log_msg("Loading establishments...")
        self.run_thread("load_establishments", {"complex_val": complex_val})

    def load_courts(self):
        est_val = self._selected_value(self.est_cb)
        complex_val = self._selected_value(self.complex_cb)
        if not (est_val or complex_val):
            return self.log_msg("Select an establishment or complex first.")
        self.log_msg("Loading courts...")
        self.run_thread("load_courts", {"est_val": est_val, "complex_val": complex_val})

    def load_captcha(self):
        self.log_msg("Fetching captcha image...")
        self.run_thread("get_captcha", {})

    # ------------------------------------------------------------------
    #                            MAIN ACTION
    # ------------------------------------------------------------------
    def fetch_causelist(self):
        """Start the cause list fetching sequence."""
        params = {
            "state_val": self._selected_value(self.state_cb),
            "dist_val": self._selected_value(self.dist_cb),
            "complex_val": self._selected_value(self.complex_cb),
            "est_val": self._selected_value(self.est_cb),
            "court_val": self._selected_value(self.court_cb),
            "date_str": self.date_edit.date().toString("dd-MM-yyyy"),
            "captcha_text": self.captcha_input.text().strip(),
            "cause_type": self._selected_value(self.cause_type_cb),
        }
        if not params["captcha_text"]:
            return self.log_msg("Please enter captcha before fetching.")
        self.log_msg("Fetching cause list (this may take a few seconds)...")
        self.run_thread("fetch_causelist", params)

    # ------------------------------------------------------------------
    def run_thread(self, action, params):
        """Run Selenium actions in a background thread."""
        worker = WorkerThread(self.manager, action, params)
        self._last_worker = worker
        worker.finished_signal.connect(self.on_worker_finished)
        worker.start()

    # ------------------------------------------------------------------
    def on_worker_finished(self, payload, tag):
        """Handle results from background worker threads."""
        mapping = {
            "states_loaded": (self.state_cb, "States loaded."),
            "districts_loaded": (self.dist_cb, "Districts loaded."),
            "complexes_loaded": (self.complex_cb, "Complexes loaded."),
            "establishments_loaded": (self.est_cb, "Establishments loaded."),
            "courts_loaded": (self.court_cb, "Courts loaded."),
        }

        if tag in mapping:
            cb, msg = mapping[tag]
            cb.clear()
            for val, txt in payload:
                cb.addItem(txt, val)
            self.log_msg(msg)
        elif tag == "captcha_image":
            if not payload:
                return self.log_msg("Captcha not found.")
            pix = QtGui.QPixmap()
            pix.loadFromData(payload)
            scaled = pix.scaled(self.captcha_lbl.size(), QtCore.Qt.KeepAspectRatio)
            self.captcha_lbl.setPixmap(scaled)
            self.log_msg("Captcha loaded. Enter it below.")
        elif tag == "submit_failed":
            self.log_msg("Failed to submit form (captcha or button issue).")
        elif tag == "table_not_found":
            self.log_msg("Cause list table not found after submission.")
        elif tag == "done":
            self.log_msg(f"Done. PDF saved as {payload}")
        elif tag.startswith("error:"):
            self.log_msg(f"Error occurred: {tag}")
        else:
            self.log_msg(f"Unknown result: {tag}")


# ======================================================================
#                                 MAIN
# ======================================================================
def main():
    """Application entry point."""
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
