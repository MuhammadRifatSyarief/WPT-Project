# Project 2: Sales Performance & Customer Segmentation Analytics

## Overview

Aplikasi modular untuk analisis performa penjualan dan segmentasi pelanggan menggunakan data dari Accurate Online API.

### Fitur Utama

1. **RFM Analysis (Recency, Frequency, Monetary)**
   - Segmentasi pelanggan berdasarkan perilaku pembelian
   - Identifikasi pelanggan loyal, at-risk, dan churning
   - Rekomendasi aksi per segmen

2. **Market Basket Analysis**
   - Analisis produk yang sering dibeli bersamaan
   - Rekomendasi cross-selling dan up-selling
   - Association rules dengan support, confidence, lift

## Struktur Direktori

\`\`\`
project2_sales_analytics/
│
├── main.py                          # Entry point utama
│
├── config/
│   └── constants.py                 # Konfigurasi global & konstanta
│
├── modules/
│   ├── __init__.py                  
│   ├── api_client.py                # API client untuk Accurate Online
│   ├── data_puller.py               # Data fetching & caching
│   ├── rfm_analyzer.py              # RFM Analysis
│   ├── market_basket_analyzer.py    # Market Basket Analysis
│   └── data_enricher.py             # Data enrichment & preprocessing
│
├── utils/
│   ├── __init__.py                  
│   ├── helpers.py                   # Helper functions
│   └── exporters.py                 # Excel/CSV export utilities
│
└── README.md                        # Dokumentasi ini
\`\`\`

## Instalasi

\`\`\`bash
pip install pandas numpy requests pytz openpyxl
\`\`\`

## Penggunaan

### 1. Konfigurasi

Edit `main.py` dan masukkan credentials API:

\`\`\`python
API_TOKEN = "your_api_token_here"
SIGNATURE_SECRET = "your_signature_secret_here"
\`\`\`

### 2. Menjalankan Analisis

\`\`\`bash
cd scripts/project2_sales_analytics
python main.py
\`\`\`

### 3. Penggunaan Programmatic

\`\`\`python
from main import run_sales_analytics

results = run_sales_analytics(
    api_token="your_token",
    signature_secret="your_secret",
    start_date="01/01/2024",
    end_date="31/12/2024"
)
\`\`\`

## Output

Hasil analisis di-export ke file Excel dengan sheets:

1. **1_RFM_Analysis** - Hasil RFM per pelanggan
2. **2_Customer_Segments** - Metrik per segmen
3. **3_Market_Basket** - Association rules
4. **4_Product_Associations** - Produk frequently bought together
5. **5_Sales_By_Customer** - Agregasi penjualan per pelanggan
6. **6_Sales_By_Product** - Agregasi penjualan per produk
7. **7_Customer_Master** - Data master pelanggan
8. **8_Item_Master** - Data master item
9. **9_Summary_Stats** - Statistik ringkasan

## RFM Segments

| Segment | Deskripsi | Aksi Rekomendasi |
|---------|-----------|------------------|
| Champions | Best customers | Reward, early adopters |
| Loyal Customers | High value regulars | Upsell, engage |
| Potential Loyalist | Recent with potential | Loyalty program |
| At Risk | Previously active | Win back campaigns |
| Cannot Lose Them | Highest value at risk | Personal outreach |
| Hibernating | Long inactive | Special offers |

## API Endpoints yang Digunakan

- `/api/customer/list.do` - Master pelanggan
- `/api/item/list.do` - Master item
- `/api/sales-invoice/list.do` - Daftar faktur penjualan
- `/api/sales-invoice/detail.do` - Detail faktur

## Checkpoint & Resume

Aplikasi menyimpan progress secara otomatis. Jika terputus, jalankan ulang dan pilih "y" untuk melanjutkan dari checkpoint.

## Konfigurasi Lanjutan

Edit `config/constants.py` untuk mengubah:

- Threshold RFM scoring
- Minimum support/confidence Market Basket
- Rate limiting API
- Format tanggal & currency

---

**Author:** v0  
**Version:** 1.0  
**Created:** 2025
