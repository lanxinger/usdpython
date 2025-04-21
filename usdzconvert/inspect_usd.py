# inspect_usd.py (updated)
import sys
import os
from pxr import Usd, Sdf, Tf # Import Tf for error handling

if len(sys.argv) != 2:
    print("Usage: python inspect_usd.py <path_to_usd_file>")
    sys.exit(1)

usd_file_path = sys.argv[1]
print(f"Attempting to inspect: {usd_file_path}")

# 1. Check if file exists
if not os.path.exists(usd_file_path):
    print(f"Error: File does not exist at path: {usd_file_path}")
    sys.exit(1)
print("File exists.")

# 2. Check read permissions
if not os.access(usd_file_path, os.R_OK):
    print(f"Error: No read permissions for file: {usd_file_path}")
    sys.exit(1)
print("Read permissions OK.")

# Ensure environment is set for dependencies (might help Sdf)
usd_root = os.environ.get("USD_ROOT", "/usr/local/USD") # Default if not set
plugin_path = os.path.join(usd_root, "lib", "usd")
python_path = os.path.join(usd_root, "lib", "python")

if "PXR_PLUGINPATH_NAME" not in os.environ or plugin_path not in os.environ["PXR_PLUGINPATH_NAME"]:
     os.environ["PXR_PLUGINPATH_NAME"] = f"{plugin_path}:{os.environ.get('PXR_PLUGINPATH_NAME','')}"
if "PYTHONPATH" not in os.environ or python_path not in os.environ["PYTHONPATH"]:
     os.environ["PYTHONPATH"] = f"{python_path}:{os.environ.get('PYTHONPATH','')}"

print(f"Using PXR_PLUGINPATH_NAME: {os.environ.get('PXR_PLUGINPATH_NAME')}")
print(f"Using PYTHONPATH: {os.environ.get('PYTHONPATH')}")


try:
    # 3. Try opening the layer directly first
    print("Attempting to open layer...")
    layer = Sdf.Layer.FindOrOpen(usd_file_path)
    if not layer:
        print(f"Error: Sdf.Layer.FindOrOpen failed for {usd_file_path}")
        # Check for Tf errors which might give more details
        for err in Tf.Error.GetErrors():
            print(f"Tf Error: {err.commentary} (Source: {err.sourceFileName}:{err.sourceLineNumber})")
        sys.exit(1)
    print("Layer opened successfully.")

    # 4. Try opening the stage using the opened layer
    print("Attempting to open stage using layer...")
    stage = Usd.Stage.Open(layer)
    if not stage:
        print(f"Error: Usd.Stage.Open failed using pre-opened layer.")
        for err in Tf.Error.GetErrors():
            print(f"Tf Error: {err.commentary} (Source: {err.sourceFileName}:{err.sourceLineNumber})")
        sys.exit(1)
    print("Stage opened successfully.")

    # Get the textual representation
    usda_content = stage.GetRootLayer().ExportToString()
    print("\n--- USDA Content ---")
    print(usda_content)
    print("--- End USDA Content ---")


except Exception as e:
    print(f"\nAn unexpected error occurred: {e}")
    # Print any Tf errors as well
    for err in Tf.Error.GetErrors():
            print(f"Tf Error: {err.commentary} (Source: {err.sourceFileName}:{err.sourceLineNumber})")
    sys.exit(1)
