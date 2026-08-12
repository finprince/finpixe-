const fs = require('fs');

const files = [
  'd:/finpixe/Ai_Accounting_35/AI-accounting-0.03/frontend/src/pages/Vouchers/PaymentVoucherBulk.tsx',
  'd:/finpixe/Ai_Accounting_35/AI-accounting-0.03/frontend/src/pages/Vouchers/PaymentVoucherSingle.tsx',
  'd:/finpixe/Ai_Accounting_35/AI-accounting-0.03/frontend/src/pages/Vouchers/ReceiptVoucher.tsx',
  'd:/finpixe/Ai_Accounting_35/AI-accounting-0.03/frontend/src/pages/Vouchers/Vouchers.tsx',
];

files.forEach(file => {
  if (fs.existsSync(file)) {
    let content = fs.readFileSync(file, 'utf8');
    
    // Fix the broken import syntax
    content = content.replace("import React,\nimport { NumericFormat } from 'react-number-format';\n {", "import React, {");
    
    // Add it cleanly after the react import
    if (!content.includes("import { NumericFormat } from 'react-number-format';")) {
        content = content.replace("import React, {", "import { NumericFormat } from 'react-number-format';\nimport React, {");
    }

    // Sometimes it might just be "import React," if it didn't have "{". Let's cover that if it exists.
    content = content.replace("import React,\nimport { NumericFormat } from 'react-number-format';\n", "import { NumericFormat } from 'react-number-format';\nimport React,");

    fs.writeFileSync(file, content);
    console.log('Fixed:', file);
  }
});
