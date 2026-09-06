"""PostgreSQL client example for a device data.

This module provides ``DBClient``, a lightweight wrapper around psycopg2 for
creating a database, executing parameterized queries, and managing device
records. It is intended for learning and small experiments, not as a complete
production database layer.

Usage:
     1. Install the PostgreSQL driver: ``pip install psycopg2-binary``
     2. Make sure PostgreSQL is running and the configured user can connect.
     3. Set the optional ``POSTGRES_*`` environment variables, or use the
         defaults (database ``postgres``, user ``postgres``, password
         ``postgres``, host ``localhost``, port ``5432``).
     4. Run this file:
         ``python3 db-lab/postgres_db_client.py``

The sample session creates the ``devices`` table, inserts one device, reads it,
updates its JSON data, reads it again, and finally deletes it. The connection
settings are read by ``build_sample_client`` so the example can be run without
editing the source file.
"""

import logging
import os
import re
import psycopg2

from json import dumps


class DBClient:
    def __init__(self, config, queries, log):
        self.__queries = queries
        self.__log = log
        self.__dbconf = config["connection"]

    def __init_connection(self):
        connection = None
        try:
            connection = psycopg2.connect(database=self.__dbconf["dbName"],
                                          user=self.__dbconf["username"],
                                          password=self.__dbconf["password"],
                                          host=self.__dbconf["server"],
                                          port=self.__dbconf["port"],
                                          connect_timeout=self.__dbconf["timeout"])
            self.__log.debug("Connection to database opened")
        except Exception as e:
            if connection:
                connection.close()
            connection = None
            self.__log.error(f"Failed to connect to database: {str(e)}")
        return connection

    def __commit_query(self, db_query: str, qry_params: tuple = None):
        status = False
        conn = None
        try:
            with self.__init_connection() as conn:
                with conn.cursor() as cursor:
                    if qry_params:
                        cursor.execute(db_query, qry_params)
                    else:
                        cursor.execute(db_query)
                    status = True
        except Exception as e:
            self.__log.error(f"Commit query {db_query} : {str(e)}")
        finally:
            if conn:
                conn.close()
        return status

    def __fetch_query(self, db_query: str, qry_params: list = None):
        result = []
        conn = None
        try:
            with self.__init_connection() as conn:
                with conn.cursor() as cursor:
                    if qry_params:
                        cursor.execute(db_query, qry_params)
                    else:
                        cursor.execute(db_query)
                    result = cursor.fetchall()
        except Exception as e:
            self.__log.error(f"Commit query {db_query} : {str(e)}")
        finally:
            if conn:
                conn.close()
        return result

    def create_db(self):
        conn = None
        result = None
        try:
            # connection establishment
            conn = psycopg2.connect(database="postgres",
                                    user=self.__dbconf["username"],
                                    password=self.__dbconf["password"],
                                    host=self.__dbconf["server"],
                                    port=self.__dbconf["port"],
                                    connect_timeout=self.__dbconf["timeout"])
            conn.autocommit = True
            with conn.cursor() as cursor:
                new_db_name = self.__dbconf["dbName"]
                find_sql = "SELECT 1 FROM pg_catalog.pg_database WHERE datname = (%s)"
                cursor.execute(find_sql, (new_db_name,))
                exists = cursor.fetchone()
                if not exists:
                    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", new_db_name):
                        raise ValueError("Database name contains invalid characters")
                    cursor.execute('CREATE DATABASE "' + new_db_name + '"')
                    cursor.execute(find_sql, (new_db_name,))
                    result = cursor.fetchone()
                else:
                    result = exists
        except Exception as e:
            self.__log.error(f'Create DB : {str(e)}')
        finally:
            if conn:
                conn.close()
        return result

    def create_table(self, query):
        status = self.create_db()
        if not status:
            raise Exception("Create DB failed.")
        db_query = self.__queries[query]
        return self.__commit_query(db_query)

    def save_device(self, device_data, query):
        db_query = self.__queries[query]
        dev_data = dumps(device_data)
        qry_params = (device_data["id"], device_data["name"], dev_data, device_data["name"], dev_data)
        return self.__commit_query(db_query, qry_params)

    def update_db(self, query, dev_id=None, data=None):
        db_query = self.__queries[query]
        qry_params = ()
        if data != None:
            qry_params = qry_params + (data,)
        if dev_id != None:
            qry_params = qry_params + (dev_id,)
        return self.__commit_query(db_query, qry_params)

    def get_devices(self, query, id):
        db_query = self.__queries[query]
        return self.__fetch_query(db_query, (id,))

    def get_devices_with_multi_params(self, query, qry_params=None):
        db_query = self.__queries[query]
        return self.__fetch_query(db_query, qry_params)

    def delete_device(self, query, dev_id):
        db_query = self.__queries[query]
        qry_params = (dev_id,)
        return self.__commit_query(db_query, qry_params)

    def delete_devices_with_multi_params(self, query, qry_params=None):
        db_query = self.__queries[query]
        return self.__commit_query(db_query, qry_params)

    def insert_or_update_db(self, query, qry_params=None):
        db_query = self.__queries[query]
        return self.__commit_query(db_query, qry_params)


def build_sample_client():
    """Build the configured client and SQL statements used by ``main``.

    Environment variables:
        POSTGRES_DB: Database name. Defaults to ``postgres``.
        POSTGRES_USER: PostgreSQL username. Defaults to ``postgres``.
        POSTGRES_PASSWORD: PostgreSQL password. Defaults to ``postgres``.
        POSTGRES_HOST: PostgreSQL host. Defaults to ``localhost``.
        POSTGRES_PORT: PostgreSQL port. Defaults to ``5432``.
        POSTGRES_TIMEOUT: Connection timeout in seconds. Defaults to ``5``.
        
    The sample session creates the ``devices`` table, inserts one device, reads it,
    updates its JSON data, reads it again, and finally deletes it. The connection
    settings are read by ``build_sample_client`` so the example can be run without
    editing the source file.
    """
    config = {
        "connection": {
            "dbName": os.getenv("POSTGRES_DB", "postgres"),
            "username": os.getenv("POSTGRES_USER", "postgres"),
            "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
            "server": os.getenv("POSTGRES_HOST", "localhost"),
            "port": os.getenv("POSTGRES_PORT", "5432"),
            "timeout": int(os.getenv("POSTGRES_TIMEOUT", "5")),
        }
    }
    queries = {
        "create_table": """
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                data JSONB NOT NULL
            )
        """,
        "save_device": """
            INSERT INTO devices (id, name, data)
            VALUES (%s, %s, %s::jsonb)
            ON CONFLICT (id) DO UPDATE SET
                name = %s,
                data = %s::jsonb
        """,
        "get_devices": """
            SELECT id, name, data
            FROM devices
            WHERE name = %s
            ORDER BY id
        """,
        "update_device": """
            UPDATE devices
            SET data = %s::jsonb
            WHERE id = %s
        """,
        "delete_device": "DELETE FROM devices WHERE id = %s",
    }
    return DBClient(config, queries, logging.getLogger(__name__))


def main():
    """Run a complete insert, read, update, and delete example session."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    # Create the client and sample table before starting the CRUD session.
    client = build_sample_client()

    if not client.create_table("create_table"):
        raise RuntimeError("Could not create the sample table")

    # Insert a device, then query it by the name used by the sample SQL.
    device = {"id": 1, "name": "device_1", "data": {"type": "camera", "enabled": True}}
    client.save_device(device, "save_device")
    print("After insert:", client.get_devices("get_devices", device["name"]))

    # Update the JSON payload and verify the new value.
    client.update_db("update_device", device["id"], dumps({**device, "enabled": False}))
    print("After update:", client.get_devices("get_devices", device["name"]))

    # Remove the sample record so repeated runs leave the database clean.
    client.delete_device("delete_device", device["id"])
    print("After delete:", client.get_devices("get_devices", device["name"]))


if __name__ == "__main__":
    main()
