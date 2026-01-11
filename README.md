<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Flask-3.0-green?style=for-the-badge&logo=flask&logoColor=white" alt="Flask">
  <img src="https://img.shields.io/badge/PostgreSQL-Supabase-336791?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="License">
</p>

<h1 align="center">🎓 Sarva Gyaan Academy</h1>

<p align="center">
  <strong>A modern, full-featured Student Management System for coaching institutions</strong>
</p>

<p align="center">
  <a href="#-features">Features</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-tech-stack">Tech Stack</a> •
  <a href="#-deployment">Deployment</a> •
  <a href="#-contributing">Contributing</a>
</p>

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔐 **Authentication** | Secure login with role-based access (Admin, Teacher, Student, Parent) |
| 👨‍🎓 **Student Management** | Registration, profiles, batch assignment, CSV import, photo upload |
| 📅 **Attendance Tracking** | Daily marking, calendar view, monthly reports, CSV export |
| 💰 **Fee Management** | Collection, printable receipts, pending dues, fee structures |
| 📢 **Announcements** | Rich text announcements with image support |
| 💬 **AI Chat** | Integrated AI assistant powered by Google Gemini |
| 🌙 **Dark Mode** | Beautiful dark theme with system preference detection |
| 📊 **Dashboard** | Real-time statistics, charts, and quick actions |

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- pip (Python package manager)
- [Supabase](https://supabase.com) account (for production)

### Local Development

```bash
# Clone the repository
git clone https://github.com/isar-durganand/sarva-gyan-academy.git
cd sarva-gyan-academy

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template and configure
cp .env.example .env
# Edit .env with your settings

# Run the application
python run.py
```

Open your browser at `http://localhost:5000`

## 🛠 Tech Stack

| Category | Technology |
|----------|------------|
| **Backend** | Python, Flask 3.0, SQLAlchemy |
| **Database** | PostgreSQL (Supabase) / SQLite (dev) |
| **Frontend** | HTML5, CSS3, JavaScript |
| **UI** | Custom CSS, Bootstrap Icons, Chart.js |
| **AI** | Google Gemini API |
| **Deployment** | Vercel |

## 📂 Project Structure

```
sarva-gyan-academy/
├── api/                 # Vercel serverless entry
├── app/
│   ├── models/          # Database models
│   ├── routes/          # Route blueprints
│   ├── templates/       # Jinja2 templates
│   ├── static/          # CSS, JS, images
│   └── utils/           # Helper functions
├── instance/            # Local database
├── .env.example         # Environment template
├── requirements.txt     # Python dependencies
├── vercel.json          # Vercel configuration
└── run.py               # Entry point
```

## 🚀 Deployment

### Deploy to Vercel

1. Push your code to GitHub
2. Import project in [Vercel Dashboard](https://vercel.com/new)
3. Set environment variables:
   - `SECRET_KEY` - Random secure string
   - `DATABASE_URL` - Supabase PostgreSQL URL
   - `ADMIN_EMAIL` - Admin login email
   - `ADMIN_PASSWORD` - Admin password
   - `GEMINI_API_KEY` - Google Gemini API key
4. Deploy!

### Supabase Setup

1. Create a project at [supabase.com](https://supabase.com)
2. Go to **Settings → Database → Connection string**
3. Copy the URI and replace `postgres://` with `postgresql://`
4. Add as `DATABASE_URL` in Vercel

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) before submitting a PR.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with ❤️ for education
- Powered by [Flask](https://flask.palletsprojects.com/)
- Database hosted on [Supabase](https://supabase.com)
- Deployed on [Vercel](https://vercel.com)

---

<p align="center">
  <strong>⭐ Star this repo if you find it helpful!</strong>
</p>
