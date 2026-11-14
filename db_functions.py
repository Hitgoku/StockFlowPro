import os
from mysql.connector import connect
from dotenv import load_dotenv

load_dotenv()


# we will create function out of it to use/establish connection if needed
def conn_to_db():
    return connect(
        host=os.getenv("DB_HOST"),
        port=3306,
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        connection_timeout=10
    )


# store all your SQL queries inside one Python dictionary.
# This is useful for your Inventory & Supply Chain project
# because Python can access each query by its name whenever needed
# Same using function
def get_basic_info(cursor):
    queries = {

        # 1. Total Suppliers
        "total_suppliers": """
                           SELECT COUNT(*) AS total_suppliers
                           FROM suppliers;
                           """,

        # 2. Total Products
        "total_products": """
                          SELECT COUNT(*) AS total_products
                          FROM products;
                          """,

        # 3. Total Categories Dealing
        "total_categories": """
                            SELECT COUNT(DISTINCT category) AS total_categories
                            FROM products;
                            """,

        # 4. Total Sales Made in Last 3 Months
        "total_sales_3_months": """
                                SELECT COALESCE(
                                               ROUND(SUM(ABS(se.change_quantity) * p.price), 2),
                                               0) AS total_sales_3_months
                                FROM stock_entries AS se
                                         JOIN products AS p
                                              ON p.product_id = se.product_id
                                WHERE se.change_type = 'Sale'
                                  AND se.entry_date >= (SELECT DATE_SUB(MAX(entry_date), INTERVAL 3 MONTH)
                                                        FROM stock_entries);
                                """,

        # 5. Total Restock Made in Last 3 Months
        "total_restock_3_months": """
                                  SELECT ROUND(SUM(ABS(se.change_quantity) * p.price), 2)
                                             AS total_restock_3_months
                                  FROM stock_entries AS se
                                           JOIN products AS p
                                                ON p.product_id = se.product_id
                                  WHERE se.change_type = 'Restock'
                                    AND se.entry_date >= (SELECT DATE_SUB(MAX(entry_date), INTERVAL 3 MONTH)
                                                          FROM stock_entries);
                                  """,

        # 6. Products Below Reorder Level Without Pending Orders
        "products_below_reorder": """
                                  SELECT COUNT(*) AS products_below_reorder
                                  FROM products AS p
                                  WHERE p.stock_quantity < p.reorder_level
                                    AND p.product_id NOT IN (SELECT DISTINCT product_id
                                                             FROM reorders
                                                             WHERE status = 'Pending');
                                  """
    }
    res = {}
    for label, query in queries.items():
        cursor.execute(query)
        row = cursor.fetchone()
        res[label] = list(row.values())[0]
    return res


def get_additional_tables(cursor):
    queries = {
        # 7. Suppliers and their contact details
        "supplier_contact_details": """
                                    SELECT supplier_name, contact_name, email, phone
                                    FROM suppliers;
                                    """,

        # 8. Products with their suppliers and current stock
        "products_with_suppliers": """
                                   SELECT p.product_name,
                                          s.supplier_name,
                                          p.stock_quantity,
                                          p.reorder_level
                                   FROM products AS p
                                            JOIN suppliers AS s
                                                 ON p.supplier_id = s.supplier_id
                                   ORDER BY p.product_name ASC;
                                   """,

        # 9. Products needing reorder
        "products_needing_reorder": """
                                    SELECT product_id,
                                           product_name,
                                           stock_quantity,
                                           reorder_level
                                    FROM products
                                    WHERE stock_quantity < reorder_level;
                                    """
    }

    tables = {}
    for label, query in queries.items():
        cursor.execute(query)
        tables[label] = cursor.fetchall()

    return tables


def get_categories(cursor):
    cursor.execute("select Distinct category from products order by category asc")
    rows = cursor.fetchall()
    return [row["category"] for row in rows]


def get_suppliers(cursor):
    cursor.execute("select supplier_id,supplier_name from suppliers order by supplier_name asc")
    return cursor.fetchall()


def add_new_manual_id(cursor, db, p_name, p_category, p_price, p_stock, p_reorder, p_supplier):
    procedure_call = "CALL AddNewProductManualID(%s,%s,%s,%s,%s,%s)"

    parameter = (p_name, p_category, p_price, p_stock, p_reorder, p_supplier)

    cursor.execute(procedure_call, parameter)

    db.commit()


# Retrieve all products so the warehouse employee can select which product's history they want to view.
def get_all_products(cursor):
    cursor.execute("select product_id,product_name from products order by product_name")
    return cursor.fetchall()


# Retrieve all historical activities for the product selected by the employee.
def get_product_history(cursor, product_id):
    query = "select * from product_inventory_history where product_id=%s order by record_date desc"
    cursor.execute(query, (product_id,))
    return cursor.fetchall()


# to place a reorder for a product in our  inventory application.
def place_reorder(cursor, db, product_id, reorder_quantity):
    query = """
            insert into reorders (reorder_id, product_id, reorder_quantity, reorder_date, status)
            select max(reorder_id) + 1, %s, %s, curdate(), "ordered"
            from reorders \
            """
    cursor.execute(query, (product_id, reorder_quantity))
    db.commit()


# to get/fetch pending orderrs in ordered state
def get_pending_reorders(cursor):
    cursor.execute("""
                   select r.reorder_id, p.product_name
                   from reorders as r
                            join products as p
                                 on r.product_id = p.product_id
                   """)
    return cursor.fetchall()


# to execute store procedure
def mark_reorder_as_received(cursor, db, reorder_id):
    cursor.callproc("MarkReorderAsReceived", [reorder_id])
    db.commit()
