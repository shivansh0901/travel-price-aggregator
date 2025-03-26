import sqlite3
import csv

DATABASE = "airports.db"
CSV_FILE = "airports.csv"

# Connect to SQLite
conn = sqlite3.connect(DATABASE)
cursor = conn.cursor()

# Create airports table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS airports (
        id INTEGER PRIMARY KEY,
        name TEXT,
        iata_code TEXT,
        city TEXT,
        country TEXT
    )
""")

# Load CSV into database
with open(CSV_FILE, newline='', encoding="utf-8") as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        if row["iata_code"]:  # Only store airports with valid IATA codes
            cursor.execute(
                "INSERT INTO airports (name, iata_code, city, country) VALUES (?, ?, ?, ?)",
                (row["name"], row["iata_code"], row["municipality"], row["iso_country"]),
            )

# Commit and close
conn.commit()
conn.close()

print("✅ Airports dataset loaded successfully!")
