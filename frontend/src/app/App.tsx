/**
* ============================================================================
* MAIN APPLICATION COMPONENT (App.tsx)
* ============================================================================
* This is the heart of the application. It manages:
* - User authentication (login/logout)
* - Application routing (which page to show)
* - Global state (ledgers, vouchers, stock items, etc.)
* - Data synchronization with backend API
* - AI features (invoice extraction, AI agent)
* 
* ARCHITECTURE:
* - Uses React hooks for state management (useState, useEffect, useCallback)
* - Communicates with Django backend via REST API
* - Stores authentication tokens in HttpOnly cookies (secure)
* - Supports multi-tenancy (each company has isolated data)
* 
* FOR NEW DEVELOPERS:
* - Start by understanding the state variables (lines 80-115)
* - Then review the data handlers (lines 437-835)
* - Finally, look at the render logic (lines 840-973)
*/

// ============================================================================
// REACT IMPORTS
// ============================================================================
// Import core React functionality
import React, { useState, useEffect, useMemo, useCallback, useRef, Suspense } from 'react';
// Import TypeScript types for type safety
// These define the shape of our data structures (see ../types/types.ts)
import type { Page, Ledger, Voucher, ExtractedInvoiceData, CompanyDetails, LedgerGroupMaster, SalesPurchaseVoucher, StockItem } from '../types';
import { ChevronDown } from 'lucide-react';

// ============================================================================
// COMPONENT IMPORTS
// ============================================================================

// Page Components - Essential ones are static for instant entry
import DashboardPage from '../pages/Dashboard';
const MastersPage = React.lazy(() => import('../pages/Masters'));
const InventoryPage = React.lazy(() => import('../pages/Inventory'));
const VouchersPage = React.lazy(() => import('../pages/Vouchers'));
const ReportsPage = React.lazy(() => import('../pages/Reports'));
const SettingsPage = React.lazy(() => import('../pages/Settings'));
const UsersAndRolesPage = React.lazy(() => import('../pages/UsersAndRoles'));
const PendingPurchasesPage = React.lazy(() => import('../pages/PendingPurchases/PendingPurchases'));
const VendorPortalPage = React.lazy(() => import('../pages/VendorPortal'));
const CustomerPortalPage = React.lazy(() => import('../pages/CustomerPortal'));
const PayrollPage = React.lazy(() => import('../pages/Payroll'));
const ServicePage = React.lazy(() => import('../pages/Service'));
const GSTPage = React.lazy(() => import('../pages/GST'));
const DashboardBuilderPage = React.lazy(() => import('../pages/DashboardBuilder'));

// Auth Pages - Static imports for instant first-paint
import LoginPage from '../pages/Login';
const ForgotPasswordPage = React.lazy(() => import('../pages/Login').then(m => ({ default: m.ForgotPassword })));
const SignupPage = React.lazy(() => import('../pages/Register'));
import MasterDashboardPage from '../pages/MasterDashboard/MasterDashboard';
import MasterLoginPage from '../pages/MasterDashboard/MasterLogin';
import AuthPortalPage from '../pages/AuthPortal/AuthPortal';

// Shared UI Components
import Sidebar from '../components/Sidebar';  // Left navigation sidebar
import MasterSidebar, { MasterPage } from '../components/MasterSidebar';
import MasterHeader from '../components/MasterHeader';
import Modal from '../components/Modal';                  // Reusable modal dialog

import FloatingCalculator from '../components/FloatingCalculator';
import FloatingCalendar from '../components/FloatingCalendar';
import FloatingNotes from '../components/FloatingNotes';
import { KikiPanel } from '../components/kiki';
import Icon from '../components/Icon';                    // Icon component
import ErrorBoundary from '../components/ErrorBoundary';  // Error handling wrapper
import { showError, showSuccess } from '../utils/toast';
import VendorViewModal from '../components/VendorViewModal';
import CustomerViewModal from '../pages/CustomerPortal/CustomerViewModal';


// Import assets


// ============================================================================
// SERVICE IMPORTS
// ============================================================================
// AI Services - Google Gemini integration for invoice extraction and AI agent
import { extractInvoiceDataWithRetry } from '../services/geminiService';

// API Service - Handles all HTTP requests to Django backend
import { apiService, httpClient } from '../services';
import {
  hasStoredSession, hasMasterSession, hasCompanySession,
  clearTenantContext, getAccessToken,
  setMasterTokens, setCompanyTokens
} from '../services/authService';
import { getUserTypeFromToken, isTokenExpired } from '../services/jwtUtils';

// Initial Data - Default data for new companies (fallback if backend is empty)
import { initialLedgers, initialLedgerGroups } from '../store/initialData';
import { initialVouchers } from '../store/initialVouchers';

// ============================================================================
// CONFIGURATION
// ============================================================================
// API Base URL - Read from environment variable or use default
// In production, set VITE_API_URL in .env file
const API_BASE = (import.meta as any).env?.VITE_API_URL || 'http://localhost:5003';

// Default company details - Used for new companies or as fallback
// This includes default voucher numbering configuration
const defaultCompanyDetails: CompanyDetails = {
  name: 'Your Company', address: '', gstin: '', state: 'Maharashtra',
  logo: '', email: '', phone: '', website: '', pan: '', cin: '',
  voucherNumbering: {
    Sales: { autoIncrement: true, prefix: 'INV-', nextNumber: 1, width: 4, suffix: '/24-25' },
    Purchase: { autoIncrement: true, prefix: 'PO-', nextNumber: 1, width: 4, suffix: '/24-25' }
  }
};

declare global {
  interface Window {
    showGlobalVendorView?: (id: number) => void;
    showGlobalCustomerView?: (customerOrId: any) => void;
  }
}

// ============================================================================
// MAIN APP COMPONENT
// ============================================================================
const App: React.FC = () => {
  // Global View Modal states
  const [globalVendorId, setGlobalVendorId] = useState<number | null>(null);
  const [globalCustomer, setGlobalCustomer] = useState<any | null>(null);
  const [isToolsDropdownOpen, setIsToolsDropdownOpen] = useState(false);
  const toolsDropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleOutsideClick = (event: MouseEvent) => {
      if (toolsDropdownRef.current && !toolsDropdownRef.current.contains(event.target as Node)) {
        setIsToolsDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleOutsideClick);
    return () => {
      document.removeEventListener('mousedown', handleOutsideClick);
    };
  }, []);

  useEffect(() => {
    window.showGlobalVendorView = (id: number) => {
      setGlobalVendorId(id);
    };
    window.showGlobalCustomerView = (customerOrId: any) => {
      setGlobalCustomer(customerOrId);
    };
    return () => {
      window.showGlobalVendorView = undefined;
      window.showGlobalCustomerView = undefined;
    };
  }, []);

  // ============================================================================
  // HELPER FUNCTIONS
  // ============================================================================

  /**
   * Get feature limits based on user's subscription plan
   * Plans: Basic, Pro, Enterprise
   * Returns: Object with feature flags and limits
   */
  const getPlanLimits = (plan?: string) => {
    const plans: Record<string, any> = {
      'Free': {
        maxUploads: 5,
        hasAI: false,
        hasReports: true,
        hasSettings: true,
        hasMultipleCompanies: false,
        hasAdvancedFeatures: false
      },
      'Starter': {
        maxUploads: 100,
        hasAI: true,
        hasReports: true,
        hasSettings: true,
        hasMultipleCompanies: true,
        hasAdvancedFeatures: false
      },
      'Pro': {
        maxUploads: 999999, // Unlimited
        hasAI: true,
        hasReports: true,
        hasSettings: true,
        hasMultipleCompanies: true,
        hasAdvancedFeatures: true
      }
    };

    // Map legacy names to new names and handle casing
    let activePlan = plan || 'Free';
    // Normalize casing (e.e.g., 'FREE' -> 'Free', 'STARTER' -> 'Starter')
    if (activePlan.toUpperCase() === 'FREE') activePlan = 'Free';
    if (activePlan.toUpperCase() === 'STARTER' || activePlan === 'Basic') activePlan = 'Starter';
    if (activePlan.toUpperCase() === 'PRO' || activePlan === 'Enterprise') activePlan = 'Pro';

    return plans[activePlan] || plans['Free'];
  };

  /**
   * Get the user's subscription plan from sessionStorage
   * Used to determine which features are available
   * Returns: 'Free', 'Starter', or 'Pro'
   */
  const getUserPlan = () => {
    // Try to get plan from user data stored in sessionStorage first, then fallback to localStorage for migration
    const userPlan = sessionStorage.getItem('userPlan') || localStorage.getItem('userPlan');
    return userPlan;
  };

  // ============================================================================
  // STATE VARIABLES - Authentication & UI
  // ============================================================================

  // Authentication state - tracks if user is logged in
  const [isLoggedIn, setIsLoggedIn] = useState<boolean>(false);
  const [isAuthenticating, setIsAuthenticating] = useState<boolean>(() => hasStoredSession());
  const [isDataLoaded, setIsDataLoaded] = useState(false);

  // Router state
  const [viewVoucherData, setViewVoucherData] = useState<any>(null);
  const [vouchersNavParams, setVouchersNavParams] = useState<any>(null);
  const [reportsNavParams, setReportsNavParams] = useState<any>(null);
  const [gstNavParams, setGstNavParams] = useState<any>(null);
  const [inventoryNavParams, setInventoryNavParams] = useState<any>(null);
  const [mastersNavParams, setMastersNavParams] = useState<any>(null);
  const [settingsNavParams, setSettingsNavParams] = useState<any>(null);
  const [usersNavParams, setUsersNavParams] = useState<any>(null);
  const [vendorNavParams, setVendorNavParams] = useState<any>(null);
  const [customerNavParams, setCustomerNavParams] = useState<any>(null);
  const [serviceNavParams, setServiceNavParams] = useState<any>(null);

  const [currentPath, setCurrentPath] = useState(window.location.pathname);
  const [currentPage, setCurrentPage] = useState<Page | MasterPage | 'BranchDetail'>('Dashboard');
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const toggleSidebar = () => setIsSidebarOpen(!isSidebarOpen);
  const [isHeaderCollapsed, setIsHeaderCollapsed] = useState(false);

  const isMasterMode = useMemo(() => {
    return hasMasterSession() && currentPath.startsWith('/master');
  }, [currentPath]);

  // User permissions - No longer used (RBAC removed)
  // const [permissions, setPermissions] = useState<string[]>([]);

  // ============================================================================
  // STATE VARIABLES - Business Data (In-Memory Database)
  // ============================================================================
  // These store the main business data loaded from the backend
  // All data is tenant-specific (isolated per company)

  // Company information (name, address, GST, etc.)
  const [companyDetails, setCompanyDetails] = useState<CompanyDetails>(() => {
    const saved = sessionStorage.getItem('companyName') || localStorage.getItem('companyName');
    return saved ? { ...defaultCompanyDetails, name: saved } : defaultCompanyDetails;
  });

  // Chart of Accounts - individual ledger accounts (Cash, Bank, Sales, etc.)
  const [ledgers, setLedgers] = useState<Ledger[]>([]);

  // Ledger Groups - hierarchical grouping of ledgers (Assets, Liabilities, etc.)
  const [ledgerGroups, setLedgerGroups] = useState<LedgerGroupMaster[]>([]);

  // Vouchers - all transactions (sales, purchase, payment, receipt, etc.)
  const [vouchers, setVouchers] = useState<Voucher[]>([]);

  // Journal Entries - the double-entry source of truth for reports
  const [journalEntries, setJournalEntries] = useState<any[]>([]);

  // RICH DATA for AI Agency (Emails, Phones, etc.)
  const [richVendors, setRichVendors] = useState<any[]>([]);
  const [richCustomers, setRichCustomers] = useState<any[]>([]);

  // Database Schema (for AI "Table Knowledge")
  const [userTables, setUserTables] = useState<any[]>([]);

  // Stock Items - inventory items for sales/purchase
  const [stockItems, setStockItems] = useState<StockItem[]>([]);
  const [entries, setEntries] = useState<any[]>([]);


  // ============================================================================
  // STATE VARIABLES - AI Features
  // ============================================================================

  // AI invoice extraction loading state
  const [isLoading, setIsLoading] = useState(false);

  // Error message display
  const [error, setError] = useState<string | null>(null);

  // Prefilled voucher data from AI invoice extraction
  const [prefilledVoucherData, setPrefilledVoucherData] = useState<ExtractedInvoiceData | null>(null);

  // Import summary - shows success/failure count after bulk import
  const [importSummary, setImportSummary] = useState<{ success: number, failed: number } | null>(null);

  // Deactivation modal - shown when user account is deactivated
  const [showDeactivationModal, setShowDeactivationModal] = useState(false);

  // Drill-down voucher viewing state

  const handleClearViewVoucherData = useCallback(() => {
    setViewVoucherData(null);
  }, []);

  // ============================================================================
  // NAVIGATION HANDLER
  // ============================================================================

  /**
   * Handle page navigation
   * Called when user clicks on sidebar menu items
   */

  const handleNavigate = useCallback((page: Page, params?: any) => {
    setCurrentPage(page);
    window.history.pushState(null, '', `?page=${page.replace(/\s+/g, '')}`);

    if (page === 'Vouchers') {
      if (params?.viewVoucher) {
        setViewVoucherData(params.viewVoucher);
      }
      setVouchersNavParams(params);
    } else {
      if (!params || !params.preserveVoucherState) {
        setViewVoucherData(null);
        setVouchersNavParams(null);
      }
    }

    setReportsNavParams(page === 'Reports' ? params : null);
    setGstNavParams(page === 'GST' ? params : null);
    setInventoryNavParams(page === 'Inventory' ? params : null);
    setMastersNavParams(page === 'Masters' ? params : null);
    setSettingsNavParams(page === 'Settings' ? params : null);
    setUsersNavParams(page === 'Users & Roles' ? params : null);
    setVendorNavParams(page === 'Vendor Portal' ? params : null);
    setCustomerNavParams(page === 'Customer Portal' ? params : null);
    setServiceNavParams(page === 'Service' ? params : null);
  }, []);

  // Handle logout: clear all session data and redirect to login
  const handleLogout = useCallback(async () => {
    try {
      await apiService.logout();
    } catch (error) {
      console.error('Error during logout:', error);
    } finally {
      // Clear all session and local storage related to auth and tenant data
      sessionStorage.clear();
      localStorage.clear();
      httpClient.clearAuthData(); // Clears BOTH master and company token slots
      setIsLoggedIn(false);
      setIsDataLoaded(false);
      setLedgers([]);
      setLedgerGroups([]);
      setVouchers([]);
      setStockItems([]);
      setRichVendors([]);
      setRichCustomers([]);
      setCompanyDetails(defaultCompanyDetails);
      // Redirect to domain-appropriate login
      const isMasterPath = window.location.pathname.startsWith('/master');
      const loginPath = isMasterPath ? '/master/login' : '/login';
      window.history.pushState({}, '', loginPath);
      setCurrentPath(loginPath);
      showSuccess('You have been successfully logged out.');
    }
  }, []); // Removed clearTenantCache from dependency array as it's not defined here

  // Load cached tenant data - DATA CACHING DISABLED FOR PRODUCTION
  const loadCachedData = useCallback((tenantId: string) => {
    // We intentionally return false to force loading from the API.
    // This prevents stale data and storage limit issues (5MB limit).
    return false;
  }, []);

  // Cache tenant data - DISABLED FOR PRODUCTION
  const cacheTenantData = useCallback((tenantId: string, data: any) => {
    // No-op: Do not save data to localStorage.
    // This protects against XSS (reading plain text data) and storage quotas.
  }, []);

  // Clear all tenant cache data
  const clearTenantCache = useCallback(() => {
    try {
      // Get all localStorage keys
      const keys = Object.keys(localStorage);
      // Filter keys that start with 'tenant_'
      const tenantKeys = keys.filter(key => key.startsWith('tenant_'));
      // Remove all tenant cache keys
      tenantKeys.forEach(key => localStorage.removeItem(key));
    } catch (error) {

    }
  }, []);

  // Load tenant-scoped data from backend after login
  const loadTenantData = useCallback(async (tenantId?: string) => {
    try {
      setIsDataLoaded(false);

      // Check if user is admin (tenantId is null)
      const isAdmin = tenantId === null || tenantId === undefined;

      // Try to load from cache first
      const hasCachedData = tenantId ? loadCachedData(tenantId) : false;

      const [
        backendCompanyDetails,
        backendLedgers,
        backendLedgerGroups,
        backendVouchers,
        backendJournalEntries,
        backendStockItems,
        backendRichVendors,
        backendRichCustomers
      ] = await Promise.all([

        apiService.getCompanyDetails().catch(() => defaultCompanyDetails),
        apiService.getLedgers().catch(() => []),
        apiService.getLedgerGroups().catch(() => []),
        apiService.getVouchers().catch(() => []),
        apiService.getJournalEntries().catch(() => []),
        apiService.getStockItems().catch(() => []),
        apiService.getRichVendors().catch(() => []),
        apiService.getRichCustomers().catch(() => [])
      ]);


      // Update state with tenant data
      const newData = {
        companyDetails: backendCompanyDetails && typeof backendCompanyDetails === 'object' ? backendCompanyDetails : defaultCompanyDetails,
        ledgers: Array.isArray(backendLedgers) ? backendLedgers : [],
        ledgerGroups: Array.isArray(backendLedgerGroups) ? backendLedgerGroups : [],
        vouchers: Array.isArray(backendVouchers) ? backendVouchers : [],
        journalEntries: Array.isArray(backendJournalEntries) ? backendJournalEntries : [],
        stockItems: Array.isArray(backendStockItems) ? backendStockItems : [],
        richVendors: Array.isArray(backendRichVendors) ? backendRichVendors : [],
        richCustomers: Array.isArray(backendRichCustomers) ? backendRichCustomers : []
      };


      if (newData.companyDetails) {
        setCompanyDetails(prev => ({ ...prev, ...newData.companyDetails }));
      }
      setLedgers(newData.ledgers);
      setLedgerGroups(newData.ledgerGroups);
      setVouchers(newData.vouchers);
      setJournalEntries(newData.journalEntries);
      setStockItems(newData.stockItems);
      setRichVendors(newData.richVendors);
      setRichCustomers(newData.richCustomers);


      // Cache the data if we have a tenant ID
      if (tenantId) {
        cacheTenantData(tenantId, newData);
      }

    } catch (error) {
      console.error('❌ Failed to load tenant data:', error);
      // Keep cached data on error if available
    } finally {
      setIsDataLoaded(true);
    }
  }, [loadCachedData, cacheTenantData]);

  // Map URL page parameter slugs to Page enum names
  const mapPageSlugToPageName = useCallback((rawParam: string): Page => {
    const normalized = rawParam.trim().toLowerCase().replace(/_/g, '-');
    switch (normalized) {
      case 'dashboard': return 'Dashboard';
      case 'masters':
      case 'ledgers':
      case 'ledger': return 'Masters';
      case 'inventory': return 'Inventory';
      case 'vouchers':
      case 'voucher': return 'Vouchers';
      case 'vendor-portal':
      case 'vendor_portal':
      case 'vendor': return 'Vendor Portal';
      case 'customer-portal':
      case 'customer_portal':
      case 'customer': return 'Customer Portal';
      case 'reports':
      case 'report': return 'Reports';
      case 'settings': return 'Settings';
      case 'users':
      case 'users-roles':
      case 'users_roles':
      case 'users & roles': return 'Users & Roles';
      case 'pending-purchases':
      case 'pending_purchases': return 'Pending Purchases';
      case 'payroll': return 'Payroll';
      case 'service': return 'Service';
      case 'gst': return 'GST';
      case 'dashboard-builder':
      case 'dashboard_builder': return 'Dashboard Builder';
      default:
        const validPages: Page[] = ['Dashboard', 'Masters', 'Inventory', 'Vouchers', 'Vendor Portal', 'Customer Portal', 'Reports', 'Settings', 'Users & Roles', 'Pending Purchases', 'Payroll', 'Service', 'GST', 'Dashboard Builder'];
        const titleMatch = validPages.find(p => p.toLowerCase() === rawParam.toLowerCase());
        return titleMatch || (rawParam as Page);
    }
  }, []);

  // Handle URL query parameters and path-based routing
  useEffect(() => {
    const handleLocationChange = () => {
      setCurrentPath(window.location.pathname);
      const params = new URLSearchParams(window.location.search);
      const pageParam = params.get('page');
      if (pageParam) {
        setCurrentPage(mapPageSlugToPageName(pageParam));
      } else if (window.location.pathname === '/dashboard') {
        setCurrentPage('Dashboard');
      }
    };

    // Listen for browser back/forward buttons
    window.addEventListener('popstate', handleLocationChange);

    const params = new URLSearchParams(window.location.search);

    // Page navigation
    const pageParam = params.get('page');
    if (pageParam) {
      setCurrentPage(mapPageSlugToPageName(pageParam));
    }

    return () => window.removeEventListener('popstate', handleLocationChange);
  }, [mapPageSlugToPageName]);


  // Synchronize currentPage state to URL query parameter
  useEffect(() => {
    const isMasterPath = currentPath.startsWith('/master');
    const isAuthPath =
      currentPath === '/login' ||
      currentPath === '/signup' ||
      currentPath === '/forgot-password' ||
      currentPath === '/master/login' ||
      currentPath === '/master/register' ||
      currentPath === '/auth' ||
      currentPath === '/login/business' ||
      currentPath === '/register';

    if (isLoggedIn && !isMasterPath && !isAuthPath) {
      const url = new URL(window.location.href);
      const currentPageInUrl = url.searchParams.get('page');
      if (currentPageInUrl !== currentPage) {
        url.searchParams.set('page', currentPage);
        window.history.pushState({}, '', url.pathname + url.search);
      }
    }
  }, [currentPage, isLoggedIn, currentPath]);



  // MAIN INITIALIZATION — JWT-driven domain routing
  useEffect(() => {
    const initializeApp = async () => {
      // Check for tokens using user-requested priority (Master > Company)
      const masterToken = localStorage.getItem('master_token');
      const companyToken = localStorage.getItem('company_token');

      if (!masterToken && !companyToken) {
        setIsAuthenticating(false);
        setIsDataLoaded(true);
        // Priority 6: If no tokens, redirect to /login
        if (window.location.pathname === '/' || window.location.pathname === '/master') {
          window.history.replaceState({}, '', '/login');
          setCurrentPath('/login');
        }
        return;
      }

      const timeoutId = setTimeout(() => {
        if (!isDataLoaded) {
          console.warn('⚠️ Initialization timeout: Forcing data loaded state.');
          setIsDataLoaded(true);
          setIsAuthenticating(false);
        }
      }, 5000);

      try {
        console.log('🚀 App: Initializing...');
        // 1. Validate Session with Backend
        const userData = await apiService.getCurrentUser();
        console.log('✅ App: Session validated.', userData?.username);

        if (!userData) {
          throw new Error('Invalid user session');
        }

        const isMaster = userData.is_master;

        if (isMaster) {
          console.log('👑 App: Master context detected.');
          clearTenantContext();
          setIsLoggedIn(true);

          if (window.location.pathname === '/') {
            window.history.replaceState({}, '', '/master/dashboard');
            setCurrentPath('/master/dashboard');
          }
        } else {
          console.log('🏢 App: Business context detected.');
          // Restore Business User Context
          const tenantId = userData.tenant_id;
          if (tenantId) {
            sessionStorage.setItem('tenantId', tenantId);
            localStorage.setItem('tenantId', tenantId);
          }

          if (userData.company_name) {
            sessionStorage.setItem('companyName', userData.company_name);
            localStorage.setItem('companyName', userData.company_name);
          }

          // Parallel load application data
          console.log('📥 App: Syncing background data...');
          await Promise.all([
            apiService.getMyPermissions().catch(() => null),
            tenantId ? loadTenantData(tenantId) : Promise.resolve(),
          ]);

          setIsLoggedIn(true);

          if (window.location.pathname === '/') {
            window.history.replaceState({}, '', '/dashboard');
            setCurrentPath('/dashboard');
          }
        }
      } catch (err: any) {
        console.warn('⚠️ App: Initialization failed (Session Invalid):', err.message || 'Unknown error');
        handleLogout();
      } finally {
        clearTimeout(timeoutId);
        setIsAuthenticating(false);
        setIsDataLoaded(true);
        console.log('✨ App: Initialization complete.');
      }
    };

    initializeApp();
  }, [loadTenantData, handleLogout]);



  // Handle login: JWT-driven domain detection
  const handleLogin = useCallback(async (payload: any) => {
    try {
      // Get the JWT access token from the response — this is the ground truth
      const accessToken = payload?.access;
      const refreshToken = payload?.refresh;
      const domain = getUserTypeFromToken(accessToken);

      // Persist tokens to storage immediately
      if (domain === 'master') {
        setMasterTokens(accessToken, refreshToken);
        clearTenantContext(); // Master never has tenant context
      } else {
        setCompanyTokens(accessToken, refreshToken);
      }

      sessionStorage.removeItem('loggedOut');
      localStorage.removeItem('loggedOut');

      setIsLoggedIn(true);

      if (domain === 'master') {
        // ── MASTER DOMAIN ─────────────────────────────────────
        // Never load tenant data for master
        const dashboardPath = '/master/dashboard';
        window.history.pushState({}, '', dashboardPath);
        setCurrentPath(dashboardPath);
      } else {
        // ── COMPANY DOMAIN ────────────────────────────────────
        const user = payload?.user || payload;
        const tenantId = user?.tenant_id || user?.tenantId || null;

        if (tenantId) sessionStorage.setItem('tenantId', tenantId);
        const companyName = user?.company_name || user?.companyName || 'Your Company';
        sessionStorage.setItem('companyName', companyName);
        setCompanyDetails(prev => ({ ...prev, name: companyName }));

        const plan = user?.selected_plan || user?.selectedPlan || 'Free';
        sessionStorage.setItem('userPlan', plan);

        window.history.pushState({}, '', '/dashboard');
        setCurrentPath('/dashboard');

        if (tenantId) await loadTenantData(tenantId);
      }

      const displayName = payload?.user?.username || payload?.username || 'User';
      const cap = displayName.charAt(0).toUpperCase() + displayName.slice(1);
      showSuccess(
        `Stay driven, stay focused, and let's turn your vision into reality today.`,
        `Welcome back, ${cap}! ✨`,
        6000
      );
    } catch (err) {
      console.error('Login handler error:', err);
    }
  }, [loadTenantData]);


  // Check user active status frequently when logged in (exclude admin users)
  // DISABLED: This was causing 401 errors when cookies expired
  // The deactivation check can be re-enabled later with proper session management
  useEffect(() => {
    // Disabled for now to prevent 401 errors
    return;

    /* Original code - disabled */
    if (!isLoggedIn) return;

    const tenantId = sessionStorage.getItem('tenantId') || localStorage.getItem('tenantId');

    // Don't check status for admin users (they can't be deactivated)
    if (!tenantId) return;

    /* Original code - disabled
    if (!isLoggedIn) return;

    const tenantId = sessionStorage.getItem('tenantId') || localStorage.getItem('tenantId');

    // Don't check status for admin users (they can't be deactivated)
    if (!tenantId) return;

    const checkUserStatus = async () => {
      try {
        // Only check if we have authentication cookies
        const statusResponse = await apiService.checkUserStatus();
        if (!statusResponse.isActive) {
          // User has been deactivated
          setShowDeactivationModal(true);
          setTimeout(() => {
            handleLogout();
            setShowDeactivationModal(false);
          }, 3000); // Show modal for 3 seconds then logout (faster)
        }
      } catch (error: any) {}
    };

    // Check immediately, then every 5 seconds when online
    checkUserStatus();
    const statusInterval = setInterval(checkUserStatus, 5000); // More frequent checks

    return () => clearInterval(statusInterval);
    */
  }, [isLoggedIn, handleLogout]);


  // --- Data mutation handlers --- (all include Authorization header when token present)
  const handleAddLedger = useCallback(async (ledger: Ledger) => {
    try {
      const response = await apiService.saveLedger(ledger);
      if (response && response.id) {
        // Preserve backend table order (no client-side alphabetical sorting).
        setLedgers(prev => [...prev, response]);
        const savedName = response.ledger_type || response.name || 'Ledger entry';
        showSuccess(`Ledger "${savedName}" saved successfully.`);
      } else {
        console.error(`Failed to save ledger ${ledger.name}: No ID in response`, response);
        showError(`Failed to save ledger "${ledger.name}". Please try again.`);
      }
    } catch (err: any) {
      console.error(`Error saving ledger ${ledger.name}:`, err);
      const detail = err?.response?.data
        ? JSON.stringify(err.response.data)
        : (err?.message || 'Unknown error');
      showError(`Failed to save ledger "${ledger.name}": ${detail}`);
    }
  }, []);


  const handleUpdateLedger = useCallback(async (idOrName: number | string, ledger: Partial<Ledger>) => {
    try {
      // If it's a number, use it as ID. Otherwise, find by name
      const ledgerId = typeof idOrName === 'number' ? idOrName : ledgers.find(l => l.name === idOrName)?.id;

      if (ledgerId) {
        const response = await apiService.updateLedger(ledgerId, ledger);
        if (response && (response as any).id) {
          // Preserve backend order; replace in place.
          setLedgers(prev => prev.map(l => l.id === ledgerId ? response : l));
        } else {
          // Fallback: optimistic local merge if backend response shape changes.
          setLedgers(prev => prev.map(l => l.id === ledgerId ? { ...l, ...ledger } : l));
        }
      } else {
        // Fallback: update by name if no ID available

        setLedgers(prev => prev.map(l => l.name === idOrName ? { ...l, ...ledger } : l));
      }
    } catch (err) {
      console.error(`Error updating ledger ${idOrName}:`);
      showError('Failed to update ledger. Please try again.');
    }
  }, [ledgers]);

  const handleDeleteLedger = useCallback(async (idOrName: number | string) => {
    try {
      // If it's a number, use it as ID. Otherwise, find by name
      const ledgerId = typeof idOrName === 'number' ? idOrName : ledgers.find(l => l.name === idOrName)?.id;

      if (ledgerId) {
        await apiService.deleteLedger(ledgerId);

        setLedgers(prev => prev.filter(l => l.id !== ledgerId));
      } else {
        // Fallback: delete by name if no ID available

        setLedgers(prev => prev.filter(l => l.name !== idOrName));
      }
    } catch (err) {
      console.error(`Error deleting ledger ${idOrName}:`);
      showError('Failed to delete ledger. Please try again.');
    }
  }, [ledgers]);

  const handleAddLedgerGroup = useCallback(async (group: LedgerGroupMaster) => {
    try {
      const response = await apiService.saveLedgerGroup(group);
      if (response && response.id) {

        setLedgerGroups(prev => [...prev, response].sort((a, b) => a.name.localeCompare(b.name)));
      } else {
        console.error(`Failed to save ledger group ${group.name}`);
        setLedgerGroups(prev => [...prev, group].sort((a, b) => a.name.localeCompare(b.name)));
      }
    } catch (err) {
      console.error(`Error saving ledger group ${group.name}:`);
      setLedgerGroups(prev => [...prev, group].sort((a, b) => a.name.localeCompare(b.name)));
    }
  }, []);

  const handleUpdateLedgerGroup = useCallback(async (idOrName: number | string, group: Partial<LedgerGroupMaster>) => {
    try {
      const groupId = typeof idOrName === 'number' ? idOrName : ledgerGroups.find(g => g.name === idOrName)?.id;

      if (groupId) {
        const response = await apiService.updateLedgerGroup(groupId, group);
        if (response.success) {

          setLedgerGroups(prev => prev.map(g => g.id === groupId ? { ...g, ...group } : g).sort((a, b) => a.name.localeCompare(b.name)));
        }
      } else {

        setLedgerGroups(prev => prev.map(g => g.name === idOrName ? { ...g, ...group } : g).sort((a, b) => a.name.localeCompare(b.name)));
      }
    } catch (err) {
      console.error(`Error updating ledger group ${idOrName}:`);
      showError('Failed to update group. Please try again.');
    }
  }, [ledgerGroups]);

  const handleDeleteLedgerGroup = useCallback(async (idOrName: number | string) => {
    try {
      const groupId = typeof idOrName === 'number' ? idOrName : ledgerGroups.find(g => g.name === idOrName)?.id;

      if (groupId) {
        await apiService.deleteLedgerGroup(groupId);

        setLedgerGroups(prev => prev.filter(g => g.id !== groupId));
      } else {

        setLedgerGroups(prev => prev.filter(g => g.name !== idOrName));
      }
    } catch (err) {
      console.error(`Error deleting ledger group ${idOrName}:`);
      showError('Failed to delete group. Please try again.');
    }
  }, [ledgerGroups]);



  const handleAddVouchers = useCallback(async (vouchersToAdd: Voucher[], saveToMySQL: boolean = true) => {
    const newVouchers = vouchersToAdd.map(v => ({ ...v, id: v.id || new Date().toISOString() + Math.random() }));

    // Handle auto-incrementing voucher numbers
    let newCompanyDetails = { ...companyDetails };
    let detailsChanged = false;

    newVouchers.forEach(v => {
      if (v.type === 'Sales' || v.type === 'Purchase') {
        const config = newCompanyDetails.voucherNumbering?.[v.type];
        if (config?.autoIncrement) {
          const paddedNumber = String(config.nextNumber).padStart(config.width || 0, '0');
          const expectedInvoiceNo = `${config.prefix || ''}${paddedNumber}${config.suffix || ''}`;
          if (v.invoiceNo === expectedInvoiceNo) {
            config.nextNumber++;
            detailsChanged = true;
          }
        }
      }
    });

    if (detailsChanged) setCompanyDetails(newCompanyDetails);

    if (saveToMySQL) {

      try {
        await apiService.saveVouchers(newVouchers);

      } catch (err) {
        console.error(`Error saving vouchers to backend:`);
      }
    } else {

    }

    setVouchers(prev => {
      const updatedMap = new Map(prev.map(v => [String(v.id || (v as any).reference_id || (v as any).referenceId), v]));
      newVouchers.forEach(nv => {
        updatedMap.set(String(nv.id || (nv as any).reference_id || (nv as any).referenceId), nv);
      });
      return Array.from(updatedMap.values())
        .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
    });

    // Fire a background refetch to guarantee the Daybook is 100% in sync with the DB
    if (!saveToMySQL) {
      setTimeout(() => {
        apiService.getVouchers().then(v => {
          if (v && v.length > 0) setVouchers(v);
        }).catch(console.error);
      }, 500);
    }
  }, [companyDetails]);

  const handleUpdateVoucher = useCallback(async (updatedVoucher: Voucher) => {
    try {
      await apiService.saveVouchers([updatedVoucher]);

    } catch (err) {
      console.error(`Error updating voucher ${updatedVoucher.id} in backend:`);
    }

    setVouchers(prevVouchers => prevVouchers.map(v =>
      (v.id === updatedVoucher.id || (v as any).reference_id === updatedVoucher.id || (v as any).referenceId === updatedVoucher.id || v.id === (updatedVoucher as any).reference_id || v.id === (updatedVoucher as any).referenceId) ? updatedVoucher : v
    ));

    // Guarantee sync
    setTimeout(() => {
      apiService.getVouchers().then(v => {
        if (v && v.length > 0) setVouchers(v);
      }).catch(console.error);
    }, 500);
  }, []);

  const handleMassUploadComplete = useCallback(async (vouchersToCreate: Voucher[]) => {
    try {

      const createdVouchers = vouchersToCreate.map(v => ({ ...v, id: v.id || new Date().toISOString() + Math.random() }));


      try {
        await apiService.saveVouchers(createdVouchers);

      } catch (err) {
        console.error(`Error saving vouchers to backend:`);
      }

      setVouchers(prev => [...prev, ...createdVouchers].sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()));
      setImportSummary({ success: createdVouchers.length, failed: 0 });
      setCurrentPage('Vouchers');
    } catch (err) {
      console.error('Mass upload save error:');
      setError('Failed to save mass uploaded vouchers');
    }
  }, []);

  const buildPrefilledDataFromVoucher = useCallback((voucher: Voucher): (ExtractedInvoiceData & { voucherType?: string; igstAmount?: number }) | null => {
    if (voucher.type === 'Purchase' || voucher.type === 'Sales' || voucher.type === 'Credit Note' || voucher.type === 'Debit Note') {
      const sp = voucher as SalesPurchaseVoucher;
      return {
        sellerName: sp.party || '',
        invoiceNumber: sp.invoiceNo || '',
        invoiceDate: sp.date || '',
        subtotal: Number(sp.totalTaxableAmount || 0),
        cgstAmount: Number(sp.totalCgst || 0),
        sgstAmount: Number(sp.totalSgst || 0),
        igstAmount: Number((sp as any).totalIgst || 0),
        totalAmount: Number(sp.total || 0),
        lineItems: (sp.items || []).map(item => ({
          itemDescription: item.name || '',
          hsnCode: '',
          quantity: Number(item.qty || 0),
          rate: Number(item.rate || 0),
          amount: Number(item.totalAmount || 0),
        })),
        voucherType: sp.type,
      };
    }

    if (voucher.type === 'Payment' || voucher.type === 'Receipt') {
      const pr = voucher as any;
      return {
        sellerName: pr.party || '',
        invoiceNumber: '',
        invoiceDate: pr.date || '',
        subtotal: Number(pr.amount || 0),
        cgstAmount: 0,
        sgstAmount: 0,
        igstAmount: 0,
        totalAmount: Number(pr.amount || 0),
        lineItems: [],
        voucherType: pr.type,
      };
    }

    return null;
  }, []);

  const handleInvoiceUpload = useCallback(async (file: File, voucherType?: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const extractedData = await extractInvoiceDataWithRetry(file);
      const updatedExtractedData = { ...extractedData, voucherType: voucherType || 'Purchase' };
      setPrefilledVoucherData(updatedExtractedData);
      // Removed import summary modal - extracting data is not the same as saving it.
      // setImportSummary({ success: 1, failed: 0 });
      setCurrentPage('Vouchers');
    } catch (err) {
      console.error('Invoice upload error:');
      setError(err instanceof Error ? err.message : 'An unknown error occurred during AI extraction.');
    } finally {
      setIsLoading(false);
    }
  }, [vouchers.length, getUserPlan, getPlanLimits]);



  const clearPrefilledData = useCallback(() => setPrefilledVoucherData(null), []);

  const handleSaveSettings = useCallback(async (details: CompanyDetails) => {
    try {
      const response = await apiService.saveCompanyDetails(details);

      // apiService now returns the object (or throws on error)
      if (response) {

        // Update local state with the details we saved
        // (Response might be snake_case from backend, so safer to keep using 'details' 
        // which matches frontend model, relying on success)
        setCompanyDetails(details);
      }
    } catch (err) {
      console.error('Error saving company settings:');
    }
  }, []);

  const userPlan = getUserPlan();
  const planLimits = getPlanLimits(userPlan);

  const renderPage = () => {
    if (!isDataLoaded) {
      return (
        <div className="flex flex-col items-center justify-center min-h-[400px]">
          <div className="w-10 h-10 border-4 border-indigo-100 border-t-[#6366F1] rounded-full animate-spin mb-4"></div>
          <p className="text-slate-400 text-[10px] font-bold uppercase tracking-widest animate-pulse">Syncing Workspace Data...</p>
        </div>
      );
    }

    if (isMasterMode) {
      return (
        <MasterDashboardPage
          onLogout={handleLogout}
          currentPage={currentPage as MasterPage | 'BranchDetail'}
          setCurrentPage={(page) => setCurrentPage(page)}
        />
      );
    }

    // Plan-based feature restrictions (only for premium features now)
    switch (currentPage as Page) {
      case 'Dashboard': return <DashboardPage onNavigate={handleNavigate} companyName={companyDetails.name} vouchers={vouchers} ledgers={ledgers} isAdmin={(sessionStorage.getItem('tenantId') || localStorage.getItem('tenantId')) === null || (sessionStorage.getItem('tenantId') || localStorage.getItem('tenantId')) === 'null'} />;
      case 'Masters': return <MastersPage
        navParams={mastersNavParams}
        ledgers={ledgers}
        ledgerGroups={ledgerGroups}
        onAddLedger={handleAddLedger}
        onAddLedgerGroup={handleAddLedgerGroup}
        onUpdateLedger={handleUpdateLedger}
        onDeleteLedger={handleDeleteLedger}
        onUpdateLedgerGroup={handleUpdateLedgerGroup}
        onDeleteLedgerGroup={handleDeleteLedgerGroup}
      />;
      case 'Inventory': return <InventoryPage navParams={inventoryNavParams} />;
      case 'Vouchers': return <VouchersPage
        navParams={vouchersNavParams}
        vouchers={vouchers}
        ledgers={ledgers}
        stockItems={stockItems}
        onAddVouchers={handleAddVouchers}
        onNavigate={handleNavigate}
        prefilledData={prefilledVoucherData}
        clearPrefilledData={() => setPrefilledVoucherData(null)}
        onInvoiceUpload={handleInvoiceUpload}
        companyDetails={companyDetails}
        permissions={[]}
        viewVoucherData={viewVoucherData}
        clearViewVoucherData={handleClearViewVoucherData}
      />;
      case 'Reports': return <ErrorBoundary><ReportsPage
        navParams={reportsNavParams}
        vouchers={vouchers}
        entries={journalEntries}
        ledgers={ledgers}
        ledgerGroups={ledgerGroups}
        stockItems={stockItems}
        onNavigate={handleNavigate}
        setViewVoucherData={setViewVoucherData}
      /></ErrorBoundary>;

      case 'Settings': return <SettingsPage navParams={settingsNavParams} companyDetails={companyDetails} onSave={handleSaveSettings} />;
      case 'Users & Roles': return <UsersAndRolesPage navParams={usersNavParams} onNavigate={handleNavigate} />;
      case 'Pending Purchases': return <PendingPurchasesPage onNavigate={handleNavigate} />;
      case 'Vendor Portal': return <VendorPortalPage navParams={vendorNavParams} onLogout={handleLogout} onNavigate={handleNavigate} setPrefilledVoucherData={setPrefilledVoucherData} />;
      case 'Customer Portal': return <CustomerPortalPage navParams={customerNavParams} onNavigate={handleNavigate} setPrefilledVoucherData={setPrefilledVoucherData} />;
      case 'Payroll': return <PayrollPage />;
      case 'Service': return <ServicePage navParams={serviceNavParams} />;
      case 'GST': return <GSTPage onNavigate={handleNavigate} setViewVoucherData={setViewVoucherData} vouchers={vouchers} navParams={gstNavParams} />;
      case 'Dashboard Builder': return <DashboardBuilderPage vouchers={vouchers} ledgers={ledgers} onNavigate={handleNavigate} />;
      default: return <div>Page not found</div>;
    }
  };

  // --- RENDER HELPERS ---
  const PageLoader = () => (
    <div className="flex flex-col items-center justify-center min-h-[400px]">
      <div className="w-10 h-10 border-4 border-indigo-100 border-t-[#6366F1] rounded-full animate-spin mb-4"></div>
      <p className="text-slate-400 text-[10px] font-bold uppercase tracking-widest animate-pulse">Syncing Workspace Data...</p>
    </div>
  );

  const isMasterPath = currentPath.startsWith('/master');
  const isAuthPath =
    currentPath === '/login' ||
    currentPath === '/signup' ||
    currentPath === '/forgot-password' ||
    currentPath === '/master/login' ||
    currentPath === '/master/register' ||
    currentPath === '/auth' ||
    currentPath === '/login/business' ||
    currentPath === '/register';

  // 0. ROOT REDIRECT
  if (currentPath === '/' && !isLoggedIn && !isAuthenticating) {
    window.history.replaceState({}, '', '/auth');
    setCurrentPath('/auth');
  }

  // 7. HARD UI PROTECTION
  // "Company pages: Must NOT render if master_token exists"
  // "Master pages: Must NOT render if company_token exists"
  if (isMasterPath && !isAuthPath && hasCompanySession() && !hasMasterSession()) {
    // User is on master path but ONLY company token exists — redirect to company UI
    window.history.replaceState({}, '', '/dashboard');
    setCurrentPath('/dashboard');
    return (
      <div className="flex items-center justify-center h-screen erp-main-bg">
        <div className="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!isMasterPath && !isAuthPath && hasMasterSession() && !hasCompanySession()) {
    // User is on company path but ONLY master token exists — redirect to master UI
    window.history.replaceState({}, '', '/master/dashboard');
    setCurrentPath('/master/dashboard');
    return (
      <div className="flex items-center justify-center h-screen erp-main-bg">
        <div className="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  // ── MASTER DOMAIN AUTH PAGES ───────────────────────────────────
  // /master/login is a standalone page — always rendered if on that path
  if (currentPath === '/master/login' || currentPath === '/master/register') {
    return (
      <Suspense fallback={<div className="flex items-center justify-center h-screen" style={{ background: '#0f172a' }}><div className="w-10 h-10 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" /></div>}>
        <MasterLoginPage onLogin={handleLogin} />
      </Suspense>
    );
  }


  // Show global loader while initializing master path
  if (isMasterPath && isAuthenticating && !isDataLoaded) {
    return <div className="erp-main-bg h-screen flex items-center justify-center"><PageLoader /></div>;
  }

  if (isMasterPath && !isLoggedIn && !isAuthenticating) {
    // Not authenticated, trying to reach master path — redirect to master login
    window.history.replaceState({}, '', '/master/login');
    return (
      <Suspense fallback={<div />}>
        <MasterLoginPage onLogin={handleLogin} />
      </Suspense>
    );
  }

  // ── COMPANY DOMAIN AUTH PAGES ──────────────────────────────────
  // 1. Auth Flow (Login/Signup/Forgot Password)
  if (!isAuthenticating && (!isLoggedIn || (isAuthPath && !isMasterPath))) {
    // 0. Auth Portal (Selection)
    if (currentPath === '/auth' || currentPath === '/') {
      return (
        <Suspense fallback={<div className="flex items-center justify-center h-screen erp-main-bg"><div className="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" /></div>}>
          <AuthPortalPage />
        </Suspense>
      );
    }

    // 1. Other auth routes
    if (currentPath === '/signup' || currentPath === '/register') {
      return (
        <Suspense fallback={<div className="flex items-center justify-center h-screen erp-main-bg"><div className="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" /></div>}>
          <SignupPage
            onSwitchToLogin={() => { window.history.pushState({}, '', '/login'); setCurrentPath('/login'); }}
            onBack={() => { window.history.pushState({}, '', '/login'); setCurrentPath('/login'); }}
          />
        </Suspense>
      );
    }

    if (currentPath === '/forgot-password') {
      return (
        <Suspense fallback={<div className="flex items-center justify-center h-screen erp-main-bg"><div className="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" /></div>}>
          <ForgotPasswordPage
            onBackToLogin={() => { window.history.pushState({}, '', '/login'); setCurrentPath('/login'); }}
          />
        </Suspense>
      );
    }

    // Default for /login and any other auth paths
    return (
      <Suspense fallback={<div className="flex items-center justify-center h-screen erp-main-bg"><div className="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" /></div>}>
        <LoginPage
          onLogin={handleLogin}
          onSwitchToSignup={() => { window.history.pushState({}, '', '/register'); setCurrentPath('/register'); }}
          onForgotPassword={() => { window.history.pushState({}, '', '/forgot-password'); setCurrentPath('/forgot-password'); }}
        />
      </Suspense>
    );
  }

  // ── COMPANY DOMAIN APP LAYOUT ────────────────────────────────────
  // Only renders if JWT does NOT indicate master domain
  // (Additional guard: if access token says 'master' but we're here, redirect away)
  const currentToken = getAccessToken();
  const tokenDomain = getUserTypeFromToken(currentToken);
  if (tokenDomain === 'master' && isLoggedIn && !currentPath.startsWith('/master')) {
    // Token says master but we're on a company path — redirect
    window.history.replaceState({}, '', '/master/dashboard');
    setCurrentPath('/master/dashboard');
    return <PageLoader />;
  }

  return (
    <div className="flex min-h-screen font-sans erp-main-bg">
      {/* Sidebar — renders MasterSidebar for Master admin, Sidebar for company users */}
      {(isLoggedIn || isAuthenticating) && (
        isMasterMode ? (
          <MasterSidebar
            currentPage={(currentPage === 'BranchDetail' ? 'Branches' : currentPage) as MasterPage}
            onNavigate={(page) => setCurrentPage(page)}
            onLogout={handleLogout}
            adminName={sessionStorage.getItem('username') || localStorage.getItem('username') || 'Master Admin'}
            isOpen={isSidebarOpen}
          />
        ) : (
          <Sidebar
            currentPage={currentPage as Page}
            onNavigate={handleNavigate}
            onLogout={handleLogout}
            companyName={companyDetails.name}
            isOpen={isSidebarOpen}
          />
        )
      )}

      <main className={`flex-1 ${(isLoggedIn || isAuthenticating) && isSidebarOpen ? 'ml-[220px]' : 'ml-0'} min-h-screen transition-all duration-300 erp-main-bg min-w-0 max-w-full overflow-x-hidden`}>
        {/* ── Sticky Master Header ───────────────────────────── */}
        {isHeaderCollapsed && (
          <div className="fixed top-0 left-1/2 -translate-x-1/2 z-[9999] animate-in slide-in-from-top duration-200">
            <button
              onClick={() => setIsHeaderCollapsed(false)}
              className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-b-xl shadow-lg hover:shadow-xl active:scale-95 transition-all flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider"
              title="Show Header"
            >
              <ChevronDown className="w-3.5 h-3.5 text-white" />
              <span>Show Header</span>
            </button>
          </div>
        )}

        {!isHeaderCollapsed && (
          <MasterHeader
            title={currentPage}
            isSidebarOpen={isSidebarOpen}
            toggleSidebar={toggleSidebar}
            adminName={
              isMasterMode
                ? (sessionStorage.getItem('username') || localStorage.getItem('username') || 'Platform Admin')
                : (companyDetails.name || 'Ai Accounting')
            }
            onNavigate={(page, params) => handleNavigate(page as Page, params)}
            onLogout={handleLogout}
            onCollapseHeader={() => setIsHeaderCollapsed(true)}
          />
        )}

        {/* ── Page Content ──────────────────────────────────── */}
        <div className="p-6 min-w-0 w-full">
          <div className="max-w-[1600px] mx-auto min-w-0 w-full">
            {(!isLoggedIn && isAuthenticating) || !isDataLoaded ? (
              <PageLoader />
            ) : (
              <Suspense fallback={<PageLoader />}>
                {renderPage()}
              </Suspense>
            )}
          </div>
        </div>
      </main>

      <Modal isOpen={isLoading} title="AI Processing" type="loading">
        <p>Extracting invoice data with Gemini AI. This may take a moment...</p>
      </Modal>
      <Modal isOpen={!!error} onClose={() => setError(null)} title="Error" type="error">
        <p>{error}</p>
      </Modal>
      {importSummary && (
        <Modal isOpen={!!importSummary} onClose={() => setImportSummary(null)} title="Import Complete" type="success">
          <p>Successfully imported {importSummary.success} vouchers.</p>
          {importSummary.failed > 0 && <p className="text-yellow-700 mt-1">{importSummary.failed} rows were skipped due to errors or incorrect formatting.</p>}
        </Modal>
      )}

      {/* Deactivation Modal */}
      <Modal isOpen={showDeactivationModal} title="Account Deactivated" type="warning">
        <div className="text-center">
          <Icon name="exclamation-triangle" className="mx-auto h-12 w-12 text-indigo-500" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">Your account has been deactivated</h3>
          <p className="mt-1 text-sm text-gray-500">
            Please contact your administrator or support for assistance.
          </p>
          <p className="mt-3 text-xs text-gray-400">You will be logged out automatically...</p>
        </div>
      </Modal>

      <FloatingCalculator />
      <FloatingCalendar />
      <FloatingNotes />
      <KikiPanel onNavigate={(page) => handleNavigate(page as Page)} />




      {globalVendorId !== null && (
        <VendorViewModal
          vendorId={globalVendorId}
          onClose={() => setGlobalVendorId(null)}
        />
      )}
      {globalCustomer !== null && (
        <CustomerViewModal
          customer={globalCustomer}
          onClose={() => setGlobalCustomer(null)}
        />
      )}


    </div>
  );
};

export default App;


