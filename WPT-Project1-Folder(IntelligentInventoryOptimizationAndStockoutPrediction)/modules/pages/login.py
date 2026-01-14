"""
Login Page - Optimized Dark Theme Layout
==========================================
Professional dark-themed login page with balanced layout and no empty spaces.
Following international UI/UX principles: visual hierarchy, balance, and content density.
"""

import streamlit as st
from modules.auth import login, signup, is_authenticated, logout


def render_login_page():
    """Render the optimized dark-themed login page with balanced layout."""
    
    # Dark theme CSS with optimized layout
    st.markdown("""
        <style>
        /* Hide Streamlit default elements */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* Dark background */
        .stApp {
            background: #0f172a;
        }
        [data-testid="stAppViewContainer"] {
            background: #0f172a;
        }
        [data-testid="stVerticalBlock"] {
            background: #0f172a;
        }
        
        /* Login card - dark theme */
        .login-card {
            background: #1e293b;
            border-radius: 16px;
            padding: 2rem;
            border: 1px solid #334155;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
            margin-bottom: 1.5rem;
        }
        
        .login-header h1 {
            color: #f1f5f9;
            font-size: 1.75rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }
        
        .login-header p {
            color: #94a3b8;
            font-size: 0.9rem;
            margin-bottom: 1.5rem;
        }
        
        /* Form inputs - dark theme */
        .stTextInput>div>div>input {
            background-color: #0f172a;
            border: 1px solid #334155;
            border-radius: 8px;
            color: #f1f5f9;
            padding: 0.75rem 1rem;
        }
        
        .stTextInput>div>div>input:focus {
            border-color: #6366f1;
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
        }
        
        .stTextInput label {
            color: #cbd5e1;
            font-weight: 500;
            font-size: 0.875rem;
        }
        
        /* Selectbox - dark theme */
        .stSelectbox>div>div {
            background-color: #0f172a;
            border: 1px solid #334155;
            border-radius: 8px;
            color: #f1f5f9;
        }
        
        /* Buttons - dark theme */
        .stButton>button {
            width: 100%;
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 0.75rem 1.5rem;
            font-weight: 600;
            transition: all 0.3s ease;
            margin-top: 1rem;
        }
        
        .stButton>button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(99, 102, 241, 0.4);
        }
        
        /* Tabs - dark theme */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.5rem;
            margin-bottom: 1.5rem;
            background: #0f172a;
            border-radius: 8px;
            padding: 0.25rem;
        }
        
        .stTabs [data-baseweb="tab"] {
            border-radius: 6px;
            padding: 0.5rem 1rem;
            color: #94a3b8;
            transition: all 0.3s ease;
        }
        
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            color: white;
        }
        
        /* Expander styling - dark theme */
        .streamlit-expanderHeader {
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 10px;
            padding: 0.75rem 1rem;
            color: #f1f5f9;
            font-weight: 600;
            font-size: 0.875rem;
        }
        
        .streamlit-expanderHeader:hover {
            border-color: #6366f1;
            background: #1e293b;
        }
        
        .streamlit-expanderContent {
            background: #0f172a;
            border: 1px solid #334155;
            border-top: none;
            border-radius: 0 0 10px 10px;
            padding: 1rem;
            margin-top: 0.5rem;
        }
        
        /* Info box - dark theme */
        .info-box {
            background: #0f172a;
            border-left: 3px solid #6366f1;
            border-radius: 6px;
            padding: 1rem;
            margin-bottom: 1.5rem;
            color: #cbd5e1;
            font-size: 0.875rem;
        }
        
        .info-box code {
            background: #1e293b;
            padding: 0.2rem 0.4rem;
            border-radius: 4px;
            color: #8b5cf6;
        }
        
        /* Left column additional sections */
        .left-section {
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1rem;
        }
        
        .left-section-title {
            color: #f1f5f9;
            font-size: 1rem;
            font-weight: 600;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .left-section-content {
            color: #cbd5e1;
            font-size: 0.85rem;
            line-height: 1.6;
        }
        
        .benefit-item {
            display: flex;
            align-items: flex-start;
            gap: 0.75rem;
            margin-bottom: 0.75rem;
            padding: 0.75rem;
            background: #0f172a;
            border-radius: 8px;
            border: 1px solid #334155;
        }
        
        .benefit-icon {
            font-size: 1.25rem;
            flex-shrink: 0;
        }
        
        .benefit-text {
            flex: 1;
        }
        
        .benefit-title {
            color: #f1f5f9;
            font-weight: 600;
            font-size: 0.875rem;
            margin-bottom: 0.25rem;
        }
        
        .benefit-desc {
            color: #94a3b8;
            font-size: 0.8rem;
        }
        
        .stat-item {
            text-align: center;
            padding: 1rem;
            background: #0f172a;
            border-radius: 10px;
            border: 1px solid #334155;
        }
        
        .stat-value {
            color: #8b5cf6;
            font-size: 1.5rem;
            font-weight: 700;
            margin-bottom: 0.25rem;
        }
        
        .stat-label {
            color: #94a3b8;
            font-size: 0.8rem;
        }
        
        /* Overview section - right side */
        .overview-container {
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            border-radius: 16px;
            padding: 2rem;
            border: 1px solid #334155;
        }
        
        .overview-title {
            color: #f1f5f9;
            font-size: 1.75rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }
        
        .overview-subtitle {
            color: #94a3b8;
            font-size: 0.9rem;
            margin-bottom: 1.5rem;
        }
        
        /* Company info sections */
        .company-section {
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 10px;
            padding: 1.25rem;
            margin-bottom: 1rem;
        }
        
        .company-section-title {
            color: #f1f5f9;
            font-size: 0.95rem;
            font-weight: 600;
            margin-bottom: 0.75rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .company-section-content {
            color: #cbd5e1;
            font-size: 0.8rem;
            line-height: 1.6;
        }
        
        .company-section-content a {
            color: #8b5cf6;
            text-decoration: none;
        }
        
        .company-section-content a:hover {
            text-decoration: underline;
        }
        
        /* Success/Error messages - dark theme */
        .stSuccess {
            background: #064e3b;
            border: 1px solid #10b981;
            color: #6ee7b7;
        }
        
        .stError {
            background: #7f1d1d;
            border: 1px solid #ef4444;
            color: #fca5a5;
        }
        
        .stInfo {
            background: #1e3a8a;
            border: 1px solid #3b82f6;
            color: #93c5fd;
        }
        
        /* Role badges */
        .role-badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 600;
            margin-left: 0.5rem;
        }
        
        .role-admin {
            background: #7f1d1d;
            color: #fca5a5;
        }
        
        .role-user {
            background: #1e3a8a;
            color: #93c5fd;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Split layout: Login (left) and Overview (right) - balanced proportions
    col_left, col_right = st.columns([1, 1], gap="large")
    
    # LEFT COLUMN: Login Form + Additional Content
    with col_left:
        # Login Card
        st.markdown("""
            <div class="login-card">
                <div class="login-header">
                    <h1>🔐 Welcome Back</h1>
                    <p>Sign in to access your dashboard</p>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Tabs
        tab1, tab2 = st.tabs(["Sign In", "Sign Up"])
        
        # Sign In Tab
        with tab1:
            with st.form("signin_form", clear_on_submit=False):
                username = st.text_input(
                    "Username",
                    placeholder="admin1, user1, etc.",
                    key="signin_username"
                )
                
                password = st.text_input(
                    "Password",
                    type="password",
                    placeholder="Enter your password",
                    key="signin_password"
                )
                
                submit_button = st.form_submit_button("Sign In →", use_container_width=True, type="primary")
                
                if submit_button:
                    if not username or not password:
                        st.error("⚠️ Please fill in all required fields")
                    else:
                        with st.spinner("Authenticating..."):
                            success, message = login(username, password)
                            if success:
                                st.success(f"✅ {message}")
                                st.balloons()
                                st.rerun()
                            else:
                                st.error(f"❌ {message}")
        
        # Sign Up Tab
        with tab2:
            st.markdown("""
                <div class="info-box">
                    <strong>📋 Account Format:</strong><br>
                    • Username: <code>admin</code> or <code>user</code> + number<br>
                    • Password: <code>{username}!wahana25</code><br>
                    • Example: <code>admin2</code> / <code>admin2!wahana25</code>
                </div>
            """, unsafe_allow_html=True)
            
            with st.form("signup_form", clear_on_submit=False):
                new_username = st.text_input(
                    "New Username",
                    placeholder="admin2, user2, etc.",
                    key="signup_username"
                )
                
                new_password = st.text_input(
                    "New Password",
                    type="password",
                    placeholder="admin2!wahana25",
                    key="signup_password"
                )
                
                user_role = st.selectbox(
                    "Role",
                    ["admin", "user"],
                    help="Admin: Full access | User: View only",
                    key="signup_role"
                )
                
                if user_role == "admin":
                    st.info("🔴 **Admin**: Full access (view, edit, delete)")
                else:
                    st.info("🔵 **User**: Read-only access")
                
                submit_button = st.form_submit_button("Create Account →", use_container_width=True, type="primary")
                
                if submit_button:
                    if not new_username or not new_password:
                        st.error("⚠️ Please fill in all required fields")
                    else:
                        with st.spinner("Creating account..."):
                            success, message = signup(new_username, new_password, user_role)
                            if success:
                                st.success(f"✅ {message}")
                                st.info("💡 You can now sign in")
                                st.balloons()
                            else:
                                st.error(f"❌ {message}")
        
        # Additional Content Below Login - System Highlights
        st.markdown("""
            <div class="left-section">
                <div class="left-section-title">✨ System Highlights</div>
                <div class="left-section-content">
        """, unsafe_allow_html=True)
        
        benefits = [
            {"icon": "🔒", "title": "Secure Authentication", "desc": "Role-based access control with encrypted credentials"},
            {"icon": "📊", "title": "Real-time Analytics", "desc": "Live data synchronization and instant insights"},
            {"icon": "🤖", "title": "AI-Powered Predictions", "desc": "Machine learning models for accurate forecasting"},
            {"icon": "⚡", "title": "High Performance", "desc": "Optimized for speed and scalability"}
        ]
        
        for benefit in benefits:
            st.markdown(f"""
                <div class="benefit-item">
                    <span class="benefit-icon">{benefit['icon']}</span>
                    <div class="benefit-text">
                        <div class="benefit-title">{benefit['title']}</div>
                        <div class="benefit-desc">{benefit['desc']}</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        
        st.markdown("</div></div>", unsafe_allow_html=True)
        
        # Quick Stats Section
        st.markdown("""
            <div class="left-section">
                <div class="left-section-title">📈 Platform Statistics</div>
        """, unsafe_allow_html=True)
        
        stats_cols = st.columns(2)
        with stats_cols[0]:
            st.markdown("""
                <div class="stat-item">
                    <div class="stat-value">2,136+</div>
                    <div class="stat-label">Products</div>
                </div>
            """, unsafe_allow_html=True)
        
        with stats_cols[1]:
            st.markdown("""
                <div class="stat-item">
                    <div class="stat-value">8</div>
                    <div class="stat-label">Features</div>
                </div>
            """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Technology Stack
        st.markdown("""
            <div class="left-section">
                <div class="left-section-title">🛠️ Technology Stack</div>
                <div class="left-section-content">
                    <div style="display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.5rem;">
                        <span style="background: #0f172a; padding: 0.4rem 0.8rem; border-radius: 6px; border: 1px solid #334155; color: #cbd5e1; font-size: 0.75rem;">Python</span>
                        <span style="background: #0f172a; padding: 0.4rem 0.8rem; border-radius: 6px; border: 1px solid #334155; color: #cbd5e1; font-size: 0.75rem;">Streamlit</span>
                        <span style="background: #0f172a; padding: 0.4rem 0.8rem; border-radius: 6px; border: 1px solid #334155; color: #cbd5e1; font-size: 0.75rem;">PostgreSQL</span>
                        <span style="background: #0f172a; padding: 0.4rem 0.8rem; border-radius: 6px; border: 1px solid #334155; color: #cbd5e1; font-size: 0.75rem;">ML/AI</span>
                        <span style="background: #0f172a; padding: 0.4rem 0.8rem; border-radius: 6px; border: 1px solid #334155; color: #cbd5e1; font-size: 0.75rem;">Pandas</span>
                        <span style="background: #0f172a; padding: 0.4rem 0.8rem; border-radius: 6px; border: 1px solid #334155; color: #cbd5e1; font-size: 0.75rem;">Plotly</span>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    # RIGHT COLUMN: Feature Overview & Company Info
    with col_right:
        st.markdown("""
            <div class="overview-container">
                <div class="overview-title">🏢 Wahana Piranti Teknologi</div>
                <div class="overview-subtitle">Indonesia's leading IT & Technology Solutions Distributor</div>
                <div style="margin-top: 1rem; padding: 1rem; background: #0f172a; border-radius: 10px; border: 1px solid #334155;">
                    <div style="color: #f1f5f9; font-size: 1rem; font-weight: 600; margin-bottom: 0.5rem; display: flex; align-items: center; gap: 0.5rem;">
                        📦 Inventory Intelligence
                    </div>
                    <div style="color: #94a3b8; font-size: 0.85rem; line-height: 1.5;">
                        Comprehensive inventory management and analytics platform
                    </div>
                </div>
        """, unsafe_allow_html=True)
        
        # Feature cards in grid layout
        features = [
            {
                "icon": "🏠",
                "title": "Dashboard",
                "detail": "Real-time inventory metrics, KPIs, service levels, turnover ratios, and comprehensive visual analytics dashboard with interactive charts and graphs."
            },
            {
                "icon": "📈",
                "title": "Forecasting",
                "detail": "AI-powered demand prediction using machine learning models. Forecast future inventory needs with time series analysis and trend prediction algorithms."
            },
            {
                "icon": "📊",
                "title": "Health",
                "detail": "Monitor inventory health scores, ABC classification, turnover ratios, service levels, and identify products requiring attention."
            },
            {
                "icon": "⚠️",
                "title": "Stockout",
                "detail": "Early warning system for potential stockouts with risk assessment. Predict days until stockout and prioritize critical products."
            },
            {
                "icon": "🔄",
                "title": "Reorder",
                "detail": "Intelligent reorder point calculation and safety stock optimization using EOQ models and service level targets."
            },
            {
                "icon": "📋",
                "title": "Slow-Moving",
                "detail": "Identify and analyze slow-moving products, dead stock, and inventory aging to optimize warehouse space and reduce holding costs."
            },
            {
                "icon": "👥",
                "title": "RFM",
                "detail": "Customer segmentation using Recency, Frequency, and Monetary analysis. Classify customers into Champions, Loyal, At Risk, and more."
            },
            {
                "icon": "🛒",
                "title": "MBA",
                "detail": "Market Basket Analysis to discover product associations, cross-selling opportunities, and customer buying patterns using association rules."
            }
        ]
        
        # Display features in 2-column grid using Streamlit columns
        cols = st.columns(2)
        
        for i, feature in enumerate(features):
            col_idx = i % 2
            with cols[col_idx]:
                # Use expander for compact grid layout with details
                with st.expander(f"{feature['icon']} {feature['title']}", expanded=False):
                    st.markdown(f"""
                        <div style="color: #cbd5e1; font-size: 0.85rem; line-height: 1.6; padding: 0.5rem 0;">
                            {feature['detail']}
                        </div>
                    """, unsafe_allow_html=True)
        
        # Company Information Sections
        st.markdown("""
            <div style="margin-top: 1.5rem;">
        """, unsafe_allow_html=True)
        
        # About Us
        st.markdown("""
            <div class="company-section">
                <div class="company-section-title">
                    📖 About Us
                </div>
                <div class="company-section-content">
                    Founded in 2015, Wahana Piranti Teknologi (or Wahana in short) started as a distributor of premium brands IT within solutions within Jakarta. Over the years, through sheer professionalism and a strong focus on customer servicing, Wahana has been entrusted by more and more international and reputable brands that seek to expand their market and outreach throughout Indonesia.<br><br>
                    Underpinned by its strong local networks and understanding of the Indonesia's market scene, Wahana has also progressed from just being a product distributor to a one-stop that provides end-to-end service, for its premium brand partners. Today, Wahana operates throughout Indonesia archipelago through its vast wide network of experience resellers, technical professionals and enterprise IT consultants, in delivering a multitude of premium brands of IT solutions and services.
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Vision & Mission
        st.markdown("""
            <div class="company-section">
                <div class="company-section-title">
                    🎯 Vision & Mission
                </div>
                <div class="company-section-content">
                    <strong style="color: #8b5cf6;">Vision:</strong><br>
                    To be Indonesia's trusted one-stop distributor and system architect for affordable and cutting-edge enterprise IT solutions.<br><br>
                    <strong style="color: #8b5cf6;">Mission:</strong><br>
                    We deliver the latest, most reliable and very affordable IT and end-to-end technology solutions for enterprises.
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Office Location & Contact in 2 columns
        contact_cols = st.columns(2)
        
        with contact_cols[0]:
            st.markdown("""
                <div class="company-section">
                    <div class="company-section-title">
                        📍 Office Location
                    </div>
                    <div class="company-section-content">
                        Grand Puri Niaga K6 2M-2L<br>
                        Jl. Puri Kencana, Kembangan<br>
                        Jakarta Barat, 11610<br>
                        Indonesia
                    </div>
                </div>
            """, unsafe_allow_html=True)
        
        with contact_cols[1]:
            st.markdown("""
                <div class="company-section">
                    <div class="company-section-title">
                        📞 Contact Us
                    </div>
                    <div class="company-section-content">
                        <strong>Email:</strong><br>
                        <a href="mailto:sales@wpteknologi.com">sales@wpteknologi.com</a><br><br>
                        <strong>Phone:</strong><br>
                        021 38771011<br><br>
                        <strong>Mobile:</strong><br>
                        +62 858 1075 7246
                    </div>
                </div>
            """, unsafe_allow_html=True)
        
        st.markdown("</div></div>", unsafe_allow_html=True)
    
    # Show current user info if logged in (shouldn't appear, but just in case)
    if is_authenticated():
        st.markdown("---")
        role = st.session_state.get('role', 'user')
        role_class = "role-admin" if role == "admin" else "role-user"
        role_icon = "🔴" if role == "admin" else "🔵"
        
        st.info(f"""
        Currently logged in as: **{st.session_state.get('username')}** 
        <span class="role-badge {role_class}">{role_icon} {role.upper()}</span>
        """, unsafe_allow_html=True)
        
        if st.button("🚪 Logout", use_container_width=True):
            logout()
            st.rerun()
