# Healthcare Lead Conversational Agent

## Project Description

In simple words, this project creates a smart AI chatbot for a medical products company. When you start the app, it first reads and "learns" the company's product pages directly from their website. Later, when a user asks a question, the chatbot uses this learned knowledge to provide highly accurate answers. 

If the user wants to buy a product or acts like a serious customer, the chatbot will politely ask for their contact details and save them as a "lead." It then automatically emails the company's sales or customer care team so they can reach out to the customer. All website knowledge and lead data are saved securely on your local system using lightweight databases.

## Prerequisites

- Python 3.9+ 
- A valid Google Gemini API Key

## Setup & Requirements

1. **Install Dependencies**
   Open your terminal in the project's root folder and install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment Variables (`.env` file)**
   The project requires certain settings and API keys to function properly. Create a file named `.env` in the root directory of the project and add the following configuration:

   ```env
   # ── Gemini AI Settings ──
   GEMINI_API_KEY=your_gemini_api_key_here
   GEMINI_MODEL=gemini-2.5-flash
   GEMINI_EMBEDDING_MODEL=gemini-embedding-001

   # ── Email Notification Settings ──
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=your_email@gmail.com
   SMTP_PASSWORD=your_app_password
   CUSTOMER_CARE_EMAIL=support@yourdomain.com

   # ── Target Website (for scraper) ──
   TARGET_WEBSITE_URL=https://www.polymedicure.com/product-category/cardiology/

   # ── App Settings ──
   APP_ENV=development
   SESSION_EXPIRY_MINUTES=30
   CHROMA_DB_PATH=./data/chromadb
   SQLITE_DB_PATH=./data/leads.db
   PYTHONPATH=.
   ```
   **Important:** You must replace `your_gemini_api_key_here` with your actual Google Gemini API key. Also, update the SMTP details with your valid sender credentials to ensure the lead email notifications work.

## How to Run the Code

1. Double-check that your `.env` file is properly configured.
2. Launch the application by running the provided entry-point script:
   ```bash
   python run.py
   ```
3. **On First Run:** The system will automatically scrape the website specified in `TARGET_WEBSITE_URL` (this usually takes around 2-3 minutes). It extracts the data to build the initial knowledge base.
4. Once the server finishes starting up, you can access the application at:
   - **Main App URL:** [http://localhost:8000](http://localhost:8000)
   - **Interactive API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
