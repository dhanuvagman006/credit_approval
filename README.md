# Credit Approval System

A Django REST Framework backend for credit approval based on customer history and credit scoring.

---

## Tech Stack

- **Django 4.2** + **Django REST Framework**
- **PostgreSQL** — primary database
- **Celery** + **Redis** — background task queue for data ingestion
- **Docker** + **Docker Compose** — full containerization

---

## Project Structure

```
credit_approval/
├── core/                   # Django project config
│   ├── settings.py
│   ├── urls.py
│   ├── celery.py
│   └── wsgi.py
├── credit_app/             # Main application
│   ├── models.py           # Customer & Loan models
│   ├── views.py            # API views
│   ├── serializers.py      # DRF serializers
│   ├── services.py         # Credit scoring & EMI logic
│   ├── tasks.py            # Celery ingestion tasks
│   ├── urls.py             # URL routing
│   ├── tests.py            # Unit tests
│   └── management/
│       └── commands/
│           └── ingest_data.py
├── data/                   # Place Excel files here
│   ├── customer_data.xlsx
│   └── loan_data.xlsx
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── manage.py
```

---

## Setup & Running

### 1. Add Data Files

Place your Excel files in the `data/` directory:
```
data/customer_data.xlsx
data/loan_data.xlsx
```

### 2. Start the Application

```bash
docker-compose up --build
```

This will:
- Start PostgreSQL and Redis
- Run Django migrations
- Trigger data ingestion via Celery background workers
- Start the Django dev server on **http://localhost:8000**

### 3. Run Tests

```bash
docker-compose run web python manage.py test credit_app
```

---

## API Reference

All endpoints accept and return JSON.

---

### `POST /register`

Register a new customer.

**Request:**
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "age": 30,
  "monthly_income": 50000,
  "phone_number": 9876543210
}
```

**Response `201`:**
```json
{
  "customer_id": 1,
  "name": "John Doe",
  "age": 30,
  "monthly_income": 50000,
  "approved_limit": 1800000,
  "phone_number": 9876543210
}
```

> `approved_limit = 36 × monthly_income`, rounded to the nearest lakh.

---

### `POST /check-eligibility`

Check loan eligibility without creating a loan.

**Request:**
```json
{
  "customer_id": 1,
  "loan_amount": 200000,
  "interest_rate": 10.0,
  "tenure": 12
}
```

**Response `200`:**
```json
{
  "customer_id": 1,
  "approval": true,
  "interest_rate": 10.0,
  "corrected_interest_rate": 10.0,
  "tenure": 12,
  "monthly_installment": 17584.15
}
```

**Credit Score Rules:**

| Credit Score  | Approval Condition              |
|---------------|---------------------------------|
| > 50          | Approved at requested rate      |
| 30 – 50       | Approved only if rate > 12%     |
| 10 – 30       | Approved only if rate > 16%     |
| ≤ 10          | Not approved                    |
| Any           | Rejected if EMIs > 50% salary   |

---

### `POST /create-loan`

Create and approve a loan.

**Request:**
```json
{
  "customer_id": 1,
  "loan_amount": 200000,
  "interest_rate": 14.0,
  "tenure": 24
}
```

**Response `201` (approved):**
```json
{
  "loan_id": 42,
  "customer_id": 1,
  "loan_approved": true,
  "message": "Loan approved.",
  "monthly_installment": 9638.21
}
```

**Response `200` (rejected):**
```json
{
  "loan_id": null,
  "customer_id": 1,
  "loan_approved": false,
  "message": "Credit score too low to approve any loan.",
  "monthly_installment": 0.0
}
```

---

### `GET /view-loan/<loan_id>`

Get full details of a loan with customer info.

**Response `200`:**
```json
{
  "loan_id": 42,
  "customer": {
    "id": 1,
    "first_name": "John",
    "last_name": "Doe",
    "phone_number": 9876543210,
    "age": 30
  },
  "loan_amount": 200000.0,
  "interest_rate": 14.0,
  "monthly_installment": 9638.21,
  "tenure": 24
}
```

---

### `GET /view-loans/<customer_id>`

Get all active loans for a customer.

**Response `200`:**
```json
[
  {
    "loan_id": 42,
    "loan_amount": 200000.0,
    "interest_rate": 14.0,
    "monthly_installment": 9638.21,
    "repayments_left": 18
  }
]
```

---

## Credit Score Components

The credit score (0–100) is computed from:

1. **Past loans paid on time** — ratio of on-time EMIs to total EMIs (weight: 35)
2. **Number of past loans** — fewer is better (weight: 20)
3. **Loan activity in current year** — fewer active new loans is better (weight: 20)
4. **Loan approved volume** — compared against approved limit (weight: 25)
5. **Hard rule** — if total active loan amount > approved limit → score = 0

---

## EMI Calculation

Uses the standard compound interest EMI formula:

```
EMI = P × r × (1 + r)^n / ((1 + r)^n − 1)
```

where `r = annual_rate / 1200` and `n = tenure in months`.

---

## Data Ingestion

Excel files are ingested via Celery background tasks on startup.
To re-run ingestion manually:

```bash
# Via Celery (async)
docker-compose run web python manage.py ingest_data

# Synchronously (no Celery needed)
docker-compose run web python manage.py ingest_data --sync
```
