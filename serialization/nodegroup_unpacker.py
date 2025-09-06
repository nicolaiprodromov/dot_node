import bpy
import os
import json
import tempfile
import zipfile
import shutil
from typing import Tuple, List, Optional

class NodeGroupUnpacker:    
    REQUIRED_FILES = {'.config', '.json', '.blend'}
    
    def __init__(self):
        self.temp_dirs = []
        self._mouse_coords = None
    
    def set_mouse_coordinates(self, x: int, y: int):
        self._mouse_coords = (x, y)
        print(f"Mouse coordinates set for unpacker: ({x}, {y})")

    def unpack_node_file(self, filepath: str) -> Tuple[bool, str]:
        try:
            print(f"🔍 Processing .node file: {os.path.basename(filepath)}")
            
            if not os.path.exists(filepath):
                return False, f"File does not exist: {filepath}"
            
            if not filepath.lower().endswith('.node'):
                return False, f"File is not a .node file: {filepath}"
            
            temp_dir = tempfile.mkdtemp(prefix="nodegroup_unpack_")
            self.temp_dirs.append(temp_dir)
            
            success, message = self._extract_node_file(filepath, temp_dir)
            if not success:
                return False, message
            
            success, message = self._validate_node_structure(temp_dir)
            if not success:
                return False, message
            
            config_data = self._load_config(temp_dir)
            
            success, message = self._append_nodegroups(temp_dir, config_data)
            if not success:
                return False, message
            
            return True, f"Successfully imported node groups from {os.path.basename(filepath)}"
                
        except Exception as e:
            return False, f"Error processing {os.path.basename(filepath)}: {str(e)}"
    
    def _extract_node_file(self, filepath: str, temp_dir: str) -> Tuple[bool, str]:
        try:
            print(f"Extracting {os.path.basename(filepath)}...")
            
            with zipfile.ZipFile(filepath, 'r') as zip_file:
                try:
                    zip_file.testzip()
                except zipfile.BadZipFile:
                    return False, "File is not a valid zip archive"
                
                zip_file.extractall(temp_dir)
                
            extracted_files = os.listdir(temp_dir)
            print(f"Extracted {len(extracted_files)} files: {extracted_files}")
            
            return True, "Extraction successful"
            
        except zipfile.BadZipFile:
            return False, "File is not a valid zip archive"
        except Exception as e:
            return False, f"Error extracting file: {str(e)}"
    
    def _validate_node_structure(self, temp_dir: str) -> Tuple[bool, str]:
        try:
            extracted_files = os.listdir(temp_dir)
            print(f"Validating file structure...")
            print(f"   Found files: {extracted_files}")
            
            found_files = set()
            for filename in extracted_files:
                if filename == '.config':
                    found_files.add('.config')
                else:
                    _, ext = os.path.splitext(filename)
                    if ext.lower() in {'.json', '.blend'}:
                        found_files.add(ext.lower())
            
            print(f"   Found required files: {found_files}")
            print(f"   Required files: {self.REQUIRED_FILES}")
            
            missing_files = self.REQUIRED_FILES - found_files
            
            if missing_files:
                missing_str = ", ".join(missing_files)
                return False, f"Malformed .node file - missing required files: {missing_str}"
            
            print("File structure validation passed")
            return True, "Valid .node file structure"
            
        except Exception as e:
            return False, f"Error validating file structure: {str(e)}"
    
    def _load_config(self, temp_dir: str) -> Optional[dict]:
        try:
            config_files = [f for f in os.listdir(temp_dir) if f.endswith('.config')]
            if not config_files:
                print("No .config file found")
                return None
            
            config_path = os.path.join(temp_dir, config_files[0])
            
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                print(f"Loaded configuration: {config_files[0]}")
                return config_data
            except json.JSONDecodeError:
                print(".config file is not valid JSON, skipping...")
                return None
                
        except Exception as e:
            print(f"Error loading config: {e}")
            return None
    
    def _append_nodegroups(self, temp_dir: str, config_data: Optional[dict]) -> Tuple[bool, str]:
        try:
            blend_files = [f for f in os.listdir(temp_dir) if f.endswith('.blend')]
            if not blend_files:
                return False, "No .blend file found in .node package"
            
            print(f"Found {len(blend_files)} blend file(s): {blend_files}")
            
            existing_nodegroups = set(bpy.data.node_groups.keys())
            
            all_imported_nodegroups = []
            
            for blend_file in blend_files:
                blend_path = os.path.join(temp_dir, blend_file)
                print(f"Processing blend file: {blend_file}")
                
                with bpy.data.libraries.load(blend_path) as (data_from, data_to):
                    print(f"Available node groups in {blend_file}: {data_from.node_groups}")
                    
                    if data_from.node_groups:
                        data_to.node_groups = data_from.node_groups
            
            new_nodegroups = set(bpy.data.node_groups.keys()) - existing_nodegroups
            
            if new_nodegroups:
                print(f"Successfully appended {len(new_nodegroups)} node group(s) from {len(blend_files)} blend file(s):")
                for ng_name in sorted(new_nodegroups):
                    node_group = bpy.data.node_groups[ng_name]
                    ng_type = getattr(node_group, 'type', 'Unknown')
                    print(f"   • {ng_name} ({ng_type})")
                    all_imported_nodegroups.append((ng_name, ng_type, node_group))
                
                should_place_at_cursor = (len(blend_files) == 1 and len(all_imported_nodegroups) == 1)
                
                mouse_coords = getattr(self, '_mouse_coords', None)
                self._place_nodes_in_editors(all_imported_nodegroups, should_place_at_cursor, mouse_coords)
                
                return True, f"Appended {len(new_nodegroups)} node group(s) from {len(blend_files)} blend file(s): {', '.join(sorted(new_nodegroups))}"
            else:
                return False, "No new node groups were appended (they may already exist)"
                
        except Exception as e:
            return False, f"Error appending node groups: {str(e)}"
    
    def _place_nodes_in_editors(self, imported_nodegroups, place_at_cursor: bool = False, mouse_coords = None):
        """Place imported node groups as nodes in appropriate editors"""
        try:
            context = bpy.context
            
            if not (context.area and context.area.type == 'NODE_EDITOR' and context.space_data):
                print("📍 Not in node editor - nodes imported but not placed")
                return
            
            space = context.space_data
            tree_type = getattr(space, 'tree_type', None)
            active_tree = getattr(space, 'node_tree', None)
            
            if not active_tree:
                print("No active node tree - nodes imported but not placed")
                return

            print(f"Detected editor context: {tree_type}")
            print(f"Placement mode: {'cursor position' if place_at_cursor else 'automatic spacing'}")

            compatible_groups = []
            
            if tree_type == 'GeometryNodeTree':
                compatible_groups = [
                    (name, ng_type, node_group) for name, ng_type, node_group in imported_nodegroups
                    if ng_type in ('GeometryNodeTree', 'GEOMETRY')
                ]
                node_type_to_create = 'GeometryNodeGroup'
                
            elif tree_type == 'ShaderNodeTree':
                compatible_groups = [
                    (name, ng_type, node_group) for name, ng_type, node_group in imported_nodegroups
                    if ng_type in ('ShaderNodeTree', 'SHADER')
                ]
                node_type_to_create = 'ShaderNodeGroup'
                
            elif tree_type == 'CompositorNodeTree':
                compatible_groups = [
                    (name, ng_type, node_group) for name, ng_type, node_group in imported_nodegroups
                    if ng_type in ('CompositorNodeTree', 'COMPOSITING')
                ]
                node_type_to_create = 'CompositorNodeGroup'
                
            else:
                print(f"Unsupported editor type: {tree_type}")
                return
            
            print(f"Found {len(compatible_groups)} compatible node group(s) for {tree_type}")
            for name, ng_type, _ in compatible_groups:
                print(f"   • {name} ({ng_type})")
            
            if not compatible_groups:
                print(f"No compatible node groups found for {tree_type}")
                return

            cursor_location = None
            if place_at_cursor and mouse_coords and context.region:
                try:
                    region = context.region
                    if hasattr(space, 'cursor_location'):
                        view_center_x = space.cursor_location[0] if space.cursor_location else 0
                        view_center_y = space.cursor_location[1] if space.cursor_location else 0
                        cursor_location = (view_center_x, view_center_y)
                    else:
                        cursor_location = (0, 0)
                    
                    print(f"Target location: {cursor_location} (converted from mouse {mouse_coords})")
                except Exception as e:
                    print(f"Could not convert mouse coordinates, using default: {e}")
                    cursor_location = (0, 0)
            
            placed_count = 0
            for name, ng_type, node_group in compatible_groups:
                try:
                    new_node = active_tree.nodes.new(type=node_type_to_create)
                    new_node.node_tree = node_group
                    new_node.label = name
                    new_node.name = name
                    
                    if place_at_cursor and cursor_location:

                        location = (cursor_location[0] + placed_count * 50, cursor_location[1] - placed_count * 50)
                    else:
                        location = (placed_count * 300, -placed_count * 200)
                    
                    new_node.location = location
                    
                    for node in active_tree.nodes:
                        node.select = False
                    new_node.select = True
                    active_tree.nodes.active = new_node
                    
                    print(f"Placed node: {name} at ({location[0]}, {location[1]})")
                    placed_count += 1
                    
                except Exception as e:
                    print(f"Failed to place node {name}: {e}")
            
            if placed_count > 0:
                print(f"Successfully placed {placed_count} node(s) in {tree_type} editor")
                if context.area:
                    context.area.tag_redraw()
            
        except Exception as e:
            print(f"Error placing nodes in editors: {e}")
            import traceback
            traceback.print_exc()
    
    def process_multiple_files(self, file_paths: List[str]) -> Tuple[int, int, List[str]]:
        success_count = 0
        failure_count = 0
        error_messages = []
        
        print(f"Processing {len(file_paths)} .node file(s)...")
        
        for filepath in file_paths:
            success, message = self.unpack_node_file(filepath)
            if success:
                success_count += 1
                print(f"✅ {os.path.basename(filepath)}: {message}")
            else:
                failure_count += 1
                error_msg = f"❌ {os.path.basename(filepath)}: {message}"
                print(error_msg)
                error_messages.append(error_msg)
        
        return success_count, failure_count, error_messages
    
    def cleanup(self):
        for temp_dir in self.temp_dirs:
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                    print(f"Cleaned up temp directory: {temp_dir}")
            except Exception as e:
                print(f"Failed to clean up {temp_dir}: {e}")
        self.temp_dirs.clear()
    
    def __del__(self):
        self.cleanup()


def unpack_node_files(file_paths: List[str]) -> Tuple[bool, str]:
    if not file_paths:
        return False, "No files provided"
    
    unpacker = NodeGroupUnpacker()
    
    try:
        if len(file_paths) == 1:
            success, message = unpacker.unpack_node_file(file_paths[0])
            return success, message
        else:
            success_count, failure_count, error_messages = unpacker.process_multiple_files(file_paths)
            
            if success_count > 0:
                summary = f"Successfully processed {success_count}/{len(file_paths)} file(s)"
                if failure_count > 0:
                    summary += f". {failure_count} failed."
                return True, summary
            else:
                return False, f"All {len(file_paths)} file(s) failed to process"
                
    finally:
        unpacker.cleanup()
