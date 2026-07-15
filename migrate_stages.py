import sqlite3
import os

# Connect to database
db_path = os.path.join(os.path.dirname(__file__), 'backend', 'cicd.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("Starting migration to add stage tables...")

# Create build_stages table
cursor.execute("""
CREATE TABLE IF NOT EXISTS build_stages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    build_id INTEGER NOT NULL,
    stage_name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    started_at DATETIME,
    finished_at DATETIME,
    duration INTEGER,
    log_file TEXT,
    error_message TEXT,
    FOREIGN KEY (build_id) REFERENCES builds (id)
)
""")
print("Created build_stages table")

# Create deploy_stages table
cursor.execute("""
CREATE TABLE IF NOT EXISTS deploy_stages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deploy_id INTEGER NOT NULL,
    stage_name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    started_at DATETIME,
    finished_at DATETIME,
    duration INTEGER,
    log_file TEXT,
    error_message TEXT,
    FOREIGN KEY (deploy_id) REFERENCES deploys (id)
)
""")
print("Created deploy_stages table")

# Create indexes
cursor.execute("CREATE INDEX IF NOT EXISTS ix_build_stages_id ON build_stages (id)")
cursor.execute("CREATE INDEX IF NOT EXISTS ix_build_stages_build_id ON build_stages (build_id)")
print("Created indexes on build_stages table")

cursor.execute("CREATE INDEX IF NOT EXISTS ix_deploy_stages_id ON deploy_stages (id)")
cursor.execute("CREATE INDEX IF NOT EXISTS ix_deploy_stages_deploy_id ON deploy_stages (deploy_id)")
print("Created indexes on deploy_stages table")

conn.commit()
conn.close()

print("Migration completed successfully!")
print("Added build_stages and deploy_stages tables")
