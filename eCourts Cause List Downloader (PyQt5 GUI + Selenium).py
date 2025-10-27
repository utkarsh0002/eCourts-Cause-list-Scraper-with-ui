"""
eCourts Cause List Scraper (Manual Captcha)
-------------------------------------------
Scrapes district court cause list data case-by-case from the eCourts portal
and exports it as a clean, formatted PDF file.

WORKFLOW:
1. Opens the eCourts "Cause List" page in a browser.
2. User manually selects State, District, Court, Date, and fills captcha.
3. After the table loads, user presses Enter in the console.
4. Script extracts all visible rows from the table, ignoring section headers.
5. Results are saved as a structured, styled PDF.

REQUIREMENTS:
    pip install selenium webdriver-manager reportlab

Author: Utkarsh Vats
Date: 15-10-2025
"""

# ------------------------ Imports ------------------------

import sys
import time
import re
from datetime import date
from io import BytesIO

from PyQt5 import QtWidgets, QtGui, QtCore

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# PDF tools (reportlab)
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

# =========================================================
#                   PDF GENERATION FUNCTION
# =========================================================

def save_cause_list_pdf(data, output_path="Cause_List.pdf"):
    print("PDF: building", output_path)
    pdf = SimpleDocTemplate(
        output_path,
        pagesize=landscape(A4),
        rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30
    )
    styles = getSampleStyleSheet()
    normal_style = ParagraphStyle(
        'Wrapped', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=11, wordWrap='CJK'
    )

    title = Paragraph("<b>District Court Cause List</b>", styles['Title'])
    elements = [title, Spacer(1, 12)]

    wrapped_data = []
    for row_index, row in enumerate(data):
        wrapped_row = []
        for cell in row:
            if row_index == 0:
                wrapped_row.append(Paragraph(f"<b>{cell}</b>", normal_style))
            else:
                wrapped_row.append(Paragraph(str(cell), normal_style))
        wrapped_data.append(wrapped_row)

    table = Table(wrapped_data, colWidths=[0.6 * inch, 3.2 * inch, 3.5 * inch, 2.8 * inch])
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#003366")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f3f3")]),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ])
    table.setStyle(style)
    elements.append(table)
    pdf.build(elements)
    print("PDF: saved", output_path)

# =========================================================
#                   SELENIUM SCRAPER
# =========================================================

class SeleniumManager:
    def __init__(self):
        print('1 - SeleniumManager.__init__')
        opts = Options()
        # headful so user can interact and see captcha; remove comment to run headless (not recommended for captcha)
        # opts.add_argument("--headless")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
        self.wait = WebDriverWait(self.driver, 15)

    def open_cause_list_page(self):
        print('2 - open_cause_list_page')
        self.driver.get("https://services.ecourts.gov.in/ecourtindia_v6/?p=cause_list/index")

    def get_select_options(self, select_css_selector):
        """Return list of tuples (value, text) for options in a <select> given CSS selector."""
        print('3 - get_select_options for', select_css_selector)
        try:
            el = self.driver.find_element(By.CSS_SELECTOR, select_css_selector)
            print(3.1)
            opts = el.find_elements(By.TAG_NAME, "option")
            print(3.2)
            results = [(o.get_attribute("value"), o.text.strip()) for o in opts if o.get_attribute("value")]
            print(f"  found {len(results)} options for {select_css_selector}")
            return results
        except Exception as e:
            print(f"  get_select_options error for {select_css_selector}: {e}")
            return []

    def screenshot_element_png(self, element):
        print('4 - screenshot_element_png')
        """Return PNG bytes for element screenshot (Selenium 4)."""
        return element.screenshot_as_png

    def set_select_by_value(self, select_css_selector, value):
        print(f'5 - set_select_by_value {select_css_selector} {value}')
        try:
            print("5.1 - locating select element...")
            el = self.driver.find_element(By.CSS_SELECTOR, select_css_selector)
            if not el.is_displayed():
                print(f"  Element {select_css_selector} is hidden (display:none); skipping selection.")
                return False

            print("5.2 - selecting value...")
            Select(el).select_by_value(value)
            print("5.3 - selection complete.")
            time.sleep(0.3)
            return True

        except Exception as e:
            print(f"  set_select_by_value failed for {select_css_selector} = {value}: {e}")
            try:
                alert = self.driver.switch_to.alert
                alert_text = alert.text
                print(f"  ALERT detected: {alert_text}")
                alert.accept()
                print("  Alert closed; skipping this selection.")
            except Exception:
                print("  No alert detected or already handled.")
            return False



    def find_captcha_element(self):
        print('6 - find_captcha_element')
        # Attempt common ids; update if site differs
        candidates = ["//img[@id='captcha_image']", "//img[contains(@src,'captcha')]", "//img[contains(@id,'captcha')]"]
        for xp in candidates:
            try:
                el = self.driver.find_element(By.XPATH, xp)
                print("  captcha element found with xpath:", xp)
                return el
            except Exception:
                continue
        print("  captcha element NOT found with tried xpaths.")
        return None

    def set_captcha_and_submit(self, captcha_value, cause_type="civ"):
        print('7 - set_captcha_and_submit start')
        """Fill captcha input, close validation modals if present, then click Civil/Criminal."""
        try:
            print(f"Attempting to fill captcha: {captcha_value}, type={cause_type}")

            # --- Fill captcha ---
            captcha_input_candidates = [
                "cause_list_captcha_code",  # ✅ actual site ID
                "captcha", "txtCaptcha", "captcha_text"
            ]

            filled = False
            for cid in captcha_input_candidates:
                try:
                    inp = self.driver.find_element(By.ID, cid)
                    inp.clear()
                    inp.send_keys(captcha_value)
                    filled = True
                    print(f"Captcha filled using element id={cid}")
                    break
                except Exception as e:
                    print(f"Captcha field {cid} not found: {e}")
            if not filled:
                print("Captcha input not found at all!")
                return False

            # --- Check for validation modal that blocks click ---
            try:
                modals = self.driver.find_elements(By.CSS_SELECTOR, "#validateError.show")
                if modals:
                    print("⚠️ Validation modal detected — closing it before submit.")
                    # click close button inside modal if exists
                    close_btns = modals[0].find_elements(By.CSS_SELECTOR, "button[data-bs-dismiss='modal'], .close")
                    if close_btns:
                        close_btns[0].click()
                        print("Modal closed via close button.")
                    else:
                        self.driver.execute_script("document.getElementById('validateError').style.display='none';")
                        print("Modal forcibly hidden via JS.")
                    time.sleep(0.5)
            except Exception as e:
                print(f"Modal handling error (ignored): {e}")

            # --- Attempt to click Civil or Criminal ---
            clicked = False
            try:
                cause_type = cause_type.strip().lower()
                btn_xpath = f"//button[contains(@onclick, \"submit_causelist('{cause_type}')\")]"
                print(f"Looking for button: {btn_xpath}")
                btn = self.driver.find_element(By.XPATH, btn_xpath)

                # scroll to button before clicking
                self.driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                time.sleep(0.3)

                btn.click()
                print(f"{cause_type.title()} button clicked successfully.")
                clicked = True
            except Exception as e:
                print(f"Could not click {cause_type} button directly: {e}")
                # fallback: use JavaScript click
                try:
                    print("Retrying click with JS...")
                    self.driver.execute_script("arguments[0].click();", btn)
                    clicked = True
                except Exception as e2:
                    print(f"JS click also failed: {e2}")

            print(f"Submit clicked: {clicked}")
            return filled and clicked

        except Exception as e:
            print("Error during captcha + submit step:", e)
            return False


    def wait_for_table(self, table_id="dispTable", timeout=15):
        print('8 - wait_for_table', table_id)
        try:
            self.wait.until(EC.presence_of_element_located((By.ID, table_id)))
            print("  table appeared:", table_id)
            return True
        except Exception as e:
            print("  wait_for_table timeout / error:", e)
            return False

    def scrape_table_dispTable(self):
        print('9 - scrape_table_dispTable')
        """Scrape the dispTable into a data list (header + rows)."""
        try:
            table = self.driver.find_element(By.ID, "dispTable")
            rows = table.find_elements(By.TAG_NAME, "tr")
        except Exception as e:
            print("  could not find dispTable:", e)
            return []

        data = [["Sr No", "Case Info", "Party Name", "Advocate"]]
        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            if not cols:
                continue
            # skip section headers or rows with colspan
            if len(cols) < 4 or any(td.get_attribute("colspan") for td in cols):
                continue
            sr_no = cols[0].text.strip()

            case_text = cols[1].get_attribute("innerText").replace("\n", " ").strip()
            case_text = case_text.replace("\xa0", " ").replace("\u00A0", " ")
            # remove view label (joined) and quotes
            case_text = case_text.replace("View", "").replace("view", "")
            case_text = re.sub(r"['\"]+", "", case_text)
            case_text = re.sub(r"\s{2,}", " ", case_text).strip()

            party_text = cols[2].get_attribute("innerText").replace("\n", " ").strip()
            advocate = cols[3].get_attribute("innerText").replace("\n", " ").strip()

            data.append([sr_no, case_text, party_text, advocate])
        print(f"  scraped {len(data)-1} rows")
        return data

# ------------------------ PyQt5 UI / Worker ------------------------
class WorkerThread(QtCore.QThread):
    print('10 - WorkerThread class defined')
    """Run long-running Selenium tasks here to keep UI responsive."""
    finished_signal = QtCore.pyqtSignal(object, str)  # (data/result, message)

    def __init__(self, manager: SeleniumManager, action: str, params: dict):
        print('11 - WorkerThread.__init__')
        super().__init__()
        self.manager = manager
        self.action = action
        self.params = params
        print('11.1 - WorkerThread initialized', action)

    def run(self):
        print('12.0 - WorkerThread.run start')
        try:
            print(f"Thread started with action={self.action}, params keys={list(self.params.keys())}")
            if self.action == "load_states":
                opts = self.manager.get_select_options("#sess_state_code")
                self.finished_signal.emit(opts, "states_loaded")
                return

            if self.action == "load_districts":
                val = self.params.get("state_val")
                self.manager.set_select_by_value("#sess_state_code", val)
                time.sleep(0.5)
                opts = self.manager.get_select_options("#sess_dist_code")
                self.finished_signal.emit(opts, "districts_loaded")
                return

            if self.action == "load_complexes":
                val = self.params.get("district_val")
                self.manager.set_select_by_value("#sess_dist_code", val)
                time.sleep(0.5)
                opts = self.manager.get_select_options("#court_complex_code")
                self.finished_signal.emit(opts, "complexes_loaded")
                return

            if self.action == "load_establishments":
                val = self.params.get("complex_val")
                # set complex then read establishments (if any)
                self.manager.set_select_by_value("#court_complex_code", val)
                time.sleep(0.5)
                opts = self.manager.get_select_options("#court_est_code")
                self.finished_signal.emit(opts, "establishments_loaded")
                #return

            if self.action == "load_courts":
                # This action supports two flows:
                # - If est_val provided, set establishment then fetch courts
                # - Else if complex_val provided, set complex then fetch courts directly
                est_val = self.params.get("est_val")
                complex_val = self.params.get("complex_val")
                if est_val:
                    try:
                        self.manager.set_select_by_value("#court_est_code", est_val)
                        time.sleep(0.5)
                    except Exception as e:
                        print("  load_courts: set establishment failed:", e)
                else:
                    # try using complex to fetch courts (for complexes without establishments)
                    if complex_val:
                        try:
                            self.manager.set_select_by_value("#court_complex_code", complex_val)
                            time.sleep(0.5)
                        except Exception as e:
                            print("  load_courts: set complex failed:", e)
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
                # params: state_val, dist_val, complex_val, est_val, court_val, date_str, captcha_text, cause_type
                print("  fetch_causelist: starting selection sequence")
                sequence = [
                    ("#sess_state_code", self.params.get("state_val")),
                    ("#sess_dist_code", self.params.get("dist_val")),
                    ("#court_complex_code", self.params.get("complex_val")),
                    ("#court_est_code", self.params.get("est_val")),
                    ("#CL_court_no", self.params.get("court_val"))
                ]
                for sel, val in sequence:
                    if not val:
                        print(f"  skipping {sel} because no value provided")
                        continue
                    try:
                        elements = self.manager.driver.find_elements(By.CSS_SELECTOR, sel)
                        if not elements:
                            print(f"  Dropdown {sel} not found — skipping.")
                            continue
                        Select(elements[0]).select_by_value(val)
                        print(f"  Selected {val} on {sel}")
                        time.sleep(0.3)
                    except Exception as e:
                        print(f"  Skipping {sel} due to error: {e}")
                        continue

                # --- Set cause list date safely ---
                try:
                    date_str = self.params.get("date_str")
                    print(f"  trying to set date safely: {date_str}")

                    # Use the correct ID from site: causelist_date
                    date_input = self.manager.driver.find_element(By.ID, "causelist_date")

                    # Scroll into view & focus it
                    self.manager.driver.execute_script("arguments[0].scrollIntoView(true);", date_input)
                    time.sleep(0.3)
                    date_input.click()
                    time.sleep(0.2)

                    # Clear and enter date
                    date_input.clear()
                    date_input.send_keys(date_str)
                    print(f"  entered date: {date_str}")

                    # Trigger the site’s datepicker change handler (important!)
                    self.manager.driver.execute_script(
                        "arguments[0].dispatchEvent(new Event('change', { bubbles: true }));",
                        date_input
                    )
                    print("  date change event triggered successfully.")

                except Exception as e:
                    print(f"  ⚠️ Failed to set date field: {e}")


                # set captcha and submit using chosen cause type (civ/cri)
                captcha_val = self.params.get("captcha_text")
                cause_type = (self.params.get("cause_type") or "civ").strip().lower()
                print(f"  Submitting with cause_type: {cause_type}, captcha: '{captcha_val}'")

                ok = self.manager.set_captcha_and_submit(captcha_val, cause_type)
                print("  set_captcha_and_submit returned:", ok)

                if not ok:
                    # helpful debug: try one more time with default fallbacks
                    print("  Initial submit failed — attempting fallback submit with 'civ'.")
                    ok2 = self.manager.set_captcha_and_submit(captcha_val, "civ")
                    print("  fallback submit returned:", ok2)
                    if not ok2:
                        self.finished_signal.emit(None, "submit_failed")
                        return

                # wait for table
                ok2 = self.manager.wait_for_table("dispTable", timeout=25)
                if not ok2:
                    # maybe table id changed / page shows PDF etc.
                    self.finished_signal.emit(None, "table_not_found")
                    return

                # scrape table
                data = self.manager.scrape_table_dispTable()
                # save pdf
                today_suffix = date.today().strftime("%Y-%m-%d")
                filename = f"Cause_List_{today_suffix}.pdf"
                save_cause_list_pdf(data, filename)
                self.finished_signal.emit(filename, "done")
                return

        except Exception as e:
            print("WorkerThread.run caught exception:", e)
            try:
                self.finished_signal.emit(None, f"error:{e}")
            except Exception:
                pass

# =========================================================
#                   MAIN WINDOW
# =========================================================

class MainWindow(QtWidgets.QWidget):
    print('12 - MainWindow class defined')
    def __init__(self):
        print('13 - MainWindow.__init__ start')
        super().__init__()
        self.setWindowTitle("eCourts Cause List - GUI")
        self.setGeometry(200, 200, 980, 600)
        self.manager = SeleniumManager()
        self.manager.open_cause_list_page()
        self._last_worker = None
        self.init_ui()
        print('13 - MainWindow.__init__ done')

    def init_ui(self):
        print('14 - init_ui')
        layout = QtWidgets.QVBoxLayout(self)

        # Top inputs grid
        grid = QtWidgets.QGridLayout()
        row = 0

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

        row += 1

        self.load_complex_btn = QtWidgets.QPushButton("Load Court Complexes")
        self.load_complex_btn.clicked.connect(self.load_complexes)
        grid.addWidget(self.load_complex_btn, row, 0)

        self.complex_cb = QtWidgets.QComboBox()
        grid.addWidget(QtWidgets.QLabel("Court Complex:"), row, 1)
        grid.addWidget(self.complex_cb, row, 2)

        self.load_est_btn = QtWidgets.QPushButton("Load Establishments")
        self.load_est_btn.clicked.connect(self.load_establishments)
        grid.addWidget(self.load_est_btn, row, 3)

        self.est_cb = QtWidgets.QComboBox()
        grid.addWidget(QtWidgets.QLabel("Establishment:"), row, 4)
        grid.addWidget(self.est_cb, row, 5)

        row += 1

        self.load_court_btn = QtWidgets.QPushButton("Load Courts")
        self.load_court_btn.clicked.connect(self.load_courts)
        grid.addWidget(self.load_court_btn, row, 0)

        self.court_cb = QtWidgets.QComboBox()
        grid.addWidget(QtWidgets.QLabel("Court Name:"), row, 1)
        grid.addWidget(self.court_cb, row, 2)

        # Date input
        self.date_edit = QtWidgets.QDateEdit()
        self.date_edit.setDate(QtCore.QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        grid.addWidget(QtWidgets.QLabel("Cause List Date:"), row, 3)
        grid.addWidget(self.date_edit, row, 4)

        row += 1

        # Cause Type (Civil/Criminal)
        self.cause_type_cb = QtWidgets.QComboBox()
        self.cause_type_cb.addItem("Civil", "civ")
        self.cause_type_cb.addItem("Criminal", "cri")
        grid.addWidget(QtWidgets.QLabel("Cause Type:"), row, 0)
        grid.addWidget(self.cause_type_cb, row, 1)

        # Captcha area
        self.captcha_lbl = QtWidgets.QLabel()
        self.captcha_lbl.setFixedSize(220, 80)
        self.captcha_lbl.setStyleSheet("border: 1px solid #444;")
        grid.addWidget(QtWidgets.QLabel("Captcha:"), row, 2)
        grid.addWidget(self.captcha_lbl, row, 3)
        self.refresh_captcha_btn = QtWidgets.QPushButton("Refresh Captcha")
        print(14.1)
        self.refresh_captcha_btn.clicked.connect(self.load_captcha)
        grid.addWidget(self.refresh_captcha_btn, row, 4)

        self.captcha_input = QtWidgets.QLineEdit()
        grid.addWidget(self.captcha_input, row, 5)

        row += 1

        # Fetch button
        self.fetch_btn = QtWidgets.QPushButton("Fetch Cause List & Save PDF")
        self.fetch_btn.clicked.connect(self.fetch_causelist)
        grid.addWidget(self.fetch_btn, row, 5)

        layout.addLayout(grid)

        # Log box
        self.log = QtWidgets.QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)

        self.setLayout(layout)
        # initial load captcha
        print(14.2)
        QtCore.QTimer.singleShot(1000, self.load_captcha)

    def log_msg(self, msg):
        print('15 - log_msg:', msg)
        self.log.append(msg)
        print(msg)

    # ---------- Loader functions ----------
    def load_states(self):
        print('16 - load_states')
        self.log_msg("Loading states...")
        self.run_thread("load_states", {})

    def load_districts(self):
        print('17 - load_districts')
        state_val = self._selected_value(self.state_cb)
        if not state_val:
            self.log_msg("Select a state first.")
            return
        self.log_msg("Loading districts...")
        self.run_thread("load_districts", {"state_val": state_val})

    def load_complexes(self):
        print('18 - load_complexes')
        dist_val = self._selected_value(self.dist_cb)
        if not dist_val:
            self.log_msg("Select a district first.")
            return
        self.log_msg("Loading court complexes...")
        self.run_thread("load_complexes", {"district_val": dist_val})

    def load_establishments(self):
        print('19 - load_establishments')
        complex_val = self._selected_value(self.complex_cb)
        if not complex_val:
            self.log_msg("Select a court complex first.")
            return
        self.log_msg("Loading establishments...")
        self.run_thread("load_establishments", {"complex_val": complex_val})

    def load_courts(self):
        print('20 - load_courts')
        est_val = self._selected_value(self.est_cb)
        complex_val = self._selected_value(self.complex_cb)
        # Accept either an establishment selection or, if missing, use the complex to load courts
        if not est_val and not complex_val:
            self.log_msg("Select an establishment or a court complex first.")
            return
        self.log_msg("Loading courts...")
        # pass both params so worker can decide
        self.run_thread("load_courts", {"est_val": est_val, "complex_val": complex_val})

    def load_captcha(self):
        print('21 - load_captcha')
        self.log_msg("Fetching captcha image...")
        self.run_thread("get_captcha", {})

    def fetch_causelist(self):
        print('22 - fetch_causelist')
        # collect values
        params = {
            "state_val": self._selected_value(self.state_cb),
            "dist_val": self._selected_value(self.dist_cb),
            "complex_val": self._selected_value(self.complex_cb),
            "est_val": self._selected_value(self.est_cb),
            "court_val": self._selected_value(self.court_cb),
            "date_str": self.date_edit.date().toString("dd-MM-yyyy"),
            "captcha_text": self.captcha_input.text().strip(),
            "cause_type": self._selected_value(self.cause_type_cb)
        }
        print("  params collected:", params)
        if not params["captcha_text"]:
            self.log_msg("Please enter captcha.")
            return
        self.log_msg("Starting fetch (this may take a while)...")
        self.run_thread("fetch_causelist", params)

    # ---------- Thread runner ----------
    def run_thread(self, action, params):
        print('23 - run_thread', action)
        worker = WorkerThread(self.manager, action, params)
        self._last_worker = worker  # keep reference to avoid GC killing the thread
        worker.finished_signal.connect(self.on_worker_finished)
        worker.start()

    # ---------- Helper ----------
    def _selected_value(self, combobox: QtWidgets.QComboBox):
        print('24 - _selected_value called')
        if combobox is None:
            return None
        idx = combobox.currentIndex()
        if idx < 0:
            return None
        val = combobox.itemData(idx)
        return val

    # ---------- Worker finished handler ----------
    def on_worker_finished(self, payload, tag):
        print('25 - on_worker_finished', tag)
        if tag == "states_loaded":
            self.state_cb.clear()
            for val, txt in payload:
                self.state_cb.addItem(txt, val)
            self.log_msg("States loaded.")
        elif tag == "districts_loaded":
            self.dist_cb.clear()
            for val, txt in payload:
                self.dist_cb.addItem(txt, val)
            self.log_msg("Districts loaded.")
        elif tag == "complexes_loaded":
            self.complex_cb.clear()
            for val, txt in payload:
                self.complex_cb.addItem(txt, val)
            self.log_msg("Court complexes loaded.")
        elif tag == "establishments_loaded":
            self.est_cb.clear()
            for val, txt in payload:
                self.est_cb.addItem(txt, val)
            self.log_msg("Establishments loaded.")
        elif tag == "courts_loaded":
            self.court_cb.clear()
            for val, txt in payload:
                self.court_cb.addItem(txt, val)
            self.log_msg("Courts loaded.")
        elif tag == "captcha_image":
            if not payload:
                self.log_msg("No captcha image returned.")
                return
            png = payload
            pix = QtGui.QPixmap()
            pix.loadFromData(png)
            scaled = pix.scaled(self.captcha_lbl.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            self.captcha_lbl.setPixmap(scaled)
            self.log_msg("Captcha loaded. Please type it into the field.")
        elif tag == "captcha_not_found":
            self.log_msg("Captcha not found on the page.")
        elif tag == "submit_failed":
            self.log_msg("Failed to submit form (captcha or button not found).")
        elif tag == "table_not_found":
            self.log_msg("Cause list table not found after submission.")
        elif tag == "done":
            filename = payload
            self.log_msg(f"Done. Saved PDF: {filename}")
        elif isinstance(tag, str) and tag.startswith("error:"):
            self.log_msg(f"Error in worker: {tag}")
        else:
            self.log_msg(f"Unknown worker result: {tag} / {payload}")

# =========================================================
#                   MAIN
# =========================================================

def main():
    print(26, "- main start")
    app = QtWidgets.QApplication(sys.argv)
    print(27, "- QApplication created")
    win = MainWindow()
    print(28, "- MainWindow created")
    win.show()
    print(29, "- MainWindow shown")
    sys.exit(app.exec_())
    print(30, "- app.exec_ returned (shouldn't reach)")

if __name__ == "__main__":
    main()
print(31, "- script end")
