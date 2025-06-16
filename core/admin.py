"""
Admin interface for user management and role assignment.
Only accessible to users with Admin role.
"""
import streamlit as st
from core.firebase_auth import FirebaseAuthManager, UserRole

def display_admin_interface(auth_manager: FirebaseAuthManager) -> None:
    """Display the admin interface for user and role management.
    
    Args:
        auth_manager: Authenticated Firebase manager instance
    """
    st.title("Admin Dashboard")
    
    # Verify admin access
    if not auth_manager.is_authenticated():
        st.error("You need to log in first")
        return
        
    user_role = auth_manager.get_user_role()
    if user_role != UserRole.ADMIN.value:
        st.error("Access denied. Admin privileges required.")
        return
        
    # Display admin information
    st.info(f"Logged in as: {st.session_state.user_info.get('email')} (Admin)")
    
    # User management section
    st.header("User Management")
    
    # Get all users
    result = auth_manager.get_all_users()
    if not result.get("success", False):
        st.error(f"Error fetching users: {result.get('error')}")
        return
        
    users = result.get("users", [])
    if not users:
        st.warning("No users found in the system.")
        return
        
    # Create columns for user display and actions
    st.subheader("User List")
    
    # Create a dictionary of users for easy access
    user_dict = {user.get("email"): user for user in users}
    
    # Create a table with users
    for user in users:
        uid = user.get("uid")
        email = user.get("email")
        role = user.get("role")
        
        # Use consistent column layout but conditionally show delete button
        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
        with col1:
            st.write(f"**{email}**")
        with col2:
            st.write(f"Role: {role}")
        with col3:
            st.write(f"UID: {uid[:8]}...")
        
        # Only show delete button for non-admin users
        with col4:
            if role != UserRole.ADMIN.value:
                if st.button("❌ Delete", key=f"delete_{uid}"):
                    st.session_state[f"confirm_delete_{uid}"] = True
        
        # Confirmation dialog
        if st.session_state.get(f"confirm_delete_{uid}", False):
            st.warning(f"Are you sure you want to delete user {email}? This cannot be undone.")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Yes, delete", key=f"confirm_yes_{uid}"):
                    # Delete the user
                    result = auth_manager.delete_user(uid)
                    if result.get("success", False):
                        st.success(result.get("message"))
                        st.session_state.pop(f"confirm_delete_{uid}", None)
                        st.rerun()  # Refresh to update the user list
                    else:
                        st.error(f"Error deleting user: {result.get('error')}")
            with col2:
                if st.button("No, cancel", key=f"confirm_no_{uid}"):
                    st.session_state.pop(f"confirm_delete_{uid}", None)
                    st.rerun()
        
        st.divider()
    
    # Create tabs for different admin functions
    admin_tabs = st.tabs(["Register New User", "Update User Role"])
    
    # Tab 1: New user registration section
    with admin_tabs[0]:
        st.subheader("Register New User")
        
        new_email = st.text_input("Email")
        new_password = st.text_input("Password", type="password")
        new_user_role = st.selectbox("Role", [role.value for role in UserRole])
        
        if st.button("Register User", key="register_user_btn"):
            if not new_email or not new_password:
                st.error("Email and password are required")
            else:
                register_result = auth_manager.register_user(
                    new_email,
                    new_password,
                    UserRole(new_user_role)
                )
                
                if register_result.get("success", False):
                    st.success(f"User registered successfully: {new_email}")
                    st.rerun()  # Refresh the page to see the new user
                else:
                    st.error(f"Error registering user: {register_result.get('error')}")
    
    # Tab 2: Role management section
    with admin_tabs[1]:
        st.subheader("Update User Role")
        
        # User selection - filter out admin users
        non_admin_users = [user for user in users if user.get("role") != UserRole.ADMIN.value]
        user_options = ["Select a user"] + [user.get("email") for user in non_admin_users]
        selected_user_email = st.selectbox("Select User", user_options)
        
        if selected_user_email != "Select a user":
            # Find the selected user
            selected_user = next((user for user in users if user.get("email") == selected_user_email), None)
            if not selected_user:
                st.error("Selected user not found")
            else:
                # Role selection
                current_role = selected_user.get("role")
                st.info(f"Current role: {current_role}")
                
                new_role = st.selectbox(
                    "Select New Role", 
                    [role.value for role in UserRole],
                    index=[role.value for role in UserRole].index(current_role) if current_role in [role.value for role in UserRole] else 0
                )
                
                # Update role button
                if st.button("Update Role", key="update_role_btn"):
                    if new_role == current_role:
                        st.warning("Selected role is the same as current role")
                    else:
                        update_result = auth_manager.update_user_role(
                            selected_user.get("uid"), 
                            UserRole(new_role)
                        )
                        
                        if update_result.get("success", False):
                            st.success(update_result.get("message"))
                            st.rerun()  # Refresh the page to see updated roles
                        else:
                            st.error(f"Error updating role: {update_result.get('error')}")
        else:
            st.info("Please select a user to update their role")
