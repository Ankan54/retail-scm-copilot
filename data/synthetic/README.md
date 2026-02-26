# Synthetic Data for SupplyChain Copilot

## Generation Details
- Generated: 2026-02-25 15:38:35
- Generator: Synthetic Data Script
- Business Context: Small MSME detergent manufacturer in Delhi NCR

## Record Counts
| Table | Records |
|-------|---------|
| territories | 5 |
| sales_persons | 5 |
| territory_assignments | 5 |
| product_categories | 1 |
| hsn_codes | 1 |
| products | 3 |
| warehouses | 1 |
| dealers | 45 |
| dealer_inventory | ~120 |
| inventory | 3 |
| incoming_stock | 10 |
| production_capacity | 3 |
| production_schedule | 150 |
| visits | ~1500 |
| commitments | 500 |
| orders | ~900 |
| order_items | ~1500 |
| order_splits | ~15 |
| invoices | ~850 |
| payments | ~1000 |
| issues | 40 |
| vehicles | 2 |
| delivery_routes | ~200 |
| route_stops | ~1200 |
| alerts | 80 |
| sales_targets | 48 |
| dealer_health_scores | ~400 |
| weekly_sales_actuals | 156 |
| consumption_config | 1 |
| system_settings | 8 |
| **TOTAL** | **~7,700** |

## Data Characteristics
- Time Range: 2024-03-01 to 2025-02-24 (12 months)
- Geography: Delhi NCR only
- Products: 3 SKUs (500g, 1kg, 2kg) of CleanMax Detergent
- Training Data: weekly_sales_actuals (filter to CLN-1KG for 52 rows)
- Seasonal patterns: Diwali (Oct) and Holi (Mar) peaks, Monsoon (Jun-Jul) dips

## Key IDs for Testing
- Manager (Rajesh Kumar): c361d450-2f4c-46b8-a441-3f819e888d3b
- 1kg Product (CLN-1KG): 691d2da3-3a95-42f4-af6a-57c1f73652fa
- Primary Warehouse: 3c7fb12b-5cc0-412a-84b2-2937e54e6492
