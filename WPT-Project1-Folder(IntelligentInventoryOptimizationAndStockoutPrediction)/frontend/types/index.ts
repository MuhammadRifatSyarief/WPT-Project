export interface InventoryItem {
    id: number;
    product_id: string;
    product_name: string;
    category: string;
    current_stock: number;
    min_stock_level: number;
    max_stock_level: number;
    unit_price: number;
    lead_time_days: number;
    last_updated: string;
    status: 'Optimal' | 'Low Stock' | 'Overstock' | 'Stockout';
}

export interface PaginatedResponse<T> {
    items: T[];
    total: number;
    pages: number;
    current_page: number;
}
