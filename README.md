# Pragma E-Commerce - Order Discount Engine

A Django REST Framework based e-commerce backend with a powerful order discount engine.

## Table of Contents

- [Overview](#overview)
- [Things Not Covered](#things-not-covered)
- [Tech Stack](#tech-stack)
- [Model Architecture](#model-architecture)
  - [Abstract Base Models](#abstract-base-models)
  - [Model Hierarchy](#model-hierarchy)
- [Discount Engine](#discount-engine)
- [Setup & Installation](#setup--installation)
  - [Local Development](#local-development)
  - [Docker Setup](#docker-setup)
- [API Endpoints](#api-endpoints)
- [Testing](#testing)

---

## Overview

This project implements a complete e-commerce backend with:
- User authentication (JWT-based)
- Product catalog with categories and variants
- Order management with checkout flow
- **Discount Engine** - Automatic discount calculation based on configurable rules

---
## Things Not Covered 
- Email validation Of the User to make user Validate
- CRUD APIS for all Models of Product, Inventory for creating objects must use Django Admin
- User Must be validated to create and access Orders
- Inventory Transaction to import products into inventory
---

## Tech Stack

| Technology | Purpose |
|------------|---------|
| Django 5.2 | Web Framework |
| Django REST Framework | REST API |
| PostgreSQL | Database |
| JWT (SimpleJWT) | Authentication |
| Docker | Containerization |
| Gunicorn | Production Server |

---

## Model Architecture

### Abstract Base Models

All models inherit from abstract base classes defined in `core/models.py` for consistency:

```
┌─────────────────────────────────────────────────────────────┐
│                    AbstractBaseModel                         │
│  ┌─────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ AbstractUUID│  │ AbstractMonitor │  │ AbstractActive  │  │
│  │             │  │                 │  │                 │  │
│  │ • id (UUID) │  │ • created_at    │  │ • is_active     │  │
│  │             │  │ • updated_at    │  │ • soft_delete() │  │
│  └─────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

| Abstract Model | Fields | Purpose |
|----------------|--------|---------|
| `AbstractUUID` | `id` (UUID) | Provides UUID as primary key instead of auto-increment |
| `AbstractMonitor` | `created_at`, `updated_at` | Automatic timestamp tracking |
| `AbstractActive` | `is_active` | Soft delete functionality (never hard delete) |
| `AbstractBaseModel` | All above | Complete base model for most entities |

**Why this design?**
- **UUID**: Better for distributed systems, no sequential ID guessing
- **Timestamps**: Audit trail without additional code
- **Soft Delete**: Data recovery, maintain referential integrity

### Model Hierarchy

```
accounts/
├── User                    # Custom user with email auth
│   ├── email, first_name, last_name
│   ├── is_loyalty_member   # For loyalty-only discounts
│   └── addresses (M2M → Address)

core/
├── Address                 # Shipping/billing addresses
│   ├── address_line_1, city, country, postal_code
│   └── phone (PhoneNumberField)
└── MediaFile               # File storage references

products/
├── Category               # Product categories (self-referential for hierarchy)
│   └── parent → Category
├── Product                # Main product entity
│   ├── category → Category
│   └── default_variant → ProductVariant
├── ProductVariant         # Purchasable unit with price
│   ├── product → Product
│   ├── product_sku → SKU
│   └── price
└── SKU                    # Stock Keeping Unit

orders/
├── Order                  # Customer order
│   ├── user → User
│   ├── shipping_address → Address
│   ├── order_status, payment_status
│   ├── total_payable_amount
│   ├── discount_amount     # Calculated by discount engine
│   └── total_payable_tax
└── OrderItem              # Line items in order
    ├── order → Order
    ├── product_variant → ProductVariant
    ├── quantity, unit_rate, amount

discounts/
├── DiscountRule           # Configurable discount rules
│   ├── scope: ORDER | CATEGORY | ITEM
│   ├── discount_type: FIX | PERCENTAGE
│   ├── discount_value
│   ├── min_order_amount, min_quantity (conditions)
│   ├── categories → Category (for category scope)
│   ├── product_variant → ProductVariant (for item scope)
│   ├── requires_loyalty, is_stackable
│   └── start_date, end_date
└── AppliedDiscount        # Record of discounts applied to orders
    ├── order → Order
    ├── discount_rule → DiscountRule
    ├── discount_amount
    └── metadata (JSON)
```

---

## Discount Engine

The discount engine (`discounts/utils.py`) automatically calculates and applies discounts during checkout.

### Discount Scopes

| Scope | Description | Example |
|-------|-------------|---------|
| `ORDER` | Applies to entire order total | "10% off orders over ₹500" |
| `CATEGORY` | Applies to items in a category | "15% off Electronics" |
| `ITEM` | Applies to specific product variant | "₹50 off Laptop Pro" |

### Discount Types

| Type | Description |
|------|-------------|
| `FIX` | Fixed amount discount (₹50 off) |
| `PERCENTAGE` | Percentage discount (10% off) |

### Stacking Logic

- **Stackable discounts**: All applicable discounts are summed
- **Non-stackable discounts**: Only the best (highest) one applies
- Stackable + Non-stackable: Both types can work together

### Conditions

| Condition | Description |
|-----------|-------------|
| `min_order_amount` | Minimum subtotal required |
| `min_quantity` | Minimum quantity required |
| `requires_loyalty` | Only for loyalty members |
| `start_date` / `end_date` | Validity period |

---

## Setup & Installation

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Docker (optional)

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/SwapnilK3/Pragma-Assesment.git
   cd Pragma-Assesment
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   
   # Windows
   .venv\Scripts\activate
   
   # Linux/Mac
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```

5. **Start PostgreSQL** (if not using Docker)
   ```bash
   # Ensure PostgreSQL is running with database 'pragma_db'
   ```

6. **Run migrations**
   ```bash
   python manage.py migrate
   ```

7. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

8. **Run development server**
   ```bash
   python manage.py runserver
   ```

   Server runs at: `http://localhost:8000`

### Docker Setup

1. **Start all services**
   ```bash
   docker-compose up -d
   ```

2. **Run migrations**
   ```bash
   docker-compose exec web python manage.py migrate
   ```

3. **Create superuser**
   ```bash
   docker-compose exec web python manage.py createsuperuser
   ```

4. **View logs**
   ```bash
   docker-compose logs -f web
   ```

5. **Stop services**
   ```bash
   docker-compose down
   ```

---

## API Endpoints

### Authentication (`/api/auth/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register/` | Register new user |
| POST | `/api/auth/login/` | Login and get JWT tokens |
| POST | `/api/auth/logout/` | Logout (blacklist token) |
| POST | `/api/auth/token/refresh/` | Refresh access token |

**Register Payload:**
```json
{
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "password": "securepassword123"
}
```

**Login Response:**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

---

### Orders (`/api/order/`)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/order/` | List user's orders | Required |
| POST | `/api/order/checkout/` | Create new order | Required |
| GET | `/api/order/{id}/` | Get order details | Required |

**Checkout Payload:**
```json
{
  "items": [
    {"product_variant_id": "uuid-here", "quantity": 2},
    {"product_variant_id": "uuid-here", "quantity": 1}
  ],
  "shipping_address": {
    "address_line_1": "123 Main St",
    "city": "Mumbai",
    "country_code": "IN",
    "country_area": "Maharashtra",
    "postal_code": "400001",
    "phone": "+919876543210"
  },
  "payment_mode": "online"
}
```

**Order Detail Response (with discount breakdown):**
```json
{
  "id": "order-uuid",
  "order_number": 1001,
  "subtotal": "1500.00",
  "discount_amount": "150.00",
  "discount_breakdown": {
    "total_discount": "150.00",
    "applied_count": 2,
    "distribution": [
      {
        "scope": "order",
        "scope_display": "Order",
        "total_amount": "100.00",
        "discount_count": 1,
        "discounts": [
          {"rule_name": "10% Off Orders", "amount": "100.00"}
        ]
      },
      {
        "scope": "category",
        "scope_display": "Category",
        "total_amount": "50.00",
        "discount_count": 1,
        "discounts": [
          {"rule_name": "Electronics Sale", "amount": "50.00"}
        ]
      }
    ]
  },
  "total_payable_tax": "135.00",
  "total_payable_amount": "1350.00"
}
```

---

### Discount Rules (`/api/discount/`) - Admin Only

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/discount/rules/` | List all discount rules |
| POST | `/api/discount/rules/` | Create discount rule |
| GET | `/api/discount/rules/{id}/` | Get rule details |
| PUT | `/api/discount/rules/{id}/` | Update rule |
| PATCH | `/api/discount/rules/{id}/` | Partial update |
| DELETE | `/api/discount/rules/{id}/` | Soft delete rule |
| GET | `/api/discount/rules/active/` | Get only active rules |
| GET | `/api/discount/applied/` | View applied discounts |

**Create Order Discount Rule:**
```json
{
  "name": "10% Off Orders Over ₹500",
  "scope": "order",
  "discount_type": "percentage",
  "discount_value": "10.00",
  "min_order_amount": "500.00",
  "is_stackable": true,
  "start_date": "2026-01-01T00:00:00Z"
}
```

**Create Category Discount Rule:**
```json
{
  "name": "Electronics 15% Off",
  "scope": "category",
  "discount_type": "percentage",
  "discount_value": "15.00",
  "categories": "category-uuid",
  "start_date": "2026-01-01T00:00:00Z",
  "end_date": "2026-01-31T23:59:59Z"
}
```

**Create Item Discount Rule:**
```json
{
  "name": "₹100 Off Laptop (Buy 2+)",
  "scope": "item",
  "discount_type": "fix",
  "discount_value": "100.00",
  "product_variant": "variant-uuid",
  "min_quantity": "2",
  "start_date": "2026-01-01T00:00:00Z"
}
```

**Filter & Search:**
```
GET /api/discount/rules/?scope=order
GET /api/discount/rules/?discount_type=percentage
GET /api/discount/rules/?is_stackable=true
GET /api/discount/rules/?search=electronics
GET /api/discount/rules/?ordering=-discount_value
```

---

### Products (`/api/product/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/product/` | List products |

---

### Admin Panel

Access Django admin at: `http://localhost:8000/admin/`

---

## Testing

Run all tests:
```bash
python manage.py test
```

Run specific app tests:
```bash
python manage.py test discounts.tests
python manage.py test orders.tests
```

Run with verbosity:
```bash
python manage.py test discounts.tests -v 2
```

### Test Coverage

| Module | Tests | Coverage |
|--------|-------|----------|
| Discount Rules API | 19 | CRUD, validation, filtering |
| Discount Models | 4 | Model creation |
| Discount Engine | 20 | All calculation scenarios |

---

## Project Structure

```
pragma-assessment/
├── accounts/           # User authentication
├── core/               # Abstract models, utilities
├── discounts/          # Discount rules & engine
├── orders/             # Order management
├── products/           # Product catalog
├── inventory/          # Stock management (future)
├── pragma/             # Django settings
├── templates/          # HTML templates
├── docker-compose.yml  # Docker services
├── Dockerfile          # Container definition
├── requirements.txt    # Python dependencies
└── .env.example        # Environment template
```

---

## Next Version

Adding all other Curd API for all apps and UI for Easy Access

---

## License

This project is for assessment purposes.

---

## Author

Swapnil Kale,  with help of GitHub Copilot. - [GitHub](https://github.com/SwapnilK3)