![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Flask](https://img.shields.io/badge/Flask-2.x-lightgrey)
![Gemini](https://img.shields.io/badge/LLM-Gemini%202.0-orange)
![License](https://img.shields.io/badge/License-MIT-green)

# NutritionRAG - Medical Health & Diet Planning System

A healthcare-focused Retrieval-Augmented Generation (RAG) system that processes nutrition and health textbooks to generate personalized diet plans using semantic search and AI.

<img width="1096" height="683" alt="image" src="https://github.com/user-attachments/assets/bbd925fe-2941-41e5-80a7-5f670233a3b7" />

# Healthy-AI

AI-powered personalized diet and health recommendation system using RAG (Retrieval-Augmented Generation), semantic search, and Gemini 2.0.

---

# Features

* Secure user authentication with PostgreSQL
* Upload and manage health/nutrition documents
* Semantic search using LanceDB vector database
* Personalized AI-generated diet plans
* Gemini 2.0 powered health insights
* User-level document privacy and access control

---

# Tech Stack

| Component        | Technology                      |
| ---------------- | ------------------------------- |
| Backend          | Python + Flask                  |
| Authentication   | PostgreSQL                      |
| Vector Database  | LanceDB                         |
| Embeddings       | all-MiniLM-L6-v2                |
| LLM              | Gemini 2.0 Flash                |
| Document Parsing | PyPDF2, pdfplumber, python-docx |

---

# How It Works

1. Upload health or nutrition documents
2. Documents are chunked and converted into embeddings
3. Semantic retrieval fetches relevant context
4. Gemini generates evidence-based diet recommendations

---

# Supported Document Types

* PDF
* DOCX
* TXT

### Supported Categories

* Nutrition
* Diet Plans
* Health Conditions
* Wellness
* Supplements

---

# Installation

## 1. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 2. Create PostgreSQL Database

```bash
createdb nutrition_rag_users
```

---

## 3. Configure Environment Variables

Create a `.env` file:

```env
DB_HOST=localhost
DB_NAME=nutrition_rag_users
DB_USER=postgres
DB_PASSWORD=your_password
DB_PORT=5432

GOOGLE_API_KEY=your_gemini_api_key
```

---

## 4. Initialize Vector Database

```bash
python setup_vectordb.py
```

---

# Running the Application

```bash
python main.py
```

---

# API Endpoints

## Document Management

| Method | Endpoint                  | Description     |
| ------ | ------------------------- | --------------- |
| POST   | `/api/documents/add`      | Upload document |
| GET    | `/api/documents/list`     | List documents  |
| DELETE | `/api/documents/{doc_id}` | Delete document |

---

## AI Features

| Method | Endpoint                   | Description            |
| ------ | -------------------------- | ---------------------- |
| POST   | `/api/diet-plans/generate` | Generate diet plan     |
| POST   | `/api/health/query`        | Semantic health search |

---

# Security

* PBKDF2 password hashing with salt
* UUID-based document identifiers
* Per-user document isolation
* No cross-user access

---

# Project Structure

```bash
Healthy-AI/
│
├── main.py
├── api.py
├── user_auth.py
├── vector_db.py
├── llm_processor.py
├── docreader.py
├── setup_vectordb.py
├── requirements.txt
├── README.md
└── .env
```

---

# Database Schema

## Users Table

| Field         | Description       |
| ------------- | ----------------- |
| id            | Primary key       |
| user_id       | Unique user ID    |
| password_hash | Hashed password   |
| salt          | Password salt     |
| created_at    | Registration time |

---

## Documents Table

| Field         | Description               |
| ------------- | ------------------------- |
| document_id   | UUID document ID          |
| file_name     | Original filename         |
| document_type | nutrition / health / diet |
| uploaded_at   | Upload timestamp          |
| indexed       | Embedding status          |

---

# Environment Variables

| Variable       | Description         |
| -------------- | ------------------- |
| DB_HOST        | PostgreSQL host     |
| DB_NAME        | Database name       |
| DB_USER        | Database user       |
| DB_PASSWORD    | PostgreSQL password |
| GOOGLE_API_KEY | Gemini API key      |
| EMBED_MODEL    | Embedding model     |

---

# Future Improvements

* OCR support for scanned PDFs
* Medical report analysis
* Allergy-aware diet generation
* Fitness recommendation engine
* Multi-model LLM support (Gemma, Llama)

---

This version feels:

* more startup/professional
* easier for judges/recruiters to scan
* cleaner on GitHub
* less intimidating technically
* more “production-ready”

Biggest improvement: tables + spacing + reducing wall-of-text density.

