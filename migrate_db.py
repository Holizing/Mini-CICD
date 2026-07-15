import sqlite3
import os

# Connect to database (backend directory)
db_path = os.path.join(os.path.dirname(__file__), 'backend', 'cicd.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Add new columns to builds table
try:
    cursor.execute("ALTER TABLE builds ADD COLUMN build_type VARCHAR(50) DEFAULT 'source'")
    print("Added build_type column to builds table")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("build_type column already exists in builds table")
    else:
        print(f"Error adding build_type: {e}")

try:
    cursor.execute("ALTER TABLE builds ADD COLUMN image_name VARCHAR(255)")
    print("Added image_name column to builds table")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("image_name column already exists in builds table")
    else:
        print(f"Error adding image_name: {e}")

try:
    cursor.execute("ALTER TABLE builds ADD COLUMN image_tag VARCHAR(50)")
    print("Added image_tag column to builds table")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("image_tag column already exists in builds table")
    else:
        print(f"Error adding image_tag: {e}")

try:
    cursor.execute("ALTER TABLE builds ADD COLUMN dockerfile_path VARCHAR(500)")
    print("Added dockerfile_path column to builds table")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("dockerfile_path column already exists in builds table")
    else:
        print(f"Error adding dockerfile_path: {e}")

try:
    cursor.execute("ALTER TABLE builds ADD COLUMN build_context VARCHAR(500)")
    print("Added build_context column to builds table")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("build_context column already exists in builds table")
    else:
        print(f"Error adding build_context: {e}")

try:
    cursor.execute("ALTER TABLE builds ADD COLUMN build_script TEXT")
    print("Added build_script column to builds table")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("build_script column already exists in builds table")
    else:
        print(f"Error adding build_script: {e}")

try:
    cursor.execute("ALTER TABLE builds ADD COLUMN artifact_path TEXT")
    print("Added artifact_path column to builds table")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("artifact_path column already exists in builds table")
    else:
        print(f"Error adding artifact_path: {e}")

try:
    cursor.execute("ALTER TABLE builds ADD COLUMN artifact_type VARCHAR(50)")
    print("Added artifact_type column to builds table")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("artifact_type column already exists in builds table")
    else:
        print(f"Error adding artifact_type: {e}")

# Add new column to deploys table
try:
    cursor.execute("ALTER TABLE deploys ADD COLUMN deploy_type VARCHAR(50) DEFAULT 'source'")
    print("Added deploy_type column to deploys table")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("deploy_type column already exists in deploys table")
    else:
        print(f"Error adding deploy_type to deploys: {e}")

try:
    cursor.execute("ALTER TABLE deploys ADD COLUMN deploy_script TEXT")
    print("Added deploy_script column to deploys table")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("deploy_script column already exists in deploys table")
    else:
        print(f"Error adding deploy_script to deploys: {e}")

# Make deploy_path and service_name nullable for docker deploy
try:
    cursor.execute("ALTER TABLE deploys ALTER COLUMN deploy_path DROP NOT NULL")
    print("Made deploy_path nullable in deploys table")
except sqlite3.OperationalError as e:
    # SQLite doesn't support ALTER COLUMN, so we need to recreate the table
    print("Note: SQLite doesn't support ALTER COLUMN, deploy_path will remain NOT NULL")

try:
    cursor.execute("ALTER TABLE deploys ALTER COLUMN service_name DROP NOT NULL")
    print("Made service_name nullable in deploys table")
except sqlite3.OperationalError as e:
    print("Note: SQLite doesn't support ALTER COLUMN, service_name will remain NOT NULL")

# Add Docker-specific columns to deploys table
try:
    cursor.execute("ALTER TABLE deploys ADD COLUMN container_name VARCHAR(255)")
    print("Added container_name column to deploys table")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("container_name column already exists in deploys table")
    else:
        print(f"Error adding container_name to deploys: {e}")

try:
    cursor.execute("ALTER TABLE deploys ADD COLUMN image_name VARCHAR(255)")
    print("Added image_name column to deploys table")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("image_name column already exists in deploys table")
    else:
        print(f"Error adding image_name to deploys: {e}")

try:
    cursor.execute("ALTER TABLE deploys ADD COLUMN image_tag VARCHAR(50)")
    print("Added image_tag column to deploys table")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("image_tag column already exists in deploys table")
    else:
        print(f"Error adding image_tag to deploys: {e}")

try:
    cursor.execute("ALTER TABLE deploys ADD COLUMN port_mapping VARCHAR(100)")
    print("Added port_mapping column to deploys table")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("port_mapping column already exists in deploys table")
    else:
        print(f"Error adding port_mapping to deploys: {e}")

# Add detection fields to builds table
try:
    cursor.execute("ALTER TABLE builds ADD COLUMN detected_framework VARCHAR(255)")
    print("Added detected_framework column to builds table")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("detected_framework column already exists in builds table")
    else:
        print(f"Error adding detected_framework to builds: {e}")

try:
    cursor.execute("ALTER TABLE builds ADD COLUMN detected_runtime VARCHAR(50)")
    print("Added detected_runtime column to builds table")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("detected_runtime column already exists in builds table")
    else:
        print(f"Error adding detected_runtime to builds: {e}")

try:
    cursor.execute("ALTER TABLE builds ADD COLUMN detected_build_tool VARCHAR(50)")
    print("Added detected_build_tool column to builds table")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("detected_build_tool column already exists in builds table")
    else:
        print(f"Error adding detected_build_tool to builds: {e}")

try:
    cursor.execute("ALTER TABLE builds ADD COLUMN detected_packaging VARCHAR(50)")
    print("Added detected_packaging column to builds table")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("detected_packaging column already exists in builds table")
    else:
        print(f"Error adding detected_packaging to builds: {e}")

try:
    cursor.execute("ALTER TABLE builds ADD COLUMN recommended_deploy_script TEXT")
    print("Added recommended_deploy_script column to builds table")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("recommended_deploy_script column already exists in builds table")
    else:
        print(f"Error adding recommended_deploy_script to builds: {e}")

try:
    cursor.execute("ALTER TABLE builds ADD COLUMN recommended_deploy_path VARCHAR(500)")
    print("Added recommended_deploy_path column to builds table")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("recommended_deploy_path column already exists in builds table")
    else:
        print(f"Error adding recommended_deploy_path to builds: {e}")

try:
    cursor.execute("ALTER TABLE builds ADD COLUMN recommended_service_name VARCHAR(255)")
    print("Added recommended_service_name column to builds table")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("recommended_service_name column already exists in builds table")
    else:
        print(f"Error adding recommended_service_name to builds: {e}")

# Add Docker mode columns to builds table
try:
    cursor.execute("ALTER TABLE builds ADD COLUMN docker_mode VARCHAR(50) DEFAULT 'build_from_git'")
    print("Added docker_mode column to builds table")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("docker_mode column already exists in builds table")
    else:
        print(f"Error adding docker_mode to builds: {e}")

try:
    cursor.execute("ALTER TABLE builds ADD COLUMN docker_image VARCHAR(500)")
    print("Added docker_image column to builds table")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("docker_image column already exists in builds table")
    else:
        print(f"Error adding docker_image to builds: {e}")

try:
    cursor.execute("ALTER TABLE builds ADD COLUMN docker_compose_file VARCHAR(500)")
    print("Added docker_compose_file column to builds table")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("docker_compose_file column already exists in builds table")
    else:
        print(f"Error adding docker_compose_file to builds: {e}")

# Make branch nullable in builds table for existing docker image mode
try:
    cursor.execute("ALTER TABLE builds ALTER COLUMN branch DROP NOT NULL")
    print("Made branch nullable in builds table")
except sqlite3.OperationalError as e:
    print("Note: SQLite doesn't support ALTER COLUMN, branch will remain NOT NULL")

# Add Docker mode columns to deploys table
try:
    cursor.execute("ALTER TABLE deploys ADD COLUMN docker_mode VARCHAR(50) DEFAULT 'build_from_git'")
    print("Added docker_mode column to deploys table")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("docker_mode column already exists in deploys table")
    else:
        print(f"Error adding docker_mode to deploys: {e}")

try:
    cursor.execute("ALTER TABLE deploys ADD COLUMN docker_image VARCHAR(500)")
    print("Added docker_image column to deploys table")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("docker_image column already exists in deploys table")
    else:
        print(f"Error adding docker_image to deploys: {e}")

try:
    cursor.execute("ALTER TABLE deploys ADD COLUMN docker_compose_file VARCHAR(500)")
    print("Added docker_compose_file column to deploys table")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("docker_compose_file column already exists in deploys table")
    else:
        print(f"Error adding docker_compose_file to deploys: {e}")

# Make branch nullable in deploys table for existing docker image mode
try:
    cursor.execute("ALTER TABLE deploys ALTER COLUMN branch DROP NOT NULL")
    print("Made branch nullable in deploys table")
except sqlite3.OperationalError as e:
    print("Note: SQLite doesn't support ALTER COLUMN, branch will remain NOT NULL")

conn.commit()
conn.close()

print("Migration completed successfully!")
