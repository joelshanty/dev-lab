import json
import logging
from sqlalchemy import create_engine, text

# This script compares two PostgreSQL tables for differences in a shared key field,
# such as device_id. It is typically used during database migrations or validation
# checks to confirm that a new table contains the same records and values as the
# original table before replacing it. Update the DB_URL, table names, and columns
# list to match the environment you want to audit.

# --- CONFIGURATION ---
DB_URL = "postgresql://postgres:postgres@localhost:5432/gateway"
TABLE_1 = 'dms_video_devices'
TABLE_2 = 'new_dms_device'
KEY_COLUMN = 'device_id'
# Columns to compare: only common ones
COLUMNS_TO_COMPARE = ['device_id','device_name','device_type','label','is_parent','parent_id','connector_name','connector_type','manufacturer','vendor','model','client_attributes','points','connection_config','device_metadata','enable_device','is_monitorable','is_discoverable','monitoring_event_conf','created_at','updated_at']  # device_data is JSON


# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# SQLAlchemy Setup
engine = create_engine(DB_URL)

def compare_tables(table1, table2, key_column, columns_to_compare):
    """
    Compare two tables based on a key column and specified columns.
    """
    differences = []

    with engine.connect() as conn:
        # Get all device_ids from both tables
        query1 = text(f"SELECT {key_column} FROM {table1}")
        query2 = text(f"SELECT {key_column} FROM {table2}")

        ids1 = {row[0] for row in conn.execute(query1).fetchall()}
        ids2 = {row[0] for row in conn.execute(query2).fetchall()}

        # IDs only in table1
        only_in_1 = ids1 - ids2
        if only_in_1:
            differences.append(f"IDs only in {table1}: {sorted(only_in_1)}")

        # IDs only in table2
        only_in_2 = ids2 - ids1
        if only_in_2:
            differences.append(f"IDs only in {table2}: {sorted(only_in_2)}")

        # Common IDs
        common_ids = ids1 & ids2

        for device_id in sorted(common_ids):
            query = text(f"""
                SELECT {', '.join(columns_to_compare)} FROM {table1} WHERE {key_column} = :id
                UNION ALL
                SELECT {', '.join(columns_to_compare)} FROM {table2} WHERE {key_column} = :id
            """)
            rows = conn.execute(query, {'id': device_id}).fetchall()

            if len(rows) == 2:
                row1, row2 = rows
                for col in columns_to_compare:
                    val1 = row1[columns_to_compare.index(col)]
                    val2 = row2[columns_to_compare.index(col)]

                    # normalize JSON-like fields and None/empty values
                    if col in ('client_attributes', 'points', 'connection_config', 'device_metadata', 'monitoring_event_conf'):
                        if val1 is None:
                            val1 = {}
                        if val2 is None:
                            val2 = {}
                        # Parse strings as JSON if needed
                        if isinstance(val1, str):
                            try:
                                val1 = json.loads(val1)
                            except Exception:
                                pass
                        if isinstance(val2, str):
                            try:
                                val2 = json.loads(val2)
                            except Exception:
                                pass

                    if val1 != val2:
                        differences.append(f"Device {device_id}, Column {col}: {table1}={val1}, {table2}={val2}")

    return differences

def main():
    
    logger.info(f"Comparing {TABLE_1} and {TABLE_2} on {KEY_COLUMN}")
    diffs = compare_tables(TABLE_1, TABLE_2, KEY_COLUMN, COLUMNS_TO_COMPARE)

    if diffs:
        logger.info("Differences found:")
        for diff in diffs:
            print(diff)
    else:
        logger.info("No differences found.")

if __name__ == "__main__":
    main()
