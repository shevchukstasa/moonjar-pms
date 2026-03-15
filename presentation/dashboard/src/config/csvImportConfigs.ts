import type { CsvColumn } from '@/components/admin/CsvImportDialog';

export interface CsvImportConfig {
  entityName: string;
  entityLabel: string;
  columns: CsvColumn[];
}

export const CSV_CONFIGS: Record<string, CsvImportConfig> = {
  /* ── Simple reference tables ─────────────────────────────────────── */

  collections: {
    entityName: 'collections',
    entityLabel: 'Collections',
    columns: [
      { key: 'name', header: 'name', required: true, type: 'string', example: 'Collection 2025' },
    ],
  },

  colors: {
    entityName: 'colors',
    entityLabel: 'Colors',
    columns: [
      { key: 'name', header: 'name', required: true, type: 'string', example: 'Terracotta Red' },
      { key: 'code', header: 'code', required: false, type: 'string', example: '#CC4422' },
      { key: 'is_basic', header: 'is_basic', required: false, type: 'boolean', example: 'false' },
    ],
  },

  application_types: {
    entityName: 'application_types',
    entityLabel: 'Application Types',
    columns: [
      { key: 'name', header: 'name', required: true, type: 'string', example: 'Wall' },
    ],
  },

  places_of_application: {
    entityName: 'places_of_application',
    entityLabel: 'Places of Application',
    columns: [
      { key: 'code', header: 'code', required: true, type: 'string', example: 'face_only' },
      { key: 'name', header: 'name', required: true, type: 'string', example: 'Face Only' },
    ],
  },

  finishing_types: {
    entityName: 'finishing_types',
    entityLabel: 'Finishing Types',
    columns: [
      { key: 'name', header: 'name', required: true, type: 'string', example: 'Matte' },
    ],
  },

  /* ── Complex entities ────────────────────────────────────────────── */

  recipes: {
    entityName: 'recipes',
    entityLabel: 'Recipes',
    columns: [
      { key: 'name', header: 'name', required: true, type: 'string', example: 'White Base Glaze' },
      { key: 'color_collection', header: 'color_collection', required: false, type: 'string', example: 'Collection 2025' },
      { key: 'recipe_type', header: 'recipe_type', required: false, type: 'string', example: 'glaze' },
      { key: 'specific_gravity', header: 'specific_gravity', required: false, type: 'number', example: '1.45' },
      { key: 'consumption_spray_ml_per_sqm', header: 'consumption_spray_ml_per_sqm', required: false, type: 'number', example: '850' },
      { key: 'consumption_brush_ml_per_sqm', header: 'consumption_brush_ml_per_sqm', required: false, type: 'number', example: '1200' },
      { key: 'is_default', header: 'is_default', required: false, type: 'boolean', example: 'false' },
      { key: 'is_active', header: 'is_active', required: false, type: 'boolean', example: 'true' },
    ],
  },

  suppliers: {
    entityName: 'suppliers',
    entityLabel: 'Suppliers',
    columns: [
      { key: 'name', header: 'name', required: true, type: 'string', example: 'PT Bali Ceramics' },
      { key: 'contact_person', header: 'contact_person', required: false, type: 'string', example: 'Wayan' },
      { key: 'phone', header: 'phone', required: false, type: 'string', example: '+62-361-123456' },
      { key: 'email', header: 'email', required: false, type: 'string', example: 'info@baliceramics.com' },
      { key: 'address', header: 'address', required: false, type: 'string', example: 'Jl. Raya Ubud 45' },
      { key: 'default_lead_time_days', header: 'default_lead_time_days', required: false, type: 'number', example: '35' },
      { key: 'notes', header: 'notes', required: false, type: 'string', example: '' },
      { key: 'is_active', header: 'is_active', required: false, type: 'boolean', example: 'true' },
    ],
  },

  materials: {
    entityName: 'materials',
    entityLabel: 'Materials',
    columns: [
      { key: 'name', header: 'name', required: true, type: 'string', example: 'Feldspar FK-200' },
      { key: 'material_type', header: 'material_type', required: true, type: 'string', example: 'frit' },
      { key: 'unit', header: 'unit', required: false, type: 'string', example: 'kg' },
    ],
  },

  sizes: {
    entityName: 'sizes',
    entityLabel: 'Sizes',
    columns: [
      { key: 'name', header: 'name', required: true, type: 'string', example: '60x60' },
      { key: 'width_mm', header: 'width_mm', required: true, type: 'number', example: '600' },
      { key: 'height_mm', header: 'height_mm', required: true, type: 'number', example: '600' },
      { key: 'thickness_mm', header: 'thickness_mm', required: false, type: 'number', example: '11' },
      { key: 'shape', header: 'shape', required: false, type: 'string', example: 'rectangle' },
      { key: 'is_custom', header: 'is_custom', required: false, type: 'boolean', example: 'false' },
    ],
  },

  warehouse_sections: {
    entityName: 'warehouse_sections',
    entityLabel: 'Warehouses',
    columns: [
      { key: 'name', header: 'name', required: true, type: 'string', example: 'Main Warehouse' },
      { key: 'code', header: 'code', required: true, type: 'string', example: 'WH-01' },
      { key: 'description', header: 'description', required: false, type: 'string', example: 'Primary storage' },
      { key: 'warehouse_type', header: 'warehouse_type', required: false, type: 'string', example: 'section' },
      { key: 'display_order', header: 'display_order', required: false, type: 'number', example: '1' },
      { key: 'is_default', header: 'is_default', required: false, type: 'boolean', example: 'false' },
      { key: 'is_active', header: 'is_active', required: false, type: 'boolean', example: 'true' },
    ],
  },

  packaging: {
    entityName: 'packaging',
    entityLabel: 'Packaging',
    columns: [
      { key: 'notes', header: 'notes', required: false, type: 'string', example: 'Standard box' },
    ],
  },

  temperature_groups: {
    entityName: 'temperature_groups',
    entityLabel: 'Temperature Groups',
    columns: [
      { key: 'name', header: 'name', required: true, type: 'string', example: 'Low Temperature' },
      { key: 'min_temperature', header: 'min_temperature', required: true, type: 'number', example: '800' },
      { key: 'max_temperature', header: 'max_temperature', required: true, type: 'number', example: '1050' },
      { key: 'description', header: 'description', required: false, type: 'string', example: 'Earthenware range' },
      { key: 'thermocouple', header: 'thermocouple', required: false, type: 'string', example: 'chinese' },
      { key: 'control_cable', header: 'control_cable', required: false, type: 'string', example: 'indonesia_manufacture' },
      { key: 'control_device', header: 'control_device', required: false, type: 'string', example: 'moonjar' },
      { key: 'display_order', header: 'display_order', required: false, type: 'number', example: '1' },
    ],
  },
};
