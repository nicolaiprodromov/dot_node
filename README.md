
![Node Extension Preview](./docs/Asset%2026.png)

<div align="center">

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/nicolaiprodromov/dot_node/releases)
[![Blender](https://img.shields.io/badge/Blender-4.1%2B-orange.svg)](https://www.blender.org)
[![Community](https://img.shields.io/badge/join-community-ff69b4.svg)](https://xwz.app)

</div>

<div align="center">

### Introducing `.node`

*Package, share, and distribute Geometry Node groups across the Blender community.*

Instead of spending time appending node groups you can now use `.node` as a simple and portable file that you can *import* or *export* at will with one simple action.

Check the releases for the latest version.

</div>

###

![Node File Examples](./docs/Asset%2022.png)

###

- **One-Click Import**: Drag and drop `.node` files directly into Blender
- **Complete Packaging**: All node data, connections, and metadata in one file
- **Version Control Ready**: Perfect for Git workflows and collaborative projects
- **Community Standard**: Establish a unified format for the entire nodes ecosystem
- **Lightning Fast**: No more hunting through blend files, just instant access to node groups

## Install

1. **Download** the latest release from [Releases](https://github.com/nicolaiprodromov/dot_node/releases)
2. **Install** via Blender → Edit → Preferences → Add-ons → Install
3. **Enable** the "Node File Link" addon
4. **Enjoy** seamless `.node` file support!

###

<div align="center">

![File Example](./docs/Capture.JPG)

</div>

## Import & Export

- **IMPORT**:
    1. Drag & Drop the nodes you want to import
- **EXPORT**:
    1. Select the node/nodes you want to export
    2. Right click > Export Node Groups

###

![Node Format Features](./docs/Asset%2023.png)
![Node Workflow](./docs/Asset%2025.png)

## 🌟 The file

The `.node` file is designed to become the **standard** for sharing Blender node groups.

> More than just a file type, a **community initiative** to standardize how we share and collaborate using procedural setups in Blender.

### Understanding `.node` files

A `.node` file is a lightweight, portable package for sharing procedural node group setups with all the data, connections, and metadata. Technically, it's a ZIP archive containing three essential components:

- a `.json` metadata file with nodes structure and properties
- a `.blend` file with the actual node group data
- a `.config` file for package validation.

This format enables seamless sharing and importing across different Blender projects without complex file dependencies.

### Features

| Feature | Description |
|---------|-------------|
| **Export** | Convert any Geometry Node group to `.node` format |
| **Import** | Seamlessly import `.node` files with full fidelity |
| **Drag & Drop** | Native file association for instant workflow integration |
| **Metadata** | Preserve all node properties, connections, and interface definitions |
| **Cross-Platform** | WIP -> Works only on Windows atm|

## How to help

- **Adopt** the `.node` format in your projects
- **Share** `.node` files along with your .blend files (they're very small)
- **Contribute** to the project development by becoming a *contributor*/sharing your opinion
- **Buy** the addon on superhive or blenderkit

## Contributors

- Found an issue? [Create an issue](https://github.com/nicolaiprodromov/dot_node/issues/new)
- Have an idea? [Start a discussion](https://github.com/nicolaiprodromov/dot_node/discussions)
- Help improve the docs and examples

###

[![Star this repo](https://img.shields.io/github/stars/nicolaiprodromov/dot_node?style=social)](https://github.com/nicolaiprodromov/dot_node)

<div align="center">

![Footer Image](./docs/Asset%2030.png)

</div>
