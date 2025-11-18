with open('api_extended.py', 'r') as f:
    content = f.read()

# Find and replace the startup function to add the MCSI loading call
old_end = '''        logger.info("API ready! 🚀")
    
    except Exception as e:'''

new_end = '''        # Load MCSI data from GCS
        mcsi_data = load_mcsi_from_gcs()
        if mcsi_data is not None:
            logger.info("✓ MCSI data loaded from GCS")
        else:
            logger.warning("⚠ No MCSI data - using temporal estimates")
        
        logger.info("API ready! 🚀")
    
    except Exception as e:'''

content = content.replace(old_end, new_end)

with open('api_extended.py', 'w') as f:
    f.write(content)

print("✓ Fixed startup to load MCSI data")
