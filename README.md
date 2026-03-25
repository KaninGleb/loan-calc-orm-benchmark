# Loan Calculator Benchmark (SQLAlchemy vs PL/pgSQL)

This repository demonstrates a comparative implementation of loan annuity calculations using two different architectural approaches:

1. **Database-side processing** using PL/pgSQL
2. **Application-side processing** using Python, SQLAlchemy 2.0, and Pydantic V2 for strict data validation (DTOs).

The goal is to compare calculations directly in the database versus handling them in the application layer.

## Quick Start

1. Run `sql/fintech.sql` in PostgreSQL.
2. Create `.env` based on `.env.example`:

```env
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=loan_db  # or any existing database
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run script:

```bash
python main.py
```

