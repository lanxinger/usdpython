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

### File Conversion
- Convert to USDZ: `usdzconvert <input_file> <output.usdz> [options]`
- Help for conversion: `usdzconvert -h`
- iOS 12 compatibility: Add `-iOS12` flag

### Validation
- Validate USDZ files: `usdARKitChecker <file.usdz>`
- Help for validation: `usdARKitChecker -h`

### Other Tools
- Fix opacity issues: `fixOpacity <model.usdz>`
- Create asset library: `usdzcreateassetlib <assets...>`
- Import audio: `usdzaudioimport -h`
- Condition USD files: `python3 USD-Support-Scripts/usd_conditioner.py`
- Combine variants: `python3 USD-Support-Scripts/variant_combiner.py`

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

### Important Notes

- The precompiled USD library requires Python 3.7.9 for full compatibility
- FBX support requires Autodesk's FBX SDK and Python bindings (configure in USD.command)
- All tools use Pixar's USD library (pxr module) version 22.03
- Default coordinate system uses Y-up axis