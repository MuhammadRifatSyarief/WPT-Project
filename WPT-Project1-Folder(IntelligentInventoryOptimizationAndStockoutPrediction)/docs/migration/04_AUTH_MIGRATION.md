# 🔐 Authentication Migration

> **Tujuan**: Migrasi sistem autentikasi dari `st.session_state` ke JWT
> 
> **File Source**: `modules/auth.py`, `modules/pages/login.py`, `modules/database.py`

---

## 📊 Perbandingan Sistem Auth

| Aspek | Streamlit | Flask + JWT |
|-------|-----------|-------------|
| Session Storage | Server-side (`st.session_state`) | Client-side (JWT token) |
| Authentication | Cookie-based | Token-based |
| State Check | `is_authenticated()` → reads session | Middleware → verifies JWT |
| Logout | Clear session state | Delete token from client |
| Token Lifetime | Until browser closed | Configurable (1 hour default) |

---

## 🏗️ Struktur File Auth di Flask

```
backend/app/
├── api/
│   └── auth.py              # Auth endpoints
├── services/
│   └── auth_service.py      # Auth business logic
├── models/
│   └── user.py              # User model
└── middleware/
    └── auth_middleware.py   # JWT verification
```

---

## 📄 Service Layer: `auth_service.py`

```python
"""
Authentication Service
======================
Migrasi dari: modules/auth.py + modules/database.py
"""

import bcrypt
from typing import Optional, Dict, Tuple
from app.models.user import User
from app.extensions import db


class AuthService:
    """Service class untuk autentikasi."""
    
    def authenticate(self, username: str, password: str) -> Optional[Dict]:
        """
        Authenticate user credentials.
        
        Streamlit equivalent:
            user = authenticate_user(username, password)
            if user:
                st.session_state['authenticated'] = True
        """
        user = User.query.filter_by(username=username).first()
        
        if user and self._verify_password(password, user.password_hash):
            return {
                'id': user.id,
                'username': user.username,
                'role': user.role
            }
        return None
    
    def create_user(self, username: str, password: str, role: str = 'user') -> Tuple[bool, str]:
        """
        Create new user.
        
        Streamlit equivalent:
            signup(username, password, role) dari modules/auth.py
        """
        # Validate username format
        if not (username.startswith('admin') or username.startswith('user')):
            return False, "Username must start with 'admin' or 'user'"
        
        # Check if exists
        if User.query.filter_by(username=username).first():
            return False, "Username already exists"
        
        # Hash password
        password_hash = self._hash_password(password)
        
        # Create user
        user = User(
            username=username,
            password_hash=password_hash,
            role=role
        )
        
        try:
            db.session.add(user)
            db.session.commit()
            return True, "User created successfully"
        except Exception as e:
            db.session.rollback()
            return False, f"Error creating user: {str(e)}"
    
    def _hash_password(self, password: str) -> str:
        """Hash password dengan bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash."""
        return bcrypt.checkpw(
            password.encode('utf-8'),
            password_hash.encode('utf-8')
        )
```

---

## 📄 User Model: `user.py`

```python
"""
User Model
==========
SQLAlchemy model untuk users.
"""

from datetime import datetime
from app.extensions import db


class User(db.Model):
    """User model untuk autentikasi."""
    
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'username': self.username,
            'role': self.role,
            'created_at': self.created_at.isoformat()
        }
```

---

## 🛡️ JWT Configuration

### Update `config.py`

```python
from datetime import timedelta

class Config:
    # ... existing config ...
    
    # JWT Configuration
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-dev-secret-change-in-prod')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_TOKEN_LOCATION = ['headers']
    JWT_HEADER_NAME = 'Authorization'
    JWT_HEADER_TYPE = 'Bearer'
```

### JWT Callbacks (optional)

```python
# backend/app/jwt_callbacks.py

from flask_jwt_extended import JWTManager

def configure_jwt(app):
    jwt = JWTManager(app)
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return {
            'error': 'Token has expired',
            'code': 'token_expired'
        }, 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return {
            'error': 'Invalid token',
            'code': 'invalid_token'
        }, 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return {
            'error': 'Authorization token required',
            'code': 'authorization_required'
        }, 401
```

---

## 🔄 Protected Routes (Pengganti `is_authenticated()`)

```python
# Di Streamlit:
if not is_authenticated():
    login.render_login_page()
    st.stop()

# Di Flask:
from flask_jwt_extended import jwt_required

@bp.route('/protected-endpoint')
@jwt_required()  # <-- Decorator ini menggantikan is_authenticated()
def protected_endpoint():
    return {'data': 'sensitive'}
```

---

## 👤 Role-Based Access (Pengganti `is_admin()`)

```python
# Di Streamlit:
if not is_admin():
    st.error("Admin only!")
    st.stop()

# Di Flask - buat custom decorator:
from functools import wraps
from flask_jwt_extended import get_jwt, verify_jwt_in_request

def admin_required():
    """Decorator untuk endpoint admin-only."""
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            if claims.get('role') != 'admin':
                return {'error': 'Admin access required'}, 403
            return fn(*args, **kwargs)
        return decorator
    return wrapper


# Penggunaan:
@bp.route('/admin-only')
@admin_required()
def admin_endpoint():
    return {'data': 'admin only data'}
```

---

## 🖥️ Frontend Auth Flow

### `frontend/lib/auth.ts`

```typescript
import { api } from './api';

interface User {
    username: string;
    role: 'admin' | 'user';
}

interface AuthState {
    isAuthenticated: boolean;
    user: User | null;
    token: string | null;
}

class AuthManager {
    private state: AuthState = {
        isAuthenticated: false,
        user: null,
        token: null
    };

    constructor() {
        // Load from localStorage on init
        const stored = localStorage.getItem('auth');
        if (stored) {
            const parsed = JSON.parse(stored);
            this.state = parsed;
            if (parsed.token) {
                api.setToken(parsed.token);
            }
        }
    }

    async login(username: string, password: string): Promise<boolean> {
        try {
            const response = await api.login(username, password);
            
            this.state = {
                isAuthenticated: true,
                user: response.user,
                token: response.access_token
            };
            
            // Persist to localStorage
            localStorage.setItem('auth', JSON.stringify(this.state));
            
            // Set token for future requests
            api.setToken(response.access_token);
            
            return true;
        } catch (error) {
            return false;
        }
    }

    logout(): void {
        this.state = {
            isAuthenticated: false,
            user: null,
            token: null
        };
        localStorage.removeItem('auth');
        api.setToken('');
    }

    isAuthenticated(): boolean {
        return this.state.isAuthenticated;
    }

    isAdmin(): boolean {
        return this.state.user?.role === 'admin';
    }

    getUser(): User | null {
        return this.state.user;
    }
}

export const authManager = new AuthManager();
```

### Protected Route Component (React)

```tsx
// frontend/components/ProtectedRoute.tsx

import { useRouter } from 'next/router';
import { useEffect } from 'react';
import { authManager } from '@/lib/auth';

interface Props {
    children: React.ReactNode;
    requireAdmin?: boolean;
}

export function ProtectedRoute({ children, requireAdmin = false }: Props) {
    const router = useRouter();

    useEffect(() => {
        if (!authManager.isAuthenticated()) {
            router.push('/login');
            return;
        }

        if (requireAdmin && !authManager.isAdmin()) {
            router.push('/unauthorized');
            return;
        }
    }, [router, requireAdmin]);

    if (!authManager.isAuthenticated()) {
        return <div>Loading...</div>;
    }

    return <>{children}</>;
}

// Penggunaan di page:
export default function DashboardPage() {
    return (
        <ProtectedRoute>
            <Dashboard />
        </ProtectedRoute>
    );
}
```

---

## ⏭️ Langkah Selanjutnya

Lanjut ke **[05_DATA_LAYER_MIGRATION.md](./05_DATA_LAYER_MIGRATION.md)** untuk migrasi data loader services.
