with open('api_extended.py', 'r') as f:
    content = f.read()

# Remove the old stub function
old_stub = '''def load_mcsi_from_gcs():
    """Load latest MCSI data from GCS"""
    try:
        # This would load the actual MCSI processed data
        # For now, we'll simulate it
        logger.info("Loading MCSI data from GCS...")
        return None
    except Exception as e:
        logger.error(f"Error loading MCSI: {e}")
        return None'''

content = content.replace(old_stub, '')

with open('api_extended.py', 'w') as f:
    f.write(content)

print("✓ Removed duplicate function")
