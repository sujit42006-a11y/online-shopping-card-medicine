# MediKart — Complete Flask/MySQL Prototype

This version implements the core project requirements from the supplied MediKart prompt: customer authentication, medicines, categories, cart, checkout, prescription upload/review, orders and admin dashboard.

## Setup

1. Install Python 3.10+.
2. Create a virtual environment:
   `python -m venv venv`
3. Activate it:
   Windows: `venv\Scripts\activate`
4. Install:
   `pip install -r requirements.txt`
5. Copy `.env.example` to `.env` and enter your MySQL password.
6. Import `database/medikart.sql` into MySQL.
7. Create an admin password hash:
   `python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('Admin@123'))"`
8. Insert an admin using the generated hash:
   `INSERT INTO users(name,email,password_hash,role) VALUES ('MediKart Admin','admin@medikart.local','PASTE_HASH_HERE','admin');`
9. Run:
   `python app.py`
10. Open `http://127.0.0.1:5000`

## Main routes

Customer: `/`, `/register`, `/login`, `/medicines`, `/categories`, `/cart`, `/checkout`, `/prescription/upload`, `/orders`, `/profile`, `/addresses`.

Admin: `/admin/login`, `/admin`, `/admin/medicines`, `/admin/categories`, `/admin/users`, `/admin/orders`, `/admin/prescriptions`.

## Prescription workflow

Prescription-required demo medicines are marked in the database. The customer uploads JPG/JPEG/PNG/PDF files (5 MB application limit). Admin reviews and approves/rejects the file. No automated diagnosis or medical decision-making is performed.

## Payments

Only Cash on Delivery and Demo Payment are included. No real payment gateway is connected.

## Security

Passwords are hashed. SQL queries use parameters. Admin pages require an admin session. Uploaded prescription filenames are randomized and prescription files are served through an admin-protected route. Keep `.env` private.

## Important limitation

This is a college/project prototype. Real-world medicine sales require applicable pharmacy, licensing, prescription, privacy, payment, consumer-protection and other regulatory compliance.
