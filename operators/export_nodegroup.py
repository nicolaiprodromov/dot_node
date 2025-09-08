import bpy
import os
import tempfile
import shutil
import subprocess
from bpy.props import StringProperty, BoolProperty
from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper, ImportHelper
from ..serialization.nodegroup_serializer import NodeGroupSerializer

class SelectPreviewImage(Operator, ImportHelper):
    """Operator to select preview image for export"""
    bl_idname = "node.select_preview_image"
    bl_label = "Select Preview Image"
    bl_description = "Select a preview image for the node group export"
    bl_options = {'REGISTER', 'INTERNAL'}
    
    filename_ext = ".png"
    filter_glob: StringProperty(
        default="*.png",
        options={'HIDDEN'},
        maxlen=255,
    )
    
    # Store the calling export operator
    export_operator: StringProperty(options={'HIDDEN'})
    
    def execute(self, context):
        # Validate the selected image
        if not self.filepath:
            self.report({'ERROR'}, "No image file selected")
            return {'CANCELLED'}
        
        is_valid, message = self._validate_preview_image(self.filepath)
        if not is_valid:
            self.report({'ERROR'}, f"Invalid preview image: {message}")
            return {'CANCELLED'}
        
        # Store the preview path in the scene for the export operator to use
        context.scene.node_export_preview_path = self.filepath
        
        # Now call the main export operator
        bpy.ops.node.export_nodegroup_with_preview('INVOKE_DEFAULT')
        
        return {'FINISHED'}
    
    def _validate_preview_image(self, image_path):
        """Validate the preview image meets requirements"""
        if not image_path or not os.path.exists(image_path):
            return False, "Preview image file not found"
        
        # Check file extension
        if not image_path.lower().endswith('.png'):
            return False, "Preview image must be a .png file"
        
        # Check filename
        filename = os.path.basename(image_path)
        if filename.lower() != 'preview.png':
            return False, "Preview image must be named 'preview.png'"
        
        # Check file size (max 250KB = 256000 bytes)
        file_size = os.path.getsize(image_path)
        max_size = 250 * 1024  # 250KB in bytes
        if file_size > max_size:
            size_kb = file_size / 1024
            return False, f"Preview image is too large ({size_kb:.1f}KB). Maximum allowed is 250KB"
        
        return True, "Preview image is valid"

class ExportNodeGroupWithPreview(Operator, ExportHelper):
    """Main export operator that handles the actual export with optional preview"""
    bl_idname = "node.export_nodegroup_with_preview"
    bl_label = "Export Node Group"
    bl_description = "Export the selected node group as a .node package"
    bl_options = {'REGISTER'}
    
    filename_ext = ".node"
    
    filter_glob: StringProperty(
        default="*.node",
        options={'HIDDEN'},
        maxlen=255,
    )
    
    def invoke(self, context, event):
        node_group_to_export = self._get_node_group_to_export(context)
        if node_group_to_export:
            default_name = node_group_to_export.name.replace(" ", "_")
            self.filepath = default_name + ".node"
        
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
    def execute(self, context):
        try:
            # Check if we have a preview image path from the previous step
            preview_path = getattr(context.scene, 'node_export_preview_path', None)
            
            # Validate preview image if provided
            if preview_path:
                is_valid, message = self._validate_preview_image(preview_path)
                if not is_valid:
                    self.report({'ERROR'}, f"Preview image validation failed: {message}")
                    return {'CANCELLED'}
                self.report({'INFO'}, f"Preview image validated: {message}")
            
            node_tree = self._get_node_group_to_export(context)
            if not node_tree:
                self.report({'ERROR'}, "No node group selected")
                return {'CANCELLED'}
            
            output_path = self.filepath
            
            if not output_path or output_path.strip() == "" or output_path == "untitled":
                default_name = node_tree.name.replace(" ", "_")
                self.filepath = default_name + ".node"
                context.window_manager.fileselect_add(self)
                return {'RUNNING_MODAL'}
            
            if not output_path or output_path.strip() == "":
                self.report({'ERROR'}, "No output file path specified")
                return {'CANCELLED'}
            
            if output_path.endswith('.node'):
                output_path = output_path[:-5]
            
            if not output_path or os.path.basename(output_path).strip() == "":
                default_name = node_tree.name.replace(" ", "_")
                output_path = os.path.join(os.path.dirname(output_path) if output_path else os.getcwd(), default_name)
                print(f"Using fallback output path: {output_path}")
            
            final_output_path = output_path
            if not final_output_path.strip():
                self.report({'ERROR'}, "Invalid output file path")
                return {'CANCELLED'}
            
            package_name = os.path.basename(final_output_path)
            if not package_name:
                package_name = node_tree.name.replace(" ", "_")
            
            temp_dir = tempfile.mkdtemp(prefix="nodegroup_export_")
            print(f"Created temp directory: {temp_dir}")
            
            try:
                serializer = NodeGroupSerializer()
                
                self.report({'INFO'}, f"Serializing node group '{node_tree.name}' as '{package_name}'...")
                print(f"Serializing node group data for: {node_tree.name} with package name: {package_name}")
                success = serializer.serialize_nodegroup(node_tree, temp_dir, package_name)
                
                if not success:
                    self.report({'ERROR'}, "Failed to serialize node group")
                    return {'CANCELLED'}
                
                # Copy preview image if specified and validated
                if preview_path:
                    preview_dest = os.path.join(temp_dir, "preview.png")
                    try:
                        shutil.copy2(preview_path, preview_dest)
                        self.report({'INFO'}, "Preview image added to package")
                        print(f"Preview image copied to: {preview_dest}")
                        # Clear the scene property after use
                        try:
                            if hasattr(context.scene, 'node_export_preview_path'):
                                delattr(context.scene, 'node_export_preview_path')
                        except (AttributeError, KeyError):
                            pass  # Property already deleted or doesn't exist
                    except Exception as e:
                        self.report({'WARNING'}, f"Failed to copy preview image: {str(e)}")
                        print(f"Warning: Failed to copy preview image: {e}")
                
                print(f"Serialization completed. Temp dir contents: {os.listdir(temp_dir)}")
                
                addon_dir = os.path.dirname(os.path.dirname(__file__))
                package_script = os.path.join(addon_dir, "serialization", "package.bat")
                
                if not os.path.exists(package_script):
                    self.report({'ERROR'}, f"Package script not found: {package_script}")
                    return {'CANCELLED'}
                
                self.report({'INFO'}, "Packaging node group...")
                
                original_cwd = os.getcwd()
                os.chdir(temp_dir)
                
                try:
                    files_to_package = []
                    for item in os.listdir(temp_dir):
                        if os.path.isfile(item) or os.path.isdir(item):
                            files_to_package.append(item)
                    
                    if not files_to_package:
                        self.report({'ERROR'}, "No files to package")
                        return {'CANCELLED'}
                    
                    output_name = package_name  # Use the package name consistently
                    print(f"Output path: {final_output_path}")
                    print(f"Output name: {output_name}")
                    print(f"Files to package: {files_to_package}")
                    
                    if not output_name:
                        output_name = node_tree.name.replace(" ", "_")
                        print(f"Using node tree name as output: {output_name}")
                    
                    cmd = [package_script, output_name] + files_to_package
                    
                    formatted_args = [f'"{arg}"' if ' ' in arg else arg for arg in cmd]
                    print(f"Full command being executed: {' '.join(formatted_args)}")
                    
                    result = subprocess.run(cmd, capture_output=True, text=True, shell=False, cwd=temp_dir)
                    
                    print(f"Package command: {' '.join(cmd)}")
                    print(f"Return code: {result.returncode}")
                    print(f"STDOUT: {result.stdout}")
                    print(f"STDERR: {result.stderr}")
                    
                    if result.returncode == 0:
                        temp_node_file = os.path.join(temp_dir, f"{output_name}.node")
                        final_node_file = f"{final_output_path}.node"
                        
                        print(f"Looking for temp file: {temp_node_file}")
                        print(f"Target final file: {final_node_file}")
                        print(f"Output path variable: '{final_output_path}'")
                        print(f"Output name variable: '{output_name}'")
                        
                        if not os.path.exists(temp_node_file):
                            temp_files = [f for f in os.listdir(temp_dir) if f.endswith('.node')]
                            print(f"Available .node files in temp dir: {temp_files}")
                            
                            if temp_files:
                                temp_node_file = os.path.join(temp_dir, temp_files[0])
                                print(f"Using found file: {temp_node_file}")
                            else:
                                self.report({'ERROR'}, "No .node package file was created by the packaging script")
                                return {'CANCELLED'}
                        
                        if os.path.exists(temp_node_file):
                            target_dir = os.path.dirname(final_node_file)
                            if target_dir:  # Only create directory if there's a path
                                os.makedirs(target_dir, exist_ok=True)
                            
                            print(f"Moving from: {temp_node_file}")
                            print(f"Moving to: {final_node_file}")
                            
                            shutil.move(temp_node_file, final_node_file)
                            
                            self.report({'INFO'}, f"Successfully exported node group to: {final_node_file}")
                            return {'FINISHED'}
                        else:
                            self.report({'ERROR'}, "Package file was not created")
                            return {'CANCELLED'}
                    else:
                        self.report({'ERROR'}, f"Packaging failed: {result.stderr}")
                        return {'CANCELLED'}
                        
                finally:
                    os.chdir(original_cwd)
                    
            finally:
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    print(f"Warning: Failed to clean up temp directory: {e}")
                    
        except Exception as e:
            self.report({'ERROR'}, f"Export failed: {str(e)}")
            return {'CANCELLED'}
    
    def _get_node_group_to_export(self, context):
        if hasattr(context, 'active_node') and context.active_node:
            if hasattr(context.active_node, 'node_tree') and context.active_node.node_tree:
                return context.active_node.node_tree
        
        current_tree = context.space_data.node_tree
        if current_tree and hasattr(current_tree, 'bl_rna') and current_tree.bl_rna.identifier == 'GeometryNodeTree':
            if current_tree.name in bpy.data.node_groups:
                return current_tree
            elif current_tree.name != "Geometry Nodes":
                return current_tree
        
        return current_tree
    
    def _validate_preview_image(self, image_path):
        """Validate the preview image meets requirements"""
        if not image_path or not os.path.exists(image_path):
            return False, "Preview image file not found"
        
        # Check file extension
        if not image_path.lower().endswith('.png'):
            return False, "Preview image must be a .png file"
        
        # Check filename
        filename = os.path.basename(image_path)
        if filename.lower() != 'preview.png':
            return False, "Preview image must be named 'preview.png'"
        
        # Check file size (max 250KB = 256000 bytes)
        file_size = os.path.getsize(image_path)
        max_size = 250 * 1024  # 250KB in bytes
        if file_size > max_size:
            size_kb = file_size / 1024
            return False, f"Preview image is too large ({size_kb:.1f}KB). Maximum allowed is 250KB"
        
        return True, "Preview image is valid"
    
    @classmethod
    def poll(cls, context):
        if context.space_data.type != 'NODE_EDITOR':
            return False
        if context.space_data.tree_type != 'GeometryNodeTree':
            return False
        if not context.space_data.node_tree:
            return False
        if hasattr(context, 'active_node') and context.active_node:
            if hasattr(context.active_node, 'node_tree') and context.active_node.node_tree:
                return True
        return True


class ExportNodeGroup(Operator):
    """Initial operator that presents export options"""
    bl_idname = "node.export_nodegroup"
    bl_label = "Export Node Group"
    bl_description = "Export the selected node group as a .node package"
    bl_options = {'REGISTER'}
    
    include_preview: BoolProperty(
        name="Include Preview",
        description="Include a preview image in the .node package",
        default=False
    )
    
    @classmethod
    def poll(cls, context):
        if context.space_data.type != 'NODE_EDITOR':
            return False
        if context.space_data.tree_type != 'GeometryNodeTree':
            return False
        if not context.space_data.node_tree:
            return False
        if hasattr(context, 'active_node') and context.active_node:
            if hasattr(context.active_node, 'node_tree') and context.active_node.node_tree:
                return True
        return True
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        
        layout.label(text="Export Options:", icon='EXPORT')
        layout.separator()
        
        col = layout.column()
        col.prop(self, "include_preview")
        
        if self.include_preview:
            box = col.box()
            box.label(text="Preview Image Requirements:", icon='INFO')
            box.label(text="• Must be named 'preview.png'")
            box.label(text="• Must be PNG format")
            box.label(text="• Maximum 250KB file size")
    
    def execute(self, context):
        if self.include_preview:
            # Clear any existing preview path
            try:
                if hasattr(context.scene, 'node_export_preview_path'):
                    delattr(context.scene, 'node_export_preview_path')
            except (AttributeError, KeyError):
                pass  # Property already deleted or doesn't exist
            # Start with preview image selection
            bpy.ops.node.select_preview_image('INVOKE_DEFAULT')
        else:
            # Go directly to export
            bpy.ops.node.export_nodegroup_with_preview('INVOKE_DEFAULT')
        
        return {'FINISHED'}


def register():
    # Add scene properties for communication between operators
    bpy.types.Scene.node_export_preview_path = StringProperty(
        name="Preview Path",
        description="Temporary storage for preview image path",
        options={'HIDDEN'}
    )
    
    bpy.utils.register_class(SelectPreviewImage)
    bpy.utils.register_class(ExportNodeGroupWithPreview)
    bpy.utils.register_class(ExportNodeGroup)

def unregister():
    bpy.utils.unregister_class(ExportNodeGroup)
    bpy.utils.unregister_class(ExportNodeGroupWithPreview)
    bpy.utils.unregister_class(SelectPreviewImage)
    
    # Remove scene properties
    if hasattr(bpy.types.Scene, 'node_export_preview_path'):
        del bpy.types.Scene.node_export_preview_path

def node_context_menu(self, context):
    if (context.space_data.type == 'NODE_EDITOR' and 
        context.space_data.tree_type == 'GeometryNodeTree' and
        context.space_data.node_tree):
        
        layout = self.layout
        layout.separator()
        op = layout.operator("node.export_nodegroup", text="Export Node Group", icon='EXPORT')

def node_editor_menu(self, context):
    if (hasattr(context.space_data, 'type') and 
        context.space_data.type == 'NODE_EDITOR' and 
        hasattr(context.space_data, 'tree_type') and
        context.space_data.tree_type == 'GeometryNodeTree' and
        context.space_data.node_tree):
        
        layout = self.layout
        layout.separator()
        layout.operator("node.export_nodegroup", text="Export Node Group", icon='EXPORT')

def register_menu():
    bpy.types.NODE_MT_context_menu.append(node_context_menu)
    if hasattr(bpy.types, 'NODE_MT_editor_menus'):
        bpy.types.NODE_MT_editor_menus.append(node_editor_menu)

def unregister_menu():
    bpy.types.NODE_MT_context_menu.remove(node_context_menu)
    if hasattr(bpy.types, 'NODE_MT_editor_menus'):
        bpy.types.NODE_MT_editor_menus.remove(node_editor_menu)
