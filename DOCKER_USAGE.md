# Docker Usage for usdzconvert

## Building the Docker Image

Build the Docker image:
```bash
docker build -t usdzconvert:latest .
```

Or using docker-compose:
```bash
docker-compose build
```

## Usage

### Method 1: Direct Docker Commands

Place your files in the `data/` directory, then run:

```bash
# Convert a file to USDZ
docker run -v $(pwd)/data:/data usdzconvert:latest input.obj output.usdz

# With iOS 12 compatibility
docker run -v $(pwd)/data:/data usdzconvert:latest input.gltf output.usdz -iOS12

# Get help
docker run usdzconvert:latest -h

# Validate a USDZ file
docker run -v $(pwd)/data:/data usdzconvert:latest \
  python3 /app/usdzconvert/usdARKitChecker file.usdz
```

### Method 2: Docker Compose

```bash
# Show help
docker-compose run --rm usdzconvert -h

# Convert a file (place it in data/ directory first)
docker-compose run --rm usdzconvert input.obj output.usdz

# Validate a USDZ file
docker-compose run --rm usd-validator file.usdz

# Open interactive shell for multiple operations
docker-compose run --rm usd-shell
```

### Method 3: Shell Alias (Recommended)

Add this to your `.bashrc` or `.zshrc`:

```bash
alias usdzconvert='docker run -v $(pwd):/data usdzconvert:latest'
alias usdARKitChecker='docker run -v $(pwd):/data usdzconvert:latest python3 /app/usdzconvert/usdARKitChecker'
```

Then use as normal:
```bash
usdzconvert model.gltf model.usdz
usdARKitChecker model.usdz
```

## Directory Structure

```
usdpython/
├── data/           # Place your input files here
├── Dockerfile      # Docker image definition
├── docker-compose.yml
└── ...
```

## Advanced Usage

### Custom Python Scripts

Run custom scripts that use the USD tools:

```bash
# Mount current directory and run a script
docker run -v $(pwd):/data -v $(pwd)/scripts:/scripts usdzconvert:latest \
  python3 /scripts/my_usd_script.py
```

### Running Samples

```bash
# Run sample scripts
docker run -v $(pwd)/samples:/data usdzconvert:latest \
  python3 /app/samples/usdz_cylinder.py
```

## Troubleshooting

1. **Permission Issues**: Output files are created as root. Fix with:
   ```bash
   sudo chown -R $(whoami):$(whoami) data/
   ```

2. **Memory Issues**: Increase Docker memory limit in Docker Desktop settings

3. **Missing Dependencies**: Rebuild the image:
   ```bash
   docker-compose build --no-cache
   ```

## Notes

- The Docker image includes all necessary USD libraries and Python dependencies
- FBX support is not included (requires proprietary Autodesk SDK)
- Input/output files should be placed in the `data/` directory
- The image is based on Python 3.9 for compatibility with usd-core