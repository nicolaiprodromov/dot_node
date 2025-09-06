import bpy
import os
import json
import tempfile
import zipfile
from bpy.props import StringProperty, CollectionProperty
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper
from mathutils import Vector, Color, Euler

class ImportNodeGroup(Operator, ImportHelper):
    bl_idname = "node.import_nodegroup"
    bl_label = "Import Node Group"
    bl_description = "Import a .node file into Blender"
    bl_options = {'REGISTER', 'UNDO'}
    
    filename_ext = ".node"
    filter_glob: StringProperty(
        default="*.node",
        options={'HIDDEN'},
        maxlen=255,
    )
    
    directory: StringProperty(
        subtype='DIR_PATH', 
        options={'SKIP_SAVE', 'HIDDEN'}
    )
    files: CollectionProperty(
        type=bpy.types.OperatorFileListElement, 
        options={'SKIP_SAVE', 'HIDDEN'}
    )
    
    @classmethod
    def poll(cls, context):
        return True
    
    def execute(self, context):
        try:
            if self.directory and self.files:
                return self._import_multiple_files(context)
            elif self.filepath:
                return self._import_single_file(context, self.filepath)
            else:
                self.report({'ERROR'}, "No files specified for import")
                return {'CANCELLED'}
                
        except Exception as e:
            self.report({'ERROR'}, f"Import failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}
    
    def invoke(self, context, event):
        if self.filepath or (self.directory and self.files):
            return self.execute(context)
        else:
            context.window_manager.fileselect_add(self)
            return {'RUNNING_MODAL'}
    
    def _import_multiple_files(self, context):
        if not self.directory:
            self.report({'ERROR'}, "No directory specified")
            return {'CANCELLED'}
        
        imported_count = 0
        failed_count = 0
        
        for file_elem in self.files:
            if file_elem.name.lower().endswith('.node'):
                filepath = os.path.join(self.directory, file_elem.name)
                try:
                    success = self._import_node_file(context, filepath)
                    if success:
                        imported_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    print(f"Failed to import {filepath}: {e}")
                    failed_count += 1
        
        if imported_count > 0:
            self.report({'INFO'}, f"Successfully imported {imported_count} node group(s)")
            if failed_count > 0:
                self.report({'WARNING'}, f"{failed_count} file(s) failed to import")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "No files were successfully imported")
            return {'CANCELLED'}
    
    def _import_single_file(self, context, filepath):
        if not filepath.lower().endswith('.node'):
            self.report({'ERROR'}, "File must have .node extension")
            return {'CANCELLED'}
        
        success = self._import_node_file(context, filepath)
        if success:
            filename = os.path.basename(filepath)
            self.report({'INFO'}, f"Successfully imported {filename}")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "Failed to import node group")
            return {'CANCELLED'}
    
    def _import_node_file(self, context, filepath):
        try:
            temp_dir = tempfile.mkdtemp(prefix="nodegroup_import_")
            
            try:
                with zipfile.ZipFile(filepath, 'r') as zip_file:
                    zip_file.extractall(temp_dir)
                
                json_files = [f for f in os.listdir(temp_dir) if f.endswith('.json')]
                if not json_files:
                    print("No JSON metadata file found in .node package")
                    return False
                
                json_path = os.path.join(temp_dir, json_files[0])
                
                with open(json_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                return self._reconstruct_node_group(context, metadata, temp_dir)
                
            finally:
                import shutil
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    print(f"Warning: Failed to clean up temp directory: {e}")
                    
        except Exception as e:
            print(f"Error importing node file {filepath}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _reconstruct_node_group(self, context, metadata, temp_dir):
        """Reconstruct node group from metadata"""
        try:
            nodegroup_info = metadata.get('nodegroup_info', {})
            original_name = nodegroup_info.get('name', 'Imported NodeGroup')
            package_name = nodegroup_info.get('package_name', original_name)
            
            node_group_name = self._get_unique_name(original_name)
            
            node_group = bpy.data.node_groups.new(name=node_group_name, type='GeometryNodeTree')
            
            print(f"Created node group: {node_group_name}")
            
            node_group.nodes.clear()
            
            self._reconstruct_interface(node_group, metadata.get('interface', {}))
            
            node_map = self._reconstruct_nodes(node_group, metadata.get('nodes', []))
            
            self._reconstruct_links(node_group, metadata.get('links', []), node_map)
            
            if (context.space_data and 
                hasattr(context.space_data, 'type') and 
                context.space_data.type == 'NODE_EDITOR'):
                
                if (hasattr(context.space_data, 'tree_type') and 
                    context.space_data.tree_type == 'GeometryNodeTree' and 
                    context.space_data.node_tree):
                    
                    group_node = context.space_data.node_tree.nodes.new('GeometryNodeGroup')
                    group_node.node_tree = node_group
                    group_node.label = node_group_name
                    
                    if hasattr(context, 'region') and context.region:
                        # Try to position at mouse cursor
                        group_node.location = (0, 0)
                    
                    for node in context.space_data.node_tree.nodes:
                        node.select = False
                    group_node.select = True
                    context.space_data.node_tree.nodes.active = group_node
            
            print(f"Successfully reconstructed node group: {node_group_name}")
            return True
            
        except Exception as e:
            print(f"Error reconstructing node group: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _get_unique_name(self, base_name):
        if base_name not in bpy.data.node_groups:
            return base_name
        
        counter = 1
        while f"{base_name}.{counter:03d}" in bpy.data.node_groups:
            counter += 1
        
        return f"{base_name}.{counter:03d}"
    
    def _reconstruct_interface(self, node_group, interface_data):
        try:
            node_group.interface.clear()
            
            for input_data in interface_data.get('inputs', []):
                socket_type = input_data.get('socket_type', 'NodeSocketGeometry')
                socket = node_group.interface.new_socket(
                    name=input_data.get('name', 'Input'),
                    in_out='INPUT',
                    socket_type=socket_type
                )
                
                default_value = input_data.get('default_value')
                if default_value is not None and hasattr(socket, 'default_value'):
                    try:
                        socket.default_value = default_value
                    except Exception as e:
                        print(f"Could not set default value for input {socket.name}: {e}")
            
            for output_data in interface_data.get('outputs', []):
                socket_type = output_data.get('socket_type', 'NodeSocketGeometry')
                socket = node_group.interface.new_socket(
                    name=output_data.get('name', 'Output'),
                    in_out='OUTPUT',
                    socket_type=socket_type
                )
        
        except Exception as e:
            print(f"Error reconstructing interface: {e}")
    
    def _reconstruct_nodes(self, node_group, nodes_data):
        node_map = {}
        
        for node_data in nodes_data:
            try:
                node_type = node_data.get('bl_idname', node_data.get('type', 'GeometryNodeGroup'))
                node = node_group.nodes.new(type=node_type)
                
                node.name = node_data.get('name', node.name)
                node.label = node_data.get('label', '')
                node.location = Vector(node_data.get('location', [0, 0]))
                node.width = node_data.get('width', node.width)
                node.height = node_data.get('height', node.height)
                node.hide = node_data.get('hide', False)
                node.mute = node_data.get('mute', False)
                
                properties = node_data.get('properties', {})
                for prop_name, prop_value in properties.items():
                    if hasattr(node, prop_name):
                        try:
                            setattr(node, prop_name, prop_value)
                        except Exception as e:
                            print(f"Could not set property {prop_name} on node {node.name}: {e}")
                
                inputs_data = node_data.get('inputs', [])
                for i, input_data in enumerate(inputs_data):
                    if i < len(node.inputs):
                        socket = node.inputs[i]
                        default_value = input_data.get('default_value')
                        if default_value is not None and hasattr(socket, 'default_value'):
                            try:
                                socket.default_value = default_value
                            except Exception as e:
                                print(f"Could not set default value for socket {socket.name}: {e}")
                
                node_map[node_data.get('name')] = node
                
            except Exception as e:
                print(f"Error creating node {node_data.get('name', 'Unknown')}: {e}")
        
        return node_map
    
    def _reconstruct_links(self, node_group, links_data, node_map):
        for link_data in links_data:
            try:
                from_node_name = link_data.get('from_node')
                to_node_name = link_data.get('to_node')
                from_socket_id = link_data.get('from_socket')
                to_socket_id = link_data.get('to_socket')
                
                from_node = node_map.get(from_node_name)
                to_node = node_map.get(to_node_name)
                
                if not from_node or not to_node:
                    print(f"Could not find nodes for link: {from_node_name} -> {to_node_name}")
                    continue
                
                from_socket = None
                for socket in from_node.outputs:
                    if socket.identifier == from_socket_id:
                        from_socket = socket
                        break
                
                to_socket = None
                for socket in to_node.inputs:
                    if socket.identifier == to_socket_id:
                        to_socket = socket
                        break
                
                if from_socket and to_socket:
                    node_group.links.new(from_socket, to_socket)
                else:
                    print(f"Could not find sockets for link: {from_socket_id} -> {to_socket_id}")
                    
            except Exception as e:
                print(f"Error creating link: {e}")


class NODE_FH_import_nodegroup(bpy.types.FileHandler):
    """File handler for .node files drag-and-drop"""
    bl_idname = "NODE_FH_import_nodegroup"
    bl_label = "Node Group Import Handler"
    bl_import_operator = "node.import_nodegroup"
    bl_file_extensions = ".node"

    @classmethod
    def poll_drop(cls, context):
        return True
        
        


def register():
    bpy.utils.register_class(ImportNodeGroup)
    bpy.utils.register_class(NODE_FH_import_nodegroup)

def unregister():
    bpy.utils.unregister_class(NODE_FH_import_nodegroup)
    bpy.utils.unregister_class(ImportNodeGroup)


def import_menu_func(self, context):
    self.layout.operator(ImportNodeGroup.bl_idname, text="Node Group (.node)")

def node_add_menu_func(self, context):
    if (context.space_data.type == 'NODE_EDITOR' and 
        context.space_data.tree_type == 'GeometryNodeTree'):
        self.layout.separator()
        self.layout.operator(ImportNodeGroup.bl_idname, text="Import Node Group (.node)", icon='IMPORT')

def register_menu():
    bpy.types.TOPBAR_MT_file_import.append(import_menu_func)
    if hasattr(bpy.types, 'NODE_MT_add'):
        bpy.types.NODE_MT_add.append(node_add_menu_func)

def unregister_menu():
    bpy.types.TOPBAR_MT_file_import.remove(import_menu_func)
    if hasattr(bpy.types, 'NODE_MT_add'):
        bpy.types.NODE_MT_add.remove(node_add_menu_func)
