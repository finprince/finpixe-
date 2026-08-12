const fs = require('fs');
const files = [
  'd:/finpixe/Ai_Accounting_35/AI-accounting-0.03/frontend/src/pages/Vouchers/SalesVoucher.tsx',
  'd:/finpixe/Ai_Accounting_35/AI-accounting-0.03/frontend/src/pages/Vouchers/Vouchers.tsx',
  'd:/finpixe/Ai_Accounting_35/AI-accounting-0.03/frontend/src/pages/Vouchers/DebitNoteVoucher.tsx'
];

const replacements = [
  { search: /calculateTotals\(\)\.taxableValue\.toFixed\(2\)/g, replace: 'calculateTotals().taxableValue.toLocaleString(\'en-IN\', { minimumFractionDigits: 2, maximumFractionDigits: 2 })' },
  { search: /calculateTotals\(\)\.igst\.toFixed\(2\)/g, replace: 'calculateTotals().igst.toLocaleString(\'en-IN\', { minimumFractionDigits: 2, maximumFractionDigits: 2 })' },
  { search: /calculateTotals\(\)\.cgst\.toFixed\(2\)/g, replace: 'calculateTotals().cgst.toLocaleString(\'en-IN\', { minimumFractionDigits: 2, maximumFractionDigits: 2 })' },
  { search: /calculateTotals\(\)\.sgst\.toFixed\(2\)/g, replace: 'calculateTotals().sgst.toLocaleString(\'en-IN\', { minimumFractionDigits: 2, maximumFractionDigits: 2 })' },
  { search: /calculateTotals\(\)\.cess\.toFixed\(2\)/g, replace: 'calculateTotals().cess.toLocaleString(\'en-IN\', { minimumFractionDigits: 2, maximumFractionDigits: 2 })' },
  { search: /calculateTotals\(\)\.invoiceValue\.toFixed\(2\)/g, replace: 'calculateTotals().invoiceValue.toLocaleString(\'en-IN\', { minimumFractionDigits: 2, maximumFractionDigits: 2 })' },
  { search: /value=\{paymentTdsIncomeTax\}/g, replace: 'value={Number(paymentTdsIncomeTax || 0).toLocaleString(\'en-IN\', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}' },
  { search: /value=\{paymentAdvance\}/g, replace: 'value={Number(paymentAdvance || 0).toLocaleString(\'en-IN\', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}' },
  { search: /value=\{paymentPayable\}/g, replace: 'value={Number(paymentPayable || 0).toLocaleString(\'en-IN\', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}' },
  { search: /value=\{purchaseTdsIt\}/g, replace: 'value={Number(purchaseTdsIt || 0).toLocaleString(\'en-IN\', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}' },
  { search: /value=\{purchaseAdvancePaid\}/g, replace: 'value={Number(purchaseAdvancePaid || 0).toLocaleString(\'en-IN\', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}' },
  { search: /value=\{cnAdvanceAmount\}/g, replace: 'value={Number(cnAdvanceAmount || 0).toLocaleString(\'en-IN\', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}' },
  { search: /value=\{cnPayableAmount\}/g, replace: 'value={Number(cnPayableAmount || 0).toLocaleString(\'en-IN\', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}' },
  { search: /value=\{cnTdsIt\}/g, replace: 'value={Number(cnTdsIt || 0).toLocaleString(\'en-IN\', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}' },
  { search: /\(invVal \+ tdsIT - tdsGst\)\.toFixed\(2\)/g, replace: '(invVal + tdsIT - tdsGst).toLocaleString(\'en-IN\', { minimumFractionDigits: 2, maximumFractionDigits: 2 })' },
  { search: /\(invVal - tdsIT - tdsGst\)\.toFixed\(2\)/g, replace: '(invVal - tdsIT - tdsGst).toLocaleString(\'en-IN\', { minimumFractionDigits: 2, maximumFractionDigits: 2 })' },
];

files.forEach(path => {
  if (fs.existsSync(path)) {
    let content = fs.readFileSync(path, 'utf8');
    let changed = false;
    
    // Also replace the sum expressions used in Vouchers.tsx
    const sumRegexes = [
      { search: /\(purchaseItems\.reduce\(\(sum, item\) => sum \+ \(Number\(item\.taxableValue\) \|\| 0\), 0\)\)\.toFixed\(2\)/g, replace: '(purchaseItems.reduce((sum, item) => sum + (Number(item.taxableValue) || 0), 0)).toLocaleString(\'en-IN\', { minimumFractionDigits: 2, maximumFractionDigits: 2 })' },
      { search: /\(purchaseItems\.reduce\(\(sum, item\) => sum \+ \(Number\(item\.igst\) \|\| 0\), 0\)\)\.toFixed\(2\)/g, replace: '(purchaseItems.reduce((sum, item) => sum + (Number(item.igst) || 0), 0)).toLocaleString(\'en-IN\', { minimumFractionDigits: 2, maximumFractionDigits: 2 })' },
      { search: /\(purchaseItems\.reduce\(\(sum, item\) => sum \+ \(Number\(item\.cgst\) \|\| 0\), 0\)\)\.toFixed\(2\)/g, replace: '(purchaseItems.reduce((sum, item) => sum + (Number(item.cgst) || 0), 0)).toLocaleString(\'en-IN\', { minimumFractionDigits: 2, maximumFractionDigits: 2 })' },
      { search: /\(purchaseItems\.reduce\(\(sum, item\) => sum \+ \(Number\(item\.sgst\) \|\| 0\), 0\)\)\.toFixed\(2\)/g, replace: '(purchaseItems.reduce((sum, item) => sum + (Number(item.sgst) || 0), 0)).toLocaleString(\'en-IN\', { minimumFractionDigits: 2, maximumFractionDigits: 2 })' },
      { search: /\(purchaseItems\.reduce\(\(sum, item\) => sum \+ \(Number\(item\.cess\) \|\| 0\), 0\)\)\.toFixed\(2\)/g, replace: '(purchaseItems.reduce((sum, item) => sum + (Number(item.cess) || 0), 0)).toLocaleString(\'en-IN\', { minimumFractionDigits: 2, maximumFractionDigits: 2 })' },
      { search: /\(purchaseItems\.reduce\(\(sum, item\) => sum \+ \(Number\(item\.invoiceValue\) \|\| 0\), 0\)\)\.toFixed\(2\)/g, replace: '(purchaseItems.reduce((sum, item) => sum + (Number(item.invoiceValue) || 0), 0)).toLocaleString(\'en-IN\', { minimumFractionDigits: 2, maximumFractionDigits: 2 })' },
      { search: /\(\n?\s*purchaseItems\.reduce\(\(sum, item\) => sum \+ \(Number\(item\.invoiceValue\) \|\| 0\), 0\)\n?\s*\+ \(purchaseTaxIsTcs \? \(Number\(purchaseTdsIt\) \|\| 0\) : -\(Number\(purchaseTdsIt\) \|\| 0\)\)\n?\s*\)\.toFixed\(2\)/g, replace: '(\n                          purchaseItems.reduce((sum, item) => sum + (Number(item.invoiceValue) || 0), 0)\n                          + (purchaseTaxIsTcs ? (Number(purchaseTdsIt) || 0) : -(Number(purchaseTdsIt) || 0))\n                        ).toLocaleString(\'en-IN\', { minimumFractionDigits: 2, maximumFractionDigits: 2 })' },
      { search: /\(\n?\s*purchaseItems\.reduce\(\(sum, item\) => sum \+ \(Number\(item\.invoiceValue\) \|\| 0\), 0\)\n?\s*\+ \(purchaseTaxIsTcs \? \(Number\(purchaseTdsIt\) \|\| 0\) : -\(Number\(purchaseTdsIt\) \|\| 0\)\)\n?\s*- \(Number\(purchaseAdvancePaid\) \|\| 0\)\n?\s*\)\.toFixed\(2\)/g, replace: '(\n                          purchaseItems.reduce((sum, item) => sum + (Number(item.invoiceValue) || 0), 0)\n                          + (purchaseTaxIsTcs ? (Number(purchaseTdsIt) || 0) : -(Number(purchaseTdsIt) || 0))\n                          - (Number(purchaseAdvancePaid) || 0)\n                        ).toLocaleString(\'en-IN\', { minimumFractionDigits: 2, maximumFractionDigits: 2 })' }
    ];

    replacements.concat(sumRegexes).forEach(r => {
      if (r.search.test(content)) {
        content = content.replace(r.search, r.replace);
        changed = true;
      }
    });

    if (changed) {
      fs.writeFileSync(path, content);
      console.log('Updated:', path);
    }
  }
});
