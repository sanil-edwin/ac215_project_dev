# Data Validation Module

Quality assurance and data monitoring for AgriGuard clean data.

## Components

### 1. SchemaValidator
Validates data structure and column types.

```python
from validation import SchemaValidator

validator = SchemaValidator()

# Check schema matches
is_valid, errors = validator.validate_schema(df, dataset_type='daily')

# Check required values
is_valid, missing = validator.validate_required_values(df)
```

**Checks:**
- Required columns exist
- Column data types correct
- Required values not null (>5% tolerance)

### 2. QualityChecker
Detects outliers and quality issues.

```python
from validation import QualityChecker

checker = QualityChecker()

# Check value ranges
is_valid, violations = checker.check_value_ranges(df)

# Detect outliers (IQR method)
outliers = checker.detect_outliers(df)

# Check completeness
is_valid, report = checker.check_completeness(df, min_completeness=0.95)

# Check duplicates
is_valid, count = checker.check_duplicates(df, key_cols=['date', 'fips'])
```

**Checks:**
- NDVI: 0-1
- LST: -50 to 60°C
- VPD: 0-5 kPa
- ETo: 0-15 mm/day
- Precipitation: 0-200 mm/day
- Water Deficit: -200 to 15 mm/day
- Outliers (IQR method)
- Data completeness >95%
- Duplicate rows

### 3. DriftDetector
Monitors for distribution shifts.

```python
from validation import DriftDetector

detector = DriftDetector(baseline_period_days=30)

# Temporal drift (time series changes)
drift = detector.detect_temporal_drift(df, column='ndvi_mean', window_days=7)

# County-level anomalies
anomalies = detector.detect_county_drift(df, column='ndvi_mean')

# Missing data drift
missing = detector.detect_missing_data_drift(df)

# Complete report
report = detector.generate_drift_report(df)
```

**Detects:**
- Temporal shifts (z-score > 2)
- County-level anomalies
- Changes in missing data patterns

## Usage

### Run All Checks
```python
from validation import SchemaValidator, QualityChecker, DriftDetector
import pandas as pd

# Load clean data
df = pd.read_parquet('gs://agriguard-ac215-data/data_clean/daily/...')

# 1. Schema validation
validator = SchemaValidator()
is_valid, errors = validator.validate_schema(df)
is_valid, missing = validator.validate_required_values(df)

# 2. Quality checks
checker = QualityChecker()
is_valid, violations = checker.check_value_ranges(df)
outliers = checker.detect_outliers(df)
is_valid, report = checker.check_completeness(df)

# 3. Drift detection
detector = DriftDetector()
drift_report = detector.generate_drift_report(df)

# Report results
print(f"Schema valid: {is_valid}")
print(f"Quality violations: {violations}")
print(f"Drift report: {drift_report}")
```

### Integration with Processing Pipeline
```python
# In data/processing/cleaner/clean_data.py
from validation import SchemaValidator, QualityChecker

def run(self):
    # ... existing processing ...
    
    # Validate clean data before saving
    daily_df = self.create_daily_clean_data()
    
    # Validate schema
    validator = SchemaValidator()
    is_valid, errors = validator.validate_schema(daily_df, 'daily')
    if not is_valid:
        logger.error(f"Schema validation failed: {errors}")
        return
    
    # Check quality
    checker = QualityChecker()
    is_valid, violations = checker.check_value_ranges(daily_df)
    is_valid, report = checker.check_completeness(daily_df)
    
    # Save if valid
    if is_valid:
        self.save_daily_clean_data(daily_df)
```

## Valid Ranges

| Indicator | Min | Max | Unit |
|-----------|-----|-----|------|
| NDVI | 0 | 1 | - |
| LST | -50 | 60 | °C |
| VPD | 0 | 5 | kPa |
| ETo | 0 | 15 | mm/day |
| Precipitation | 0 | 200 | mm/day |
| Water Deficit | -200 | 15 | mm/day |

## Outputs

### Schema Validation
```
✅ Schema validation passed for daily data
❌ Schema validation failed: ['Missing columns: {...}']
```

### Quality Checks
```
⚠️  Out-of-range values detected: {'ndvi_mean': {'count': 5, 'pct': 0.003}}
⚠️  Outliers detected: {'lst_mean': {'count': 12, 'pct': 0.007}}
✅ Completeness check passed: 99.8%
```

### Drift Detection
```
⚠️  Drift detected in ndvi_mean: z=2.5
⚠️  Anomalies detected in 3 counties
✅ Missing data patterns normal
```

## For MS5

Implement these checks before production:
1. Add validation to `create_daily_clean_data()`
2. Generate validation reports for each run
3. Store validation logs in GCS
4. Alert on validation failures
5. Monitor drift over time

---

**Status:** Template ready for MS5 implementation
