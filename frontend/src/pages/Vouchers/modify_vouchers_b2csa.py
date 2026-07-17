with open('Vouchers.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    "if (viewVoucherData?.source === 'b2b_drilldown' || viewVoucherData?.source === 'b2cs_drilldown') {",
    "if (viewVoucherData?.source === 'b2b_drilldown' || viewVoucherData?.source === 'b2cs_drilldown' || viewVoucherData?.source === 'b2csa_drilldown') {"
)

with open('Vouchers.tsx', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done")
