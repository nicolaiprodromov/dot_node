import bpy
from .operators import register_association, export_nodegroup, import_nodegroup, drop_handler

def register():
    register_association.register()
    export_nodegroup.register()
    export_nodegroup.register_menu()
    drop_handler.register()
    
    # Actually run the file association registration
    print("[XWZ] Running file association registration...")

    try:
        success = register_association.perform_file_association()
        if success:
            print("File association registration completed successfully!")
        else:
            print("File association registration failed!")
    except Exception as e:
        print(f"Error during file association registration: {e}")

def unregister():
    drop_handler.unregister()
    export_nodegroup.unregister_menu()
    export_nodegroup.unregister()
    register_association.unregister()
    print("[XWZ] Node File Link addon unregistered.")