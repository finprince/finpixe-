/**
 * ============================================================================
 * INVOICE AI SERVICE (geminiService.ts)
 * ============================================================================
 * Handles invoice data extraction using backend AI OCR provider.
 * 
 * KEY FEATURES:
 * 1. Invoice Data Extraction - Extract structured data from invoice images/PDFs
 */

import { httpClient } from './httpClient';

// Import TypeScript types
import type { ExtractedInvoiceData } from '../types';

// ============================================================================
// INVOICE DATA EXTRACTION
// ============================================================================

/**
 * Extract structured data from invoice images/PDFs using AI
 * Implements automatic retry logic with exponential backoff
 * 
 * WHAT IT EXTRACTS:
 * - Seller name
 * - Invoice number and date
 * - Line items (description, quantity, rate, HSN code)
 * - Tax amounts (CGST, SGST, IGST)
 * - Total amount
 * 
 * USAGE:
 * ```typescript
 * const file = event.target.files[0]; // User-selected file
 * const data = await extractInvoiceDataWithRetry(file);
 * // data contains: { sellerName, invoiceNumber, lineItems, totalAmount, ... }
 * ```
 * 
 * @param file - Invoice file (image or PDF)
 * @param maxRetries - Maximum number of retry attempts (default: 3)
 * @param initialDelay - Initial delay between retries in ms (default: 5000)
 * @returns Extracted invoice data
 * @throws Error if extraction fails after all retries
 */
export const extractInvoiceDataWithRetry = async (
  file: File,
  maxRetries = 3,
  initialDelay = 5000
): Promise<ExtractedInvoiceData> => {
  // Prepare file for upload
  const formData = new FormData();
  formData.append('file', file);

  let attempt = 0;
  let delay = initialDelay;

  // Retry loop
  while (attempt < maxRetries) {
    try {
      // Wait before retry (skip on first attempt)
      if (attempt > 0) {
        await new Promise((r) => setTimeout(r, delay));
      }

      // Use httpClient for authenticated request with automatic token refresh
      formData.append('save', 'false');
      const response: any = await httpClient.postFormData('/api/ai/extract-invoice/', formData);

      // Backend returns { reply: "stringified json" }
      // We need to parse it to get the actual object
      if (response && response.reply) {
        let cleanJson = response.reply.replace(/```json\n?|```/g, '').trim();
        let parsedData: any = JSON.parse(cleanJson);

        // API might return an array [ { invoice... } ]
        if (Array.isArray(parsedData) && parsedData.length > 0) {
          parsedData = parsedData[0];
        }

        // MAP BACKEND KEYS TO FRONTEND INTERFACE
        // Backend now returns STRICT snake_case: supplier_invoice_no, vendor_name, etc.
        const mappedData: ExtractedInvoiceData = {
          sellerName: parsedData.vendor_name || '',
          invoiceNumber: parsedData.supplier_invoice_no || '',
          invoiceDate: parsedData.invoice_date || new Date().toISOString().split('T')[0],
          dueDate: parsedData.due_date || '',
          subtotal: parseFloat(parsedData.total_taxable_value || '0'),
          cgstAmount: parseFloat(parsedData.total_cgst || '0'),
          sgstAmount: parseFloat(parsedData.total_sgst || '0'),
          igstAmount: parseFloat(parsedData.total_igst || '0'),
          totalAmount: parseFloat(parsedData.total_invoice_value || '0'),
          lineItems: []
        };

        // Standardized line_items from backend
        const rawItems = parsedData.line_items || parsedData.items || [];
        if (Array.isArray(rawItems)) {
          mappedData.lineItems = rawItems.map((item: any) => ({
            itemDescription: item.description || item.item_name || 'Item',
            quantity: parseFloat(item.quantity || '0'),
            rate: parseFloat(item.rate || '0'),
            amount: parseFloat(item.amount || '0'),
            hsnCode: item.hsn_sac || item.hsn_code || ''
          }));
        }

        return mappedData;
      }
    } catch (error: any) {
      attempt++;

      // If all retries exhausted, throw error
      if (attempt >= maxRetries) {
        throw new Error(`❌ Failed to extract invoice data after ${maxRetries} attempts. ${error.message || error}`);
      }

      // Adjust delay based on error type
      const errMsg = error.message || JSON.stringify(error);
      if (errMsg.includes('429') || errMsg.includes('overloaded') || errMsg.includes('rate limit')) {
        // Rate limiting - increase delay more aggressively
        delay = Math.min(delay * 3, 30000); // Max 30 seconds
      } else {
        // Other errors - standard exponential backoff
        delay = Math.min(delay * 2, 10000); // Max 10 seconds
      }
    }
  }
  throw new Error('Unexpected retry termination.');
};


