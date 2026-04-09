/**
 * Client-side status machine — mirrors business/services/status_machine.py
 * Eliminates N+1 API calls for allowed-transitions per position.
 */

const TRANSITIONS: Record<string, string[]> = {
  planned: [
    'insufficient_materials', 'awaiting_recipe', 'awaiting_stencil_silkscreen',
    'awaiting_color_matching', 'awaiting_size_confirmation', 'awaiting_consumption_data',
    'engobe_applied', 'glazed',
  ],
  insufficient_materials: ['planned'],
  awaiting_recipe: ['planned'],
  awaiting_stencil_silkscreen: ['planned'],
  awaiting_color_matching: ['planned'],
  awaiting_size_confirmation: ['planned'],
  awaiting_consumption_data: ['planned'],
  engobe_applied: ['engobe_check'],
  engobe_check: ['glazed', 'engobe_applied'],
  glazed: ['pre_kiln_check'],
  pre_kiln_check: ['loaded_in_kiln', 'sent_to_glazing'],
  sent_to_glazing: ['planned'],
  loaded_in_kiln: ['fired'],
  fired: ['transferred_to_sorting', 'refire', 'sent_to_glazing'],
  transferred_to_sorting: ['packed', 'sent_to_glazing', 'awaiting_reglaze'],
  awaiting_reglaze: ['sent_to_glazing'],
  refire: ['loaded_in_kiln'],
  packed: ['sent_to_quality_check', 'ready_for_shipment', 'shipped', 'merged'],
  sent_to_quality_check: ['quality_check_done'],
  quality_check_done: ['ready_for_shipment', 'merged'],
  ready_for_shipment: ['shipped', 'merged'],
  blocked_by_qm: [],
  shipped: [],
  merged: [],
  cancelled: [],
};

// Universal transitions reachable from any status
const UNIVERSAL_TARGETS = ['blocked_by_qm', 'cancelled'];

export function getAllowedTransitions(currentStatus: string, _role?: string): string[] {
  const specific = TRANSITIONS[currentStatus] ?? [];
  const universal = UNIVERSAL_TARGETS.filter((s) => s !== currentStatus);
  return [...specific, ...universal];
}
