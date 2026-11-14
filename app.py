import pandas as pd
import streamlit as st

from db_functions import *

# Sidebar
st.sidebar.title("Inventory Management Dashboard")

option = st.sidebar.radio(
    "Select Options:", ["Basic Information", "Operational Tasks"]
)

# Main space
st.set_page_config(
    layout="wide"
)
st.title("Inventory and Supply Chain Dashboard")
db = conn_to_db()

# A cursor is an object in Python that allows Python to communicate with your MySQL database and execute SQL commands.
# Think of it like a messenger between Python and MySQL.
# - Python sends an SQL command.
# - Cursor executes that command in MySQL.
# - Cursor helps Python collect the result.

cursor = db.cursor(dictionary=True)

# ------------------- Basic information page-----------------------------
if option == "Basic Information":
    st.header("Basic Metrics")

    # get basic info from DB
    # - get_basic_info() is a function imported from db_functions.py.
    # - cursor sends SQL commands to MySQL.
    # - The function retrieves basic inventory information.
    # - The returned information is stored in basic_info.
    basic_info = get_basic_info(cursor)
    # st.write(basic_info)

    cols = st.columns(3)
    keys = list(basic_info.keys())

    # cols[i] selects a particular column.
    # metric() displays a metric card.
    # label=keys[i] displays the metric name.
    # value=basic_info[keys[i]] retrieves the corresponding metric value.

    for i in range(3):
        cols[i].metric(label=keys[i], value=basic_info[keys[i]])

    cols = st.columns(3)
    for i in range(3, 6):
        cols[i - 3].metric(label=keys[i], value=basic_info[keys[i]])

    # You might wonder why we subtract 3.
    # Because your columns have indexes starting from zero:
    # - First column = cols[0]
    # - Second column = cols[1]
    # - Third column = cols[2]

    st.divider()

    # fetch and display all details in tabular form
    tables = get_additional_tables(cursor)
    for labels, data in tables.items():
        st.header(labels)
        df = pd.DataFrame(data)
        st.dataframe(df)
        st.divider()

elif option == "Operational Tasks":
    st.header("Operational Tasks")
    selected_task = st.selectbox("Choose a Task:",
                                 ["Add New Product", "Product History", "Place Reorder", "Receive Reorder"])
    if selected_task == "Add New Product":
        st.header("Add New Product")
        categories = get_categories(cursor)
        suppliers = get_suppliers(cursor)

        with st.form("Add Product Form"):
            product_name = st.text_input("Enter Product Name")
            product_category = st.selectbox("Select Product Category", categories)
            product_price = st.number_input("Enter Product Price", min_value=0.00)
            product_stock = st.number_input("Stock Quantity", min_value=0, step=1)
            product_level = st.number_input("Reorder level", min_value=0, step=1)

            supplier_ids = [s["supplier_id"] for s in suppliers]
            supplier_names = [s["supplier_name"] for s in suppliers]

            supplier_id = st.selectbox("Select Supplier", supplier_ids,
                                       format_func=lambda x: supplier_names[supplier_ids.index(x)])
            submitted = st.form_submit_button("Add New Product")

            if submitted:
                if not product_name:
                    st.error("Product Name is required")
                else:
                    try:
                        add_new_manual_id(cursor, db, product_name, product_category,
                                          product_price, product_stock, product_level, supplier_id)
                        st.success(f"Product {product_name} Added Successfully")
                    except Exception as e:
                        st.error(f"Error adding Product {product_name} Failed with {e}")

    # --------------------------------Product history----------------------------------------------------------

    if selected_task == "Product History":
        st.header("Product Inventory History")

        # get product list
        products = get_all_products(cursor)
        product_names = [p['product_name'] for p in products]
        product_ids = [p['product_id'] for p in products]

        selected_product_name = st.selectbox("Select Product Name", product_names)

        if selected_product_name:
            selected_product_id = product_ids[product_names.index(selected_product_name)]
            history_data = get_product_history(cursor, selected_product_id)

            if history_data:
                df = pd.DataFrame(history_data)
                st.dataframe(df)
            else:
                st.info("No history available for this product.")

    # ----------------------------------Place Reorder-----------------------------------------------------------
    if selected_task == "Place Reorder":
        st.header("Place Reorder")

        # get product list
        products = get_all_products(cursor)
        product_names = [p['product_name'] for p in products]
        product_ids = [p['product_id'] for p in products]

        selected_product_name = st.selectbox("Select Product Name", product_names)
        reorder_qty = st.number_input("Reorder Quantity", min_value=1, step=1)

        if st.button("Place Reorder"):
            if not selected_product_name:
                st.error("Product Name is required")
            elif reorder_qty < 1:
                st.error("Quantity must be greater than 0")
            else:
                selected_product_id = product_ids[product_names.index(selected_product_name)]
                try:
                    place_reorder(cursor, db, selected_product_id, reorder_qty)
                    st.success(f"Product {selected_product_name} Reordered with qunatity {reorder_qty} Successfully")
                except Exception as e:
                    st.error(f"Error reordering Product {selected_product_name} Failed with {e}")

    # ----------------------------Receiving an order----------------------------------
    if selected_task == "Receive Reorder":
        st.header("Mark Receive Reorder")
        # fetch orders in oredered stage
        pending_reorders = get_pending_reorders(cursor)
        if not pending_reorders:
            st.info("No pending reorders available.")
        else:
            reorder_ids = [r['reorder_id'] for r in pending_reorders]
            reorder_labels = [f"ID {r['reorder_id']} - {r['product_name']}" for r in pending_reorders]

            selected_label = st.selectbox("Select reorder to mark as received", reorder_labels)

            if selected_label:
                selected_reorder_id = reorder_ids[reorder_labels.index(selected_label)]

                if st.button("Mark as Receive"):
                    try:
                        mark_reorder_as_received(cursor, db, selected_reorder_id)
                        st.success(f"Reordered id {selected_reorder_id} mark as received")
                    except Exception as e:
                        st.error(f"Error marking reorder as received {e}")
