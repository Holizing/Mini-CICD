import sqlite3

# Connect to database
conn = sqlite3.connect('cicd.db')
cursor = conn.cursor()

# Add new columns to builds table
try:
    cursor.execute("ALTER TABLE builds ADD COLUMN deploy_type VARCHAR(50) DEFAULT 'source'")
    print("Added deploy_type column to builds table")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("deploy_type column already exists in builds table")
    else:
        print(f"Error adding deploy_type: {e}")

try:
    cursor.execute("ALTER TABLE builds ADD COLUMN build_script TEXT")
    print("Added build_script column to builds table")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("build_script column already exists in builds table")
    else:
        print(f"Error adding build_script: {e}")

# Add new column to deploys table
try:
    cursor.execute("ALTER TABLE deploys ADD COLUMN deploy_type VARCHAR(50) DEFAULT 'source'")
    print("Added deploy_type column to deploys table")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("deploy_type column already exists in deploys table")
    else:
        print(f"Error adding deploy_type to deploys: {e}")

conn.commit()
conn.close()

print("Migration completed successfully!")
