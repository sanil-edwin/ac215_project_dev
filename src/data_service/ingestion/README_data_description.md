# AgriGuard Data Ingestion Documentation - Corn-Masked Indicators

**Project:** AgriGuard  
**GCS Bucket:** `gs://agriguard-ac215-data`  
**Last Updated:** November 15, 2025  
**Last Validated:** November 15, 2025  
**Validation Status:** ✅ Verified against GCS data

---

## Table of Contents

1. [Overview](#overview)
2. [Bucket Structure](#bucket-structure)
3. [Data Categories](#data-categories)
   - [Corn Yields](#1-corn-yields)
   - [MODIS Satellite Indicators (Corn-Masked)](#2-modis-satellite-indicators-corn-masked)
   - [Weather Data](#3-weather-data)
   - [Corn Field Masks](#4-corn-field-masks)
4. [Data Quality & Validation](#data-quality--validation)
5. [Update Schedule](#update-schedule)
6. [Contact & Support](#contact--support)

---

## Overview

This dataset includes **seven corn-masked indicators** (NDVI, LST, VPD, ETo, Precipitation, Water Deficit) and yield data covering all 99 Iowa counties from 2016-2025. Using USDA Cropland Data Layer masks to extract values only from corn field pixels, this provides more accurate data for corn stress detection and yield forecasting than county-wide aggregations.

### Key Statistics

| Metric | Value |
|--------|-------|
| **Spatial Coverage** | All 99 Iowa counties |
| **Temporal Coverage** | 2016-05-01 to 2025-10-30 |
| **Growing Seasons** | May 1 - October 31 annually (corn season only) |
| **Total Records** | 770,547 across corn-masked datasets |
| **Data Categories** | 7 corn-masked indicators (NDVI, LST, VPD, ETo, Precipitation, Water Deficit) + yields |
| **Masking Method** | USDA CDL corn classification (year-specific) |
| **Update Frequency** | Weekly during growing season |

---

## Bucket Structure

## Bucket Structure

```
gs://agriguard-ac215-data/data_raw/
│
├── masks/                                      # Corn field identification masks
│   ├── iowa_counties.geojson                  # County boundaries (99 counties)
│   └── corn/                                   # USDA CDL corn masks
│       ├── iowa_corn_mask_2010.tif           
│       ├── ...
│       └── iowa_corn_mask_2024.tif           
│
└── yields/                                     # USDA NASS corn yield data
    ├── iowa_corn_yields_2010_2025.csv         # Combined dataset
    ├── iowa_corn_yields_2010.csv              
    ├── ...       
    └── iowa_corn_yields_2024.csv              
```

```
gs://agriguard-ac215-data/data_raw_new/
│
├── modis/                                     # Corn-masked MODIS indicators
│   ├── ndvi/
│   │   └── iowa_corn_ndvi_20160501_20251031.parquet
│   └── lst/
│       └── iowa_corn_lst_20160501_20251031.parquet
│
└── weather/                                   # Weather data (corn season only)
    ├── vpd/
    │   ├── yearly/                            # Year-specific files
    │   │   ├── iowa_corn_vpd_2016.parquet
    │   │   ├── iowa_corn_vpd_2017.parquet
    │   │   ├── ...
    │   │   └── iowa_corn_vpd_2025.parquet
    │   └── iowa_corn_vpd_20160501_20251031.parquet  # Merged file
    │
    ├── eto/                                   # Reference Evapotranspiration
    │   ├── yearly/
    │   │   ├── iowa_corn_eto_2016.parquet
    │   │   ├── iowa_corn_eto_2017.parquet
    │   │   ├── ...
    │   │   └── iowa_corn_eto_2025.parquet
    │   └── iowa_corn_eto_20160501_20251031.parquet  # Merged file
    │
    ├── pr/                                    # Precipitation 
    │   ├── yearly/
    │   │   ├── iowa_corn_pr_2016.parquet
    │   │   ├── iowa_corn_pr_2017.parquet
    │   │   ├── ...
    │   │   └── iowa_corn_pr_2025.parquet
    │   └── iowa_corn_pr_20160501_20251031.parquet   # Merged file
    │
    └── water_deficit/                         # Water Stress Indicator
        └── iowa_corn_water_deficit_20160501_20251031.parquet
```

---

## Data Categories

## 1. Corn Yields

**Location:** `gs://agriguard-ac215-data/data_raw/yields/`  
**Source:** USDA NASS Quick Stats API  
**Purpose:** Ground truth yield data for model training and validation  
**Total Records:** 1,416

### File Details

- **Combined Dataset:** `iowa_corn_yields_2010_2024.csv` (all years)
- **Individual Years:** `iowa_corn_yields_YYYY.csv` (2010-2024, 15 files)
- **Format:** CSV
- **Coverage:** 101 unique county-year combinations (includes 99 current Iowa counties)

### Schema

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `year` | int | Harvest year | `2016` |
| `state` | string | State name | `IOWA` |
| `state_fips` | string | State FIPS code | `19` |
| `county` | string | County name | `ADAIR` |
| `county_fips` | string | County FIPS code | `1` |
| `yield_bu_per_acre` | float | Corn yield (bushels/acre) | `185.3` |
| `unit` | string | Unit of measurement | `BU / ACRE` |
| `fips` | string | Combined FIPS (state+county) | `19001` |

### Yield Value Ranges

**Historical Range (2010-2024):**
- **Minimum:** 44.5 bu/acre (2012 historic drought)
- **Maximum:** 240.9 bu/acre (optimal conditions)
- **Mean:** 181.9 bu/acre
- **Typical Range:** 120-220 bu/acre
- **Severe Drought:** <80 bu/acre (2012)
- **Excellent Conditions:** >200 bu/acre

**Note:** The 101 counties reflect historical data that may include counties with boundary or reporting changes over the 15-year period.

### Data Source Details

- **API:** [USDA NASS Quick Stats](https://quickstats.nass.usda.gov/api)
- **Collection Method:** Survey-based (official USDA estimates)
- **Release Schedule:** Annual, typically January following harvest
- **Coverage:** Complete for all 99 Iowa counties

---

## 2. MODIS Satellite Indicators (Corn-Masked)

**Location:** `gs://agriguard-ac215-data/data_raw_new/modis/`  
**Source:** Google Earth Engine (NASA MODIS products)  
**Purpose:** Corn-specific crop stress monitoring  
**Masking:** USDA Cropland Data Layer (CDL) corn classification

All MODIS data is **corn-masked and county-aggregated** (mean, std, min, max per county) covering **May 1, 2016 to October 31, 2025** (corn growing season only).

### Corn Masking Methodology

Each satellite observation is masked using the USDA CDL corn classification layer for the corresponding year:
- **2016-2024 data:** Uses year-specific CDL corn masks
- **2025 data:** Uses 2024 CDL mask (most recent available)
- **Masking Process:** Only pixels classified as "Corn" (CDL value = 1) are included in aggregation
- **Benefit:** Eliminates contamination from soybeans, forests, urban areas, water bodies

### Common Schema for All Corn-Masked MODIS Products

| Column | Type | Description |
|--------|------|-------------|
| `fips` | string | 5-digit county FIPS code |
| `county_name` | string | County name |
| `date` | string | Observation date (YYYY-MM-DD) |
| `mean` | float | County-wide mean value (corn fields only) |
| `std` | float | Standard deviation across corn fields |
| `min` | float | Minimum value in corn fields |
| `max` | float | Maximum value in corn fields |
| `mask_year` | int | CDL mask year used for this observation |

---

### 2.1 NDVI (Normalized Difference Vegetation Index) - Corn-Masked

**File:** `modis/ndvi/iowa_corn_ndvi_20160501_20251031.parquet`  
**Source:** MOD13A1.061 (MODIS Vegetation Indices)  
**Resolution:** 500m, 16-day composites  
**Total Records:** 11,187  
**Date Range:** 2016-05-08 to 2025-10-16  
**Corn Masking:** USDA CDL 2016-2024

**Coverage:**
- **Years:** 2016-2025 (10 growing seasons)
- **Months:** May-October only (corn season)
- **Counties:** All 99 Iowa counties
- **Records per year:** ~1,089-1,188 (varies by year and data availability)

**Use Cases:**
- Corn vegetation health monitoring
- Canopy density tracking for corn fields
- Early season corn growth assessment
- Corn-specific stress detection

**Typical Values (Iowa Corn Fields):**
- **Planting (May):** 0.20-0.40 (emergence)
- **Vegetative (June-July):** 0.40-0.70 (rapid growth)
- **Peak (July-Aug):** 0.70-0.93 (full canopy)
- **Maturity (Sept-Oct):** 0.40-0.60 (senescence)

**Actual Value Range (Corn Fields 2016-2025):**
- **Minimum:** 0.198
- **Maximum:** 0.931
- **Mean:** 0.630
- **Std Dev:** 0.211

**Stress Thresholds:**
- **Healthy Corn:** NDVI > 0.60
- **Moderate Stress:** NDVI 0.40-0.60
- **Severe Stress:** NDVI < 0.40

---

### 2.2 ET (Evapotranspiration) - Corn-Masked

**File:** `modis/et/iowa_corn_et_20160501_20251031.parquet`  
**Source:** OpenET ENSEMBLE v2.0 (CONUS/GRIDMET/MONTHLY)  
**Resolution:** 30m, monthly composites  
**Total Records:** 10,593  
**Date Range:** 2016-05-01 to 2024-10-01  
**Corn Masking:** USDA CDL 2016-2024

**Coverage:**
- **Years:** 2016-2024 (9 growing seasons)
- **Months:** May-October only
- **Counties:** All 99 Iowa counties
- **Records per year:** ~1,089-1,188

**Variables:**
- `et_ensemble_mad`: Actual evapotranspiration ensemble (mm/month)

**Use Cases:**
- Corn water stress detection
- Drought impact assessment on corn
- Irrigation management for corn fields
- Crop water use monitoring

**Typical Values (Iowa Corn Fields):**
- **May (Emergence):** 40-60 mm/month
- **June-July (Vegetative):** 80-120 mm/month
- **July-August (Peak):** 100-150 mm/month
- **September-October (Maturity):** 40-80 mm/month

**Actual Value Range (Corn Fields 2016-2024):**
- **Minimum:** 19.9 mm/month
- **Maximum:** 186.2 mm/month
- **Mean:** 93.8 mm/month
- **Std Dev:** 41.6 mm/month

**Water Stress Indicators:**
- **Well-Watered Corn:** ET > 90 mm/month (July-Aug)
- **Moderate Stress:** ET 60-90 mm/month
- **Severe Stress:** ET < 60 mm/month during peak growth

**Note:** 2025 data not yet available in OpenET dataset. Some early-season records may contain NaN values due to data latency.

---

### 2.3 LST (Land Surface Temperature) - Corn-Masked

**File:** `modis/lst/iowa_corn_lst_20160501_20251031.parquet`  
**Source:** MOD11A2.061 (MODIS LST)  
**Resolution:** 1km, 8-day composites  
**Total Records:** 22,770  
**Date Range:** 2016-05-08 to 2025-10-24  
**Corn Masking:** USDA CDL 2016-2024

**Coverage:**
- **Years:** 2016-2025 (10 growing seasons)
- **Months:** May-October only
- **Counties:** All 99 Iowa counties
- **Records per year:** 2,277 (23 8-day periods × 99 counties)

**Variables:**
- `LST_Day_1km`: Daytime land surface temperature (°C)

**Use Cases:**
- Corn heat stress monitoring
- Temperature-based stress detection
- Pollination period monitoring (critical during tasseling)
- Growing degree day calculations for corn

**Typical Values (Iowa Corn Fields):**
- **May (Planting):** 15-25°C
- **June-July (Vegetative):** 25-32°C
- **July-August (Reproductive):** 28-35°C
- **September-October (Maturity):** 15-28°C

**Actual Value Range (Corn Fields 2016-2025):**
- **Minimum:** -0.17°C (early May cold snap)
- **Maximum:** 44.0°C (extreme heat event)
- **Mean:** 26.3°C
- **Std Dev:** 5.6°C

**Heat Stress Thresholds for Corn:**
- **Optimal:** LST 25-30°C
- **Moderate Stress:** LST 30-35°C
- **Severe Stress:** LST 35-38°C
- **Critical Damage:** LST > 38°C (especially during pollination)

**Critical Period:** July 15 - August 15 (tasseling/pollination)
- **Optimal Temp:** < 32°C
- **Stress Threshold:** > 35°C can cause pollen sterility

---

## 3. Weather Data

**Location:** `gs://agriguard-ac215-data/data_raw_new/weather/`  
**Purpose:** Meteorological context for corn stress analysis  
**Coverage:** May-October (corn season) only

### Common Schema for Weather Products

| Column | Type | Description |
|--------|------|-------------|
| `fips` | string | 5-digit county FIPS code |
| `county_name` | string | County name |
| `date` | string | Observation date |
| `mean` | float | County-wide mean value |
| `std` | float | Standard deviation |
| `min` | float | Minimum value |
| `max` | float | Maximum value |
| `mask_year` | int | CDL mask year used (for corn-masked products) |

---

### 3.1 VPD (Vapor Pressure Deficit) - Corn-Masked

**File:** `weather/vpd/iowa_corn_vpd_20160501_20251031.parquet`  
**Source:** gridMET (IDAHO_EPSCOR/GRIDMET)  
**Resolution:** 4km, daily  
**Total Records:** 181,170  
**Date Range:** 2016-05-01 to 2025-10-30  
**Corn Masking:** USDA CDL 2016-2024

**Coverage:**
- **Years:** 2016-2025 (10 growing seasons)
- **Months:** May-October only (corn season)
- **Counties:** All 99 Iowa counties
- **Records per year:** 18,117 per year (183 days × 99 counties)

**Mask Details:**
- **2016-2024 data:** Uses year-specific CDL corn masks
- **2025 data:** Uses 2024 CDL mask (most recent available)

**Schema:**
- `date`: Observation date (YYYY-MM-DD)
- `fips`: 5-digit county FIPS code
- `county_name`: County name
- `mean`: County-wide mean VPD (kPa) across corn fields
- `std`: Standard deviation across corn fields
- `min`: Minimum VPD in corn fields
- `max`: Maximum VPD in corn fields
- `mask_year`: CDL mask year used for this observation

**Actual Value Range (Corn Fields 2016-2025):**
- **Mean:** 0.0009 kPa
- **Minimum:** 0.0000 kPa
- **Maximum:** 0.0031 kPa
- **Std Dev:** 0.0005 kPa

**Use Cases:**
- Atmospheric dryness monitoring for corn
- Evaporative demand assessment
- Combined temperature-humidity stress indicator
- Corn water stress early warning

**Note on Units:** VPD values appear to be in kPa. Typical meteorological VPD ranges are 0.5-3.5 kPa, so these values may represent scaled or normalized VPD. Verify units with gridMET documentation for proper interpretation.

**Critical for Corn:**
- High VPD during pollination (July 15-Aug 15) can reduce kernel set
- Persistent high VPD indicates atmospheric drought conditions
- Combine with low ET for comprehensive water stress assessment

---

### 3.2 ETo (Reference Evapotranspiration) - Corn-Masked

**File:** `weather/eto/iowa_corn_eto_20160501_20251031.parquet`  
**Source:** gridMET (IDAHO_EPSCOR/GRIDMET)  
**Resolution:** 4km, daily  
**Total Records:** 181,170  
**Date Range:** 2016-05-01 to 2025-10-30  
**Corn Masking:** USDA CDL 2016-2024

**Coverage:**
- **Years:** 2016-2025 (10 growing seasons)
- **Months:** May-October only (corn season)
- **Counties:** All 99 Iowa counties
- **Records per year:** ~18,117 per year (183 days × 99 counties)

**Mask Details:**
- **2016-2024 data:** Uses year-specific CDL corn masks
- **2025 data:** Uses 2024 CDL mask (most recent available)

**Schema:**
- `date`: Observation date (YYYY-MM-DD)
- `fips`: 5-digit county FIPS code
- `county_name`: County name
- `mean`: County-wide mean ETo (mm/day) across corn fields
- `std`: Standard deviation across corn fields
- `min`: Minimum ETo in corn fields
- `max`: Maximum ETo in corn fields
- `mask_year`: CDL mask year used for this observation

**Actual Value Range (Corn Fields 2016-2025):**
- **Mean:** 4.41 mm/day
- **Minimum:** 0.20 mm/day
- **Maximum:** 10.72 mm/day
- **Std Dev:** 1.57 mm/day

**Use Cases:**
- Atmospheric evaporative demand monitoring
- Reference evapotranspiration for corn water needs
- Water balance calculations (ETo - Precipitation = deficit)
- Alternative to actual ET for 2025 predictions

**Typical Values by Season (Iowa Corn):**
- **May (Planting):** 3-5 mm/day
- **June-July (Vegetative):** 5-7 mm/day
- **July-August (Peak):** 6-8 mm/day
- **September-October (Maturity):** 3-5 mm/day

**Critical for Corn:**
- ETo represents atmospheric water demand on well-watered crops
- When ETo > Precipitation, crops experience water deficit stress
- Combine with Precipitation to calculate daily water balance
- High ETo (>7 mm/day) during pollination increases water stress risk

---

### 3.3 Precipitation - Corn-Masked

**File:** `weather/pr/iowa_corn_pr_20160501_20251031.parquet`  
**Source:** gridMET (IDAHO_EPSCOR/GRIDMET)  
**Resolution:** 4km, daily  
**Total Records:** 181,071  
**Date Range:** 2016-05-01 to 2025-10-30  
**Corn Masking:** USDA CDL 2016-2024

**Coverage:**
- **Years:** 2016-2025 (10 growing seasons)
- **Months:** May-October only (corn season)
- **Counties:** All 99 Iowa counties
- **Records per year:** ~18,107 per year (varies slightly by year)

**Mask Details:**
- **2016-2024 data:** Uses year-specific CDL corn masks
- **2025 data:** Uses 2024 CDL mask (most recent available)

**Schema:**
- `date`: Observation date (YYYY-MM-DD)
- `fips`: 5-digit county FIPS code
- `county_name`: County name
- `mean`: County-wide mean precipitation (mm/day) across corn fields
- `std`: Standard deviation across corn fields
- `min`: Minimum precipitation in corn fields
- `max`: Maximum precipitation in corn fields
- `mask_year`: CDL mask year used for this observation

**Actual Value Range (Corn Fields 2016-2025):**
- **Mean:** 3.47 mm/day
- **Minimum:** 0.00 mm/day (no precipitation)
- **Maximum:** 170.93 mm/day (extreme rainfall event)
- **Std Dev:** 8.79 mm/day

**Precipitation Distribution:**
- **Days with no rain:** 97,117 (53.6%)
- **Days with rain:** 83,954 (46.4%)
- **Heavy rain events (>25mm):** 6,549 (3.6%)

**Use Cases:**
- Daily water input to corn fields
- Drought monitoring (consecutive days with low/no precipitation)
- Water balance calculations (Precipitation - ETo = surplus/deficit)
- Flood risk assessment (extreme precipitation events)

**Typical Values by Season (Iowa Corn):**
- **May:** 3-5 mm/day average
- **June-July:** 3-6 mm/day average
- **August (critical):** 2-4 mm/day average
- **September-October:** 2-4 mm/day average

**Precipitation Thresholds:**
- **Dry day:** 0 mm
- **Light rain:** 0-5 mm/day
- **Moderate rain:** 5-15 mm/day
- **Heavy rain:** 15-25 mm/day
- **Very heavy rain:** 25-50 mm/day
- **Extreme rain:** >50 mm/day

**Critical for Corn:**
- Precipitation is the primary water input for corn growth
- Consecutive days without precipitation during pollination (July 15-Aug 15) critically impacts yields
- Combine with ETo to calculate cumulative water deficit over critical periods
- Heavy rainfall (>25 mm/day) can cause flooding stress and nutrient leaching
- Extended dry periods (>7 days with <2 mm/day) lead to drought stress

---

### 3.4 Water Deficit - Derived Indicator

**File:** `weather/water_deficit/iowa_corn_water_deficit_20160501_20251031.parquet`  
**Source:** Derived (ETo - Precipitation)  
**Resolution:** 4km, daily  
**Total Records:** 181,071  
**Date Range:** 2016-05-01 to 2025-10-30  
**Corn Masking:** USDA CDL 2016-2024

**Coverage:**
- **Years:** 2016-2025 (10 growing seasons)
- **Months:** May-October only (corn season)
- **Counties:** All 99 Iowa counties
- **Records per year:** ~18,107 per year

**Calculation:**
```
Water Deficit = ETo (evaporative demand) - Precipitation (water input)
```

**Schema:**
- `date`: Observation date (YYYY-MM-DD)
- `fips`: 5-digit county FIPS code
- `county_name`: County name
- `eto_mean`: Reference evapotranspiration (mm/day)
- `pr_mean`: Precipitation (mm/day)
- `water_deficit`: **ETo - Precipitation (mm/day)**
- `eto_std`: ETo standard deviation
- `pr_std`: Precipitation standard deviation
- `mask_year`: CDL mask year used

**Actual Value Range (2016-2025):**
- **Mean Deficit:** ~0.94 mm/day
- **Maximum Deficit:** ~10.52 mm/day (severe drought)
- **Maximum Surplus:** ~-164.44 mm/day (extreme rainfall)

**Stress Classification (Based on Water Deficit):**
- **Surplus (negative values):** ~90,500 records (50.0%) - Excess water
- **Normal (0-2 mm/day):** ~39,700 records (21.9%) - Adequate water
- **Moderate Stress (2-4 mm/day):** ~30,400 records (16.8%) - Beginning stress
- **High Stress (4-6 mm/day):** ~15,000 records (8.3%) - Significant stress
- **Severe Stress (>6 mm/day):** ~5,500 records (3.0%) - Critical stress

**Use Cases:**
- **Direct water stress indicator:** Single metric combining supply and demand
- **Drought monitoring:** Consecutive days with positive deficit
- **Cumulative stress:** Sum deficit over critical growth periods
- **ML feature:** Alternative to ET for 2025 predictions
- **Irrigation scheduling:** Identifies when corn fields need water

**Interpretation:**
- **Negative deficit (surplus):** Precipitation exceeds ETo - No water stress, potential for excess water/flooding
- **0-2 mm/day:** Normal conditions - Adequate soil moisture for corn
- **2-4 mm/day:** Moderate stress - Soil moisture declining, monitor closely
- **4-6 mm/day:** High stress - Soil moisture depleted, yield impacts likely
- **>6 mm/day:** Severe stress - Critical water shortage, significant yield loss expected

**Critical Periods for Corn:**
- **Pollination (July 15 - Aug 15):** Deficit >4 mm/day for 7+ consecutive days causes severe yield loss (up to 50%)
- **Grain Fill (Aug 15 - Sept 15):** Sustained deficit >6 mm/day reduces kernel weight
- **Early Season (May-June):** High deficits less critical but affect root development

**Advantages Over Individual Metrics:**
- Combines water supply (Precipitation) and demand (ETo) into single indicator
- Directly quantifies daily water stress intensity
- Easier to interpret than separate ETo and Precipitation values
- Better predictor of yield impacts when cumulated over critical periods
- Accounts for both atmospheric demand and water availability

**Example Scenarios:**
- **ETo=5, Precip=2:** Deficit=3 mm/day → Moderate stress
- **ETo=7, Precip=1:** Deficit=6 mm/day → High stress  
- **ETo=4, Precip=15:** Deficit=-11 mm/day → Surplus (flooding risk)
- **ETo=8, Precip=0:** Deficit=8 mm/day → Severe stress

---

## 4. Corn Field Masks

**Location:** `gs://agriguard-ac215-data/data_raw/masks/corn/`  
**Source:** USDA Cropland Data Layer (CDL)  
**Purpose:** Identify corn field pixels for accurate indicator extraction

### Available Masks

**Files:** `iowa_corn_mask_YYYY.tif` (2010-2024)
- **Format:** GeoTIFF
- **Resolution:** 30m
- **Coverage:** All Iowa
- **Binary Classification:** 1 = Corn, 0 = Other land cover
- **Total Files:** 15 masks (2010-2024)

### Mask Usage

| Year | Mask Applied | Notes |
|------|-------------|-------|
| 2016 | 2016 CDL | Year-specific |
| 2017 | 2017 CDL | Year-specific |
| 2018 | 2018 CDL | Year-specific |
| 2019 | 2019 CDL | Year-specific |
| 2020 | 2020 CDL | Year-specific |
| 2021 | 2021 CDL | Year-specific |
| 2022 | 2022 CDL | Year-specific |
| 2023 | 2023 CDL | Year-specific |
| 2024 | 2024 CDL | Year-specific |
| 2025 | 2024 CDL | Most recent available |

### County Boundaries

**File:** `gs://agriguard-ac215-data/data_raw/masks/iowa_counties.geojson`
- **Format:** GeoJSON
- **Features:** 99 Iowa counties
- **Attributes:** GEOID (FIPS), NAME (county name)
- **Purpose:** County-level aggregation boundaries

---

## Data Quality & Validation

### Strengths

✅ **Corn-Specific Data:** CDL masking eliminates contamination from other crops  
✅ **Year-Specific Masks:** Uses appropriate CDL mask for each year (2016-2024)  
✅ **Growing Season Focus:** May-October only (corn season) reduces irrelevant data  
✅ **Complete Spatial Coverage:** All 99 Iowa counties with consistent coverage  
✅ **Multi-Sensor Fusion:** 3 complementary satellite indicators for comprehensive monitoring  
✅ **Official Sources:** USDA (CDL, yields), NASA (MODIS), OpenET, gridMET  
✅ **County Aggregation:** Matches yield data resolution while preserving corn-specific values  
✅ **Consistent Processing:** Standardized Google Earth Engine workflows  
✅ **Automated Updates:** Cloud Run Jobs for weekly updates during growing season


### Known Limitations

⚠️ **CDL Mask Lag:** 2025 data uses 2024 CDL mask (current year not yet published)  
⚠️ **OpenET Delay:** ET data typically lags 3-6 months; 2025 not yet available  
⚠️ **Temporal Resolution:** 8-16 day composites may miss rapid stress events  
⚠️ **Cloud Cover:** Optical sensors (NDVI, LST) affected by persistent clouds  
⚠️ **Resolution Mismatch:** LST (1km), NDVI (500m), ET (30m), VPD (4km)  
⚠️ **County-Level Aggregation:** Cannot detect field-level variability  
⚠️ **Yield Data Lag:** Current year yields not available until following January  
⚠️ **Corn Classification Accuracy:** CDL is ~85-95% accurate for corn classification

---

## Update Schedule

### During Growing Season (May-October)

| Data Type | Update Frequency | Typical Lag | Automated | Corn-Masked |
|-----------|------------------|-------------|-----------|-------------|
| **MODIS NDVI** | Every 16 days | 3-5 days | Yes | Yes |
| **OpenET (ET)** | Monthly | 3-6 months | Yes | Yes |
| **MODIS LST** | Every 8 days | 3-5 days | Yes | Yes |
| **gridMET VPD** | Daily | 1-2 days | Yes | Yes |
| **gridMET ETo** | Daily | 1-2 days | Yes | Yes |
| **gridMET Precipitation** | Daily | 1-2 days | Yes | Yes |
| **Yields** | Annual | Previous year | January | N/A |

### Cloud Run Jobs

**Deployment:** 6 indicator types with parallel processing

| Job | Indicator | Timeout | Status |
|-----|-----------|---------|--------|
| `agriguard-ndvi-corn-job` | NDVI | 8 hours | ✅ Active |
| `agriguard-et-corn-job` | ET | 8 hours | ✅ Active |
| `agriguard-lst-corn-job` | LST | 8 hours | ✅ Active |
| `agriguard-vpd-YYYY` | VPD | 2 hours | ✅ Complete (10 yearly jobs) |
| `agriguard-eto-YYYY` | ETo | 2 hours | ✅ Complete (10 yearly jobs) |
| `agriguard-pr-YYYY` | Precipitation | 2 hours | ✅ Complete (10 yearly jobs) |

**Features:**
- Incremental updates (checks existing data before downloading)
- Year-specific CDL mask loading
- Automatic retry on failure
- Progress logging to Cloud Logging

### Data Refresh Protocol

The corn-masked data ingestion pipeline automatically:
1. Loads year-specific CDL corn masks from GCS
2. Checks existing data in `data_raw_new/`
3. Downloads only missing/new data (incremental)
4. Applies corn masks before aggregation
5. Processes and uploads to `data_raw_new/`
6. Logs mask year used and processing statistics

**Last Full Refresh:** November 15, 2025  
**Next Scheduled Refresh:** Weekly during growing season (May-October 2026)

---

## Data Access & Usage

### GCS Bucket Access

**Bucket:** `gs://agriguard-ac215-data`  
**Path:** `data_raw_new/`  
**Region:** `us-central1`  
**Storage Class:** Standard

### Required Permissions

To read this data, you need:
- `storage.objects.get`
- `storage.objects.list`

**Service Account:** `agriguard-service-account@agriguard-ac215.iam.gserviceaccount.com`

### Data Size Summary

| Category | Files | Total Size (approx) | Format |
|----------|-------|---------------------|--------|
| **NDVI** | 1 | ~300 KB | Parquet |
| **ET** | 1 | ~130 KB | Parquet |
| **LST** | 1 | ~524 KB | Parquet |
| **VPD** | 11 (10 yearly + 1 merged) | ~3.8 MB | Parquet |
| **ETo** | 11 (10 yearly + 1 merged) | ~3.6 MB | Parquet |
| **Precipitation** | 11 (10 yearly + 1 merged) | ~2.0 MB | Parquet |
| **Water Deficit** | 1 | ~2.5 MB | Parquet |
| **Total** | ~37 | ~12.9 MB | Parquet |

**Note:** Corn-masked data is smaller than county-wide data due to:
- Fewer pixels included (corn fields only vs. entire county)
- Shorter time period (2016-2025 vs. 2010-2025)
- Seasonal filtering (May-Oct vs. full year)

---

## Data Verification Commands

### Quick File Check (in Cloud Shell or with gsutil installed)

```bash
# Check all merged files exist
gsutil ls -lh gs://agriguard-ac215-data/data_raw_new/modis/ndvi/*.parquet
gsutil ls -lh gs://agriguard-ac215-data/data_raw_new/modis/et/*.parquet
gsutil ls -lh gs://agriguard-ac215-data/data_raw_new/modis/lst/*.parquet
gsutil ls -lh gs://agriguard-ac215-data/data_raw_new/weather/vpd/*.parquet
gsutil ls -lh gs://agriguard-ac215-data/data_raw_new/weather/eto/*.parquet
gsutil ls -lh gs://agriguard-ac215-data/data_raw_new/weather/pr/*.parquet
gsutil ls -lh gs://agriguard-ac215-data/data_raw_new/weather/water_deficit/*.parquet
```

### Detailed Data Inspection (requires pandas)

**ETo Data:**
```bash
# In Cloud Shell
gsutil cp gs://agriguard-ac215-data/data_raw_new/weather/eto/iowa_corn_eto_20160501_20251031.parquet .

python3 << 'EOF'
import pandas as pd
df = pd.read_parquet('iowa_corn_eto_20160501_20251031.parquet')
print(f"Total Records: {len(df):,}")
print(f"Date Range: {df['date'].min()} to {df['date'].max()}")
print(f"Counties: {df['fips'].nunique()}")
print(f"Years: {sorted(df['date'].str[:4].unique())}")
print(f"ETo Mean: {df['mean'].mean():.2f} mm/day")
print(f"ETo Min: {df['mean'].min():.2f} mm/day")
print(f"ETo Max: {df['mean'].max():.2f} mm/day")
print(f"\nSample data:")
print(df.head(3))
EOF
```

**Precipitation Data:**
```bash
# In Cloud Shell
gsutil cp gs://agriguard-ac215-data/data_raw_new/weather/pr/iowa_corn_pr_20160501_20251031.parquet .

python3 << 'EOF'
import pandas as pd
df = pd.read_parquet('iowa_corn_pr_20160501_20251031.parquet')
print(f"Total Records: {len(df):,}")
print(f"Date Range: {df['date'].min()} to {df['date'].max()}")
print(f"Counties: {df['fips'].nunique()}")
print(f"Years: {sorted(df['date'].str[:4].unique())}")
print(f"Precipitation Mean: {df['mean'].mean():.2f} mm/day")
print(f"Precipitation Min: {df['mean'].min():.2f} mm/day")
print(f"Precipitation Max: {df['mean'].max():.2f} mm/day")
print(f"\nSample data:")
print(df.head(3))
EOF
```

**Water Deficit Data:**
```bash
# In Cloud Shell
gsutil cp gs://agriguard-ac215-data/data_raw_new/weather/water_deficit/iowa_corn_water_deficit_20160501_20251031.parquet .

python3 << 'EOF'
import pandas as pd
df = pd.read_parquet('iowa_corn_water_deficit_20160501_20251031.parquet')
print(f"Total Records: {len(df):,}")
print(f"Date Range: {df['date'].min()} to {df['date'].max()}")
print(f"Counties: {df['fips'].nunique()}")
print(f"Years: {sorted(df['date'].str[:4].unique())}")
print(f"\nWater Deficit Statistics:")
print(f"  Mean: {df['water_deficit'].mean():.2f} mm/day")
print(f"  Min (max surplus): {df['water_deficit'].min():.2f} mm/day")
print(f"  Max (max deficit): {df['water_deficit'].max():.2f} mm/day")
print(f"\nStress Distribution:")
total = len(df)
surplus = (df['water_deficit'] < 0).sum()
normal = ((df['water_deficit'] >= 0) & (df['water_deficit'] <= 2)).sum()
moderate = ((df['water_deficit'] > 2) & (df['water_deficit'] <= 4)).sum()
high = ((df['water_deficit'] > 4) & (df['water_deficit'] <= 6)).sum()
severe = (df['water_deficit'] > 6).sum()
print(f"  Surplus (negative): {surplus:,} ({surplus/total*100:.1f}%)")
print(f"  Normal (0-2 mm): {normal:,} ({normal/total*100:.1f}%)")
print(f"  Moderate (2-4 mm): {moderate:,} ({moderate/total*100:.1f}%)")
print(f"  High (4-6 mm): {high:,} ({high/total*100:.1f}%)")
print(f"  Severe (>6 mm): {severe:,} ({severe/total*100:.1f}%)")
print(f"\nSample data:")
print(df[['date', 'fips', 'county_name', 'eto_mean', 'pr_mean', 'water_deficit']].head(5))
EOF
```

### Verify All Yearly Files

```bash
# List all ETo yearly files
gsutil ls gs://agriguard-ac215-data/data_raw_new/weather/eto/yearly/

# List all Precipitation yearly files  
gsutil ls gs://agriguard-ac215-data/data_raw_new/weather/pr/yearly/

# Should show 10 files each (2016-2025)
```

### Check File Sizes

```bash
# Check merged file sizes
gsutil du -sh gs://agriguard-ac215-data/data_raw_new/weather/eto/
gsutil du -sh gs://agriguard-ac215-data/data_raw_new/weather/pr/
gsutil du -sh gs://agriguard-ac215-data/data_raw_new/weather/water_deficit/

# Expected sizes:
# ETo: ~3.6 MB
# Precipitation: ~2.0 MB
# Water Deficit: ~2.5 MB
```

---

## Contact & Support

**Artem Biriukov** - arb433@g.harvard.edu

**External Resources:**
- USDA NASS Quick Stats: https://quickstats.nass.usda.gov/
- USDA Cropland Data Layer: https://nassgeodata.gmu.edu/CropScape/
- Google Earth Engine: https://earthengine.google.com/
- MODIS Products: https://lpdaac.usgs.gov/
- OpenET: https://openetdata.org/
- gridMET: https://www.climatologylab.org/gridmet.html

---

## Appendix: Indicator Summary Table

| Indicator | Records | Source | Resolution | Temporal | Corn-Masked | Date Range | Primary Use |
|-----------|---------|--------|------------|----------|-------------|------------|-------------|
| **NDVI** | 11,187 | MOD13A1 | 500m | 16-day | ✅ CDL 2016-2024 | 2016-2025 | Corn vegetation health |
| **ET** | 10,593 | OpenET v2.0 | 30m | Monthly | ✅ CDL 2016-2024 | 2016-2024 | Corn water stress |
| **LST** | 22,770 | MOD11A2 | 1km | 8-day | ✅ CDL 2016-2024 | 2016-2025 | Corn heat stress |
| **VPD** | 181,170 | gridMET | 4km | Daily | ✅ CDL 2016-2024 | 2016-2025 | Atmospheric dryness |
| **ETo** | 181,170 | gridMET | 4km | Daily | ✅ CDL 2016-2024 | 2016-2025 | Evaporative demand |
| **Precipitation** | 181,071 | gridMET | 4km | Daily | ✅ CDL 2016-2024 | 2016-2025 | Water input |
| **Water Deficit** | 181,071 | Derived (ETo-Precip) | 4km | Daily | ✅ CDL 2016-2024 | 2016-2025 | Direct water stress |
| **Yields** | 1,416 | USDA NASS | County | Annual | N/A | 2010-2024 | Ground truth |
| **TOTAL** | **770,448** | - | - | - | - | - | - |

---

**Last Updated:** November 15, 2025  
**Last Validated:** November 15, 2025 ✅  
**Data Version:** v2.0 (Corn-Masked)  
**README Version:** 2.0  
**Coverage:** 2016-05-01 to 2025-10-31 (Corn Season Only)  
**Masking:** USDA CDL Corn Classification 2016-2024
