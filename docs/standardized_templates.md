# Standardized Model Templates
Generated: 2025-09-13 19:34:50

## Overview
This document describes the standardized templates for genomic testing models.
Templates define the structure, validation rules, and data types for consistent model formatting.

## Base

### Required Columns
- **Test** (string)
- **Category** (category)
- **Sub-Category** (category)
- **Item** (string)
- **Unit Cost (AUD $/unit)** (float64)
- **Units** (float64)
- **Total Cost (AUD)** (float64)
- **Notes** (string)

### Optional Columns
- **Supplier** (string)
- **Catalogue Number** (string)
- **Batch/Lot Number** (string)
- **Expiry Date** (datetime64[ns])
- **Storage Conditions** (string)
- **Quality Control** (string)
- **References** (string)

### Validation Rules
- **Required Categories**: Labour, Equipment, Consumables
- **Minimum Labour Subcategories**: 3
- **Minimum Equipment Subcategories**: 3
- **Minimum Consumables Subcategories**: 2

## Panel

### Required Columns
- **Test** (string)
- **Category** (category)
- **Sub-Category** (category)
- **Item** (string)
- **Unit Cost (AUD $/unit)** (float64)
- **Units** (float64)
- **Total Cost (AUD)** (float64)
- **Notes** (string)

### Optional Columns
- **Supplier** (string)
- **Catalogue Number** (string)
- **Batch/Lot Number** (string)
- **Expiry Date** (datetime64[ns])
- **Storage Conditions** (string)
- **Quality Control** (string)
- **References** (string)

### Validation Rules
- **Required Categories**: Labour, Equipment, Consumables
- **Minimum Labour Subcategories**: 3
- **Minimum Equipment Subcategories**: 3
- **Minimum Consumables Subcategories**: 2

## Wes P

### Required Columns
- **Test** (string)
- **Category** (category)
- **Sub-Category** (category)
- **Item** (string)
- **Unit Cost (AUD $/unit)** (float64)
- **Units** (float64)
- **Total Cost (AUD)** (float64)
- **Notes** (string)

### Optional Columns
- **Supplier** (string)
- **Catalogue Number** (string)
- **Batch/Lot Number** (string)
- **Expiry Date** (datetime64[ns])
- **Storage Conditions** (string)
- **Quality Control** (string)
- **References** (string)

### Validation Rules
- **Required Categories**: Labour, Equipment, Consumables
- **Minimum Labour Subcategories**: 3
- **Minimum Equipment Subcategories**: 3
- **Minimum Consumables Subcategories**: 2

## Wes T

### Required Columns
- **Test** (string)
- **Category** (category)
- **Sub-Category** (category)
- **Item** (string)
- **Unit Cost (AUD $/unit)** (float64)
- **Units** (float64)
- **Total Cost (AUD)** (float64)
- **Notes** (string)

### Optional Columns
- **Supplier** (string)
- **Catalogue Number** (string)
- **Batch/Lot Number** (string)
- **Expiry Date** (datetime64[ns])
- **Storage Conditions** (string)
- **Quality Control** (string)
- **References** (string)

### Validation Rules
- **Required Categories**: Labour, Equipment, Consumables
- **Minimum Labour Subcategories**: 3
- **Minimum Equipment Subcategories**: 3
- **Minimum Consumables Subcategories**: 2

## Wgs

### Required Columns
- **Test** (string)
- **Category** (category)
- **Sub-Category** (category)
- **Item** (string)
- **Unit Cost (AUD $/unit)** (float64)
- **Units** (float64)
- **Total Cost (AUD)** (float64)
- **Notes** (string)

### Optional Columns
- **Supplier** (string)
- **Catalogue Number** (string)
- **Batch/Lot Number** (string)
- **Expiry Date** (datetime64[ns])
- **Storage Conditions** (string)
- **Quality Control** (string)
- **References** (string)

### Validation Rules
- **Required Categories**: Labour, Equipment, Consumables
- **Minimum Labour Subcategories**: 3
- **Minimum Equipment Subcategories**: 3
- **Minimum Consumables Subcategories**: 2

## Wgs T

### Required Columns
- **Test** (string)
- **Category** (category)
- **Sub-Category** (category)
- **Item** (string)
- **Unit Cost (AUD $/unit)** (float64)
- **Units** (float64)
- **Total Cost (AUD)** (float64)
- **Notes** (string)

### Optional Columns
- **Supplier** (string)
- **Catalogue Number** (string)
- **Batch/Lot Number** (string)
- **Expiry Date** (datetime64[ns])
- **Storage Conditions** (string)
- **Quality Control** (string)
- **References** (string)

### Validation Rules
- **Required Categories**: Labour, Equipment, Consumables
- **Minimum Labour Subcategories**: 3
- **Minimum Equipment Subcategories**: 3
- **Minimum Consumables Subcategories**: 2

## Usage
1. Use the base template for general model creation
2. Use model-specific templates for specialized requirements
3. Follow the column order and data types specified
4. Ensure all validation rules are met
5. Use default values for optional fields when appropriate
