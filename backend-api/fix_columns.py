# Fix column name mismatches
with open('api_extended.py', 'r') as f:
    content = f.read()

# Fix the get_mcsi_for_period function to use correct column names
old_func = '''def get_mcsi_for_period(df, fips, start_date, end_date):
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
        return None'''

new_func = '''def get_mcsi_for_period(df, fips, start_date, end_date):
    """Get MCSI for period"""
    if df is None:
        return None
    try:
        # Use county_fips column and parse dates
        df['start_date'] = pd.to_datetime(df['start_date'])
        df['end_date'] = pd.to_datetime(df['end_date'])
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        
        # Filter by FIPS and overlapping date range
        filtered = df[
            (df['county_fips'] == fips) & 
            (df['start_date'] <= end) & 
            (df['end_date'] >= start)
        ]
        
        if len(filtered) == 0:
            return None
        
        # Extract stress components from dict
        result = {
            'mcsi_score': filtered['mcsi_score'].mean()
        }
        
        # Parse components dict
        if len(filtered) > 0:
            components = filtered['components'].iloc[0]
            if isinstance(components, dict):
                result['water_stress'] = components.get('water_stress', 0)
                result['heat_stress'] = components.get('heat_stress', 0)
                result['vegetation_stress'] = components.get('vegetation_stress', 0)
            else:
                # Fallback
                result['water_stress'] = result['mcsi_score'] * 0.45
                result['heat_stress'] = result['mcsi_score'] * 0.35
                result['vegetation_stress'] = result['mcsi_score'] * 0.20
        
        return result
        
    except Exception as e:
        logger.error(f"Period error: {e}")
        return None'''

content = content.replace(old_func, new_func)

with open('api_extended.py', 'w') as f:
    f.write(content)

print("✓ Fixed column names")
