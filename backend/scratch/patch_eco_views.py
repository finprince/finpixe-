import re
import os

file_path = r'd:\finpixe\Ai_Accounting_28\AI-accounting-0.03\backend\accounting\views_gst.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

endpoints = ['ecob2b', 'ecob2c', 'ecourp2b', 'ecourp2c', 'ecoab2b', 'ecoab2c', 'ecoaurp2b', 'ecoaurp2c']

for ep in endpoints:
    pattern = r"(def " + ep + r"\(self, request\):.*?)data\.append\(\{([^}]+)\}\)"
    
    def repl(m):
        func_body = m.group(1)
        dict_body = m.group(2)
        
        # Add missing fields if not present
        if "'is_ecommerce_operator'" not in dict_body:
            dict_body = dict_body.rstrip() + ",\n                'is_ecommerce_operator': True"
        if "'is_ecommerce_sales'" not in dict_body:
            dict_body = dict_body + ",\n                'is_ecommerce_sales': True"
        if "'supplier_name'" not in dict_body:
            dict_body = dict_body + ",\n                'supplier_name': getattr(v, 'third_party_supplier_name', '')"
            
        return f"{func_body}data.append({{{dict_body}}})"
        
    content = re.sub(pattern, repl, content, flags=re.DOTALL)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done")
