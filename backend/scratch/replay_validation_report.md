# Known Corrupted Invoice Replay Validation Report
**Date:** 2026-07-13
**Target Invoices:** [1009461, 1009480, 1009527, 1009545, 1009563]

## Verification Walkthrough

### Record 1009461 (Invoice: EIS/25-26/1014)
----------------------------------------
- **Classification:** `F: Frozen/Corrected`
- **Mode B Correctable:** `True`

#### Item-by-Item GST Correction Comparison
| Description | Before Rates (C/S) | Before CGST/SGST | After Rates (C/S) | After CGST/SGST | Status |
|:---|:---:|:---:|:---:|:---:|:---:|
| Lab Coat Blue Colour | 5.0% / 5.0% | Rs.22.50 / Rs.22.50 | 2.5% / 2.5% | Rs.11.25 / Rs.11.25 | **CHANGED** |
| Knitted Gloves | 5.0% / 5.0% | Rs.14.40 / Rs.14.40 | 2.5% / 2.5% | Rs.7.20 / Rs.7.20 | **CHANGED** |
| Lathe Chuck Key 7/16" | 18.0% / 18.0% | Rs.48.60 / Rs.48.60 | 9.0% / 9.0% | Rs.24.30 / Rs.24.30 | **CHANGED** |

#### Accounting Invariant Reconciliation
| Metric | Before Correction | After Correction | Match? |
|:---|:---:|:---:|:---:|
| Header Taxable Value | 923.00 | 923.00 | [PASS] Yes |
| Header CGST | 42.75 | 42.75 | [PASS] Yes |
| Header SGST | 42.75 | 42.75 | [PASS] Yes |
| Header IGST | 0.00 | 0.00 | [PASS] Yes |
| Invoice Total | 1008.50 | 1008.50 | [PASS] Yes |
| Discount | 0.00 | 0.00 | [PASS] Yes |
| CESS | 0.00 | 0.00 | [PASS] Yes |
| Round-off | 0.00 | 0.00 | [PASS] Yes |

#### GST Validation Replay Summary
- **Before Correction:** Status = `FAIL`, Expected GST = `Rs.171.00`, Current GST = `Rs.85.50`, Mismatch = `YES`
- **After Correction:** Status = `PASS`, Expected GST = `Rs.85.50`, Current GST = `Rs.85.50`, Mismatch = `NO`

#### Regression Validation
[PASS] **No regressions detected.** All item structures and rates remain completely stable.
**Result:** [PASS] SUCCESS

### Record 1009480 (Invoice: UMT25-26/091)
----------------------------------------
- **Classification:** `F: Frozen/Corrected`
- **Mode B Correctable:** `False`

#### Item-by-Item GST Correction Comparison
| Description | Before Rates (C/S) | Before CGST/SGST | After Rates (C/S) | After CGST/SGST | Status |
|:---|:---:|:---:|:---:|:---:|:---:|
| Service charges for Tool charger Problem for Toyok Vmc | 9.0% / 9.0% | Rs.450.00 / Rs.450.00 | 9.0% / 9.0% | Rs.450.00 / Rs.450.00 | Unchanged |
| Service charges for Turret assemble and Chuck Not Working for HAAS CVC | 9.0% / 9.0% | Rs.450.00 / Rs.450.00 | 9.0% / 9.0% | Rs.450.00 / Rs.450.00 | Unchanged |

#### Accounting Invariant Reconciliation
| Metric | Before Correction | After Correction | Match? |
|:---|:---:|:---:|:---:|
| Header Taxable Value | 4500.00 | 4500.00 | [PASS] Yes |
| Header CGST | 450.00 | 450.00 | [PASS] Yes |
| Header SGST | 450.00 | 450.00 | [PASS] Yes |
| Header IGST | 0.00 | 0.00 | [PASS] Yes |
| Invoice Total | 5900.00 | 5900.00 | [PASS] Yes |
| Discount | 0.00 | 0.00 | [PASS] Yes |
| CESS | 0.00 | 0.00 | [PASS] Yes |
| Round-off | 0.00 | 0.00 | [PASS] Yes |

#### GST Validation Replay Summary
- **Before Correction:** Status = `PASS`, Expected GST = `Rs.900.00`, Current GST = `Rs.900.00`, Mismatch = `NO`
- **After Correction:** Status = `PASS`, Expected GST = `Rs.900.00`, Current GST = `Rs.900.00`, Mismatch = `NO`

#### Regression Validation
[PASS] **No regressions detected.** All item structures and rates remain completely stable.
**Result:** [PASS] SKIPPED CORRECTLY

### Record 1009527 (Invoice: EIS/25-26/1014)
----------------------------------------
- **Classification:** `F: Frozen/Corrected`
- **Mode B Correctable:** `True`

#### Item-by-Item GST Correction Comparison
| Description | Before Rates (C/S) | Before CGST/SGST | After Rates (C/S) | After CGST/SGST | Status |
|:---|:---:|:---:|:---:|:---:|:---:|
| Lab Coat Blue Colour | 5.0% / 5.0% | Rs.22.50 / Rs.22.50 | 2.5% / 2.5% | Rs.11.25 / Rs.11.25 | **CHANGED** |
| Knitted Gloves | 5.0% / 5.0% | Rs.14.40 / Rs.14.40 | 2.5% / 2.5% | Rs.7.20 / Rs.7.20 | **CHANGED** |
| Lathe Chuck Key 7/16" | 18.0% / 18.0% | Rs.48.60 / Rs.48.60 | 9.0% / 9.0% | Rs.24.30 / Rs.24.30 | **CHANGED** |

#### Accounting Invariant Reconciliation
| Metric | Before Correction | After Correction | Match? |
|:---|:---:|:---:|:---:|
| Header Taxable Value | 923.00 | 923.00 | [PASS] Yes |
| Header CGST | 42.75 | 42.75 | [PASS] Yes |
| Header SGST | 42.75 | 42.75 | [PASS] Yes |
| Header IGST | 0.00 | 0.00 | [PASS] Yes |
| Invoice Total | 1008.50 | 1008.50 | [PASS] Yes |
| Discount | 0.00 | 0.00 | [PASS] Yes |
| CESS | 0.00 | 0.00 | [PASS] Yes |
| Round-off | 0.00 | 0.00 | [PASS] Yes |

#### GST Validation Replay Summary
- **Before Correction:** Status = `FAIL`, Expected GST = `Rs.171.00`, Current GST = `Rs.85.50`, Mismatch = `YES`
- **After Correction:** Status = `PASS`, Expected GST = `Rs.85.50`, Current GST = `Rs.85.50`, Mismatch = `NO`

#### Regression Validation
[PASS] **No regressions detected.** All item structures and rates remain completely stable.
**Result:** [PASS] SUCCESS

### Record 1009545 (Invoice: EIS/25-26/1014)
----------------------------------------
- **Classification:** `F: Frozen/Corrected`
- **Mode B Correctable:** `True`

#### Item-by-Item GST Correction Comparison
| Description | Before Rates (C/S) | Before CGST/SGST | After Rates (C/S) | After CGST/SGST | Status |
|:---|:---:|:---:|:---:|:---:|:---:|
| Lab Coat Blue Colour | 5.0% / 5.0% | Rs.22.50 / Rs.22.50 | 2.5% / 2.5% | Rs.11.25 / Rs.11.25 | **CHANGED** |
| Knitted Gloves | 5.0% / 5.0% | Rs.14.40 / Rs.14.40 | 2.5% / 2.5% | Rs.7.20 / Rs.7.20 | **CHANGED** |
| Lathe Chuck Key 7/16" | 18.0% / 18.0% | Rs.48.60 / Rs.48.60 | 9.0% / 9.0% | Rs.24.30 / Rs.24.30 | **CHANGED** |

#### Accounting Invariant Reconciliation
| Metric | Before Correction | After Correction | Match? |
|:---|:---:|:---:|:---:|
| Header Taxable Value | 923.00 | 923.00 | [PASS] Yes |
| Header CGST | 42.75 | 42.75 | [PASS] Yes |
| Header SGST | 42.75 | 42.75 | [PASS] Yes |
| Header IGST | 0.00 | 0.00 | [PASS] Yes |
| Invoice Total | 1008.50 | 1008.50 | [PASS] Yes |
| Discount | 0.00 | 0.00 | [PASS] Yes |
| CESS | 0.00 | 0.00 | [PASS] Yes |
| Round-off | 0.00 | 0.00 | [PASS] Yes |

#### GST Validation Replay Summary
- **Before Correction:** Status = `FAIL`, Expected GST = `Rs.171.00`, Current GST = `Rs.85.50`, Mismatch = `YES`
- **After Correction:** Status = `PASS`, Expected GST = `Rs.85.50`, Current GST = `Rs.85.50`, Mismatch = `NO`

#### Regression Validation
[PASS] **No regressions detected.** All item structures and rates remain completely stable.
**Result:** [PASS] SUCCESS

### Record 1009563 (Invoice: EIS/25-26/1014)
----------------------------------------
- **Classification:** `F: Frozen/Corrected`
- **Mode B Correctable:** `True`

#### Item-by-Item GST Correction Comparison
| Description | Before Rates (C/S) | Before CGST/SGST | After Rates (C/S) | After CGST/SGST | Status |
|:---|:---:|:---:|:---:|:---:|:---:|
| Lab Coat Blue Colour | 5.0% / 5.0% | Rs.22.50 / Rs.22.50 | 2.5% / 2.5% | Rs.11.25 / Rs.11.25 | **CHANGED** |
| Knitted Gloves | 5.0% / 5.0% | Rs.14.40 / Rs.14.40 | 2.5% / 2.5% | Rs.7.20 / Rs.7.20 | **CHANGED** |
| Lathe Chuck Key 7/16" | 18.0% / 18.0% | Rs.48.60 / Rs.48.60 | 9.0% / 9.0% | Rs.24.30 / Rs.24.30 | **CHANGED** |

#### Accounting Invariant Reconciliation
| Metric | Before Correction | After Correction | Match? |
|:---|:---:|:---:|:---:|
| Header Taxable Value | 923.00 | 923.00 | [PASS] Yes |
| Header CGST | 42.75 | 42.75 | [PASS] Yes |
| Header SGST | 42.75 | 42.75 | [PASS] Yes |
| Header IGST | 0.00 | 0.00 | [PASS] Yes |
| Invoice Total | 1008.50 | 1008.50 | [PASS] Yes |
| Discount | 0.00 | 0.00 | [PASS] Yes |
| CESS | 0.00 | 0.00 | [PASS] Yes |
| Round-off | 0.00 | 0.00 | [PASS] Yes |

#### GST Validation Replay Summary
- **Before Correction:** Status = `FAIL`, Expected GST = `Rs.171.00`, Current GST = `Rs.85.50`, Mismatch = `YES`
- **After Correction:** Status = `PASS`, Expected GST = `Rs.85.50`, Current GST = `Rs.85.50`, Mismatch = `NO`

#### Regression Validation
[PASS] **No regressions detected.** All item structures and rates remain completely stable.
**Result:** [PASS] SUCCESS

## Section 8: Confusion Matrix

```
                  Predicted
               Correct   Corrupt
  Actual Correct     1        0
  Actual Corrupt     0        4
```
- **Precision:** 100.00%
- **Recall:** 100.00%
- **False Positive Rate:** 0.00%
- **False Negative Rate:** 0.00%


## Section 9: Final Verdict
### **VERDICT: SAFE FOR PRODUCTION**

- `[PASS]` Every true Mode B corrupted invoice corrected successfully: 4/4
- `[PASS]` GST validation passes after correction: True
- `[PASS]` Header totals remain unchanged: True
- `[PASS]` Grand totals remain unchanged: True
- `[PASS]` Voucher totals remain unchanged: True
- `[PASS]` No unrelated fields changed: True
- `[PASS]` No accounting regression occurred: True