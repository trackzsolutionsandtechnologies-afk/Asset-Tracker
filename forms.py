"""
Forms module for Asset Tracker
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from google_sheets import read_data, append_data, update_data, delete_data, find_row
from config import SHEETS, SESSION_KEYS
from auth import hash_password

def generate_location_id() -> str:
    """Generate a unique Location ID"""
    import uuid
    # Generate a short unique ID
    return f"LOC-{uuid.uuid4().hex[:8].upper()}"

def generate_supplier_id() -> str:
    """Generate a unique Supplier ID"""
    import uuid
    # Generate a short unique ID
    return f"SUP-{uuid.uuid4().hex[:8].upper()}"

def generate_category_id() -> str:
    """Generate a unique Category ID"""
    import uuid
    # Generate a short unique ID
    return f"CAT-{uuid.uuid4().hex[:8].upper()}"

def generate_subcategory_id() -> str:
    """Generate a unique Sub Category ID"""
    import uuid
    # Generate a short unique ID
    return f"SUB-{uuid.uuid4().hex[:8].upper()}"

def location_form():
    """Location"""
    st.header("📍 Location Management")
    
    df = read_data(SHEETS["locations"])
    
    tab1, tab2 = st.tabs(["Add New Location", "View/Edit Locations"])
    
    with tab1:
        # Green Add Location button styling, white form background, and hide loading indicators
        st.markdown("""
            <style>
            /* White background for Add Location */
            div[data-testid="stForm"] {
                background-color: white !important;
                padding: 20px !important;
                border-radius: 10px !important;
                border: 1px solid #e0e0e0 !important;
            }
            /* Target the primary button in the Location section */
            div[data-testid="stForm"] button[kind="primary"],
            button.stButton > button[kind="primary"] {
                background-color: #28a745 !important;
                color: white !important;
                border-color: #28a745 !important;
            }
            div[data-testid="stForm"] button[kind="primary"]:hover,
            button.stButton > button[kind="primary"]:hover {
                background-color: #218838 !important;
                border-color: #1e7e34 !important;
            }
            /* Hide loading indicators */
            [data-testid="stStatusWidget"] {
                display: none !important;
            }
            .stSpinner {
                display: none !important;
            }
            </style>
        """, unsafe_allow_html=True)
        
        # Show success message if exists
        if "location_success_message" in st.session_state:
            st.success(st.session_state["location_success_message"])
            # Clear message after showing
            del st.session_state["location_success_message"]
        
        # Initialize form key for reset
        if "location_form_key" not in st.session_state:
            st.session_state["location_form_key"] = 0
        
        with st.form(key=f"location_form_{st.session_state['location_form_key']}"):
            auto_generate = st.checkbox("Auto-generate Location ID", value=True, key=f"auto_gen_{st.session_state['location_form_key']}")
            if auto_generate:
                # Generate ID once and store in session state
                if "generated_location_id" not in st.session_state:
                    st.session_state["generated_location_id"] = generate_location_id()
                location_id = st.text_input("Location ID *", value=st.session_state["generated_location_id"], disabled=True, help="Auto-generated unique identifier", key=f"loc_id_{st.session_state['location_form_key']}")
            else:
                location_id = st.text_input("Location ID *", help="Unique identifier for the location", key=f"loc_id_manual_{st.session_state['location_form_key']}")
                if "generated_location_id" in st.session_state:
                    del st.session_state["generated_location_id"]
            
            location_name = st.text_input("Location Name *", key=f"loc_name_{st.session_state['location_form_key']}")
            department = st.text_input("Department *", key=f"dept_{st.session_state['location_form_key']}")
            
            submitted = st.form_submit_button("Add Location", use_container_width=True, type="primary")
            
            if submitted:
                if not location_id or not location_name or not department:
                    st.error("Please fill in all required fields")
                elif not df.empty and "Location ID" in df.columns and location_id in df["Location ID"].values:
                    st.error("Location ID already exists")
                else:
                    with st.spinner("Adding location..."):
                        if append_data(SHEETS["locations"], [location_id, location_name, department]):
                            # Clear generated location ID and reset form
                            if "generated_location_id" in st.session_state:
                                del st.session_state["generated_location_id"]
                            # Clear search bar
                            if "location_search" in st.session_state:
                                del st.session_state["location_search"]
                            # Set success message
                            st.session_state["location_success_message"] = f"✅ Location '{location_name}' (ID: {location_id}) added successfully!"
                            # Increment form key to reset form
                            st.session_state["location_form_key"] += 1
                            st.rerun()
                        else:
                            st.error("Failed to add location")
    
    with tab2:
        # Show success message if exists
        if "location_success_message" in st.session_state:
            st.success(st.session_state["location_success_message"])
            # Clear message after showing
            del st.session_state["location_success_message"]
        
        if not df.empty and "Location ID" in df.columns:
            st.subheader("All Locations")
            
            # Search bar
            search_term = st.text_input("🔍 Search Locations", placeholder="Search by Location ID, Name, or Department...", key="location_search")
            
            # Filter data based on search
            if search_term:
                mask = (
                    df["Location ID"].astype(str).str.contains(search_term, case=False, na=False) |
                    df["Location Name"].astype(str).str.contains(search_term, case=False, na=False) |
                    df["Department"].astype(str).str.contains(search_term, case=False, na=False)
                )
                filtered_df = df[mask]
                if filtered_df.empty:
                    st.info(f"No locations found matching '{search_term}'")
                    filtered_df = pd.DataFrame()
            else:
                filtered_df = df
            
            if not filtered_df.empty:
                # Show count
                st.caption(f"Showing {len(filtered_df)} of {len(df)} location(s)")
                
                # Check if user is admin
                user_role = st.session_state.get(SESSION_KEYS.get("user_role", "user_role"), "user")
                is_admin = user_role.lower() == "admin"
                
                # Table header - adjust columns based on admin status
                if is_admin:
                    header_col1, header_col2, header_col3, header_col4, header_col5 = st.columns([2, 3, 3, 1, 1])
                    with header_col1:
                        st.write("**Location ID**")
                    with header_col2:
                        st.write("**Location Name**")
                    with header_col3:
                        st.write("**Department**")
                    with header_col4:
                        st.write("**Edit**")
                    with header_col5:
                        st.write("**Delete**")
                else:
                    header_col1, header_col2, header_col3, header_col4 = st.columns([2, 3, 3, 1])
                    with header_col1:
                        st.write("**Location ID**")
                    with header_col2:
                        st.write("**Location Name**")
                    with header_col3:
                        st.write("**Department**")
                    with header_col4:
                        st.write("**Edit**")
                st.divider()

                # Display table with edit/delete buttons
                for idx, row in filtered_df.iterrows():
                    # Get original index from df for delete/update operations
                    # Convert to Python int to avoid JSON serialization issues
                    if not df[df["Location ID"] == row.get('Location ID', '')].empty:
                        original_idx = int(df[df["Location ID"] == row.get('Location ID', '')].index[0])
                    else:
                        original_idx = int(idx) if isinstance(idx, (int, type(pd.NA))) else 0

                    if is_admin:
                        col1, col2, col3, col4, col5 = st.columns([2, 3, 3, 1, 1])
                    else:
                        col1, col2, col3, col4 = st.columns([2, 3, 3, 1])

                    with col1:
                        st.write(row.get('Location ID', 'N/A'))
                    with col2:
                        st.write(row.get('Location Name', 'N/A'))
                    with col3:
                        st.write(row.get('Department', 'N/A'))
                    with col4:
                        edit_key = f"edit_loc_{row.get('Location ID', idx)}"
                        if st.button("✏️", key=edit_key, use_container_width=True, help="Edit this location"):
                            st.session_state["edit_location_id"] = row.get('Location ID', '')
                            st.session_state["edit_location_idx"] = int(original_idx)  # Ensure it's a Python int
                            st.rerun()
                    # Only show delete button for admin users
                    if is_admin:
                        with col5:
                            delete_key = f"delete_loc_{row.get('Location ID', idx)}"
                            if st.button("🗑️", key=delete_key, use_container_width=True, help="Delete this location"):
                                location_name_to_delete = row.get('Location Name', 'Unknown')
                                location_id_to_delete = row.get('Location ID', 'Unknown')
                                if delete_data(SHEETS["locations"], original_idx):
                                    # Set success message
                                    st.session_state["location_success_message"] = f"✅ Location '{location_name_to_delete}' (ID: {location_id_to_delete}) deleted successfully!"
                                    # Clear search bar
                                    if "location_search" in st.session_state:
                                        del st.session_state["location_search"]
                                    st.rerun()
                                else:
                                    st.error("Failed to delete location")
                    
                    st.divider()
            elif search_term:
                # Search returned no results, but search was performed
                pass
            else:
                st.info("No locations found. Add a new location using the 'Add New Location' tab.")
            
            # Edit form (shown when edit button is clicked)
            if "edit_location_id" in st.session_state and st.session_state["edit_location_id"]:
                st.subheader("Edit Location")
                edit_id = st.session_state["edit_location_id"]
                edit_idx = st.session_state.get("edit_location_idx", 0)
                
                location_rows = df[df["Location ID"] == edit_id]
                if not location_rows.empty:
                    location = location_rows.iloc[0]
                    
                    with st.form("edit_location_form"):
                        new_location_id = st.text_input("Location ID", value=location.get("Location ID", ""), disabled=True)
                        new_location_name = st.text_input("Location Name", value=location.get("Location Name", ""))
                        new_department = st.text_input("Department", value=location.get("Department", ""))
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("Update Location", use_container_width=True):
                                with st.spinner("Updating location..."):
                                    if update_data(SHEETS["locations"], edit_idx, [new_location_id, new_location_name, new_department]):
                                        # Set success message
                                        st.session_state["location_success_message"] = f"✅ Location '{new_location_name}' (ID: {new_location_id}) updated successfully!"
                                        if "edit_location_id" in st.session_state:
                                            del st.session_state["edit_location_id"]
                                        if "edit_location_idx" in st.session_state:
                                            del st.session_state["edit_location_idx"]
                                        # Clear search bar
                                        if "location_search" in st.session_state:
                                            del st.session_state["location_search"]
                                        st.rerun()
                                    else:
                                        st.error("Failed to update location")
                        with col2:
                            if st.form_submit_button("Cancel", use_container_width=True):
                                if "edit_location_id" in st.session_state:
                                    del st.session_state["edit_location_id"]
                                if "edit_location_idx" in st.session_state:
                                    del st.session_state["edit_location_idx"]
                                st.rerun()
        else:
            st.info("No locations found. Add a new location using the 'Add New Location' tab.")

def supplier_form():
    """Supplier"""
    st.header("🚚 Supplier Management")
    
    df = read_data(SHEETS["suppliers"])
    
    tab1, tab2 = st.tabs(["Add New Supplier", "View/Edit Suppliers"])
    
    with tab1:
        # Green Add Supplier button styling, white form background, and hide loading indicators
        st.markdown("""
            <style>
            /* White background for Add Supplier */
            div[data-testid="stForm"] {
                background-color: white !important;
                padding: 20px !important;
                border-radius: 10px !important;
                border: 1px solid #e0e0e0 !important;
            }
            /* Target the primary button in the Supplier section */
            div[data-testid="stForm"] button[kind="primary"],
            button.stButton > button[kind="primary"] {
                background-color: #28a745 !important;
                color: white !important;
                border-color: #28a745 !important;
            }
            div[data-testid="stForm"] button[kind="primary"]:hover,
            button.stButton > button[kind="primary"]:hover {
                background-color: #218838 !important;
                border-color: #1e7e34 !important;
            }
            /* Hide loading indicators */
            [data-testid="stStatusWidget"] {
                display: none !important;
            }
            .stSpinner {
                display: none !important;
            }
            </style>
        """, unsafe_allow_html=True)
        
        # Show success message if exists
        if "supplier_success_message" in st.session_state:
            st.success(st.session_state["supplier_success_message"])
            # Clear message after showing
            del st.session_state["supplier_success_message"]
        
        # Initialize form key for reset
        if "supplier_form_key" not in st.session_state:
            st.session_state["supplier_form_key"] = 0
        
        with st.form(key=f"supplier_form_{st.session_state['supplier_form_key']}"):
            auto_generate = st.checkbox("Auto-generate Supplier ID", value=True, key=f"auto_gen_sup_{st.session_state['supplier_form_key']}")
            if auto_generate:
                # Generate ID once and store in session state
                if "generated_supplier_id" not in st.session_state:
                    st.session_state["generated_supplier_id"] = generate_supplier_id()
                supplier_id = st.text_input("Supplier ID *", value=st.session_state["generated_supplier_id"], disabled=True, help="Auto-generated unique identifier", key=f"sup_id_{st.session_state['supplier_form_key']}")
            else:
                supplier_id = st.text_input("Supplier ID *", help="Unique identifier for the supplier", key=f"sup_id_manual_{st.session_state['supplier_form_key']}")
                if "generated_supplier_id" in st.session_state:
                    del st.session_state["generated_supplier_id"]
            
            supplier_name = st.text_input("Supplier Name *", key=f"sup_name_{st.session_state['supplier_form_key']}")
            
            submitted = st.form_submit_button("Add Supplier", use_container_width=True, type="primary")
            
            if submitted:
                if not supplier_id or not supplier_name:
                    st.error("Please fill in all required fields")
                elif not df.empty and "Supplier ID" in df.columns and supplier_id in df["Supplier ID"].values:
                    st.error("Supplier ID already exists")
                else:
                    with st.spinner("Adding supplier..."):
                        if append_data(SHEETS["suppliers"], [supplier_id, supplier_name]):
                            # Clear generated supplier ID and reset form
                            if "generated_supplier_id" in st.session_state:
                                del st.session_state["generated_supplier_id"]
                            # Clear search bar
                            if "supplier_search" in st.session_state:
                                del st.session_state["supplier_search"]
                            # Set success message
                            st.session_state["supplier_success_message"] = f"✅ Supplier '{supplier_name}' (ID: {supplier_id}) added successfully!"
                            # Increment form key to reset form
                            st.session_state["supplier_form_key"] += 1
                            st.rerun()
                        else:
                            st.error("Failed to add supplier")
    
    with tab2:
        # Show success message if exists
        if "supplier_success_message" in st.session_state:
            st.success(st.session_state["supplier_success_message"])
            # Clear message after showing
            del st.session_state["supplier_success_message"]
        
        if not df.empty and "Supplier ID" in df.columns:
            st.subheader("All Suppliers")
            
            # Search bar
            search_term = st.text_input("🔍 Search Suppliers", placeholder="Search by Supplier ID or Name...", key="supplier_search")
            
            # Filter data based on search
            if search_term:
                mask = (
                    df["Supplier ID"].astype(str).str.contains(search_term, case=False, na=False) |
                    df["Supplier Name"].astype(str).str.contains(search_term, case=False, na=False)
                )
                filtered_df = df[mask]
                if filtered_df.empty:
                    st.info(f"No suppliers found matching '{search_term}'")
                    filtered_df = pd.DataFrame()
            else:
                filtered_df = df
            
            if not filtered_df.empty:
                # Show count
                st.caption(f"Showing {len(filtered_df)} of {len(df)} supplier(s)")
                
                # Check if user is admin
                user_role = st.session_state.get(SESSION_KEYS.get("user_role", "user_role"), "user")
                is_admin = user_role.lower() == "admin"
                
                # Table header - adjust columns based on admin status
                if is_admin:
                    header_col1, header_col2, header_col3, header_col4 = st.columns([3, 4, 1, 1])
                    with header_col1:
                        st.write("**Supplier ID**")
                    with header_col2:
                        st.write("**Supplier Name**")
                    with header_col3:
                        st.write("**Edit**")
                    with header_col4:
                        st.write("**Delete**")
                else:
                    header_col1, header_col2, header_col3 = st.columns([3, 4, 1])
                    with header_col1:
                        st.write("**Supplier ID**")
                    with header_col2:
                        st.write("**Supplier Name**")
                    with header_col3:
                        st.write("**Edit**")
                st.divider()

                # Display table with edit/delete buttons
                for idx, row in filtered_df.iterrows():
                    # Get original index from df for delete/update operations
                    # Convert to Python int to avoid JSON serialization issues
                    if not df[df["Supplier ID"] == row.get('Supplier ID', '')].empty:
                        original_idx = int(df[df["Supplier ID"] == row.get('Supplier ID', '')].index[0])
                    else:
                        original_idx = int(idx) if isinstance(idx, (int, type(pd.NA))) else 0

                    if is_admin:
                        col1, col2, col3, col4 = st.columns([3, 4, 1, 1])
                    else:
                        col1, col2, col3 = st.columns([3, 4, 1])

                    with col1:
                        st.write(row.get('Supplier ID', 'N/A'))
                    with col2:
                        st.write(row.get('Supplier Name', 'N/A'))
                    with col3:
                        edit_key = f"edit_sup_{row.get('Supplier ID', idx)}"
                        if st.button("✏️", key=edit_key, use_container_width=True, help="Edit this supplier"):
                            st.session_state["edit_supplier_id"] = row.get('Supplier ID', '')
                            st.session_state["edit_supplier_idx"] = int(original_idx)  # Ensure it's a Python int
                            st.rerun()
                    # Only show delete button for admin users
                    if is_admin:
                        with col4:
                            delete_key = f"delete_sup_{row.get('Supplier ID', idx)}"
                            if st.button("🗑️", key=delete_key, use_container_width=True, help="Delete this supplier"):
                                supplier_name_to_delete = row.get('Supplier Name', 'Unknown')
                                supplier_id_to_delete = row.get('Supplier ID', 'Unknown')
                                if delete_data(SHEETS["suppliers"], original_idx):
                                    # Set success message
                                    st.session_state["supplier_success_message"] = f"✅ Supplier '{supplier_name_to_delete}' (ID: {supplier_id_to_delete}) deleted successfully!"
                                    # Clear search bar
                                    if "supplier_search" in st.session_state:
                                        del st.session_state["supplier_search"]
                                    st.rerun()
                                else:
                                    st.error("Failed to delete supplier")
                    
                    st.divider()
            elif search_term:
                # Search returned no results, but search was performed
                pass
            else:
                st.info("No suppliers found. Add a new supplier using the 'Add New Supplier' tab.")

            # Edit form (shown when edit button is clicked)
            if "edit_supplier_id" in st.session_state and st.session_state["edit_supplier_id"]:
                st.subheader("Edit Supplier")
                edit_id = st.session_state["edit_supplier_id"]
                edit_idx = st.session_state.get("edit_supplier_idx", 0)
                
                supplier_rows = df[df["Supplier ID"] == edit_id]
                if not supplier_rows.empty:
                    supplier = supplier_rows.iloc[0]
                    
                    with st.form("edit_supplier_form"):
                        new_supplier_id = st.text_input("Supplier ID", value=supplier.get("Supplier ID", ""), disabled=True)
                        new_supplier_name = st.text_input("Supplier Name", value=supplier.get("Supplier Name", ""))
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("Update Supplier", use_container_width=True):
                                with st.spinner("Updating supplier..."):
                                    if update_data(SHEETS["suppliers"], edit_idx, [new_supplier_id, new_supplier_name]):
                                        # Set success message
                                        st.session_state["supplier_success_message"] = f"✅ Supplier '{new_supplier_name}' (ID: {new_supplier_id}) updated successfully!"
                                        if "edit_supplier_id" in st.session_state:
                                            del st.session_state["edit_supplier_id"]
                                        if "edit_supplier_idx" in st.session_state:
                                            del st.session_state["edit_supplier_idx"]
                                        # Clear search bar
                                        if "supplier_search" in st.session_state:
                                            del st.session_state["supplier_search"]
                                        st.rerun()
                                    else:
                                        st.error("Failed to update supplier")
                        with col2:
                            if st.form_submit_button("Cancel", use_container_width=True):
                                if "edit_supplier_id" in st.session_state:
                                    del st.session_state["edit_supplier_id"]
                                if "edit_supplier_idx" in st.session_state:
                                    del st.session_state["edit_supplier_idx"]
                                st.rerun()
                else:
                    st.warning("Selected supplier not found in data.")
        else:
            st.info("No suppliers found. Add a new supplier using the 'Add New Supplier' tab.")

def category_form():
    """Asset Category and Sub Category"""
    st.header("📂 Category Management")
    
    categories_df = read_data(SHEETS["categories"])
    subcategories_df = read_data(SHEETS["subcategories"])
    
    tab1, tab2, tab3, tab4 = st.tabs(["Add Category", "Add Sub Category", "View/Edit Categories", "View/Edit Sub Categories"])
    
    with tab1:
        # Green Add Category button styling, white form background, and hide loading indicators
        st.markdown("""
            <style>
            /* White background for Add Category */
            div[data-testid="stForm"] {
                background-color: white !important;
                padding: 20px !important;
                border-radius: 10px !important;
                border: 1px solid #e0e0e0 !important;
            }
            /* Target the primary button in the Category section */
            div[data-testid="stForm"] button[kind="primary"],
            button.stButton > button[kind="primary"] {
                background-color: #28a745 !important;
                color: white !important;
                border-color: #28a745 !important;
            }
            div[data-testid="stForm"] button[kind="primary"]:hover,
            button.stButton > button[kind="primary"]:hover {
                background-color: #218838 !important;
                border-color: #1e7e34 !important;
            }
            /* Hide loading indicators */
            [data-testid="stStatusWidget"] {
                display: none !important;
            }
            .stSpinner {
                display: none !important;
            }
            </style>
        """, unsafe_allow_html=True)
        
        # Show success message if exists
        if "category_success_message" in st.session_state:
            st.success(st.session_state["category_success_message"])
            # Clear message after showing
            del st.session_state["category_success_message"]
        
        # Initialize form key for reset
        if "category_form_key" not in st.session_state:
            st.session_state["category_form_key"] = 0
        
        with st.form(key=f"category_form_{st.session_state['category_form_key']}"):
            auto_generate = st.checkbox("Auto-generate Category ID", value=True, key=f"auto_gen_cat_{st.session_state['category_form_key']}")
            if auto_generate:
                # Generate ID once and store in session state
                if "generated_category_id" not in st.session_state:
                    st.session_state["generated_category_id"] = generate_category_id()
                category_id = st.text_input("Category ID *", value=st.session_state["generated_category_id"], disabled=True, help="Auto-generated unique identifier", key=f"cat_id_{st.session_state['category_form_key']}")
            else:
                category_id = st.text_input("Category ID *", help="Unique identifier for the category", key=f"cat_id_manual_{st.session_state['category_form_key']}")
                if "generated_category_id" in st.session_state:
                    del st.session_state["generated_category_id"]
            
            category_name = st.text_input("Category Name *", key=f"cat_name_{st.session_state['category_form_key']}")
            
            submitted = st.form_submit_button("Add Category", use_container_width=True, type="primary")
            
            if submitted:
                if not category_id or not category_name:
                    st.error("Please fill in all required fields")
                elif not categories_df.empty and "Category ID" in categories_df.columns and category_id in categories_df["Category ID"].values:
                    st.error("Category ID already exists")
                else:
                    with st.spinner("Adding category..."):
                        if append_data(SHEETS["categories"], [category_id, category_name]):
                            # Clear generated category ID and reset form
                            if "generated_category_id" in st.session_state:
                                del st.session_state["generated_category_id"]
                            # Clear search bar
                            if "category_search" in st.session_state:
                                del st.session_state["category_search"]
                            # Set success message
                            st.session_state["category_success_message"] = f"✅ Category '{category_name}' (ID: {category_id}) added successfully!"
                            # Increment form key to reset form
                            st.session_state["category_form_key"] += 1
                            st.rerun()
                        else:
                            st.error("Failed to add category")
    
    with tab2:
        # Green Add Sub Category button styling, white form background, and hide loading indicators
        st.markdown("""
            <style>
            /* White background for Add Sub Category form */
            div[data-testid="stForm"] {
                background-color: white !important;
                padding: 20px !important;
                border-radius: 10px !important;
                border: 1px solid #e0e0e0 !important;
            }
            /* Target the primary button in the subcategory form */
            div[data-testid="stForm"] button[kind="primary"],
            button.stButton > button[kind="primary"] {
                background-color: #28a745 !important;
                color: white !important;
                border-color: #28a745 !important;
            }
            div[data-testid="stForm"] button[kind="primary"]:hover,
            button.stButton > button[kind="primary"]:hover {
                background-color: #218838 !important;
                border-color: #1e7e34 !important;
            }
            /* Hide loading indicators */
            [data-testid="stStatusWidget"] {
                display: none !important;
            }
            .stSpinner {
                display: none !important;
            }
            </style>
        """, unsafe_allow_html=True)
        
        # Show success message if exists
        if "subcategory_success_message" in st.session_state:
            st.success(st.session_state["subcategory_success_message"])
            # Clear message after showing
            del st.session_state["subcategory_success_message"]
        
        # Initialize form key for reset
        if "subcategory_form_key" not in st.session_state:
            st.session_state["subcategory_form_key"] = 0
        
        with st.form(key=f"subcategory_form_{st.session_state['subcategory_form_key']}"):
            if categories_df.empty:
                st.warning("Please add categories first before adding subcategories")
            else:
                # Show category names in dropdown but store category ID
                category_options = categories_df["Category Name"].tolist()
                category_names = ["Select category"] + category_options
                selected_category_name = st.selectbox("Category *", category_names, key=f"subcat_cat_{st.session_state['subcategory_form_key']}")
                
                # Map selected category name back to category ID
                if selected_category_name != "Select category":
                    category_id = categories_df[categories_df["Category Name"] == selected_category_name]["Category ID"].iloc[0]
                    category_name = selected_category_name
                else:
                    category_id = "Select category"
                    category_name = ""
                
                auto_generate = st.checkbox("Auto-generate Sub Category ID", value=True, key=f"auto_gen_subcat_{st.session_state['subcategory_form_key']}")
                if auto_generate:
                    # Generate ID once and store in session state
                    if "generated_subcategory_id" not in st.session_state:
                        st.session_state["generated_subcategory_id"] = generate_subcategory_id()
                    subcategory_id = st.text_input("Sub Category ID *", value=st.session_state["generated_subcategory_id"], disabled=True, help="Auto-generated unique identifier", key=f"subcat_id_{st.session_state['subcategory_form_key']}")
                else:
                    subcategory_id = st.text_input("Sub Category ID *", help="Unique identifier for the subcategory", key=f"subcat_id_manual_{st.session_state['subcategory_form_key']}")
                    if "generated_subcategory_id" in st.session_state:
                        del st.session_state["generated_subcategory_id"]
                
                subcategory_name = st.text_input("Sub Category Name *", key=f"subcat_name_{st.session_state['subcategory_form_key']}")
                
                submitted = st.form_submit_button("Add Sub Category", use_container_width=True, type="primary")
                
                if submitted:
                    if selected_category_name == "Select category" or not subcategory_id or not subcategory_name:
                        st.error("Please fill in all required fields")
                    elif not subcategories_df.empty and "SubCategory ID" in subcategories_df.columns and subcategory_id in subcategories_df["SubCategory ID"].values:
                        st.error("Sub Category ID already exists")
                    else:
                        with st.spinner("Adding sub category..."):
                            # Save: SubCategory ID, Category ID, Category Name, SubCategory Name
                            if append_data(SHEETS["subcategories"], [subcategory_id, category_id, category_name, subcategory_name]):
                                # Clear generated subcategory ID and reset form
                                if "generated_subcategory_id" in st.session_state:
                                    del st.session_state["generated_subcategory_id"]
                                # Clear search bar
                                if "subcategory_search" in st.session_state:
                                    del st.session_state["subcategory_search"]
                                # Set success message
                                st.session_state["subcategory_success_message"] = f"✅ Sub Category '{subcategory_name}' (ID: {subcategory_id}) added successfully!"
                                # Increment form key to reset form
                                st.session_state["subcategory_form_key"] += 1
                                st.rerun()
                            else:
                                st.error("Failed to add sub category")
    
    with tab3:
        # Show success message if exists
        if "category_success_message" in st.session_state:
            st.success(st.session_state["category_success_message"])
            # Clear message after showing
            del st.session_state["category_success_message"]
        
        if not categories_df.empty and "Category ID" in categories_df.columns:
            st.subheader("All Categories")
            
            # Search bar
            search_term = st.text_input("🔍 Search Categories", placeholder="Search by Category ID or Name...", key="category_search")
            
            # Filter data based on search
            if search_term:
                mask = (
                    categories_df["Category ID"].astype(str).str.contains(search_term, case=False, na=False) |
                    categories_df["Category Name"].astype(str).str.contains(search_term, case=False, na=False)
                )
                filtered_df = categories_df[mask]
                if filtered_df.empty:
                    st.info(f"No categories found matching '{search_term}'")
                    filtered_df = pd.DataFrame()
            else:
                filtered_df = categories_df
            
            if not filtered_df.empty:
                # Show count
                st.caption(f"Showing {len(filtered_df)} of {len(categories_df)} category(ies)")
                
                # Check if user is admin
                user_role = st.session_state.get(SESSION_KEYS.get("user_role", "user_role"), "user")
                is_admin = user_role.lower() == "admin"
                
                # Table header - adjust columns based on admin status
                if is_admin:
                    header_col1, header_col2, header_col3, header_col4 = st.columns([3, 4, 1, 1])
                    with header_col1:
                        st.write("**Category ID**")
                    with header_col2:
                        st.write("**Category Name**")
                    with header_col3:
                        st.write("**Edit**")
                    with header_col4:
                        st.write("**Delete**")
                else:
                    header_col1, header_col2, header_col3 = st.columns([3, 4, 1])
                    with header_col1:
                        st.write("**Category ID**")
                    with header_col2:
                        st.write("**Category Name**")
                    with header_col3:
                        st.write("**Edit**")
                st.divider()

                # Display table with edit/delete buttons
                for idx, row in filtered_df.iterrows():
                    # Get original index from df for delete/update operations
                    # Convert to Python int to avoid JSON serialization issues
                    if not categories_df[categories_df["Category ID"] == row.get('Category ID', '')].empty:
                        original_idx = int(categories_df[categories_df["Category ID"] == row.get('Category ID', '')].index[0])
                    else:
                        original_idx = int(idx) if isinstance(idx, (int, type(pd.NA))) else 0

                    if is_admin:
                        col1, col2, col3, col4 = st.columns([3, 4, 1, 1])
                    else:
                        col1, col2, col3 = st.columns([3, 4, 1])

                    with col1:
                        st.write(row.get('Category ID', 'N/A'))
                    with col2:
                        st.write(row.get('Category Name', 'N/A'))
                    with col3:
                        edit_key = f"edit_cat_{row.get('Category ID', idx)}"
                        if st.button("✏️", key=edit_key, use_container_width=True, help="Edit this category"):
                            st.session_state["edit_category_id"] = row.get('Category ID', '')
                            st.session_state["edit_category_idx"] = int(original_idx)  # Ensure it's a Python int
                            st.rerun()
                    # Only show delete button for admin users
                    if is_admin:
                        with col4:
                            delete_key = f"delete_cat_{row.get('Category ID', idx)}"
                            if st.button("🗑️", key=delete_key, use_container_width=True, help="Delete this category"):
                                category_name_to_delete = row.get('Category Name', 'Unknown')
                                category_id_to_delete = row.get('Category ID', 'Unknown')
                                if delete_data(SHEETS["categories"], original_idx):
                                    # Set success message
                                    st.session_state["category_success_message"] = f"✅ Category '{category_name_to_delete}' (ID: {category_id_to_delete}) deleted successfully!"
                                    # Clear search bar
                                    if "category_search" in st.session_state:
                                        del st.session_state["category_search"]
                                    st.rerun()
                                else:
                                    st.error("Failed to delete category")
                    
                    st.divider()
            elif search_term:
                # Search returned no results, but search was performed
                pass
            else:
                st.info("No categories found. Add a new category using the 'Add Category' tab.")

            # Edit form (shown when edit button is clicked)
            if "edit_category_id" in st.session_state and st.session_state["edit_category_id"]:
                st.subheader("Edit Category")
                edit_id = st.session_state["edit_category_id"]
                edit_idx = st.session_state.get("edit_category_idx", 0)
                
                category_rows = categories_df[categories_df["Category ID"] == edit_id]
                if not category_rows.empty:
                    category = category_rows.iloc[0]
                    
                    with st.form("edit_category_form"):
                        new_category_id = st.text_input("Category ID", value=category.get("Category ID", ""), disabled=True)
                        new_category_name = st.text_input("Category Name", value=category.get("Category Name", ""))
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("Update Category", use_container_width=True):
                                with st.spinner("Updating category..."):
                                    if update_data(SHEETS["categories"], edit_idx, [new_category_id, new_category_name]):
                                        # Set success message
                                        st.session_state["category_success_message"] = f"✅ Category '{new_category_name}' (ID: {new_category_id}) updated successfully!"
                                        if "edit_category_id" in st.session_state:
                                            del st.session_state["edit_category_id"]
                                        if "edit_category_idx" in st.session_state:
                                            del st.session_state["edit_category_idx"]
                                        # Clear search bar
                                        if "category_search" in st.session_state:
                                            del st.session_state["category_search"]
                                        st.rerun()
                                    else:
                                        st.error("Failed to update category")
                        with col2:
                            if st.form_submit_button("Cancel", use_container_width=True):
                                if "edit_category_id" in st.session_state:
                                    del st.session_state["edit_category_id"]
                                if "edit_category_idx" in st.session_state:
                                    del st.session_state["edit_category_idx"]
                                st.rerun()
                else:
                    st.warning("Selected category not found in data.")
        else:
            st.info("No categories found. Add a new category using the 'Add Category' tab.")
    
    with tab4:
        # Show success message if exists
        if "subcategory_success_message" in st.session_state:
            st.success(st.session_state["subcategory_success_message"])
            # Clear message after showing
            del st.session_state["subcategory_success_message"]
        
        if not subcategories_df.empty and "SubCategory ID" in subcategories_df.columns:
            st.subheader("All Sub Categories")
            
            # Search bar
            search_term = st.text_input("🔍 Search Sub Categories", placeholder="Search by Sub Category ID, Name, Category ID, or Category Name...", key="subcategory_search")
            
            # Filter data based on search
            if search_term:
                mask = (
                    subcategories_df["SubCategory ID"].astype(str).str.contains(search_term, case=False, na=False) |
                    subcategories_df["SubCategory Name"].astype(str).str.contains(search_term, case=False, na=False) |
                    subcategories_df["Category ID"].astype(str).str.contains(search_term, case=False, na=False)
                )
                # Add Category Name to search if column exists
                if "Category Name" in subcategories_df.columns:
                    mask = mask | subcategories_df["Category Name"].astype(str).str.contains(search_term, case=False, na=False)
                filtered_df = subcategories_df[mask]
                if filtered_df.empty:
                    st.info(f"No subcategories found matching '{search_term}'")
                    filtered_df = pd.DataFrame()
            else:
                filtered_df = subcategories_df
            
            if not filtered_df.empty:
                # Show count
                st.caption(f"Showing {len(filtered_df)} of {len(subcategories_df)} subcategory(ies)")
                
                # Check if user is admin
                user_role = st.session_state.get(SESSION_KEYS.get("user_role", "user_role"), "user")
                is_admin = user_role.lower() == "admin"
                
                # Table header - adjust columns based on admin status
                if is_admin:
                    header_col1, header_col2, header_col3, header_col4, header_col5, header_col6 = st.columns([2, 2, 3, 3, 1, 1])
                    with header_col1:
                        st.write("**Sub Category ID**")
                    with header_col2:
                        st.write("**Category ID**")
                    with header_col3:
                        st.write("**Category Name**")
                    with header_col4:
                        st.write("**Sub Category Name**")
                    with header_col5:
                        st.write("**Edit**")
                    with header_col6:
                        st.write("**Delete**")
                else:
                    header_col1, header_col2, header_col3, header_col4, header_col5 = st.columns([2, 2, 3, 3, 1])
                    with header_col1:
                        st.write("**Sub Category ID**")
                    with header_col2:
                        st.write("**Category ID**")
                    with header_col3:
                        st.write("**Category Name**")
                    with header_col4:
                        st.write("**Sub Category Name**")
                    with header_col5:
                        st.write("**Edit**")
                st.divider()

                # Display table with edit/delete buttons
                for idx, row in filtered_df.iterrows():
                    # Get original index from df for delete/update operations
                    # Convert to Python int to avoid JSON serialization issues
                    if not subcategories_df[subcategories_df["SubCategory ID"] == row.get('SubCategory ID', '')].empty:
                        original_idx = int(subcategories_df[subcategories_df["SubCategory ID"] == row.get('SubCategory ID', '')].index[0])
                    else:
                        original_idx = int(idx) if isinstance(idx, (int, type(pd.NA))) else 0

                    if is_admin:
                        col1, col2, col3, col4, col5, col6 = st.columns([2, 2, 3, 3, 1, 1])
                    else:
                        col1, col2, col3, col4, col5 = st.columns([2, 2, 3, 3, 1])

                    with col1:
                        st.write(row.get('SubCategory ID', 'N/A'))
                    with col2:
                        st.write(row.get('Category ID', 'N/A'))
                    with col3:
                        st.write(row.get('Category Name', 'N/A'))
                    with col4:
                        st.write(row.get('SubCategory Name', 'N/A'))
                    with col5:
                        edit_key = f"edit_subcat_{row.get('SubCategory ID', idx)}"
                        if st.button("✏️", key=edit_key, use_container_width=True, help="Edit this subcategory"):
                            st.session_state["edit_subcategory_id"] = row.get('SubCategory ID', '')
                            st.session_state["edit_subcategory_idx"] = int(original_idx)  # Ensure it's a Python int
                            st.rerun()
                    # Only show delete button for admin users
                    if is_admin:
                        with col6:
                            delete_key = f"delete_subcat_{row.get('SubCategory ID', idx)}"
                            if st.button("🗑️", key=delete_key, use_container_width=True, help="Delete this subcategory"):
                                subcategory_name_to_delete = row.get('SubCategory Name', 'Unknown')
                                subcategory_id_to_delete = row.get('SubCategory ID', 'Unknown')
                                if delete_data(SHEETS["subcategories"], original_idx):
                                    # Set success message
                                    st.session_state["subcategory_success_message"] = f"✅ Sub Category '{subcategory_name_to_delete}' (ID: {subcategory_id_to_delete}) deleted successfully!"
                                    # Clear search bar
                                    if "subcategory_search" in st.session_state:
                                        del st.session_state["subcategory_search"]
                                    st.rerun()
                                else:
                                    st.error("Failed to delete subcategory")
                    
                    st.divider()
            elif search_term:
                # Search returned no results, but search was performed
                pass
            else:
                st.info("No subcategories found. Add a new subcategory using the 'Add Sub Category' tab.")

            # Edit form (shown when edit button is clicked)
            if "edit_subcategory_id" in st.session_state and st.session_state["edit_subcategory_id"]:
                st.subheader("Edit Sub Category")
                edit_id = st.session_state["edit_subcategory_id"]
                edit_idx = st.session_state.get("edit_subcategory_idx", 0)
                
                subcategory_rows = subcategories_df[subcategories_df["SubCategory ID"] == edit_id]
                if not subcategory_rows.empty:
                    subcategory = subcategory_rows.iloc[0]
                    
                    with st.form("edit_subcategory_form"):
                        new_subcategory_id = st.text_input("Sub Category ID", value=subcategory.get("SubCategory ID", ""), disabled=True)
                        
                        # Category dropdown for editing - show category names
                        selected_category_name = None
                        if not categories_df.empty:
                            category_options = categories_df["Category Name"].tolist()
                            current_category_id = subcategory.get("Category ID", "")
                            # Find the category name for the current category ID
                            if not categories_df[categories_df["Category ID"] == current_category_id].empty:
                                current_category_name = categories_df[categories_df["Category ID"] == current_category_id]["Category Name"].iloc[0]
                                if current_category_name in category_options:
                                    default_index = category_options.index(current_category_name) + 1
                                else:
                                    default_index = 0
                            else:
                                default_index = 0
                            selected_category_name = st.selectbox("Category *", ["Select category"] + category_options, index=default_index)
                            
                            # Map selected category name back to category ID
                            if selected_category_name != "Select category":
                                new_category_id = categories_df[categories_df["Category Name"] == selected_category_name]["Category ID"].iloc[0]
                                new_category_name = selected_category_name
                            else:
                                new_category_id = "Select category"
                                new_category_name = ""
                        else:
                            new_category_id = st.text_input("Category ID *", value=subcategory.get("Category ID", ""))
                            new_category_name = st.text_input("Category Name *", value=subcategory.get("Category Name", ""))
                            selected_category_name = None
                        
                        new_subcategory_name = st.text_input("Sub Category Name", value=subcategory.get("SubCategory Name", ""))
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("Update Sub Category", use_container_width=True):
                                if selected_category_name == "Select category" or (selected_category_name is None and new_category_id == "Select category"):
                                    st.error("Please select a category")
                                else:
                                    with st.spinner("Updating subcategory..."):
                                        # Update: SubCategory ID, Category ID, Category Name, SubCategory Name
                                        if update_data(SHEETS["subcategories"], edit_idx, [new_subcategory_id, new_category_id, new_category_name, new_subcategory_name]):
                                            # Set success message
                                            st.session_state["subcategory_success_message"] = f"✅ Sub Category '{new_subcategory_name}' (ID: {new_subcategory_id}) updated successfully!"
                                            if "edit_subcategory_id" in st.session_state:
                                                del st.session_state["edit_subcategory_id"]
                                            if "edit_subcategory_idx" in st.session_state:
                                                del st.session_state["edit_subcategory_idx"]
                                            # Clear search bar
                                            if "subcategory_search" in st.session_state:
                                                del st.session_state["subcategory_search"]
                                            st.rerun()
                                        else:
                                            st.error("Failed to update subcategory")
                        with col2:
                            if st.form_submit_button("Cancel", use_container_width=True):
                                if "edit_subcategory_id" in st.session_state:
                                    del st.session_state["edit_subcategory_id"]
                                if "edit_subcategory_idx" in st.session_state:
                                    del st.session_state["edit_subcategory_idx"]
                                st.rerun()
                else:
                    st.warning("Selected subcategory not found in data.")
        else:
            st.info("No subcategories found. Add a new subcategory using the 'Add Sub Category' tab.")

def generate_asset_id() -> str:
    """Generate a unique Asset ID/Barcode"""
    import uuid
    # Generate a short unique ID
    return f"AST-{uuid.uuid4().hex[:8].upper()}"

def asset_master_form():
    """Asset Master Form"""
    st.header("📦 Asset Master Management")
    
    assets_df = read_data(SHEETS["assets"])
    locations_df = read_data(SHEETS["locations"])
    suppliers_df = read_data(SHEETS["suppliers"])
    categories_df = read_data(SHEETS["categories"])
    subcategories_df = read_data(SHEETS["subcategories"])
    
    tab1, tab2 = st.tabs(["Add New Asset", "View/Edit Assets"])
    
    with tab1:
        with st.form("asset_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                auto_generate = st.checkbox("Auto-generate Asset ID", value=True)
                if auto_generate:
                    # Generate ID once and store in session state
                    if "generated_asset_id" not in st.session_state:
                        st.session_state["generated_asset_id"] = generate_asset_id()
                    asset_id = st.text_input("Asset ID / Barcode", value=st.session_state["generated_asset_id"], disabled=True)
                else:
                    asset_id = st.text_input("Asset ID / Barcode *")
                    if "generated_asset_id" in st.session_state:
                        del st.session_state["generated_asset_id"]
                
                asset_name = st.text_input("Asset Name *")
                
                if not categories_df.empty:
                    category_options = categories_df["Category Name"].tolist()
                    category = st.selectbox("Category *", ["Select category"] + category_options, key="asset_category_select")
                else:
                    category = st.text_input("Category *")
                    st.warning("No categories found. Please add categories first.")
                
                # Sub Category dropdown - show based on selected category
                if category != "Select category" and not categories_df.empty and not subcategories_df.empty:
                    # Get category ID from selected category name
                    category_row = categories_df[categories_df["Category Name"] == category]
                    if not category_row.empty:
                        category_id = category_row["Category ID"].iloc[0]
                        
                        # Filter subcategories by Category ID
                        if "Category ID" in subcategories_df.columns:
                            matching_subcats = subcategories_df[subcategories_df["Category ID"] == category_id]
                        # Also try matching by Category Name if Category ID doesn't work
                        elif "Category Name" in subcategories_df.columns:
                            matching_subcats = subcategories_df[subcategories_df["Category Name"] == category]
                        else:
                            matching_subcats = pd.DataFrame()
                        
                        if not matching_subcats.empty and "SubCategory Name" in matching_subcats.columns:
                            subcat_options = matching_subcats["SubCategory Name"].tolist()
                            if subcat_options:
                                subcategory = st.selectbox("Sub Category", ["None"] + subcat_options, key="asset_subcategory_select")
                            else:
                                subcategory = st.selectbox("Sub Category", ["None"], key="asset_subcategory_select", help="No subcategories available for this category")
                        else:
                            subcategory = st.selectbox("Sub Category", ["None"], key="asset_subcategory_select", help="No subcategories found for this category")
                    else:
                        subcategory = st.text_input("Sub Category", key="asset_subcategory_text")
                else:
                    # Show text input if no category selected or no subcategories available
                    if category == "Select category":
                        subcategory = st.text_input("Sub Category", key="asset_subcategory_text", disabled=True, help="Please select a category first")
                    else:
                        subcategory = st.text_input("Sub Category", key="asset_subcategory_text")
                
                model_serial = st.text_input("Model / Serial No")
                purchase_date = st.date_input("Purchase Date")
            
            with col2:
                purchase_cost = st.number_input("Purchase Cost", min_value=0.0, value=0.0, step=0.01)
                
                if not suppliers_df.empty:
                    supplier_options = suppliers_df["Supplier Name"].tolist()
                    supplier = st.selectbox("Supplier", ["None"] + supplier_options)
                else:
                    supplier = st.text_input("Supplier")
                
                if not locations_df.empty:
                    location_options = locations_df["Location Name"].tolist()
                    location = st.selectbox("Location", ["None"] + location_options)
                else:
                    location = st.text_input("Location")
                
                assigned_to = st.text_input("Assigned To")
                condition = st.selectbox("Condition", ["Excellent", "Good", "Fair", "Poor", "Damaged"])
                status = st.selectbox("Status", ["Active", "Inactive", "Maintenance", "Retired"])
                remarks = st.text_area("Remarks")
                attachment = st.text_input("Attachment URL")
            
            submitted = st.form_submit_button("Add Asset", use_container_width=True)
            
            if submitted:
                if not asset_id or not asset_name:
                    st.error("Please fill in Asset ID and Asset Name")
                elif not assets_df.empty and asset_id in assets_df["Asset ID"].values:
                    st.error("Asset ID already exists")
                else:
                    data = [
                        asset_id, asset_name, category if category != "Select category" else "",
                        subcategory if subcategory != "None" else "", model_serial,
                        purchase_date.strftime("%Y-%m-%d") if purchase_date else "",
                        purchase_cost, supplier if supplier != "None" else "",
                        location if location != "None" else "", assigned_to,
                        condition, status, remarks, attachment
                    ]
                    if append_data(SHEETS["assets"], data):
                        st.success("Asset added successfully!")
                        # Clear generated asset ID
                        if "generated_asset_id" in st.session_state:
                            del st.session_state["generated_asset_id"]
                        st.rerun()
                    else:
                        st.error("Failed to add asset")
    
    with tab2:
        if not assets_df.empty:
            # Search functionality
            search_term = st.text_input("Search Assets (by ID, Name, or Barcode)")
            if search_term:
                filtered_df = assets_df[
                    assets_df["Asset ID"].str.contains(search_term, case=False, na=False) |
                    assets_df["Asset Name"].str.contains(search_term, case=False, na=False)
                ]
                st.dataframe(filtered_df, use_container_width=True)
            else:
                st.dataframe(assets_df, use_container_width=True)
            
            # Edit/Delete functionality
            st.subheader("Edit/Delete Asset")
            asset_ids = ["Select an asset"] + assets_df["Asset ID"].tolist()
            selected_id = st.selectbox("Select Asset", asset_ids)
            
            if selected_id != "Select an asset":
                asset = assets_df[assets_df["Asset ID"] == selected_id].iloc[0]
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Edit", use_container_width=True):
                        st.session_state["edit_asset"] = selected_id
                
                with col2:
                    if st.button("Delete", use_container_width=True):
                        row_index = assets_df[assets_df["Asset ID"] == selected_id].index[0]
                        if delete_data(SHEETS["assets"], row_index):
                            st.success("Asset deleted successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to delete asset")
        else:
            st.info("No assets found. Add a new asset using the 'Add New Asset' tab.")

def asset_transfer_form():
    """Asset Transfer Form"""
    st.header("🚚 Asset Transfer Management")
    
    transfers_df = read_data(SHEETS["transfers"])
    assets_df = read_data(SHEETS["assets"])
    locations_df = read_data(SHEETS["locations"])
    
    tab1, tab2 = st.tabs(["New Transfer", "View Transfers"])
    
    with tab1:
        with st.form("transfer_form"):
            # Generate Transfer ID
            import uuid
            transfer_id = st.text_input("Transfer ID", value=f"TRF-{uuid.uuid4().hex[:8].upper()}", disabled=True)
            
            if not assets_df.empty:
                asset_options = assets_df["Asset ID"].tolist()
                asset_id = st.selectbox("Asset ID *", ["Select asset"] + asset_options)
            else:
                asset_id = st.text_input("Asset ID *")
                st.warning("No assets found. Please add assets first.")
            
            if not locations_df.empty:
                location_options = locations_df["Location Name"].tolist()
                col1, col2 = st.columns(2)
                with col1:
                    from_location = st.selectbox("From Location *", ["Select location"] + location_options)
                with col2:
                    to_location = st.selectbox("To Location *", ["Select location"] + location_options)
            else:
                col1, col2 = st.columns(2)
                with col1:
                    from_location = st.text_input("From Location *")
                with col2:
                    to_location = st.text_input("To Location *")
            
            transfer_date = st.date_input("Transfer Date *", value=datetime.now().date())
            approved_by = st.text_input("Approved By *")
            
            submitted = st.form_submit_button("Create Transfer", use_container_width=True)
            
            if submitted:
                if asset_id == "Select asset" or not asset_id:
                    st.error("Please select an asset")
                elif from_location == "Select location" or to_location == "Select location":
                    st.error("Please select both locations")
                elif from_location == to_location:
                    st.error("From and To locations cannot be the same")
                elif not approved_by:
                    st.error("Please enter approver name")
                else:
                    data = [
                        transfer_id, asset_id, from_location, to_location,
                        transfer_date.strftime("%Y-%m-%d"), approved_by
                    ]
                    if append_data(SHEETS["transfers"], data):
                        # Update asset location
                        if not assets_df.empty:
                            asset_row = assets_df[assets_df["Asset ID"] == asset_id]
                            if not asset_row.empty:
                                row_index = asset_row.index[0]
                                asset_data = asset_row.iloc[0].tolist()
                                asset_data[8] = to_location  # Update location field
                                update_data(SHEETS["assets"], row_index, asset_data)
                        
                        st.success("Transfer created successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to create transfer")
    
    with tab2:
        if not transfers_df.empty:
            st.dataframe(transfers_df, use_container_width=True)
        else:
            st.info("No transfers found. Create a new transfer using the 'New Transfer' tab.")


def user_management_form():
    """User Management Form"""
    st.header("👥 User Management")

    # Only admins can manage users
    user_role = st.session_state.get(SESSION_KEYS.get("user_role", "user_role"), "user")
    if str(user_role).lower() != "admin":
        st.warning("Only administrators can view or modify users.")
        return

    users_df = read_data(SHEETS["users"])

    tab1, tab2 = st.tabs(["Add User", "View/Edit Users"])

    with tab1:
        if "user_success_message" in st.session_state:
            st.success(st.session_state["user_success_message"])
            del st.session_state["user_success_message"]

        with st.form("add_user_form"):
            username = st.text_input("Username *")
            password = st.text_input("Password *", type="password")
            confirm_password = st.text_input("Confirm Password *", type="password")
            email = st.text_input("Email *")
            role = st.selectbox("Role *", ["admin", "user"], index=1)

            submitted = st.form_submit_button("Add User", use_container_width=True)

            if submitted:
                if not username or not password or not confirm_password or not email:
                    st.error("Please fill in all required fields")
                elif password != confirm_password:
                    st.error("Passwords do not match")
                elif not users_df.empty and "Username" in users_df.columns and username in users_df["Username"].astype(str).values:
                    st.error("Username already exists")
                else:
                    hashed_password = hash_password(password)
                    success = append_data(SHEETS["users"], [username, hashed_password, email, role])
                    if success:
                        st.session_state["user_success_message"] = f"✅ User '{username}' added successfully!"
                        st.rerun()
                    else:
                        st.error("Failed to add user")

    with tab2:
        if "user_success_message" in st.session_state:
            st.success(st.session_state["user_success_message"])
            del st.session_state["user_success_message"]

        if users_df.empty:
            st.info("No users found. Add a new user using the 'Add User' tab.")
            return

        st.subheader("Existing Users")

        search_term = st.text_input(
            "🔍 Search Users",
            placeholder="Search by Username, Email, or Role...",
            key="user_search",
        )

        if search_term:
            mask = (
                users_df["Username"].astype(str).str.contains(search_term, case=False, na=False)
                | users_df["Email"].astype(str).str.contains(search_term, case=False, na=False)
                | users_df["Role"].astype(str).str.contains(search_term, case=False, na=False)
            )
            filtered_df = users_df[mask]
            if filtered_df.empty:
                st.info(f"No users found matching '{search_term}'")
                return
        else:
            filtered_df = users_df

        st.caption(f"Showing {len(filtered_df)} of {len(users_df)} user(s)")

        st.divider()

        for idx, row in filtered_df.iterrows():
            original_idx = int(users_df[users_df["Username"] == row.get("Username")].index[0])

            is_editing = st.session_state.get("edit_user", "") == row.get("Username")

            if is_editing:
                email = st.text_input(
                    "Email",
                    value=row.get("Email", ""),
                    key=f"user_email_{row.get('Username')}"
                )
                role = st.selectbox(
                    "Role",
                    ["admin", "user"],
                    index=0 if str(row.get("Role", "user")).lower() == "admin" else 1,
                    key=f"user_role_{row.get('Username')}"
                )
                new_password = st.text_input(
                    "New Password (leave blank to keep current)",
                    type="password",
                    key=f"user_new_password_{row.get('Username')}"
                )
                confirm_password = st.text_input(
                    "Confirm New Password",
                    type="password",
                    key=f"user_confirm_password_{row.get('Username')}"
                )

                col_save, col_cancel = st.columns(2)
                with col_save:
                    if st.button("Save", key=f"user_save_{row.get('Username')}"):
                        if new_password and new_password != confirm_password:
                            st.error("Passwords do not match")
                        else:
                            hashed = row.get("Password", "")
                            if new_password:
                                hashed = hash_password(new_password)
                            updated_data = [
                                row.get("Username"),
                                hashed,
                                email,
                                role,
                            ]
                            if update_data(SHEETS["users"], original_idx, updated_data):
                                st.session_state["user_success_message"] = f"✅ User '{row.get('Username')}' updated successfully!"
                                st.session_state.pop("edit_user", None)
                                st.rerun()
                            else:
                                st.error("Failed to update user")
                with col_cancel:
                    if st.button("Cancel", key=f"user_cancel_{row.get('Username')}"):
                        st.session_state.pop("edit_user", None)
                        st.rerun()
                st.divider()
            else:
                col_username, col_email, col_role, col_edit, col_delete = st.columns([2, 3, 2, 1, 1])
                with col_username:
                    st.write(row.get("Username", "-"))
                with col_email:
                    st.write(row.get("Email", "-"))
                with col_role:
                    st.write(row.get("Role", "-"))
                with col_edit:
                    if st.button("Edit", key=f"user_edit_{row.get('Username')}"):
                        st.session_state["edit_user"] = row.get("Username")
                        st.rerun()
                with col_delete:
                    if st.button("Delete", key=f"user_delete_{row.get('Username')}"):
                        if delete_data(SHEETS["users"], original_idx):
                            st.session_state["user_success_message"] = f"🗑️ User '{row.get('Username')}' deleted."
                            st.rerun()
                        else:
                            st.error("Failed to delete user")
                st.divider()

