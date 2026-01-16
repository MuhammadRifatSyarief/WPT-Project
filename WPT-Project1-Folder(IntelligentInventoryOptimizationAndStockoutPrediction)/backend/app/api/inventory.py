from flask import Blueprint, request, jsonify
from app.services.data_loader_service import DataLoaderService
from flask_jwt_extended import jwt_required
import math

bp = Blueprint('inventory', __name__, url_prefix='/api/inventory')

@bp.route('/groups', methods=['GET'])
@jwt_required()
def get_groups():
    """Get list of all product groups (categories)"""
    try:
        groups = DataLoaderService.get_groups_list()
        return jsonify({
            'groups': groups,
            'count': len(groups)
        }), 200
    except Exception as e:
        print(f"❌ Error getting groups: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('', methods=['GET'])
@jwt_required()
def get_inventory():
    """Get all inventory items from CSV filtered by group"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        group = request.args.get('group', 'All Groups')
        
        print(f"🔍 Inventory API: page={page}, per_page={per_page}, group='{group}'")

        # Load data from CSV via Service
        df = DataLoaderService.load_products_data()
        
        print(f"📊 Data loaded: {len(df)} rows")
        
        if df.empty:
            return jsonify({
                'items': [],
                'total': 0,
                'pages': 0,
                'current_page': page
            }), 200

        # Filter by Group
        if group and group != 'All Groups':
            df = df[df['group'] == group]
            print(f"📌 Filtered to {len(df)} items for group: {group}")

        # Pagination
        total_items = len(df)
        total_pages = max(1, math.ceil(total_items / per_page))
        
        # Slice dataframe for current page
        start = (page - 1) * per_page
        end = start + per_page
        page_items = df.iloc[start:end]
        
        # Convert to dictionary
        items_list = []
        for idx, (_, row) in enumerate(page_items.iterrows()):
            items_list.append({
                'id': start + idx,
                'product_id': str(row.get('product_code', 'N/A')),
                'product_name': str(row.get('product_name', 'Unknown')),
                'category': str(row.get('group', 'Uncategorized')),
                'current_stock': int(row.get('current_stock', 0)),
                'min_stock_level': 10, 
                'max_stock_level': 100,
                'unit_price': float(row.get('price', 0.0)),
                'lead_time_days': 1,
                'last_updated': None,
                'status': str(row.get('risk_level', 'Optimal'))
            })

        return jsonify({
            'items': items_list,
            'total': total_items,
            'pages': total_pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        print(f"❌ Inventory API Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
