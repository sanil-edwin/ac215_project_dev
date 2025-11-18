# Quick patch to read parquet instead of csv
with open('api_extended.py', 'r') as f:
    content = f.read()

# Replace CSV reading with parquet reading
content = content.replace(
    "df = pd.read_csv(pd.io.common.StringIO(data))",
    "df = pd.read_parquet(pd.io.common.BytesIO(latest.download_as_bytes()))"
)

# Also update the download method
content = content.replace(
    "data = latest.download_as_text()",
    "# Download parquet file"
)

with open('api_extended.py', 'w') as f:
    f.write(content)

print("✓ Fixed to read parquet files")
