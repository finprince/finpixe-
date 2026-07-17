with open('views_gst.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("'port_code': '',", "'port_code': v.port_code or '',")
content = content.replace("'shipping_bill_number': '',", "'shipping_bill_number': v.shipping_bill_number or '',")
content = content.replace("'shipping_bill_date': '',", "'shipping_bill_date': v.shipping_bill_date or '',")

with open('views_gst.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done")
