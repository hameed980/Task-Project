# University ETL Data Extraction Pipeline

A production-style AI-powered ETL pipeline in Python that extracts structured university data (admissions, tuition, deadlines, and contact information) from university websites or university names using smart crawling, page ranking, and Gemini LLM-based extraction.

---

## Features

* **Dual Input Support**

  * Accepts both:

    * University name (e.g., "Bucknell University")
    * Direct domain (e.g., https://www.bucknell.edu)
  * Automatically resolves names to official domains using search + fallback logic

* **Smart Web Crawling**

  * Domain-restricted crawler (no external leakage)
  * Depth-limited crawling (max depth = 2)
  * Filters irrelevant pages (login, portals, media files)

* **Intelligent Page Discovery**

  * Scores pages based on relevance (admissions, tuition, financial aid)
  * Selects only high-quality pages for extraction

* **AI-Powered Extraction (Gemini)**

  * Uses a single optimized LLM call per university
  * Extracts structured JSON from cleaned HTML text
  * Prevents hallucination using strict prompting

* **Data Cleaning & Optimization**

  * Removes boilerplate (headers, navbars, scripts, footers)
  * Reduces noise to minimize token usage (~70% reduction)

* **Strict Validation Layer**

  * Uses Pydantic schemas for structured output validation
  * Normalizes:

    * Dates → YYYY-MM-DD
    * Currency → numeric USD values

* **Quality Tracking**

  * Confidence scoring per field
  * Source URL attribution for extracted data
  * Basic duplicate detection and validation reporting

---

## Project Structure

```
TASK
│
├── logs/                         # Runtime logs
├── output/                       # Final JSON outputs per university
│   ├── Bucknell_University.json
│   ├── Salisbury_University.json
│   └── University_of_the_District_of_Columbia.json
│
├── src/
│   ├── __init__.py
│   ├── cleaner.py                # HTML cleaning & noise removal
│   ├── crawler.py                # Web crawler (depth-limited BFS/DFS)
│   ├── discovery.py              # Page scoring & ranking logic
│   ├── extractor.py              # Gemini LLM extraction layer
│   ├── models.py                 # Pydantic schemas
│   ├── pipeline.py               # Main orchestration pipeline
│   ├── resolver.py               # Name → domain resolver
│   └── utils.py                  # Helpers & logging utilities
│
├── tests/                        # Pytest unit tests
├── venv/                         # Virtual environment
├── .env                          # API keys & configuration
├── main.py                       # Entry point (CLI runner)
├── README.md                     # Project documentation
├── requirements.txt              # Dependencies
```

---

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Setup Environment Variables

Create a `.env` file:

```env
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

---

##  Usage

### Run Single University

```bash
python main.py --input "Bucknell University"
```

or

```bash
python main.py --input "https://www.bucknell.edu"
```

---

### Run Batch Mode

```bash
python main.py --batch "MIT, Bucknell University, Salisbury University"
```

---

## Architecture Overview

1. **Input Layer**

   * Accepts university name or URL

2. **Resolver Layer**

   * Converts name → official domain (if needed)

3. **Crawler Layer**

   * Crawls website (depth ≤ 2)
   * Restricts to same domain

4. **Discovery Layer**

   * Scores pages based on relevance:

     * Admissions
     * Tuition
     * Financial Aid

5. **Cleaning Layer**

   * Removes noise (scripts, nav, footer)
   * Reduces token size for LLM

6. **Extraction Layer (Gemini)**

   * Single optimized request per university
   * Outputs structured JSON

7. **Validation Layer**

   * Pydantic schema validation
   * Normalization of formats

8. **Output Layer**

   * Stores structured JSON per university

---

##  Output Example

Each university produces:

* overview
* tuition breakdown
* admission deadlines
* contact info
* source attribution
* confidence scores

Stored in:

```
/output/*.json
```

---

##  Key Design Decisions

* **Single LLM Call Strategy**
  → Reduces cost, avoids rate limits

* **Depth-Limited Crawling (≤2)**
  → Prevents irrelevant page explosion

* **Page Scoring Instead of Hardcoding**
  → More scalable across universities

* **Strict Pydantic Validation**
  → Ensures structured and reliable outputs

---


##  Testing

```bash
pytest
```

Includes:

* crawler tests
* discovery tests
* pipeline validation tests

---

##  Summary

This pipeline demonstrates a full AI-powered ETL system combining:

* Web scraping
* Intelligent crawling
* LLM-based structured extraction
* Data validation
* Production-grade pipeline design
