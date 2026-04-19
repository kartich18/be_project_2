import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv("DATABASE_URL")

if not db_url:
    print("Error: DATABASE_URL not found in environment.")
    exit(1)

try:
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cursor = conn.cursor()

    columns_to_add = [
        "sign_time_ms FLOAT",
        "verify_time_ms FLOAT",
        "dsa_algorithm VARCHAR(50)",
        "dsa_public_key_bytes INTEGER",
        "signature_size_bytes INTEGER"
    ]

    for col in columns_to_add:
        try:
            cursor.execute(f"ALTER TABLE transactions ADD COLUMN {col};")
            print(f"Added column {col}")
        except psycopg2.errors.DuplicateColumn:
            print(f"Column {col} already exists, skipping.")
        except Exception as e:
            print(f"Error adding {col}: {e}")

    cursor.close()
    conn.close()
    print("Database schema updated successfully!")

except Exception as e:
    print(f"Connection failed: {e}")
