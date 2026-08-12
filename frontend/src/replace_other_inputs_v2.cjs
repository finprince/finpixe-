const fs = require('fs');
const path = require('path');

const dir = 'd:/finpixe/Ai_Accounting_35/AI-accounting-0.03/frontend/src/pages/Vouchers';
const files = fs.readdirSync(dir).filter(f => f.endsWith('.tsx')).map(f => path.join(dir, f));

files.forEach(file => {
  let content = fs.readFileSync(file, 'utf8');
  let originalContent = content;

  let changed = false;

  const replaceInput = (searchStr, replaceFn) => {
    let index = 0;
    while (true) {
      index = content.indexOf(searchStr, index);
      if (index === -1) break;
      
      const startIdx = content.lastIndexOf('<input', index);
      if (startIdx === -1 || startIdx < index - 1500) { index += searchStr.length; continue; } 
      
      const endIdx = content.indexOf('/>', index);
      if (endIdx === -1 || endIdx > index + 1500) { index += searchStr.length; continue; }
      
      const fullTag = content.substring(startIdx, endIdx + 2);
      
      if (!fullTag.includes('<NumericFormat') && !fullTag.includes('toLocaleString')) {
          const newTag = replaceFn(fullTag);
          content = content.substring(0, startIdx) + newTag + content.substring(endIdx + 2);
          changed = true;
          index = startIdx + newTag.length;
      } else {
          index = endIdx + 2;
      }
    }
  };

  const genericReplace = (tag) => {
    return tag
      .replace('<input', '<NumericFormat')
      .replace(/type="number"\s*onWheel=\{\(e\)\s*=>\s*e\.currentTarget\.blur\(\)\}/g, 'thousandSeparator="," thousandsGroupStyle="lakh" decimalScale={2} fixedDecimalScale={true} allowNegative={false}')
      .replace(/type="number"/g, 'thousandSeparator="," thousandsGroupStyle="lakh" decimalScale={2} fixedDecimalScale={true} allowNegative={false}')
      .replace(/onChange=\{\(e\) =>/g, 'onValueChange={(values) =>')
      .replace(/onChange=\{e =>/g, 'onValueChange={values =>')
      .replace(/e\.target\.value/g, 'values.value')
      .replace(/min="0"/g, '');
  };

  replaceInput("value={topAmount || ''}", genericReplace);
  replaceInput("value={singleAdvanceAmount || ''}", genericReplace);
  replaceInput("value={txn.receipt || ''}", genericReplace);
  replaceInput("value={txn.payment || ''}", genericReplace);
  replaceInput("value={row.amount || ''}", genericReplace);
  replaceInput("value={simpleAmount}", genericReplace);
  replaceInput("value={advanceAmount}", genericReplace);
  replaceInput("value={bulkTotalReceipt || ''}", genericReplace);
  replaceInput("value={bulkTotalPayment || ''}", genericReplace);

  if (changed) {
    fs.writeFileSync(file, content);
    console.log('Updated:', file);
  }
});
