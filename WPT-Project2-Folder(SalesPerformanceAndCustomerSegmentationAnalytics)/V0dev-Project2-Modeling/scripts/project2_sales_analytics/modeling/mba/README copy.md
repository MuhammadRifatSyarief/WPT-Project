Masalahnya ada di **path yang berbeda**! Perhatikan baik-baik:

**Path yang dicari oleh pipeline:**
```
D:\CTEST\V0dev-Project2-Folder\V0dev-Project2-Modeling\scripts\project2_sales_analytics\output\features\csv\sales_details.csv
```

**Path tempat kamu meletakkan file:**
```
D:\CTEST\V0dev-Project2-Folder\V0dev-Project2-Modeling\scripts\project2_sales_analytics\modeling\output\features\csv\sales_details.csv
```

Perbedaannya adalah ada **tidak ada** folder `modeling` dalam path yang dicari pipeline. Pipeline mencari file di direktori `project2_sales_analytics\output\...`, bukan `project2_sales_analytics\modeling\output\...`.

## Solusi 1: Pindahkan file ke lokasi yang benar

```powershell
# Pindahkan file dari modeling/output ke output (satu tingkat di atas)
$source = "D:\CTEST\V0dev-Project2-Folder\V0dev-Project2-Modeling\scripts\project2_sales_analytics\modeling\output\features\csv"
$destination = "D:\CTEST\V0dev-Project2-Folder\V0dev-Project2-Modeling\scripts\project2_sales_analytics\output\features\csv"

# Buat direktori tujuan jika belum ada
New-Item -ItemType Directory -Path $destination -Force

# Pindahkan semua file CSV
Copy-Item -Path "$source\*.csv" -Destination $destination -Force

# Verifikasi
Get-ChildItem -Path $destination
```

## Solusi 2: Atau, salin langsung dari feature engineering ke lokasi yang benar

```powershell
# Salin langsung dari feature engineering ke lokasi yang benar
$source = "D:\CTEST\V0dev-Project2-Folder\V0dev-Project2-FeatureEngineering\scripts\project2_sales_analytics\feature_engineering\output\features\csv"
$destination = "D:\CTEST\V0dev-Project2-Folder\V0dev-Project2-Modeling\scripts\project2_sales_analytics\output\features\csv"

# Buat direktori tujuan jika belum ada
New-Item -ItemType Directory -Path $destination -Force

# Salin semua file CSV
Copy-Item -Path "$source\*.csv" -Destination $destination -Force

# Verifikasi
Get-ChildItem -Path $destination
```

## Solusi 3: Gunakan path relatif yang benar

Setelah file dipindahkan ke lokasi yang benar, jalankan:

```powershell
# Pastikan kamu berada di direktori modeling
cd "D:\CTEST\V0dev-Project2-Folder\V0dev-Project2-Modeling\scripts\project2_sales_analytics\modeling"

# Gunakan path relatif yang benar (ke atas satu level)
& "C:\Users\rifat syarief\AppData\Local\Programs\Python\Python310\python.exe" "mba\run_mba_pipeline.py" `
    --input "../output/features/csv/sales_details.csv" `
    --output "../output/mba" `
    --min-support 0.01 `
    --min-confidence 0.3 `
    --algorithm fpgrowth
```

## Solusi 4: Atau gunakan path absolut langsung

```powershell
& "C:\Users\rifat syarief\AppData\Local\Programs\Python\Python310\python.exe" "mba\run_mba_pipeline.py" `
    --input "D:\CTEST\V0dev-Project2-Folder\V0dev-Project2-Modeling\scripts\project2_sales_analytics\output\features\csv\sales_details.csv" `
    --output "D:\CTEST\V0dev-Project2-Folder\V0dev-Project2-Modeling\scripts\project2_sales_analytics\output\mba" `
    --min-support 0.01 `
    --min-confidence 0.3 `
    --algorithm fpgrowth
```

## **Rekomendasi:**

1. **Jalankan Solusi 2** untuk menyalin semua file dari feature engineering langsung ke lokasi yang benar
2. **Kemudian jalankan Solusi 4** dengan path absolut untuk memastikan tidak ada kesalahan path

**Intinya:** Pipeline mencari file di `...\project2_sales_analytics\output\features\csv\`, bukan di `...\project2_sales_analytics\modeling\output\features\csv\`. Kamu perlu memindahkan file ke direktori yang **sejajar dengan folder `modeling`**, bukan di dalamnya.