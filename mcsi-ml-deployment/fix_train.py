import re

with open('src/train_model.py', 'r') as f:
    content = f.read()

# Drop county from feature matrix
content = re.sub(
    r"X = df\.drop\(\['fips', 'year', 'yield_bu_per_acre'\], axis=1\)",
    "X = df.drop(['fips', 'year', 'yield_bu_per_acre', 'county'], axis=1, errors='ignore')",
    content
)

with open('src/train_model.py', 'w') as f:
    f.write(content)

print("Fixed!")
