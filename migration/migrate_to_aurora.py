"""
Migrates items from the DynamoDB `Orders` table into Aurora PostgreSQL
(created via the AWS CLI "express configuration" flow, IAM auth only -
no static password, no VPC).

Idempotent by design: safe to re-run. Uses ON CONFLICT DO UPDATE so
re-running this script never creates duplicate rows or errors out -
mirrors the JD's "repeatable, safe to re-run" migration requirement.

Usage:
    python migrate_to_aurora.py <aurora-endpoint> <region>
"""

import sys
import boto3
import psycopg2

DYNAMO_TABLE_NAME = "Orders"
DB_USER = "postgres"
DB_PORT = 5432
APP_DB_NAME = "orderflow"


def generate_auth_token(endpoint: str, region: str) -> str:
    client = boto3.client("rds", region_name=region)
    return client.generate_db_auth_token(
        DBHostname=endpoint, Port=DB_PORT, DBUsername=DB_USER, Region=region
    )


def connect(endpoint: str, region: str, dbname: str):
    token = generate_auth_token(endpoint, region)
    return psycopg2.connect(
        host=endpoint,
        port=DB_PORT,
        dbname=dbname,
        user=DB_USER,
        password=token,
        sslmode="require",
    )


def ensure_app_database(endpoint: str, region: str):
    conn = connect(endpoint, region, "postgres")
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (APP_DB_NAME,))
        if cur.fetchone() is None:
            cur.execute(f"CREATE DATABASE {APP_DB_NAME}")
            print(f"Created database '{APP_DB_NAME}'.")
        else:
            print(f"Database '{APP_DB_NAME}' already exists.")
    conn.close()


def apply_schema(conn):
    with open("schema.sql", "r") as f:
        schema_sql = f.read()
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
        cur.execute(schema_sql)
    conn.commit()


def scan_dynamo_orders() -> list:
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(DYNAMO_TABLE_NAME)
    items = []
    response = table.scan()
    items.extend(response.get("Items", []))
    while "LastEvaluatedKey" in response:
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response.get("Items", []))
    return items


def migrate(conn, orders):
    with conn.cursor() as cur:
        for order in orders:
            customer_name = order["customerName"]
            order_id = order["orderId"]
            item = order["item"]
            amount = order["amount"]
            created_at = order["createdAt"]

            cur.execute(
                """
                INSERT INTO customers (name)
                VALUES (%s)
                ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
                RETURNING customer_id
                """,
                (customer_name,),
            )
            customer_id = cur.fetchone()[0]

            cur.execute(
                """
                INSERT INTO orders (order_id, customer_id, item, amount, created_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (order_id) DO UPDATE SET
                    customer_id = EXCLUDED.customer_id,
                    item = EXCLUDED.item,
                    amount = EXCLUDED.amount,
                    created_at = EXCLUDED.created_at
                """,
                (order_id, customer_id, item, amount, created_at),
            )
    conn.commit()


def main():
    if len(sys.argv) != 3:
        print("Usage: python migrate_to_aurora.py <aurora-endpoint> <region>")
        sys.exit(1)

    endpoint = sys.argv[1]
    region = sys.argv[2]

    print(f"Ensuring '{APP_DB_NAME}' database exists...")
    ensure_app_database(endpoint, region)

    print(f"Connecting to '{APP_DB_NAME}'...")
    conn = connect(endpoint, region, APP_DB_NAME)

    print("Applying schema (idempotent - CREATE TABLE IF NOT EXISTS)...")
    apply_schema(conn)

    print("Scanning DynamoDB Orders table...")
    orders = scan_dynamo_orders()
    print(f"Found {len(orders)} order(s) to migrate.")

    print("Migrating (idempotent upsert)...")
    migrate(conn, orders)

    conn.close()
    print("Migration complete. Safe to re-run this script at any time.")


if __name__ == "__main__":
    main()