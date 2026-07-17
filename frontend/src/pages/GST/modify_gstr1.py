import re

with open('GSTR1.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

b2cs_drilldown = '''                            {selectedB2csRow ? (
                                <div>
                                    <div className="flex items-center mb-6 border-b pb-4">
                                        <button 
                                            onClick={() => setSelectedB2csRow(null)}
                                            className="mr-4 px-4 py-2 text-sm font-semibold text-indigo-600 bg-indigo-50 rounded-xl hover:bg-indigo-100 transition-colors flex items-center gap-2"
                                        >
                                            <span className="text-lg leading-none">&larr;</span> Back to Summary
                                        </button>
                                        <div>
                                            <h3 className="text-xl font-bold text-gray-800 border-none pb-0 mb-0">
                                                Invoices for Place of Supply: {selectedB2csRow.place_of_supply || selectedB2csRow.revised_pos}
                                            </h3>
                                            <p className="text-sm text-gray-500 mt-1">
                                                Click on an invoice to view or amend it.
                                            </p>
                                        </div>
                                    </div>
                                    <div className="erp-table-container">
                                        <table className="erp-table w-full">
                                            <thead>
                                                <tr>
                                                    <th className="px-4 py-3 border-b text-left text-sm font-semibold text-gray-600">Invoice No</th>
                                                    <th className="px-4 py-3 border-b text-left text-sm font-semibold text-gray-600">Date</th>
                                                    <th className="px-4 py-3 border-b text-right text-sm font-semibold text-gray-600">Value</th>
                                                    <th className="px-4 py-3 border-b text-center text-sm font-semibold text-gray-600">Status</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {(selectedB2csRow.vouchers || []).map((v: any) => (
                                                    <tr
                                                        key={v.id}
                                                        className="hover:bg-indigo-50 cursor-pointer transition-colors"
                                                        onClick={() => {
                                                            setSelectedB2csRow(null);
                                                            if (setViewVoucherData && onNavigate) {
                                                                setViewVoucherData({
                                                                    ...v,
                                                                    voucherNo: v.invoice_no,
                                                                    type: 'Sales',
                                                                    source: 'b2cs_drilldown',
                                                                    _viewAsGSTFiled: v.amendment_date ? true : false
                                                                });
                                                                onNavigate('Vouchers');
                                                            }
                                                        }}
                                                    >
                                                        <td className="px-4 py-3 border-b text-sm font-medium text-indigo-600">{v.invoice_no}</td>
                                                        <td className="px-4 py-3 border-b text-sm text-gray-600">{v.invoice_date}</td>
                                                        <td className="px-4 py-3 border-b text-sm text-gray-800 text-right font-medium">?{Number(v.invoice_value).toFixed(2)}</td>
                                                        <td className="px-4 py-3 border-b text-sm text-center">
                                                            {v.amendment_date ? (
                                                                <span className="px-2 py-1 bg-amber-50 text-amber-700 border border-amber-200 rounded-full text-[10px] font-bold uppercase">Amended</span>
                                                            ) : v.gst_registered === 'Yes' ? (
                                                                <span className="px-2 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full text-[10px] font-bold uppercase">GST Filed</span>
                                                            ) : (
                                                                <span className="px-2 py-1 bg-gray-100 text-gray-600 border border-gray-200 rounded-full text-[10px] font-bold uppercase">Pending</span>
                                                            )}
                                                        </td>
                                                    </tr>
                                                ))}
                                                {(!selectedB2csRow.vouchers || selectedB2csRow.vouchers.length === 0) && (
                                                    <tr>
                                                        <td colSpan={4} className="px-4 py-8 text-center text-gray-500">
                                                            No detailed invoices found.
                                                        </td>
                                                    </tr>
                                                )}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            ) : (
                                <div>'''

# Replace B2CS
content = content.replace('''                    {!isLoading && activeSubTab === 'B2CS' && (
                        <div>
                            <h3 className="erp-section-title border-none pb-0 mb-4">B2C Small - Summary of Small Invoices</h3>''', 
                            '''                    {!isLoading && activeSubTab === 'B2CS' && (
                        <div>
''' + b2cs_drilldown + '''
                                    <h3 className="erp-section-title border-none pb-0 mb-4">B2C Small - Summary of Small Invoices</h3>''')

# Close B2CS
content = content.replace('''                                </table>
                            </div>
                        </div>
                    )}

                    {!isLoading && activeSubTab === 'B2CSA' && (''',
'''                                </table>
                            </div>
                                </div>
                            )}
                        </div>
                    )}

                    {!isLoading && activeSubTab === 'B2CSA' && (''')

# Replace B2CSA
content = content.replace('''                    {!isLoading && activeSubTab === 'B2CSA' && (
                        <div>
                            <h3 className="erp-section-title border-none pb-0 mb-4">B2CSA - B2C Small (Amendment)</h3>''',
                            '''                    {!isLoading && activeSubTab === 'B2CSA' && (
                        <div>
''' + b2cs_drilldown + '''
                                    <h3 className="erp-section-title border-none pb-0 mb-4">B2CSA - B2C Small (Amendment)</h3>''')

# Close B2CSA
content = content.replace('''                                </table>
                            </div>
                        </div>
                    )}

                    {!isLoading && activeSubTab === 'CDNR' && (''',
'''                                </table>
                            </div>
                                </div>
                            )}
                        </div>
                    )}

                    {!isLoading && activeSubTab === 'CDNR' && (''')

# Remove Modal
modal_start = "{/* B2CS / B2CSA Sub-Vouchers Drilldown Modal */}"
idx = content.find(modal_start)
if idx != -1:
    end_idx = content.find("</div>\\n    );\\n}", idx)
    if end_idx != -1:
        content = content[:idx] + content[end_idx:]

with open('GSTR1.tsx', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done")
