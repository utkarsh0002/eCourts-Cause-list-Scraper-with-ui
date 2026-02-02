# 🏛️ eCourts Cause List Downloader (PyQt5 + Selenium)

**Description:**  

A desktop GUI tool that automates downloading **District Court Cause Lists** directly from the [eCourts Services](https://services.ecourts.gov.in/ecourtindia_v6/) website.

This app allows users to select court parameters (state, district, complex, establishment, etc.), view and enter captcha manually, and automatically generate a **well-formatted PDF** of the cause list.

---

## ✨ Features

- ✅ Interactive **PyQt5 GUI**
- ⚙️ Automated **Selenium** browser control
- 🧩 Dropdown loading for all fields (State → District → Complex → Establishment → Court)
- 🔐 Manual captcha entry (auto-displays image)
- 🗓️ Custom date picker (defaults to today)
- 📄 Automatic PDF generation using **ReportLab**
- 💾 PDF saved locally with date-based filename

---

## 📦 Tech Stack

- Python 3.x  
- PyQt5 — GUI  
- Selenium — Web automation  
- WebDriver Manager — ChromeDriver auto-install  
- ReportLab — PDF generation

---

## ⚙️ Installation

```bash
pip install pyqt5 selenium webdriver-manager reportlab
```

---

## ▶️ Usage

1. **Run the app**

   ```bash
   python ecourts_pyqt_cause_list_ui.py
   ```

2. **Steps inside the GUI:**
   - Click **Load States**
   - Select **State → District → Complex → Establishment (if available) → Court**
   - Verify **Date** (defaults to today)
   - Click **Refresh Captcha**, then type it into the field
   - Choose **Civil** or **Criminal**
   - Click **Fetch Cause List & Save PDF**

3. **Output**
   - The program scrapes the cause list table and saves it as  
     `Cause_List_YYYY-MM-DD.pdf` in the same directory.

---

## 🧱 Project Structure

```bash
ecourts-cause-list/
│
├── ecourts_pyqt_cause_list_ui.py     # Main application script (GUI + Selenium)
├── Cause_List_YYYY-MM-DD.pdf         # Output PDFs (generated)
└── README.md                         # Documentation
```

---

## 💡 Notes

- The app uses **Selenium in normal (non-headless) mode** to let users see and manually solve the captcha.  
- Some court complexes **don’t have “Establishment” dropdowns** — the app automatically skips those gracefully.  
- For best performance, use **stable internet connection** since dropdown data loads dynamically.  
- Tested on **Windows 10/11** and **Python 3.9+**.

---

## 🧑‍💻 Author

**Utkarsh Vats**  
Python Developer & Engineering Student  
📧 *utkarshvats002@gmail.com* 

---

## 🔗 Example Output

When a valid captcha and court are selected, the generated PDF looks like:

| Sr No | Case Info | Party Name | Advocate |
|-------|------------|-------------|-----------|
| 1 | Civil Case No. 123/2025 | A vs B | John Doe |
| 2 | Civil Case No. 456/2025 | X vs Y | Jane Smith |

---

## 🚀 Future Improvements
- Auto-detect captcha using OCR (optional)
- Headless mode for automation pipelines
- Export results as CSV or Excel
- Save user’s last selections

---

**⭐ If you find this useful, give it a star on GitHub!**
