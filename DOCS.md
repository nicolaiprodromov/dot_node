![Node Extension Preview](./docs/Asset%2026.png)

<div align="center">

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/nicolaiprodromov/dot_node/releases)
[![Blender](https://img.shields.io/badge/Blender-4.1%2B-orange.svg)](https://www.blender.org)
[![Community](https://img.shields.io/badge/join-community-ff69b4.svg)](https://xwz.app)

</div>

<div align="center">

### Technical Documentation for `.node`

*Deep dive into the architecture, implementation, and technical specifications of the Node File Link addon.*

This documentation covers the internal workings of the `.node` file format, serialization engine, and Blender integration mechanisms that power seamless node group sharing and distribution.

</div>

###

- **Advanced Serialization**: Complete node tree serialization with metadata, properties, and interface definitions
- **Cross-Version Compatibility**: Handles Blender 4.1+ interface changes and node tree variations
- **Windows Registry Integration**: Automatic file association registration with custom icon support
- **Real-time Import System**: Drag & drop functionality with cursor-aware node placement

> *Deep dive into the architecture, implementation, and technical specifications of the Node File Link addon.*

## 📁 File Format Specification

### Internal Structure

A `.node` file is a ZIP archive containing exactly three components:

| Component | Filename | Purpose | Format |
|-----------|----------|---------|--------|
| **Metadata** | `{package_name}.json` | Node structure, properties, and interface definitions | JSON with UTF-8 encoding |
| **Node Data** | `{package_name}.blend` | Actual Blender node group data for importing | Standard Blender file |
| **Package Config** | `.config` | Package validation and integrity verification | Plain text key=value pairs |

### JSON Metadata Schema

The JSON metadata follows a structured schema that captures complete node tree information:

```json
{
  "nodegroup_info": {
    "name": "string",              // Original node group name
    "package_name": "string",      // Sanitized package identifier
    "description": "string",       // Node group description
    "type": "GeometryNodeTree",    // Blender node tree type
    "version": "1.0.0",           // Package format version
    "blender_version": "string",   // Source Blender version
    "export_timestamp": "ISO8601"  // Creation timestamp
  },
  "interface": {
    "inputs": [...],              // Input socket definitions
    "outputs": [...]              // Output socket definitions
  },
  "nodes": [...],                 // Individual node data
  "links": [...],                 // Node connections
  "layout": {                     // Visual layout information
    "frames": [...],              // Frame node data
    "reroutes": [...]             // Reroute node positions
  },
  "dependencies": {               // External dependencies
    "node_groups": [...],         // Required node groups
    "materials": [...],           // Material dependencies
    "objects": [...],             // Object references
    "images": [...],              // Image textures
    "texts": [...]                // Text datablocks
  }
}
```

#### Socket Serialization

Socket data includes comprehensive type information and default values:

```json
{
  "name": "string",
  "identifier": "string",         // Unique socket identifier
  "socket_type": "string",        // Blender socket type (bl_idname)
  "in_out": "INPUT|OUTPUT",       // Socket direction
  "description": "string",        // User description
  "default_value": "variant",     // Serialized default value
  "min_value": "number",          // Optional range constraints
  "max_value": "number",
  "subtype": "string",            // Socket subtype information
  "attribute_domain": "string"    // Geometry domain (4.5+)
}
```

### Package Validation System

The `.config` file contains integrity verification data:

```
hash=sha256_hash_of_all_files
created=2025-09-07T12:34:56Z
format_version=1.0.0
```

The hash is computed from all file contents in the package, ensuring data integrity during transfer and storage.

## ⚙️ Serialization Engine

### NodeGroupSerializer Class

The serialization engine handles the complex task of converting Blender's internal node tree representation into a portable format:

#### Core Serialization Methods

| Method | Purpose | Output |
|--------|---------|--------|
| `_serialize_interface()` | Extract input/output socket definitions | Interface structure with socket metadata |
| `_serialize_nodes()` | Capture individual node properties and settings | Complete node data with properties |
| `_serialize_links()` | Map all node connections and relationships | Connection data with socket identifiers |
| `_serialize_layout()` | Preserve visual layout and frame information | Layout data with positioning |

#### Blender Version Compatibility

The serializer handles interface differences between Blender versions:

```python
# Blender 4.5+ Interface API
if hasattr(self.node_group, 'interface') and hasattr(self.node_group.interface, 'items_tree'):
    for item in self.node_group.interface.items_tree:
        if hasattr(item, 'item_type') and item.item_type == 'SOCKET':
            # Process new interface structure
            
# Fallback for Blender 4.1-4.4
elif hasattr(self.node_group, 'inputs') and hasattr(self.node_group, 'outputs'):
    for input_socket in self.node_group.inputs:
        # Process legacy interface structure
```

### Advanced Property Handling

The serializer captures node-specific properties including:

- **Mathematical Properties**: `operation`, `blend_type`, `distribution`, `mode`
- **Data Properties**: `data_type`, `domain`, `interpolation`, `resolution`
- **Control Properties**: `use_clamp`, `clamp_factor`, `offset`, `scale`
- **Custom Properties**: User-defined properties via `node.keys()`

#### Default Value Serialization

Complex data types are handled with appropriate serialization:

```python
def _serialize_socket_default_value(self, socket):
    if not hasattr(socket, 'default_value'):
        return None
    
    try:
        value = socket.default_value
        
        # Handle Blender math types
        if hasattr(value, '__iter__') and not isinstance(value, str):
            return list(value)  # Vector, Color, Euler
        elif hasattr(value, 'copy'):
            return value.copy()  # Ensure immutable copy
        else:
            return value
            
    except Exception:
        return None  # Fallback for unsupported types
```

## 📥 Import & Unpacking System

### NodeGroupUnpacker Class

The unpacking system reconstructs Blender node trees from `.node` files with full fidelity:

#### Import Process Flow

1. **File Validation** - Verify ZIP structure and .config integrity
2. **Metadata Parsing** - Load and validate JSON schema
3. **Dependency Resolution** - Check for required node groups and assets
4. **Node Tree Creation** - Reconstruct nodes with proper typing
5. **Interface Building** - Recreate input/output sockets
6. **Connection Mapping** - Restore all node links
7. **Layout Restoration** - Position nodes and frames

#### Multi-File Processing

The unpacker supports batch processing of multiple `.node` files:

```python
def process_multiple_files(self, file_paths):
    success_count = 0
    error_count = 0
    error_messages = []
    
    for file_path in file_paths:
        success, message = self.unpack_node_file(file_path)
        if success:
            success_count += 1
        else:
            error_count += 1
            error_messages.append(message)
    
    return success_count, error_count, error_messages
```

### Context-Aware Node Placement

The system intelligently places imported nodes based on context:

| Context | Placement Strategy |
|---------|-------------------|
| **Shader Editor** | Center of viewport or at cursor position |
| **Geometry Nodes** | Append to existing tree or create new |
| **Compositor** | Non-overlapping placement with existing nodes |
| **Material Editor** | Integration with active material slot |

## 🖥️ Windows Integration

### File Association System

The `FileAssociationManager` class handles Windows registry integration for seamless file handling:

#### Registry Structure

The addon creates the following registry entries:

```
HKEY_CURRENT_USER\Software\Classes\.node
└── (Default) = "NodeFile"

HKEY_CURRENT_USER\Software\Classes\NodeFile
├── (Default) = "Node Archive File"
├── DefaultIcon
│   └── (Default) = "C:\path\to\addon\icons\logo_xwz_ne.ico"
└── shell\open\command
    └── (Default) = "C:\Program Files\7-Zip\7zFM.exe \"%1\""
```

#### Archive Application Discovery

The system automatically detects suitable archive applications:

1. **7-Zip Detection** - Check standard installation paths and PATH environment
2. **Registry Lookup** - Query both 32-bit and 64-bit registry entries
3. **WinRAR Fallback** - Detect WinRAR installations if 7-Zip unavailable
4. **System Default** - Use Windows "Open With" dialog as last resort

### Shell Integration Features

- **Custom Icons**: `.node` files display with custom XWZ icon
- **Context Menu**: Right-click integration for "Open with Archive Manager"
- **Double-Click Handling**: Direct access to file contents via archive viewer
- **Shell Notifications**: Automatic icon cache refresh and file association updates

## 🎯 Drag & Drop System

### Drop Handler Implementation

The drag & drop system uses Blender's `FileHandler` API for seamless integration:

```python
class NODE_FH_drop_handler(bpy.types.FileHandler):
    bl_idname = "NODE_FH_drop_handler"
    bl_label = "Node Drop Handler"
    bl_import_operator = "node.drop_handler"
    bl_file_extensions = ".node"
    
    @classmethod
    def poll_drop(cls, context):
        return True  # Accept drops in any context
```

#### Mouse Coordinate Capture

Precise cursor positioning for intelligent node placement:

```python
def invoke(self, context, event):
    self.mouse_x = event.mouse_region_x if hasattr(event, 'mouse_region_x') else 0
    self.mouse_y = event.mouse_region_y if hasattr(event, 'mouse_region_y') else 0
    
    # Pass coordinates to unpacker for placement
```

### Multi-File Batch Processing

#### Processing Pipeline

1. **File Validation** - Check each dropped file for .node extension
2. **Batch Queuing** - Organize files for sequential processing
3. **Context Preservation** - Maintain cursor position and active editor
4. **Error Handling** - Collect and report any processing failures
5. **Completion Report** - Display summary of successful imports

## ⚙️ Configuration & Settings

### Addon Manifest Configuration

```toml
schema_version = "1.0.0"
id = "node_file_link"
name = "Node File Link"
tagline = "The base functionality for the .node extension"
version = "1.0.0"
type = "add-on"
maintainer = "XWZ"
website = "https://xwz.app"
license = ["MIT"]
blender_version_min = "4.1.0"
```

### Package Creation System

The `package.bat` script creates optimized `.node` files with integrity verification:

#### PowerShell Integration

Uses .NET compression APIs for cross-platform compatibility:

```powershell
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::Open('output.node', 'Create')

# Add files with proper directory structure
# Calculate SHA256 hash for integrity
# Create .config file with validation data
```

#### Hash Calculation Algorithm

1. Calculate SHA256 hash for each file in package
2. Sort hashes alphabetically for consistency
3. Combine all hashes with pipe separator
4. Calculate final SHA256 hash of combined string
5. Store in `.config` file for validation

## 🔧 API Reference

### Core Classes

#### NodeGroupSerializer

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `serialize()` | `node_group, output_path` | `bool, str` | Main serialization entry point |
| `_serialize_interface()` | `node_group` | `dict` | Extract socket definitions |
| `_serialize_nodes()` | `node_group` | `list` | Capture node properties |
| `_serialize_links()` | `node_group` | `list` | Map node connections |

#### NodeGroupUnpacker

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `unpack_node_file()` | `file_path, mouse_coords` | `bool, str` | Main import entry point |
| `_validate_package()` | `zip_file` | `bool` | Verify package integrity |
| `_reconstruct_interface()` | `metadata` | `None` | Rebuild socket interface |
| `_place_nodes()` | `nodes_data, mouse_coords` | `None` | Position imported nodes |

#### FileAssociationManager

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `register_association()` | `None` | `bool` | Create registry entries |
| `unregister_association()` | `None` | `bool` | Remove file association |
| `is_registered()` | `None` | `bool` | Check association status |
| `find_archive_app()` | `None` | `str` | Locate archive application |

## 💻 Development Guidelines

### Extending the System

For developers looking to extend or modify the addon:

- **Custom Serializers**: Inherit from `NodeGroupSerializer` for specialized node types
- **Additional File Formats**: Implement new packers/unpackers following the established pattern
- **Platform Support**: Add file association managers for macOS and Linux
- **UI Extensions**: Integrate additional operators into Blender's interface

## 📊 Technical Specifications

| Specification | Value |
|---------------|-------|
| **File Format Version** | 1.0.0 |
| **Minimum Blender Version** | 4.1.0 |
| **Maximum Package Size** | 100MB (recommended) |
| **Compression Algorithm** | ZIP (Deflate) |
| **Hash Algorithm** | SHA256 |
| **Encoding** | UTF-8 |
| **Platform Support** | Windows (macOS/Linux planned) |
| **Node Tree Types** | GeometryNodeTree, ShaderNodeTree, CompositorNodeTree |
| **Dependencies Support** | Node Groups, Materials, Objects, Images, Texts |

## 📝 Changelog

- **Version 1.0.0 (September 2025)**: Initial release with core functionality

###

<div align="center">

![Footer Image](./docs/Asset%2030.png)

</div>

[![Star this repo](https://img.shields.io/github/stars/nicolaiprodromov/dot_node?style=social)](https://github.com/nicolaiprodromov/dot_node)