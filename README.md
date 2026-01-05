# Sarva Gyaan Academy - Student Management System

A comprehensive web-based student database management system built with Python Flask for coaching institutions.

## Features

### Phase 1 (Current)
- **User Authentication**: Secure login with role-based access (Admin, Teacher, Student, Parent)
- **Student Management**: Registration, profile management, batch assignment, CSV import
- **Attendance Tracking**: Daily marking, monthly views, reports, CSV export
- **Fee Management**: Collection, receipts, pending dues, reports

### Coming Soon
- Assignment Management
- Examination & Results
- Performance Analytics
- Communication System

## Quick Start

### Prerequisites
- Python 3.8+
- pip (Python package manager)

### Installation

1. **Clone or navigate to the project folder:**
   ```bash
   cd sarva-gyan-academy
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   ```

3. **Activate virtual environment:**
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Run the application:**
   ```bash
   python run.py
   ```

6. **Open browser:**
   Navigate to `http://localhost:5000`

### Default Login Credentials
- **Email:** ********@gmail.com
- **Password:** ********

## Project Structure

```
sarva-gyan-academy/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── config.py            # Configuration
│   ├── models/              # Database models
│   ├── routes/              # Route blueprints
│   ├── templates/           # HTML templates
│   ├── static/              # CSS, JS, images
│   └── utils/               # Helper functions
├── instance/                # Database file
├── uploads/                 # Uploaded files
├── requirements.txt
├── run.py                   # Entry point
└── README.md
```

## Technology Stack

- **Backend:** Python Flask
- **Database:** SQLite
- **Frontend:** HTML5, CSS3, JavaScript
- **UI Framework:** Custom CSS with Bootstrap Icons
- **Charts:** Chart.js

## Features Overview

### Dashboard
- Total students, attendance stats, fee collection
- Recent enrollments and transactions
- Batch distribution charts

### Student Management
- Add/Edit/View student profiles
- Photo upload
- Batch assignment
- CSV bulk import
- Search and filter

### Attendance
- Mark daily attendance by batch
- Calendar view
- Monthly reports
- Export to CSV

### Fee Management
- Collect fees with multiple payment modes
- Generate printable receipts
- Track pending dues
- Fee structure configuration
- Collection reports

## Dark Mode

Click the theme toggle button in the header to switch between light and dark themes. Your preference is saved automatically.

## License

This project is developed for Durganand Ishar.

---

**Developed with ❤️ for education**
