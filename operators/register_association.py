import bpy
from bpy.props import StringProperty
from bpy.types import Operator

from ..registry import FileAssociationManager

def perform_file_association():
    manager = FileAssociationManager()
    return manager.perform_file_association()

class RegisterNodeFileAssociation(Operator):
    bl_idname = "wm.register_node_file_association"
    bl_label = "Register .node File Association"
    
    def check_existing_association(self, file_extension):
        manager = FileAssociationManager()
        return manager.check_existing_association()
    
    def validate_icon_path(self, icon_path):
        manager = FileAssociationManager()
        return manager.validate_icon_path()
    
    def execute(self, context):
        success = perform_file_association()
        if success:
            self.report({'INFO'}, "Successfully registered .node file association")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "Failed to register file association")
            return {'CANCELLED'}

def register_file_association():
    bpy.utils.register_class(RegisterNodeFileAssociation)

def register():
    register_file_association()

def unregister():
    bpy.utils.unregister_class(RegisterNodeFileAssociation)

# Add menu item
def menu_func(self, context):
    self.layout.operator("wm.register_node_file_association")
