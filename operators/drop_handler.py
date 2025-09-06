import bpy
import os
from bpy.props import StringProperty, CollectionProperty
from bpy.types import Operator
from ..serialization.nodegroup_unpacker import unpack_node_files


class NodeDropHandler(Operator):
    bl_idname = "node.drop_handler"
    bl_label = "Node Drop Handler"
    bl_description = "Handle dropped .node files and import node groups"
    bl_options = {'REGISTER'}
    
    directory: StringProperty(
        subtype='DIR_PATH', 
        options={'SKIP_SAVE', 'HIDDEN'}
    )
    files: CollectionProperty(
        type=bpy.types.OperatorFileListElement, 
        options={'SKIP_SAVE', 'HIDDEN'}
    )
    
    mouse_x: bpy.props.IntProperty(default=0)
    mouse_y: bpy.props.IntProperty(default=0)
    
    def invoke(self, context, event):
        self.mouse_x = event.mouse_region_x if hasattr(event, 'mouse_region_x') else 0
        self.mouse_y = event.mouse_region_y if hasattr(event, 'mouse_region_y') else 0
        
        print(f"Mouse position captured: ({self.mouse_x}, {self.mouse_y})")
        
        return self.execute(context)
    
    def execute(self, context):
        print("=" * 60)
        print("NODE FILE DROP DETECTED!")
        print("=" * 60)
        
        if not self.directory:
            print("No directory specified")
            self.report({'ERROR'}, "No directory specified")
            return {'CANCELLED'}
        
        print(f"Drop directory: {self.directory}")
        
        node_file_paths = []
        other_files = []
        
        for file_elem in self.files:
            filepath = os.path.join(self.directory, file_elem.name)
            print(f"Dropped file: {file_elem.name}")
            
            if file_elem.name.lower().endswith('.node'):
                if os.path.exists(filepath):
                    node_file_paths.append(filepath)
                    print(f"   Valid .node file: {file_elem.name}")
                else:
                    print(f"   File does not exist: {file_elem.name}")
            else:
                other_files.append(file_elem.name)
                print(f"   Not a .node file: {file_elem.name}")
        
        print("-" * 40)
        print(f"   Summary:")
        print(f"   Total files dropped: {len(self.files)}")
        print(f"   Valid .node files: {len(node_file_paths)}")
        print(f"   Other files: {len(other_files)}")
        
        if not node_file_paths:
            message = "No valid .node files found in drop"
            print(f"{message}")
            self.report({'WARNING'}, message)
            return {'CANCELLED'}
        
        print("-" * 40)
        print("Processing .node files...")
        
        try:
            from ..serialization.nodegroup_unpacker import NodeGroupUnpacker
            unpacker = NodeGroupUnpacker()
            unpacker.set_mouse_coordinates(self.mouse_x, self.mouse_y)
            
            success_count, error_count, error_messages = unpacker.process_multiple_files(node_file_paths)
            
            if success_count > 0:
                message = f"Successfully imported node groups from {success_count} file(s)"
                print(f"{message}")
                self.report({'INFO'}, message)
                if error_count > 0:
                    self.report({'WARNING'}, f"{error_count} file(s) failed to process")
                print("=" * 60)
                return {'FINISHED'}
            else:
                message = "No files were successfully processed"
                print(f"{message}")
                if error_messages:
                    print("Errors:")
                    for err in error_messages:
                        print(f"  • {err}")
                self.report({'ERROR'}, message)
                print("=" * 60)
                return {'CANCELLED'}
                
        except Exception as e:
            error_msg = f"Error processing .node files: {str(e)}"
            print(f"{error_msg}")
            import traceback
            traceback.print_exc()
            self.report({'ERROR'}, error_msg)
            print("=" * 60)
            return {'CANCELLED'}


class NODE_FH_drop_handler(bpy.types.FileHandler):
    bl_idname = "NODE_FH_drop_handler"
    bl_label = "Node Drop Handler"
    bl_import_operator = "node.drop_handler"
    bl_file_extensions = ".node"

    @classmethod
    def poll_drop(cls, context):
        print(f"Drop poll check - Area: {context.area.type if context.area else 'None'}")
        return True


def register():
    bpy.utils.register_class(NodeDropHandler)
    bpy.utils.register_class(NODE_FH_drop_handler)
    print("Node drop handler registered")

def unregister():
    bpy.utils.unregister_class(NODE_FH_drop_handler)
    bpy.utils.unregister_class(NodeDropHandler)
    print("Node drop handler unregistered")
