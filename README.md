# Aurum Jewellery CRM

A Flask CRM starter for an Indian jewellery store. It includes authentication, customer profiles, sales leads, jewellery inventory, employees and incentives, and business reports. The data model also includes sales and repair entities ready for the next POS workflow slice.

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python app.py
```

Open `http://127.0.0.1:5000` and sign in with `admin@aurum.local` / `admin123`.

## Included defaults

- INR pricing and India-oriented jewellery fields: metal, purity, gross weight, stone weight, SKU and reorder level.
- SQLite database stored in the Flask instance database by default.
- Configuration through `.env`, including `DATABASE_URL`, so PostgreSQL can be used later without changing the application routes.
- Seed data is inserted only into an empty database.

## Included workflows

- Role-based access control for Owner/Admin, Manager and Cashier users.
- Supplier directory and purchase order tracking.
- GST invoice PDF downloads with embedded verification QR codes.
- SKU/barcode lookup at the POS (USB barcode scanners work as keyboard input).
- Historical 22K/24K gold rates per gram.
- Returns and exchanges with automatic stock restoration.
- Customer loyalty points and purchase-linked invoice history.
- Sales KPIs and an interactive sales trend chart.

## Next production steps

Change the secret and demo password, add CSRF protection, configure PostgreSQL plus backups, and add GSTIN/business details before using real customer data.
