"""
Forms module for Asset Tracker
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from google_sheets import read_data, append_data, update_data, delete_data, find_row
from config import SHEETS, SESSION_KEYS

def generate_location_id() -> str:
    """Generate a unique Location ID"""
    import uuid
    # Generate a short unique ID
    return f"LOC-{uuid.uuid4().hex[:8].upper()}"

def location_form():
    """Location Form"""
    st.header("📍 Location Management")
    
    df = read_data(SHEETS["locations"])
    
    tab1, tab2 = st.tabs(["Add New Location", "View/Edit Locations"])
    
    with tab1:
        # Green Add Location button styling, white form background, and hide loading indicators
        st.markdown("""
            <style>
            /* White background for Add Location form */
            div[data-testid="stForm"] {
                background-color: white !important;
                padding: 20px !important;
                border-radius: 10px !important;
                border: 1px solid #e0e0e0 !important;
            }
            /* Target the primary button in the location form */
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
                    original_idx = df[df["Location ID"] == row.get('Location ID', '')].index[0] if not df[df["Location ID"] == row.get('Location ID', '')].empty else idx

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
                            st.session_state["edit_location_idx"] = original_idx
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
    """Supplier Form"""
    st.header("🏢 Supplier Management")
    
    df = read_data(SHEETS["suppliers"])
    
    tab1, tab2 = st.tabs(["Add New Supplier", "View/Edit Suppliers"])
    
    with tab1:
        with st.form("supplier_form"):
            supplier_id = st.text_input("Supplier ID *", help="Unique identifier for the supplier")
            supplier_name = st.text_input("Supplier Name *")
            
            submitted = st.form_submit_button("Add Supplier", use_container_width=True)
            
            if submitted:
                if not supplier_id or not supplier_name:
                    st.error("Please fill in all required fields")
                elif not df.empty and supplier_id in df["Supplier ID"].values:
                    st.error("Supplier ID already exists")
                else:
                    if append_data(SHEETS["suppliers"], [supplier_id, supplier_name]):
                        st.success("Supplier added successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to add supplier")
    
    with tab2:
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            
            # Edit/Delete functionality
            st.subheader("Edit/Delete Supplier")
            supplier_ids = ["Select a supplier"] + df["Supplier ID"].tolist()
            selected_id = st.selectbox("Select Supplier", supplier_ids)
            
            if selected_id != "Select a supplier":
                supplier = df[df["Supplier ID"] == selected_id].iloc[0]
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Edit", use_container_width=True):
                        st.session_state["edit_supplier"] = selected_id
                
                with col2:
                    if st.button("Delete", use_container_width=True):
                        row_index = df[df["Supplier ID"] == selected_id].index[0]
                        if delete_data(SHEETS["suppliers"], row_index):
                            st.success("Supplier deleted successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to delete supplier")
                
                if st.session_state.get("edit_supplier") == selected_id:
                    with st.form("edit_supplier_form"):
                        new_supplier_id = st.text_input("Supplier ID", value=supplier["Supplier ID"])
                        new_supplier_name = st.text_input("Supplier Name", value=supplier["Supplier Name"])
                        
                        if st.form_submit_button("Update Supplier"):
                            row_index = df[df["Supplier ID"] == selected_id].index[0]
                            if update_data(SHEETS["suppliers"], row_index, [new_supplier_id, new_supplier_name]):
                                st.success("Supplier updated successfully!")
                                st.session_state["edit_supplier"] = None
                                st.rerun()
                            else:
                                st.error("Failed to update supplier")
        else:
            st.info("No suppliers found. Add a new supplier using the 'Add New Supplier' tab.")

def category_form():
    """Asset Category and Sub Category Form"""
    st.header("📂 Category Management")
    
    categories_df = read_data(SHEETS["categories"])
    subcategories_df = read_data(SHEETS["subcategories"])
    
    tab1, tab2, tab3 = st.tabs(["Add Category", "Add Sub Category", "View All"])
    
    with tab1:
        with st.form("category_form"):
            category_id = st.text_input("Category ID *", help="Unique identifier for the category")
            category_name = st.text_input("Category Name *")
            
            submitted = st.form_submit_button("Add Category", use_container_width=True)
            
            if submitted:
                if not category_id or not category_name:
                    st.error("Please fill in all required fields")
                elif not categories_df.empty and category_id in categories_df["Category ID"].values:
                    st.error("Category ID already exists")
                else:
                    if append_data(SHEETS["categories"], [category_id, category_name]):
                        st.success("Category added successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to add category")
    
    with tab2:
        with st.form("subcategory_form"):
            if categories_df.empty:
                st.warning("Please add categories first before adding subcategories")
            else:
                category_options = categories_df["Category ID"].tolist()
                category_id = st.selectbox("Category *", ["Select category"] + category_options)
                subcategory_id = st.text_input("Sub Category ID *", help="Unique identifier for the subcategory")
                subcategory_name = st.text_input("Sub Category Name *")
                
                submitted = st.form_submit_button("Add Sub Category", use_container_width=True)
                
                if submitted:
                    if category_id == "Select category" or not subcategory_id or not subcategory_name:
                        st.error("Please fill in all required fields")
                    elif not subcategories_df.empty and subcategory_id in subcategories_df["SubCategory ID"].values:
                        st.error("Sub Category ID already exists")
                    else:
                        if append_data(SHEETS["subcategories"], [subcategory_id, category_id, subcategory_name]):
                            st.success("Sub Category added successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to add sub category")
    
    with tab3:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Categories")
            if not categories_df.empty:
                st.dataframe(categories_df, use_container_width=True)
            else:
                st.info("No categories found")
        
        with col2:
            st.subheader("Sub Categories")
            if not subcategories_df.empty:
                st.dataframe(subcategories_df, use_container_width=True)
            else:
                st.info("No subcategories found")

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
                    category = st.selectbox("Category *", ["Select category"] + category_options)
                else:
                    category = st.text_input("Category *")
                    st.warning("No categories found. Please add categories first.")
                
                if category != "Select category" and not subcategories_df.empty:
                    category_id = categories_df[categories_df["Category Name"] == category]["Category ID"].iloc[0] if category in categories_df["Category Name"].values else None
                    if category_id:
                        subcat_options = subcategories_df[subcategories_df["Category ID"] == category_id]["SubCategory Name"].tolist()
                        subcategory = st.selectbox("Sub Category", ["None"] + subcat_options)
                    else:
                        subcategory = st.text_input("Sub Category")
                else:
                    subcategory = st.text_input("Sub Category")
                
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

