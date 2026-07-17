with open('GSTR1.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# The second occurrence of b2cs_drilldown is in B2CSA
parts = content.split("source: 'b2cs_drilldown',")
if len(parts) == 3:
    new_content = parts[0] + "source: 'b2cs_drilldown'," + parts[1] + "source: 'b2csa_drilldown',\n                                                                    _viewAsGSTFiled: false\n                                                                });\n                                                                onNavigate('Vouchers');"
    
    # We need to correctly replace the _viewAsGSTFiled line in the second block
    # Let's use regex to be safe
    import re
    # Find the B2CSA block by looking for "B2CSA - B2C Small (Amendment)"
    b2csa_idx = content.find("B2CSA - B2C Small (Amendment)")
    if b2csa_idx != -1:
        # Find the source: 'b2cs_drilldown' after this index
        source_idx = content.find("source: 'b2cs_drilldown',", b2csa_idx)
        if source_idx != -1:
            # Replace source
            content = content[:source_idx] + "source: 'b2csa_drilldown'," + content[source_idx + len("source: 'b2cs_drilldown',"):]
            
            # Find the _viewAsGSTFiled line after the new source
            view_idx = content.find("_viewAsGSTFiled: v.amendment_date ? true : false", source_idx)
            if view_idx != -1:
                content = content[:view_idx] + "_viewAsGSTFiled: false" + content[view_idx + len("_viewAsGSTFiled: v.amendment_date ? true : false"):]

with open('GSTR1.tsx', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done")
