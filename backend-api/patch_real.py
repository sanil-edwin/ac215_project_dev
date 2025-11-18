#!/usr/bin/env python3
"""Patch API for real GCS data"""
import sys

print("🔧 Patching api_extended.py for REAL DATA...")

with open('api_extended.py', 'r') as f:
    content = f.read()

# Backup
with open('api_extended.py.backup', 'w') as f:
    f.write(content)
print("✓ Backup created")

# 1. Add pandas import
if 'import pandas as pd' not in content:
    content = content.replace('from google.cloud import storage', 
                             'from google.cloud import storage\nimport pandas as pd')
    print("✓ Added pandas")

# 2. Add GCS config
if 'GCS_BUCKET = ' not in content:
    content = content.replace(']\n\n# =============================================================================\n# Data Models',
''']\n
# GCS configuration
GCS_BUCKET = "agriguard-ac215-data"
MCSI_PATH = "processed/mcsi/"

# =============================================================================
# Data Models''')
    print("✓ Added GCS config")

# 3. Add mcsi_data global
content = content.replace('rf_model = None\nfeature_names = None\nmodel_config = None',
                         'rf_model = None\nfeature_names = None\nmodel_config = None\nmcsi_data = None')
print("✓ Added mcsi_data global")

# 4. Update HealthResponse
content = content.replace('    models_loaded: bool\n    version: str',
                         '    models_loaded: bool\n    data_loaded: bool\n    version: str')
print("✓ Updated HealthResponse")

# 5. Update MCSIResponse  
content = content.replace('    growth_stage: str\n\nclass YieldPrediction',
                         '    growth_stage: str\n    data_source: str\n\nclass YieldPrediction')
print("✓ Updated MCSIResponse")

# 6. Add GCS loading functions before startup
gcs_funcs = '''
def load_mcsi_from_gcs():
    """Load MCSI data from GCS"""
    try:
        logger.info("Loading MCSI from GCS...")
        client = storage.Client()
        bucket = client.bucket(GCS_BUCKET)
        blobs = list(bucket.list_blobs(prefix=MCSI_PATH))
        if not blobs:
            logger.warning("No MCSI data in GCS")
            return None
        latest = max(blobs, key=lambda b: b.updated)
        logger.info(f"Loading: {latest.name}")
        data = latest.download_as_text()
        df = pd.read_csv(pd.io.common.StringIO(data))
        logger.info(f"Loaded {len(df)} MCSI records")
        return df
    except Exception as e:
        logger.error(f"GCS error: {e}")
        return None

def get_mcsi_for_period(df, fips, start_date, end_date):
    """Get MCSI for period"""
    if df is None:
        return None
    try:
        df['date'] = pd.to_datetime(df['date'])
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        filtered = df[(df['fips'] == fips) & (df['date'] >= start) & (df['date'] <= end)]
        if len(filtered) == 0:
            return None
        return {
            'mcsi_score': filtered['mcsi_score'].mean(),
            'water_stress': filtered['water_stress_score'].mean(),
            'heat_stress': filtered['heat_stress_score'].mean(),
            'vegetation_stress': filtered['vegetation_stress_score'].mean()
        }
    except Exception as e:
        logger.error(f"Period error: {e}")
        return None

'''

content = content.replace('# =============================================================================\n# Startup\n# =============================================================================',
                         gcs_funcs + '# =============================================================================\n# Startup\n# =============================================================================')
print("✓ Added GCS functions")

# 7. Update startup
content = content.replace('    global rf_model, feature_names, model_config',
                         '    global rf_model, feature_names, model_config, mcsi_data')
content = content.replace('        logger.info("Models loaded successfully")',
'''        logger.info("Models loaded successfully")
        
        # Load MCSI from GCS
        mcsi_data = load_mcsi_from_gcs()
        if mcsi_data is not None:
            logger.info("✓ MCSI data loaded from GCS")''')
print("✓ Updated startup")

# 8. Update health endpoint
content = content.replace('        "models_loaded": rf_model is not None,\n        "version": "2.0.0"',
                         '        "models_loaded": rf_model is not None,\n        "data_loaded": mcsi_data is not None,\n        "version": "2.1.0-real-data"')
print("✓ Updated health")

# 9. Update calculate_mcsi_simple to use real data first
calc_start = content.find('def calculate_mcsi_simple(county_fips: str, start_date: str, end_date: str)')
calc_end = content.find('    # Calculate MCSI (weighted average)', calc_start)
old_calc = content[calc_start:calc_end]

new_calc = '''def calculate_mcsi_simple(county_fips: str, start_date: str, end_date: str) -> Dict:
    """Calculate MCSI using REAL DATA from GCS"""
    from datetime import datetime
    import random
    
    county_name = next((c["name"] for c in IOWA_COUNTIES if c["fips"] == county_fips), "Unknown")
    
    # Try real data first
    real_data = get_mcsi_for_period(mcsi_data, county_fips, start_date, end_date)
    
    if real_data:
        water_stress = real_data['water_stress']
        heat_stress = real_data['heat_stress']
        veg_stress = real_data['vegetation_stress']
        data_source = "Real MCSI from GCS"
        logger.info(f"Using real data for {county_fips}")
    else:
        logger.warning(f"No real data for {county_fips}, using estimate")
        end = datetime.strptime(end_date, '%Y-%m-%d')
        month, year = end.month, end.year
        seed = int(county_fips) + (year * 100) + (month * 10)
        random.seed(seed)
        
        if month == 5:
            water_stress, heat_stress, veg_stress = random.uniform(10,25), random.uniform(15,30), random.uniform(20,35)
        elif month == 6:
            water_stress, heat_stress, veg_stress = random.uniform(20,40), random.uniform(25,45), random.uniform(15,30)
        elif month == 7:
            water_stress, heat_stress, veg_stress = random.uniform(30,60), random.uniform(35,65), random.uniform(20,40)
        elif month == 8:
            water_stress, heat_stress, veg_stress = random.uniform(35,70), random.uniform(40,70), random.uniform(25,50)
        elif month == 9:
            water_stress, heat_stress, veg_stress = random.uniform(20,45), random.uniform(25,50), random.uniform(30,55)
        else:
            water_stress, heat_stress, veg_stress = random.uniform(15,35), random.uniform(20,40), random.uniform(35,60)
        
        if year == 2022:
            water_stress *= 1.3
            heat_stress *= 1.2
        elif year == 2023:
            water_stress *= 0.8
            heat_stress *= 0.9
        
        water_stress = min(water_stress, 100)
        heat_stress = min(heat_stress, 100)
        veg_stress = min(veg_stress, 100)
        data_source = "Temporal Estimate"
    
'''

content = content.replace(old_calc, new_calc)
print("✓ Updated calculate_mcsi_simple")

# 10. Add data_source to return
content = content.replace('        "growth_stage": growth_stage\n    }',
                         '        "growth_stage": growth_stage,\n        "data_source": data_source\n    }')
print("✓ Added data_source to return")

with open('api_extended.py', 'w') as f:
    f.write(content)

print("\n✅ PATCH COMPLETE!")
print("Rebuild: docker build -t us-central1-docker.pkg.dev/agriguard-ac215/agriguard/api-ms4:latest .")
print("Push: docker push us-central1-docker.pkg.dev/agriguard-ac215/agriguard/api-ms4:latest")
print("Deploy: gcloud run deploy agriguard-api-ms4 --image=us-central1-docker.pkg.dev/agriguard-ac215/agriguard/api-ms4:latest --region=us-central1 --service-account=agriguard-service-account@agriguard-ac215.iam.gserviceaccount.com")