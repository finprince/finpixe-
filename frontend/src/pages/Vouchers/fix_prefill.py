import re

with open('d:/finpixe/Ai_Accounting_28/AI-accounting-0.03/frontend/src/pages/Vouchers/SalesVoucher.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    "setDate(prefilledData.invoiceDate || new Date().toISOString().split('T')[0]);",
    "setDate(prefilledData.invoiceDate || prefilledData.date || new Date().toISOString().split('T')[0]);"
)

content = content.replace(
    "setSalesInvoiceNo(prefilledData.invoiceNumber || '');",
    "setSalesInvoiceNo(prefilledData.invoiceNumber || prefilledData.sales_invoice_no || '');"
)

content = content.replace(
    "const sellerName = prefilledData.sellerName || '';",
    "const sellerName = prefilledData.sellerName || prefilledData.customer_name || '';"
)

content = content.replace(
    "if (prefilledData.placeOfSupply) {",
    "if (prefilledData.placeOfSupply || prefilledData.place_of_supply) {"
)
content = content.replace(
    "const val = prefilledData.placeOfSupply;",
    "const val = prefilledData.placeOfSupply || prefilledData.place_of_supply;"
)

content = content.replace(
    "if (prefilledData.invoiceType) setInvoiceType(prefilledData.invoiceType);",
    "if (prefilledData.invoiceType || prefilledData.invoice_type) setInvoiceType(prefilledData.invoiceType || prefilledData.invoice_type);"
)

with open('d:/finpixe/Ai_Accounting_28/AI-accounting-0.03/frontend/src/pages/Vouchers/SalesVoucher.tsx', 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed prefilledData mappings in SalesVoucher.tsx')
