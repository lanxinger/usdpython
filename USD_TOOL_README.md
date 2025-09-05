# Unified USD Tool

A centralized command-line tool that combines all USD conversion, validation, and manipulation capabilities into a single interface.

## Features

- **Single tool** for all USD operations (no need to remember different commands)
- **Batch processing** for converting entire directories
- **Pipeline mode** for chaining operations (convert → condition → validate)
- **Docker support** with pre-configured services
- Backwards compatible with original tool arguments

## Installation

### Local Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Make executable
chmod +x usd_tool.py

# Add to PATH (optional)
echo 'alias usd-tool="python3 /path/to/usdpython/usd_tool.py"' >> ~/.bashrc
```

### Docker Installation
```bash
# Build the Docker image
docker build -t usd-tool:latest .

# Or using docker-compose
docker-compose build
```

## Commands

### `convert` - Convert 3D files to USDZ
```bash
# Basic conversion
usd_tool.py convert model.obj model.usdz

# With options (passes through to usdzconvert)
usd_tool.py convert model.gltf model.usdz -iOS12 -v

# Docker
docker-compose run --rm convert model.obj model.usdz
```

### `validate` - Validate USDZ for AR compatibility
```bash
# Validate a file
usd_tool.py validate model.usdz

# Docker
docker-compose run --rm validate model.usdz
```

### `condition` - Fix USD compatibility issues
```bash
# Fix double-sided, subdivision, and binding issues
usd_tool.py condition input.usdz -o output.usdz

# Control specific fixes
usd_tool.py condition input.usdz -o output.usdz -d off -s auto

# Docker
docker-compose run --rm condition input.usdz -o output.usdz
```

### `variants` - Combine multiple USD files as variants
```bash
# Material variants
usd_tool.py variants -m red.usdz blue.usdz green.usdz -o combined.usdz

# Animation variants
usd_tool.py variants -a walk.usdz run.usdz idle.usdz -o animated.usdz

# Docker
docker-compose run --rm variants -m red.usdz blue.usdz -o combined.usdz
```

### `batch` - Batch convert directories
```bash
# Convert all supported files in directory
usd_tool.py batch input_dir/ output_dir/

# Recursive with iOS 12 compatibility
usd_tool.py batch input_dir/ output_dir/ --recursive --ios12

# Docker
docker-compose run --rm batch input_dir/ output_dir/ --recursive
```

### `pipeline` - Run full processing pipeline
```bash
# Convert, condition, and validate in one command
usd_tool.py pipeline model.obj final.usdz --condition --validate

# With conditioning options
usd_tool.py pipeline model.fbx final.usdz --condition --validate \
  --doublesided auto --subdivision off --ios12

# Docker
docker-compose run --rm pipeline model.obj final.usdz --condition --validate
```

### Additional Commands

- `opacity` - Fix opacity issues in USDZ files
- `assetlib` - Create asset libraries
- `audio` - Import audio into USDZ files

## Docker Usage

### Quick Commands
```bash
# Place files in data/ directory, then:

# Convert
docker-compose run --rm usd convert input.obj output.usdz

# Validate
docker-compose run --rm usd validate model.usdz

# Batch process
docker-compose run --rm usd batch . processed/ --recursive

# Full pipeline
docker-compose run --rm usd pipeline input.gltf output.usdz --condition --validate

# Interactive shell
docker-compose run --rm shell
```

### Docker Alias Setup
Add to your shell config:
```bash
alias usd-tool='docker run -v $(pwd):/data usd-tool:latest'
```

Then use like:
```bash
usd-tool convert model.obj model.usdz
usd-tool validate model.usdz
usd-tool batch input/ output/ --recursive
```

## Examples

### Example 1: Simple Conversion
```bash
# Convert OBJ to USDZ
usd_tool.py convert statue.obj statue.usdz
```

### Example 2: Batch Process with Pipeline
```bash
# Convert all GLB files, condition them, and validate
for file in *.glb; do
  usd_tool.py pipeline "$file" "processed/${file%.glb}.usdz" \
    --condition --validate
done
```

### Example 3: Create Material Variants
```bash
# Combine different colored versions
usd_tool.py variants \
  -m Red red_chair.usdz Blue blue_chair.usdz Green green_chair.usdz \
  -o chair_variants.usdz
```

### Example 4: Fix Legacy Files
```bash
# Fix old USDZ files for modern iOS
usd_tool.py condition legacy.usdz -o modern.usdz -d auto -s auto
```

### Example 5: Production Pipeline
```bash
# Full production pipeline with all optimizations
usd_tool.py pipeline raw_model.fbx production.usdz \
  --condition \
  --validate \
  --ios12 \
  --doublesided auto \
  --subdivision off
```

## Supported Input Formats

- **Mesh**: OBJ, FBX, ABC (Alembic)
- **Scene**: GLTF, GLB
- **USD**: USD, USDA, USDC, USDZ

## Command Comparison

| Old Command | New Unified Command |
|------------|-------------------|
| `usdzconvert model.obj out.usdz` | `usd_tool.py convert model.obj out.usdz` |
| `usdARKitChecker file.usdz` | `usd_tool.py validate file.usdz` |
| `python3 usd_conditioner.py in.usdz -o out.usdz` | `usd_tool.py condition in.usdz -o out.usdz` |
| `python3 variant_combiner.py -m ...` | `usd_tool.py variants -m ...` |
| `fixOpacity model.usdz` | `usd_tool.py opacity model.usdz` |

## Advantages

1. **Single Entry Point**: One command to remember instead of multiple tools
2. **Consistent Interface**: Unified argument structure and help system
3. **Pipeline Support**: Chain operations without intermediate files
4. **Batch Processing**: Built-in directory processing
5. **Docker Integration**: Pre-configured services for each operation
6. **Extensible**: Easy to add new commands and features

## Troubleshooting

### Permission Denied
```bash
chmod +x usd_tool.py
```

### Module Not Found
```bash
# Ensure you're in the right directory
cd /path/to/usdpython

# Or set PYTHONPATH
export PYTHONPATH=$PYTHONPATH:/path/to/usdpython/USD/lib/python
```

### Docker Build Issues
```bash
# Rebuild without cache
docker-compose build --no-cache
```

## License

This tool integrates components with various licenses. See individual tool directories for specific license information.