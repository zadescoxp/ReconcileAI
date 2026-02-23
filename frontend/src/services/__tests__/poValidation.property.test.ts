/**
 * Property-Based Test for PO Validation
 * Feature: reconcile-ai, Property 2: PO Validation Completeness
 * 
 * Property 2: For any PO upload attempt, if the PO is missing any required field 
 * (PO number, vendor, line items, quantities, or prices), the validation should 
 * reject it and prevent storage.
 * 
 * Validates: Requirements 2.1
 */

import fc from 'fast-check';
import { POService } from '../poService';
import { POMetadata, LineItem } from '../../types/po';

describe('Property 2: PO Validation Completeness', () => {
  // Helper to create valid line item
  const validLineItemArb = fc.record({
    LineNumber: fc.integer({ min: 1, max: 100 }),
    ItemDescription: fc.string({ minLength: 1, maxLength: 200 }),
    Quantity: fc.float({ min: Math.fround(0.01), max: Math.fround(10000), noNaN: true }),
    UnitPrice: fc.float({ min: Math.fround(0.01), max: Math.fround(100000), noNaN: true }),
    TotalPrice: fc.float({ min: Math.fround(0.01), max: Math.fround(1000000), noNaN: true })
  });

  // Helper to create valid PO metadata
  const validPOArb = fc.record({
    vendorName: fc.string({ minLength: 1, maxLength: 100 }),
    poNumber: fc.string({ minLength: 1, maxLength: 50 }),
    totalAmount: fc.float({ min: Math.fround(0.01), max: Math.fround(10000000), noNaN: true }),
    lineItems: fc.array(validLineItemArb, { minLength: 1, maxLength: 20 })
  });

  test('Property 2.1: PO with missing vendor name should be rejected', () => {
    fc.assert(
      fc.property(validPOArb, (validPO) => {
        // Create PO with empty vendor name
        const invalidPO: POMetadata = {
          ...validPO,
          vendorName: ''
        };

        // Validate using the private validation method via uploadPO
        const result = (POService as any).validatePO(invalidPO);

        // Should have validation errors
        expect(result.length).toBeGreaterThan(0);
        expect(result.some((err: string) => err.toLowerCase().includes('vendor'))).toBe(true);
      }),
      { numRuns: 100 }
    );
  });

  test('Property 2.2: PO with missing PO number should be rejected', () => {
    fc.assert(
      fc.property(validPOArb, (validPO) => {
        // Create PO with empty PO number
        const invalidPO: POMetadata = {
          ...validPO,
          poNumber: ''
        };

        const result = (POService as any).validatePO(invalidPO);

        // Should have validation errors
        expect(result.length).toBeGreaterThan(0);
        expect(result.some((err: string) => err.toLowerCase().includes('po number'))).toBe(true);
      }),
      { numRuns: 100 }
    );
  });

  test('Property 2.3: PO with no line items should be rejected', () => {
    fc.assert(
      fc.property(validPOArb, (validPO) => {
        // Create PO with empty line items
        const invalidPO: POMetadata = {
          ...validPO,
          lineItems: []
        };

        const result = (POService as any).validatePO(invalidPO);

        // Should have validation errors
        expect(result.length).toBeGreaterThan(0);
        expect(result.some((err: string) => err.toLowerCase().includes('line item'))).toBe(true);
      }),
      { numRuns: 100 }
    );
  });

  test('Property 2.4: PO with line item missing description should be rejected', () => {
    fc.assert(
      fc.property(validPOArb, (validPO) => {
        // Create PO with line item missing description
        const invalidPO: POMetadata = {
          ...validPO,
          lineItems: [
            ...validPO.lineItems,
            {
              LineNumber: validPO.lineItems.length + 1,
              ItemDescription: '',
              Quantity: 10,
              UnitPrice: 100,
              TotalPrice: 1000
            }
          ]
        };

        const result = (POService as any).validatePO(invalidPO);

        // Should have validation errors
        expect(result.length).toBeGreaterThan(0);
        expect(result.some((err: string) => err.toLowerCase().includes('description'))).toBe(true);
      }),
      { numRuns: 100 }
    );
  });

  test('Property 2.5: PO with line item having zero or negative quantity should be rejected', () => {
    fc.assert(
      fc.property(
        validPOArb,
        fc.float({ min: Math.fround(-1000), max: Math.fround(0), noNaN: true }),
        (validPO, invalidQuantity) => {
          // Create PO with invalid quantity
          const invalidPO: POMetadata = {
            ...validPO,
            lineItems: [
              ...validPO.lineItems,
              {
                LineNumber: validPO.lineItems.length + 1,
                ItemDescription: 'Test Item',
                Quantity: invalidQuantity,
                UnitPrice: 100,
                TotalPrice: invalidQuantity * 100
              }
            ]
          };

          const result = (POService as any).validatePO(invalidPO);

          // Should have validation errors
          expect(result.length).toBeGreaterThan(0);
          expect(result.some((err: string) => err.toLowerCase().includes('quantity'))).toBe(true);
        }
      ),
      { numRuns: 100 }
    );
  });

  test('Property 2.6: PO with line item having zero or negative unit price should be rejected', () => {
    fc.assert(
      fc.property(
        validPOArb,
        fc.float({ min: Math.fround(-10000), max: Math.fround(0), noNaN: true }),
        (validPO, invalidPrice) => {
          // Create PO with invalid unit price
          const invalidPO: POMetadata = {
            ...validPO,
            lineItems: [
              ...validPO.lineItems,
              {
                LineNumber: validPO.lineItems.length + 1,
                ItemDescription: 'Test Item',
                Quantity: 10,
                UnitPrice: invalidPrice,
                TotalPrice: 10 * invalidPrice
              }
            ]
          };

          const result = (POService as any).validatePO(invalidPO);

          // Should have validation errors
          expect(result.length).toBeGreaterThan(0);
          expect(result.some((err: string) => err.toLowerCase().includes('price'))).toBe(true);
        }
      ),
      { numRuns: 100 }
    );
  });

  test('Property 2.7: Valid PO with all required fields should pass validation', () => {
    fc.assert(
      fc.property(validPOArb, (validPO) => {
        // Ensure all line items have positive values
        const normalizedPO: POMetadata = {
          ...validPO,
          lineItems: validPO.lineItems.map((item, index) => ({
            ...item,
            LineNumber: index + 1,
            ItemDescription: item.ItemDescription.trim() || 'Item',
            Quantity: Math.abs(item.Quantity) || 1,
            UnitPrice: Math.abs(item.UnitPrice) || 1,
            TotalPrice: Math.abs(item.TotalPrice) || 1
          }))
        };

        const result = (POService as any).validatePO(normalizedPO);

        // Should have no validation errors
        expect(result.length).toBe(0);
      }),
      { numRuns: 100 }
    );
  });

  test('Property 2.8: PO with whitespace-only vendor name should be rejected', () => {
    fc.assert(
      fc.property(
        validPOArb,
        fc.string({ minLength: 1, maxLength: 10 }).filter(s => s.trim() === ''),
        (validPO, whitespace) => {
          const invalidPO: POMetadata = {
            ...validPO,
            vendorName: whitespace
          };

          const result = (POService as any).validatePO(invalidPO);

          // Should have validation errors
          expect(result.length).toBeGreaterThan(0);
          expect(result.some((err: string) => err.toLowerCase().includes('vendor'))).toBe(true);
        }
      ),
      { numRuns: 100 }
    );
  });

  test('Property 2.9: PO with whitespace-only PO number should be rejected', () => {
    fc.assert(
      fc.property(
        validPOArb,
        fc.string({ minLength: 1, maxLength: 10 }).filter(s => s.trim() === ''),
        (validPO, whitespace) => {
          const invalidPO: POMetadata = {
            ...validPO,
            poNumber: whitespace
          };

          const result = (POService as any).validatePO(invalidPO);

          // Should have validation errors
          expect(result.length).toBeGreaterThan(0);
          expect(result.some((err: string) => err.toLowerCase().includes('po number'))).toBe(true);
        }
      ),
      { numRuns: 100 }
    );
  });

  test('Property 2.10: PO with multiple validation errors should report all errors', () => {
    fc.assert(
      fc.property(validPOArb, (validPO) => {
        // Create PO with multiple issues
        const invalidPO: POMetadata = {
          vendorName: '',
          poNumber: '',
          totalAmount: validPO.totalAmount,
          lineItems: []
        };

        const result = (POService as any).validatePO(invalidPO);

        // Should have multiple validation errors
        expect(result.length).toBeGreaterThanOrEqual(3);
        expect(result.some((err: string) => err.toLowerCase().includes('vendor'))).toBe(true);
        expect(result.some((err: string) => err.toLowerCase().includes('po number'))).toBe(true);
        expect(result.some((err: string) => err.toLowerCase().includes('line item'))).toBe(true);
      }),
      { numRuns: 100 }
    );
  });
});
