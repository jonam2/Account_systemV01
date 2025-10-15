"""
Invoice Routes - API URL Configuration
Maps URLs to invoice controller functions

URL Pattern: /api/v1/invoices/*
"""
from django.urls import path
from layers.controllers import invoice_controller


app_name = 'invoices'

urlpatterns = [
    # Invoice CRUD
    path(
        '<str:invoice_type>/',
        invoice_controller.invoice_list_create,
        name='invoice-list-create'
    ),
    path(
        'detail/<int:invoice_id>/',
        invoice_controller.invoice_detail,
        name='invoice-detail'
    ),
    
    # Invoice Actions
    path(
        'detail/<int:invoice_id>/approve/',
        invoice_controller.invoice_approve,
        name='invoice-approve'
    ),
    path(
        'detail/<int:invoice_id>/cancel/',
        invoice_controller.invoice_cancel,
        name='invoice-cancel'
    ),
    
    # Payments
    path(
        'detail/<int:invoice_id>/payments/',
        invoice_controller.invoice_payments,
        name='invoice-payments'
    ),
    path(
        'payments/<int:payment_id>/',
        invoice_controller.payment_delete,
        name='payment-delete'
    ),
    
    # Reports & Statistics
    path(
        '<str:invoice_type>/overdue/',
        invoice_controller.invoice_overdue,
        name='invoice-overdue'
    ),
    path(
        '<str:invoice_type>/stats/',
        invoice_controller.invoice_stats,
        name='invoice-stats'
    ),
    path(
        'contact/<int:contact_id>/<str:invoice_type>/summary/',
        invoice_controller.contact_invoice_summary,
        name='contact-invoice-summary'
    ),
]


"""
API Endpoints Documentation:

1. LIST/CREATE INVOICES
   GET    /api/v1/invoices/sales/              - List sales invoices
   GET    /api/v1/invoices/purchase/           - List purchase invoices
   POST   /api/v1/invoices/sales/              - Create sales invoice
   POST   /api/v1/invoices/purchase/           - Create purchase invoice
   
   Query Parameters (GET):
   - status: Filter by status
   - contact_id: Filter by contact
   - warehouse_id: Filter by warehouse
   - date_from: Filter from date
   - date_to: Filter to date
   - search: Search in invoice number, reference, contact name
   - page: Page number (default: 1)
   - page_size: Items per page (default: 20)

2. INVOICE DETAIL
   GET    /api/v1/invoices/detail/{id}/        - Get invoice details
   PUT    /api/v1/invoices/detail/{id}/        - Update invoice
   DELETE /api/v1/invoices/detail/{id}/        - Delete invoice (soft)

3. INVOICE ACTIONS
   POST   /api/v1/invoices/detail/{id}/approve/ - Approve & update inventory
   POST   /api/v1/invoices/detail/{id}/cancel/  - Cancel & reverse inventory

4. PAYMENTS
   GET    /api/v1/invoices/detail/{id}/payments/ - List payments
   POST   /api/v1/invoices/detail/{id}/payments/ - Add payment
   DELETE /api/v1/invoices/payments/{payment_id}/ - Delete payment

5. REPORTS & STATISTICS
   GET    /api/v1/invoices/sales/overdue/      - Overdue sales invoices
   GET    /api/v1/invoices/purchase/overdue/   - Overdue purchase invoices
   GET    /api/v1/invoices/all/overdue/        - All overdue invoices
   GET    /api/v1/invoices/sales/stats/        - Sales statistics
   GET    /api/v1/invoices/purchase/stats/     - Purchase statistics
   GET    /api/v1/invoices/contact/{contact_id}/sales/summary/   - Contact sales summary
   GET    /api/v1/invoices/contact/{contact_id}/purchase/summary/ - Contact purchase summary

Example Requests:

# Create Sales Invoice
POST /api/v1/invoices/sales/
{
  "invoice_type": "SALES",
  "contact_id": 1,
  "warehouse_id": 1,
  "invoice_date": "2024-10-15",
  "payment_terms": "NET_30",
  "discount_percentage": 5,
  "tax_percentage": 10,
  "shipping_cost": 50.00,
  "notes": "Urgent order",
  "items": [
    {
      "product_id": 1,
      "quantity": 10,
      "unit_price": 100.00,
      "discount_percentage": 0,
      "tax_percentage": 10
    },
    {
      "product_id": 2,
      "quantity": 5,
      "unit_price": 50.00
    }
  ]
}

# Add Payment
POST /api/v1/invoices/detail/1/payments/
{
  "payment_date": "2024-10-20",
  "amount": 500.00,
  "payment_method": "BANK_TRANSFER",
  "reference_number": "TXN123456",
  "notes": "Partial payment"
}

# Approve Invoice
POST /api/v1/invoices/detail/1/approve/
(No body required - updates inventory automatically)

# Get Statistics
GET /api/v1/invoices/sales/stats/?period_days=30

Response Formats:

# Invoice List Response
{
  "invoices": [...],
  "pagination": {
    "total_count": 100,
    "page": 1,
    "page_size": 20,
    "total_pages": 5
  }
}

# Invoice Detail Response
{
  "id": 1,
  "invoice_number": "INV-SALES-2024-0001",
  "invoice_type": "SALES",
  "contact": {...},
  "warehouse": {...},
  "items": [...],
  "payments": [...],
  "total_amount": 1050.00,
  "paid_amount": 500.00,
  "balance_due": 550.00,
  "status": "PARTIALLY_PAID",
  ...
}

# Statistics Response
{
  "total_invoices": 45,
  "total_amount": 45000.00,
  "total_paid": 30000.00,
  "outstanding_balance": 15000.00,
  "pending_invoices": 10,
  "paid_invoices": 35,
  "overdue_invoices": 5,
  "overdue_amount": 5000.00
}
"""