import sqlite3
import os

# Connect to database
db_path = os.path.join(os.path.dirname(__file__), 'backend', 'cicd.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("Starting migration to make Git-related columns nullable...")

# Step 1: Create new builds table with nullable columns
cursor.execute("""
CREATE TABLE IF NOT EXISTS builds_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    project_name VARCHAR(255) NOT NULL,
    branch VARCHAR(255),
    commit_hash VARCHAR(255),
    build_type VARCHAR(50) NOT NULL DEFAULT 'source',
    build_script TEXT,
    docker_mode VARCHAR(50) DEFAULT 'build_from_git',
    image_name VARCHAR(255),
    image_tag VARCHAR(50),
    dockerfile_path VARCHAR(500),
    build_context VARCHAR(500),
    docker_image VARCHAR(500),
    docker_compose_file VARCHAR(500),
    artifact_path TEXT,
    artifact_type VARCHAR(50),
    detected_framework VARCHAR(255),
    detected_runtime VARCHAR(50),
    detected_build_tool VARCHAR(50),
    detected_packaging VARCHAR(50),
    recommended_deploy_script TEXT,
    recommended_deploy_path VARCHAR(500),
    recommended_service_name VARCHAR(255),
    status VARCHAR(50) NOT NULL DEFAULT 'running',
    start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    end_time DATETIME,
    duration INTEGER,
    log_path TEXT,
    error_message TEXT
)
""")
print("Created builds_new table")

# Step 2: Migrate data from builds to builds_new
cursor.execute("""
INSERT INTO builds_new (
    id, project_id, project_name, branch, commit_hash, build_type, build_script,
    docker_mode, image_name, image_tag, dockerfile_path, build_context,
    docker_image, docker_compose_file, artifact_path, artifact_type,
    detected_framework, detected_runtime, detected_build_tool, detected_packaging,
    recommended_deploy_script, recommended_deploy_path, recommended_service_name,
    status, start_time, end_time, duration, log_path, error_message
)
SELECT 
    id, project_id, project_name, branch, commit_hash, build_type, build_script,
    docker_mode, image_name, image_tag, dockerfile_path, build_context,
    docker_image, docker_compose_file, artifact_path, artifact_type,
    detected_framework, detected_runtime, detected_build_tool, detected_packaging,
    recommended_deploy_script, recommended_deploy_path, recommended_service_name,
    status, start_time, end_time, duration, log_path, error_message
FROM builds
""")
print(f"Migrated {cursor.rowcount} rows from builds to builds_new")

# Step 3: Drop old builds table
cursor.execute("DROP TABLE builds")
print("Dropped old builds table")

# Step 4: Rename builds_new to builds
cursor.execute("ALTER TABLE builds_new RENAME TO builds")
print("Renamed builds_new to builds")

# Step 5: Rebuild indexes
cursor.execute("CREATE INDEX IF NOT EXISTS ix_builds_id ON builds (id)")
cursor.execute("CREATE INDEX IF NOT EXISTS ix_builds_project_id ON builds (project_id)")
print("Rebuilt indexes on builds table")

# Step 6: Create new deploys table with nullable branch column
cursor.execute("""
CREATE TABLE IF NOT EXISTS deploys_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    build_id INTEGER NOT NULL,
    project_id INTEGER NOT NULL,
    project_name VARCHAR(255) NOT NULL,
    branch VARCHAR(255),
    server_ip VARCHAR(255) NOT NULL,
    server_user VARCHAR(255) NOT NULL,
    deploy_path VARCHAR(500),
    service_name VARCHAR(255),
    deploy_type VARCHAR(50) NOT NULL DEFAULT 'source',
    deploy_script TEXT,
    docker_mode VARCHAR(50) DEFAULT 'build_from_git',
    container_name VARCHAR(255),
    image_name VARCHAR(255),
    image_tag VARCHAR(50),
    port_mapping VARCHAR(100),
    docker_image VARCHAR(500),
    docker_compose_file VARCHAR(500),
    status VARCHAR(50) NOT NULL DEFAULT 'running',
    start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    end_time DATETIME,
    duration INTEGER,
    log_path TEXT,
    error_message TEXT
)
""")
print("Created deploys_new table")

# Step 7: Migrate data from deploys to deploys_new
cursor.execute("""
INSERT INTO deploys_new (
    id, build_id, project_id, project_name, branch, server_ip, server_user,
    deploy_path, service_name, deploy_type, deploy_script, docker_mode,
    container_name, image_name, image_tag, port_mapping, docker_image,
    docker_compose_file, status, start_time, end_time, duration, log_path, error_message
)
SELECT 
    id, build_id, project_id, project_name, branch, server_ip, server_user,
    deploy_path, service_name, deploy_type, deploy_script, docker_mode,
    container_name, image_name, image_tag, port_mapping, docker_image,
    docker_compose_file, status, start_time, end_time, duration, log_path, error_message
FROM deploys
""")
print(f"Migrated {cursor.rowcount} rows from deploys to deploys_new")

# Step 8: Drop old deploys table
cursor.execute("DROP TABLE deploys")
print("Dropped old deploys table")

# Step 9: Rename deploys_new to deploys
cursor.execute("ALTER TABLE deploys_new RENAME TO deploys")
print("Renamed deploys_new to deploys")

# Step 10: Rebuild indexes
cursor.execute("CREATE INDEX IF NOT EXISTS ix_deploys_id ON deploys (id)")
cursor.execute("CREATE INDEX IF NOT EXISTS ix_deploys_build_id ON deploys (build_id)")
cursor.execute("CREATE INDEX IF NOT EXISTS ix_deploys_project_id ON deploys (project_id)")
print("Rebuilt indexes on deploys table")

conn.commit()
conn.close()

print("Migration completed successfully!")
print("Git-related columns (branch, build_script, image_name, image_tag, dockerfile_path, build_context) are now nullable in builds table")
print("branch column is now nullable in deploys table")
