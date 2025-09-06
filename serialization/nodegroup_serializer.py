import bpy
import os
import json
from mathutils import Vector, Euler, Color

class NodeGroupSerializer:
    def __init__(self):
        self.node_group = None
        self.output_dir = None
        self.package_name = None
        
    def serialize_nodegroup(self, node_tree, output_directory, package_name=None):
        try:
            self.node_group = node_tree
            self.output_dir = output_directory
            
            self.package_name = package_name if package_name else node_tree.name

            print(f"Serializing node group data for: {node_tree.name} as package: {self.package_name}")

            if node_tree.bl_rna.identifier != 'GeometryNodeTree':
                print(f"Error: Not a geometry node tree. Type: {node_tree.bl_rna.identifier}")
                return False
            
            json_success = self._create_metadata_json()
            if not json_success:
                return False
            
            blend_success = self._create_blend_file()
            if not blend_success:
                return False
                
            return True
            
        except Exception as e:
            print(f"Error during serialization: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _create_metadata_json(self):
        try:
            metadata = {
                'nodegroup_info': {
                    'name': self.node_group.name,
                    'package_name': self.package_name,
                    'description': getattr(self.node_group, 'description', ''),
                    'type': self.node_group.bl_rna.identifier,
                    'version': '1.0.0',
                    'blender_version': bpy.app.version_string,
                    'export_timestamp': self._get_timestamp()
                },
                'interface': self._serialize_interface(),
                'nodes': self._serialize_nodes(),
                'links': self._serialize_links(),
                'layout': self._serialize_layout(),
                'dependencies': self._get_dependencies()
            }
            
            # Write JSON file
            json_filename = f"{self.package_name}.json"
            json_path = os.path.join(self.output_dir, json_filename)
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
                
            return True
            
        except Exception as e:
            print(f"Error creating metadata JSON: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _serialize_interface(self):
        interface = {
            'inputs': [],
            'outputs': []
        }
        
        try:
            # Blender 4.5+ uses the interface.items_tree API
            if hasattr(self.node_group, 'interface') and hasattr(self.node_group.interface, 'items_tree'):
                for item in self.node_group.interface.items_tree:
                    if hasattr(item, 'item_type') and item.item_type == 'SOCKET':
                        socket_data = {
                            'name': item.name,
                            'identifier': getattr(item, 'identifier', item.name),
                            'socket_type': item.socket_type,
                            'in_out': item.in_out,
                            'description': getattr(item, 'description', ''),
                            'default_value': self._serialize_socket_default_value(item)
                        }
                        
                        if hasattr(item, 'min_value'):
                            socket_data['min_value'] = item.min_value
                        if hasattr(item, 'max_value'):
                            socket_data['max_value'] = item.max_value
                        if hasattr(item, 'subtype'):
                            socket_data['subtype'] = item.subtype
                        if hasattr(item, 'attribute_domain'):
                            socket_data['attribute_domain'] = item.attribute_domain
                        
                        if item.in_out == 'INPUT':
                            interface['inputs'].append(socket_data)
                        else:
                            interface['outputs'].append(socket_data)
            

            elif hasattr(self.node_group, 'inputs') and hasattr(self.node_group, 'outputs'):
                for input_socket in self.node_group.inputs:
                    socket_data = {
                        'name': input_socket.name,
                        'identifier': getattr(input_socket, 'identifier', input_socket.name),
                        'socket_type': input_socket.bl_idname,
                        'in_out': 'INPUT',
                        'description': getattr(input_socket, 'description', ''),
                        'default_value': self._serialize_socket_default_value(input_socket)
                    }
                    interface['inputs'].append(socket_data)
                
                for output_socket in self.node_group.outputs:
                    socket_data = {
                        'name': output_socket.name,
                        'identifier': getattr(output_socket, 'identifier', output_socket.name),
                        'socket_type': output_socket.bl_idname,
                        'in_out': 'OUTPUT',
                        'description': getattr(output_socket, 'description', ''),
                        'default_value': self._serialize_socket_default_value(output_socket)
                    }
                    interface['outputs'].append(socket_data)
        
        except Exception as e:
            print(f"Error serializing interface: {e}")
            pass
        
        return interface
    
    def _serialize_nodes(self):
        nodes = []
        
        for node in self.node_group.nodes:
            node_data = {
                'name': node.name,
                'label': node.label,
                'type': node.type,
                'bl_idname': node.bl_idname,
                'location': [node.location.x, node.location.y],
                'width': node.width,
                'height': node.height,
                'hide': node.hide,
                'mute': node.mute,
                'select': node.select,
                'inputs': self._serialize_node_sockets(node.inputs),
                'outputs': self._serialize_node_sockets(node.outputs),
                'properties': self._serialize_node_properties(node)
            }
            
            # Add node-specific data
            if hasattr(node, 'node_tree') and node.node_tree:
                node_data['node_tree'] = node.node_tree.name
                
            nodes.append(node_data)
            
        return nodes
    
    def _serialize_node_sockets(self, sockets):
        socket_data = []
        
        for socket in sockets:
            data = {
                'name': socket.name,
                'identifier': socket.identifier,
                'type': socket.type,
                'bl_idname': socket.bl_idname,
                'enabled': socket.enabled,
                'hide': socket.hide,
                'hide_value': socket.hide_value,
                'default_value': self._serialize_socket_default_value(socket)
            }
            socket_data.append(data)
            
        return socket_data
    
    def _serialize_socket_default_value(self, socket):
        try:
            if not hasattr(socket, 'default_value'):
                return None
                
            value = socket.default_value
            
            if value is None:
                return None
            elif isinstance(value, (int, float, bool, str)):
                return value
            elif hasattr(value, '__iter__') and not isinstance(value, str):
                try:
                    return list(value)
                except (TypeError, ValueError):
                    return str(value)
            elif hasattr(value, 'name'):
                return value.name
            else:
                return str(value)
                
        except Exception as e:
            print(f"Error serializing socket value: {e}")
            return None
    
    def _serialize_node_properties(self, node):
        properties = {}
        
        if hasattr(node, 'keys'):
            for key in node.keys():
                if not key.startswith('_'):
                    properties[key] = node[key]
        
        if hasattr(node, 'operation'):
            properties['operation'] = node.operation
        if hasattr(node, 'blend_type'):
            properties['blend_type'] = node.blend_type
        if hasattr(node, 'distribution'):
            properties['distribution'] = node.distribution
        if hasattr(node, 'mode'):
            properties['mode'] = node.mode
        if hasattr(node, 'data_type'):
            properties['data_type'] = node.data_type
        if hasattr(node, 'domain'):
            properties['domain'] = node.domain
            
        return properties
    
    def _serialize_links(self):
        links = []
        
        for link in self.node_group.links:
            link_data = {
                'from_node': link.from_node.name,
                'from_socket': link.from_socket.identifier,
                'to_node': link.to_node.name,
                'to_socket': link.to_socket.identifier,
                'is_valid': link.is_valid,
                'is_muted': link.is_muted
            }
            links.append(link_data)
            
        return links
    
    def _serialize_layout(self):
        layout = {
            'frames': [],
            'reroutes': []
        }
        
        for node in self.node_group.nodes:
            if node.type == 'FRAME':
                frame_data = {
                    'name': node.name,
                    'label': node.label,
                    'location': [node.location.x, node.location.y],
                    'width': node.width,
                    'height': node.height,
                    'shrink': node.shrink,
                    'text': getattr(node, 'text', '')
                }
                layout['frames'].append(frame_data)
                
            elif node.type == 'REROUTE':
                reroute_data = {
                    'name': node.name,
                    'location': [node.location.x, node.location.y]
                }
                layout['reroutes'].append(reroute_data)
        
        return layout
    
    def _get_dependencies(self):
        dependencies = {
            'node_groups': [],
            'materials': [],
            'objects': [],
            'images': [],
            'texts': []
        }
        
        for node in self.node_group.nodes:
            if hasattr(node, 'node_tree') and node.node_tree:
                if node.node_tree != self.node_group:
                    dependencies['node_groups'].append(node.node_tree.name)
        
        for key in dependencies:
            dependencies[key] = list(set(dependencies[key]))
            
        return dependencies
    
    def _get_timestamp(self):
        import datetime
        return datetime.datetime.now().isoformat()
    
    def _create_blend_file(self):
        try:
            import tempfile
            import shutil
            
            blend_filename = f"{self.package_name}.blend"
            blend_path = os.path.join(self.output_dir, blend_filename)
            
            print(f"Creating .blend file: {blend_path}")
            
            try:
                original_use_fake_user = self.node_group.use_fake_user
                self.node_group.use_fake_user = True
                
                with tempfile.NamedTemporaryFile(suffix='.blend', delete=False) as temp_file:
                    temp_blend_path = temp_file.name
                
                bpy.data.libraries.write(
                    temp_blend_path,
                    datablocks={self.node_group},
                    fake_user=True,
                    compress=True
                )
                
                shutil.copy2(temp_blend_path, blend_path)
                os.unlink(temp_blend_path)
                
                self.node_group.use_fake_user = original_use_fake_user
                
                print(f"Successfully created .blend file using libraries.write: {blend_path}")
                return True
                
            except Exception as lib_error:
                print(f"libraries.write failed: {lib_error}")
                
                return self._create_blend_file_fallback(blend_path)
                
        except Exception as e:
            print(f"Error creating .blend file: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    def _create_blend_file_fallback(self, blend_path):
        try:
            print("Using fallback method to create .blend file")
            
            current_file = bpy.data.filepath
            current_is_saved = not bpy.data.is_dirty
            
            node_group_data = {
                'name': self.node_group.name,
                'nodes': [],
                'links': [],
                'inputs': [],
                'outputs': []
            }
            
            for node in self.node_group.nodes:
                node_data = {
                    'name': node.name,
                    'type': node.bl_idname,
                    'location': list(node.location),
                    'width': node.width,
                    'height': node.height,
                    'inputs': {},
                    'properties': {}
                }
                
                for i, input_socket in enumerate(node.inputs):
                    if hasattr(input_socket, 'default_value') and not input_socket.is_linked:
                        try:
                            if hasattr(input_socket.default_value, '__iter__') and not isinstance(input_socket.default_value, str):
                                node_data['inputs'][i] = list(input_socket.default_value)
                            else:
                                node_data['inputs'][i] = input_socket.default_value
                        except:
                            pass
                
                node_group_data['nodes'].append(node_data)
            
            for link in self.node_group.links:
                link_data = {
                    'from_node': link.from_node.name,
                    'from_socket': link.from_socket.identifier,
                    'to_node': link.to_node.name,
                    'to_socket': link.to_socket.identifier
                }
                node_group_data['links'].append(link_data)
            
            for input_socket in self.node_group.inputs:
                socket_data = {
                    'name': input_socket.name,
                    'type': input_socket.bl_idname,
                    'default_value': getattr(input_socket, 'default_value', None)
                }
                node_group_data['inputs'].append(socket_data)
                
            for output_socket in self.node_group.outputs:
                socket_data = {
                    'name': output_socket.name,
                    'type': output_socket.bl_idname
                }
                node_group_data['outputs'].append(socket_data)
            
            bpy.ops.wm.read_homefile(use_empty=True)
            
            new_group = bpy.data.node_groups.new(
                name=self.package_name, 
                type='GeometryNodeTree'
            )
            
            for input_data in node_group_data['inputs']:
                new_input = new_group.inputs.new(input_data['type'], input_data['name'])
                if input_data['default_value'] is not None:
                    try:
                        new_input.default_value = input_data['default_value']
                    except:
                        pass
            
            for output_data in node_group_data['outputs']:
                new_group.outputs.new(output_data['type'], output_data['name'])
            
            node_map = {}
            for node_data in node_group_data['nodes']:
                new_node = new_group.nodes.new(node_data['type'])
                new_node.name = node_data['name']
                new_node.location = node_data['location']
                new_node.width = node_data['width']
                new_node.height = node_data['height']
                
                for i, value in node_data['inputs'].items():
                    if i < len(new_node.inputs):
                        try:
                            new_node.inputs[i].default_value = value
                        except:
                            pass
                
                node_map[node_data['name']] = new_node
            
            for link_data in node_group_data['links']:
                from_node = node_map.get(link_data['from_node'])
                to_node = node_map.get(link_data['to_node'])
                
                if from_node and to_node:
                    from_socket = None
                    to_socket = None
                    
                    for socket in from_node.outputs:
                        if socket.identifier == link_data['from_socket']:
                            from_socket = socket
                            break
                    
                    for socket in to_node.inputs:
                        if socket.identifier == link_data['to_socket']:
                            to_socket = socket
                            break
                    
                    if from_socket and to_socket:
                        new_group.links.new(from_socket, to_socket)
            
            bpy.ops.wm.save_as_mainfile(filepath=blend_path)
            
            if current_file:
                bpy.ops.wm.open_mainfile(filepath=current_file)
            elif current_is_saved:
                bpy.ops.wm.read_homefile(use_empty=True)
            
            print(f"Successfully created .blend file using fallback method: {blend_path}")
            return True
            
        except Exception as e:
            print(f"Fallback .blend creation failed: {e}")
            import traceback
            traceback.print_exc()
            
            try:
                if current_file:
                    bpy.ops.wm.open_mainfile(filepath=current_file)
                else:
                    bpy.ops.wm.read_homefile(use_empty=True)
            except:
                print("Failed to restore original Blender state")
            
            return False
    
    def _copy_node_group_interface(self, source_group, target_group):
        try:
            target_group.inputs.clear()
            target_group.outputs.clear()
            
            for input_socket in source_group.inputs:
                new_input = target_group.inputs.new(input_socket.bl_idname, input_socket.name)
                if hasattr(input_socket, 'default_value') and hasattr(new_input, 'default_value'):
                    try:
                        new_input.default_value = input_socket.default_value
                    except:
                        pass
                        
                for attr in ['min_value', 'max_value', 'description']:
                    if hasattr(input_socket, attr) and hasattr(new_input, attr):
                        try:
                            setattr(new_input, attr, getattr(input_socket, attr))
                        except:
                            pass
            
            for output_socket in source_group.outputs:
                new_output = target_group.outputs.new(output_socket.bl_idname, output_socket.name)
                if hasattr(output_socket, 'default_value') and hasattr(new_output, 'default_value'):
                    try:
                        new_output.default_value = output_socket.default_value
                    except:
                        pass
                        
                for attr in ['description']:
                    if hasattr(output_socket, attr) and hasattr(new_output, attr):
                        try:
                            setattr(new_output, attr, getattr(output_socket, attr))
                        except:
                            pass
                            
        except Exception as e:
            print(f"Error copying interface: {e}")
    
    def _copy_nodes(self, source_group, target_group):
        try:
            target_group.nodes.clear()
            
            node_map = {}
            
            for source_node in source_group.nodes:
                new_node = target_group.nodes.new(source_node.bl_idname)
                new_node.name = source_node.name
                new_node.label = source_node.label
                new_node.location = source_node.location
                new_node.width = source_node.width
                new_node.height = source_node.height
                new_node.hide = source_node.hide
                new_node.mute = source_node.mute
                new_node.select = source_node.select
                
                self._copy_node_properties(source_node, new_node)
                
                node_map[source_node] = new_node
                
            return node_map
            
        except Exception as e:
            print(f"Error copying nodes: {e}")
            return {}
    
    def _copy_node_properties(self, source_node, target_node):
        try:
            for i, source_socket in enumerate(source_node.inputs):
                if i < len(target_node.inputs):
                    target_socket = target_node.inputs[i]
                    if (hasattr(source_socket, 'default_value') and 
                        hasattr(target_socket, 'default_value') and
                        not source_socket.is_linked):
                        try:
                            target_socket.default_value = source_socket.default_value
                        except:
                            pass
            
            properties_to_copy = [
                'operation', 'blend_type', 'distribution', 'mode', 
                'data_type', 'domain', 'interpolation', 'resolution',
                'use_clamp', 'clamp_factor', 'offset', 'scale'
            ]
            
            for prop in properties_to_copy:
                if hasattr(source_node, prop) and hasattr(target_node, prop):
                    try:
                        setattr(target_node, prop, getattr(source_node, prop))
                    except:
                        pass
                        
            if source_node.type == 'GROUP' and hasattr(source_node, 'node_tree'):
                if hasattr(target_node, 'node_tree'):
                    target_node.node_tree = source_node.node_tree
                    
        except Exception as e:
            print(f"Error copying node properties: {e}")
    
    def _copy_links(self, source_group, target_group):
        try:
            node_map = {}
            for target_node in target_group.nodes:
                node_map[target_node.name] = target_node
            
            # Copy links
            for source_link in source_group.links:
                try:
                    from_node = node_map.get(source_link.from_node.name)
                    to_node = node_map.get(source_link.to_node.name)
                    
                    if from_node and to_node:
                        from_socket = None
                        for socket in from_node.outputs:
                            if socket.identifier == source_link.from_socket.identifier:
                                from_socket = socket
                                break
                        
                        to_socket = None
                        for socket in to_node.inputs:
                            if socket.identifier == source_link.to_socket.identifier:
                                to_socket = socket
                                break
                        
                        if from_socket and to_socket:
                            target_group.links.new(from_socket, to_socket)
                            
                except Exception as link_error:
                    print(f"Error copying individual link: {link_error}")
                    continue
                    
        except Exception as e:
            print(f"Error copying links: {e}")
