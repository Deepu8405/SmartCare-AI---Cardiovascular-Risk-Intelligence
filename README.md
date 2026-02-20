# 🩺 SmartCare AI

SmartCare AI is a comprehensive heart health monitoring platform that leverages **Machine Learning** for risk prediction and **Generative AI** for clinical document analysis.

## 🚀 Key Features
* **Dual-Model Ensemble:** Combines Random Forest and XGBoost to calculate precise heart attack probability scores.
* **AI Doctor Assistant (RAG):** A chatbot integrated with Gemini 1.5-Flash that analyzes user-uploaded medical reports in real-time.
* **Clinical History:** Securely syncs and stores every health record in Supabase for long-term monitoring.
* **Medical News Feed:** Dynamic RSS integration fetching the latest health updates from WHO and CDC.
* **Responsive Dashboard:** A modern UI built with Tailwind CSS and HTMX for a seamless, "no-refresh" experience.

## 🛠️ Tech Stack
- **Frontend:** HTML5, Tailwind CSS, HTMX, JavaScript (ES6+).
- **Backend:** Flask (Python).
- **AI/ML:** Scikit-Learn, XGBoost, Google Generative AI (Gemini 1.5).
- **Database:** Supabase (PostgreSQL + Auth).

## 📦 Installation
1. Clone the repository: `git clone https://github.com/yourusername/smartcare-ai.git`
2. Install dependencies: `pip install -r requirements.txt`
3. Setup `.env` file with your credentials:
   - `SUPABASE_URL`, `SUPABASE_KEY`, `GOOGLE_AI_API_KEY`, `FLASK_SECRET_KEY`
4. Run locally: `python app.py`

## ⚖️ Disclaimer
This application is for educational and informational purposes only. It is not a substitute for professional medical advice, diagnosis, or treatment. Always seek the advice of your physician.
