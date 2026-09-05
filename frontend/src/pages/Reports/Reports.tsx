import finpixeLogo from '../../assets/branding/logo';
import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { usePermissions } from '../../hooks/usePermissions';
import type { Ledger, Voucher, StockItem, SalesPurchaseVoucher, LedgerGroupMaster, Page } from '../../types';
import { showError, showSuccess } from '../../utils/toast';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line, AreaChart, Area } from 'recharts';
import { apiService } from '../../services/api';
import { httpClient } from '../../services/httpClient';
import { UniversalWorkspaceLayout } from '../../components/layouts/UniversalWorkspaceLayout';
import DateInput from '../../components/common/DateInput';
import { formatDate } from '../../utils/formatting';

const API_BASE_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:5003';


// Ledger Selector Component
interface LedgerSelectorProps {
  selectedValue: string;
  onChange: (value: string) => void;
  groups: LedgerGroupMaster[];
  ledgers: Ledger[];
}

const LedgerSelector: React.FC<LedgerSelectorProps> = ({
  selectedValue,
  onChange,
  groups,
  ledgers
}) => {
  return (
    <select
      value={selectedValue}
      onChange={(e) => onChange(e.target.value)}
      className="erp-select"
    >
      <option value="all">All Ledgers</option>
      <optgroup label="Groups">
        {groups.map(g => <option key={g.id || g.name} value={`group:${g.name}`}>{g.name}</option>)}
      </optgroup>
      <optgroup label="Ledgers">
        {ledgers.map(l => <option key={l.id || l.name} value={`ledger:${l.name}`}>{l.name}</option>)}
      </optgroup>
    </select>
  );
};

interface ReportsPageProps {
  vouchers: Voucher[];
  entries?: any[];
  ledgers: Ledger[];
  ledgerGroups: LedgerGroupMaster[];
  stockItems: StockItem[];
  onNavigate?: (page: Page, params?: any) => void;
  setViewVoucherData?: (data: any) => void;
  navParams?: any;
}


type ReportType = 'DayBook' | 'LedgerReport' | 'TrialBalance' | 'ProfitAndLoss' | 'BalanceSheet' | 'StockSummary' | 'GSTReports' | 'AIReport' | 'GSTR1';

type GSTForm = 'GSTR-1' | 'GSTR-2' | 'GSTR-2A' | 'GSTR-2B' | 'GSTR-3B' | 'GSTR-4' | 'GSTR-5' | 'GSTR-5A' | 'GSTR-6' | 'GSTR-7' | 'GSTR-8' | 'GSTR-9' | 'GSTR-9A' | 'GSTR-9C' | 'GSTR-10';

type GSTTab = 'B2B' | 'B2C-L' | 'B2C-S' | 'Exports' | 'CDN' | 'Advances' | 'ITC-Eligible' | 'ITC-Ineligible' | 'RCM-Liability' | 'ITC-Available' | 'ITC-Reversal' | 'Outward' | 'ITC' | 'Payment';

const formatToDMY = (dateVal: any) => {
  if (!dateVal) return '-';
  const str = String(dateVal).trim();
  if (!str || str === '-') return '-';
  const match = str.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (match) {
    return `${parseInt(match[3])}/${parseInt(match[2])}/${match[1]}`;
  }
  try {
    const parts = str.split(/[\/\-]/);
    if (parts.length === 3) {
      if (parts[0].length === 4) {
        return `${parseInt(parts[2])}/${parseInt(parts[1])}/${parts[0]}`;
      } else if (parts[2].length === 4) {
        return `${parseInt(parts[0])}/${parseInt(parts[1])}/${parts[2]}`;
      }
    }
  } catch (e) { }
  return str;
};

/** Normalize raw backend voucher_type strings to human-readable labels */
const normalizeVoucherType = (raw: string | undefined | null): string => {
  if (!raw) return '';
  const typeMap: Record<string, string> = {
    'DEBIT_NOTE': 'Debit Note',
    'debit_note': 'Debit Note',
    'debit note': 'Debit Note',
    'CREDIT_NOTE': 'Credit Note',
    'credit_note': 'Credit Note',
    'credit note': 'Credit Note',
    'PURCHASE_VOUCHER': 'Purchase',
    'SALES_VOUCHER': 'Sales',
    'PAYMENT_VOUCHER': 'Payment',
    'RECEIPT_VOUCHER': 'Receipt',
    'CONTRA_VOUCHER': 'Contra',
    'JOURNAL_VOUCHER': 'Journal',
    'EXPENSE_VOUCHER': 'Expenses',
    'EXPENSE': 'Expenses',
    'expense': 'Expenses',
  };
  return typeMap[raw] || typeMap[raw.toLowerCase()] || raw;
};

/** Flexible reference/voucher number matcher supporting zero-padding variations and field aliases */
const matchRefOrVoucherNo = (entry: any, query: string): boolean => {
  if (!query || !query.trim()) return true;
  const q = query.toLowerCase().trim();
  const raw = entry?.rawVoucher || entry || {};
  const candidates = [
    entry?.referenceNo,
    entry?.voucherNo,
    raw.reference_number,
    raw.referenceNo,
    raw.ref_no,
    raw.voucher_number,
    raw.voucherNo,
    raw.voucher_no,
    raw.purchase_voucher_no,
    raw.voucher_number_display
  ].filter((val): val is string | number => val !== undefined && val !== null && val !== '' && val !== '-').map(s => String(s).toLowerCase());

  if (candidates.some(c => c.includes(q))) return true;

  // Normalize leading zeros in numeric sequences for zero-padding mismatch resilience (e.g. VCN00111 vs VCN000111)
  const normQ = q.replace(/([a-zA-Z])0+([1-9])/g, '$1$2').replace(/^0+/, '');
  if (normQ.length >= 2) {
    for (const c of candidates) {
      const normC = c.replace(/([a-zA-Z])0+([1-9])/g, '$1$2').replace(/^0+/, '');
      if (normC.includes(normQ)) return true;
    }
  }

  return false;
};

const ReportsPage: React.FC<ReportsPageProps> = ({ vouchers = [], entries = [], ledgers = [], ledgerGroups = [], stockItems = [], onNavigate, setViewVoucherData, navParams }) => {
  // Report Options Mapping
  const { hasTabAccess, isSuperuser } = usePermissions();

  // Report Options Mapping
  const allReports: { id: ReportType; label: string }[] = [
    { id: 'DayBook', label: 'DAY BOOK' },
    { id: 'LedgerReport', label: 'LEDGER REPORT' },
    { id: 'TrialBalance', label: 'TRIAL BALANCE' },
    { id: 'ProfitAndLoss', label: 'PROFIT & LOSS' },
    { id: 'BalanceSheet', label: 'BALANCE SHEET' },
    { id: 'StockSummary', label: 'STOCK SUMMARY' },
    { id: 'GSTReports', label: 'GST REPORTS' },
    { id: 'AIReport', label: 'AI REPORT' }
  ];

  // Map ReportType IDs to permission tab names
  const reportPermissionMap: { [key in ReportType]: string } = {
    'DayBook': 'DayBook',
    'LedgerReport': 'LedgerReport',
    'TrialBalance': 'TrialBalance',
    'ProfitAndLoss': 'TrialBalance',
    'BalanceSheet': 'BalanceSheet',
    'StockSummary': 'StockSummary',
    'GSTReports': 'GSTReports',
    'AIReport': 'AIReport',
    'GSTR1': 'GSTReports'
  };

  // Filter Reports based on permissions
  const availableReports = isSuperuser
    ? allReports
    : allReports.filter(report => {
      const permissionTabName = reportPermissionMap[report.id];
      return hasTabAccess('Reports', permissionTabName);
    });

  const defaultReport = navParams?.reportType || (availableReports.length > 0 ? availableReports[0].id : ('DayBook' as ReportType));

  const [reportType, setReportType] = useState<ReportType>(defaultReport);

  // Inspector Drawer State
  const [inspectorState, setInspectorState] = useState<{
    isOpen: boolean;
    title?: string;
    subtitle?: string;
    entityType?: string;
    data?: Record<string, any> | null;
    activityLogs?: Array<{ id: string; user: string; action: string; timestamp: string }>;
    aiRecommendations?: Array<{ id: string; text: string; confidence?: number }>;
  }>({ isOpen: false, title: '', data: null });

  // Ensure active report is valid
  useEffect(() => {
    if (availableReports.length > 0 && !availableReports.find(r => r.id === reportType)) {
      setReportType(availableReports[0].id);
    }
  }, [availableReports, reportType]);

  const [selectedLedger, setSelectedLedger] = useState<string>('all');
  const [startDate, setStartDate] = useState<string>(() => sessionStorage.getItem('reports_startDate') || '');
  const [endDate, setEndDate] = useState<string>(() => sessionStorage.getItem('reports_endDate') || '');

  useEffect(() => {
    sessionStorage.setItem('reports_startDate', startDate);
  }, [startDate]);

  useEffect(() => {
    sessionStorage.setItem('reports_endDate', endDate);
  }, [endDate]);

  // Day Book Filter States
  const [daybookVoucherType, setDaybookVoucherType] = useState<string>('all');
  const [daybookSearch, setDaybookSearch] = useState<string>('');
  const [daybookPartyFilter, setDaybookPartyFilter] = useState<string>('');
  const [daybookMinAmount, setDaybookMinAmount] = useState<string>('');
  const [daybookMaxAmount, setDaybookMaxAmount] = useState<string>('');

  // Ledger Report Filter States
  const [ledgerVoucherType, setLedgerVoucherType] = useState<string>('all');
  const [ledgerStatusFilter, setLedgerStatusFilter] = useState<string>('all');
  const [ledgerSearch, setLedgerSearch] = useState<string>('');
  const [ledgerRefSearch, setLedgerRefSearch] = useState<string>('');
  const [ledgerMinAmount, setLedgerMinAmount] = useState<string>('');
  const [ledgerMaxAmount, setLedgerMaxAmount] = useState<string>('');

  // Drill-down: null = summary view (all ledgers list), string = detail view for that ledger
  const [drillDownLedger, setDrillDownLedger] = useState<string | null>(navParams?.drillDownLedger || null);
  const [drillDownSourceType, setDrillDownSourceType] = useState<string | null>(null);

  useEffect(() => {
    if (navParams) {
      if (navParams.reportType) setReportType(navParams.reportType);
      if (navParams.drillDownLedger !== undefined) setDrillDownLedger(navParams.drillDownLedger);
    } else {
      setReportType(availableReports.length > 0 ? availableReports[0].id : ('DayBook' as ReportType));
      setDrillDownLedger(null);
      setDrillDownSourceType(null);
    }
  }, [navParams]);

  const [selectedSession, setSelectedSession] = useState<string>('all');
  const [selectedSection, setSelectedSection] = useState<string>('all');
  const isTdsTcsLedger = drillDownLedger ? (drillDownLedger.toLowerCase().includes('tds') || drillDownLedger.toLowerCase().includes('tcs')) : false;
  const [drillDownData, setDrillDownData] = useState<any[]>([]);
  const [isDrillDownLoading, setIsDrillDownLoading] = useState<boolean>(false);
  // Transaction detail slide-out panel
  const [selectedTransaction, setSelectedTransaction] = useState<any | null>(null);
  const [voucherDetails, setVoucherDetails] = useState<any | null>(null);
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);
  const [panelActiveTab, setPanelActiveTab] = useState<string>('invoice');
  const [isEditingVoucher, setIsEditingVoucher] = useState<boolean>(false);
  const [editedVoucher, setEditedVoucher] = useState<any>(null);

  const handleViewTransaction = (e: any) => {
    if (setViewVoucherData && onNavigate) {
      setViewVoucherData({ ...e, ledgerName: drillDownLedger });
      onNavigate('Vouchers', { viewVoucher: { ...e, ledgerName: drillDownLedger } });
    } else {
      setSelectedTransaction({ ...e, ledgerName: drillDownLedger });
    }
  };

  useEffect(() => {
    let accountVal = '';
    let partyVal = '';
    let amt = 0;

    if (selectedTransaction) {
      const isPayment = selectedTransaction?.voucherType?.toLowerCase() === 'payment';
      const isReceipt = selectedTransaction?.voucherType?.toLowerCase() === 'receipt';
      const isContra = selectedTransaction?.voucherType?.toLowerCase() === 'contra';
      const isExpense = selectedTransaction?.voucherType?.toLowerCase() === 'expense' || selectedTransaction?.voucherType?.toLowerCase() === 'expenses';

      const ledgerNameClean = (selectedTransaction?.ledgerName || drillDownLedger || '').replace('ledger:', '').replace('group:', '');
      const otherParty = selectedTransaction?.particulars || '';

      if (isPayment) {
        if ((selectedTransaction?.debit || 0) > 0) {
          partyVal = ledgerNameClean;
          accountVal = otherParty;
        } else {
          accountVal = ledgerNameClean;
          partyVal = otherParty;
        }
      } else if (isReceipt) {
        if ((selectedTransaction?.debit || 0) > 0) {
          accountVal = ledgerNameClean;
          partyVal = otherParty;
        } else {
          partyVal = ledgerNameClean;
          accountVal = otherParty;
        }
      } else if (isContra || isExpense) {
        if ((selectedTransaction?.debit || 0) > 0) {
          partyVal = ledgerNameClean;
          accountVal = otherParty;
        } else {
          accountVal = ledgerNameClean;
          partyVal = otherParty;
        }
      } else {
        accountVal = otherParty;
        partyVal = ledgerNameClean;
      }
      amt = selectedTransaction?.debit || selectedTransaction?.credit || 0;
    }

    if (voucherDetails) {
      const copy = JSON.parse(JSON.stringify(voucherDetails));
      if (!copy.date) copy.date = selectedTransaction?.date || '';
      if (!copy.voucher_number && !copy.voucher_no) copy.voucher_number = selectedTransaction?.voucherNo || '';
      if (!copy.amount && !copy.total) {
        copy.amount = amt;
        copy.total = amt;
      }
      if (!copy.account && !copy.fromAccount && !copy.from_account) {
        copy.account = accountVal;
        copy.fromAccount = accountVal;
        copy.from_account = accountVal;
      }
      if (!copy.party && !copy.toAccount && !copy.to_account) {
        copy.party = partyVal;
        copy.toAccount = partyVal;
        copy.to_account = partyVal;
      }
      if (!copy.ref_no && !copy.refNo) {
        copy.ref_no = selectedTransaction?.referenceNo && selectedTransaction?.referenceNo !== '-' ? selectedTransaction.referenceNo : '';
      }
      setEditedVoucher(copy);
    } else if (selectedTransaction) {
      setEditedVoucher({
        date: selectedTransaction?.date || '',
        voucher_type: selectedTransaction?.voucherType || '',
        voucher_number: selectedTransaction?.voucherNo || '',
        amount: amt,
        total: amt,
        account: accountVal,
        party: partyVal,
        ref_no: selectedTransaction?.referenceNo && selectedTransaction?.referenceNo !== '-' ? selectedTransaction.referenceNo : '',
        narration: selectedTransaction?.rawVoucher?.narration || ''
      });
    } else {
      setEditedVoucher(null);
    }
  }, [voucherDetails, selectedTransaction, drillDownLedger]);

  useEffect(() => {
    if (selectedTransaction) {
      const type = selectedTransaction?.voucherType?.toLowerCase() || '';
      if (['payment', 'receipt', 'contra', 'expense'].includes(type)) {
        setPanelActiveTab('voucher');
      } else {
        setPanelActiveTab('invoice');
      }
    }
  }, [selectedTransaction]);

  const handleFieldChange = (path: string, value: any) => {
    setEditedVoucher((prev: any) => {
      if (!prev) return prev;
      const copy = { ...prev };
      const keys = path.split('.');
      let current = copy;
      for (let i = 0; i < keys.length - 1; i++) {
        if (!current[keys[i]]) current[keys[i]] = {};
        current = current[keys[i]];
      }
      current[keys[keys.length - 1]] = value;
      return copy;
    });
  };

  // ─── Backend-backed API state for reports (presentation-only) ───────────
  const [tbData, setTbData] = useState<{ results: any[]; total_debit: number; total_credit: number; is_balanced: boolean } | null>(null);
  const [tbLoading, setTbLoading] = useState(false);
  const [trialBalanceType, setTrialBalanceType] = useState<'opening' | 'closing' | 'with_transactions'>('closing');
  const [expandedTbNodes, setExpandedTbNodes] = useState<Set<string>>(new Set());
  const [hasInitializedTbTree, setHasInitializedTbTree] = useState(false);
  const [bsData, setBsData] = useState<any | null>(null);
  const [bsLoading, setBsLoading] = useState(false);
  const [balanceSheetFormat, setBalanceSheetFormat] = useState<'auto' | 'vertical' | 'horizontal'>('auto');
  const [expandedBsCategories, setExpandedBsCategories] = useState<Set<string>>(new Set());
  const [bsCategoryModal, setBsCategoryModal] = useState<{
    isOpen: boolean;
    title: string;
    items: any[];
  } | null>(null);
  const [selectedBsCategoryInModal, setSelectedBsCategoryInModal] = useState<string | null>(null);
  const [pnlData, setPnlData] = useState<any | null>(null);
  const [pnlLoading, setPnlLoading] = useState(false);
  const [pnlFormat, setPnlFormat] = useState<'auto' | 'vertical' | 'standard'>('auto');
  const [expandedPnlCategories, setExpandedPnlCategories] = useState<Set<string>>(new Set());
  const [expandedPnlSubCategories, setExpandedPnlSubCategories] = useState<Set<string>>(new Set());
  const [daybookData, setDaybookData] = useState<{ results: any[]; count: number } | null>(null);
  const [daybookLoading, setDaybookLoading] = useState(false);

  // Fetch Trial Balance from backend when report type changes or dates change
  useEffect(() => {
    if (reportType !== 'TrialBalance') return;
    setTbLoading(true);
    setHasInitializedTbTree(false);
    apiService.getTrialBalanceReport(startDate || undefined, endDate || undefined)
      .then(res => setTbData(res?.data || res))
      .catch(err => console.error('Trial Balance API error:', err))
      .finally(() => setTbLoading(false));
  }, [reportType, startDate, endDate, trialBalanceType]);

  // Fetch Profit & Loss from backend when report type changes or dates change
  useEffect(() => {
    if (reportType !== 'ProfitAndLoss') return;
    setPnlLoading(true);
    apiService.getProfitAndLossReport(startDate || undefined, endDate || undefined)
      .then(res => setPnlData(res?.data || res))
      .catch(err => console.error('Profit & Loss API error:', err))
      .finally(() => setPnlLoading(false));
  }, [reportType, startDate, endDate]);

  // Fetch Balance Sheet from backend when report type changes or end date changes
  useEffect(() => {
    if (reportType !== 'BalanceSheet') return;
    setBsLoading(true);
    apiService.getBalanceSheetReport(endDate || undefined)
      .then(res => setBsData(res?.data || res))
      .catch(err => console.error('Balance Sheet API error:', err))
      .finally(() => setBsLoading(false));
  }, [reportType, endDate]);

  // Fetch Day Book from backend when report type changes or dates change
  useEffect(() => {
    if (reportType !== 'DayBook') return;
    setDaybookLoading(true);
    apiService.getDaybookReport(startDate || undefined, endDate || undefined)
      .then(res => setDaybookData(res?.data || res))
      .catch(err => console.error('Day Book API error:', err))
      .finally(() => setDaybookLoading(false));
  }, [reportType, startDate, endDate]);

  const [stockData, setStockData] = useState<{ results: any[]; count: number } | null>(null);
  const [stockLoading, setStockLoading] = useState(false);

  // Fetch Stock Summary from backend when report type changes or dates change
  useEffect(() => {
    if (reportType !== 'StockSummary') return;
    setStockLoading(true);
    apiService.getStockSummaryReport(startDate || undefined, endDate || undefined)
      .then(res => setStockData(res?.data || res))
      .catch(err => console.error('Stock Summary API error:', err))
      .finally(() => setStockLoading(false));
  }, [reportType, startDate, endDate]);



  // Fetch voucher details when a transaction is selected
  useEffect(() => {
    const voucherId = selectedTransaction?.voucher_id || selectedTransaction?.rawVoucher?.voucher_id || selectedTransaction?.voucherId || selectedTransaction?.rawVoucher?.voucherId;
    if (selectedTransaction && voucherId) {
      setIsLoadingDetails(true);
      const sourceHint = selectedTransaction?.voucher_type || selectedTransaction?.voucherType || selectedTransaction?.rawVoucher?.voucher_type;
      apiService.getVoucher(voucherId, {}, sourceHint)
        .then(details => {
          setVoucherDetails(details);
          setIsLoadingDetails(false);
        })
        .catch(err => {
          console.error('Error fetching voucher details:', err);
          setIsLoadingDetails(false);
          setVoucherDetails(null);
        });
    } else {
      setVoucherDetails(null);
    }
  }, [selectedTransaction]);
  // Multi-view mode for Ledger drill-down (mirrors VendorPortal procurement)
  const [ledgerViewMode, setLedgerViewMode] = useState<'list' | 'ledger' | 'month' | 'journal' | 'allocation'>('ledger');
  // Column filters for the ledger view
  const [ledgerFilters, setLedgerFilters] = useState({ date: '', dateFrom: '', dateTo: '', particulars: '', voucherNo: '', voucherType: '', debit: '', credit: '', runningBalance: '' });
  const [activeFilter, setActiveFilter] = useState<string | null>(null);
  // Month view multi-select
  const [selectedMonths, setSelectedMonths] = useState<string[]>([]);
  const [isMonthFilterOpen, setIsMonthFilterOpen] = useState(false);
  // Allocation modal state
  const [allocationModalRow, setAllocationModalRow] = useState<any | null>(null);
  const [selectedAllocationAdvances, setSelectedAllocationAdvances] = useState<any[]>([]);
  const [isAllocating, setIsAllocating] = useState(false);

  const monthNameToNumber: Record<string, string> = {
    'January': '01', 'February': '02', 'March': '03', 'April': '04',
    'May': '05', 'June': '06', 'July': '07', 'August': '08',
    'September': '09', 'October': '10', 'November': '11', 'December': '12'
  };

  const resetLedgerDetailFilters = () => {
    setLedgerVoucherType('all');
    setLedgerStatusFilter('all');
    setLedgerSearch('');
    setLedgerRefSearch('');
    setLedgerMinAmount('');
    setLedgerMaxAmount('');
    setSelectedSession('all');
    setSelectedSection('all');
    setLedgerFilters({ date: '', dateFrom: '', dateTo: '', particulars: '', voucherNo: '', voucherType: '', debit: '', credit: '', runningBalance: '' });
  };

  // Reset column filters when active report tab changes
  useEffect(() => {
    resetLedgerDetailFilters();
  }, [reportType]);

  // When user clicks a ledger, fetch its specific transactions from the API and reset active filter inputs
  useEffect(() => {
    resetLedgerDetailFilters();
    if (drillDownLedger && drillDownLedger !== 'all') {
      setIsDrillDownLoading(true);
      setDrillDownData([]);
      setLedgerViewMode('ledger');
      const ledgerName = drillDownLedger.includes(':') ? drillDownLedger.split(':')[1] : drillDownLedger;
      apiService.getJournalEntriesReport(ledgerName, undefined, undefined)
        .then(data => { setDrillDownData(Array.isArray(data) ? data : []); setIsDrillDownLoading(false); })
        .catch(() => { setIsDrillDownLoading(false); setDrillDownData([]); });
    } else {
      setDrillDownData([]);
    }
  }, [drillDownLedger]);

  // Download mappings for each report type
  const downloadMappings: { [key in ReportType]: { endpoint: string; filename: string } } = {
    DayBook: { endpoint: '/api/reports/daybook/excel', filename: 'DayBook.xlsx' },
    LedgerReport: { endpoint: '/api/reports/ledger/excel', filename: 'Ledger.xlsx' },
    TrialBalance: { endpoint: '/api/reports/trialbalance/excel', filename: 'TrialBalance.xlsx' },
    ProfitAndLoss: { endpoint: '/api/reports/pnl/excel', filename: 'ProfitAndLoss.xlsx' },
    StockSummary: { endpoint: '/api/reports/stocksummary/excel', filename: 'StockSummary.xlsx' },
    GSTReports: { endpoint: '/api/reports/gst/excel', filename: 'GstReport.xlsx' },
    AIReport: { endpoint: '/api/reports/ai/excel', filename: 'AIReport.xlsx' },
    BalanceSheet: { endpoint: '/api/reports/balancesheet/excel', filename: 'BalanceSheet.xlsx' },
    GSTR1: { endpoint: '/api/reports/gst/excel', filename: 'GstReport.xlsx' }
  };

  // Handle Excel download
  const handleDownload = async () => {
    const mapping = downloadMappings[reportType];
    try {
      // Construct Query Params
      const params = new URLSearchParams();
      if (startDate && reportType !== 'LedgerReport') params.append('startDate', startDate);
      if (endDate && reportType !== 'LedgerReport') params.append('endDate', endDate);
      if (reportType === 'LedgerReport' && selectedLedger && selectedLedger !== 'all') {
        // Extract actual name if it has prefix
        const cleanName = selectedLedger.includes(':') ? selectedLedger.split(':')[1] : selectedLedger;
        params.append('ledger', cleanName);
      }

      const response = await fetch(`${API_BASE_URL}${mapping.endpoint}?${params.toString()}`, {
        method: 'GET',
        headers: {
          // 'Authorization': ... removed, using cookies now
        },
        credentials: 'include', // Important: Send cookies
      });
      if (!response.ok) throw new Error('Failed to download');

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = mapping.filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error downloading Excel:');
      showError('Failed to download Excel file. Please try again.');
    }
  };

  const [gstForm, setGstForm] = useState<GSTForm>('GSTR-1');
  const [gstTab, setGstTab] = useState<GSTTab>('B2B');
  const [selectedGstReturn, setSelectedGstReturn] = useState<GSTForm>('GSTR-1');

  // Handle GST return dropdown changes
  useEffect(() => {
    setSelectedGstReturn(gstForm);
  }, [gstForm]);

  // ============================================================================
  // AI REPORT STATE
  // ============================================================================
  interface KPIMetric {
    label: string;
    value: string;
    change?: string;
    changeType?: 'positive' | 'negative' | 'neutral';
    icon: 'sales' | 'purchase' | 'payment' | 'receipt' | 'tax' | 'profit';
  }

  interface AIMessage {
    role: 'user' | 'ai';
    text: string;
    reportData?: {
      title: string;
      summary: string;
      tableData: { [key: string]: string | number }[];
      chartData: { name: string; value: number; color?: string }[];
      chartType: 'bar' | 'pie' | 'line' | 'area';
      kpiMetrics?: KPIMetric[];
    };
  }

  const [aiInput, setAiInput] = useState<string>('');
  const [aiLoading, setAiLoading] = useState<boolean>(false);
  const [currentReport, setCurrentReport] = useState<AIMessage['reportData'] | null>(null);
  const [reportView, setReportView] = useState<'table' | 'chart'>('table'); // Default to table view

  // Chart colors
  const CHART_COLORS = ['#6366F1', '#4F46E5', '#22c55e', '#818CF8', '#ef4444', '#6366F1', '#eab308', '#64748b'];

  // Generate report data based on query
  const generateReportFromQuery = useCallback((query: string) => {
    const lowerQuery = query.toLowerCase();
    let reportData: AIMessage['reportData'] | null = null;

    // Detect if query specifies a particular party/customer/vendor
    const matchedPartyName = vouchers.map(v => (v as any).party).find(party => {
      if (!party || typeof party !== 'string') return false;
      const lowerP = party.toLowerCase();
      if (lowerQuery.includes(lowerP)) return true;
      const significantWords = lowerP.split(/\s+/).filter(w => w.length > 3 && !['pvt', 'ltd', 'inc', 'corp', 'india', 'tech', 'solutions', 'digital', 'global'].includes(w));
      return significantWords.some(w => lowerQuery.includes(w));
    });

    // Calculate common metrics with proper number conversion (filtered by party if specified)
    let salesVouchers = vouchers.filter(v => v.type === 'Sales') as SalesPurchaseVoucher[];
    let purchaseVouchers = vouchers.filter(v => v.type === 'Purchase') as SalesPurchaseVoucher[];

    if (matchedPartyName) {
      salesVouchers = salesVouchers.filter(v => v.party.toLowerCase().includes(matchedPartyName.toLowerCase()) || matchedPartyName.toLowerCase().includes(v.party.toLowerCase()));
      purchaseVouchers = purchaseVouchers.filter(v => v.party.toLowerCase().includes(matchedPartyName.toLowerCase()) || matchedPartyName.toLowerCase().includes(v.party.toLowerCase()));
    }

    const totalSales = salesVouchers.reduce((sum, v) => {
      const total = Number(v.total) || 0;
      return sum + total;
    }, 0);

    const totalPurchases = purchaseVouchers.reduce((sum, v) => {
      const total = Number(v.total) || 0;
      return sum + total;
    }, 0);

    const grossProfit = totalSales - totalPurchases;
    const profitMargin = totalSales > 0 ? ((grossProfit / totalSales) * 100).toFixed(1) : '0';

    // If query references a specific party or asks for party data
    const isPartySpecificQuery = Boolean(matchedPartyName) && !lowerQuery.includes('purchase') && !lowerQuery.includes('expense') && !lowerQuery.includes('gst') && !lowerQuery.includes('tax');

    // Sales related queries or specific customer query
    if (lowerQuery.includes('sales') || lowerQuery.includes('revenue') || isPartySpecificQuery) {
      const wantsDetailed = matchedPartyName || !lowerQuery.includes('summary_only');

      if (wantsDetailed) {
        // Show individual transaction details
        const tableData = salesVouchers.map((v, idx) => ({
          '#': String(idx + 1),
          'Date': formatDate(v.date),
          'Invoice No': v.invoiceNo || '-',
          'Customer': v.party,
          'Taxable Amount (₹)': `₹${(Number(v.totalTaxableAmount) || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
          'CGST (₹)': `₹${(Number(v.totalCgst) || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
          'SGST (₹)': `₹${(Number(v.totalSgst) || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
          'IGST (₹)': `₹${(Number(v.totalIgst) || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
          'Total Amount (₹)': `₹${(Number(v.total) || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
        }));

        const chartData = salesVouchers
          .slice(0, 10)
          .map((v, idx) => ({
            name: `${formatDate(v.date)} - ${v.party.substring(0, 15)}`,
            value: Number(v.total) || 0,
            color: CHART_COLORS[idx % CHART_COLORS.length]
          }));

        reportData = {
          title: matchedPartyName ? `Filtered Report: ${matchedPartyName}` : 'Individual Sales Transactions',
          summary: matchedPartyName ? `Filtered analysis for ${matchedPartyName} (${salesVouchers.length} transaction(s))` : `Complete list of all ${salesVouchers.length} individual sales transactions`,
          tableData,
          chartData,
          chartType: 'bar',
          kpiMetrics: [
            {
              label: 'Total Transactions',
              value: salesVouchers.length.toString(),
              icon: 'receipt',
              change: 'Individual Records',
              changeType: 'neutral'
            },
            {
              label: 'Total Revenue',
              value: `₹${totalSales.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
              icon: 'sales',
              change: 'Sum of All',
              changeType: 'positive'
            },
            {
              label: 'Avg Transaction',
              value: `₹${(salesVouchers.length > 0 ? totalSales / salesVouchers.length : 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
              icon: 'payment'
            },
            {
              label: 'Date Range',
              value: salesVouchers.length > 0 ? `${new Date(Math.min(...salesVouchers.map(v => new Date(v.date).getTime()))).toLocaleDateString('en-IN')} - ${new Date(Math.max(...salesVouchers.map(v => new Date(v.date).getTime()))).toLocaleDateString('en-IN')}` : '-',
              icon: 'profit'
            }
          ]
        };
      } else {
        // Calculate detailed metrics for each customer (aggregated view)
        const customerDetails: {
          [key: string]: {
            total: number;
            count: number;
            taxableAmount: number;
            cgst: number;
            sgst: number;
            igst: number;
            dates: Date[];
          }
        } = {};

        salesVouchers.forEach(v => {
          if (!customerDetails[v.party]) {
            customerDetails[v.party] = {
              total: 0,
              count: 0,
              taxableAmount: 0,
              cgst: 0,
              sgst: 0,
              igst: 0,
              dates: []
            };
          }
          customerDetails[v.party].total += Number(v.total) || 0;
          customerDetails[v.party].count += 1;
          customerDetails[v.party].taxableAmount += Number(v.totalTaxableAmount) || 0;
          customerDetails[v.party].cgst += Number(v.totalCgst) || 0;
          customerDetails[v.party].sgst += Number(v.totalSgst) || 0;
          customerDetails[v.party].igst += Number(v.totalIgst) || 0;
          customerDetails[v.party].dates.push(new Date(v.date));
        });

        const chartData = Object.entries(customerDetails)
          .map(([name, details], idx) => ({ name, value: details.total, color: CHART_COLORS[idx % CHART_COLORS.length] }))
          .sort((a, b) => b.value - a.value)
          .slice(0, 6);

        const tableData = chartData.map((item, idx) => {
          const details = customerDetails[item.name];
          const avgValue = details.count > 0 ? details.total / details.count : 0;
          const totalTax = details.cgst + details.sgst + details.igst;
          const sortedDates = details.dates.sort((a, b) => a.getTime() - b.getTime());
          const firstDate = sortedDates[0];
          const lastDate = sortedDates[sortedDates.length - 1];

          return {
            '#': String(idx + 1),
            'Customer': item.name,
            'Total Sales (₹)': `₹${item.value.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
            'Transactions': String(details.count),
            'Avg Transaction (₹)': `₹${avgValue.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
            'Taxable Amount (₹)': `₹${details.taxableAmount.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
            'Total Tax (₹)': `₹${totalTax.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
            'CGST (₹)': `₹${details.cgst.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
            'SGST (₹)': `₹${details.sgst.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
            'IGST (₹)': `₹${details.igst.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
            'First Transaction': formatDate(firstDate.toISOString()),
            'Last Transaction': formatDate(lastDate.toISOString()),
            'Share (%)': totalSales > 0 ? `${((item.value / totalSales) * 100).toFixed(1)}%` : '0%'
          };
        });

        const avgOrderValue = salesVouchers.length > 0 ? totalSales / salesVouchers.length : 0;

        reportData = {
          title: 'Sales Analytics Dashboard',
          summary: `Comprehensive analysis of ${salesVouchers.length} sales transactions`,
          tableData,
          chartData,
          chartType: 'bar',
          kpiMetrics: [
            {
              label: 'Total Revenue',
              value: `₹${totalSales.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
              icon: 'sales',
              change: '+12.5%',
              changeType: 'positive'
            },
            {
              label: 'Transactions',
              value: salesVouchers.length.toString(),
              icon: 'receipt',
              change: '+8',
              changeType: 'positive'
            },
            {
              label: 'Avg Order Value',
              value: `₹${avgOrderValue.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
              icon: 'payment'
            },
            {
              label: 'Top Customers',
              value: Object.keys(customerDetails).length.toString(),
              icon: 'profit'
            }
          ]
        };
      }
    }
    // Purchase/Expense related queries
    else if (lowerQuery.includes('purchase') || lowerQuery.includes('expense') || lowerQuery.includes('spending') || lowerQuery.includes('vendor')) {
      // Calculate detailed metrics for each vendor
      const vendorDetails: {
        [key: string]: {
          total: number;
          count: number;
          taxableAmount: number;
          cgst: number;
          sgst: number;
          igst: number;
          dates: Date[];
        }
      } = {};

      purchaseVouchers.forEach(v => {
        if (!vendorDetails[v.party]) {
          vendorDetails[v.party] = {
            total: 0,
            count: 0,
            taxableAmount: 0,
            cgst: 0,
            sgst: 0,
            igst: 0,
            dates: []
          };
        }
        vendorDetails[v.party].total += Number(v.total) || 0;
        vendorDetails[v.party].count += 1;
        vendorDetails[v.party].taxableAmount += Number(v.totalTaxableAmount) || 0;
        vendorDetails[v.party].cgst += Number(v.totalCgst) || 0;
        vendorDetails[v.party].sgst += Number(v.totalSgst) || 0;
        vendorDetails[v.party].igst += Number(v.totalIgst) || 0;
        vendorDetails[v.party].dates.push(new Date(v.date));
      });

      const chartData = Object.entries(vendorDetails)
        .map(([name, details], idx) => ({ name, value: details.total, color: CHART_COLORS[idx % CHART_COLORS.length] }))
        .sort((a, b) => b.value - a.value)
        .slice(0, 6);

      const tableData = chartData.map((item, idx) => {
        const details = vendorDetails[item.name];
        const avgValue = details.count > 0 ? details.total / details.count : 0;
        const totalTax = details.cgst + details.sgst + details.igst;
        const sortedDates = details.dates.sort((a, b) => a.getTime() - b.getTime());
        const firstDate = sortedDates[0];
        const lastDate = sortedDates[sortedDates.length - 1];

        return {
          '#': String(idx + 1),
          'Vendor': item.name,
          'Total Purchases (₹)': `₹${item.value.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
          'Transactions': String(details.count),
          'Avg Transaction (₹)': `₹${avgValue.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
          'Taxable Amount (₹)': `₹${details.taxableAmount.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
          'Total Tax (₹)': `₹${totalTax.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
          'CGST (₹)': `₹${details.cgst.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
          'SGST (₹)': `₹${details.sgst.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
          'IGST (₹)': `₹${details.igst.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
          'First Transaction': formatDate(firstDate.toISOString()),
          'Last Transaction': formatDate(lastDate.toISOString()),
          'Share (%)': totalPurchases > 0 ? `${((item.value / totalPurchases) * 100).toFixed(1)}%` : '0%'
        };
      });

      const avgPurchaseValue = purchaseVouchers.length > 0 ? totalPurchases / purchaseVouchers.length : 0;

      reportData = {
        title: 'Expense Analytics Dashboard',
        summary: `Detailed breakdown of ${purchaseVouchers.length} expense transactions`,
        tableData,
        chartData,
        chartType: 'pie',
        kpiMetrics: [
          { label: 'Total Expenses', value: `₹${totalPurchases.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, icon: 'purchase', change: '-5.2%', changeType: 'positive' },
          { label: 'Transactions', value: purchaseVouchers.length.toString(), icon: 'receipt' },
          { label: 'Avg Purchase', value: `₹${avgPurchaseValue.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, icon: 'payment' },
          { label: 'Vendors', value: Object.keys(vendorDetails).length.toString(), icon: 'profit' }
        ]
      };
    }
    // GST/Tax related queries
    else if (lowerQuery.includes('gst') || lowerQuery.includes('tax')) {
      const outputCGST = salesVouchers.reduce((sum, v) => sum + (v.totalCgst || 0), 0);
      const outputSGST = salesVouchers.reduce((sum, v) => sum + (v.totalSgst || 0), 0);
      const outputIGST = salesVouchers.reduce((sum, v) => sum + (v.totalIgst || 0), 0);

      const inputCGST = purchaseVouchers.reduce((sum, v) => sum + (v.totalCgst || 0), 0);
      const inputSGST = purchaseVouchers.reduce((sum, v) => sum + (v.totalSgst || 0), 0);
      const inputIGST = purchaseVouchers.reduce((sum, v) => sum + (v.totalIgst || 0), 0);

      const totalOutput = outputCGST + outputSGST + outputIGST;
      const totalInput = inputCGST + inputSGST + inputIGST;
      const netLiability = totalOutput - totalInput;

      const chartData = [
        { name: 'Output CGST', value: outputCGST, color: '#6366F1' },
        { name: 'Output SGST', value: outputSGST, color: '#818CF8' },
        { name: 'Output IGST', value: outputIGST, color: '#A5B4FC' },
        { name: 'Input CGST', value: inputCGST, color: '#4F46E5' },
        { name: 'Input SGST', value: inputSGST, color: '#4338CA' },
        { name: 'Input IGST', value: inputIGST, color: '#3730A3' }
      ];

      const tableData = [
        { 'Tax Type': 'CGST', 'Output (₹)': `₹${outputCGST.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, 'Input (₹)': `₹${inputCGST.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, 'Net (₹)': `₹${(outputCGST - inputCGST).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` },
        { 'Tax Type': 'SGST', 'Output (₹)': `₹${outputSGST.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, 'Input (₹)': `₹${inputSGST.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, 'Net (₹)': `₹${(outputSGST - inputSGST).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` },
        { 'Tax Type': 'IGST', 'Output (₹)': `₹${outputIGST.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, 'Input (₹)': `₹${inputIGST.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, 'Net (₹)': `₹${(outputIGST - inputIGST).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` },
        { 'Tax Type': 'TOTAL', 'Output (₹)': `₹${totalOutput.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, 'Input (₹)': `₹${totalInput.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, 'Net (₹)': `₹${netLiability.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` }
      ];

      reportData = {
        title: 'GST Analytics Dashboard',
        summary: `Complete GST overview with input tax credit analysis`,
        tableData,
        chartData,
        chartType: 'bar',
        kpiMetrics: [
          { label: 'Output Tax', value: `₹${totalOutput.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, icon: 'tax', change: 'Collected', changeType: 'neutral' },
          { label: 'Input Credit', value: `₹${totalInput.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, icon: 'receipt', change: 'Claimable', changeType: 'positive' },
          { label: 'Net Liability', value: `₹${netLiability.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, icon: 'payment', change: netLiability > 0 ? 'Payable' : 'Refund', changeType: netLiability > 0 ? 'negative' : 'positive' },
          { label: 'Effective Rate', value: totalSales > 0 ? `${((totalOutput / totalSales) * 100).toFixed(1)}%` : '0%', icon: 'profit' }
        ]
      };
    }
    // Default - Show customer/vendor breakdown
    else {
      // Combine sales and purchase data for a comprehensive view
      const partyDetails: {
        [key: string]: {
          sales: number;
          purchases: number;
          salesCount: number;
          purchasesCount: number;
          totalTax: number;
          dates: Date[];
        }
      } = {};

      // Process sales vouchers
      salesVouchers.forEach(v => {
        if (!partyDetails[v.party]) {
          partyDetails[v.party] = {
            sales: 0,
            purchases: 0,
            salesCount: 0,
            purchasesCount: 0,
            totalTax: 0,
            dates: []
          };
        }
        partyDetails[v.party].sales += Number(v.total) || 0;
        partyDetails[v.party].salesCount += 1;
        partyDetails[v.party].totalTax += (Number(v.totalCgst) || 0) + (Number(v.totalSgst) || 0) + (Number(v.totalIgst) || 0);
        partyDetails[v.party].dates.push(new Date(v.date));
      });

      // Process purchase vouchers
      purchaseVouchers.forEach(v => {
        if (!partyDetails[v.party]) {
          partyDetails[v.party] = {
            sales: 0,
            purchases: 0,
            salesCount: 0,
            purchasesCount: 0,
            totalTax: 0,
            dates: []
          };
        }
        partyDetails[v.party].purchases += Number(v.total) || 0;
        partyDetails[v.party].purchasesCount += 1;
        partyDetails[v.party].totalTax += (Number(v.totalCgst) || 0) + (Number(v.totalSgst) || 0) + (Number(v.totalIgst) || 0);
        partyDetails[v.party].dates.push(new Date(v.date));
      });

      const chartData = Object.entries(partyDetails)
        .map(([name, details]) => ({
          name,
          value: details.sales + details.purchases,
          color: CHART_COLORS[0]
        }))
        .sort((a, b) => b.value - a.value)
        .slice(0, 6);

      const tableData = Object.entries(partyDetails)
        .sort(([, a], [, b]) => (b.sales + b.purchases) - (a.sales + a.purchases))
        .slice(0, 10)
        .map(([name, details], idx) => {
          const totalTransactions = details.salesCount + details.purchasesCount;
          const totalAmount = details.sales + details.purchases;
          const netBalance = details.sales - details.purchases;
          const sortedDates = details.dates.sort((a, b) => a.getTime() - b.getTime());
          const firstDate = sortedDates[0];
          const lastDate = sortedDates[sortedDates.length - 1];

          return {
            '#': String(idx + 1),
            'Party Name': name,
            'Sales (₹)': `₹${details.sales.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
            'Purchases (₹)': `₹${details.purchases.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
            'Net Balance (₹)': `₹${netBalance.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
            'Total Tax (₹)': `₹${details.totalTax.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
            'Transactions': String(totalTransactions),
            'First Transaction': firstDate ? formatDate(firstDate.toISOString()) : '-',
            'Last Transaction': lastDate ? formatDate(lastDate.toISOString()) : '-'
          };
        });

      reportData = {
        title: 'Party-wise Financial Overview',
        summary: `Comprehensive analysis of ${Object.keys(partyDetails).length} parties with ${vouchers.length} total transactions`,
        tableData,
        chartData,
        chartType: 'bar',
        kpiMetrics: [
          { label: 'Total Sales', value: `₹${totalSales.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, icon: 'sales', change: '+15.3%', changeType: 'positive' },
          { label: 'Total Expenses', value: `₹${totalPurchases.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, icon: 'purchase', change: '-3.2%', changeType: 'positive' },
          { label: 'Gross Profit', value: `₹${grossProfit.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, icon: 'profit', change: `${profitMargin}%`, changeType: grossProfit >= 0 ? 'positive' : 'negative' },
          { label: 'Transactions', value: vouchers.length.toString(), icon: 'receipt' }
        ]
      };
    }

    return reportData;
  }, [vouchers]);

  // Handle AI Report send
  const handleAiSend = useCallback(() => {
    if (!aiInput.trim() || aiLoading) return;

    setAiLoading(true);

    // Simulate AI processing
    setTimeout(() => {
      const reportData = generateReportFromQuery(aiInput);
      setCurrentReport(reportData);
      setAiLoading(false);
    }, 1500);

    setAiInput('');
  }, [aiInput, aiLoading, generateReportFromQuery]);

  // Handle Enter key in AI input
  const handleAiKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleAiSend();
    }
  };

  // Download report as Excel
  const downloadReportExcel = useCallback((report: AIMessage['reportData']) => {
    if (!report) return;

    // Create CSV content
    const headers = Object.keys(report.tableData[0] || {});
    const csvContent = [
      headers.join(','),
      ...report.tableData.map(row => headers.map(h => `"${row[h]}"`).join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${report.title.replace(/\s+/g, '_')}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }, []);

  // Download report as PDF (simple print)
  const downloadReportPDF = useCallback((report: AIMessage['reportData']) => {
    if (!report) return;

    const printWindow = window.open('', '_blank');
    if (!printWindow) return;

    const tableHtml = `
      <table border="1" style="border-collapse: collapse; width: 100%;">
        <thead>
          <tr style="background: #6366F1; color: white;">
            ${Object.keys(report.tableData[0] || {}).map(h => `<th style="padding: 8px;">${h}</th>`).join('')}
          </tr>
        </thead>
        <tbody>
          ${report.tableData.map(row => `
            <tr>
              ${Object.values(row).map(v => `<td style="padding: 8px;">${v}</td>`).join('')}
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;

    printWindow.document.write(`
      <html>
        <head>
          <title>${report.title}</title>
          <style>
            body { font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; padding: 20px; }
            h1 { color: #6366F1; }
            p { color: #666; }
          </style>
        </head>
        <body>
          <h1>${report.title}</h1>
          <p>${report.summary}</p>
          ${tableHtml}
          <p style="margin-top: 20px; font-size: 12px; color: #999;">Generated on ${new Date().toLocaleString()}</p>
        </body>
      </html>
    `);
    printWindow.document.close();
    printWindow.print();
  }, []);

  // Prevent rendering if data arrays are not properly initialized
  if (!Array.isArray(vouchers) || !Array.isArray(ledgers) || !Array.isArray(stockItems)) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="helper-text">Loading reports data...</div>
      </div>
    );
  }

  const ledgersByName = useMemo(() => {
    if (!ledgers || !Array.isArray(ledgers)) return {};
    return ledgers.filter(ledger => ledger && ledger.name).reduce((acc, ledger) => {
      acc[ledger.name] = ledger;
      return acc;
    }, {} as { [key: string]: Ledger });
  }, [ledgers]);

  const ledgerToGroup = useMemo(() => {
    const map: { [key: string]: string } = {};
    ledgers.forEach(l => map[l.name] = l.group);
    return map;
  }, [ledgers]);

  const getInvolvedLedgers = (v: Voucher): string[] => {
    switch (v.type) {
      case 'Purchase':
      case 'Sales':
        return [v.party];
      case 'Payment':
      case 'Receipt':
        return [v.party, (v as any).account];
      case 'Contra':
        const contra = v as any;
        return [contra.fromAccount, contra.toAccount];
      case 'Journal':
        return (v as any).entries.map((e: any) => e.ledger);
      default:
        return [];
    }
  };



  const availableMonths = useMemo(() => {
    const months = new Set<string>();
    if (vouchers && Array.isArray(vouchers)) {
      vouchers.forEach(v => {
        const d = new Date(v.date);
        // Handle potential invalid dates from user input
        if (!isNaN(d.getTime())) {
          const monthKey = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
          months.add(monthKey);
        }
      });
    }
    return Array.from(months).sort((a, b) => b.localeCompare(a)).map(monthKey => {
      const [year, month] = monthKey.split('-');
      const date = new Date(parseInt(year), parseInt(month) - 1, 1);
      return {
        value: monthKey,
        label: date.toLocaleString('default', { month: 'long', year: 'numeric' })
      };
    });
  }, [vouchers]);

  const trialBalanceData = useMemo(() => {
    if (reportType !== 'TrialBalance') return null;

    try {
      const balances: { [key: string]: { debit: number; credit: number } } = {};

      // Helper to safely initialize a ledger if it doesn't exist
      const ensureLedger = (name: string) => {
        if (name && typeof name === 'string' && !balances[name]) {
          balances[name] = { debit: 0, credit: 0 };
        }
      };

      // Initialize with all known ledgers from the master list
      if (ledgers && Array.isArray(ledgers)) {
        ledgers.forEach(l => ensureLedger(l.name));
      }

      if (vouchers && Array.isArray(vouchers)) {
        vouchers.forEach(v => {
          // Ensure all ledgers mentioned in the voucher exist in our balances object
          // before we start calculating. This prevents crashes if data is out of sync.
          switch (v.type) {
            case 'Purchase':
              ensureLedger(v.party);
              ensureLedger('Purchases');
              ensureLedger('IGST'); ensureLedger('CGST'); ensureLedger('SGST');

              if (balances[v.party]) balances[v.party].credit += Number(v.total || 0);
              if (balances['Purchases']) balances['Purchases'].debit += Number(v.totalTaxableAmount || 0);
              if (v.isInterState) {
                if (balances['IGST']) balances['IGST'].debit += Number(v.totalIgst || 0);
              } else {
                if (balances['CGST']) balances['CGST'].debit += Number(v.totalCgst || 0);
                if (balances['SGST']) balances['SGST'].debit += Number(v.totalSgst || 0);
              }
              break;
            case 'Sales':
              ensureLedger(v.party);
              ensureLedger('Sales');
              ensureLedger('IGST'); ensureLedger('CGST'); ensureLedger('SGST');

              if (balances[v.party]) balances[v.party].debit += Number(v.total || 0);
              if (balances['Sales']) balances['Sales'].credit += Number(v.totalTaxableAmount || 0);
              if (v.isInterState) {
                if (balances['IGST']) balances['IGST'].credit += Number(v.totalIgst || 0);
              } else {
                if (balances['CGST']) balances['CGST'].credit += Number(v.totalCgst || 0);
                if (balances['SGST']) balances['SGST'].credit += Number(v.totalSgst || 0);
              }
              break;
            case 'Payment':
              ensureLedger(v.party);
              ensureLedger((v as any).account);
              if (balances[v.party]) balances[v.party].debit += Number((v as any).amount || 0);
              if (balances[(v as any).account]) balances[(v as any).account].credit += Number((v as any).amount || 0);
              break;
            case 'Receipt':
              ensureLedger(v.party);
              ensureLedger((v as any).account);
              if (balances[v.party]) balances[v.party].credit += Number((v as any).amount || 0);
              if (balances[(v as any).account]) balances[(v as any).account].debit += Number((v as any).amount || 0);
              break;
            case 'Contra':
              ensureLedger((v as any).fromAccount);
              ensureLedger((v as any).toAccount);
              if (balances[(v as any).fromAccount]) balances[(v as any).fromAccount].credit += Number((v as any).amount || 0);
              if (balances[(v as any).toAccount]) balances[(v as any).toAccount].debit += Number((v as any).amount || 0);
              break;
            case 'Journal':
              if ((v as any).entries && Array.isArray((v as any).entries)) {
                (v as any).entries.forEach((e: any) => {
                  if (e && typeof e === 'object' && e.ledger && typeof e.ledger === 'string') {
                    ensureLedger(e.ledger);
                    if (balances[e.ledger]) {
                      balances[e.ledger].debit += Number(e.debit || 0);
                      balances[e.ledger].credit += Number(e.credit || 0);
                    }
                  }
                });
              }
              break;
          }
        });
      }

      const result = Object.entries(balances)
        .map(([ledger, { debit, credit }]) => {
          if (debit > credit) return { ledger, debit: debit - credit, credit: 0 };
          if (credit > debit) return { ledger, debit: 0, credit: credit - debit };
          return { ledger, debit: 0, credit: 0 };
        })
        .filter(item => item.debit > 0 || item.credit > 0);

      const totals = result.reduce((acc, curr) => ({
        debit: acc.debit + curr.debit,
        credit: acc.credit + curr.credit
      }), { debit: 0, credit: 0 });

      return { result, totals };
    } catch (error) {
      console.error('Error calculating trial balance:');
      return { result: [], totals: { debit: 0, credit: 0 } };
    }
  }, [reportType, vouchers, ledgers]);

  const stockSummaryData = useMemo(() => {
    if (reportType !== 'StockSummary') return null;

    const summary: { [key: string]: { inward: number, outward: number } } = {};
    if (stockItems && Array.isArray(stockItems)) {
      stockItems.filter(i => i && i.name).forEach(i => {
        summary[i.name] = { inward: 0, outward: 0 };
      });
    }

    if (vouchers && Array.isArray(vouchers)) {
      vouchers.forEach(v => {
        if (v.type === 'Purchase' || v.type === 'Sales') {
          const voucher = v as SalesPurchaseVoucher;
          if (voucher.items && Array.isArray(voucher.items)) {
            voucher.items.filter(item => item && item.name).forEach(item => {
              if (summary[item.name]) {
                if (v.type === 'Purchase') {
                  summary[item.name].inward += item.qty || 0;
                } else {
                  summary[item.name].outward += item.qty || 0;
                }
              }
            });
          }
        }
      });
    }

    return Object.entries(summary).map(([name, data]) => ({
      name,
      opening: 0,
      ...data,
      closing: data.inward - data.outward,
    }));
  }, [reportType, vouchers, stockItems]);

  const gstr1Data = useMemo(() => {
    if (reportType !== 'GSTR1') return null;
    if (!vouchers || !Array.isArray(vouchers)) return { b2b: [], b2c: [] };

    const salesVouchers = vouchers.filter(v => v.type === 'Sales') as SalesPurchaseVoucher[];

    const b2b = salesVouchers.filter(v => {
      const partyLedger = ledgersByName[v.party];
      return partyLedger?.registrationType === 'Registered' && partyLedger?.gstin;
    });

    const b2c = salesVouchers.filter(v => {
      const partyLedger = ledgersByName[v.party];
      return !partyLedger || partyLedger.registrationType !== 'Registered' || !partyLedger.gstin;
    });

    return { b2b, b2c };
  }, [reportType, vouchers, ledgersByName]);




  const filteredVouchers = useMemo(() => {
    if (!vouchers || !Array.isArray(vouchers)) return [];

    let filtered = vouchers;

    if (reportType === 'LedgerReport' && selectedLedger && selectedLedger !== 'all') {
      const [prefix, name] = selectedLedger.split(':');

      const filteredLedgers = prefix === 'group'
        ? ledgers.filter(l => l.group === name).map(l => l.name)
        : [name];

      filtered = filtered.filter(v => {
        switch (v.type) {
          case 'Purchase':
          case 'Sales':
          case 'Payment':
          case 'Receipt':
            return filteredLedgers.includes(v.party) || ('account' in v && filteredLedgers.includes(v.account));
          case 'Contra':
            return filteredLedgers.includes(v.fromAccount) || filteredLedgers.includes(v.toAccount);
          case 'Journal':
            return v.entries && Array.isArray(v.entries) && v.entries.some((e: any) => e && (filteredLedgers.includes(e.ledger) || filteredLedgers.includes(e.ledger_name) || filteredLedgers.includes(e.account)));
          case 'Debit Note':
          case 'Credit Note':
            // Debit Note / Credit Note involve the party (vendor/customer)
            return filteredLedgers.includes(v.party);
          default:
            return false;
        }
      });
    }

    if ((reportType === 'DayBook') && (startDate || endDate)) {
      filtered = filtered.filter(v => {
        const vDate = new Date(v.date);
        const start = startDate ? new Date(startDate) : null;
        const end = endDate ? new Date(endDate) : null;
        if (start && vDate < start) return false;
        if (end && vDate > end) return false;
        return true;
      });
    }

    return filtered;
  }, [vouchers, reportType, selectedLedger, startDate, endDate, ledgers]);

  const getVoucherAmount = (v: Voucher) => {
    if ('total' in v && v.total != null) {
      const num = Number(v.total);
      if (!isNaN(num)) return num;
    }
    if ('amount' in v && v.amount != null) {
      const num = Number(v.amount);
      if (!isNaN(num)) return num;
    }
    return 0;
  };
  const getVoucherParty = (v: any) => {
    // For Journal and Expense Vouchers, extract multiple party names if available
    const typeLower = (v.type || '').toLowerCase();
    if (typeLower === 'journal' || typeLower === 'journal voucher' || typeLower === 'expense' || typeLower === 'expense voucher' || typeLower === 'expenses') {
      const targetEntries = v.entries || v.expense_rows || v.expenseRows || [];
      if (Array.isArray(targetEntries) && targetEntries.length > 0) {
        const uniqueLedgers = Array.from(new Set(targetEntries.map((e: any) => {
          // Resolve name from ledgers array if it's an ID
          const partyId = e.ledger || e.postTo || e.post_to || e.party;
          if (!partyId) return null;
          const found = ledgers.find((l: any) => String(l.id) === String(partyId) || l.name === partyId);
          return found ? found.name : partyId;
        }).filter(Boolean)));
        if (uniqueLedgers.length > 0) {
          if (uniqueLedgers.length > 3) {
            return uniqueLedgers.slice(0, 3).join(', ') + '...';
          }
          return uniqueLedgers.join(', ');
        }
      }
    }

    let p = v.party;
    if (p && String(p).trim() !== '') {
      const found = ledgers.find((l: any) => String(l.id) === String(p));
      if (found) return found.name;
      return p;
    }

    // Fallbacks
    p = v.party_name || v.vendor_name || v.customer_name || v.pay_to_ledger || v.pay_to || v.pay_from || v.account;
    if (p && String(p).trim() !== '') {
      const found = ledgers.find((l: any) => String(l.id) === String(p));
      if (found) return found.name;
      return p;
    }

    return 'Unknown';
  };

  const ledgerEntries = useMemo(() => {
    const [prefix, nameOrId] = (selectedLedger || '').split(':');

    // If we have direct journal entries, use them as the source of truth for Ledger Report
    if (entries && entries.length > 0) {
      let balance = 0;
      let targetEntries = entries;

      // Filter by ledger if selected
      if (selectedLedger && selectedLedger !== 'all' && prefix === 'ledger') {
        targetEntries = entries.filter(e => e.ledger === nameOrId || String(e.ledger_id) === nameOrId);
      } else if (selectedLedger && selectedLedger !== 'all' && prefix === 'group') {
        const groupLedgers = ledgers.filter(l => l.group === nameOrId).map(l => l.name);
        targetEntries = entries.filter(e => groupLedgers.includes(e.ledger));
      }

      // Apply date filters if set
      if (startDate && reportType !== 'LedgerReport') {
        const s = new Date(startDate);
        targetEntries = targetEntries.filter(e => new Date(e.date || e.transaction_date) >= s);
      }
      if (endDate && reportType !== 'LedgerReport') {
        const e = new Date(endDate);
        targetEntries = targetEntries.filter(e => new Date(e.date || e.transaction_date) <= e);
      }

      return targetEntries.map(e => {
        const dr = Number(e.debit) || 0;
        const cr = Number(e.credit) || 0;
        // If backend already computed balance+balance_type, use them directly
        const backendBalance = e.balance !== undefined ? Number(e.balance) : null;
        const backendBalanceType: string = e.balance_type || '';
        if (backendBalance === null) {
          balance += dr - cr;
        }
        const finalBalance = backendBalance !== null ? backendBalance : Math.abs(balance);
        const finalBalanceType = backendBalance !== null
          ? backendBalanceType
          : (balance > 0 ? 'Dr' : balance < 0 ? 'Cr' : '');
        return {
          id: e.id,
          date: e.date || e.transaction_date,
          type: normalizeVoucherType(e.type || e.voucher_type),
          // Backend now sends correct counterpart name as 'particulars'
          particulars: e.particulars || e.ledger || 'N/A',
          debit: dr,
          credit: cr,
          balance: finalBalance,
          balanceType: finalBalanceType
        };
      });
    }

    // Fallback to deriving from vouchers if entries prop is empty
    if (!filteredVouchers.length) return [];

    // Handle ALL Ledgers case — shows every debit/credit line across all accounts
    if (selectedLedger === 'all') {
      const ledgerRunningBals: { [ledger: string]: number } = {};
      const allEntries: any[] = [];

      filteredVouchers.forEach(v => {
        const addEntry = (ledger: string, dr: number, cr: number, part: string, id: string | number) => {
          const currentBal = (ledgerRunningBals[ledger] || 0) + dr - cr;
          ledgerRunningBals[ledger] = currentBal;
          allEntries.push({
            id, date: v.date, type: v.type, particulars: part, debit: dr, credit: cr,
            balance: Math.abs(currentBal),
            balanceType: currentBal > 0 ? 'Dr' : currentBal < 0 ? 'Cr' : ''
          });
        };

        if ('entries' in v && v.entries && Array.isArray(v.entries)) {
          (v as any).entries.forEach((e: any, idx: number) => {
            const dr = Number(e.debit) || 0;
            const cr = Number(e.credit) || 0;
            const counterparts = (v as any).entries.filter((x: any) => x !== e).map((x: any) => x.ledger).join(', ') || e.ledger || 'N/A';
            addEntry(e.ledger, dr, cr, counterparts, `${v.id}-${idx}`);
          });
        } else {
          const amount = getVoucherAmount(v);
          if (v.type === 'Payment') {
            // Payment: Pay FROM cash (CREDIT cash) → Pay TO vendor (DEBIT vendor)
            const vendorName = (v as any).party || 'Vendor';
            const cashName = (v as any).account || 'Cash/Bank';
            // vendor1 → Debit (liability reduced; we paid them)
            addEntry(vendorName, amount, 0, cashName, `${v.id}-1`);
            // cash1   → Credit (money leaves)
            addEntry(cashName, 0, amount, vendorName, `${v.id}-2`);

          } else if (v.type === 'Receipt') {
            // Receipt: Receive FROM customer (CREDIT customer) INTO cash (DEBIT cash)
            const custName = (v as any).party || 'Customer';
            const cashName = (v as any).account || 'Cash/Bank';
            // customer → Credit (receivable settled)
            addEntry(custName, 0, amount, cashName, `${v.id}-1`);
            // cash    → Debit (money arrives)
            addEntry(cashName, amount, 0, custName, `${v.id}-2`);

          } else if (v.type === 'Contra') {
            // Contra: Transfer FROM one account TO another
            // fromAccount → Credit (money leaves), toAccount → Debit (money arrives)
            const fromAcc = (v as any).fromAccount || 'Account';
            const toAcc = (v as any).toAccount || 'Account';
            addEntry(fromAcc, 0, amount, toAcc, `${v.id}-1`);
            addEntry(toAcc, amount, 0, fromAcc, `${v.id}-2`);

          } else if ((v.type as string) === 'debit_note' || v.type === 'Debit Note' || (v.type as string) === 'DEBIT_NOTE') {
            // Debit Note: Debit the vendor
            const partyName = getVoucherParty(v);
            addEntry(partyName, amount, 0, 'Purchase Return', v.id);

          } else if ((v.type as string) === 'credit_note' || v.type === 'Credit Note' || (v.type as string) === 'CREDIT_NOTE') {
            // Credit Note: Credit the customer
            const partyName = getVoucherParty(v);
            addEntry(partyName, 0, amount, 'Sales Return', v.id);

          } else {
            // Sales → Debit customer. Purchase → Credit vendor.
            const partyName = getVoucherParty(v);
            const isSales = v.type === 'Sales';
            addEntry(
              partyName,
              isSales ? amount : 0,
              isSales ? 0 : amount,
              isSales ? 'Sales' : 'Purchases',
              v.id
            );
          }
        }
      });

      return allEntries;
    }

    // Single Ledger view
    const name = nameOrId;
    if (prefix === 'group') {
      // Handle group view
      const groupLedgers = ledgers.filter(l => l.group === name).map(l => l.name);
      let balance = 0;
      const groupEntries: any[] = [];

      filteredVouchers.forEach(v => {
        if ('entries' in v && v.entries && Array.isArray(v.entries)) {
          (v as any).entries.forEach((e: any) => {
            if (groupLedgers.includes(e.ledger)) {
              const dr = Number(e.debit) || 0;
              const cr = Number(e.credit) || 0;
              balance += dr - cr;
              groupEntries.push({
                id: v.id,
                date: v.date,
                type: v.type,
                particulars: e.ledger,
                debit: dr,
                credit: cr,
                balance
              });
            }
          });
        }
      });

      return groupEntries;
    }

    let runningBalance = 0;
    return filteredVouchers.map(v => {
      let debit = 0, credit = 0, particulars = '';
      const vType = v.type as string;

      const vAny = v as any;
      switch (vType) {
        case 'Purchase':
          // Vendor (party/pay_to) is CREDITED when we purchase on credit
          // Purchase account is DEBITED
          if (vAny.party === name) {
            // This ledger is the Vendor/Supplier — they are the CREDITOR
            credit = Number(vAny.total) || 0;
            particulars = 'Purchases';
          } else if ('account' in vAny && vAny.account === name) {
            debit = Number(vAny.total) || 0;
            particulars = vAny.party;
          }
          break;
        case 'Sales':
          // Customer (party) is DEBITED — they owe us money
          // Sales account is CREDITED
          if (vAny.party === name) {
            debit = Number(vAny.total) || 0;
            particulars = 'Sales';
          } else if ('account' in vAny && vAny.account === name) {
            credit = Number(vAny.total) || 0;
            particulars = vAny.party;
          }
          break;
        case 'Payment':
          // Payment: Pay FROM cash/bank (CREDIT cash) → Pay TO vendor (DEBIT vendor, reduces liability)
          // v.party = vendor (pay_to), v.account = cash/bank (pay_from)
          if (vAny.party === name) {
            // This is the Vendor ledger — being DEBITED (liability reduced)
            debit = Number(vAny.amount) || 0;
            particulars = vAny.account || 'Cash/Bank';
          } else if (vAny.account === name) {
            // This is the Cash/Bank ledger — being CREDITED (money goes out)
            credit = Number(vAny.amount) || 0;
            particulars = vAny.party || 'Vendor';
          }
          break;
        case 'Receipt':
          // Receipt: Receive INTO cash/bank (DEBIT cash) ← FROM customer (CREDIT customer)
          // v.party = customer (receive_from), v.account = cash/bank (receive_into)
          if (vAny.party === name) {
            // Customer ledger — being CREDITED (receivable settled)
            credit = Number(vAny.amount) || 0;
            particulars = vAny.account || 'Cash/Bank';
          } else if (vAny.account === name) {
            // Cash/Bank ledger — being DEBITED (money comes in)
            debit = Number(vAny.amount) || 0;
            particulars = vAny.party || 'Customer';
          }
          break;
        case 'Contra':
          // Contra: Transfer between cash/bank accounts
          // fromAccount is CREDITED (money leaves), toAccount is DEBITED (money arrives)
          if (vAny.fromAccount === name) {
            credit = Number(vAny.amount) || 0;
            particulars = vAny.toAccount;
          } else if (vAny.toAccount === name) {
            debit = Number(vAny.amount) || 0;
            particulars = vAny.fromAccount;
          }
          break;
        case 'Journal':
          if (vAny.entries && Array.isArray(vAny.entries)) {
            const entry = vAny.entries.find((e: any) => e.ledger === name);
            if (entry) {
              debit = Number(entry.debit) || 0;
              credit = Number(entry.credit) || 0;
              particulars = vAny.entries.filter((e: any) => e.ledger !== name).map((e: any) => e.ledger).join(', ') || 'Journal Entry';
            }
          }
          break;
        case 'debit_note':
        case 'Debit Note':
        case 'DEBIT_NOTE':
          // Debit Note: reduces vendor liability
          // Vendor (party) is DEBITED (liability reduced — they owe us less)
          // Purchase Return A/c is CREDITED
          if ((v as any).party === name) {
            debit = Number((v as any).total) || Number((v as any).amount) || 0;
            particulars = 'Purchase Return / Debit Note';
          }
          break;
        case 'credit_note':
        case 'Credit Note':
        case 'CREDIT_NOTE':
          // Credit Note: reduces customer receivable
          // Customer (party) is CREDITED (they owe us less)
          // Sales Return A/c is DEBITED
          if ((v as any).party === name) {
            credit = Number((v as any).total) || Number((v as any).amount) || 0;
            particulars = 'Sales Return / Credit Note';
          }
          break;
      }

      // Running balance: Dr entries increase balance, Cr entries decrease it
      runningBalance += debit - credit;
      const balanceAbs = Math.abs(runningBalance);
      const balanceType = runningBalance > 0 ? 'Dr' : runningBalance < 0 ? 'Cr' : '';

      return {
        id: v.id,
        date: v.date,
        type: v.type,
        particulars,
        debit,
        credit,
        balance: balanceAbs,
        balanceType
      };
    });
  }, [reportType, selectedLedger, filteredVouchers, entries, startDate, endDate, ledgers]);

  // ═══ LEDGER SUMMARY useMemo ════════════════════════════════════════════════
  const ledgerSummary = useMemo(() => {
    const map = new Map<string, number>();
    const add = (name: string, delta: number) => name && map.set(name, (map.get(name) || 0) + delta);

    // 1. Initialize with Opening Balances
    if (ledgers && ledgers.length > 0) {
      ledgers.forEach(l => {
        if (l.name && l.opening_balance) {
          const bal = Number(l.opening_balance) || 0;
          const type = l.opening_balance_type || 'Dr';
          if (bal > 0) {
            add(l.name, type === 'Dr' ? bal : -bal);
          }
        }
      });
    }

    // 2. Process Transactions
    if (entries && entries.length > 0) {
      entries.forEach(e => {
        // Date filtering
        const vDate = e.transaction_date || e.date;
        if (vDate && reportType !== 'LedgerReport') {
          const d = new Date(vDate);
          if (startDate && d < new Date(startDate)) return;
          if (endDate && d > new Date(endDate)) return;
        }

        const n = e.ledger_name || e.ledger || e.particulars;
        add(n, (Number(e.debit) || 0) - (Number(e.credit) || 0));
      });
    } else {
      filteredVouchers.forEach(v => {
        const amt = getVoucherAmount(v);
        if (v.type === 'Payment') { add((v as any).party || 'Vendor', +amt); add((v as any).account || 'Cash/Bank', -amt); }
        else if (v.type === 'Receipt') { add((v as any).party || 'Customer', -amt); add((v as any).account || 'Cash/Bank', +amt); }
        else if (v.type === 'Contra') { add((v as any).fromAccount || 'Account', -amt); add((v as any).toAccount || 'Account', +amt); }
        else if ('entries' in v && Array.isArray((v as any).entries)) {
          (v as any).entries.forEach((e: any) => add(e.ledger, (Number(e.debit) || 0) - (Number(e.credit) || 0)));
        } else { const p = getVoucherParty(v); add(p, v.type === 'Sales' ? +amt : -amt); }
      });
    }
    let result = Array.from(map.entries())
      .map(([name, net]) => {
        const ledgerObj = ledgers?.find(l => l.name === name);
        let category = '-';
        if (ledgerObj) {
          const groupLower = (ledgerObj.group || '').toLowerCase();
          if (groupLower.includes('creditor')) category = 'Vendor';
          else if (groupLower.includes('debtor')) category = 'Customer';
          else {
            // Fallback to Major Category (e.g. ASSET, LIABILITY, INCOME) as requested
            category = ledgerObj.category || ledgerObj.group || '-';
          }
        }
        return { name, category, balance: Math.abs(net), balanceType: net > 0 ? 'Dr' : net < 0 ? 'Cr' : '' };
      })
      .filter(r => r.balance > 0).sort((a, b) => String(a?.name || '').localeCompare(String(b?.name || '')));

    if (reportType === 'LedgerReport' && selectedLedger && selectedLedger !== 'all') {
      const [prefix, name] = selectedLedger.split(':');
      if (prefix === 'ledger') {
        result = result.filter(r => r.name === name);
      } else if (prefix === 'group') {
        const groupLedgers = ledgers.filter(l => l.group === name).map(l => l.name);
        result = result.filter(r => groupLedgers.includes(r.name));
      }
    }

    return result;
  }, [entries, filteredVouchers, ledgers, selectedLedger, reportType, startDate, endDate]);

  // ═══ DRILL-DOWN ENTRIES useMemo ════════════════════════════════════════════
  const drillDownEntries = useMemo(() => {
    if (!drillDownLedger) return [];
    const name = drillDownLedger;
    let running = 0;
    const rows: any[] = [];

    // 1. Add Opening Balance Row
    const ledger = ledgers?.find(l => l.name === name);
    if (ledger && ledger.opening_balance) {
      const bal = Number(ledger.opening_balance) || 0;
      if (bal > 0) {
        const type = ledger.opening_balance_type || 'Dr';
        running += type === 'Dr' ? bal : -bal;
        rows.push({
          date: '', particulars: 'Opening Balance', voucherType: 'Opening', voucherNo: '-',
          debit: type === 'Dr' ? bal : 0, credit: type === 'Cr' ? bal : 0,
          balance: Math.abs(running), balanceType: type
        });
      }
    }

    const push = (date: string, particulars: string, voucherType: string, voucherNo: string, dr: number, cr: number, refNo: string = '', raw: any = null) => {
      running += dr - cr;
      rows.push({
        id: raw?.id,
        date, particulars, voucherType, voucherNo, referenceNo: refNo, debit: dr, credit: cr,
        balance: Math.abs(running), balanceType: running > 0 ? 'Dr' : running < 0 ? 'Cr' : '', rawVoucher: raw
      });
    };

    // PRIMARY: Use data fetched from the API for this specific ledger
    if (drillDownData && drillDownData.length > 0) {
      drillDownData.forEach(e => {
        const refNo = e.reference_number || e.referenceNo || e.ref_no || '-';
        const allocStatus = e.allocation_status || e.allocationStatus || 'Unutilized';
        push(
          e.transaction_date || e.date || '',
          e.particulars || 'N/A',
          normalizeVoucherType(e.voucher_type || e.type || ''),
          e.voucher_number || e.voucherNo || e.purchase_voucher_no || e.voucher_no || '',
          Number(e.debit) || 0,
          Number(e.credit) || 0,
          refNo,
          { ...e, allocation_status: allocStatus, reference_number: refNo }
        );
      });
      return rows;
    }
    // FALLBACK: Try local journal entries filtered by ledger name
    if (entries && entries.length > 0) {
      const rel = entries.filter(e => (e.ledger_name || e.ledger || '') === name);
      if (rel.length > 0) {
        rel.forEach(e => push(
          e.transaction_date || e.date || '',
          e.particulars || e.ledger || 'N/A',
          normalizeVoucherType(e.voucher_type || e.type || ''),
          e.voucher_number || e.voucherNo || e.purchase_voucher_no || e.voucher_no || '',
          Number(e.debit) || 0,
          Number(e.credit) || 0,
          e.reference_number || e.referenceNo || '-',
          e
        ));
        return rows;
      }
    }
    // FALLBACK: Try vouchers
    filteredVouchers.forEach(v => {
      const amt = getVoucherAmount(v);
      const vNo = (v as any).voucher_number || (v as any).voucherNumber || '';
      if (v.type === 'Payment') { const vn = (v as any).party || 'Vendor', cn = (v as any).account || 'Cash/Bank'; if (vn === name) push(v.date, cn, v.type, vNo, amt, 0, '', v); if (cn === name) push(v.date, vn, v.type, vNo, 0, amt, '', v); }
      else if (v.type === 'Receipt') { const cn = (v as any).party || 'Customer', an = (v as any).account || 'Cash/Bank'; if (cn === name) push(v.date, an, v.type, vNo, 0, amt, '', v); if (an === name) push(v.date, cn, v.type, vNo, amt, 0, '', v); }
      else if (v.type === 'Contra') { const fa = (v as any).fromAccount || 'Account', ta = (v as any).toAccount || 'Account'; if (fa === name) push(v.date, ta, v.type, vNo, 0, amt, '', v); if (ta === name) push(v.date, fa, v.type, vNo, amt, 0, '', v); }
      else if ((v.type as string) === 'debit_note' || v.type === 'Debit Note' || (v.type as string) === 'DEBIT_NOTE') { const p = getVoucherParty(v); if (p === name) push(v.date, 'Purchase Return', 'Debit Note', vNo, amt, 0, '', v); }
      else if ((v.type as string) === 'credit_note' || v.type === 'Credit Note' || (v.type as string) === 'CREDIT_NOTE') { const p = getVoucherParty(v); if (p === name) push(v.date, 'Sales Return', 'Credit Note', vNo, 0, amt, '', v); }
      else if ('entries' in v && Array.isArray((v as any).entries)) {
        let matchedRow = false;
        (v as any).entries.forEach((e: any) => {
          if (e.ledger === name) {
            matchedRow = true;
            const cp = (v as any).entries.filter((x: any) => x !== e).map((x: any) => x.ledger).join(', ') || 'Journal';
            push(v.date, cp, v.type, vNo, Number(e.debit) || 0, Number(e.credit) || 0, '', v);
          }
        });
        if (!matchedRow && name.includes(',')) {
          if (getVoucherParty(v) === name && (!drillDownSourceType || drillDownSourceType === v.type)) {
            push(v.date, 'Journal', v.type, vNo, amt, 0, '', v);
          }
        }
      } else {
        // Handle expense vouchers and other types fallback
        // We strictly match the party name generated for this voucher to the one clicked in the Day Book
        const p = getVoucherParty(v);
        if (p === name) {
          if (name.includes(',') && drillDownSourceType && drillDownSourceType !== v.type) {
            // Skip if it's a pseudo-ledger and type doesn't match the clicked source
            return;
          }
          const s = v.type === 'Sales';
          // Pass voucher as raw so reference_id/source are available for View button
          push(v.date, s ? 'Sales' : 'Purchases', v.type, vNo, s ? amt : 0, s ? 0 : amt, '', v);
        }
      }
    });
    return rows;
  }, [drillDownLedger, drillDownData, entries, filteredVouchers, selectedLedger, ledgers]);

  const availableSections = useMemo(() => {
    if (!isTdsTcsLedger || !drillDownEntries) return [];
    const sectionsSet = new Set<string>();
    drillDownEntries.forEach((e: any) => {
      if (e.rawVoucher?.tds_components) {
        e.rawVoucher.tds_components.forEach((c: any) => {
          if (c.component) sectionsSet.add(c.component);
        });
      }
    });
    return Array.from(sectionsSet);
  }, [drillDownEntries, isTdsTcsLedger]);

  const calcEntryStatus = (e: any) => {
    if (!e || e.voucherType === 'Opening') return '-';
    let st = '';
    const raw = e.rawVoucher || {};
    let isExpired = false;
    const amount = parseFloat(raw.total || raw.amount || raw.total_amount || 0);
    const paidAmount = parseFloat(raw.paid_amount || raw.used_amount || 0);
    const pendingBalance = Math.max(0, amount - paidAmount);

    if (amount > 0 && e.date) {
      const activeLedgerNameForStatus = drillDownLedger?.includes(':') ? drillDownLedger.split(':')[1] : drillDownLedger;
      const activeLedgerForStatus = ledgers?.find((l: any) => l.name === activeLedgerNameForStatus);
      const cpStrStatus = activeLedgerForStatus?.additional_data?.credit_period || (activeLedgerForStatus as any)?.credit_period || activeLedgerForStatus?.creditPeriod || '0';
      const cpStatus = parseInt(String(cpStrStatus), 10) || (drillDownData[0]?.ledger_credit_period || 0);
      const invDate = new Date(e.date);
      const today = new Date();
      const diffDays = Math.floor((new Date(today.getFullYear(), today.getMonth(), today.getDate()).getTime() - new Date(invDate.getFullYear(), invDate.getMonth(), invDate.getDate()).getTime()) / 86400000);
      isExpired = diffDays > cpStatus;
    }

    const vtLower = (e.voucherType || '').toLowerCase();
    const txType = (raw.voucher_type || raw.type || vtLower).toLowerCase();
    const isPurchase = txType.includes('purchase') || txType.includes('expense');
    const isSales = txType.includes('sales') || txType.includes('invoice');
    const isDebitNote = vtLower.includes('debit');
    const isCreditNote = vtLower.includes('credit');
    const isPayment = vtLower.includes('payment') || vtLower.includes('receipt') || vtLower.includes('contra');

    if (raw.is_disputed || raw.status === 'Disputed' || raw.payment_status === 'Disputed') {
      st = 'Disputed';
    } else if (isSales || isDebitNote) {
      const rawDueStatus = raw.due_status || '';
      if (rawDueStatus) st = rawDueStatus;
      else if (pendingBalance === 0 && amount > 0) st = 'Received';
      else if (pendingBalance < amount && pendingBalance > 0) st = 'Partially Received';
      else if (pendingBalance === amount) st = isExpired ? 'Due' : 'Not Due';
      else st = 'Not Due';
    } else if (isPurchase || isCreditNote) {
      const rawDueStatus = raw.due_status || '';
      if (rawDueStatus && pendingBalance === amount) st = rawDueStatus;
      else if (pendingBalance === 0 && amount > 0) st = 'Paid';
      else if (pendingBalance < amount && pendingBalance > 0) st = 'Partially Paid';
      else if (pendingBalance === amount) st = isExpired ? 'Due' : 'Not Due';
      else st = 'Not Due';
    } else if (isPayment) {
      const rawPayStatus = raw.due_status || '';
      if (rawPayStatus) st = rawPayStatus;
      else if (pendingBalance === 0 && amount > 0) st = 'Utilized';
      else if (pendingBalance < amount && pendingBalance > 0) st = 'Partially Utilized';
      else st = 'Unutilized';
    } else {
      st = '-';
    }
    return st;
  };

  // ═══ FILTERED LEDGER DATA (for Ledger / Journal views) ══════════════════════
  const filteredDrillData = useMemo(() => {
    return drillDownEntries.filter(e => {
      if (e.voucherType === 'Opening') return true;

      if (startDate && e.date && e.date < startDate) return false;
      if (endDate && e.date && e.date > endDate) return false;

      if (ledgerVoucherType && ledgerVoucherType !== 'all') {
        const targetVt = ledgerVoucherType.toLowerCase();
        if (!(e.voucherType || '').toLowerCase().includes(targetVt)) return false;
      }

      if (ledgerStatusFilter && ledgerStatusFilter !== 'all') {
        const targetSt = ledgerStatusFilter.toLowerCase().trim();
        const entrySt = calcEntryStatus(e).toLowerCase().trim();
        if (targetSt === 'due') {
          if (entrySt !== 'due' && !entrySt.includes('overdue')) return false;
        } else if (targetSt === 'paid') {
          if (entrySt !== 'paid') return false;
        } else if (targetSt === 'received') {
          if (entrySt !== 'received') return false;
        } else if (targetSt === 'utilized') {
          if (entrySt !== 'utilized') return false;
        } else {
          if (!entrySt.includes(targetSt)) return false;
        }
      }

      if (ledgerSearch && ledgerSearch.trim()) {
        const q = ledgerSearch.toLowerCase().trim();
        const particularsVal = (e.particulars || '').toLowerCase();
        const partyVal = (e.rawVoucher?.party || e.rawVoucher?.account || '').toLowerCase();
        if (!particularsVal.includes(q) && !partyVal.includes(q)) return false;
      }

      if (ledgerRefSearch && ledgerRefSearch.trim()) {
        if (!matchRefOrVoucherNo(e, ledgerRefSearch)) return false;
      }

      const entryAmt = Math.max(Number(e.debit || 0), Number(e.credit || 0));
      if (ledgerMinAmount !== '' && !isNaN(Number(ledgerMinAmount))) {
        if (entryAmt < Number(ledgerMinAmount)) return false;
      }
      if (ledgerMaxAmount !== '' && !isNaN(Number(ledgerMaxAmount))) {
        if (entryAmt > Number(ledgerMaxAmount)) return false;
      }

      let dateMatch = true;
      if (ledgerFilters.dateFrom && e.date && e.date < ledgerFilters.dateFrom) dateMatch = false;
      if (ledgerFilters.dateTo && e.date && e.date > ledgerFilters.dateTo) dateMatch = false;
      if (ledgerFilters.date && e.date && !e.date.includes(ledgerFilters.date)) dateMatch = false;
      const partMatch = !ledgerFilters.particulars || (e.particulars || '').toLowerCase().includes(ledgerFilters.particulars.toLowerCase());
      const vNoMatch = !ledgerFilters.voucherNo || matchRefOrVoucherNo(e, ledgerFilters.voucherNo);
      const vtMatch = !ledgerFilters.voucherType || (e.voucherType || '').toLowerCase().includes(ledgerFilters.voucherType.toLowerCase());
      const drMatch = !ledgerFilters.debit || String(e.debit || '').includes(ledgerFilters.debit);
      const crMatch = !ledgerFilters.credit || String(e.credit || '').includes(ledgerFilters.credit);

      let sessionMatch = true;
      if (isTdsTcsLedger && selectedSession !== 'all' && e.date) {
        try {
          const d = new Date(e.date);
          if (!isNaN(d.getTime())) {
            const year = d.getFullYear();
            const month = d.getMonth() + 1;
            const sessionStartYear = month >= 4 ? year : year - 1;
            const sessionStr = `${sessionStartYear}-${sessionStartYear + 1}`;
            if (sessionStr !== selectedSession) sessionMatch = false;
          }
        } catch (err) { }
      }

      let sectionFilterMatch = true;
      if (isTdsTcsLedger && selectedSection !== 'all') {
        const hasSec = e.rawVoucher?.tds_components?.some((c: any) => c.component === selectedSection);
        if (!hasSec) sectionFilterMatch = false;
      }

      return dateMatch && partMatch && vNoMatch && vtMatch && drMatch && crMatch && sessionMatch && sectionFilterMatch;
    });
  }, [drillDownEntries, startDate, endDate, ledgerVoucherType, ledgerStatusFilter, ledgerSearch, ledgerRefSearch, ledgerMinAmount, ledgerMaxAmount, ledgerFilters, isTdsTcsLedger, selectedSession, selectedSection, ledgers, drillDownLedger, drillDownData]);

  // ═══ MONTH VIEW DATA ═════════════════════════════════════════════════════════
  const ledgerMonthData = useMemo(() => {
    const months = ['April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December', 'January', 'February', 'March'];
    let cumBal = 0;
    return months.map(month => {
      const mStr = monthNameToNumber[month];
      const inMonth = filteredDrillData.filter(e => e.date && e.date.split('-')[1] === mStr);
      const mDr = inMonth.reduce((s, e) => s + (e.debit || 0), 0);
      const mCr = inMonth.reduce((s, e) => s + (e.credit || 0), 0);
      cumBal += mDr - mCr;
      return {
        month,
        debit: mDr > 0 ? mDr.toLocaleString('en-IN', { minimumFractionDigits: 2 }) : '-',
        credit: mCr > 0 ? mCr.toLocaleString('en-IN', { minimumFractionDigits: 2 }) : '-',
        closingBalance: cumBal !== 0 ? Math.abs(cumBal).toLocaleString('en-IN', { minimumFractionDigits: 2 }) + (cumBal > 0 ? ' Dr' : ' Cr') : '-',
        rawBalance: cumBal,
      };
    });
  }, [filteredDrillData]);

  // ═══ ALLOCATION VIEW DATA ════════════════════════════════════════════════════
  const allocationRows = useMemo(() => {
    if (!filteredDrillData || filteredDrillData.length === 0) return [];

    // Group by referenceNo to find linked vouchers
    const groups: Record<string, any[]> = {};
    filteredDrillData.forEach(entry => {
      if (entry.voucherType === 'Opening') return;
      const vt = (entry.voucherType || '').toLowerCase();
      const isApplication = vt.includes('receipt') || vt.includes('payment') || vt.includes('contra') || vt.includes('debit') || vt.includes('credit');
      const isSource = !isApplication;

      let ref = entry.referenceNo?.trim() || entry.rawVoucher?.reference_number?.trim() || '-';

      // For source vouchers, if referenceNo is empty, treat voucherNo as the reference
      if (isSource && (ref === '-' || !ref)) {
        ref = entry.voucherNo?.trim() || entry.rawVoucher?.voucher_number?.trim() || '-';
      }

      if (ref === '-') {
        const uniqueId = `standalone-${Math.random()}`;
        groups[uniqueId] = [entry];
        return;
      }
      const groupKey = ref;
      if (!groups[groupKey]) groups[groupKey] = [];
      groups[groupKey].push(entry);
    });

    const rows: any[] = [];

    const activeLedgerName = drillDownLedger?.includes(':') ? drillDownLedger.split(':')[1] : drillDownLedger;
    const activeLedger = ledgers?.find(l => l.name === activeLedgerName);
    const cpStr = activeLedger?.additional_data?.credit_period || (activeLedger as any)?.extended_data?.credit_period || activeLedger?.creditPeriod || (activeLedger as any)?.credit_period || '0';
    let cp = parseInt(String(cpStr), 10) || 0;
    if (cp === 0 && drillDownData.length > 0) {
      cp = drillDownData[0]?.ledger_credit_period || 0;
    }

    const getAgingStatus = (dateStr: string) => {
      if (!dateStr) return 'Due';
      const invDate = new Date(dateStr);
      const todayD = new Date();
      const d1 = new Date(invDate.getFullYear(), invDate.getMonth(), invDate.getDate());
      const d2 = new Date(todayD.getFullYear(), todayD.getMonth(), todayD.getDate());
      const diffDays = Math.floor((d2.getTime() - d1.getTime()) / (1000 * 60 * 60 * 24));
      return diffDays > cp ? 'Due' : 'Not Due';
    };

    // Process groups and sort by date
    const sortedGroupRefs = Object.keys(groups).sort((aRef, bRef) => {
      const firstA = groups[aRef][0];
      const firstB = groups[bRef][0];
      return new Date(firstA?.date || 0).getTime() - new Date(firstB?.date || 0).getTime();
    });

    sortedGroupRefs.forEach(ref => {
      const entries = groups[ref];

      // If it's a standalone group
      if (ref.startsWith('standalone-')) {
        const entry = entries[0];
        const vt = (entry.voucherType || '').toLowerCase();
        // Only show sources in Allocation View
        if (!['sales', 'purchase', 'journal', 'opening', 'debit note', 'credit note'].includes(vt) && entry.debit === 0 && entry.credit === 0) return;

        const isDr = (entry.debit || 0) > 0;
        const amt = isDr ? (entry.debit || 0) : (entry.credit || 0);

        const isApplication = ['receipt', 'payment', 'contra', 'debit', 'credit'].some(t => vt.includes(t));
        const rawSt = entry.rawVoucher?.allocation_status || entry.rawVoucher?.allocationStatus;
        let calcSt = 'Due';
        if (isApplication) {
          calcSt = rawSt === 'Utilized' ? 'Utilized' : 'Not Utilized';
        } else {
          calcSt = rawSt === 'Utilized' ? 'Paid' : (amt === 0 ? 'Paid' : getAgingStatus(entry.date));
        }

        rows.push({
          date: entry.date,
          postedFrom: entry.voucherType,
          refNo: entry.referenceNo !== '-' ? entry.referenceNo : (entry.voucherNo || '-'),
          netAmount: amt,
          appliedDate: '-',
          appliedRefNo: '-',
          appliedAmount: '-',
          pendingBalance: amt,
          status: calcSt,
          rowSpan: 1,
          isFirstInSource: true
        });
        return;
      }

      // For linked groups
      const sources = entries.filter(e => !['receipt', 'payment', 'contra', 'debit', 'credit'].includes((e.voucherType || '').toLowerCase()));
      const applications = entries.filter(e => ['receipt', 'payment', 'contra', 'debit', 'credit'].includes((e.voucherType || '').toLowerCase()));

      if (sources.length === 0) return;

      const firstSource = sources[0];
      const isDr = (firstSource.debit || 0) > 0;

      // Calculate total source amount for the group
      const totalSourceAmt = sources.reduce((sum, s) => sum + (isDr ? (s.debit || 0) : (s.credit || 0)), 0);

      if (applications.length === 0) {
        const raw = firstSource.rawVoucher || {};
        const vtLower = (firstSource.voucherType || '').toLowerCase();
        const txType = (raw.voucher_type || raw.type || vtLower).toLowerCase();
        const isPurchase = txType.includes('purchase') || txType.includes('expense');
        const isSales = txType.includes('sales') || txType.includes('invoice');
        const isDebitNote = vtLower.includes('debit');
        const isCreditNote = vtLower.includes('credit');
        const isPayment = vtLower.includes('payment') || vtLower.includes('receipt') || vtLower.includes('contra');

        const rawDueStatus = raw.due_status || '';
        let displayStatus = getAgingStatus(firstSource.date);

        if (raw.is_disputed || raw.status === 'Disputed' || raw.payment_status === 'Disputed') {
          displayStatus = 'Disputed';
        } else if (isSales || isDebitNote) {
          if (rawDueStatus) displayStatus = rawDueStatus;
          else if (totalSourceAmt === 0) displayStatus = 'Received';
          else displayStatus = displayStatus;
        } else if (isPurchase || isCreditNote) {
          if (rawDueStatus) displayStatus = rawDueStatus;
          else if (totalSourceAmt === 0) displayStatus = 'Paid';
          else displayStatus = displayStatus;
        } else if (isPayment) {
          if (rawDueStatus) displayStatus = rawDueStatus;
          else if (totalSourceAmt === 0) displayStatus = 'Utilized';
          else displayStatus = 'Unutilized';
        } else {
          const sourceAllocStatus = raw.allocation_status;
          displayStatus = sourceAllocStatus === 'Utilized' ? 'Paid' : (totalSourceAmt === 0 ? 'Paid' : displayStatus);
        }

        let pendingBal = totalSourceAmt;
        if (['Paid', 'Received', 'Utilized'].includes(displayStatus)) {
          pendingBal = 0;
        }

        rows.push({
          date: firstSource.date,
          postedFrom: firstSource.voucherType,
          refNo: firstSource.referenceNo !== '-' ? firstSource.referenceNo : (firstSource.voucherNo || '-'),
          netAmount: totalSourceAmt,
          appliedDate: '-',
          appliedRefNo: '-',
          appliedAmount: '-',
          pendingBalance: pendingBal,
          status: displayStatus,
          rowSpan: 1,
          isFirstInSource: true
        });
      } else {
        let lastPending = totalSourceAmt;
        const totalAppAmt = applications.reduce((sum, a) => {
          const expectedAmt = isDr ? (a.credit || 0) : (a.debit || 0);
          const amt = expectedAmt > 0 ? expectedAmt : Math.max(a.debit || 0, a.credit || 0);
          return sum + amt;
        }, 0);

        let calcStatus = getAgingStatus(firstSource.date);
        if (Math.round(totalSourceAmt * 100) <= Math.round(totalAppAmt * 100)) {
          calcStatus = 'Paid';
        } else if (totalAppAmt > 0) {
          calcStatus = 'Partially Paid';
        }

        // If any application is explicitly utilized, we can also consider it partially paid at least
        if ((calcStatus === 'Due' || calcStatus === 'Not Due') && applications.some(a => a.rawVoucher?.allocation_status === 'Utilized')) {
          calcStatus = 'Partially Paid';
        }

        applications.forEach((app, appIdx) => {
          const expectedAmt = isDr ? (app.credit || 0) : (app.debit || 0);
          const appAmt = expectedAmt > 0 ? expectedAmt : Math.max(app.debit || 0, app.credit || 0);
          const currentPending = Math.max(0, lastPending - appAmt);
          rows.push({
            date: firstSource.date,
            postedFrom: firstSource.voucherType,
            refNo: firstSource.referenceNo !== '-' ? firstSource.referenceNo : (firstSource.voucherNo || '-'),
            netAmount: totalSourceAmt,
            appliedDate: app.date,
            appliedRefNo: app.voucherNo || '-',
            appliedAmount: appAmt,
            pendingBalance: currentPending,
            status: calcStatus,
            rowSpan: applications.length,
            isFirstInSource: appIdx === 0
          });
          lastPending = currentPending;
        });
      }
    });
    return rows;
  }, [drillDownEntries]);

  const filteredDaybookResults = useMemo(() => {
    let list = daybookData?.results || [];
    if (startDate && startDate.trim()) {
      list = list.filter((v: any) => v.date && v.date >= startDate);
    }
    if (endDate && endDate.trim()) {
      list = list.filter((v: any) => v.date && v.date <= endDate);
    }
    if (daybookVoucherType && daybookVoucherType !== 'all') {
      const targetVt = daybookVoucherType.toLowerCase();
      list = list.filter((v: any) => (v.type || '').toLowerCase().includes(targetVt));
    }
    if (daybookSearch && daybookSearch.trim()) {
      list = list.filter((v: any) => matchRefOrVoucherNo({ rawVoucher: v, voucherNo: v.voucher_number, referenceNo: v.reference_number || v.ref_no }, daybookSearch));
    }
    if (daybookPartyFilter && daybookPartyFilter.trim()) {
      const q = daybookPartyFilter.toLowerCase().trim();
      list = list.filter((v: any) => (v.party || '').toLowerCase().includes(q));
    }
    if (daybookMinAmount !== '' && !isNaN(Number(daybookMinAmount))) {
      const minVal = Number(daybookMinAmount);
      list = list.filter((v: any) => Number(v.amount || 0) >= minVal);
    }
    if (daybookMaxAmount !== '' && !isNaN(Number(daybookMaxAmount))) {
      const maxVal = Number(daybookMaxAmount);
      list = list.filter((v: any) => Number(v.amount || 0) <= maxVal);
    }
    return list;
  }, [daybookData, startDate, endDate, daybookVoucherType, daybookSearch, daybookPartyFilter, daybookMinAmount, daybookMaxAmount]);

  const renderDayBook = () => (
    <div className="erp-table-container">
      <table className="erp-table min-w-full">
        <thead className="bg-[#F8F9FA] border-b border-gray-200">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider min-w-[120px]">
              <div className="py-1.5 text-slate-700 font-bold">Date</div>
            </th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider min-w-[150px]">
              <div className="mb-1 text-slate-700">Voucher Type</div>
              <select
                value={daybookVoucherType}
                onChange={(e) => setDaybookVoucherType(e.target.value)}
                className="w-full text-xs font-normal py-1 px-2 border rounded border-slate-300 bg-white"
              >
                <option value="all">All Types</option>
                <option value="Sales">Sales</option>
                <option value="Purchase">Purchase</option>
                <option value="Payment">Payment</option>
                <option value="Receipt">Receipt</option>
                <option value="Expense">Expense</option>
                <option value="Journal">Journal</option>
                <option value="Contra">Contra</option>
                <option value="Debit Note">Debit Note</option>
                <option value="Credit Note">Credit Note</option>
              </select>
            </th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider min-w-[150px]">
              <div className="mb-1 text-slate-700">Reference No</div>
              <input
                type="text"
                placeholder="Filter Ref..."
                value={daybookSearch}
                onChange={(e) => setDaybookSearch(e.target.value)}
                className="w-full text-xs font-normal py-1 px-2 border rounded border-slate-300 bg-white"
              />
            </th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider min-w-[160px]">
              <div className="mb-1 text-slate-700">Party</div>
              <input
                type="text"
                placeholder="Filter Party..."
                value={daybookPartyFilter}
                onChange={(e) => setDaybookPartyFilter(e.target.value)}
                className="w-full text-xs font-normal py-1 px-2 border rounded border-slate-300 bg-white"
              />
            </th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider min-w-[180px]">
              <div className="mb-1 text-slate-700">Amount</div>
              <div className="flex items-center justify-end gap-1">
                <input
                  type="number"
                  placeholder="Min ₹"
                  value={daybookMinAmount}
                  onChange={(e) => setDaybookMinAmount(e.target.value)}
                  className="w-20 text-xs font-normal py-1 px-1 border rounded border-slate-300 bg-white text-right"
                />
                <input
                  type="number"
                  placeholder="Max ₹"
                  value={daybookMaxAmount}
                  onChange={(e) => setDaybookMaxAmount(e.target.value)}
                  className="w-20 text-xs font-normal py-1 px-1 border rounded border-slate-300 bg-white text-right"
                />
              </div>
            </th>
            <th className="px-4 py-3 text-center text-xs font-semibold text-gray-600 uppercase tracking-wider print:hidden min-w-[80px]">
              <div className="mb-1 text-slate-700">Action</div>
              {(startDate || endDate || daybookVoucherType !== 'all' || daybookSearch || daybookPartyFilter || daybookMinAmount || daybookMaxAmount) ? (
                <button
                  onClick={() => {
                    setStartDate('');
                    setEndDate('');
                    setDaybookVoucherType('all');
                    setDaybookSearch('');
                    setDaybookPartyFilter('');
                    setDaybookMinAmount('');
                    setDaybookMaxAmount('');
                  }}
                  className="text-[10px] bg-rose-50 text-rose-600 hover:bg-rose-100 font-bold px-2 py-0.5 rounded border border-rose-200"
                  title="Clear All Filters"
                >
                  Clear
                </button>
              ) : <span className="text-[10px] text-slate-400 font-normal">-</span>}
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-100">
          {daybookLoading && (
            <tr><td colSpan={6} className="px-6 py-12 text-sm text-center text-gray-400">Loading day book…</td></tr>
          )}
          {!daybookLoading && filteredDaybookResults.length > 0
            ? filteredDaybookResults.map((v, idx) => (
              <tr
                key={`daybook-${v.type}-${v.date}-${idx}`}
                className="hover:bg-indigo-50 transition-colors cursor-pointer group"
                onClick={() => {
                  if (setViewVoucherData && onNavigate) {
                    setViewVoucherData(v);
                    onNavigate('Vouchers');
                  }
                }}
              >
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">{formatDate(v.date)}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-900">{v.type}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-indigo-600">{v.voucher_number || '-'}</td>
                <td
                  className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 group-hover:text-indigo-600 group-hover:font-semibold transition-colors cursor-pointer"
                  onClick={(e) => {
                    if (!v.party) return;
                    e.stopPropagation();
                    setReportType('LedgerReport');
                    setDrillDownLedger(v.party);
                  }}
                  title={v.party ? `View Ledger Report for ${v.party}` : ''}
                >
                  {v.party || '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-right font-semibold text-gray-900">₹{Number(v.amount).toFixed(2)}</td>
                <td className="px-6 py-4 whitespace-nowrap text-center print:hidden" onClick={(e) => {
                  e.stopPropagation();
                  if (setViewVoucherData && onNavigate) {
                    setViewVoucherData(v);
                    onNavigate('Vouchers');
                  }
                }}>
                  <button className="text-indigo-600 hover:text-indigo-900 mx-auto inline-block" title="View Voucher">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                  </button>
                </td>
              </tr>
            ))
            : !daybookLoading && (
              <tr>
                <td colSpan={6} className="px-6 py-12 text-sm text-center text-gray-500">
                  {(startDate || endDate || daybookVoucherType !== 'all' || daybookSearch || daybookMinAmount || daybookMaxAmount) ? 'No transactions found for the selected filters.' : 'No transactions found.'}
                </td>
              </tr>
            )
          }
        </tbody>
        {!daybookLoading && daybookData && (
          <tfoot className="bg-gray-50 border-t border-gray-200">
            <tr>
              <td colSpan={4} className="px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Total ({filteredDaybookResults.length} entries)</td>
              <td className="px-6 py-3 text-sm font-mono text-right font-bold text-gray-900">
                ₹{filteredDaybookResults.reduce((s, v) => s + Number(v.amount || 0), 0).toFixed(2)}
              </td>
              <td className="print:hidden" />
            </tr>
          </tfoot>
        )}
      </table>
    </div>
  );




  // ═══ LEVEL 1: Summary view — Ledger Name + Balance only (clickable) ════════
  const renderLedgerSummary = () => (
    <div className="erp-table-container">
      <table className="erp-table w-full">
        <thead>
          <tr className="bg-indigo-50">
            <th className="px-6 py-3 text-left text-xs font-bold text-indigo-700 uppercase tracking-wider w-5/12">Ledger Name</th>
            <th className="px-6 py-3 text-left text-xs font-bold text-indigo-700 uppercase tracking-wider w-3/12">Category</th>
            <th className="px-6 py-3 text-right text-xs font-bold text-indigo-700 uppercase tracking-wider w-4/12">Running Balance</th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-100">
          {ledgerSummary.length > 0 ? ledgerSummary.map((row, idx) => (
            <tr key={`ls-${idx}`} onClick={() => setDrillDownLedger(row.name)}
              className="hover:bg-indigo-50 transition-colors cursor-pointer group" title={`View ${row.name} transactions`}>
              <td className="px-6 py-3 whitespace-nowrap">
                <span className="text-sm font-semibold text-indigo-700 group-hover:underline flex items-center gap-1">
                  {row.name}
                  <svg className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </span>
              </td>
              <td className="px-6 py-3 whitespace-nowrap text-left">
                <span className="px-2 py-1 text-xs font-medium rounded-md bg-gray-100 text-gray-700 border border-gray-200 shadow-sm">{row.category}</span>
              </td>
              <td className="px-6 py-3 whitespace-nowrap text-right">
                <span className={`text-sm font-mono font-bold ${row.balanceType === 'Dr' ? 'text-indigo-600' : 'text-green-700'}`}>
                  ₹{row.balance.toFixed(2)}
                  <span className={`ml-1.5 text-xs px-1.5 py-0.5 rounded font-semibold ${row.balanceType === 'Dr' ? 'bg-indigo-100 text-indigo-700' : 'bg-green-100 text-green-700'}`}>{row.balanceType}</span>
                </span>
              </td>
            </tr>
          )) : (
            <tr><td colSpan={3} className="px-6 py-12 text-sm text-center text-gray-400">No ledger data found. Add some vouchers first.</td></tr>
          )}
        </tbody>
        {ledgerSummary.length > 0 && (
          <tfoot className="bg-gray-50 border-t-2 border-gray-200">
            <tr>
              <td className="px-6 py-3 text-sm font-bold text-gray-600">{ledgerSummary.length} Ledgers</td>
              <td className="px-6 py-3"></td>
              <td className="px-6 py-3 text-right text-sm font-bold text-indigo-600">
                Dr: ₹{ledgerSummary.filter(r => r.balanceType === 'Dr').reduce((s, r) => s + r.balance, 0).toFixed(2)}
              </td>
            </tr>
          </tfoot>
        )}
      </table>
    </div>
  );

  // ═══ LEVEL 2: Detail view — full transactions for a specific ledger ═════════
  const renderLedgerDetail = () => {
    const last = drillDownEntries[drillDownEntries.length - 1];
    const fmtDate = (d: string) => d ? formatDate(d) : '-';
    const totalDr = filteredDrillData.reduce((s, e) => s + (e.debit || 0), 0);
    const totalCr = filteredDrillData.reduce((s, e) => s + (e.credit || 0), 0);

    const isTdsTcsLedger = drillDownLedger && (drillDownLedger.toLowerCase().includes('tds') || drillDownLedger.toLowerCase().includes('tcs'));

    const viewBtns = [
      { key: 'ledger', label: 'Bill-wise View' },
      { key: 'journal', label: 'Journal View' },
      { key: 'month', label: 'Month View' },
      { key: 'allocation', label: 'Allocation View' },
    ] as const;

    return (
      <div>
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 mb-4 text-sm">
          <button onClick={() => { setDrillDownLedger(null); setDrillDownSourceType(null); resetLedgerDetailFilters(); }} className="flex items-center gap-1 text-indigo-600 hover:text-indigo-900 font-semibold transition-colors">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
            All Ledgers
          </button>
          <span className="text-gray-300">/</span>
          <span className="font-bold text-gray-800">{drillDownLedger}</span>
        </div>

        {/* Header + View Switcher */}
        <div className="erp-card border border-slate-200 overflow-hidden p-0 mb-4">
          <div className="flex justify-between items-center px-6 py-4 border-b border-gray-200 bg-gray-50">
            <div>
              <div className="text-xs text-indigo-500 uppercase font-bold tracking-widest mb-1">Ledger Account</div>
              <div className="text-xl font-bold text-indigo-900">{drillDownLedger}</div>
            </div>
            <div className="flex items-center gap-3">
              {last && (
                <div className="text-right mr-4">
                  <div className="text-xs text-gray-500 uppercase font-bold tracking-widest mb-1">Closing Balance</div>
                  <div className={`text-2xl font-bold ${last.balanceType === 'Dr' ? 'text-indigo-600' : 'text-green-700'}`}>
                    ₹{last.balance.toFixed(2)}
                    <span className={`ml-2 text-sm px-2 py-0.5 rounded font-semibold ${last.balanceType === 'Dr' ? 'bg-indigo-100 text-indigo-700' : 'bg-green-100 text-green-700'}`}>{last.balanceType}</span>
                  </div>
                </div>
              )}
              {viewBtns.map(b => (
                <button key={b.key} onClick={() => setLedgerViewMode(b.key as any)}
                  className={`px-4 py-2 rounded-[4px] text-sm font-medium border transition-colors shadow-sm ${ledgerViewMode === b.key ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'}`}>
                  {b.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* ── LEDGER VIEW ── */}
        {ledgerViewMode === 'ledger' && (
          <div className="erp-card border border-slate-200 overflow-hidden p-0">
            {isDrillDownLoading ? (
              <div className="flex items-center justify-center py-16 gap-3 text-indigo-600">
                <svg className="animate-spin h-6 w-6" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
                <span className="text-sm font-semibold">Loading transactions...</span>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="erp-table min-w-full">
                  <thead className="bg-[#F8F9FA] border-b border-slate-200">
                    <tr>
                      <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider border-r border-slate-200 min-w-[110px]">
                        <div className="py-1.5 text-slate-700 font-bold">Date</div>
                      </th>
                      <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider border-r border-slate-200 min-w-[140px]">
                        <div className="mb-1 text-slate-700">Created From</div>
                        <select
                          value={ledgerVoucherType}
                          onChange={(e) => setLedgerVoucherType(e.target.value)}
                          className="w-full text-xs font-normal py-1 px-2 border rounded border-slate-300 bg-white"
                        >
                          <option value="all">All Types</option>
                          <option value="Sales">Sales</option>
                          <option value="Purchase">Purchase</option>
                          <option value="Payment">Payment</option>
                          <option value="Receipt">Receipt</option>
                          <option value="Expense">Expense</option>
                          <option value="Journal">Journal</option>
                          <option value="Contra">Contra</option>
                          <option value="Debit Note">Debit Note</option>
                          <option value="Credit Note">Credit Note</option>
                        </select>
                      </th>
                      <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider border-r border-slate-200 min-w-[140px]">
                        <div className="mb-1 text-slate-700">Reference No</div>
                        <input
                          type="text"
                          placeholder="Filter Ref..."
                          value={ledgerRefSearch}
                          onChange={(e) => setLedgerRefSearch(e.target.value)}
                          className="w-full text-xs font-normal py-1 px-2 border rounded border-slate-300 bg-white"
                        />
                      </th>
                      {isTdsTcsLedger && (
                        <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider border-r border-slate-200 min-w-[120px]">
                          <div className="mb-1 text-slate-700">Section</div>
                          <select
                            value={selectedSection}
                            onChange={(e) => setSelectedSection(e.target.value)}
                            className="w-full text-xs font-normal py-1 px-2 border rounded border-slate-300 bg-white"
                          >
                            <option value="all">All</option>
                            {(availableSections || []).map(sec => (
                              <option key={sec} value={sec}>{sec}</option>
                            ))}
                          </select>
                        </th>
                      )}
                      <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider border-r border-slate-200 min-w-[160px]">
                        <div className="mb-1 text-slate-700">Ledger</div>
                        <input
                          type="text"
                          placeholder="Filter Ledger..."
                          value={ledgerSearch}
                          onChange={(e) => setLedgerSearch(e.target.value)}
                          className="w-full text-xs font-normal py-1 px-2 border rounded border-slate-300 bg-white"
                        />
                      </th>
                      <th className="px-3 py-2 text-center text-xs font-semibold text-gray-500 uppercase tracking-wider border-r border-slate-200">
                        <div>GST Rate</div>
                      </th>
                      <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider border-r border-slate-200 min-w-[130px]">
                        <div className="mb-1 text-slate-700">Status</div>
                        <select
                          value={ledgerStatusFilter}
                          onChange={(e) => setLedgerStatusFilter(e.target.value)}
                          className="w-full text-xs font-normal py-1 px-2 border rounded border-slate-300 bg-white"
                        >
                          <option value="all">All</option>
                          <option value="Not Due">Not Due</option>
                          <option value="Due">Due / Overdue</option>
                          <option value="Paid">Paid</option>
                          <option value="Received">Received</option>
                          <option value="Partially Paid">Partially Paid</option>
                          <option value="Partially Received">Partially Received</option>
                          <option value="Utilized">Utilized</option>
                          <option value="Unutilized">Unutilized</option>
                          <option value="Disputed">Disputed</option>
                        </select>
                      </th>
                      <th className="px-3 py-2 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider border-r border-slate-200">
                        <div>Debit (₹)</div>
                      </th>
                      <th className="px-3 py-2 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider border-r border-slate-200">
                        <div>Credit (₹)</div>
                      </th>
                      <th className="px-3 py-2 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider border-r border-slate-200">
                        <div>Running Bal</div>
                      </th>
                      <th className="px-3 py-2 text-center text-xs font-semibold text-gray-500 uppercase tracking-wider min-w-[70px]">
                        <div className="mb-1 text-slate-700">Action</div>
                        {(startDate || endDate || ledgerVoucherType !== 'all' || ledgerStatusFilter !== 'all' || ledgerSearch || ledgerRefSearch || selectedSection !== 'all') ? (
                          <button
                            onClick={() => {
                              setStartDate('');
                              setEndDate('');
                              setLedgerVoucherType('all');
                              setLedgerStatusFilter('all');
                              setLedgerSearch('');
                              setLedgerRefSearch('');
                              setSelectedSection('all');
                            }}
                            className="text-[10px] bg-rose-50 text-rose-600 hover:bg-rose-100 font-bold px-2 py-0.5 rounded border border-rose-200"
                            title="Clear All Filters"
                          >
                            Clear
                          </button>
                        ) : <span className="text-[10px] text-slate-400 font-normal">-</span>}
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-100">
                    {filteredDrillData.length > 0 ? filteredDrillData.map((e, idx) => {
                      // ── Unified Status Logic (As per user request) ──────────────────────
                      let st = '';
                      const raw = e.rawVoucher || {};

                      // Calculate if credit term is expired
                      let isExpired = false;
                      const amount = parseFloat(raw.total || raw.amount || raw.total_amount || 0);
                      const paidAmount = parseFloat(raw.paid_amount || raw.used_amount || 0);
                      const pendingBalance = Math.max(0, amount - paidAmount);

                      if (amount > 0 && e.date) {
                        const activeLedgerNameForStatus = drillDownLedger?.includes(':') ? drillDownLedger.split(':')[1] : drillDownLedger;
                        const activeLedgerForStatus = ledgers?.find((l: any) => l.name === activeLedgerNameForStatus);
                        const cpStrStatus = activeLedgerForStatus?.additional_data?.credit_period || (activeLedgerForStatus as any)?.credit_period || activeLedgerForStatus?.creditPeriod || '0';
                        const cpStatus = parseInt(String(cpStrStatus), 10) || (drillDownData[0]?.ledger_credit_period || 0);
                        const invDate = new Date(e.date);
                        const today = new Date();
                        const diffDays = Math.floor((new Date(today.getFullYear(), today.getMonth(), today.getDate()).getTime() - new Date(invDate.getFullYear(), invDate.getMonth(), invDate.getDate()).getTime()) / 86400000);
                        isExpired = diffDays > cpStatus;
                      }

                      const vtLower = (e.voucherType || '').toLowerCase();
                      const txType = (raw.voucher_type || raw.type || vtLower).toLowerCase();
                      const isPurchase = txType.includes('purchase') || txType.includes('expense');
                      const isSales = txType.includes('sales') || txType.includes('invoice');
                      const isDebitNote = vtLower.includes('debit');
                      const isCreditNote = vtLower.includes('credit');
                      const isPayment = vtLower.includes('payment') || vtLower.includes('receipt') || vtLower.includes('contra');

                      // 1. Check Disputed
                      if (raw.is_disputed || raw.status === 'Disputed' || raw.payment_status === 'Disputed') {
                        st = 'Disputed';
                      } else if (isSales || isDebitNote) {
                        // ── Customer Portal parity: trust backend due_status FIRST ──
                        const rawDueStatus = raw.due_status || '';
                        if (rawDueStatus) {
                          st = rawDueStatus; // 'Due', 'Not Due', 'Received', 'Partially Received' from backend
                        } else if (pendingBalance === 0 && amount > 0) st = 'Received';
                        else if (pendingBalance < amount && pendingBalance > 0) st = 'Partially Received';
                        else if (pendingBalance === amount) st = isExpired ? 'Due' : 'Not Due';
                        else st = 'Not Due';
                      } else if (isPurchase || isCreditNote) {
                        // ── Vendor Portal parity: trust backend due_status when no payment applied yet ──
                        const rawDueStatus = raw.due_status || '';
                        if (rawDueStatus && pendingBalance === amount) {
                          st = rawDueStatus; // 'Paid', 'Partially Paid', 'Due', 'Not Due' from backend
                        } else if (pendingBalance === 0 && amount > 0) st = 'Paid';
                        else if (pendingBalance < amount && pendingBalance > 0) st = 'Partially Paid';
                        else if (pendingBalance === amount) st = isExpired ? 'Due' : 'Not Due';
                        else st = 'Not Due';
                      } else if (isPayment) {
                        // ── Portal parity: trust backend due_status (same notes-based lookup) ──
                        const rawPayStatus = raw.due_status || '';
                        if (rawPayStatus) {
                          st = rawPayStatus; // 'Utilized', 'Partially Utilized', 'Unutilized', 'Advance Applied' from backend
                        } else if (pendingBalance === 0 && amount > 0) st = 'Utilized';
                        else if (pendingBalance < amount && pendingBalance > 0) st = 'Partially Utilized';
                        else st = 'Unutilized';
                      } else {
                        st = '-';
                      }

                      // GST Rate calculation helper
                      const getGstRateVal = () => {
                        if (!e || e.voucherType === 'Opening') return '-';
                        let rate = raw.gst_rate ?? raw.gstRate ?? e.gst_rate ?? e.gstRate;
                        if (rate !== undefined && rate !== null && rate !== '' && !isNaN(Number(rate)) && Number(rate) > 0) {
                          return `${Number(rate)}%`;
                        }
                        const parts = String(e.particulars || '');
                        const match = parts.match(/@\s*(\d+(?:\.\d+)?)\s*%/);
                        if (match) {
                          return `${match[1]}%`;
                        }
                        if (e.full_legs && Array.isArray(e.full_legs) && e.full_legs.length > 0) {
                          const isTaxLeg = (name: string) => {
                            const n = (name || '').toLowerCase();
                            return n.includes('tax liability') || n.includes('tax credit') || n.includes('cgst') || n.includes('sgst') || n.includes('igst') || n.includes('output gst') || n.includes('input gst');
                          };
                          const taxLegs = e.full_legs.filter((l: any) => isTaxLeg(l.ledger_name) && !l.ledger_name?.toLowerCase().includes('tds') && !l.ledger_name?.toLowerCase().includes('tcs'));
                          const totalTax = taxLegs.reduce((sum: number, l: any) => sum + (l.debit || 0) + (l.credit || 0), 0);

                          if (totalTax > 0) {
                            const isPartyLeg = (name: string) => {
                              const n = (name || '').toLowerCase();
                              return isTaxLeg(n) || n.includes('tds') || n.includes('tcs') || n.includes('sundry debtor') || n.includes('sundry creditor') || n.includes('cash') || n.includes('bank');
                            };
                            const baseLegs = e.full_legs.filter((l: any) => !isPartyLeg(l.ledger_name));
                            let totalBase = baseLegs.reduce((sum: number, l: any) => sum + (l.debit || 0) + (l.credit || 0), 0);
                            if (totalBase === 0) {
                              const totalVoucherAmount = e.full_legs.reduce((maxVal: number, l: any) => Math.max(maxVal, l.debit || 0, l.credit || 0), 0);
                              totalBase = Math.max(0, totalVoucherAmount - totalTax);
                            }
                            if (totalBase > 0) {
                              const calc = Math.round((totalTax / totalBase) * 100);
                              if (calc > 0) return `${calc}%`;
                            }
                          }
                        }
                        return '-';
                      };

                      return (
                        <tr key={`dd-${idx}`}
                          className={`transition-colors ${e.voucherType === 'Opening' ? 'bg-indigo-50/50' : 'hover:bg-indigo-50'}`}>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 border-r border-gray-50">{fmtDate(e.date)}</td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 border-r border-gray-50">{normalizeVoucherType(e.voucherType) || '-'}</td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-blue-600 font-medium border-r border-gray-50">{e.referenceNo && e.referenceNo !== '-' ? e.referenceNo : (e.voucherNo || '-')}</td>
                          {isTdsTcsLedger && (
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-bold text-indigo-600 border-r border-gray-50">
                              {e.rawVoucher?.tds_components ? e.rawVoucher.tds_components.map((c: any) => c.component).join(', ') : '-'}
                            </td>
                          )}
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 border-r border-gray-50">
                            {isTdsTcsLedger && e.particulars && typeof e.particulars === 'string' ? e.particulars.split(' | ')[0] : (e.particulars || '-')}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-center font-semibold text-indigo-700 border-r border-gray-50">
                            {getGstRateVal()}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap border-r border-gray-50">
                            {st !== '-' && e.voucherType !== 'Opening' ? (
                              <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-[4px] ${st === 'Received' ? 'bg-green-100 text-green-800' :
                                st === 'Paid' ? 'bg-green-100 text-green-800' :
                                  st === 'Utilized' ? 'bg-teal-100 text-teal-800' :
                                    st === 'Due' ? 'bg-red-100 text-red-800' :
                                      st === 'Not Due' ? 'bg-blue-100 text-blue-700' :
                                        st === 'Partially Received' ? 'bg-yellow-100 text-yellow-800' :
                                          st === 'Partially Paid' ? 'bg-indigo-100 text-indigo-700' :
                                            st === 'Partially Utilized' ? 'bg-indigo-100 text-indigo-700' :
                                              st === 'Advance Applied' ? 'bg-purple-100 text-purple-700' :
                                                st === 'Advance' ? 'bg-purple-100 text-purple-700' :
                                                  st === 'Unutilized' ? 'bg-gray-100 text-gray-600' :
                                                    st === 'Open' ? 'bg-gray-100 text-gray-600' :
                                                      'bg-gray-100 text-gray-600'
                                }`}>{st}</span>
                            ) : '-'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900 border-r border-gray-50">{e.debit > 0 ? `₹${e.debit.toFixed(2)}` : '-'}</td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900 border-r border-gray-50">{e.credit > 0 ? `₹${e.credit.toFixed(2)}` : '-'}</td>
                          <td className={`px-6 py-4 whitespace-nowrap text-sm text-right font-bold border-r border-gray-50 ${e.balanceType === 'Dr' ? 'text-indigo-600' : e.balanceType === 'Cr' ? 'text-green-700' : 'text-gray-400'}`}>
                            {e.balance > 0 ? <>{`₹${e.balance.toFixed(2)} `}<span className={`text-[10px] font-normal uppercase ${e.balanceType === 'Dr' ? 'text-indigo-600' : 'text-green-700'}`}>{e.balanceType}</span></> : '-'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-center">
                            {e.voucherType !== 'Opening' && (
                              <button onClick={() => handleViewTransaction(e)} className="text-indigo-600 hover:text-indigo-900 mx-auto inline-block" title="View Transaction">
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>
                              </button>
                            )}
                          </td>
                        </tr>
                      )
                    }) : (
                      <tr><td colSpan={isTdsTcsLedger ? 11 : 10} className="px-6 py-12 text-center text-sm text-gray-400">No transactions found for <strong>{drillDownLedger}</strong>.</td></tr>
                    )}
                  </tbody>
                  {filteredDrillData.length > 0 && (
                    <tfoot className="bg-gray-50 font-bold border-t border-gray-200">
                      <tr>
                        <td colSpan={isTdsTcsLedger ? 7 : 6} className="px-6 py-3 text-right text-gray-900 text-sm">TOTAL</td>
                        <td className="px-6 py-3 text-right text-gray-900 text-sm">₹{totalDr.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                        <td className="px-6 py-3 text-right text-gray-900 text-sm">₹{totalCr.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                        <td className={`px-6 py-3 text-right text-sm ${last?.balanceType === 'Dr' ? 'text-indigo-600' : 'text-green-700'}`}>{last ? `₹${last.balance.toLocaleString('en-IN', { minimumFractionDigits: 2 })}` : ''}</td>
                        <td></td>
                      </tr>
                    </tfoot>
                  )}
                </table>
              </div>
            )}
          </div>
        )}

        {/* ── JOURNAL VIEW ── */}
        {ledgerViewMode === 'journal' && (
          <div className="erp-card border border-slate-200 overflow-hidden p-0">
            {isDrillDownLoading ? (
              <div className="flex items-center justify-center py-16 gap-3 text-indigo-600">
                <svg className="animate-spin h-6 w-6" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
                <span className="text-sm font-semibold">Loading journal view...</span>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full">
                  <thead className="border-y border-gray-100 bg-white">
                    <tr>
                      <th className="px-6 py-4 text-left text-xs font-bold text-gray-400 uppercase tracking-wider w-[120px] border-r border-gray-50">Date</th>
                      <th className="px-6 py-4 text-left text-xs font-bold text-gray-400 uppercase tracking-wider min-w-[350px] border-r border-gray-50">Transaction Particulars</th>
                      <th className="px-6 py-4 text-left text-xs font-bold text-gray-400 uppercase tracking-wider w-[120px] border-r border-gray-50">Type</th>
                      <th className="px-6 py-4 text-left text-xs font-bold text-gray-400 uppercase tracking-wider w-[120px] border-r border-gray-50">VCH No.</th>
                      <th className="px-6 py-4 text-center text-xs font-bold text-gray-400 uppercase tracking-wider w-[100px] border-r border-gray-50">GST Rate</th>
                      <th className="px-6 py-4 text-left text-xs font-bold text-gray-400 uppercase tracking-wider w-[120px] border-r border-gray-50">Status</th>
                      <th className="px-6 py-4 text-right text-xs font-bold text-gray-400 uppercase tracking-wider w-[140px] border-r border-gray-50">Debit (₹)</th>
                      <th className="px-6 py-4 text-right text-xs font-bold text-gray-400 uppercase tracking-wider w-[140px] border-r border-gray-50">Credit (₹)</th>
                      <th className="px-6 py-4 text-right text-xs font-bold text-gray-400 uppercase tracking-wider w-[150px]">RUNNING BALANCE</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white">
                    {filteredDrillData.length > 0 ? filteredDrillData.map((e, idx) => {
                      // ── Unified Status Logic (As per user request) ──────────────────────
                      let st = '';
                      const raw = e.rawVoucher || {};

                      // Calculate if credit term is expired
                      let isExpired = false;
                      const amount = parseFloat(raw.total || raw.amount || raw.total_amount || 0);
                      const paidAmount = parseFloat(raw.paid_amount || raw.used_amount || 0);
                      const pendingBalance = Math.max(0, amount - paidAmount);

                      if (amount > 0 && e.date) {
                        const activeLedgerNameForStatus = drillDownLedger?.includes(':') ? drillDownLedger.split(':')[1] : drillDownLedger;
                        const activeLedgerForStatus = ledgers?.find((l: any) => l.name === activeLedgerNameForStatus);
                        const cpStrStatus = activeLedgerForStatus?.additional_data?.credit_period || (activeLedgerForStatus as any)?.credit_period || activeLedgerForStatus?.creditPeriod || '0';
                        const cpStatus = parseInt(String(cpStrStatus), 10) || (drillDownData[0]?.ledger_credit_period || 0);
                        const invDate = new Date(e.date);
                        const today = new Date();
                        const diffDays = Math.floor((new Date(today.getFullYear(), today.getMonth(), today.getDate()).getTime() - new Date(invDate.getFullYear(), invDate.getMonth(), invDate.getDate()).getTime()) / 86400000);
                        isExpired = diffDays > cpStatus;
                      }

                      const vtLower = (e.voucherType || '').toLowerCase();
                      const txType = (raw.voucher_type || raw.type || vtLower).toLowerCase();
                      const isPurchase = txType.includes('purchase') || txType.includes('expense');
                      const isSales = txType.includes('sales') || txType.includes('invoice');
                      const isDebitNote = vtLower.includes('debit');
                      const isCreditNote = vtLower.includes('credit');
                      const isPayment = vtLower.includes('payment') || vtLower.includes('receipt') || vtLower.includes('contra');

                      // 1. Check Disputed
                      if (raw.is_disputed || raw.status === 'Disputed' || raw.payment_status === 'Disputed') {
                        st = 'Disputed';
                      } else if (isSales || isDebitNote) {
                        // ── Customer Portal parity: trust backend due_status FIRST ──
                        const rawDueStatus = raw.due_status || '';
                        if (rawDueStatus) {
                          st = rawDueStatus; // 'Due', 'Not Due', 'Received', 'Partially Received' from backend
                        } else if (pendingBalance === 0 && amount > 0) st = 'Received';
                        else if (pendingBalance < amount && pendingBalance > 0) st = 'Partially Received';
                        else if (pendingBalance === amount) st = isExpired ? 'Due' : 'Not Due';
                        else st = 'Not Due';
                      } else if (isPurchase || isCreditNote) {
                        // ── Vendor Portal parity: trust backend due_status when no payment applied yet ──
                        const rawDueStatus = raw.due_status || '';
                        if (rawDueStatus && pendingBalance === amount) {
                          st = rawDueStatus; // 'Paid', 'Partially Paid', 'Due', 'Not Due' from backend
                        } else if (pendingBalance === 0 && amount > 0) st = 'Paid';
                        else if (pendingBalance < amount && pendingBalance > 0) st = 'Partially Paid';
                        else if (pendingBalance === amount) st = isExpired ? 'Due' : 'Not Due';
                        else st = 'Not Due';
                      } else if (isPayment) {
                        // ── Portal parity: trust backend due_status ──
                        const rawPayStatus = raw.due_status || '';
                        if (rawPayStatus) {
                          st = rawPayStatus; // 'Utilized', 'Partially Utilized', 'Unutilized', 'Advance Applied' from backend
                        } else if (pendingBalance === 0 && amount > 0) st = 'Utilized';
                        else if (pendingBalance < amount && pendingBalance > 0) st = 'Partially Utilized';
                        else st = 'Unutilized';
                      } else {
                        st = '-';
                      }
                      const stFinal = st || '-';

                      // GST Rate calculation helper for Journal View
                      const getGstRateVal = () => {
                        if (!e || e.voucherType === 'Opening') return '-';
                        let rate = raw.gst_rate ?? raw.gstRate ?? e.gst_rate ?? e.gstRate;
                        if (rate !== undefined && rate !== null && rate !== '' && !isNaN(Number(rate)) && Number(rate) > 0) {
                          return `${Number(rate)}%`;
                        }
                        const parts = String(e.particulars || '');
                        const match = parts.match(/@\s*(\d+(?:\.\d+)?)\s*%/);
                        if (match) {
                          return `${match[1]}%`;
                        }
                        if (e.full_legs && Array.isArray(e.full_legs) && e.full_legs.length > 0) {
                          const isTaxLeg = (name: string) => {
                            const n = (name || '').toLowerCase();
                            return n.includes('tax liability') || n.includes('tax credit') || n.includes('cgst') || n.includes('sgst') || n.includes('igst') || n.includes('output gst') || n.includes('input gst');
                          };
                          const taxLegs = e.full_legs.filter((l: any) => isTaxLeg(l.ledger_name) && !l.ledger_name?.toLowerCase().includes('tds') && !l.ledger_name?.toLowerCase().includes('tcs'));
                          const totalTax = taxLegs.reduce((sum: number, l: any) => sum + (l.debit || 0) + (l.credit || 0), 0);

                          if (totalTax > 0) {
                            const isPartyLeg = (name: string) => {
                              const n = (name || '').toLowerCase();
                              return isTaxLeg(n) || n.includes('tds') || n.includes('tcs') || n.includes('sundry debtor') || n.includes('sundry creditor') || n.includes('cash') || n.includes('bank');
                            };
                            const baseLegs = e.full_legs.filter((l: any) => !isPartyLeg(l.ledger_name));
                            let totalBase = baseLegs.reduce((sum: number, l: any) => sum + (l.debit || 0) + (l.credit || 0), 0);
                            if (totalBase === 0) {
                              const totalVoucherAmount = e.full_legs.reduce((maxVal: number, l: any) => Math.max(maxVal, l.debit || 0, l.credit || 0), 0);
                              totalBase = Math.max(0, totalVoucherAmount - totalTax);
                            }
                            if (totalBase > 0) {
                              const calc = Math.round((totalTax / totalBase) * 100);
                              if (calc > 0) return `${calc}%`;
                            }
                          }
                        }
                        return '-';
                      };

                      return (
                        <React.Fragment key={`dd-j-${idx}`}>
                          {/* ── Main transaction row ── */}
                          <tr className="border-b border-gray-100 hover:bg-indigo-50/30 transition-colors cursor-pointer"
                            onClick={() => e.voucherType !== 'Opening' && handleViewTransaction(e)}>
                            <td className="px-6 py-4 text-sm font-medium text-gray-600 align-top border-r border-gray-100">{fmtDate(e.date)}</td>
                            <td className="px-6 py-4 text-sm font-bold text-gray-800 border-r border-gray-100">{e.voucherType !== 'Opening' ? '(as per details)' : e.particulars || 'Opening Balance'}</td>
                            <td className="px-6 py-4 text-sm text-gray-500 uppercase border-r border-gray-100">{normalizeVoucherType(e.voucherType) || '-'}</td>
                            <td className="px-6 py-4 text-sm text-gray-500 border-r border-gray-100">{e.voucherNo || '-'}</td>
                            <td className="px-6 py-4 text-sm text-center font-semibold text-indigo-700 border-r border-gray-100">{getGstRateVal()}</td>
                            <td className="px-6 py-4 whitespace-nowrap border-r border-gray-100">
                              {stFinal !== '-' && e.voucherType !== 'Opening' ? (
                                <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-[4px] ${stFinal === 'Received' ? 'bg-green-100 text-green-800' :
                                  stFinal === 'Paid' ? 'bg-green-100 text-green-800' :
                                    stFinal === 'Utilized' ? 'bg-teal-100 text-teal-800' :
                                      stFinal === 'Due' ? 'bg-red-100 text-red-800' :
                                        stFinal === 'Not Due' ? 'bg-blue-100 text-blue-700' :
                                          stFinal === 'Partially Received' ? 'bg-yellow-100 text-yellow-800' :
                                            stFinal === 'Partially Paid' ? 'bg-indigo-100 text-indigo-700' :
                                              stFinal === 'Partially Utilized' ? 'bg-indigo-100 text-indigo-700' :
                                                stFinal === 'Advance Applied' ? 'bg-purple-100 text-purple-700' :
                                                  stFinal === 'Advance' ? 'bg-purple-100 text-purple-700' :
                                                    stFinal === 'Unutilized' ? 'bg-gray-100 text-gray-600' :
                                                      stFinal === 'Open' ? 'bg-gray-100 text-gray-600' :
                                                        'bg-gray-100 text-gray-600'
                                  }`}>{stFinal}</span>
                              ) : '-'}
                            </td>
                            <td className="px-6 py-4 text-sm font-bold text-indigo-600 text-right border-r border-gray-100">{e.debit > 0 ? `₹${e.debit.toLocaleString('en-IN', { minimumFractionDigits: 2 })}` : '-'}</td>
                            <td className="px-6 py-4 text-sm font-bold text-gray-900 text-right border-r border-gray-100">{e.credit > 0 ? `₹${e.credit.toLocaleString('en-IN', { minimumFractionDigits: 2 })}` : '-'}</td>
                            <td className="px-6 py-4 text-sm text-right font-bold text-gray-900">
                              {e.balance > 0 ? <>{`₹${e.balance.toLocaleString('en-IN', { minimumFractionDigits: 2 })} `}<span className={`text-[10px] font-normal uppercase ${e.balanceType === 'Dr' ? 'text-indigo-600' : 'text-green-700'}`}>{e.balanceType}</span></> : '-'}
                            </td>
                          </tr>
                          {/* ── Breakdown sub-rows (Customer Portal / Tally style) ── */}
                          {e.voucherType !== 'Opening' && (() => {
                            const raw = e.rawVoucher || {};
                            const fullLegs = raw.full_legs || [];

                            const drLegs: { label: string, amount: number, indent: string }[] = [];
                            const crLegs: { label: string, amount: number, indent: string }[] = [];

                            if (fullLegs.length > 0) {
                              // Robustly determine taxable amount (base value for tax %)
                              // It is the sum of amounts of all legs that are NOT tax/TDS and NOT the customer/vendor ledger itself.
                              const isTaxOrTds = (name: string) => name.includes('Tax Liability') || name.includes('Tax Credit') || name.includes('TDS') || name.includes('TCS');
                              const baseLegs = fullLegs.filter((l: any) => !isTaxOrTds(l.ledger_name) && l.ledger_name !== drillDownLedger);
                              const taxableAmount = baseLegs.reduce((sum: number, l: any) => sum + (l.credit > 0 ? l.credit : l.debit), 0);

                              fullLegs.forEach((leg: any) => {
                                let label = leg.ledger_name;
                                const amount = leg.debit > 0 ? leg.debit : leg.credit;

                                if (taxableAmount > 0 && (label.includes('Tax Liability') || label.includes('Tax Credit') || label.includes('TDS') || label.includes('TCS'))) {
                                  const perc = parseFloat(((amount / taxableAmount) * 100).toFixed(2));
                                  if (perc > 0) {
                                    if (label.includes('Liability')) {
                                      if (label.includes('(CGST)')) label = `Output CGST Ledger @ ${perc}%`;
                                      else if (label.includes('(SGST)') || label.includes('UTGST')) label = `Output SGST Ledger @ ${perc}%`;
                                      else if (label.includes('(IGST)')) label = `Output IGST Ledger @ ${perc}%`;
                                      else if (label.includes('(Cess)')) label = `Output Cess Ledger @ ${perc}%`;
                                      else if (label.includes('State Cess')) label = `Output State Cess Ledger @ ${perc}%`;
                                      else label = `${label} @ ${perc}%`;
                                    } else if (label.includes('Credit')) {
                                      if (label.includes('(CGST)')) label = `Input CGST Ledger @ ${perc}%`;
                                      else if (label.includes('(SGST)') || label.includes('UTGST')) label = `Input SGST Ledger @ ${perc}%`;
                                      else if (label.includes('(IGST)')) label = `Input IGST Ledger @ ${perc}%`;
                                      else if (label.includes('(Cess)')) label = `Input Cess Ledger @ ${perc}%`;
                                      else if (label.includes('State Cess')) label = `Input State Cess Ledger @ ${perc}%`;
                                      else label = `${label} @ ${perc}%`;
                                    } else if (label.includes('TDS') || label.includes('TCS')) {
                                      label = `${label} @ ${perc}%`;
                                    }
                                  }
                                }

                                if (leg.debit > 0) {
                                  drLegs.push({ label, amount: leg.debit, indent: 'pl-10' });
                                }
                                if (leg.credit > 0) {
                                  crLegs.push({ label, amount: leg.credit, indent: 'pl-16' });
                                }
                              });
                            } else {
                              // Fallback if full_legs isn't available for some reason
                              if (e.debit > 0) {
                                drLegs.push({ label: drillDownLedger, amount: e.debit, indent: 'pl-10' });
                                crLegs.push({ label: e.particulars || 'Ledger', amount: e.debit, indent: 'pl-16' });
                              } else if (e.credit > 0) {
                                drLegs.push({ label: e.particulars || 'Ledger', amount: e.credit, indent: 'pl-10' });
                                crLegs.push({ label: drillDownLedger, amount: e.credit, indent: 'pl-16' });
                              }
                            }

                            return (
                              <>
                                {drLegs.map((leg, i) => (
                                  <tr key={`dr-${i}`} className="bg-white border-b border-gray-50/50">
                                    <td className="border-r border-gray-50 py-1.5"></td>
                                    <td className={`py-1.5 border-r border-gray-50 ${leg.indent} pr-4`}>
                                      <div className="flex justify-between items-center text-xs font-medium text-gray-700">
                                        <span>{leg.label}</span>
                                        <div className="flex items-center gap-1 ml-4">
                                          <span className="font-bold text-gray-900">₹{leg.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                                          <span className="text-gray-400 text-[10px]">Dr</span>
                                        </div>
                                      </div>
                                    </td>
                                    <td colSpan={6}></td>
                                  </tr>
                                ))}
                                {crLegs.map((leg, i) => (
                                  <tr key={`cr-${i}`} className="bg-white border-b border-gray-50/50">
                                    <td className="border-r border-gray-50 py-1.5"></td>
                                    <td className={`py-1.5 border-r border-gray-50 ${leg.indent} pr-4`}>
                                      <div className="flex justify-between items-center text-xs font-medium text-indigo-600">
                                        <span>{leg.label}</span>
                                        <div className="flex items-center gap-1 ml-4">
                                          <span className="font-bold">₹{leg.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                                          <span className="text-gray-400 text-[10px]">Cr</span>
                                        </div>
                                      </div>
                                    </td>
                                    <td colSpan={6}></td>
                                  </tr>
                                ))}
                                {/* Spacer row between transactions */}
                                <tr className="bg-white"><td colSpan={8} className="py-1"></td></tr>
                              </>
                            );
                          })()}
                        </React.Fragment>
                      )
                    }) : (
                      <tr><td colSpan={8} className="px-6 py-12 text-center text-sm text-gray-400">No transactions found for <strong>{drillDownLedger}</strong>.</td></tr>
                    )}
                  </tbody>
                  {filteredDrillData.length > 0 && (
                    <tfoot className="bg-gray-50 border-t-2 border-gray-200 font-bold">
                      <tr>
                        <td colSpan={4} className="px-6 py-4 text-right text-sm text-gray-700">TOTALS:</td>
                        <td className="px-6 py-4"></td>
                        <td className="px-6 py-4 text-sm text-right text-indigo-600">₹{totalDr.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                        <td className="px-6 py-4 text-sm text-right text-green-700">-</td>
                        <td className={`px-6 py-4 text-sm font-mono text-right ${last?.balanceType === 'Dr' ? 'text-indigo-600' : 'text-green-700'}`}>{last ? `₹${last.balance.toLocaleString('en-IN', { minimumFractionDigits: 2 })} ${last.balanceType}` : ''}</td>
                      </tr>
                    </tfoot>
                  )}
                </table>
              </div>
            )}
          </div>
        )}

        {/* ── MONTH VIEW ── */}
        {ledgerViewMode === 'month' && (
          <div className="erp-card border border-slate-200 p-0">
            <div className="flex justify-between items-center px-6 py-3 border-b border-gray-200 bg-gray-50">
              <span className="text-sm font-semibold text-gray-700">Monthly Summary — {drillDownLedger}</span>
              <div className="relative">
                <button onClick={() => setIsMonthFilterOpen(!isMonthFilterOpen)}
                  className="px-4 py-2 bg-white border border-gray-300 rounded-[4px] text-sm font-medium text-gray-700 hover:bg-gray-50 flex items-center gap-2">
                  <span>{selectedMonths.length > 0 ? `${selectedMonths.length} Selected` : 'All Months'}</span>
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>
                </button>
                {isMonthFilterOpen && (
                  <div className="absolute right-0 mt-2 w-48 bg-white border border-gray-200 rounded-lg shadow-lg z-50 max-h-60 overflow-y-auto">
                    {['April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December', 'January', 'February', 'March'].map(m => (
                      <label key={m} className="flex items-center px-4 py-2 hover:bg-gray-50 cursor-pointer">
                        <input type="checkbox" checked={selectedMonths.includes(m)} onChange={() => setSelectedMonths(selectedMonths.includes(m) ? selectedMonths.filter(x => x !== m) : [...selectedMonths, m])} className="w-4 h-4 text-indigo-600 border-gray-300 rounded" />
                        <span className="ml-2 text-sm text-gray-700">{m}</span>
                      </label>
                    ))}
                  </div>
                )}
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-[#F8F9FA]">
                  <tr>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider w-1/4">Month</th>
                    <th className="px-6 py-4 text-right text-xs font-semibold text-gray-400 uppercase tracking-wider w-1/4">Debit</th>
                    <th className="px-6 py-4 text-right text-xs font-semibold text-gray-400 uppercase tracking-wider w-1/4">Credit</th>
                    <th className="px-6 py-4 text-right text-xs font-semibold text-gray-400 uppercase tracking-wider w-1/4">Closing Balance</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-100">
                  {ledgerMonthData.filter(e => selectedMonths.length === 0 || selectedMonths.includes(e.month)).map((e, i) => (
                    <tr key={i} onClick={() => { setLedgerFilters(f => ({ ...f, date: `-${monthNameToNumber[e.month]}-` })); setLedgerViewMode('ledger'); }}
                      className="hover:bg-indigo-50 transition-colors cursor-pointer group">
                      <td className="px-6 py-5 text-sm font-bold text-gray-700 group-hover:text-indigo-600">{e.month}</td>
                      <td className="px-6 py-5 text-sm text-right text-gray-600 font-medium">{e.debit !== '-' ? `₹${e.debit}` : '-'}</td>
                      <td className="px-6 py-5 text-sm text-right text-gray-600 font-medium">{e.credit !== '-' ? `₹${e.credit}` : '-'}</td>
                      <td className="px-6 py-5 text-sm text-right font-bold text-gray-900">
                        {e.closingBalance !== '-' ? <>₹{Math.abs(e.rawBalance).toLocaleString('en-IN', { minimumFractionDigits: 2 })}<span className="ml-1 text-gray-500 text-xs font-normal">{e.rawBalance > 0 ? 'Dr' : 'Cr'}</span></> : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot className="bg-[#F8F9FA]">
                  <tr>
                    <td className="px-6 py-4 text-sm font-bold text-gray-500 text-center tracking-wide">TOTAL</td>
                    <td className="px-6 py-4 text-sm text-right font-bold text-gray-900">₹{ledgerMonthData.reduce((s, e) => s + (e.debit !== '-' ? parseFloat(e.debit.replace(/,/g, '')) : 0), 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                    <td className="px-6 py-4 text-sm text-right font-bold text-gray-900">₹{ledgerMonthData.reduce((s, e) => s + (e.credit !== '-' ? parseFloat(e.credit.replace(/,/g, '')) : 0), 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                    <td></td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>
        )}

        {/* ── ALLOCATION VIEW ── */}
        {ledgerViewMode === 'allocation' && (
          <div className="erp-card border border-slate-200 overflow-hidden p-0">
            <div className="overflow-x-auto">
              <table className="erp-table min-w-full">
                <thead className="bg-[#F8F9FA] border-b border-slate-200">
                  <tr className="border-b border-slate-200">
                    <th rowSpan={2} className="px-6 py-4 text-left text-[11px] font-black text-slate-500 uppercase tracking-widest border-r border-slate-200">Date</th>
                    <th rowSpan={2} className="px-6 py-4 text-left text-[11px] font-black text-slate-500 uppercase tracking-widest border-r border-slate-200">Posted From</th>
                    <th rowSpan={2} className="px-6 py-4 text-left text-[11px] font-black text-slate-500 uppercase tracking-widest border-r border-slate-200">Reference No.</th>
                    <th rowSpan={2} className="px-6 py-4 text-right text-[11px] font-black text-slate-500 uppercase tracking-widest border-r border-slate-200">Amount</th>
                    <th colSpan={4} className="px-6 py-2 border-r border-slate-200 bg-indigo-50/30 text-center text-[11px] font-black text-indigo-600 uppercase tracking-widest">Voucher Applied</th>
                    <th rowSpan={2} className="px-6 py-4 text-center text-[11px] font-black text-slate-500 uppercase tracking-widest border-r border-slate-200">Status</th>
                    <th rowSpan={2} className="px-6 py-4 text-center text-[11px] font-black text-slate-500 uppercase tracking-widest">Actions</th>
                  </tr>
                  <tr>
                    <th className="px-6 py-3 text-left text-[10px] font-bold text-slate-400 uppercase tracking-widest border-r border-slate-200">Date</th>
                    <th className="px-6 py-3 text-left text-[10px] font-bold text-slate-400 uppercase tracking-widest border-r border-slate-200">Ref No.</th>
                    <th className="px-6 py-3 text-right text-[10px] font-bold text-slate-400 uppercase tracking-widest border-r border-slate-200">Applied</th>
                    <th className="px-6 py-3 text-right text-[10px] font-bold text-slate-400 uppercase tracking-widest border-r border-slate-200">Pending</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {allocationRows.map((row, idx) => (
                    <tr key={idx} className="hover:bg-slate-50 transition-colors">
                      {row.isFirstInSource && (
                        <>
                          <td rowSpan={row.rowSpan} className="px-6 py-4 text-sm font-medium text-slate-600 border-r border-slate-100 align-top">{row.date ? formatDate(row.date) : '-'}</td>
                          <td rowSpan={row.rowSpan} className="px-6 py-4 text-sm text-slate-600 border-r border-slate-100 align-top">
                            <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${row.postedFrom === 'Purchase' ? 'bg-blue-50 text-blue-600 border border-blue-100' : row.postedFrom === 'Sales' ? 'bg-emerald-50 text-emerald-600 border border-emerald-100' : 'bg-slate-50 text-slate-600 border border-slate-100'}`}>{normalizeVoucherType(row.postedFrom)}</span>
                          </td>
                          <td rowSpan={row.rowSpan} className="px-6 py-4 text-sm font-bold text-indigo-600 border-r border-slate-100 align-top">{row.refNo}</td>
                          <td rowSpan={row.rowSpan} className="px-6 py-4 text-sm text-right font-medium text-slate-900 border-r border-slate-100 align-top">{row.netAmount !== '-' ? `₹${Number(row.netAmount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}` : '-'}</td>
                        </>
                      )}
                      <td className="px-6 py-4 text-sm text-slate-600 border-r border-slate-100">{row.appliedDate !== '-' ? formatDate(row.appliedDate) : '-'}</td>
                      <td className="px-6 py-4 text-sm font-medium text-slate-700 border-r border-slate-100">{row.appliedRefNo}</td>
                      <td className="px-6 py-4 text-sm text-right font-bold text-emerald-600 border-r border-slate-100">{row.appliedAmount !== '-' ? `₹${Number(row.appliedAmount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}` : '-'}</td>
                      <td className="px-6 py-4 text-sm text-right font-bold text-slate-900 border-r border-slate-100">{row.pendingBalance !== '-' ? `₹${Number(row.pendingBalance).toLocaleString('en-IN', { minimumFractionDigits: 2 })}` : '-'}</td>
                      {row.isFirstInSource && (
                        <>
                          <td rowSpan={row.rowSpan} className="px-6 py-4 text-center align-top border-r border-slate-100">
                            <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${row.status === 'Paid' || row.status === 'Utilized' ? 'bg-emerald-50 text-emerald-600 border border-emerald-100' : row.status === 'Partially Paid' ? 'bg-indigo-50 text-indigo-600 border border-indigo-100' : row.status === 'Due' ? 'bg-rose-50 text-rose-600 border border-rose-100' : 'bg-indigo-50 text-indigo-600 border border-indigo-100'}`}>{row.status}</span>
                          </td>
                          <td rowSpan={row.rowSpan} className="px-6 py-4 text-center align-top">
                            {(row.status === 'Due' || row.status === 'Partially Paid') && (
                              <button
                                onClick={() => setAllocationModalRow(row)}
                                className="px-3 py-1.5 bg-indigo-600 text-white text-[10px] font-bold rounded shadow-sm hover:bg-indigo-700 transition-colors uppercase tracking-widest flex items-center gap-1 mx-auto"
                              >
                                Reference
                              </button>
                            )}
                          </td>
                        </>
                      )}
                    </tr>
                  ))}
                  {allocationRows.length === 0 && (
                    <tr><td colSpan={9} className="px-6 py-20 text-center text-slate-400 text-sm">No allocation data found for <strong>{drillDownLedger}</strong>.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {allocationModalRow && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={() => { setAllocationModalRow(null); setSelectedAllocationAdvances([]); }}>
            <div className="bg-white w-[800px] max-w-[92vw] rounded-lg shadow-2xl overflow-hidden border border-gray-200" onClick={e => e.stopPropagation()}>
              {/* Modal Header */}
              <div className="bg-indigo-600 px-6 py-4 flex justify-between items-center">
                <div className="flex items-center gap-2">
                  <svg className="w-5 h-5 text-indigo-100" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                  <h3 className="text-white font-bold text-lg">Advance Allocation Details</h3>
                </div>
                <button onClick={() => { setAllocationModalRow(null); setSelectedAllocationAdvances([]); }} className="text-white hover:text-gray-200 transition-colors">
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                </button>
              </div>

              <div className="p-6">
                {/* Info Cards */}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                  <div className="bg-gray-50 p-3 rounded border border-gray-100">
                    <label className="text-[10px] text-gray-400 font-bold uppercase tracking-wider block mb-1">Invoice Ref</label>
                    <div className="text-sm font-bold text-gray-900">{allocationModalRow.refNo}</div>
                  </div>
                  <div className="bg-gray-50 p-3 rounded border border-gray-100">
                    <label className="text-[10px] text-gray-400 font-bold uppercase tracking-wider block mb-1">Ledger</label>
                    <div className="text-sm font-bold text-gray-900 truncate">{drillDownLedger}</div>
                  </div>
                  <div className="bg-gray-50 p-3 rounded border border-gray-100">
                    <label className="text-[10px] text-gray-400 font-bold uppercase tracking-wider block mb-1">Inv Amount</label>
                    <div className="text-sm font-bold text-gray-900">₹{Number(allocationModalRow.netAmount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
                  </div>
                  <div className="bg-gray-50 p-3 rounded border border-gray-100">
                    <label className="text-[10px] text-gray-400 font-bold uppercase tracking-wider block mb-1">Pending</label>
                    <div className="text-sm font-bold text-red-600">₹{Number(allocationModalRow.pendingBalance).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
                  </div>
                </div>

                {/* Available Payment Vouchers */}
                {(() => {
                  const advances = filteredDrillData.filter(e => {
                    const isPmt = e.voucherType && ['Receipt', 'Payment', 'receipt', 'payment', 'Credit Note', 'credit note', 'Debit Note', 'debit note', 'credit', 'debit'].some(t => (e.voucherType || '').toLowerCase().includes(t.toLowerCase()));
                    if (!isPmt) return false;
                    const isAdv = e.is_advance || e.rawVoucher?.is_advance || (e.referenceNo === '-' || !e.referenceNo || e.referenceNo.trim() === '');
                    if (!isAdv) return false;

                    // If the voucher is already linked to a specific invoice, do not show it as available
                    if (e.referenceNo && !['ADVANCE', '', '-', 'N/A'].includes(e.referenceNo.toUpperCase().trim())) return false;
                    if (e.allocation_status === 'Utilized' || e.allocationStatus === 'Utilized') return false;
                    const total = parseFloat(e.rawVoucher?.total_amount || e.rawVoucher?.amount || e.rawVoucher?.total || 0) || (e.debit > 0 ? e.debit : e.credit);
                    const paid = parseFloat(e.rawVoucher?.paid_amount || e.rawVoucher?.used_amount || 0);
                    const pending = Math.max(0, total - paid);
                    return pending > 0;
                  });
                  return advances.length > 0 ? (
                    <div className="space-y-3">
                      <div className="flex items-center justify-between border-b border-gray-100 pb-2">
                        <h4 className="text-xs font-bold text-gray-500 uppercase tracking-widest">Available Advance Vouchers</h4>
                        <span className="text-[10px] bg-indigo-100 text-indigo-600 px-2 py-0.5 rounded-full font-bold">{advances.length} Found</span>
                      </div>
                      <div className="max-h-[320px] overflow-y-auto border border-gray-200 rounded">
                        <table className="w-full text-sm">
                          <thead className="bg-gray-50 border-b border-gray-200 sticky top-0">
                            <tr className="text-left text-xs text-gray-600 uppercase tracking-wider">
                              <th className="px-4 py-3 font-semibold">Select</th>
                              <th className="px-4 py-3 font-semibold">Voucher No.</th>
                              <th className="px-4 py-3 font-semibold">Date</th>
                              <th className="px-4 py-3 text-right font-semibold">Amount</th>
                              <th className="px-4 py-3 text-right font-semibold">Pending</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-gray-100 bg-white">
                            {advances.map((adv: any, idx: number) => {
                              const isSelected = selectedAllocationAdvances.some(a => a.voucherNo === adv.voucherNo);
                              const total = parseFloat(adv.rawVoucher?.total_amount || adv.rawVoucher?.amount || adv.rawVoucher?.total || 0) || (adv.debit > 0 ? adv.debit : adv.credit);
                              const paid = parseFloat(adv.rawVoucher?.paid_amount || adv.rawVoucher?.used_amount || 0);
                              const pending = Math.max(0, total - paid);
                              return (
                                <tr key={idx} className={`hover:bg-gray-50 transition-colors cursor-pointer ${isSelected ? 'bg-indigo-50/50' : ''}`} onClick={() => {
                                  if (isSelected) {
                                    setSelectedAllocationAdvances(prev => prev.filter(a => a.voucherNo !== adv.voucherNo));
                                  } else {
                                    setSelectedAllocationAdvances(prev => [...prev, adv]);
                                  }
                                }}>
                                  <td className="px-4 py-3">
                                    <input
                                      type="checkbox"
                                      checked={isSelected}
                                      onChange={() => { }} // Managed by row onClick
                                      className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500 cursor-pointer"
                                    />
                                  </td>
                                  <td className="px-4 py-3 font-medium text-gray-900">{adv.voucherNo || '-'}</td>
                                  <td className="px-4 py-3 text-gray-500">{adv.date ? formatDate(adv.date) : '-'}</td>
                                  <td className="px-4 py-3 text-right text-gray-900 font-bold">
                                    {adv.credit > 0 ? `₹${adv.credit.toLocaleString('en-IN', { minimumFractionDigits: 2 })}` : adv.debit > 0 ? `₹${adv.debit.toLocaleString('en-IN', { minimumFractionDigits: 2 })}` : '-'}
                                  </td>
                                  <td className="px-4 py-3 text-right font-bold text-rose-600">
                                    ₹{Number(pending || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-12 bg-gray-50 rounded-lg border border-dashed border-gray-200">
                      <svg className="w-10 h-10 text-gray-300 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
                      <p className="text-sm text-gray-500 font-medium">No linked payment vouchers found</p>
                    </div>
                  );
                })()}

                {/* Footer Buttons */}
                <div className="mt-6 flex gap-3">
                  <button
                    onClick={() => { setAllocationModalRow(null); setSelectedAllocationAdvances([]); }}
                    className="flex-1 py-3 bg-gray-100 text-gray-700 font-bold rounded hover:bg-gray-200 transition-colors uppercase tracking-widest text-[10px]"
                  >
                    Close Window
                  </button>
                  <button
                    disabled={selectedAllocationAdvances.length === 0 || isAllocating}
                    onClick={async () => {
                      if (selectedAllocationAdvances.length === 0) {
                        showError('Please select at least one payment voucher to proceed.');
                        return;
                      }
                      setIsAllocating(true);
                      try {
                        await Promise.all(selectedAllocationAdvances.map(async (adv) => {
                          const entryId = adv.id || adv.rawVoucher?.id;
                          if (entryId) {
                            await httpClient.patch(`/api/journal-entries/${entryId}/`, {
                              reference_number: allocationModalRow.refNo,
                              allocation_status: 'Utilized'
                            });
                          }
                        }));

                        // Refresh drill-down data to reflect changes
                        if (drillDownLedger) {
                          const ledgerName = drillDownLedger.includes(':') ? drillDownLedger.split(':')[1] : drillDownLedger;
                          apiService.getJournalEntriesReport(ledgerName, ledgerFilters.dateFrom || undefined, ledgerFilters.dateTo || undefined)
                            .then(data => setDrillDownData(Array.isArray(data) ? data : []))
                            .catch(() => { });
                        }
                        showSuccess(`Successfully allocated ${selectedAllocationAdvances.length} voucher(s) to ${allocationModalRow.refNo}`);
                        setAllocationModalRow(null);
                        setSelectedAllocationAdvances([]);
                      } catch (err: any) {
                        showError(err?.message || 'Failed to proceed with allocation.');
                      } finally {
                        setIsAllocating(false);
                      }
                    }}
                    className={`flex-1 py-3 font-bold rounded transition-colors uppercase tracking-widest text-[10px] shadow-lg ${selectedAllocationAdvances.length > 0 && !isAllocating
                      ? 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-indigo-200'
                      : 'bg-gray-200 text-gray-400 cursor-not-allowed shadow-none'
                      }`}
                  >
                    {isAllocating ? 'Processing...' : 'Proceed Allocation'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── Transaction Detail Slide-Out Panel (Zoho Books style) ── */}
        {selectedTransaction && (
          <>
            {/* Backdrop */}
            <div
              className="fixed inset-0 z-40 bg-black/20 backdrop-blur-[1px]"
              onClick={() => setSelectedTransaction(null)}
              style={{ animation: 'fadeIn 0.15s ease' }}
            />
            {/* Slide panel */}
            <div
              className="fixed top-0 right-0 h-full w-full max-w-5xl z-50 bg-white shadow-2xl flex flex-col animate-slide-in"
              style={{ animation: 'slideInRight 0.22s cubic-bezier(0.4,0,0.2,1)' }}
            >
              {/* Panel header */}
              <div className="flex items-center justify-between px-6 py-4 bg-gradient-to-r from-indigo-600 to-indigo-700 text-white flex-shrink-0">
                <div>
                  <div className="text-xs font-bold uppercase tracking-widest text-indigo-200 mb-0.5">Transaction Details</div>
                  <div className="text-lg font-bold">{selectedTransaction.voucherNo || 'N/A'}</div>
                </div>
                <div className="flex items-center gap-3">
                  {voucherDetails?.gst_registered !== 'Yes' && (
                    <button
                      onClick={() => {
                        if (isEditingVoucher) {
                          setIsEditingVoucher(false);
                          setEditedVoucher(JSON.parse(JSON.stringify(voucherDetails)));
                        } else {
                          setIsEditingVoucher(true);
                        }
                      }}
                      className="px-4 py-1.5 rounded-lg text-xs font-bold bg-white text-indigo-700 hover:bg-indigo-50 transition-colors uppercase tracking-wider"
                    >
                      {isEditingVoucher ? 'Cancel Edit' : 'Edit Voucher'}
                    </button>
                  )}
                  <button
                    onClick={() => { setSelectedTransaction(null); setIsEditingVoucher(false); }}
                    className="w-8 h-8 flex items-center justify-center rounded-full bg-white/10 hover:bg-white/20 transition-colors"
                    aria-label="Close panel"
                  >
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              </div>

              {/* Panel tabs */}
              <div className="flex border-b border-gray-200 bg-gray-50 flex-shrink-0 overflow-x-auto">
                {(['payment', 'receipt', 'contra', 'expense'].includes(selectedTransaction?.voucherType?.toLowerCase() || '')
                  ? [
                    { id: 'voucher', label: (selectedTransaction?.voucherType || 'VOUCHER').toUpperCase() + ' DETAILS' },
                    { id: 'allocations', label: 'ALLOCATED INVOICES' }
                  ]
                  : [
                    { id: 'invoice', label: selectedTransaction?.voucherType?.toLowerCase() === 'purchase' ? 'SUPPLIER DETAILS' : 'INVOICE DETAILS' },
                    { id: 'item', label: selectedTransaction?.voucherType?.toLowerCase() === 'purchase' ? 'SUPPLY DETAILS' : 'ITEM & TAX DETAILS' },
                    { id: 'payment', label: selectedTransaction?.voucherType?.toLowerCase() === 'purchase' ? 'DUE DETAILS' : 'PAYMENT DETAILS' },
                    { id: 'dispatch', label: selectedTransaction?.voucherType?.toLowerCase() === 'purchase' ? 'TRANSIT DETAILS' : 'DISPATCH DETAILS' },
                    ...(selectedTransaction?.voucherType?.toLowerCase() !== 'purchase' ? [{ id: 'einvoice', label: 'E-INVOICE & E-WAY BILL DETAILS' }] : [])
                  ]
                ).map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setPanelActiveTab(tab.id)}
                    className={`px-5 py-3 text-xs font-bold transition-colors border-b-2 whitespace-nowrap ${panelActiveTab === tab.id
                      ? 'border-indigo-600 text-indigo-600 bg-white border-b-indigo-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                      }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              {/* Scrollable Content Area */}
              <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
                {!isLoadingDetails && (
                  <>
                    {['payment', 'receipt', 'contra', 'expense'].includes(selectedTransaction?.voucherType?.toLowerCase() || '') ? (
                      <>
                        {panelActiveTab === 'voucher' && (
                          <div className="grid grid-cols-2 gap-6" style={{ animation: 'fadeIn 0.15s ease' }}>
                            <div>
                              <label className="label-text">DATE *</label>
                              <DateInput

                                value={editedVoucher?.date || ''}
                                disabled={!isEditingVoucher}
                                onChange={(e) => handleFieldChange('date', e.target.value)}
                                className="erp-input"
                              />
                            </div>
                            <div>
                              <label className="label-text">VOUCHER TYPE</label>
                              <input
                                type="text"
                                value={editedVoucher?.voucher_type || selectedTransaction?.voucherType || ''}
                                disabled={true}
                                className="erp-input bg-gray-50 text-gray-500 cursor-not-allowed font-bold"
                              />
                            </div>
                            <div>
                              <label className="label-text">VOUCHER NUMBER *</label>
                              <input
                                type="text"
                                value={editedVoucher?.voucher_number || editedVoucher?.voucher_no || ''}
                                disabled={!isEditingVoucher}
                                onChange={(e) => {
                                  handleFieldChange('voucher_number', e.target.value);
                                  handleFieldChange('voucher_no', e.target.value);
                                }}
                                className="erp-input"
                              />
                            </div>
                            <div>
                              <label className="label-text">
                                {(() => {
                                  const vt = selectedTransaction?.voucherType?.toLowerCase() || '';
                                  if (vt === 'contra') return 'TRANSFER FROM *';
                                  if (vt === 'expense' || vt === 'expenses') return 'PAID FROM (BANK/CASH) *';
                                  if (vt === 'receipt') return 'RECEIVE IN (BANK/CASH) *';
                                  return 'PAY FROM (BANK/CASH) *';
                                })()}
                              </label>
                              <input
                                type="text"
                                value={editedVoucher?.account || editedVoucher?.fromAccount || editedVoucher?.from_account || ''}
                                disabled={!isEditingVoucher}
                                onChange={(e) => {
                                  handleFieldChange('account', e.target.value);
                                  handleFieldChange('fromAccount', e.target.value);
                                  handleFieldChange('from_account', e.target.value);
                                }}
                                className="erp-input"
                              />
                            </div>
                            <div>
                              <label className="label-text">
                                {(() => {
                                  const vt = selectedTransaction?.voucherType?.toLowerCase() || '';
                                  if (vt === 'contra') return 'TRANSFER TO *';
                                  if (vt === 'expense' || vt === 'expenses') return 'EXPENSE LEDGER *';
                                  if (vt === 'receipt') return 'RECEIVED FROM (CUSTOMER/PARTY) *';
                                  return 'PAY TO (VENDOR/PARTY) *';
                                })()}
                              </label>
                              <input
                                type="text"
                                value={editedVoucher?.party || editedVoucher?.toAccount || editedVoucher?.to_account || ''}
                                disabled={!isEditingVoucher}
                                onChange={(e) => {
                                  handleFieldChange('party', e.target.value);
                                  handleFieldChange('toAccount', e.target.value);
                                  handleFieldChange('to_account', e.target.value);
                                }}
                                className="erp-input"
                              />
                            </div>
                            <div>
                              <label className="label-text">AMOUNT (₹) *</label>
                              <input
                                type="number"
                                value={editedVoucher?.amount || editedVoucher?.total || 0}
                                disabled={!isEditingVoucher}
                                onChange={(e) => {
                                  handleFieldChange('amount', parseFloat(e.target.value) || 0);
                                  handleFieldChange('total', parseFloat(e.target.value) || 0);
                                }}
                                className="erp-input font-bold text-indigo-700"
                              />
                            </div>
                            {/* Contra-specific extra fields */}
                            {selectedTransaction?.voucherType?.toLowerCase() === 'contra' && (
                              <div>
                                <label className="label-text">DEDUCT CHARGES FROM</label>
                                <input
                                  type="text"
                                  value={editedVoucher?.deduct_charges_from || ''}
                                  disabled={!isEditingVoucher}
                                  onChange={(e) => handleFieldChange('deduct_charges_from', e.target.value)}
                                  className="erp-input"
                                />
                              </div>
                            )}
                            {selectedTransaction?.voucherType?.toLowerCase() === 'contra' && (
                              <div>
                                <label className="label-text">CONVERSION CHARGES</label>
                                <input
                                  type="number"
                                  value={editedVoucher?.conversion_charges || 0}
                                  disabled={!isEditingVoucher}
                                  onChange={(e) => handleFieldChange('conversion_charges', parseFloat(e.target.value) || 0)}
                                  className="erp-input font-mono"
                                />
                              </div>
                            )}
                            {selectedTransaction?.voucherType?.toLowerCase() === 'contra' && (
                              <div>
                                <label className="label-text">FEMA PURPOSE CODE</label>
                                <input
                                  type="text"
                                  value={editedVoucher?.fema_purpose_code || ''}
                                  disabled={!isEditingVoucher}
                                  onChange={(e) => handleFieldChange('fema_purpose_code', e.target.value)}
                                  className="erp-input"
                                />
                              </div>
                            )}
                            <div>
                              <label className="label-text">REFERENCE NUMBER</label>
                              <input
                                type="text"
                                value={editedVoucher?.reference_number || editedVoucher?.ref_no || editedVoucher?.refNo || ''}
                                disabled={!isEditingVoucher}
                                onChange={(e) => {
                                  handleFieldChange('reference_number', e.target.value);
                                  handleFieldChange('ref_no', e.target.value);
                                  handleFieldChange('refNo', e.target.value);
                                }}
                                className="erp-input"
                              />
                            </div>
                            <div className="col-span-2">
                              <label className="label-text">
                                {selectedTransaction?.voucherType?.toLowerCase() === 'contra' ? 'POSTING NOTE' : 'NARRATION / NOTES'}
                              </label>
                              <textarea
                                value={editedVoucher?.narration || editedVoucher?.postingNote || editedVoucher?.posting_note || ''}
                                disabled={!isEditingVoucher}
                                onChange={(e) => {
                                  handleFieldChange('narration', e.target.value);
                                  handleFieldChange('postingNote', e.target.value);
                                  handleFieldChange('posting_note', e.target.value);
                                }}
                                className="erp-input h-24 resize-none py-2"
                              />
                            </div>
                          </div>
                        )}

                        {panelActiveTab === 'allocations' && (
                          <div className="space-y-6" style={{ animation: 'fadeIn 0.15s ease' }}>
                            <div className="overflow-x-auto border border-gray-200 rounded-xl shadow-sm">
                              <table className="min-w-full divide-y divide-gray-200 text-xs">
                                <thead className="bg-gray-50 font-bold text-gray-700 uppercase tracking-wider">
                                  <tr>
                                    <th className="px-4 py-3 text-left">Invoice No / Ref No</th>
                                    <th className="px-4 py-3 text-left">Invoice Date</th>
                                    <th className="px-4 py-3 text-right">Invoice Amount (₹)</th>
                                    <th className="px-4 py-3 text-right">Paid Now (₹)</th>
                                  </tr>
                                </thead>
                                <tbody className="bg-white divide-y divide-gray-200">
                                  {(editedVoucher?.allocations && editedVoucher.allocations.length > 0) ? (
                                    editedVoucher.allocations.map((alloc: any, idx: number) => (
                                      <tr key={idx} className="hover:bg-slate-50 transition-colors">
                                        <td className="px-4 py-3">
                                          <input
                                            type="text"
                                            value={alloc.invoice_no || alloc.reference_number || alloc.refNo || alloc.invoiceNo || ''}
                                            disabled={!isEditingVoucher}
                                            onChange={(e) => {
                                              const copy = [...editedVoucher.allocations];
                                              copy[idx] = { ...alloc, invoice_no: e.target.value, reference_number: e.target.value, refNo: e.target.value };
                                              handleFieldChange('allocations', copy);
                                            }}
                                            className="erp-input py-1 text-xs"
                                          />
                                        </td>
                                        <td className="px-4 py-3">
                                          <DateInput

                                            value={alloc.date || alloc.invoice_date || ''}
                                            disabled={!isEditingVoucher}
                                            onChange={(e) => {
                                              const copy = [...editedVoucher.allocations];
                                              copy[idx] = { ...alloc, date: e.target.value, invoice_date: e.target.value };
                                              handleFieldChange('allocations', copy);
                                            }}
                                            className="erp-input py-1 text-xs"
                                          />
                                        </td>
                                        <td className="px-4 py-3 text-right font-medium">
                                          ₹{Number(alloc.amount || alloc.invoice_amount || 0).toFixed(2)}
                                        </td>
                                        <td className="px-4 py-3 text-right font-bold text-indigo-600">
                                          ₹{Number(alloc.payNow || alloc.allocated_amount || alloc.payment || 0).toFixed(2)}
                                        </td>
                                      </tr>
                                    ))
                                  ) : (
                                    <tr>
                                      <td colSpan={4} className="px-4 py-8 text-center text-gray-400 font-medium">
                                        Direct ledger posting. No invoice-level allocations recorded.
                                      </td>
                                    </tr>
                                  )}
                                </tbody>
                              </table>
                            </div>
                          </div>
                        )}
                      </>
                    ) : (
                      <>
                        {panelActiveTab === 'invoice' && (
                          <div className="grid grid-cols-2 gap-6" style={{ animation: 'fadeIn 0.15s ease' }}>
                            <div>
                              <label className="label-text">DATE *</label>
                              <DateInput

                                value={editedVoucher?.date || ''}
                                disabled={!isEditingVoucher}
                                onChange={(e) => handleFieldChange('date', e.target.value)}
                                className="erp-input"
                              />
                            </div>
                            <div>
                              <label className="label-text">
                                {selectedTransaction?.voucherType?.toLowerCase() === 'purchase' ? 'PURCHASE INVOICE SERIES' : 'SALES INVOICE SERIES'}
                              </label>
                              <select
                                value={editedVoucher?.purchase_voucher_series || editedVoucher?.voucher_series || editedVoucher?.voucher_name || ''}
                                disabled={!isEditingVoucher}
                                onChange={(e) => {
                                  handleFieldChange('purchase_voucher_series', e.target.value);
                                  handleFieldChange('voucher_series', e.target.value);
                                  handleFieldChange('voucher_name', e.target.value);
                                }}
                                className="erp-select"
                              >
                                <option value="">SELECT SERIES</option>
                                <option value="Standard">Standard Series</option>
                                {(() => {
                                  const v = editedVoucher?.purchase_voucher_series || editedVoucher?.voucher_series || editedVoucher?.voucher_name;
                                  return v && !['Standard', ''].includes(v) ? (
                                    <option value={v}>{v}</option>
                                  ) : null;
                                })()}
                              </select>
                            </div>
                            <div>
                              <label className="label-text">
                                {selectedTransaction?.voucherType?.toLowerCase() === 'purchase' ? 'PURCHASE INVOICE NO. *' : 'SALES INVOICE NO. *'}
                              </label>
                              <input
                                type="text"
                                value={editedVoucher?.voucher_number || ''}
                                disabled={!isEditingVoucher}
                                onChange={(e) => handleFieldChange('voucher_number', e.target.value)}
                                className="erp-input"
                              />
                            </div>
                            <div>
                              <label className="label-text">
                                {selectedTransaction?.voucherType?.toLowerCase() === 'purchase' ? 'VENDOR NAME *' : 'CUSTOMER NAME *'}
                              </label>
                              <input
                                type="text"
                                value={editedVoucher?.party || ''}
                                disabled={!isEditingVoucher}
                                onChange={(e) => handleFieldChange('party', e.target.value)}
                                className="erp-input"
                              />
                            </div>
                            <div>
                              <label className="label-text">BRANCH</label>
                              <input
                                type="text"
                                value={editedVoucher?.branch || editedVoucher?.customer_branch || ''}
                                disabled={!isEditingVoucher}
                                onChange={(e) => handleFieldChange('branch', e.target.value)}
                                className="erp-input"
                              />
                            </div>
                            <div>
                              <label className="label-text">GSTIN</label>
                              <input
                                type="text"
                                value={editedVoucher?.gstin || ''}
                                disabled={!isEditingVoucher}
                                onChange={(e) => handleFieldChange('gstin', e.target.value)}
                                className="erp-input"
                              />
                            </div>
                            {selectedTransaction?.voucherType?.toLowerCase() === 'purchase' && (
                              <div>
                                <label className="label-text">SUPPLIER INVOICE DATE</label>
                                <DateInput

                                  value={editedVoucher?.supplier_invoice_date || editedVoucher?.date || ''}
                                  disabled={!isEditingVoucher}
                                  onChange={(e) => handleFieldChange('supplier_invoice_date', e.target.value)}
                                  className="erp-input"
                                />
                              </div>
                            )}
                            {selectedTransaction?.voucherType?.toLowerCase() === 'purchase' && (
                              <div>
                                <label className="label-text">SUPPLIER INVOICE NO.</label>
                                <input
                                  type="text"
                                  value={editedVoucher?.supplier_invoice_no || editedVoucher?.invoice_no || editedVoucher?.invoiceNo || ''}
                                  disabled={!isEditingVoucher}
                                  onChange={(e) => handleFieldChange('supplier_invoice_no', e.target.value)}
                                  className="erp-input"
                                />
                              </div>
                            )}
                            {selectedTransaction?.voucherType?.toLowerCase() === 'purchase' && (
                              <div>
                                <label className="label-text">GRN REFERENCE NO.</label>
                                <input
                                  type="text"
                                  value={editedVoucher?.grn_reference || ''}
                                  disabled={!isEditingVoucher}
                                  onChange={(e) => handleFieldChange('grn_reference', e.target.value)}
                                  className="erp-input"
                                />
                              </div>
                            )}
                            <div className="col-span-2 grid grid-cols-2 gap-6 mt-2">
                              <div>
                                <label className="label-text font-bold text-indigo-700">Bill To (Full Address)</label>
                                <input
                                  type="text"
                                  placeholder="Address Line 1"
                                  value={editedVoucher?.bill_to_address_1 || ''}
                                  disabled={!isEditingVoucher}
                                  onChange={(e) => handleFieldChange('bill_to_address_1', e.target.value)}
                                  className="erp-input mb-2"
                                />
                                <input
                                  type="text"
                                  placeholder="Address Line 2"
                                  value={editedVoucher?.bill_to_address_2 || ''}
                                  disabled={!isEditingVoucher}
                                  onChange={(e) => handleFieldChange('bill_to_address_2', e.target.value)}
                                  className="erp-input"
                                />
                              </div>
                              <div>
                                <label className="label-text font-bold text-indigo-700">Ship To (Full Address)</label>
                                <input
                                  type="text"
                                  placeholder="Address Line 1"
                                  value={editedVoucher?.ship_to_address_1 || ''}
                                  disabled={!isEditingVoucher}
                                  onChange={(e) => handleFieldChange('ship_to_address_1', e.target.value)}
                                  className="erp-input mb-2"
                                />
                                <input
                                  type="text"
                                  placeholder="Address Line 2"
                                  value={editedVoucher?.ship_to_address_2 || ''}
                                  disabled={!isEditingVoucher}
                                  onChange={(e) => handleFieldChange('ship_to_address_2', e.target.value)}
                                  className="erp-input"
                                />
                              </div>
                            </div>
                          </div>
                        )}

                        {panelActiveTab === 'item' && (
                          <div className="space-y-6" style={{ animation: 'fadeIn 0.15s ease' }}>
                            <div className="overflow-x-auto border border-gray-200 rounded-xl shadow-sm">
                              <table className="min-w-full divide-y divide-gray-200 text-xs">
                                <thead className="bg-gray-50 font-bold text-gray-700 uppercase tracking-wider">
                                  <tr>
                                    <th className="px-3 py-2.5 text-left">Item Code</th>
                                    <th className="px-3 py-2.5 text-left">Item Name</th>
                                    <th className="px-3 py-2.5 text-left">HSN/SAC</th>
                                    <th className="px-3 py-2.5 text-right">Qty</th>
                                    <th className="px-3 py-2.5 text-left">UOM</th>
                                    <th className="px-3 py-2.5 text-right">Rate</th>
                                    <th className="px-3 py-2.5 text-right">Taxable</th>
                                    <th className="px-3 py-2.5 text-right">IGST</th>
                                    <th className="px-3 py-2.5 text-right">CGST</th>
                                    <th className="px-3 py-2.5 text-right">SGST</th>
                                    <th className="px-3 py-2.5 text-right">Invoice Value</th>
                                  </tr>
                                </thead>
                                <tbody className="bg-white divide-y divide-gray-200">
                                  {(editedVoucher?.items && editedVoucher.items.length > 0) ? editedVoucher.items.map((item: any, idx: number) => (
                                    <tr key={idx} className="hover:bg-slate-50/50 transition-colors">
                                      <td className="px-3 py-2">
                                        <input
                                          type="text"
                                          value={item.item_code || item.itemCode || ''}
                                          disabled={!isEditingVoucher}
                                          onChange={(e) => {
                                            const itemsCopy = [...editedVoucher.items];
                                            itemsCopy[idx] = { ...item, item_code: e.target.value, itemCode: e.target.value };
                                            handleFieldChange('items', itemsCopy);
                                          }}
                                          className="erp-input py-1 text-xs"
                                        />
                                      </td>
                                      <td className="px-3 py-2">
                                        <input
                                          type="text"
                                          value={item.item_name || item.itemName || ''}
                                          disabled={!isEditingVoucher}
                                          onChange={(e) => {
                                            const itemsCopy = [...editedVoucher.items];
                                            itemsCopy[idx] = { ...item, item_name: e.target.value, itemName: e.target.value };
                                            handleFieldChange('items', itemsCopy);
                                          }}
                                          className="erp-input py-1 text-xs"
                                        />
                                      </td>
                                      <td className="px-3 py-2">
                                        <input
                                          type="text"
                                          value={item.hsn_code || item.hsnSac || ''}
                                          disabled={!isEditingVoucher}
                                          onChange={(e) => {
                                            const itemsCopy = [...editedVoucher.items];
                                            itemsCopy[idx] = { ...item, hsn_code: e.target.value, hsnSac: e.target.value };
                                            handleFieldChange('items', itemsCopy);
                                          }}
                                          className="erp-input py-1 text-xs"
                                        />
                                      </td>
                                      <td className="px-3 py-2">
                                        <input
                                          type="number"
                                          value={item.quantity || item.qty || 0}
                                          disabled={!isEditingVoucher}
                                          onChange={(e) => {
                                            const itemsCopy = [...editedVoucher.items];
                                            const qty = parseFloat(e.target.value) || 0;
                                            const rate = parseFloat(item.itemRate || item.rate) || 0;
                                            const taxable = qty * rate;
                                            itemsCopy[idx] = { ...item, quantity: qty, qty, itemRate: rate, rate, taxableValue: taxable };
                                            handleFieldChange('items', itemsCopy);
                                          }}
                                          className="erp-input py-1 text-xs text-right"
                                        />
                                      </td>
                                      <td className="px-3 py-2">
                                        <input
                                          type="text"
                                          value={item.uom || ''}
                                          disabled={!isEditingVoucher}
                                          onChange={(e) => {
                                            const itemsCopy = [...editedVoucher.items];
                                            itemsCopy[idx] = { ...item, uom: e.target.value };
                                            handleFieldChange('items', itemsCopy);
                                          }}
                                          className="erp-input py-1 text-xs"
                                        />
                                      </td>
                                      <td className="px-3 py-2">
                                        <input
                                          type="number"
                                          value={item.itemRate || item.rate || 0}
                                          disabled={!isEditingVoucher}
                                          onChange={(e) => {
                                            const itemsCopy = [...editedVoucher.items];
                                            const rate = parseFloat(e.target.value) || 0;
                                            const qty = parseFloat(item.quantity || item.qty) || 0;
                                            const taxable = qty * rate;
                                            itemsCopy[idx] = { ...item, itemRate: rate, rate, taxableValue: taxable };
                                            handleFieldChange('items', itemsCopy);
                                          }}
                                          className="erp-input py-1 text-xs text-right"
                                        />
                                      </td>
                                      <td className="px-3 py-2 text-right font-mono font-medium">
                                        ₹{(parseFloat(item.taxableValue || item.taxable_value) || ((parseFloat(item.quantity || item.qty) || 0) * (parseFloat(item.itemRate || item.rate) || 0))).toFixed(2)}
                                      </td>
                                      <td className="px-3 py-2">
                                        <input
                                          type="number"
                                          value={item.igst_amount ?? item.igst ?? 0}
                                          disabled={!isEditingVoucher}
                                          onChange={(e) => {
                                            const itemsCopy = [...editedVoucher.items];
                                            itemsCopy[idx] = { ...item, igst_amount: parseFloat(e.target.value) || 0, igst: parseFloat(e.target.value) || 0 };
                                            handleFieldChange('items', itemsCopy);
                                          }}
                                          className="erp-input py-1 text-xs text-right"
                                        />
                                      </td>
                                      <td className="px-3 py-2">
                                        <input
                                          type="number"
                                          value={item.cgst_amount ?? item.cgst ?? 0}
                                          disabled={!isEditingVoucher}
                                          onChange={(e) => {
                                            const itemsCopy = [...editedVoucher.items];
                                            itemsCopy[idx] = { ...item, cgst_amount: parseFloat(e.target.value) || 0, cgst: parseFloat(e.target.value) || 0 };
                                            handleFieldChange('items', itemsCopy);
                                          }}
                                          className="erp-input py-1 text-xs text-right"
                                        />
                                      </td>
                                      <td className="px-3 py-2">
                                        <input
                                          type="number"
                                          value={item.sgst_amount ?? item.sgst ?? 0}
                                          disabled={!isEditingVoucher}
                                          onChange={(e) => {
                                            const itemsCopy = [...editedVoucher.items];
                                            itemsCopy[idx] = { ...item, sgst_amount: parseFloat(e.target.value) || 0, sgst: parseFloat(e.target.value) || 0 };
                                            handleFieldChange('items', itemsCopy);
                                          }}
                                          className="erp-input py-1 text-xs text-right"
                                        />
                                      </td>
                                      <td className="px-3 py-2 text-right font-bold text-indigo-700">
                                        ₹{(parseFloat(item.invoiceValue || item.invoice_value) || ((parseFloat(item.taxableValue || item.taxable_value) || 0) + (parseFloat(item.igst_amount ?? item.igst ?? 0) as number) + (parseFloat(item.cgst_amount ?? item.cgst ?? 0) as number) + (parseFloat(item.sgst_amount ?? item.sgst ?? 0) as number))).toFixed(2)}
                                      </td>
                                    </tr>
                                  )) : (
                                    <tr>
                                      <td colSpan={11} className="px-4 py-8 text-center text-gray-400">
                                        No items found. Defaulting to standard voucher ledger row.
                                      </td>
                                    </tr>
                                  )}
                                </tbody>
                              </table>
                            </div>
                            <div className="grid grid-cols-2 gap-6 mt-4">

                              <div>

                                <label className="label-text">

                                  {selectedTransaction?.voucherType?.toLowerCase() === 'purchase' ? 'PURCHASE LEDGER' : 'SALES LEDGER'}

                                </label>

                                <input

                                  type="text"

                                  value={

                                    selectedTransaction?.voucherType?.toLowerCase() === 'purchase'

                                      ? (editedVoucher?.purchase_ledger || editedVoucher?.supply_inr_details?.purchase_ledger || editedVoucher?.supply_foreign_details?.purchase_ledger || '')

                                      : (editedVoucher?.sales_ledger || editedVoucher?.supply_inr_details?.sales_ledger || '')

                                  }

                                  disabled={!isEditingVoucher}

                                  onChange={(e) => {

                                    if (selectedTransaction?.voucherType?.toLowerCase() === 'purchase') {

                                      handleFieldChange('purchase_ledger', e.target.value);

                                      handleFieldChange('supply_inr_details.purchase_ledger', e.target.value);

                                    } else {

                                      handleFieldChange('sales_ledger', e.target.value);

                                    }

                                  }}

                                  className="erp-input"

                                />

                              </div>

                              <div>

                                <label className="label-text">PURCHASE ORDER NO.</label>

                                <input

                                  type="text"

                                  value={

                                    editedVoucher?.supply_inr_details?.purchase_order_no

                                    || editedVoucher?.supply_foreign_details?.purchase_order_no

                                    || editedVoucher?.purchase_order_no

                                    || ''

                                  }

                                  disabled={!isEditingVoucher}

                                  onChange={(e) => {

                                    handleFieldChange('purchase_order_no', e.target.value);

                                    handleFieldChange('supply_inr_details.purchase_order_no', e.target.value);

                                  }}

                                  className="erp-input"

                                />

                              </div>

                              <div className="col-span-2">

                                <label className="label-text">LEDGER NARRATION</label>

                                <input

                                  type="text"

                                  value={editedVoucher?.ledger_narration || editedVoucher?.supply_inr_details?.description || ''}

                                  disabled={!isEditingVoucher}

                                  onChange={(e) => {

                                    handleFieldChange('ledger_narration', e.target.value);

                                    handleFieldChange('supply_inr_details.description', e.target.value);

                                  }}

                                  className="erp-input"

                                />

                              </div>

                            </div>

                          </div>

                        )}

                        {panelActiveTab === 'payment' && (() => {
                          const dd = editedVoucher?.due_details;
                          // TDS/TCS under Income Tax (reduces payable to vendor; paid to govt)
                          const tdsIt = parseFloat(dd?.tds_it ?? dd?.tdsIt ?? editedVoucher?.tds_it ?? 0);
                          const tdsGst = parseFloat(dd?.tds_gst ?? dd?.tdsGst ?? editedVoucher?.tds_gst ?? 0);
                          // Advance already paid against this invoice
                          const advance = parseFloat(dd?.advance_paid ?? dd?.advancePaid ?? editedVoucher?.advance_paid ?? 0);
                          const postingNote = dd?.posting_note ?? dd?.postingNote ?? editedVoucher?.narration ?? '';
                          // Invoice Value = total gross value of the purchase invoice (taxable + taxes)
                          const invoiceVal = parseFloat(
                            editedVoucher?.total
                            ?? editedVoucher?.total_amount
                            ?? 0
                          );
                          // Tax summary — computed from line items
                          const taxableAmt = parseFloat(editedVoucher?.total_taxable_amount ?? editedVoucher?.totalTaxableAmount ?? 0)
                            || (editedVoucher?.items || []).reduce((s: number, it: any) =>
                              s + parseFloat(it.taxableValue ?? it.taxable_value ?? 0), 0);
                          const totalIgst = parseFloat(editedVoucher?.total_igst ?? editedVoucher?.totalIgst ?? 0)
                            || (editedVoucher?.items || []).reduce((s: number, it: any) =>
                              s + parseFloat(it.igst ?? it.igst_amount ?? 0), 0);
                          const totalCgst = parseFloat(editedVoucher?.total_cgst ?? editedVoucher?.totalCgst ?? 0)
                            || (editedVoucher?.items || []).reduce((s: number, it: any) =>
                              s + parseFloat(it.cgst ?? it.cgst_amount ?? 0), 0);
                          const totalSgst = parseFloat(editedVoucher?.total_sgst ?? editedVoucher?.totalSgst ?? 0)
                            || (editedVoucher?.items || []).reduce((s: number, it: any) =>
                              s + parseFloat(it.sgst ?? it.sgst_amount ?? 0), 0);
                          const totalCess = (editedVoucher?.items || []).reduce((s: number, it: any) =>
                            s + parseFloat(it.cess ?? it.cess_amount ?? 0), 0);
                          // Accounting formulas (as per standard purchase voucher)
                          // Gross Amount Due = Invoice Value − TDS/TCS Under Income Tax
                          const grossDue = invoiceVal - tdsIt;
                          // Net Amount Due = Gross Amount Due − Advance Paid
                          // (This is what the vendor still needs to be paid)
                          const netAmountDue = grossDue - advance;

                          return (
                            <div className="space-y-6" style={{ animation: 'fadeIn 0.15s ease' }}>
                              {/* Tax Summary Table — mirrors the top summary in Due Details */}
                              <div className="overflow-x-auto border border-gray-200 rounded-xl shadow-sm">
                                <table className="min-w-full divide-y divide-gray-200 text-sm">
                                  <thead className="bg-gray-50">
                                    <tr>
                                      <th className="px-4 py-3 text-center font-semibold text-gray-700 uppercase tracking-wide text-xs">Taxable Value</th>
                                      <th className="px-4 py-3 text-center font-semibold text-gray-700 uppercase tracking-wide text-xs">IGST</th>
                                      <th className="px-4 py-3 text-center font-semibold text-gray-700 uppercase tracking-wide text-xs">CGST</th>
                                      <th className="px-4 py-3 text-center font-semibold text-gray-700 uppercase tracking-wide text-xs">SGST/UTGST</th>
                                      <th className="px-4 py-3 text-center font-semibold text-gray-700 uppercase tracking-wide text-xs">Cess</th>
                                    </tr>
                                  </thead>
                                  <tbody className="bg-white">
                                    <tr>
                                      <td className="px-4 py-3 text-center font-mono font-medium text-gray-800">{taxableAmt.toFixed(2)}</td>
                                      <td className="px-4 py-3 text-center font-mono font-medium text-gray-800">{totalIgst.toFixed(2)}</td>
                                      <td className="px-4 py-3 text-center font-mono font-medium text-gray-800">{totalCgst.toFixed(2)}</td>
                                      <td className="px-4 py-3 text-center font-mono font-medium text-gray-800">{totalSgst.toFixed(2)}</td>
                                      <td className="px-4 py-3 text-center font-mono font-medium text-gray-800">{totalCess.toFixed(2)}</td>
                                    </tr>
                                  </tbody>
                                </table>
                              </div>

                              {/* Due Details fields */}
                              <div className="grid grid-cols-2 gap-6">
                                <div>
                                  <label className="label-text">INVOICE VALUE</label>
                                  <input
                                    type="number"
                                    value={invoiceVal}
                                    disabled={!isEditingVoucher}
                                    onChange={(e) => handleFieldChange('total', parseFloat(e.target.value) || 0)}
                                    className="erp-input font-mono"
                                  />
                                </div>
                                <div>
                                  <label className="label-text">TDS/TCS UNDER INCOME TAX</label>
                                  <input
                                    type="number"
                                    value={tdsIt}
                                    disabled={!isEditingVoucher}
                                    onChange={(e) => handleFieldChange('due_details.tds_it', parseFloat(e.target.value) || 0)}
                                    className="erp-input font-mono"
                                  />
                                </div>
                                <div>
                                  <label className="label-text">ADVANCE PAID</label>
                                  <input
                                    type="number"
                                    value={advance}
                                    disabled={!isEditingVoucher}
                                    onChange={(e) => handleFieldChange('due_details.advance_paid', parseFloat(e.target.value) || 0)}
                                    className="erp-input font-mono"
                                  />
                                </div>
                                <div>
                                  <label className="label-text">TDS UNDER GST (RCM)</label>
                                  <input
                                    type="number"
                                    value={tdsGst}
                                    disabled={!isEditingVoucher}
                                    onChange={(e) => handleFieldChange('due_details.tds_gst', parseFloat(e.target.value) || 0)}
                                    className="erp-input font-mono"
                                  />
                                </div>
                                <div>
                                  <label className="label-text">GROSS AMOUNT DUE</label>
                                  <input
                                    type="number"
                                    value={grossDue.toFixed(2)}
                                    disabled={true}
                                    className="erp-input font-mono bg-gray-50 text-gray-600"
                                    title="Invoice Value − TDS/TCS Under Income Tax"
                                  />
                                </div>
                                <div>
                                  <label className="label-text">PAYMENT TERMS</label>
                                  <input
                                    type="text"
                                    value={dd?.terms || editedVoucher?.terms || ''}
                                    disabled={!isEditingVoucher}
                                    placeholder="e.g. Net 30 days"
                                    onChange={(e) => handleFieldChange('due_details.terms', e.target.value)}
                                    className="erp-input"
                                  />
                                </div>
                                <div className="col-span-2">
                                  <label className="label-text font-bold" style={{ color: '#6366F1' }}>NET AMOUNT DUE</label>
                                  <div className="flex items-center gap-2">
                                    <input
                                      type="number"
                                      value={netAmountDue.toFixed(2)}
                                      disabled={!isEditingVoucher}
                                      onChange={(e) => handleFieldChange('due_details.to_pay', parseFloat(e.target.value) || 0)}
                                      className="erp-input font-bold text-indigo-700 text-lg flex-1"
                                    />
                                    <span className="text-xs text-gray-400 whitespace-nowrap">
                                      (Invoice − TDS/IT − Advance)
                                    </span>
                                  </div>
                                </div>
                                <div className="col-span-2">
                                  <label className="label-text">POSTING NOTE</label>
                                  <textarea
                                    value={postingNote}
                                    disabled={!isEditingVoucher}
                                    placeholder="Enter posting notes..."
                                    onChange={(e) => {
                                      handleFieldChange('due_details.posting_note', e.target.value);
                                      handleFieldChange('narration', e.target.value);
                                    }}
                                    className="erp-input h-20 resize-none py-2"
                                  />
                                </div>
                              </div>
                            </div>
                          );
                        })()}

                        {panelActiveTab === 'dispatch' && (() => {
                          const td = editedVoucher?.transit_details || editedVoucher?.dispatch_details;
                          return (
                            <div className="grid grid-cols-2 gap-6" style={{ animation: 'fadeIn 0.15s ease' }}>
                              <div>
                                <label className="label-text">
                                  {selectedTransaction?.voucherType?.toLowerCase() === 'purchase' ? 'RECEIVED IN' : 'DISPATCH FROM'}
                                </label>
                                <input
                                  type="text"
                                  value={td?.received_in || td?.dispatch_from || ''}
                                  disabled={!isEditingVoucher}
                                  onChange={(e) => handleFieldChange('transit_details.received_in', e.target.value)}
                                  className="erp-input"
                                />
                              </div>
                              <div>
                                <label className="label-text">DELIVERY TYPE</label>
                                <input
                                  type="text"
                                  value={td?.delivery_type || ''}
                                  disabled={!isEditingVoucher}
                                  onChange={(e) => handleFieldChange('transit_details.delivery_type', e.target.value)}
                                  className="erp-input"
                                />
                              </div>
                              <div>
                                <label className="label-text">MODE OF TRANSPORT</label>
                                <input
                                  type="text"
                                  value={td?.mode || td?.mode_of_transport || 'Road'}
                                  disabled={!isEditingVoucher}
                                  onChange={(e) => handleFieldChange('transit_details.mode', e.target.value)}
                                  className="erp-input"
                                />
                              </div>
                              <div>
                                <label className="label-text">TRANSPORTER ID/GSTIN</label>
                                <input
                                  type="text"
                                  value={td?.transporter_id || ''}
                                  disabled={!isEditingVoucher}
                                  onChange={(e) => handleFieldChange('transit_details.transporter_id', e.target.value)}
                                  className="erp-input"
                                />
                              </div>
                              <div>
                                <label className="label-text">
                                  {selectedTransaction?.voucherType?.toLowerCase() === 'purchase' ? 'RECEIPT DATE' : 'DISPATCH DATE'}
                                </label>
                                <DateInput

                                  value={td?.receipt_date || td?.dispatch_date || ''}
                                  disabled={!isEditingVoucher}
                                  onChange={(e) => handleFieldChange('transit_details.receipt_date', e.target.value)}
                                  className="erp-input"
                                />
                              </div>
                              <div>
                                <label className="label-text">TRANSPORTER NAME</label>
                                <input
                                  type="text"
                                  value={td?.transporter_name || ''}
                                  disabled={!isEditingVoucher}
                                  onChange={(e) => handleFieldChange('transit_details.transporter_name', e.target.value)}
                                  className="erp-input"
                                />
                              </div>
                              <div>
                                <label className="label-text">
                                  {selectedTransaction?.voucherType?.toLowerCase() === 'purchase' ? 'RECEIPT TIME' : 'DISPATCH TIME'}
                                </label>
                                <input
                                  type="text"
                                  placeholder="HH:MM:SS"
                                  value={td?.receipt_time || td?.dispatch_time || ''}
                                  disabled={!isEditingVoucher}
                                  onChange={(e) => handleFieldChange('transit_details.receipt_time', e.target.value)}
                                  className="erp-input"
                                />
                              </div>
                              <div>
                                <label className="label-text">VEHICLE NO.</label>
                                <input
                                  type="text"
                                  value={td?.vehicle_no || ''}
                                  disabled={!isEditingVoucher}
                                  onChange={(e) => handleFieldChange('transit_details.vehicle_no', e.target.value)}
                                  className="erp-input"
                                />
                              </div>
                              <div className="col-span-2">
                                <label className="label-text">LR/GR/CONSIGNMENT NO</label>
                                <input
                                  type="text"
                                  value={td?.lr_gr_consignment || ''}
                                  disabled={!isEditingVoucher}
                                  onChange={(e) => handleFieldChange('transit_details.lr_gr_consignment', e.target.value)}
                                  className="erp-input"
                                />
                              </div>
                            </div>
                          );
                        })()}

                        {panelActiveTab === 'einvoice' && (
                          <div className="grid grid-cols-2 gap-6" style={{ animation: 'fadeIn 0.15s ease' }}>
                            <div>
                              <label className="label-text">E-INVOICE STATUS</label>
                              <input
                                type="text"
                                value={editedVoucher?.einvoice_details?.status || 'Not Generated'}
                                disabled={!isEditingVoucher}
                                onChange={(e) => handleFieldChange('einvoice_details.status', e.target.value)}
                                className="erp-input"
                              />
                            </div>
                            <div>
                              <label className="label-text">IRN</label>
                              <input
                                type="text"
                                value={editedVoucher?.einvoice_details?.irn || ''}
                                disabled={!isEditingVoucher}
                                onChange={(e) => handleFieldChange('einvoice_details.irn', e.target.value)}
                                className="erp-input font-mono text-xs"
                              />
                            </div>
                            <div>
                              <label className="label-text">ACK NO.</label>
                              <input
                                type="text"
                                value={editedVoucher?.einvoice_details?.ack_no || ''}
                                disabled={!isEditingVoucher}
                                onChange={(e) => handleFieldChange('einvoice_details.ack_no', e.target.value)}
                                className="erp-input"
                              />
                            </div>
                            <div>
                              <label className="label-text">ACK DATE</label>
                              <input
                                type="text"
                                value={editedVoucher?.einvoice_details?.ack_date || ''}
                                disabled={!isEditingVoucher}
                                onChange={(e) => handleFieldChange('einvoice_details.ack_date', e.target.value)}
                                className="erp-input"
                              />
                            </div>
                            <div>
                              <label className="label-text">E-WAY BILL NO.</label>
                              <input
                                type="text"
                                value={editedVoucher?.ewaybill_details?.number || ''}
                                disabled={!isEditingVoucher}
                                onChange={(e) => handleFieldChange('ewaybill_details.number', e.target.value)}
                                className="erp-input"
                              />
                            </div>
                            <div>
                              <label className="label-text">E-WAY BILL DATE</label>
                              <input
                                type="text"
                                value={editedVoucher?.ewaybill_details?.date || ''}
                                disabled={!isEditingVoucher}
                                onChange={(e) => handleFieldChange('ewaybill_details.date', e.target.value)}
                                className="erp-input"
                              />
                            </div>
                          </div>
                        )}
                      </>
                    )}
                  </>
                )}
              </div>

              {/* Panel Footer */}
              <div className="flex-shrink-0 px-6 py-4 border-t border-gray-200 bg-gray-50 flex gap-4 justify-end">
                {isEditingVoucher && (
                  <button
                    onClick={async () => {
                      const vId = selectedTransaction?.voucher_id || selectedTransaction?.rawVoucher?.voucher_id || selectedTransaction?.voucherId || selectedTransaction?.rawVoucher?.voucherId;
                      if (vId && editedVoucher) {
                        try {
                          setIsLoadingDetails(true);
                          const updated = await apiService.updateVoucher(vId, editedVoucher);
                          setVoucherDetails(updated);
                          setIsEditingVoucher(false);
                          showSuccess('Voucher updated successfully!');
                          // Refresh reports drilldown
                          if (drillDownLedger) {
                            const name = drillDownLedger.includes(':') ? drillDownLedger.split(':')[1] : drillDownLedger;
                            apiService.getJournalEntriesReport(name, undefined, undefined)
                              .then(res => setDrillDownData(Array.isArray(res) ? res : []))
                              .catch(() => { });
                          }
                        } catch (err: any) {
                          showError(err?.message || 'Failed to save changes.');
                        } finally {
                          setIsLoadingDetails(false);
                        }
                      }
                    }}
                    className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-lg text-xs transition-colors uppercase tracking-wider shadow-md"
                  >
                    Save Changes
                  </button>
                )}
                <button
                  onClick={() => { setSelectedTransaction(null); setIsEditingVoucher(false); }}
                  className="px-6 py-2.5 bg-gray-200 hover:bg-gray-300 text-gray-700 font-bold rounded-lg text-xs transition-colors uppercase tracking-wider"
                >
                  Close
                </button>
              </div>
            </div>

            <style>{`
              @keyframes slideInRight {
                from { transform: translateX(100%); opacity: 0; }
                to   { transform: translateX(0);    opacity: 1; }
              }
              @keyframes fadeIn {
                from { opacity: 0; }
                to   { opacity: 1; }
              }
            `}</style>
          </>
        )}
      </div>
    );
  };

  const renderTrialBalance = () => {
    const showOpeningBalance = trialBalanceType === 'opening';
    const showTransactions = trialBalanceType === 'with_transactions';
    const showClosingBalance = trialBalanceType === 'closing';
    const typeLabel = trialBalanceType === 'opening' ? 'Opening Trial Balance'
      : trialBalanceType === 'with_transactions' ? 'Trial Balance with Transactions'
        : 'Closing Trial Balance';

    // Filter results based on report type to ONLY show ledgers that have values for that report type
    const itemsToDisplay = (tbData?.results || []).filter(item => {
      const openingDr = Number(item.opening_debit || item.opening_balance_dr || 0);
      const openingCr = Number(item.opening_credit || item.opening_balance_cr || 0);
      const txDr = Number(item.period_debit || 0);
      const txCr = Number(item.period_credit || 0);
      const closingDr = Number(item.closing_debit || (item.debit > 0 ? item.debit : 0));
      const closingCr = Number(item.closing_credit || (item.credit > 0 ? item.credit : 0));

      if (showOpeningBalance) {
        return openingDr > 0 || openingCr > 0;
      }
      if (showClosingBalance) {
        return closingDr > 0 || closingCr > 0;
      }
      return openingDr > 0 || openingCr > 0 || txDr > 0 || txCr > 0 || closingDr > 0 || closingCr > 0;
    });

    // Calculate totals for displayed items
    let totDisplayDr = 0, totDisplayCr = 0;
    let totOpDr = 0, totOpCr = 0;
    let totTxDr = 0, totTxCr = 0;
    let totClDr = 0, totClCr = 0;

    itemsToDisplay.forEach(item => {
      const openingDr = Number(item.opening_debit || item.opening_balance_dr || 0);
      const openingCr = Number(item.opening_credit || item.opening_balance_cr || 0);
      const txDr = Number(item.period_debit || 0);
      const txCr = Number(item.period_credit || 0);
      const closingDr = Number(item.closing_debit || (item.debit > 0 ? item.debit : 0));
      const closingCr = Number(item.closing_credit || (item.credit > 0 ? item.credit : 0));

      totOpDr += openingDr;
      totOpCr += openingCr;
      totTxDr += txDr;
      totTxCr += txCr;
      totClDr += closingDr;
      totClCr += closingCr;

      if (showOpeningBalance) {
        totDisplayDr += openingDr;
        totDisplayCr += openingCr;
      } else {
        totDisplayDr += closingDr;
        totDisplayCr += closingCr;
      }
    });

    interface TBTreeNode {
      id: string;
      name: string;
      type: 'category' | 'group' | 'subgroup' | 'ledger';
      level: number;
      openingDr: number;
      openingCr: number;
      txDr: number;
      txCr: number;
      closingDr: number;
      closingCr: number;
      displayDr: number;
      displayCr: number;
      children: TBTreeNode[];
      ledgerName?: string;
      isEndpoint?: boolean;
    }

    const buildTBTree = (): TBTreeNode[] => {
      const rootCategories = [
        "OWNERS' FUNDS",
        "LIABILITY",
        "ASSET",
        "INCOME",
        "EXPENDITURE"
      ];

      const categoryMap = new Map<string, TBTreeNode>();
      rootCategories.forEach(cat => {
        categoryMap.set(cat, {
          id: `cat:${cat}`,
          name: cat,
          type: 'category',
          level: 0,
          openingDr: 0, openingCr: 0, txDr: 0, txCr: 0, closingDr: 0, closingCr: 0, displayDr: 0, displayCr: 0,
          children: []
        });
      });

      const resolveCategory = (item: any): string => {
        const catStr = String(item.category || item.major_group || '').toLowerCase().trim();
        if (catStr.includes('capital') || catStr.includes('owner') || catStr.includes('equity')) return "OWNERS' FUNDS";
        if (catStr.includes('liab')) return "LIABILITY";
        if (catStr.includes('asset')) return "ASSET";
        if (catStr.includes('inc') || catStr.includes('rev')) return "INCOME";
        if (catStr.includes('exp')) return "EXPENDITURE";

        const grpStr = String(item.group || '').toLowerCase().trim();
        if (grpStr.includes('sales') || grpStr.includes('revenue') || grpStr.includes('income')) return "INCOME";
        if (grpStr.includes('purchase') || grpStr.includes('cost') || grpStr.includes('expense') || grpStr.includes('direct') || grpStr.includes('indirect')) return "EXPENDITURE";
        if (grpStr.includes('bank') || grpStr.includes('cash') || grpStr.includes('debtor') || grpStr.includes('asset') || grpStr.includes('inventory')) return "ASSET";
        if (grpStr.includes('creditor') || grpStr.includes('liab') || grpStr.includes('tax') || grpStr.includes('duty') || grpStr.includes('provision')) return "LIABILITY";
        if (grpStr.includes('capital') || grpStr.includes('fund') || grpStr.includes('reserve') || grpStr.includes('share')) return "OWNERS' FUNDS";

        const lStr = String(item.ledger || '').toLowerCase().trim();
        if (lStr.includes('sale')) return "INCOME";
        if (lStr.includes('purchase') || lStr.includes('expense') || lStr.includes('fee') || lStr.includes('rent')) return "EXPENDITURE";
        if (lStr.includes('bank') || lStr.includes('cash') || lStr.includes('asset')) return "ASSET";
        if (lStr.includes('capital') || lStr.includes('reserve') || lStr.includes('fund')) return "OWNERS' FUNDS";
        return "EXPENDITURE";
      };

      itemsToDisplay.forEach(item => {
        const openingDr = Number(item.opening_debit || item.opening_balance_dr || 0);
        const openingCr = Number(item.opening_credit || item.opening_balance_cr || 0);
        const txDr = Number(item.period_debit || 0);
        const txCr = Number(item.period_credit || 0);
        const closingDr = Number(item.closing_debit || (item.debit > 0 ? item.debit : 0));
        const closingCr = Number(item.closing_credit || (item.credit > 0 ? item.credit : 0));
        const displayDr = showOpeningBalance ? openingDr : closingDr;
        const displayCr = showOpeningBalance ? openingCr : closingCr;

        const catName = resolveCategory(item);
        const parentCatNode = categoryMap.get(catName)!;

        const pathParts: string[] = [];
        const g = item.group && item.group !== '-' && item.group !== catName ? String(item.group).trim() : '';
        const sg1 = item.sub_group_1 && item.sub_group_1 !== '-' ? String(item.sub_group_1).trim() : '';
        const sg2 = item.sub_group_2 && item.sub_group_2 !== '-' ? String(item.sub_group_2).trim() : '';
        const sg3 = item.sub_group_3 && item.sub_group_3 !== '-' ? String(item.sub_group_3).trim() : '';

        if (g) pathParts.push(g);
        if (sg1) pathParts.push(sg1);
        if (sg2) pathParts.push(sg2);
        if (sg3) pathParts.push(sg3);

        let currChildren = parentCatNode.children;
        let currPath = parentCatNode.id;
        let currLevel = 1;

        pathParts.forEach((pName, pIdx) => {
          currPath += `>${pName}`;
          let groupNode = currChildren.find(c => c.name === pName);
          if (!groupNode) {
            groupNode = {
              id: currPath,
              name: pName,
              type: pIdx === 0 ? 'group' : 'subgroup',
              level: currLevel,
              openingDr: 0, openingCr: 0, txDr: 0, txCr: 0, closingDr: 0, closingCr: 0, displayDr: 0, displayCr: 0,
              children: []
            };
            currChildren.push(groupNode);
          }
          currChildren = groupNode.children;
          currLevel++;
        });

        const ledgerNode: TBTreeNode = {
          id: `${currPath}>${item.ledger}`,
          name: item.ledger,
          ledgerName: item.ledger,
          type: 'ledger',
          level: currLevel,
          openingDr, openingCr, txDr, txCr, closingDr, closingCr, displayDr, displayCr,
          children: [],
          isEndpoint: true
        };
        currChildren.push(ledgerNode);
      });

      const aggregateSums = (node: TBTreeNode) => {
        if (node.children.length > 0) {
          node.openingDr = 0; node.openingCr = 0;
          node.txDr = 0; node.txCr = 0;
          node.closingDr = 0; node.closingCr = 0;
          node.displayDr = 0; node.displayCr = 0;
          node.children.forEach(child => {
            aggregateSums(child);
            node.openingDr += child.openingDr;
            node.openingCr += child.openingCr;
            node.txDr += child.txDr;
            node.txCr += child.txCr;
            node.closingDr += child.closingDr;
            node.closingCr += child.closingCr;
            node.displayDr += child.displayDr;
            node.displayCr += child.displayCr;
          });
        }
      };

      const finalRoots: TBTreeNode[] = [];
      categoryMap.forEach(catNode => {
        aggregateSums(catNode);
        if (catNode.children.length > 0 || catNode.openingDr > 0 || catNode.openingCr > 0 || catNode.closingDr > 0 || catNode.closingCr > 0) {
          finalRoots.push(catNode);
        }
      });

      return finalRoots;
    };

    const treeRoots = buildTBTree();

    // Auto-populate default expanded nodes ONCE on initial load
    if (!hasInitializedTbTree && treeRoots.length > 0) {
      const initialSet = new Set<string>();
      const walkInitial = (nodes: TBTreeNode[]) => {
        nodes.forEach(n => {
          if (n.children.length > 0) {
            initialSet.add(n.id);
            if (n.level < 2) walkInitial(n.children);
          }
        });
      };
      walkInitial(treeRoots);
      setExpandedTbNodes(initialSet);
      setHasInitializedTbTree(true);
    }

    const visibleRows: TBTreeNode[] = [];
    const walkVisible = (nodes: TBTreeNode[]) => {
      nodes.forEach(n => {
        visibleRows.push(n);
        if (n.children.length > 0 && expandedTbNodes.has(n.id)) {
          walkVisible(n.children);
        }
      });
    };
    walkVisible(treeRoots);

    const formatInr = (val: number) => val.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

    const toggleNode = (nodeId: string) => {
      setExpandedTbNodes(prev => {
        const next = new Set(prev);
        if (next.has(nodeId)) next.delete(nodeId);
        else next.add(nodeId);
        return next;
      });
    };

    return (
      <div className="erp-table-container">
        <div className="p-3 text-center text-sm font-semibold text-indigo-700 bg-indigo-50 border-b border-indigo-100">{typeLabel}</div>
        <table className="erp-table table-fixed w-full">
          <colgroup>
            <col />
            {showTransactions ? (
              <>
                <col className="w-48" />
                <col className="w-44" />
                <col className="w-44" />
                <col className="w-48" />
              </>
            ) : (
              <>
                <col className="w-60" />
                <col className="w-60" />
              </>
            )}
          </colgroup>
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                Group / Ledger Hierarchy
              </th>
              {showTransactions && (
                <>
                  <th className="w-48 px-6 py-4 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">Opening Balance</th>
                  <th className="w-44 px-6 py-4 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">Transactions Debit</th>
                  <th className="w-44 px-6 py-4 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">Transactions Credit</th>
                  <th className="w-48 px-6 py-4 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">Closing Balance</th>
                </>
              )}
              {!showTransactions && (
                <>
                  <th className="w-60 px-8 py-4 text-right text-xs font-bold text-gray-700 uppercase tracking-wider">Debit</th>
                  <th className="w-60 px-8 py-4 text-right text-xs font-bold text-gray-700 uppercase tracking-wider">Credit</th>
                </>
              )}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-100">
            {tbLoading && (
              <tr><td colSpan={showTransactions ? 5 : 3} className="text-center py-8 text-gray-400">Loading trial balance…</td></tr>
            )}

            {/* TREE VIEW RENDERING */}
            {!tbLoading && visibleRows.map(node => {
              const isCat = node.type === 'category';
              const isGroupNode = node.children.length > 0;
              const isExpanded = expandedTbNodes.has(node.id);

              const opVal = node.openingDr > 0 ? `₹${formatInr(node.openingDr)} Dr` : node.openingCr > 0 ? `₹${formatInr(node.openingCr)} Cr` : '-';
              const clVal = node.closingDr > 0 ? `₹${formatInr(node.closingDr)} Dr` : node.closingCr > 0 ? `₹${formatInr(node.closingCr)} Cr` : '-';

              const paddingLeft = isCat ? 'pl-4' : node.level === 1 ? 'pl-8' : node.level === 2 ? 'pl-12' : node.level === 3 ? 'pl-16' : 'pl-20';

              const bgClass = isCat
                ? 'bg-gray-100/90 font-bold text-gray-900 hover:bg-gray-200/90'
                : isGroupNode
                  ? 'bg-indigo-50/40 font-semibold text-indigo-950 hover:bg-indigo-100/50'
                  : 'hover:bg-indigo-50/70 cursor-pointer text-indigo-600 group';

              return (
                <tr
                  key={node.id}
                  onClick={() => {
                    if (isGroupNode) {
                      toggleNode(node.id);
                    } else if (node.ledgerName) {
                      setDrillDownLedger(node.ledgerName);
                    }
                  }}
                  className={`transition-colors ${bgClass}`}
                  title={node.isEndpoint ? `Click to view transactions for ${node.name}` : `Click to ${isExpanded ? 'collapse' : 'expand'} group`}
                >
                  <td className={`px-4 py-3 whitespace-nowrap text-sm ${paddingLeft}`}>
                    <div className="flex items-center">
                      {isGroupNode ? (
                        <button
                          type="button"
                          onClick={(e) => { e.stopPropagation(); toggleNode(node.id); }}
                          className="w-5 h-5 flex items-center justify-center rounded text-indigo-600 hover:bg-indigo-200 font-bold text-xs mr-2 transition-transform select-none"
                        >
                          {isExpanded ? '−' : '+'}
                        </button>
                      ) : (
                        <span className="w-5 h-5 inline-block mr-2 select-none" />
                      )}

                      <span className={node.isEndpoint ? 'italic font-medium text-indigo-600 group-hover:underline' : isCat ? 'font-extrabold text-gray-900 tracking-wide uppercase' : 'font-semibold text-gray-800'}>
                        {node.name}
                      </span>
                    </div>
                  </td>
                  {showTransactions && (
                    <>
                      <td className="w-48 px-6 py-3 whitespace-nowrap text-sm font-mono text-right text-gray-700">{opVal}</td>
                      <td className="w-44 px-6 py-3 whitespace-nowrap text-sm font-mono text-right text-blue-700 font-medium">{node.txDr > 0 ? `₹${formatInr(node.txDr)}` : '-'}</td>
                      <td className="w-44 px-6 py-3 whitespace-nowrap text-sm font-mono text-right text-blue-700 font-medium">{node.txCr > 0 ? `₹${formatInr(node.txCr)}` : '-'}</td>
                      <td className="w-48 px-6 py-3 whitespace-nowrap text-sm font-mono text-right font-bold text-gray-900">{clVal}</td>
                    </>
                  )}
                  {!showTransactions && (
                    <>
                      <td className="w-60 px-8 py-3 whitespace-nowrap text-sm font-mono text-right font-semibold text-gray-900">{node.displayDr > 0 ? `₹${formatInr(node.displayDr)}` : '-'}</td>
                      <td className="w-60 px-8 py-3 whitespace-nowrap text-sm font-mono text-right font-semibold text-gray-900">{node.displayCr > 0 ? `₹${formatInr(node.displayCr)}` : '-'}</td>
                    </>
                  )}
                </tr>
              );
            })}
            {!tbLoading && !itemsToDisplay.length && (
              <tr><td colSpan={showTransactions ? 5 : 3} className="text-center py-8 text-gray-400">No ledgers with balances for selected view.</td></tr>
            )}
          </tbody>
          <tfoot className="bg-gray-100">
            <tr>
              <td className="px-6 py-4 whitespace-nowrap text-sm font-bold text-right text-gray-900">Total</td>
              {showTransactions && (
                <>
                  <td className="w-48 px-6 py-4 whitespace-nowrap text-sm font-mono text-right font-bold text-gray-900">
                    {totOpDr >= totOpCr ? `₹${(totOpDr - totOpCr).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} Dr` : `₹${(totOpCr - totOpDr).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} Cr`}
                  </td>
                  <td className="w-44 px-6 py-4 whitespace-nowrap text-sm font-mono text-right font-bold text-blue-800">₹{totTxDr.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                  <td className="w-44 px-6 py-4 whitespace-nowrap text-sm font-mono text-right font-bold text-blue-800">₹{totTxCr.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                  <td className="w-48 px-6 py-4 whitespace-nowrap text-sm font-mono text-right font-bold text-gray-900">
                    {totClDr >= totClCr ? `₹${(totClDr - totClCr).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} Dr` : `₹${(totClCr - totClDr).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} Cr`}
                  </td>
                </>
              )}
              {!showTransactions && (
                <>
                  <td className="w-60 px-8 py-4 whitespace-nowrap text-sm font-mono text-right font-bold text-gray-900">₹{totDisplayDr.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                  <td className="w-60 px-8 py-4 whitespace-nowrap text-sm font-mono text-right font-bold text-gray-900">₹{totDisplayCr.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                </>
              )}
            </tr>
            {tbData && Math.abs(totDisplayDr - totDisplayCr) >= 0.01 && (
              <tr><td colSpan={showTransactions ? 5 : 3} className="text-center text-xs text-indigo-600 py-1">⚠ Trial Balance difference: ₹{Math.abs(totDisplayDr - totDisplayCr).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td></tr>
            )}
          </tfoot>
        </table>
      </div>
    );
  };

  const renderTrialBalanceLedgerDetail = () => {
    const totalDr = drillDownData.reduce((sum, item) => sum + Number(item.debit || 0), 0);
    const totalCr = drillDownData.reduce((sum, item) => sum + Number(item.credit || 0), 0);
    const last = drillDownData.length > 0 ? drillDownData[drillDownData.length - 1] : null;

    const formatInr = (val: number) => val.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

    return (
      <div className="space-y-6">
        {/* Breadcrumb & Navigation */}
        <div className="flex items-center justify-between bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center gap-2 text-sm">
            <button
              onClick={() => { setDrillDownLedger(null); setDrillDownSourceType(null); }}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-indigo-600 bg-indigo-50 hover:bg-indigo-100 rounded-lg transition-colors"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              Back to Trial Balance
            </button>
            <span className="text-gray-300">/</span>
            <span className="font-bold text-gray-800">{drillDownLedger}</span>
          </div>
        </div>

        {/* Ledger Summary Bar */}
        <div className="bg-gradient-to-r from-slate-900 to-indigo-900 text-white rounded-xl p-6 shadow-md flex flex-wrap items-center justify-between gap-6">
          <div>
            <div className="text-xs uppercase font-bold text-indigo-300 tracking-wider mb-1">Ledger Account</div>
            <h2 className="text-2xl font-extrabold text-white">{drillDownLedger}</h2>
            {startDate || endDate ? (
              <p className="text-xs text-slate-300 mt-1">Period: {startDate || 'Start'} to {endDate || 'Today'}</p>
            ) : null}
          </div>

          <div className="flex items-center gap-8 bg-white/10 backdrop-blur-md px-6 py-3 rounded-lg border border-white/10">
            <div className="text-right">
              <div className="text-xs text-slate-300 uppercase font-semibold">Total Debit</div>
              <div className="text-lg font-mono font-bold text-emerald-400">₹{formatInr(totalDr)}</div>
            </div>
            <div className="w-px h-8 bg-white/20"></div>
            <div className="text-right">
              <div className="text-xs text-slate-300 uppercase font-semibold">Total Credit</div>
              <div className="text-lg font-mono font-bold text-rose-400">₹{formatInr(totalCr)}</div>
            </div>
            {last && (
              <>
                <div className="w-px h-8 bg-white/20"></div>
                <div className="text-right">
                  <div className="text-xs text-slate-300 uppercase font-semibold">Closing Balance</div>
                  <div className="text-lg font-mono font-bold text-white flex items-center gap-1">
                    ₹{formatInr(Number(last.balance || 0))}
                    <span className="text-xs px-1.5 py-0.5 rounded bg-indigo-500/40 text-indigo-200 font-sans">{last.balanceType || 'Dr'}</span>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Clean Ledger Transactions Table (Trial Balance Table Style) */}
        <div className="erp-table-container">
          <div className="p-3 text-center text-sm font-semibold text-indigo-700 bg-indigo-50 border-b border-indigo-100 flex items-center justify-between px-6">
            <span>Ledger Transaction Register — {drillDownLedger}</span>
            <span className="text-xs font-normal text-slate-500">{drillDownData.length} Transactions</span>
          </div>

          <table className="erp-table">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Date</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Particulars</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Voucher Type</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Voucher No</th>
                <th className="px-6 py-4 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">Debit (₹)</th>
                <th className="px-6 py-4 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">Credit (₹)</th>
                <th className="px-6 py-4 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">Running Balance</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-100">
              {isDrillDownLoading && (
                <tr><td colSpan={7} className="text-center py-12 text-gray-400">Loading ledger transactions…</td></tr>
              )}
              {!isDrillDownLoading && drillDownData.map((item, idx) => (
                <tr
                  key={item.id || idx}
                  onClick={() => handleViewTransaction(item)}
                  className="hover:bg-indigo-50/60 transition-colors cursor-pointer"
                  title="Click to view voucher detail"
                >
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{formatDate(item.date)}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-indigo-900">{item.particulars || '-'}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                    <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-700">
                      {normalizeVoucherType(item.voucherType)}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-700">{item.voucherNo || '-'}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-right text-emerald-600 font-semibold">
                    {item.debit > 0 ? `₹${formatInr(Number(item.debit))}` : '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-right text-rose-600 font-semibold">
                    {item.credit > 0 ? `₹${formatInr(Number(item.credit))}` : '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-right font-bold text-gray-900">
                    ₹{formatInr(Number(item.balance || 0))} <span className="text-xs text-gray-500 font-sans">{item.balanceType || 'Dr'}</span>
                  </td>
                </tr>
              ))}
              {!isDrillDownLoading && !drillDownData.length && (
                <tr><td colSpan={7} className="text-center py-12 text-gray-400">No transactions recorded for <strong>{drillDownLedger}</strong> in this period.</td></tr>
              )}
            </tbody>
            <tfoot className="bg-gray-100 font-bold text-sm">
              <tr>
                <td colSpan={4} className="px-6 py-4 text-right text-gray-900">Total</td>
                <td className="px-6 py-4 text-right font-mono text-emerald-700">₹{formatInr(totalDr)}</td>
                <td className="px-6 py-4 text-right font-mono text-rose-700">₹{formatInr(totalCr)}</td>
                <td className="px-6 py-4 text-right font-mono text-indigo-900">
                  {last ? `₹${formatInr(Number(last.balance || 0))} ${last.balanceType || 'Dr'}` : '-'}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    );
  };

  const renderStockSummary = () => (
    <div className="erp-table-container">
      <table className="erp-table">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Item Name</th>
            <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Unit</th>
            <th className="px-6 py-4 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">Opening Stock</th>
            <th className="px-6 py-4 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">Inward</th>
            <th className="px-6 py-4 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">Outward</th>
            <th className="px-6 py-4 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">Closing Stock</th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-100">
          {stockLoading && (
            <tr><td colSpan={6} className="text-center py-8 text-gray-400">Loading stock summary…</td></tr>
          )}
          {!stockLoading && (stockData?.results || []).map(item => (
            <tr key={item.name} className="hover:bg-gray-50 transition-colors">
              <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-900">{item.name}</td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{item.unit || '—'}</td>
              <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-right font-semibold text-gray-900">{Number(item.opening).toFixed(2)}</td>
              <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-right font-semibold text-green-700">{Number(item.inward).toFixed(2)}</td>
              <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-right font-semibold text-red-600">{Number(item.outward).toFixed(2)}</td>
              <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-right font-bold text-gray-900">{Number(item.closing).toFixed(2)}</td>
            </tr>
          ))}
          {!stockLoading && !(stockData?.results?.length) && (
            <tr><td colSpan={6} className="text-center py-8 text-gray-400">No stock data available.</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );



  // GST Report Render Functions
  const renderGSTR1 = () => (
    <>
      <h3 className="text-xl font-semibold text-gray-900 mb-6">GSTR-1: Details of outward supplies of goods or services</h3>

      {/* Section 1: B2B Invoices */}
      <div className="mb-8">
        <h4 className="text-lg font-medium text-gray-800 mb-4">1. B2B Invoices (Registered Dealers)</h4>
        <div className="erp-table-container">
          <table className="erp-table">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">GSTIN</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">PARTY NAME</th>
                <th className="px-6 py-4 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">TAXABLE VALUE</th>
                <th className="px-6 py-4 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">TOTAL TAX</th>
                <th className="px-6 py-4 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">INVOICE VALUE</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-100">
              {/* Sample mock data for B2B */}
              <tr className="hover:bg-gray-50 transition-colors">
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">22AAAAA0000A1Z5</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-900">ABC Corporation Ltd</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-right font-semibold text-gray-900">₹50,000.00</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-right font-semibold text-gray-900">₹9,000.00</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-right font-semibold text-gray-900">₹59,000.00</td>
              </tr>
              <tr className="hover:bg-gray-50 transition-colors">
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">33BBBBB1111B2Y6</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-900">XYZ Enterprises Pvt Ltd</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-right font-semibold text-gray-900">₹75,000.00</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-right font-semibold text-gray-900">₹13,500.00</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-right font-semibold text-gray-900">₹88,500.00</td>
              </tr>
              <tr className="hover:bg-gray-50 transition-colors">
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">44CCCCC2222C3X7</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-900">Global Tech Solutions</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-right font-semibold text-gray-900">₹30,000.00</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-right font-semibold text-gray-900">₹5,400.00</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-right font-semibold text-gray-900">₹35,400.00</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Section 2: B2C Invoices */}
      <div className="mb-8">
        <h4 className="text-lg font-medium text-gray-800 mb-4">2. B2C Invoices (Unregistered Dealers)</h4>
        <div className="erp-table-container">
          <table className="erp-table">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">PARTY NAME</th>
                <th className="px-6 py-4 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">TAXABLE VALUE</th>
                <th className="px-6 py-4 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">TOTAL TAX</th>
                <th className="px-6 py-4 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">INVOICE VALUE</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-100">
              {/* Sample mock data for B2C */}
              <tr className="hover:bg-gray-50 transition-colors">
                <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-900">Local Customer A</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-right font-semibold text-gray-900">₹25,000.00</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-right font-semibold text-gray-900">₹4,500.00</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-right font-semibold text-gray-900">₹29,500.00</td>
              </tr>
              <tr className="hover:bg-gray-50 transition-colors">
                <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-900">Walk-in Customer B</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-right font-semibold text-gray-900">₹15,000.00</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-right font-semibold text-gray-900">₹2,700.00</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-right font-semibold text-gray-900">₹17,700.00</td>
              </tr>
              <tr className="hover:bg-gray-50 transition-colors">
                <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-900">Online Customer C</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-right font-semibold text-gray-900">₹40,000.00</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-right font-semibold text-gray-900">₹7,200.00</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-right font-semibold text-gray-900">₹47,200.00</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </>
  );

  const renderGSTR2A = () => (
    <>
      <h3 className="text-xl font-semibold text-gray-900 mb-6">GSTR-2A: Details of inward supplies from registered persons</h3>

      <div className="mb-8">
        <h4 className="text-lg font-medium text-gray-800 mb-4">Purchase Invoices from Registered Suppliers</h4>
        <div className="erp-table-container">
          <table className="erp-table">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">GSTIN</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">SUPPLIER NAME</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">INVOICE NO</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">DATE</th>
                <th className="px-6 py-4 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">TAXABLE VALUE</th>
                <th className="px-6 py-4 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">IGST</th>
                <th className="px-6 py-4 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">CGST</th>
                <th className="px-6 py-4 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">SGST</th>
                <th className="px-6 py-4 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">INVOICE VALUE</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-100">
              <tr className="hover:bg-gray-50 transition-colors">
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">22AAAAA0000A1Z5</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-900">ABC Suppliers Ltd</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">INV-001</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">15/11/2025</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-right font-semibold text-gray-900">₹45,000.00</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-right font-semibold text-gray-900">₹0.00</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-right font-semibold text-gray-900">₹4,050.00</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-right font-semibold text-gray-900">₹4,050.00</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-right font-semibold text-gray-900">₹53,100.00</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </>
  );

  const renderGSTR3B = () => (
    <>
      <h3 className="text-xl font-semibold text-gray-900 mb-6">GSTR-3B: Monthly Return</h3>

      <div className="mb-8">
        <h4 className="text-lg font-medium text-gray-800 mb-4">3.1 Details of Outward Supplies</h4>
        <div className="erp-table-container">
          <table className="erp-table">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">DESCRIPTION</th>
                <th className="px-6 py-4 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">TAXABLE VALUE</th>
                <th className="px-6 py-4 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">IGST</th>
                <th className="px-6 py-4 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">CGST</th>
                <th className="px-6 py-4 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">SGST</th>
                <th className="px-6 py-4 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">CESS</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-100">
              <tr className="hover:bg-gray-50 transition-colors">
                <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-900">(a) Outward Taxable supplies (other than zero rated, nil rated and exempted)</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-right font-semibold text-gray-900">₹155,000.00</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-right font-semibold text-gray-900">₹0.00</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-right font-semibold text-gray-900">₹13,950.00</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-right font-semibold text-gray-900">₹13,950.00</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-right font-semibold text-gray-900">₹0.00</td>
              </tr>
              <tr className="hover:bg-gray-50 transition-colors">
                <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-900">(b) Outward Taxable supplies (zero rated)</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-right font-semibold text-gray-900">₹0.00</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-right font-semibold text-gray-900">₹0.00</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-right font-semibold text-gray-900">₹0.00</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-right font-semibold text-gray-900">₹0.00</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-right font-semibold text-gray-900">₹0.00</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div className="mb-8">
        <h4 className="text-lg font-medium text-gray-800 mb-4">4. Eligible ITC</h4>
        <div className="erp-table-container">
          <table className="erp-table">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">DESCRIPTION</th>
                <th className="px-6 py-4 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">IGST</th>
                <th className="px-6 py-4 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">CGST</th>
                <th className="px-6 py-4 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">SGST</th>
                <th className="px-6 py-4 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">CESS</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-100">
              <tr className="hover:bg-gray-50 transition-colors">
                <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-900">(A) ITC Available (whether in full or part)</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-right font-semibold text-gray-900">₹0.00</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-right font-semibold text-gray-900">₹4,050.00</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-right font-semibold text-gray-900">₹4,050.00</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-right font-semibold text-gray-900">₹0.00</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </>
  );

  // Default render function for other GST forms
  const renderDefaultGST = (form: GSTForm) => (
    <>
      <h3 className="text-xl font-semibold text-gray-900 mb-6">{form}: GST Return</h3>
      <div className="text-center py-12">
        <p className="text-gray-500">{form} report is under development.</p>
        <p className="text-sm text-gray-400 mt-2">This GST return type will be implemented in future updates.</p>
      </div>
    </>
  );

  // Dynamic GST renderer
  const renderGSTReport = () => {
    switch (selectedGstReturn) {
      case 'GSTR-1':
        return renderGSTR1();
      case 'GSTR-2A':
        return renderGSTR2A();
      case 'GSTR-3B':
        return renderGSTR3B();
      default:
        return renderDefaultGST(selectedGstReturn);
    }
  };






  const safeFormatDate = (dateStr?: string, options?: Intl.DateTimeFormatOptions) => {
    if (!dateStr) return '';
    const str = String(dateStr).trim();
    if (!str || str === '-') return '';

    let d: Date | null = null;
    if (str.match(/^\d{4}-\d{2}-\d{2}$/)) {
      d = new Date(str);
    } else {
      const parts = str.split(/[\/\-]/);
      if (parts.length === 3) {
        if (parts[2].length === 4) {
          d = new Date(`${parts[2]}-${parts[1].padStart(2, '0')}-${parts[0].padStart(2, '0')}`);
        } else if (parts[0].length === 4) {
          d = new Date(str);
        }
      }
    }

    if (!d || isNaN(d.getTime())) {
      return str;
    }

    return d.toLocaleDateString('en-GB', options || { day: 'numeric', month: 'long', year: 'numeric' });
  };

  const safeGetYear = (dateStr?: string) => {
    if (!dateStr) return new Date().getFullYear();
    const str = String(dateStr).trim();
    const parts = str.split(/[\/\-]/);
    if (parts.length === 3) {
      if (parts[2].length === 4) return parseInt(parts[2]);
      if (parts[0].length === 4) return parseInt(parts[0]);
    }
    const d = new Date(str);
    if (!isNaN(d.getTime())) return d.getFullYear();
    return new Date().getFullYear();
  };

  const isNonCorporateBusinessType = (bType?: string) => {
    if (!bType) return true;
    const lower = bType.trim().toLowerCase();
    return (
      lower.includes('all other entities') ||
      lower.includes('llp') ||
      lower.includes('partnership') ||
      lower.includes('other') ||
      lower.includes('proprietorship') ||
      !lower.includes('company')
    );
  };

  const formatNcAmount = (val?: number) => {
    const num = Number(val || 0);
    if (num === 0) return '-';
    return `₹${num.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const renderNcRowItem = (
    label: string,
    items: any[] | undefined,
    indentClass: string = "pl-10",
    expandedSet: Set<string>,
    setExpandedSet: React.Dispatch<React.SetStateAction<Set<string>>>
  ) => {
    const itemList = items || [];
    const total = itemList.reduce((sum: number, x: any) => sum + Number(x.balance || 0), 0);
    const prevTotal = itemList.reduce((sum: number, x: any) => sum + Number(x.prev_balance || 0), 0);
    const isExpanded = expandedSet.has(label);

    const isTargetRow = [
      "Total outstanding dues of micro, small and medium enterprises",
      "Total outstanding dues of creditors other than micro, small and medium enterprises",
      "Other current liabilities"
    ].includes(label);

    const toggleExpand = () => {
      setExpandedSet((prev) => {
        const next = new Set(prev);
        if (next.has(label)) {
          next.delete(label);
        } else {
          next.add(label);
        }
        return next;
      });
    };

    const openCategoryModal = (e: React.MouseEvent) => {
      e.stopPropagation();
      setBsCategoryModal({
        isOpen: true,
        title: label,
        items: itemList
      });
      setSelectedBsCategoryInModal(null);
    };

    const handleButtonClick = (e: React.MouseEvent) => {
      if (isTargetRow) {
        openCategoryModal(e);
      } else {
        toggleExpand();
      }
    };

    const handleLabelClick = (e: React.MouseEvent) => {
      if (isTargetRow && itemList.length > 0) {
        openCategoryModal(e);
      }
    };

    return (
      <React.Fragment key={label}>
        <tr className="hover:bg-indigo-50/30 transition-colors border-b border-slate-100 text-sm">
          <td className={`py-3 px-4 ${indentClass} font-medium text-slate-700`}>
            <div className="flex items-center justify-between pr-2">
              <span
                className={isTargetRow && itemList.length > 0 ? "cursor-pointer hover:text-indigo-600 font-medium transition-colors" : ""}
                onClick={handleLabelClick}
                title={isTargetRow && itemList.length > 0 ? "Click to view categories in window screen" : undefined}
              >
                {label}
              </span>
              {itemList.length > 0 && (
                <button
                  type="button"
                  onClick={handleButtonClick}
                  className="text-xs text-indigo-600 font-bold uppercase tracking-wider hover:text-indigo-800 ml-3 print:hidden"
                  title={isTargetRow ? "Click to view category breakdown in window screen" : "Toggle details"}
                >
                  {isTargetRow
                    ? `${itemList.length} item${itemList.length > 1 ? 's' : ''}`
                    : (isExpanded ? 'Hide Details' : `${itemList.length} item${itemList.length > 1 ? 's' : ''}`)
                  }
                </button>
              )}
            </div>
          </td>
          <td className="py-3 px-6 text-right font-mono font-semibold text-slate-900 text-sm">
            {total !== 0 ? `₹${total.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '-'}
          </td>
          <td className="py-3 px-6 text-right font-mono font-semibold text-slate-700 text-sm">
            {prevTotal !== 0 ? `₹${prevTotal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '-'}
          </td>
        </tr>
        {!isTargetRow && isExpanded && itemList.length > 0 && (
          itemList.map((it: any, idx: number) => {
            const hasSubItems = it.sub_items && it.sub_items.length > 0;
            const subId = `${label}-${it.name}`;
            const isSubExpanded = expandedPnlSubCategories.has(subId);

            const toggleSub = () => {
              setExpandedPnlSubCategories(prev => {
                const next = new Set(prev);
                if (next.has(subId)) next.delete(subId);
                else next.add(subId);
                return next;
              });
            };

            const renderRecursiveSubItems = (items: any[], pId: string, depth: number) => {
              return items.map((subIt: any, subIdx: number) => {
                const hasSub = subIt.sub_items && subIt.sub_items.length > 0;
                const currentId = `${pId}-${subIt.name}`;
                const isSubExp = expandedPnlSubCategories.has(currentId);

                const toggle = () => {
                  setExpandedPnlSubCategories(prev => {
                    const next = new Set(prev);
                    if (next.has(currentId)) next.delete(currentId);
                    else next.add(currentId);
                    return next;
                  });
                };

                const paddingLeft = 5 + depth * 1.5;

                return (
                  <React.Fragment key={`subdetail-${currentId}-${subIdx}`}>
                    <tr className="bg-slate-100/50 border-b border-slate-200/40 text-[11px]">
                      <td className="py-2 pr-4 font-sans text-slate-600 italic" style={{ paddingLeft: `${paddingLeft}rem` }}>
                        <div className="flex items-center justify-between">
                          <span className={hasSub ? "cursor-pointer hover:text-indigo-600 transition-colors" : ""} onClick={hasSub ? toggle : undefined}>
                            {hasSub ? (isSubExp ? '▼ ' : '▶ ') : '- '}{subIt.name}
                          </span>
                        </div>
                      </td>
                      <td className="py-2 px-6 text-right font-mono font-medium text-slate-700">
                        {Number(subIt.balance || 0) !== 0 ? `₹${Number(subIt.balance).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '-'}
                      </td>
                      <td className="py-2 px-6 text-right font-mono font-medium text-slate-500">
                        {Number(subIt.prev_balance || 0) !== 0 ? `₹${Number(subIt.prev_balance).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '-'}
                      </td>
                    </tr>
                    {hasSub && isSubExp && renderRecursiveSubItems(subIt.sub_items, currentId, depth + 1)}
                  </React.Fragment>
                );
              });
            };

            return (
              <React.Fragment key={`detail-${label}-${idx}`}>
                <tr className="bg-slate-50/90 border-b border-slate-200/70 text-xs">
                  <td className="py-2.5 pl-14 pr-4 font-sans font-medium text-slate-700">
                    <div className="flex items-center justify-between">
                      <span className={hasSubItems ? "cursor-pointer hover:text-indigo-600 transition-colors" : ""} onClick={hasSubItems ? toggleSub : undefined}>
                        • {it.name}
                      </span>
                      {hasSubItems && (
                        <button
                          type="button"
                          onClick={toggleSub}
                          className="text-[10px] text-indigo-600 font-bold uppercase tracking-wider hover:text-indigo-800 print:hidden"
                        >
                          {isSubExpanded ? 'Hide' : 'Show'}
                        </button>
                      )}
                    </div>
                  </td>
                  <td className="py-2.5 px-6 text-right font-mono font-semibold text-slate-900">
                    {Number(it.balance || 0) !== 0 ? `₹${Number(it.balance).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '-'}
                  </td>
                  <td className="py-2.5 px-6 text-right font-mono font-semibold text-slate-600">
                    {Number(it.prev_balance || 0) !== 0 ? `₹${Number(it.prev_balance).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '-'}
                  </td>
                </tr>
                {hasSubItems && isSubExpanded && renderRecursiveSubItems(it.sub_items, subId, 0)}
              </React.Fragment>
            );
          })
        )}
      </React.Fragment>
    );
  };

  return (
    <UniversalWorkspaceLayout
      title="Financial Reports Command Center"
      subtitle="Real-time trial balance, day book, ledger summaries, and stock valuation."
      badgeText="FINANCIAL REPORTS"
      inspectorState={inspectorState}
      onCloseInspector={() => setInspectorState(prev => ({ ...prev, isOpen: false }))}
    >
      <div className="flex flex-col gap-6">



        <div className="hidden print:block border-b border-slate-350 pb-4 mb-6">
          <h1 className="text-2xl font-bold text-slate-950 uppercase tracking-wide">{allReports.find(r => r.id === reportType)?.label}</h1>
          <p className="text-xs text-slate-500 font-semibold mt-1">Generated on {formatDate(new Date().toISOString())}</p>
        </div>

        {/* Main Tabs */}
        <div className="erp-tab-container">
          {availableReports.map(({ id, label }) => (
            <button
              key={`report-tab-${id}`}
              onClick={() => setReportType(id as ReportType)}
              className={`erp-tab ${reportType === id ? 'active' : ''}`}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="erp-container">
          {reportType === 'DayBook' && (
            <div className="mb-6 flex flex-wrap items-end justify-between gap-4 p-4 bg-slate-50/70 rounded-2xl border border-slate-200/80 shadow-sm">
              <div className="flex flex-wrap items-end gap-4">
                <div>
                  <label htmlFor="daybookStartDate" className="label-text text-xs font-semibold text-slate-600 mb-1 block">Start Date</label>
                  <DateInput
                    id="daybookStartDate"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    className="erp-input text-xs"
                  />
                </div>
                <div>
                  <label htmlFor="daybookEndDate" className="label-text text-xs font-semibold text-slate-600 mb-1 block">End Date</label>
                  <DateInput
                    id="daybookEndDate"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    className="erp-input text-xs"
                  />
                </div>
                {(startDate || endDate) && (
                  <button
                    onClick={() => { setStartDate(''); setEndDate(''); }}
                    className="text-xs font-semibold text-rose-600 hover:text-rose-700 bg-rose-50 hover:bg-rose-100 px-3 py-2 rounded-lg transition-colors border border-rose-200"
                  >
                    Clear Dates
                  </button>
                )}
              </div>
              <button
                onClick={() => window.print()}
                className="erp-button-primary bg-rose-600 hover:bg-rose-700 py-2 px-4 text-xs font-semibold flex items-center gap-1.5 shadow-sm"
                title="Create PDF"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                Create PDF
              </button>
            </div>
          )}
          {reportType === 'LedgerReport' && (
            <div className="mb-6 flex flex-wrap items-end justify-between gap-4 p-4 bg-slate-50/70 rounded-2xl border border-slate-200/80 shadow-sm">
              <div className="flex flex-wrap items-end gap-4 flex-1">
                <div className="min-w-[240px] max-w-xs">
                  <label className="label-text text-xs font-semibold text-slate-600 mb-1 block">Select Ledger / Group</label>
                  <LedgerSelector
                    selectedValue={selectedLedger}
                    onChange={(val) => {
                      setSelectedLedger(val);
                      if (val && val !== 'all') {
                        const [prefix, name] = val.split(':');
                        if (prefix === 'ledger') {
                          setDrillDownLedger(name);
                        } else {
                          setDrillDownLedger(null);
                        }
                      } else {
                        setDrillDownLedger(null);
                      }
                    }}
                    groups={ledgerGroups}
                    ledgers={ledgers}
                  />
                </div>
                <div>
                  <label htmlFor="ledgerStartDate" className="label-text text-xs font-semibold text-slate-600 mb-1 block">Start Date</label>
                  <DateInput
                    id="ledgerStartDate"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    className="erp-input text-xs"
                  />
                </div>
                <div>
                  <label htmlFor="ledgerEndDate" className="label-text text-xs font-semibold text-slate-600 mb-1 block">End Date</label>
                  <DateInput
                    id="ledgerEndDate"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    className="erp-input text-xs"
                  />
                </div>
                {(startDate || endDate) && (
                  <button
                    onClick={() => { setStartDate(''); setEndDate(''); }}
                    className="text-xs font-semibold text-rose-600 hover:text-rose-700 bg-rose-50 hover:bg-rose-100 px-3 py-2 rounded-lg transition-colors border border-rose-200"
                  >
                    Clear Dates
                  </button>
                )}
              </div>
              <button
                onClick={() => window.print()}
                className="erp-button-primary bg-rose-600 hover:bg-rose-700 py-2 px-4 text-xs font-semibold flex items-center gap-1.5 shadow-sm"
                title="Create PDF"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                Create PDF
              </button>
            </div>
          )}
          {reportType === 'TrialBalance' && (
            <>
              <div className="mb-8 flex flex-wrap items-end gap-6 p-6 bg-slate-50/50 rounded-xl border border-slate-100">
                <div className="min-w-[200px]">
                  <label htmlFor="trialStartDate" className="label-text">Start Date</label>
                  <DateInput

                    id="trialStartDate"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    className="erp-input"
                  />
                </div>
                <div className="min-w-[200px]">
                  <label htmlFor="trialEndDate" className="label-text">End Date</label>
                  <DateInput

                    id="trialEndDate"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    className="erp-input"
                  />
                </div>
                <div className="min-w-[240px]">
                  <label htmlFor="trialBalanceType" className="label-text">Report Type</label>
                  <select
                    id="trialBalanceType"
                    value={trialBalanceType}
                    onChange={(e) => setTrialBalanceType(e.target.value as 'opening' | 'closing' | 'with_transactions')}
                    className="erp-select"
                  >
                    <option value="opening">Opening Trial Balance</option>
                    <option value="closing">Closing Trial Balance</option>
                    <option value="with_transactions">Trial Balance with Transactions</option>
                  </select>
                </div>
              </div>

              <div className="flex justify-between items-center mb-4">
                {!drillDownLedger ? (
                  <button
                    type="button"
                    onClick={() => {
                      if (expandedTbNodes.size > 0) {
                        setExpandedTbNodes(new Set());
                      } else {
                        const rootCategories = ["OWNERS' FUNDS", "LIABILITY", "ASSET", "INCOME", "EXPENDITURE"];
                        const resolveCategory = (item: any): string => {
                          const catStr = String(item.category || item.major_group || '').toLowerCase().trim();
                          if (catStr.includes('capital') || catStr.includes('owner') || catStr.includes('equity')) return "OWNERS' FUNDS";
                          if (catStr.includes('liab')) return "LIABILITY";
                          if (catStr.includes('asset')) return "ASSET";
                          if (catStr.includes('inc') || catStr.includes('rev')) return "INCOME";
                          if (catStr.includes('exp')) return "EXPENDITURE";

                          const grpStr = String(item.group || '').toLowerCase().trim();
                          if (grpStr.includes('sales') || grpStr.includes('revenue') || grpStr.includes('income')) return "INCOME";
                          if (grpStr.includes('purchase') || grpStr.includes('cost') || grpStr.includes('expense') || grpStr.includes('direct') || grpStr.includes('indirect')) return "EXPENDITURE";
                          if (grpStr.includes('bank') || grpStr.includes('cash') || grpStr.includes('debtor') || grpStr.includes('asset') || grpStr.includes('inventory')) return "ASSET";
                          if (grpStr.includes('creditor') || grpStr.includes('liab') || grpStr.includes('tax') || grpStr.includes('duty') || grpStr.includes('provision')) return "LIABILITY";
                          if (grpStr.includes('capital') || grpStr.includes('fund') || grpStr.includes('reserve') || grpStr.includes('share')) return "OWNERS' FUNDS";

                          const lStr = String(item.ledger || '').toLowerCase().trim();
                          if (lStr.includes('sale')) return "INCOME";
                          if (lStr.includes('purchase') || lStr.includes('expense') || lStr.includes('fee') || lStr.includes('rent')) return "EXPENDITURE";
                          if (lStr.includes('bank') || lStr.includes('cash') || lStr.includes('asset')) return "ASSET";
                          if (lStr.includes('capital') || lStr.includes('reserve') || lStr.includes('fund')) return "OWNERS' FUNDS";
                          return "EXPENDITURE";
                        };

                        const allIds = new Set<string>();
                        rootCategories.forEach(cat => allIds.add(`cat:${cat}`));

                        const results = tbData?.results || [];
                        results.forEach((item: any) => {
                          const catName = resolveCategory(item);
                          let path = `cat:${catName}`;
                          const pathParts: string[] = [];
                          const g = item.group && item.group !== '-' && item.group !== catName ? String(item.group).trim() : '';
                          const sg1 = item.sub_group_1 && item.sub_group_1 !== '-' ? String(item.sub_group_1).trim() : '';
                          const sg2 = item.sub_group_2 && item.sub_group_2 !== '-' ? String(item.sub_group_2).trim() : '';
                          const sg3 = item.sub_group_3 && item.sub_group_3 !== '-' ? String(item.sub_group_3).trim() : '';

                          if (g) pathParts.push(g);
                          if (sg1) pathParts.push(sg1);
                          if (sg2) pathParts.push(sg2);
                          if (sg3) pathParts.push(sg3);

                          pathParts.forEach(pName => {
                            path += `>${pName}`;
                            allIds.add(path);
                          });
                        });

                        setExpandedTbNodes(allIds);
                      }
                    }}
                    className="px-3.5 py-1.5 text-xs font-semibold text-indigo-700 bg-indigo-50 border border-indigo-200 rounded-lg hover:bg-indigo-100 transition-colors shadow-sm"
                  >
                    {expandedTbNodes.size > 0 ? '− Collapse All Groups' : '+ Expand All Groups'}
                  </button>
                ) : <div />}
                <button
                  onClick={() => window.print()}
                  className="erp-button-primary bg-rose-600 hover:bg-rose-700"
                  title="Create PDF"
                >
                  Create PDF
                </button>
              </div>
            </>
          )}
          {reportType === 'ProfitAndLoss' && (
            <>
              <div className="mb-8 flex flex-wrap items-end justify-between gap-6 p-6 bg-slate-50/50 rounded-xl border border-slate-100">
                <div className="flex flex-wrap items-end gap-6">
                  <div className="min-w-[200px]">
                    <label className="label-text">Start Date</label>
                    <DateInput
                      value={startDate}
                      onChange={(e) => setStartDate(e.target.value)}
                      className="erp-input"
                    />
                  </div>
                  <div className="min-w-[200px]">
                    <label className="label-text">End Date</label>
                    <DateInput
                      value={endDate}
                      onChange={(e) => setEndDate(e.target.value)}
                      className="erp-input"
                    />
                  </div>

                </div>
                {pnlData?.business_type && (
                  <div className="text-xs text-slate-500 font-medium">
                    Business Type: <span className="font-bold text-slate-800">{pnlData.business_type}</span>
                  </div>
                )}
              </div>

              <div className="flex justify-between items-center mb-4">
                <button
                  type="button"
                  onClick={() => {
                    if (expandedPnlCategories.size > 0) {
                      setExpandedPnlCategories(new Set());
                    } else {
                      const allCats = new Set([
                        "I. Revenue from operations",
                        "II. Other Income",
                        "Cost of goods sold",
                        "Employee benefits expense",
                        "Finance costs",
                        "Depreciation and amortization expense",
                        "Other expenses",
                        "VI. Exceptional items",
                        "VIII. Extraordinary Items",
                        "Current tax",
                        "Excess/ Short provision of tax relating to earlier years",
                        "Deferred tax charge/ (benefit)"
                      ]);
                      setExpandedPnlCategories(allCats);
                    }
                  }}
                  className="px-3.5 py-1.5 text-xs font-semibold text-indigo-700 bg-indigo-50 border border-indigo-200 rounded-lg hover:bg-indigo-100 transition-colors shadow-sm"
                >
                  {expandedPnlCategories.size > 0 ? '− Collapse All Groups' : '+ Expand All Groups'}
                </button>
                <button
                  onClick={() => window.print()}
                  className="erp-button-primary bg-rose-600 hover:bg-rose-700"
                  title="Create PDF"
                >
                  Create PDF
                </button>
              </div>

              <div className="bg-white border rounded-[4px] overflow-hidden shadow-sm">
                {pnlLoading && (
                  <div className="p-12 text-center text-gray-400">Loading Profit & Loss statement…</div>
                )}
                {!pnlLoading && !pnlData && (
                  <div className="p-12 text-center text-gray-400">No data available. Select dates or ensure journal entries exist.</div>
                )}
                {!pnlLoading && pnlData && (
                  <div className="p-6 md:p-8 font-sans w-full">
                    {/* Executive Info Header Card */}
                    <div className="mb-6 p-6 bg-slate-50/80 rounded-xl border border-slate-200 flex flex-wrap items-center justify-between gap-4 shadow-sm">
                      <div className="space-y-2">
                        <div className="flex items-center gap-3 text-base text-slate-800 font-medium">
                          <span>Name of the Non-Corporate Entity:</span>
                          <span className="px-3.5 py-1 bg-indigo-50 text-indigo-700 font-bold rounded-lg border border-indigo-200 text-sm uppercase tracking-wider">
                            {pnlData.company_name || 'Buds Tech Consultancy'}
                          </span>
                        </div>
                        <div className="flex items-center gap-3 text-base text-slate-800 font-medium">
                          <span>Statement of Profit and Loss for the year ended:</span>
                          <span className="font-bold text-slate-900 text-base">
                            {endDate ? safeFormatDate(endDate, { day: 'numeric', month: 'long', year: 'numeric' }) : '31 March 2026'}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Schedule III Non-Corporate Statement of Profit and Loss Table */}
                    <div className="erp-table-container border border-slate-200 rounded-xl overflow-hidden shadow-sm w-full">
                      <table className="w-full text-left border-collapse min-w-full">
                        <thead>
                          <tr className="bg-slate-100/90 border-b border-slate-200 text-sm font-bold text-slate-700 uppercase tracking-wider">
                            <th className="py-4 px-6 border-r border-slate-200 w-7/12">Particulars</th>
                            <th className="py-4 px-6 border-r border-slate-200 text-right w-2.5/12">
                              {endDate ? safeFormatDate(endDate, { day: 'numeric', month: 'short', year: 'numeric' }) : 'Current Year'}
                            </th>
                            <th className="py-4 px-6 text-right w-2.5/12">
                              {endDate ? `31 March ${safeGetYear(endDate) - 1}` : 'Previous Year'}
                            </th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 text-sm text-slate-900">
                          {/* I. Revenue from operations */}
                          {renderNcRowItem("I. Revenue from operations", pnlData.non_corporate?.revenue_from_operations?.items, "pl-6 font-bold text-slate-900", expandedPnlCategories, setExpandedPnlCategories)}

                          {/* II. Other Income */}
                          {renderNcRowItem("II. Other Income", pnlData.non_corporate?.other_income?.items, "pl-6 font-bold text-slate-900", expandedPnlCategories, setExpandedPnlCategories)}

                          {/* III. Total Income (I+II) */}
                          <tr className="bg-indigo-50/70 border-t-2 border-b-2 border-indigo-200 font-bold text-slate-950 text-sm">
                            <td className="py-3.5 px-6">III. Total Income (I+II)</td>
                            <td className="py-3.5 px-6 text-right font-mono font-bold text-indigo-950">
                              {formatNcAmount(pnlData.non_corporate?.total_income)}
                            </td>
                            <td className="py-3.5 px-6 text-right font-mono font-bold text-indigo-950">
                              {formatNcAmount(pnlData.non_corporate?.prev_total_income)}
                            </td>
                          </tr>

                          {/* IV. Expenses Header */}
                          <tr className="bg-slate-100/80 font-bold text-sm text-slate-900">
                            <td colSpan={3} className="py-3 px-6">
                              IV. Expenses:
                            </td>
                          </tr>
                          {renderNcRowItem("Cost of goods sold", pnlData.non_corporate?.expenses?.cost_of_goods_sold?.items, "pl-10", expandedPnlCategories, setExpandedPnlCategories)}
                          {renderNcRowItem("Employee benefits expense", pnlData.non_corporate?.expenses?.employee_benefits_expense?.items, "pl-10", expandedPnlCategories, setExpandedPnlCategories)}
                          {renderNcRowItem("Finance costs", pnlData.non_corporate?.expenses?.finance_costs?.items, "pl-10", expandedPnlCategories, setExpandedPnlCategories)}
                          {renderNcRowItem("Depreciation and amortization expense", pnlData.non_corporate?.expenses?.depreciation_amortization?.items, "pl-10", expandedPnlCategories, setExpandedPnlCategories)}
                          {renderNcRowItem("Other expenses", pnlData.non_corporate?.expenses?.other_expenses?.items, "pl-10", expandedPnlCategories, setExpandedPnlCategories)}

                          {/* Total Expenses */}
                          <tr className="border-t border-b border-slate-200 font-bold bg-slate-50 text-slate-900 text-sm">
                            <td className="py-3 px-6">Total Expenses (IV)</td>
                            <td className="py-3 px-6 text-right font-mono font-bold text-slate-950">
                              {formatNcAmount(pnlData.non_corporate?.expenses?.total)}
                            </td>
                            <td className="py-3 px-6 text-right font-mono font-bold text-slate-950">
                              {formatNcAmount(pnlData.non_corporate?.expenses?.prev_total)}
                            </td>
                          </tr>

                          {/* V. Profit/(loss) before exceptional and extraordinary items and tax (III-IV) */}
                          <tr className="bg-slate-100/90 font-bold text-sm text-slate-900 border-t border-b border-slate-300">
                            <td className="py-3.5 px-6">V. Profit/(loss) before exceptional and extraordinary items and tax (III - IV)</td>
                            <td className="py-3.5 px-6 text-right font-mono font-bold">
                              {formatNcAmount(pnlData.non_corporate?.profit_before_exceptional_extraordinary)}
                            </td>
                            <td className="py-3.5 px-6 text-right font-mono font-bold">
                              {formatNcAmount(pnlData.non_corporate?.prev_profit_before_exceptional_extraordinary)}
                            </td>
                          </tr>

                          {/* VI. Exceptional items */}
                          {renderNcRowItem("VI. Exceptional items", pnlData.non_corporate?.exceptional_items?.items, "pl-6 font-medium text-slate-800", expandedPnlCategories, setExpandedPnlCategories)}

                          {/* VII. Profit/(loss) before extraordinary items and tax (V-VI) */}
                          <tr className="font-bold text-sm text-slate-900 border-t border-b border-slate-200 bg-slate-50">
                            <td className="py-3 px-6">VII. Profit/(loss) before extraordinary items and tax (V - VI)</td>
                            <td className="py-3 px-6 text-right font-mono font-bold">
                              {formatNcAmount(pnlData.non_corporate?.profit_before_extraordinary)}
                            </td>
                            <td className="py-3 px-6 text-right font-mono font-bold">
                              {formatNcAmount(pnlData.non_corporate?.prev_profit_before_extraordinary)}
                            </td>
                          </tr>

                          {/* VIII. Extraordinary Items */}
                          {renderNcRowItem("VIII. Extraordinary Items", pnlData.non_corporate?.extraordinary_items?.items, "pl-6 font-medium text-slate-800", expandedPnlCategories, setExpandedPnlCategories)}

                          {/* IX. Profit before tax (VII-VIII) */}
                          <tr className="font-bold text-sm text-slate-900 border-t border-b border-slate-300 bg-slate-100/70">
                            <td className="py-3.5 px-6">IX. Profit before tax (VII - VIII)</td>
                            <td className="py-3.5 px-6 text-right font-mono font-bold">
                              {formatNcAmount(pnlData.non_corporate?.profit_before_tax)}
                            </td>
                            <td className="py-3.5 px-6 text-right font-mono font-bold">
                              {formatNcAmount(pnlData.non_corporate?.prev_profit_before_tax)}
                            </td>
                          </tr>

                          {/* X. Tax expense */}
                          <tr className="font-bold text-slate-900 bg-slate-50/50 text-sm">
                            <td colSpan={3} className="py-3 px-6">
                              X. Tax expense:
                            </td>
                          </tr>
                          {renderNcRowItem("Current tax", pnlData.non_corporate?.tax_expense?.current_tax?.items, "pl-10", expandedPnlCategories, setExpandedPnlCategories)}
                          {renderNcRowItem("Excess/ Short provision of tax relating to earlier years", pnlData.non_corporate?.tax_expense?.prior_period_tax?.items, "pl-10", expandedPnlCategories, setExpandedPnlCategories)}
                          {renderNcRowItem("Deferred tax charge/ (benefit)", pnlData.non_corporate?.tax_expense?.deferred_tax?.items, "pl-10", expandedPnlCategories, setExpandedPnlCategories)}

                          {/* XI. Profit/(Loss) for the year (IX-X) */}
                          <tr className="bg-slate-900 text-white font-bold text-base border-t-2 border-slate-900">
                            <td className="py-4 px-6">XI. Profit/(Loss) for the year (IX - X)</td>
                            <td className="py-4 px-6 text-right font-mono text-white">
                              {formatNcAmount(pnlData.non_corporate?.profit_continuing_operations)}
                            </td>
                            <td className="py-4 px-6 text-right font-mono text-slate-300">
                              {formatNcAmount(pnlData.non_corporate?.prev_profit_continuing_operations)}
                            </td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            </>
          )}
          {reportType === 'BalanceSheet' && (
            <>
              <div className="mb-8 flex flex-wrap items-end justify-between gap-6 p-6 bg-slate-50/50 rounded-xl border border-slate-100">
                <div className="flex flex-wrap items-end gap-6">
                  <div className="min-w-[200px]">
                    <label className="label-text">As of Date</label>
                    <DateInput
                      value={endDate}
                      onChange={(e) => setEndDate(e.target.value)}
                      className="erp-input"
                    />
                  </div>
                  <div className="min-w-[240px]">
                    <label className="label-text">Balance Sheet Format</label>
                    <select
                      value={balanceSheetFormat}
                      onChange={(e) => setBalanceSheetFormat(e.target.value as any)}
                      className="erp-select"
                    >
                      <option value="auto">Auto ({isNonCorporateBusinessType(bsData?.business_type) ? 'Non-Corporate Vertical' : 'Standard Horizontal'})</option>
                      <option value="vertical">Non-Corporate Vertical (Schedule III)</option>
                      <option value="horizontal">Standard Horizontal (T-Shape)</option>
                    </select>
                  </div>
                </div>
                {bsData?.business_type && (
                  <div className="text-xs text-slate-500 font-medium">
                    Business Type: <span className="font-bold text-slate-800">{bsData.business_type}</span>
                  </div>
                )}
              </div>

              <div className="flex justify-between items-center mb-4">
                {((balanceSheetFormat === 'auto' && isNonCorporateBusinessType(bsData?.business_type)) || balanceSheetFormat === 'vertical') ? (
                  <button
                    type="button"
                    onClick={() => {
                      if (expandedBsCategories.size > 0) {
                        setExpandedBsCategories(new Set());
                      } else {
                        const allCats = new Set([
                          "Owners' Capital Account",
                          "Reserves and surplus",
                          "Long-term borrowings",
                          "Deferred tax liabilities (Net)",
                          "Other long-term liabilities",
                          "Long-term provisions",
                          "Short-term borrowings",
                          "Total outstanding dues of micro, small and medium enterprises",
                          "Total outstanding dues of creditors other than micro, small and medium enterprises",
                          "Other current liabilities",
                          "Short-term provisions",
                          "Property, Plant and Equipment",
                          "Intangible assets",
                          "Capital work in progress",
                          "Intangible asset under development",
                          "Non-current investments",
                          "Deferred tax assets (Net)",
                          "Long Term Loans and Advances",
                          "Other non-current assets",
                          "Current investments",
                          "Inventories",
                          "Trade receivables",
                          "Cash and bank balances",
                          "Short Term Loans and Advances",
                          "Other current assets"
                        ]);
                        setExpandedBsCategories(allCats);
                      }
                    }}
                    className="px-3.5 py-1.5 text-xs font-semibold text-indigo-700 bg-indigo-50 border border-indigo-200 rounded-lg hover:bg-indigo-100 transition-colors shadow-sm"
                  >
                    {expandedBsCategories.size > 0 ? '− Collapse All Groups' : '+ Expand All Groups'}
                  </button>
                ) : <div />}
                <button
                  onClick={() => window.print()}
                  className="erp-button-primary bg-rose-600 hover:bg-rose-700"
                  title="Create PDF"
                >
                  Create PDF
                </button>
              </div>

              <div className="bg-white border rounded-[4px] overflow-hidden shadow-sm">
                {bsLoading && (
                  <div className="p-12 text-center text-gray-400">Loading balance sheet…</div>
                )}
                {!bsLoading && !bsData && (
                  <div className="p-12 text-center text-gray-400">No data available. Select a date or ensure journal entries exist.</div>
                )}
                {!bsLoading && bsData && (
                  <>
                    {bsData.is_balanced === false && (
                      <div className="p-2.5 text-center text-xs font-semibold bg-rose-50 text-rose-700 border-b border-rose-200">
                        ⚠ Balance Sheet does not balance. Difference: ₹{Math.abs(Number(bsData.assets?.total || 0) - Number((bsData.liabilities?.total || 0) + (bsData.capital?.total || 0))).toFixed(2)}
                      </div>
                    )}

                    {((balanceSheetFormat === 'auto' && isNonCorporateBusinessType(bsData.business_type)) || balanceSheetFormat === 'vertical') ? (
                      /* VERTICAL FORMAT FOR NON-CORPORATE ENTITY (IMAGE 2 FORMAT WITH FULL WIDTH) */
                      <div className="p-6 md:p-8 font-sans w-full">
                        {/* Executive Info Header Card */}
                        <div className="mb-6 p-6 bg-slate-50/80 rounded-xl border border-slate-200 flex flex-wrap items-center justify-between gap-4 shadow-sm">
                          <div className="space-y-2">
                            <div className="flex items-center gap-3 text-base text-slate-800 font-medium">
                              <span>Name of the Non-Corporate Entity:</span>
                              <span className="px-3.5 py-1 bg-indigo-50 text-indigo-700 font-bold rounded-lg border border-indigo-200 text-sm uppercase tracking-wider">
                                {bsData.company_name || 'Buds Tech Consultancy'}
                              </span>
                            </div>
                            <div className="flex items-center gap-3 text-base text-slate-800 font-medium">
                              <span>Balance Sheet as at:</span>
                              <span className="font-bold text-slate-900 text-base">
                                {endDate ? safeFormatDate(endDate, { day: 'numeric', month: 'long', year: 'numeric' }) : '31 March 2026'}
                              </span>
                            </div>
                          </div>
                        </div>

                        {/* Modern Enterprise Schedule III Non-Corporate Full Width Table */}
                        <div className="erp-table-container border border-slate-200 rounded-xl overflow-hidden shadow-sm w-full">
                          <table className="w-full text-left border-collapse min-w-full">
                            <thead>
                              <tr className="bg-slate-100/90 border-b border-slate-200 text-sm font-bold text-slate-700 uppercase tracking-wider">
                                <th className="py-4 px-6 border-r border-slate-200 w-7/12">Particulars</th>
                                <th className="py-4 px-6 border-r border-slate-200 text-right w-2.5/12">
                                  {endDate ? safeFormatDate(endDate, { day: 'numeric', month: 'short', year: 'numeric' }) : 'Current Year'}
                                </th>
                                <th className="py-4 px-6 text-right w-2.5/12">
                                  {endDate ? `31 March ${safeGetYear(endDate) - 1}` : 'Previous Year'}
                                </th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100 text-sm text-slate-900">
                              {/* EQUITY AND LIABILITIES */}
                              <tr className="bg-indigo-50/80 font-bold text-sm text-indigo-950 uppercase tracking-wider">
                                <td colSpan={3} className="py-3.5 px-6 border-y border-indigo-100">
                                  EQUITY AND LIABILITIES
                                </td>
                              </tr>

                              {/* 1. Owners' Funds */}
                              <tr className="font-bold text-slate-900 bg-slate-50/50 text-sm">
                                <td colSpan={3} className="py-3 px-6">
                                  Owners' Funds
                                </td>
                              </tr>
                              {renderNcRowItem("Owners' Capital Account", bsData.non_corporate?.equity_and_liabilities?.owners_funds?.capital_account, "pl-10", expandedBsCategories, setExpandedBsCategories)}
                              {renderNcRowItem("Reserves and surplus", bsData.non_corporate?.equity_and_liabilities?.owners_funds?.reserves_and_surplus, "pl-10", expandedBsCategories, setExpandedBsCategories)}
                              <tr className="border-t border-b border-slate-200 font-bold bg-slate-50 text-slate-900 text-sm">
                                <td className="py-3 px-10">Subtotal - Owners' Funds</td>
                                <td className="py-3 px-6 text-right font-mono font-bold text-slate-950">
                                  {formatNcAmount(bsData.non_corporate?.equity_and_liabilities?.owners_funds?.total)}
                                </td>
                                <td className="py-3 px-6 text-right font-mono font-bold text-slate-700">
                                  {formatNcAmount(bsData.non_corporate?.equity_and_liabilities?.owners_funds?.prev_total)}
                                </td>
                              </tr>

                              {/* 2. Non-current liabilities */}
                              <tr className="font-bold text-slate-900 bg-slate-50/50 text-sm">
                                <td colSpan={3} className="py-3 px-6">
                                  Non-current liabilities
                                </td>
                              </tr>
                              {renderNcRowItem("Long-term borrowings", bsData.non_corporate?.equity_and_liabilities?.non_current_liabilities?.long_term_borrowings, "pl-10", expandedBsCategories, setExpandedBsCategories)}
                              {renderNcRowItem("Deferred tax liabilities (Net)", bsData.non_corporate?.equity_and_liabilities?.non_current_liabilities?.deferred_tax_liabilities, "pl-10", expandedBsCategories, setExpandedBsCategories)}
                              {renderNcRowItem("Other long-term liabilities", bsData.non_corporate?.equity_and_liabilities?.non_current_liabilities?.other_long_term_liabilities, "pl-10", expandedBsCategories, setExpandedBsCategories)}
                              {renderNcRowItem("Long-term provisions", bsData.non_corporate?.equity_and_liabilities?.non_current_liabilities?.long_term_provisions, "pl-10", expandedBsCategories, setExpandedBsCategories)}
                              <tr className="border-t border-b border-slate-200 font-bold bg-slate-50 text-slate-900 text-sm">
                                <td className="py-3 px-10">Subtotal - Non-current liabilities</td>
                                <td className="py-3 px-6 text-right font-mono font-bold text-slate-950">
                                  {formatNcAmount(bsData.non_corporate?.equity_and_liabilities?.non_current_liabilities?.total)}
                                </td>
                                <td className="py-3 px-6 text-right font-mono font-bold text-slate-700">
                                  {formatNcAmount(bsData.non_corporate?.equity_and_liabilities?.non_current_liabilities?.prev_total)}
                                </td>
                              </tr>

                              {/* 3. Current liabilities */}
                              <tr className="font-bold text-slate-900 bg-slate-50/50 text-sm">
                                <td colSpan={3} className="py-3 px-6">
                                  Current liabilities
                                </td>
                              </tr>
                              {renderNcRowItem("Short-term borrowings", bsData.non_corporate?.equity_and_liabilities?.current_liabilities?.short_term_borrowings, "pl-10", expandedBsCategories, setExpandedBsCategories)}
                              <tr className="font-semibold text-slate-800 text-sm">
                                <td colSpan={3} className="py-2.5 px-10">
                                  Trade payables
                                </td>
                              </tr>
                              {renderNcRowItem("Total outstanding dues of micro, small and medium enterprises", bsData.non_corporate?.equity_and_liabilities?.current_liabilities?.trade_payables?.msme_dues, "pl-14", expandedBsCategories, setExpandedBsCategories)}
                              {renderNcRowItem("Total outstanding dues of creditors other than micro, small and medium enterprises", bsData.non_corporate?.equity_and_liabilities?.current_liabilities?.trade_payables?.other_creditors_dues, "pl-14", expandedBsCategories, setExpandedBsCategories)}
                              {renderNcRowItem("Other current liabilities", bsData.non_corporate?.equity_and_liabilities?.current_liabilities?.other_current_liabilities, "pl-10", expandedBsCategories, setExpandedBsCategories)}
                              {renderNcRowItem("Short-term provisions", bsData.non_corporate?.equity_and_liabilities?.current_liabilities?.short_term_provisions, "pl-10", expandedBsCategories, setExpandedBsCategories)}
                              <tr className="border-t border-b border-slate-200 font-bold bg-slate-50 text-slate-900 text-sm">
                                <td className="py-3 px-10">Subtotal - Current liabilities</td>
                                <td className="py-3 px-6 text-right font-mono font-bold text-slate-950">
                                  {formatNcAmount(bsData.non_corporate?.equity_and_liabilities?.current_liabilities?.total)}
                                </td>
                                <td className="py-3 px-6 text-right font-mono font-bold text-slate-700">
                                  {formatNcAmount(bsData.non_corporate?.equity_and_liabilities?.current_liabilities?.prev_total)}
                                </td>
                              </tr>
                              {renderNcRowItem("Difference in Opening Balances", bsData.non_corporate?.equity_and_liabilities?.difference_in_opening_balances, "pl-6 font-semibold", expandedBsCategories, setExpandedBsCategories)}

                              {/* TOTAL EQUITY AND LIABILITIES */}
                              <tr className="bg-slate-900 text-white font-bold text-base border-t-2 border-slate-900">
                                <td className="py-4 px-6">Total</td>
                                <td className="py-4 px-6 text-right font-mono text-white">
                                  {formatNcAmount(bsData.non_corporate?.equity_and_liabilities?.total)}
                                </td>
                                <td className="py-4 px-6 text-right font-mono text-slate-200">
                                  {formatNcAmount(bsData.non_corporate?.equity_and_liabilities?.prev_total)}
                                </td>
                              </tr>

                              {/* ASSETS */}
                              <tr className="bg-indigo-50/80 font-bold text-sm text-indigo-950 uppercase tracking-wider">
                                <td colSpan={3} className="py-3.5 px-6 border-y border-indigo-100">
                                  ASSETS
                                </td>
                              </tr>

                              {/* 1. Non-current assets */}
                              <tr className="font-bold text-slate-900 bg-slate-50/50 text-sm">
                                <td colSpan={3} className="py-3 px-6">
                                  Non-current assets
                                </td>
                              </tr>
                              <tr className="font-semibold text-slate-800 text-sm">
                                <td colSpan={3} className="py-2.5 px-10">
                                  Property, Plant and Equipment and Intangible assets
                                </td>
                              </tr>
                              {renderNcRowItem("Property, Plant and Equipment", bsData.non_corporate?.assets?.non_current_assets?.ppe_and_intangibles?.property_plant_equipment, "pl-14", expandedBsCategories, setExpandedBsCategories)}
                              {renderNcRowItem("Intangible assets", bsData.non_corporate?.assets?.non_current_assets?.ppe_and_intangibles?.intangible_assets, "pl-14", expandedBsCategories, setExpandedBsCategories)}
                              {renderNcRowItem("Capital work in progress", bsData.non_corporate?.assets?.non_current_assets?.ppe_and_intangibles?.capital_wip, "pl-14", expandedBsCategories, setExpandedBsCategories)}
                              {renderNcRowItem("Intangible asset under development", bsData.non_corporate?.assets?.non_current_assets?.ppe_and_intangibles?.intangible_under_development, "pl-14", expandedBsCategories, setExpandedBsCategories)}
                              {renderNcRowItem("Non-current investments", bsData.non_corporate?.assets?.non_current_assets?.non_current_investments, "pl-10", expandedBsCategories, setExpandedBsCategories)}
                              {renderNcRowItem("Deferred tax assets (Net)", bsData.non_corporate?.assets?.non_current_assets?.deferred_tax_assets, "pl-10", expandedBsCategories, setExpandedBsCategories)}
                              {renderNcRowItem("Long Term Loans and Advances", bsData.non_corporate?.assets?.non_current_assets?.long_term_loans_advances, "pl-10", expandedBsCategories, setExpandedBsCategories)}
                              {renderNcRowItem("Other non-current assets", bsData.non_corporate?.assets?.non_current_assets?.other_non_current_assets, "pl-10", expandedBsCategories, setExpandedBsCategories)}
                              <tr className="border-t border-b border-slate-200 font-bold bg-slate-50 text-slate-900 text-sm">
                                <td className="py-3 px-10">Subtotal - Non-current assets</td>
                                <td className="py-3 px-6 text-right font-mono font-bold text-slate-950">
                                  {formatNcAmount(bsData.non_corporate?.assets?.non_current_assets?.total)}
                                </td>
                                <td className="py-3 px-6 text-right font-mono font-bold text-slate-700">
                                  {formatNcAmount(bsData.non_corporate?.assets?.non_current_assets?.prev_total)}
                                </td>
                              </tr>

                              {/* 2. Current assets */}
                              <tr className="font-bold text-slate-900 bg-slate-50/50 text-sm">
                                <td colSpan={3} className="py-3 px-6">
                                  Current assets
                                </td>
                              </tr>
                              {renderNcRowItem("Current investments", bsData.non_corporate?.assets?.current_assets?.current_investments, "pl-10", expandedBsCategories, setExpandedBsCategories)}
                              {renderNcRowItem("Inventories", bsData.non_corporate?.assets?.current_assets?.inventories, "pl-10", expandedBsCategories, setExpandedBsCategories)}
                              {renderNcRowItem("Trade receivables", bsData.non_corporate?.assets?.current_assets?.trade_receivables, "pl-10", expandedBsCategories, setExpandedBsCategories)}
                              {renderNcRowItem("Cash and bank balances", bsData.non_corporate?.assets?.current_assets?.cash_and_bank_balances, "pl-10", expandedBsCategories, setExpandedBsCategories)}
                              {renderNcRowItem("Short Term Loans and Advances", bsData.non_corporate?.assets?.current_assets?.short_term_loans_advances, "pl-10", expandedBsCategories, setExpandedBsCategories)}
                              {renderNcRowItem("Other current assets", bsData.non_corporate?.assets?.current_assets?.other_current_assets, "pl-10", expandedBsCategories, setExpandedBsCategories)}
                              <tr className="border-t border-b border-slate-200 font-bold bg-slate-50 text-slate-900 text-sm">
                                <td className="py-3 px-10">Subtotal - Current assets</td>
                                <td className="py-3 px-6 text-right font-mono font-bold text-slate-950">
                                  {formatNcAmount(bsData.non_corporate?.assets?.current_assets?.total)}
                                </td>
                                <td className="py-3 px-6 text-right font-mono font-bold text-slate-700">
                                  {formatNcAmount(bsData.non_corporate?.assets?.current_assets?.prev_total)}
                                </td>
                              </tr>
                              {renderNcRowItem("Difference in Opening Balances", bsData.non_corporate?.assets?.difference_in_opening_balances, "pl-6 font-semibold", expandedBsCategories, setExpandedBsCategories)}

                              {/* TOTAL ASSETS */}
                              <tr className="bg-slate-900 text-white font-bold text-base border-t-2 border-slate-900">
                                <td className="py-4 px-6">Total</td>
                                <td className="py-4 px-6 text-right font-mono text-white">
                                  {formatNcAmount(bsData.non_corporate?.assets?.total)}
                                </td>
                                <td className="py-4 px-6 text-right font-mono text-slate-200">
                                  {formatNcAmount(bsData.non_corporate?.assets?.prev_total)}
                                </td>
                              </tr>
                            </tbody>
                          </table>
                        </div>
                      </div>
                    ) : (
                      /* HORIZONTAL FORMAT FOR CORPORATE ENTITY / STANDARD T-SHAPE */
                      <div className="grid grid-cols-2 divide-x divide-gray-200">
                        {/* LEFT — Assets */}
                        <div className="p-4">
                          <h3 className="text-sm font-bold text-gray-700 uppercase tracking-wider mb-3 border-b pb-2">Assets</h3>
                          {/* Fixed Assets */}
                          {(bsData.assets?.fixed_assets?.length > 0) && (
                            <>
                              <p className="text-xs font-semibold text-gray-500 uppercase mb-1 mt-2">Fixed Assets</p>
                              {bsData.assets.fixed_assets.map((item: any) => (
                                <div key={item.name} className="flex justify-between py-1 text-sm">
                                  <span className="text-gray-700">{item.name}</span>
                                  <span className="font-mono font-semibold text-gray-900">₹{Number(item.balance).toFixed(2)}</span>
                                </div>
                              ))}
                              <div className="flex justify-between py-1 text-sm font-semibold border-t mt-1">
                                <span className="text-gray-600">Total Fixed Assets</span>
                                <span className="font-mono text-gray-900">₹{Number(bsData.assets.total_fixed_assets).toFixed(2)}</span>
                              </div>
                            </>
                          )}
                          {/* Current Assets */}
                          {(bsData.assets?.current_assets?.length > 0) && (
                            <>
                              <p className="text-xs font-semibold text-gray-500 uppercase mb-1 mt-3">Current Assets</p>
                              {bsData.assets.current_assets.map((item: any) => (
                                <div key={item.name} className="flex justify-between py-1 text-sm">
                                  <span className="text-gray-700">{item.name}</span>
                                  <span className="font-mono font-semibold text-gray-900">₹{Number(item.balance).toFixed(2)}</span>
                                </div>
                              ))}
                              <div className="flex justify-between py-1 text-sm font-semibold border-t mt-1">
                                <span className="text-gray-600">Total Current Assets</span>
                                <span className="font-mono text-gray-900">₹{Number(bsData.assets.total_current_assets).toFixed(2)}</span>
                              </div>
                            </>
                          )}
                          <div className="flex justify-between py-2 text-sm font-bold bg-gray-50 rounded mt-3 px-2 border">
                            <span>Total Assets</span>
                            <span className="font-mono">₹{Number(bsData.assets?.total || 0).toFixed(2)}</span>
                          </div>
                        </div>
                        {/* RIGHT — Liabilities + Capital */}
                        <div className="p-4">
                          <h3 className="text-sm font-bold text-gray-700 uppercase tracking-wider mb-3 border-b pb-2">Liabilities & Capital</h3>
                          {/* Capital */}
                          {(bsData.capital?.capital_account?.length > 0) && (
                            <>
                              <p className="text-xs font-semibold text-gray-500 uppercase mb-1 mt-2">Capital</p>
                              {bsData.capital.capital_account.map((item: any) => (
                                <div key={item.name} className="flex justify-between py-1 text-sm">
                                  <span className="text-gray-700">{item.name}</span>
                                  <span className="font-mono font-semibold text-gray-900">₹{Number(item.balance).toFixed(2)}</span>
                                </div>
                              ))}
                              {bsData.capital.retained_earnings !== 0 && (
                                <div className="flex justify-between py-1 text-sm">
                                  <span className="text-gray-700">Retained Earnings</span>
                                  <span className={`font-mono font-semibold ${Number(bsData.capital.retained_earnings) < 0 ? 'text-red-600' : 'text-gray-900'}`}>
                                    ₹{Number(bsData.capital.retained_earnings).toFixed(2)}
                                  </span>
                                </div>
                              )}
                              <div className="flex justify-between py-1 text-sm font-semibold border-t mt-1">
                                <span className="text-gray-600">Total Capital</span>
                                <span className="font-mono text-gray-900">₹{Number(bsData.capital.total).toFixed(2)}</span>
                              </div>
                            </>
                          )}
                          {/* Long-term Liabilities */}
                          {(bsData.liabilities?.long_term_liabilities?.length > 0) && (
                            <>
                              <p className="text-xs font-semibold text-gray-500 uppercase mb-1 mt-3">Long-term Liabilities</p>
                              {bsData.liabilities.long_term_liabilities.map((item: any) => (
                                <div key={item.name} className="flex justify-between py-1 text-sm">
                                  <span className="text-gray-700">{item.name}</span>
                                  <span className="font-mono font-semibold text-gray-900">₹{Number(item.balance).toFixed(2)}</span>
                                </div>
                              ))}
                            </>
                          )}
                          {/* Current Liabilities */}
                          {(bsData.liabilities?.current_liabilities?.length > 0) && (
                            <>
                              <p className="text-xs font-semibold text-gray-500 uppercase mb-1 mt-3">Current Liabilities</p>
                              {bsData.liabilities.current_liabilities.map((item: any) => (
                                <div key={item.name} className="flex justify-between py-1 text-sm">
                                  <span className="text-gray-700">{item.name}</span>
                                  <span className="font-mono font-semibold text-gray-900">₹{Number(item.balance).toFixed(2)}</span>
                                </div>
                              ))}
                            </>
                          )}
                          {(bsData.liabilities?.total > 0) && (
                            <div className="flex justify-between py-1 text-sm font-semibold border-t mt-1">
                              <span className="text-gray-600">Total Liabilities</span>
                              <span className="font-mono text-gray-900">₹{Number(bsData.liabilities.total).toFixed(2)}</span>
                            </div>
                          )}
                          <div className="flex justify-between py-2 text-sm font-bold bg-gray-50 rounded mt-3 px-2 border">
                            <span>Total Liabilities + Capital</span>
                            <span className="font-mono">₹{(Number(bsData.liabilities?.total || 0) + Number(bsData.capital?.total || 0)).toFixed(2)}</span>
                          </div>
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>

              {/* BALANCE SHEET CATEGORY & VENDOR/LEDGER BREAKDOWN WINDOW SCREEN (MODAL) */}
              {bsCategoryModal?.isOpen && (() => {
                const isVendorList = bsCategoryModal.title.toLowerCase().includes('creditor') || 
                                     bsCategoryModal.title.toLowerCase().includes('micro') || 
                                     bsCategoryModal.title.toLowerCase().includes('payable') ||
                                     bsCategoryModal.title.toLowerCase().includes('vendor');
                const columnHeaderName = isVendorList ? 'VENDOR NAME' : 'PARTICULARS / LEDGER NAME';
                const itemTypeLabel = isVendorList ? 'Vendor' : 'Item';
                const itemTypeLabelPlural = isVendorList ? 'Vendors' : 'Items';

                return (
                  <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn print:hidden">
                    <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden">
                      
                      {/* MODAL HEADER */}
                      <div className="px-6 py-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          {selectedBsCategoryInModal && (
                            <button
                              onClick={() => setSelectedBsCategoryInModal(null)}
                              className="p-1.5 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-slate-200/80 transition-colors"
                              title="Back to Categories"
                            >
                              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 19l-7-7 7-7" />
                              </svg>
                            </button>
                          )}
                          <div>
                            <div className="flex items-center gap-2">
                              <h3 className="text-base font-bold text-slate-800">{bsCategoryModal.title}</h3>
                              <span className="px-2.5 py-0.5 bg-indigo-50 text-indigo-700 text-xs font-bold rounded-full border border-indigo-200">
                                {bsCategoryModal.items.length} {bsCategoryModal.items.length === 1 ? itemTypeLabel : itemTypeLabelPlural}
                              </span>
                            </div>
                            {selectedBsCategoryInModal ? (
                              <p className="text-xs text-slate-500 mt-0.5">
                                Category: <span className="font-bold text-indigo-600 uppercase">{selectedBsCategoryInModal}</span>
                              </p>
                            ) : (
                              <p className="text-xs text-slate-500 mt-0.5">
                                Select a category card to view associated {isVendorList ? 'vendor names' : 'ledger accounts'}.
                              </p>
                            )}
                          </div>
                        </div>

                        <button
                          onClick={() => {
                            setBsCategoryModal(null);
                            setSelectedBsCategoryInModal(null);
                          }}
                          className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-200/60 rounded-xl transition-colors"
                        >
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      </div>

                      {/* MODAL BODY */}
                      <div className="p-6 overflow-y-auto flex-1 bg-slate-50/40">
                        {!selectedBsCategoryInModal ? (
                          /* STEP 1: CATEGORY CARDS VIEW */
                          <div>
                            <div className="mb-3 flex items-center justify-between">
                              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Categories</span>
                              <span className="text-xs text-slate-400">
                                Click any category card to view {isVendorList ? 'vendor names' : 'ledger accounts'}
                              </span>
                            </div>
                            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                              {Object.entries(
                                bsCategoryModal.items.reduce((acc: any, item: any) => {
                                  let rawCat = (item.category || 'General').trim();
                                  if (rawCat.includes('>')) {
                                    rawCat = rawCat.split('>')[0].trim();
                                  }
                                  const cat = rawCat || 'General';
                                  if (!acc[cat]) acc[cat] = [];
                                  acc[cat].push(item);
                                  return acc;
                                }, {})
                              ).map(([catName, catItems]: [string, any]) => {
                                const totalBal = catItems.reduce((s: number, x: any) => s + Number(x.balance || 0), 0);
                                return (
                                  <div
                                    key={catName}
                                    onClick={() => setSelectedBsCategoryInModal(catName)}
                                    className="p-5 bg-white border border-slate-200 rounded-xl hover:border-indigo-400 hover:shadow-md transition-all cursor-pointer group flex flex-col justify-between"
                                  >
                                    <div>
                                      <div className="flex items-center justify-between mb-3">
                                        <div className="w-10 h-10 rounded-lg bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 group-hover:bg-indigo-600 group-hover:text-white transition-colors shadow-sm">
                                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                                          </svg>
                                        </div>
                                        <span className="text-[11px] font-bold uppercase tracking-wider text-indigo-700 bg-indigo-50 border border-indigo-100 px-2 py-0.5 rounded-md">
                                          {catItems.length} {catItems.length === 1 ? itemTypeLabel : itemTypeLabelPlural}
                                        </span>
                                      </div>
                                      <h4 className="font-bold text-slate-800 text-sm uppercase tracking-wide group-hover:text-indigo-700 transition-colors">
                                        {catName}
                                      </h4>
                                      <p className="text-xs text-slate-400 mt-1">
                                        {isVendorList ? 'Manage & view vendor list' : 'View associated ledger accounts'}
                                      </p>
                                    </div>

                                    <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
                                      <span className="text-xs text-slate-500 font-medium">Total Balance</span>
                                      <span className="font-mono font-bold text-slate-900 text-sm">
                                        ₹{totalBal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                      </span>
                                    </div>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        ) : (
                          /* STEP 2: VENDOR/LEDGER TABLE VIEW UNDER SELECTED CATEGORY */
                          <div>
                            <div className="mb-4 flex items-center justify-between">
                              <button
                                onClick={() => setSelectedBsCategoryInModal(null)}
                                className="text-xs font-bold text-indigo-600 hover:text-indigo-800 flex items-center gap-1 bg-indigo-50 px-3 py-1.5 rounded-lg border border-indigo-200 transition-colors"
                              >
                                ← Back to Categories
                              </button>
                              <span className="text-xs font-semibold text-slate-500">
                                Selected Category: <strong className="text-slate-800 uppercase font-bold">{selectedBsCategoryInModal}</strong>
                              </span>
                            </div>

                            <div className="border border-slate-200 rounded-xl overflow-hidden shadow-sm bg-white">
                              <table className="w-full text-left border-collapse">
                                <thead>
                                  <tr className="bg-slate-100 text-xs font-bold text-slate-700 uppercase tracking-wider border-b border-slate-200">
                                    <th className="py-3.5 px-5">{columnHeaderName}</th>
                                    <th className="py-3.5 px-5 text-right">Current Year (₹)</th>
                                    <th className="py-3.5 px-5 text-right">Previous Year (₹)</th>
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100 text-sm text-slate-800">
                                  {bsCategoryModal.items
                                    .filter((it: any) => {
                                      let itCat = (it.category || 'General').trim();
                                      if (itCat.includes('>')) itCat = itCat.split('>')[0].trim();
                                      return (itCat || 'General') === selectedBsCategoryInModal;
                                    })
                                    .map((it: any, idx: number) => (
                                      <tr key={idx} className="hover:bg-indigo-50/30 transition-colors">
                                        <td className="py-3.5 px-5 font-medium flex items-center gap-2.5">
                                          <span className="w-2 h-2 rounded-full bg-indigo-500"></span>
                                          <span className="font-bold text-slate-800">{it.name}</span>
                                        </td>
                                        <td className="py-3.5 px-5 text-right font-mono font-bold text-slate-900">
                                          {Number(it.balance || 0) !== 0 ? `₹${Number(it.balance).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '-'}
                                        </td>
                                        <td className="py-3.5 px-5 text-right font-mono font-medium text-slate-500">
                                          {Number(it.prev_balance || 0) !== 0 ? `₹${Number(it.prev_balance).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '-'}
                                        </td>
                                      </tr>
                                    ))}
                                </tbody>
                                <tfoot>
                                  <tr className="bg-slate-50 font-bold border-t border-slate-200 text-slate-900 text-sm">
                                    <td className="py-3.5 px-5">Total for {selectedBsCategoryInModal}</td>
                                    <td className="py-3.5 px-5 text-right font-mono text-indigo-700">
                                      ₹{bsCategoryModal.items
                                        .filter((it: any) => {
                                          let itCat = (it.category || 'General').trim();
                                          if (itCat.includes('>')) itCat = itCat.split('>')[0].trim();
                                          return (itCat || 'General') === selectedBsCategoryInModal;
                                        })
                                        .reduce((s: number, x: any) => s + Number(x.balance || 0), 0)
                                        .toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                    </td>
                                    <td className="py-3.5 px-5 text-right font-mono text-slate-600">
                                      ₹{bsCategoryModal.items
                                        .filter((it: any) => {
                                          let itCat = (it.category || 'General').trim();
                                          if (itCat.includes('>')) itCat = itCat.split('>')[0].trim();
                                          return (itCat || 'General') === selectedBsCategoryInModal;
                                        })
                                        .reduce((s: number, x: any) => s + Number(x.prev_balance || 0), 0)
                                        .toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                    </td>
                                  </tr>
                                </tfoot>
                            </table>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* MODAL FOOTER */}
                    <div className="px-6 py-3.5 bg-slate-50 border-t border-slate-200 flex justify-end">
                      <button
                        onClick={() => {
                          setBsCategoryModal(null);
                          setSelectedBsCategoryInModal(null);
                        }}
                        className="px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-700 text-xs font-bold rounded-lg transition-colors"
                      >
                        Close
                      </button>
                    </div>

                  </div>
                </div>
              );
              })()}
            </>
          )}
          {reportType === 'StockSummary' && (
            <>
              <div className="mb-8 flex flex-wrap items-end gap-6 p-6 bg-slate-50/50 rounded-xl border border-slate-100">
                <div className="min-w-[200px]">
                  <label htmlFor="stockStartDate" className="label-text">Start Date</label>
                  <DateInput

                    id="stockStartDate"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    className="erp-input"
                  />
                </div>
                <div className="min-w-[200px]">
                  <label htmlFor="stockEndDate" className="label-text">End Date</label>
                  <DateInput

                    id="stockEndDate"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    className="erp-input"
                  />
                </div>
              </div>

              <div className="flex justify-end mb-4">
                <button
                  onClick={() => window.print()}
                  className="erp-button-primary bg-rose-600 hover:bg-rose-700"
                  title="Create PDF"
                >
                  Create PDF
                </button>
              </div>
            </>
          )}
          {reportType === 'GSTReports' && (
            <>
              {/* Filter Section Row */}
              <div className="mb-8 flex flex-wrap items-end gap-6 p-6 bg-slate-50/50 rounded-xl border border-slate-100">
                <div className="min-w-[200px]">
                  <label className="label-text">GST Return</label>
                  <select
                    value={gstForm}
                    onChange={(e) => setGstForm(e.target.value as GSTForm)}
                    className="block w-full pl-4 pr-10 py-3 text-base border border-gray-300 rounded-[4px] shadow-none border border-slate-200-none border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors bg-white"
                  >
                    <option value="GSTR-1">GSTR-1</option>
                    <option value="GSTR-2">GSTR-2</option>
                    <option value="GSTR-2A">GSTR-2A</option>
                    <option value="GSTR-2B">GSTR-2B</option>
                    <option value="GSTR-3B">GSTR-3B</option>
                    <option value="GSTR-4">GSTR-4</option>
                    <option value="GSTR-5">GSTR-5</option>
                    <option value="GSTR-5A">GSTR-5A</option>
                    <option value="GSTR-6">GSTR-6</option>
                    <option value="GSTR-7">GSTR-7</option>
                    <option value="GSTR-8">GSTR-8</option>
                    <option value="GSTR-9">GSTR-9</option>
                    <option value="GSTR-9A">GSTR-9A</option>
                    <option value="GSTR-9C">GSTR-9C</option>
                    <option value="GSTR-10">GSTR-10</option>
                  </select>
                </div>
                <div className="min-w-[200px]">
                  <label htmlFor="gstStartDate" className="label-text">Start Date</label>
                  <DateInput

                    id="gstStartDate"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    className="erp-input"
                  />
                </div>
                <div className="min-w-[200px]">
                  <label htmlFor="gstEndDate" className="label-text">End Date</label>
                  <DateInput

                    id="gstEndDate"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    className="erp-input"
                  />
                </div>
              </div>

              <div className="flex justify-end mb-4">
                <button
                  onClick={() => window.print()}
                  className="erp-button-primary bg-rose-600 hover:bg-rose-700"
                  title="Create PDF"
                >
                  Create PDF
                </button>
              </div>

              {/* Dynamic GST Report Content */}
              <div className="mb-8">
                {renderGSTReport()}
              </div>
            </>
          )}
          {reportType === 'AIReport' && (
            <div className="space-y-6">
              {/* Simple Heading */}
              <h2 className="section-title mb-4">AI Report</h2>

              {/* Simple Input Interface */}
              <div className="bg-white rounded-[4px] border border-gray-200 shadow-none border border-slate-200-none border border-slate-200 p-6">
                <div className="flex items-center gap-3">
                  <input
                    type="text"
                    value={aiInput}
                    onChange={(e) => setAiInput(e.target.value)}
                    onKeyDown={handleAiKeyPress}
                    placeholder="What would you like to know? (e.g., 'Show sales report', 'GST summary', 'Expense analysis')"
                    disabled={aiLoading}
                    className="flex-1 px-5 py-4 border border-gray-300 rounded-[4px] focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors disabled:bg-gray-100 text-base"
                  />
                  <button
                    onClick={handleAiSend}
                    disabled={aiLoading || !aiInput.trim()}
                    className="px-8 py-4 bg-indigo-600 text-white font-semibold rounded-[4px] hover:bg-indigo-700 transition-colors shadow-none border border-slate-200-none border border-slate-200 flex items-center gap-2 disabled:bg-gray-300 disabled:cursor-not-allowed"
                  >
                    {aiLoading ? (
                      <>
                        <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-[4px] animate-spin"></div>
                        Processing...
                      </>
                    ) : (
                      <>
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
                          <path d="M3.478 2.405a.75.75 0 00-.926.94l2.432 7.905H13.5a.75.75 0 010 1.5H4.984l-2.432 7.905a.75.75 0 00.926.94 60.519 60.519 0 0018.445-8.986.75.75 0 000-1.218A60.517 60.517 0 003.478 2.405z" />
                        </svg>
                        Generate
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Report Output Section - Professional Tableau-Style Dashboard */}
              {currentReport && (
                <div className="space-y-5">
                  {/* Clean Professional Header */}
                  <div className="bg-indigo-600 rounded-[4px] p-5 shadow-none border border-slate-200">
                    <div className="flex items-center justify-between flex-wrap gap-4">
                      <div>
                        <h4 className="text-xl font-semibold text-white">{currentReport.title}</h4>
                        <p className="text-blue-100 text-sm mt-1">{currentReport.summary}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <button onClick={() => downloadReportExcel(currentReport)} className="flex items-center gap-2 px-4 py-2 bg-white/10 backdrop-blur-sm text-white text-sm font-medium rounded hover:bg-white/20 transition-colors border border-white/20">
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
                          Excel
                        </button>
                        <button onClick={() => downloadReportPDF(currentReport)} className="flex items-center gap-2 px-4 py-2 bg-white/10 backdrop-blur-sm text-white text-sm font-medium rounded hover:bg-white/20 transition-colors border border-white/20">
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" /></svg>
                          PDF
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* View Toggle Buttons */}
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2 bg-gray-100 rounded-[4px] p-1">
                      <button
                        onClick={() => setReportView('table')}
                        className={`px-4 py-2 rounded-[4px] text-sm font-medium transition-colors ${reportView === 'table'
                          ? 'bg-white text-indigo-600 shadow-none border border-slate-200'
                          : 'text-gray-600 hover:text-gray-900'
                          }`}
                      >
                        <div className="flex items-center gap-2">
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                          </svg>
                          Table View
                        </div>
                      </button>
                      <button
                        onClick={() => setReportView('chart')}
                        className={`px-4 py-2 rounded-[4px] text-sm font-medium transition-colors ${reportView === 'chart'
                          ? 'bg-white text-indigo-600 shadow-none border border-slate-200'
                          : 'text-gray-600 hover:text-gray-900'
                          }`}
                      >
                        <div className="flex items-center gap-2">
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                          </svg>
                          Chart View
                        </div>
                      </button>
                    </div>
                  </div>

                  {/* Conditional View Rendering */}
                  {reportView === 'table' ? (
                    /* Table View */
                    <div className="bg-white border border-gray-200 rounded-[4px] overflow-hidden">
                      <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
                        <h5 className="text-sm font-semibold text-gray-700">Data Table</h5>
                      </div>
                      <div className="overflow-auto max-h-[500px]">
                        <table className="w-full">
                          <thead className="bg-indigo-600 sticky top-0">
                            <tr>{Object.keys(currentReport.tableData[0] || {}).map((h, i) => (<th key={i} className="px-4 py-2.5 text-left text-xs font-semibold text-white uppercase">{h}</th>))}</tr>
                          </thead>
                          <tbody className="divide-y divide-gray-100">{currentReport.tableData.map((row, ri) => (<tr key={ri} className="hover:bg-gray-50">{Object.values(row).map((c, ci) => (<td key={ci} className="px-4 py-3 text-sm text-gray-700">{c as any}</td>))}</tr>))}</tbody>
                        </table>
                      </div>
                    </div>
                  ) : (
                    /* Chart View */
                    <div className="bg-white border border-gray-200 rounded-[4px] overflow-hidden">
                      <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
                        <h5 className="text-sm font-semibold text-gray-700">Chart</h5>
                      </div>
                      <div className="p-6">
                        <div className="h-[400px]">
                          <ResponsiveContainer width="100%" height="100%">
                            {currentReport.chartType === 'pie' ? (
                              <PieChart><Pie data={currentReport.chartData} cx="50%" cy="50%" innerRadius={60} outerRadius={120} dataKey="value" label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}>{currentReport.chartData.map((_, index) => (<Cell key={`cell-${index}`} fill={index === 0 ? '#6366F1' : index === 1 ? '#4F46E5' : index === 2 ? '#818CF8' : index === 3 ? '#A5B4FC' : '#C7D2FE'} />))}</Pie><Tooltip formatter={(value: number) => `₹${value.toLocaleString('en-IN')}`} /></PieChart>
                            ) : currentReport.chartType === 'area' ? (
                              <AreaChart data={currentReport.chartData}><CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" /><XAxis dataKey="name" tick={{ fill: '#6b7280', fontSize: 11 }} axisLine={{ stroke: '#e5e7eb' }} /><YAxis tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`} tick={{ fill: '#6b7280', fontSize: 11 }} axisLine={{ stroke: '#e5e7eb' }} /><Tooltip formatter={(value: number) => `₹${value.toLocaleString('en-IN')}`} /><Area type="monotone" dataKey="value" stroke="#6366F1" fill="#6366F1" fillOpacity={0.2} strokeWidth={2} /></AreaChart>
                            ) : (
                              <BarChart data={currentReport.chartData} barSize={50}><CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" /><XAxis dataKey="name" tick={{ fill: '#6b7280', fontSize: 11 }} axisLine={{ stroke: '#e5e7eb' }} /><YAxis tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`} tick={{ fill: '#6b7280', fontSize: 11 }} axisLine={{ stroke: '#e5e7eb' }} /><Tooltip formatter={(value: number) => `₹${value.toLocaleString('en-IN')}`} cursor={{ fill: 'rgba(99, 102, 241, 0.05)' }} /><Bar dataKey="value" fill="#6366F1" radius={[4, 4, 0, 0]} /></BarChart>
                            )}
                          </ResponsiveContainer>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
          <div className="overflow-x-auto">
            {reportType === 'DayBook' && renderDayBook()}
            {reportType === 'LedgerReport' && (drillDownLedger ? renderLedgerDetail() : renderLedgerSummary())}
            {reportType === 'TrialBalance' && (drillDownLedger ? renderTrialBalanceLedgerDetail() : renderTrialBalance())}
            {reportType === 'StockSummary' && renderStockSummary()}
          </div>
        </div>
      </div>
    </UniversalWorkspaceLayout>
  );
};

export default ReportsPage;
