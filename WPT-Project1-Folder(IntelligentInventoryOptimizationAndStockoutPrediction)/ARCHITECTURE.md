# Architecture Documentation

## System Design

### Layered Architecture

\`\`\`
┌─────────────────────────────────────────┐
│         Streamlit UI Layer              │
│  (main.py - Page Routing & Navigation)  │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│        Pages Layer                      │
│  (modules/pages/*.py - Page Logic)      │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│      Core Modules Layer                 │
│  (modules/*.py - Business Logic)        │
│  - Session Manager                      │
│  - Data Loader                          │
│  - Email Utils                          │
│  - Activity Logger                      │
│  - UI Components                        │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│      Utilities Layer                    │
│  (utils/*.py - Helper Functions)        │
│  - Helpers                              │
│  - Formatters                           │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│      Configuration Layer                │
│  (config/*.py - Constants & Settings)   │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│      Data Layer                         │
│  (CSV Files & External Data Sources)    │
└─────────────────────────────────────────┘
\`\`\`

### Data Flow

\`\`\`
User Interaction
    ↓
main.py (Router)
    ↓
pages/*.py (Page Logic)
    ↓
modules/*.py (Business Logic)
    ├─ data_loader.py (Get Data)
    ├─ session_manager.py (Get Config)
    ├─ ui_components.py (Render UI)
    └─ email_utils.py (Send Email)
    ↓
utils/*.py (Formatting)
    ↓
Display Result
\`\`\`

### Module Dependencies

\`\`\`
main.py
├── config.constants
├── modules.session_manager
├── modules.data_loader
├── modules.ui_components
└── modules.activity_logger

pages/dashboard.py
├── modules.data_loader
├── modules.activity_logger
├── modules.ui_components
├── utils.formatters
├── utils.helpers
└── config.constants

modules/data_loader.py
└── config.constants

modules/ui_components.py
├── streamlit
└── config.constants

utils/helpers.py
├── pandas
└── numpy
\`\`\`

## Design Principles

### 1. Separation of Concerns
- Setiap module memiliki single responsibility
- Data logic terpisah dari UI logic
- Configuration terpisah dari implementation

### 2. DRY (Don't Repeat Yourself)
- Reusable components di ui_components.py
- Helper functions di utils/
- Constants di config/

### 3. Maintainability
- Clear naming conventions
- Comprehensive documentation
- Consistent code structure

### 4. Scalability
- Easy to add new pages
- Easy to add new utilities
- Modular design supports growth

## Extension Points

### Adding New Page
1. Create `modules/pages/new_page.py`
2. Implement `render_page()` function
3. Add routing in `main.py`
4. Update `PAGES` in `config/constants.py`

### Adding New Utility
1. Create function in `utils/helpers.py` or `utils/formatters.py`
2. Add documentation
3. Import where needed

### Adding New Module
1. Create `modules/new_module.py`
2. Implement core functions
3. Add to `modules/__init__.py`
4. Import in relevant files

## Performance Considerations

### Caching Strategy
- Data caching via `@st.cache_data` (1 hour TTL)
- Manual refresh available
- Session state for user interactions

### Optimization Tips
- Load data once, pass around
- Filter early for large datasets
- Use column selection to reduce memory
- Lazy load expensive computations

## Security Considerations

### Email Handling
- Validate emails before sending
- Use app passwords (Gmail)
- Don't expose passwords in code

### Data Access
- Implement row-level security if needed
- Validate user inputs
- Sanitize external data

## Testing Strategy

\`\`\`
Unit Tests
├── test_helpers.py
├── test_formatters.py
└── test_session_manager.py

Integration Tests
├── test_data_loader.py
├── test_email_utils.py
└── test_ui_components.py

End-to-End Tests
└── test_pages.py
\`\`\`

## Deployment Checklist

- [ ] Update version in constants.py
- [ ] Test all pages
- [ ] Clear cache
- [ ] Update README
- [ ] Review requirements.txt
- [ ] Test email functionality
- [ ] Performance optimization
- [ ] Security review
- [ ] Deploy to production
- [ ] Monitor logs
