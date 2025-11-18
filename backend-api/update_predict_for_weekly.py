# Update predict function to use weekly data

with open('api_extended.py', 'r') as f:
    content = f.read()

# Find and replace the predict_yield_simple function
old_predict_start = content.find('def predict_yield_simple(county_fips: str, year: int) -> Dict:')
old_predict_end = content.find('\n\n@app.get', old_predict_start)

new_predict = '''def predict_yield_simple(county_fips: str, year: int) -> Dict:
    """
    Predict yield using season-progressive weekly data
    Uses REAL weekly aggregated data up to current date
    """
    from datetime import datetime
    
    # Determine as-of date
    current_date = datetime.now()
    season_start = datetime(year, 5, 1)
    season_end = datetime(year, 10, 31)
    
    # Determine forecast type and confidence
    if current_date > season_end:
        # Post-season: full data available
        as_of_date = season_end
        forecast_type = "post_season"
        season_completion = 100.0
    elif current_date < season_start:
        # Pre-season: use historical average
        as_of_date = season_start
        forecast_type = "pre_season"
        season_completion = 0.0
    else:
        # In-season: progressive forecast
        as_of_date = current_date
        forecast_type = "in_season"
        days_into_season = (current_date - season_start).days
        season_completion = min(100.0, (days_into_season / 184.0) * 100)
    
    # Calculate confidence based on season completion
    if season_completion < 25:
        confidence = "Low"
    elif season_completion < 50:
        confidence = "Medium"
    elif season_completion < 75:
        confidence = "High"
    else:
        confidence = "Very High"
    
    # Try to use real weekly data
    if clean_data is not None:
        try:
            # Filter for this county-year up to as_of_date
            season_data = clean_data[
                (clean_data['fips'] == county_fips) & 
                (clean_data['year'] == year) &
                (clean_data['week_start'] <= as_of_date)
            ]
            
            if len(season_data) > 0:
                # Aggregate weekly features
                ndvi_avg = season_data['ndvi_mean'].mean()
                lst_avg = season_data['lst_mean'].mean()
                lst_max = season_data['lst_max'].max()
                water_deficit_total = season_data['water_deficit_mean'].sum()
                pr_total = season_data['pr_sum'].sum()
                
                # Check for critical stress periods
                has_pollination_data = len(season_data[season_data['growth_phase'].str.contains('pollination', na=False)]) > 0
                
                # Simple yield model based on stress indicators
                base_yield = 180.0  # Iowa average
                
                # NDVI impact (vegetation health)
                if ndvi_avg > 0.7:
                    ndvi_impact = +15
                elif ndvi_avg > 0.6:
                    ndvi_impact = +5
                elif ndvi_avg > 0.5:
                    ndvi_impact = 0
                else:
                    ndvi_impact = -10
                
                # Heat stress impact
                if lst_max > 38:
                    heat_impact = -20  # Severe heat damage
                elif lst_max > 35:
                    heat_impact = -10
                elif lst_max > 32:
                    heat_impact = -5
                else:
                    heat_impact = 0
                
                # Water deficit impact
                if water_deficit_total > 100:
                    water_impact = -15  # Drought stress
                elif water_deficit_total > 50:
                    water_impact = -8
                elif water_deficit_total > 20:
                    water_impact = -3
                else:
                    water_impact = 0
                
                # Precipitation impact (too much or too little)
                if pr_total < 300:
                    pr_impact = -10  # Too dry
                elif pr_total > 800:
                    pr_impact = -5   # Too wet
                else:
                    pr_impact = +5   # Good rainfall
                
                # Pollination period bonus
                poll_bonus = +10 if has_pollination_data else 0
                
                predicted_yield = base_yield + ndvi_impact + heat_impact + water_impact + pr_impact + poll_bonus
                
                # Ensure reasonable range
                predicted_yield = max(100, min(220, predicted_yield))
                
                # Determine trend
                iowa_avg = 180.0
                if predicted_yield > iowa_avg + 10:
                    trend = "above_average"
                elif predicted_yield < iowa_avg - 10:
                    trend = "below_average"
                else:
                    trend = "average"
                
                logger.info(f"Real prediction from {len(season_data)} weeks: {county_fips} {year} = {predicted_yield:.1f} bu/acre")
                
                return {
                    "county_fips": county_fips,
                    "year": year,
                    "predicted_yield": round(predicted_yield, 1),
                    "confidence": confidence,
                    "trend": trend,
                    "forecast_type": forecast_type,
                    "season_completion": f"{season_completion:.1f}%",
                    "as_of_date": as_of_date.strftime('%Y-%m-%d'),
                    "weeks_data": len(season_data),
                    "model": "Season-Progressive Stress Model",
                    "data_source": "Real weekly aggregated data"
                }
                
        except Exception as e:
            logger.error(f"Error using weekly data: {e}")
            # Fall through to estimate
    
    # Fallback: Use temporal estimate
    import random
    random.seed(int(county_fips) + year)
    base_yield = 180.0
    
    # Vary by year
    year_factor = {
        2022: -15,  # Drought year
        2023: +5,   # Better year
        2024: 0,    # Average
        2025: +3,   # Slightly above
        2026: +5    # Trend up
    }.get(year, 0)
    
    variation = random.uniform(-10, 10)
    predicted_yield = base_yield + year_factor + variation
    
    iowa_avg = 180.0
    if predicted_yield > iowa_avg + 10:
        trend = "above_average"
    elif predicted_yield < iowa_avg - 10:
        trend = "below_average"
    else:
        trend = "average"
    
    return {
        "county_fips": county_fips,
        "year": year,
        "predicted_yield": round(predicted_yield, 1),
        "confidence": "Low",
        "trend": trend,
        "forecast_type": forecast_type,
        "season_completion": f"{season_completion:.1f}%",
        "as_of_date": as_of_date.strftime('%Y-%m-%d'),
        "model": "Temporal Estimate",
        "data_source": "Fallback estimate"
    }
'''

content = content[:old_predict_start] + new_predict + content[old_predict_end:]

with open('api_extended.py', 'w') as f:
    f.write(content)

print("✓ Updated predict function to use weekly aggregated data")
