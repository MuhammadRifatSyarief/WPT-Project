from app.extensions import db
from datetime import datetime

class Inventory(db.Model):
    __tablename__ = 'inventory'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    product_name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50))
    current_stock = db.Column(db.Integer, default=0)
    min_stock_level = db.Column(db.Integer, default=0) # Reorder Point
    max_stock_level = db.Column(db.Integer, default=100)
    unit_price = db.Column(db.Float, default=0.0)
    lead_time_days = db.Column(db.Integer, default=1)
    
    # Metadata
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'product_name': self.product_name,
            'category': self.category,
            'current_stock': self.current_stock,
            'min_stock_level': self.min_stock_level,
            'max_stock_level': self.max_stock_level,
            'unit_price': self.unit_price,
            'lead_time_days': self.lead_time_days,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'status': self.stock_status  # Helper property
        }

    @property
    def stock_status(self):
        if self.current_stock <= 0:
            return 'Stockout'
        elif self.current_stock <= self.min_stock_level:
            return 'Low Stock'
        elif self.current_stock >= self.max_stock_level:
            return 'Overstock'
        else:
            return 'Optimal'
