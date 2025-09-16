# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based USD (Universal Scene Description) tools repository focused on converting various 3D file formats to USDZ and working with USD files. The tools are designed to work with macOS and iOS devices for AR content.

## Environment Setup

Before running any tools, set up the environment:

```bash
# Run the setup script to set environment variables
./USD.command

# Or manually set the environment:
export PATH=$PATH:<PATH_TO_USDPYTHON>/USD:<PATH_TO_USDPYTHON>/usdzconvert
export PYTHONPATH=$PYTHONPATH:<PATH_TO_USDPYTHON>/USD/lib/python
```

Install Python dependencies:
```bash
python3 -m pip install -r requirements.txt
```

## Common Development Commands

### Unified Tool Interface (Preferred)
The **centralized `usd_tool.py`** is the main entry point for all operations:

```bash
# Convert any 3D file to USDZ (auto-detects textures)
./usd_tool.py convert model.obj model.usdz

# Run full pipeline (convert → condition → validate)
./usd_tool.py pipeline model.gltf final.usdz --condition --validate

# Batch convert directory
./usd_tool.py batch input_dir/ output_dir/ --recursive

# Validate USDZ for ARKit compatibility
./usd_tool.py validate model.usdz

# View all available commands
./usd_tool.py --help
```

### Legacy Tools (Still Available)
- Convert to USDZ: `usdzconvert <input_file> <output.usdz> [options]`
- Help for conversion: `usdzconvert -h`
- iOS 12 compatibility: Add `-iOS12` flag
- Validate USDZ files: `usdARKitChecker <file.usdz>`
- Fix opacity issues: `fixOpacity <model.usdz>`
- Create asset library: `usdzcreateassetlib <assets...>`
- Import audio: `usdzaudioimport -h`
- Condition USD files: `python3 USD-Support-Scripts/usd_conditioner.py`
- Combine variants: `python3 USD-Support-Scripts/variant_combiner.py`

### Docker Usage
```bash
# Build Docker image
docker build -t usd-tool:latest .

# Run commands in container
docker run -v $(pwd)/data:/data usd-tool:latest convert model.obj model.usdz
```

### Running Samples
```bash
cd samples
python3 <sample_script>.py  # Creates files in samples/assets/
```

## Architecture

### Core Components

**usdzconvert/** - Main conversion tool and utilities
- `usdzconvert` - Main entry point for file conversion
- `usdStageWithObj.py`, `usdStageWithFbx.py`, `usdStageWithGlTF.py` - Format-specific converters
- `usdUtils.py` - Core USD utilities and Asset class
- `validateMesh.py`, `validateMaterial.py` - Validation modules
- `iOS12LegacyModifier.py` - iOS 12 compatibility layer

**USD-Support-Scripts/** - Additional USD manipulation tools
- `variant_combiner.py` - Combines multiple USD variants
- `usd_conditioner.py` - Conditions USD files for specific platforms

**samples/** - Example scripts demonstrating USD creation patterns
- Each script generates both .usd and .usdz files in samples/assets/

### Key Patterns

1. **USD Stage Creation**: All conversion tools create a USD stage, define geometry/materials, then export to USDZ
2. **Material System**: Materials are managed through USDParameters class with paths stored at `/Materials`
3. **Asset Management**: The `usdUtils.Asset` class handles file paths and textures
4. **Validation Pipeline**: Files pass through usdchecker, mesh validation, and material validation
5. **Unified Tool Architecture**: `usd_tool.py` acts as a central dispatcher, dynamically loading conversion modules
6. **Automatic Texture Detection**: OBJ files use MTL parsing first, then fall back to filename pattern matching
7. **Modern Format Support**: AVIF textures supported with 40-80% smaller file sizes

### Texture Auto-Detection Patterns
When no MTL file exists, the tools automatically detect textures by filename:
- **Diffuse**: `*diffuse*`, `*albedo*`, `*color*`, `*_d.*`
- **Normal**: `*normal*`, `*bump*`, `*_n.*`
- **Roughness**: `*roughness*`, `*rough*`, `*_r.*`
- **Metallic**: `*metallic*`, `*metal*`, `*_m.*`
- **Occlusion**: `*occlusion*`, `*ao*`, `*_o.*`
- **Opacity**: `*opacity*`, `*alpha*`, `*_a.*`
- **Emissive**: `*emissive*`, `*glow*`, `*_e.*`
- **Displacement**: `*displacement*`, `*height*`, `*disp*`, `*_disp.*`

### Development Workflow

1. **Setup**: Run `./USD.command` or manually set PATH/PYTHONPATH
2. **Install Dependencies**: `python3 -m pip install -r requirements.txt`
3. **Convert/Test**: Use `./usd_tool.py` for all operations
4. **Validate**: All conversions automatically run ARKit validation
5. **Docker Alternative**: Use containerized workflow for isolation

### Important Notes

- Modern setup uses `usd-core` package (Python 3.9+) instead of precompiled libraries
- FBX support requires Autodesk's FBX SDK and Python bindings (configure in USD.command)
- All tools use Pixar's USD library (pxr module), now version 24.0.0+
- Default coordinate system uses Y-up axis
- AVIF textures provide native ARKit support on modern iOS devices