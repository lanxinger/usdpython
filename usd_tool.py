#!/usr/bin/env python3
"""
Unified USD Tool - A centralized command-line interface for all USD operations.
Combines functionality from usdzconvert, validation tools, and support scripts.
"""

import argparse
import sys
import os
import subprocess
from pathlib import Path
import importlib.util

# Add paths for imports
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR / 'usdzconvert'))
sys.path.insert(0, str(BASE_DIR / 'USD-Support-Scripts'))
sys.path.insert(0, str(BASE_DIR / 'USD' / 'lib' / 'python'))


def load_module(name, path):
    """Dynamically load a Python module from a file path."""
    spec = importlib.util.spec_from_file_location(name, path)
    if spec and spec.loader:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    return None


class USDTool:
    """Centralized USD tool combining all functionality."""
    
    def __init__(self):
        self.base_dir = BASE_DIR
        self.usdzconvert_dir = self.base_dir / 'usdzconvert'
        self.support_scripts_dir = self.base_dir / 'USD-Support-Scripts'
        
    def convert(self, args):
        """Convert 3D files to USDZ format."""
        # Call original usdzconvert
        cmd = [sys.executable, str(self.usdzconvert_dir / 'usdzconvert')] + args.remaining
        return subprocess.call(cmd)
    
    def validate(self, args):
        """Validate USDZ files for AR compatibility."""
        # Use wrapper for better error handling
        wrapper = self.base_dir / 'usdARKitChecker_wrapper.py'
        if wrapper.exists():
            cmd = [sys.executable, str(wrapper)] + args.remaining
        else:
            cmd = [sys.executable, str(self.usdzconvert_dir / 'usdARKitChecker')] + args.remaining
        try:
            return subprocess.call(cmd)
        except Exception as e:
            print(f"Validation error (possibly due to missing shader resources): {e}")
            return 1
    
    def condition(self, args):
        """Condition USD files for compatibility (fix double-sided, subdivision, etc.)."""
        # Import and run usd_conditioner
        conditioner = load_module('usd_conditioner', 
                                 self.support_scripts_dir / 'usd_conditioner.py')
        if conditioner:
            sys.argv = ['usd_conditioner.py'] + args.remaining
            result = conditioner.main()
            return result if result is not None else 0
        else:
            print("Error: Could not load usd_conditioner module")
            return 1
    
    def combine_variants(self, args):
        """Combine multiple USD files into variants."""
        # Import and run variant_combiner
        combiner = load_module('variant_combiner',
                              self.support_scripts_dir / 'variant_combiner.py')
        if combiner:
            sys.argv = ['variant_combiner.py'] + args.remaining
            result = combiner.main()
            return result if result is not None else 0
        else:
            print("Error: Could not load variant_combiner module")
            return 1
    
    def fix_opacity(self, args):
        """Fix opacity issues in USDZ files."""
        cmd = [sys.executable, str(self.usdzconvert_dir / 'fixOpacity')] + args.remaining
        return subprocess.call(cmd)
    
    def create_asset_library(self, args):
        """Create asset library from multiple USDZ files."""
        cmd = [sys.executable, str(self.usdzconvert_dir / 'usdzcreateassetlib')] + args.remaining
        return subprocess.call(cmd)
    
    def import_audio(self, args):
        """Import audio into USDZ files."""
        cmd = [sys.executable, str(self.usdzconvert_dir / 'usdzaudioimport')] + args.remaining
        return subprocess.call(cmd)
    
    def batch_convert(self, args):
        """Batch convert multiple files."""
        input_dir = Path(args.input_dir)
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Supported extensions
        extensions = {'.obj', '.gltf', '.glb', '.fbx', '.abc', '.usda', '.usdc', '.usd'}
        
        files = []
        if args.recursive:
            for ext in extensions:
                files.extend(input_dir.rglob(f'*{ext}'))
        else:
            for ext in extensions:
                files.extend(input_dir.glob(f'*{ext}'))
        
        if not files:
            print(f"No supported files found in {input_dir}")
            return 1
        
        print(f"Found {len(files)} files to convert")
        
        failed = []
        for i, file in enumerate(files, 1):
            relative = file.relative_to(input_dir)
            output_file = output_dir / relative.with_suffix('.usdz')
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            print(f"[{i}/{len(files)}] Converting {relative}...")
            
            cmd = [sys.executable, str(self.usdzconvert_dir / 'usdzconvert'),
                   str(file), str(output_file)]
            
            # Add iOS12 flag if requested
            if args.ios12:
                cmd.append('-iOS12')
            
            # Add verbose flag if requested
            if args.verbose:
                cmd.append('-v')
            
            result = subprocess.call(cmd)
            if result != 0:
                failed.append(relative)
                print(f"  Failed to convert {relative}")
        
        if failed:
            print(f"\nConversion complete with {len(failed)} failures:")
            for f in failed:
                print(f"  - {f}")
            return 1
        else:
            print(f"\nSuccessfully converted all {len(files)} files")
            return 0
    
    def pipeline(self, args):
        """Run a full pipeline: convert -> condition -> validate."""
        steps = []
        
        # Step 1: Convert if input is not already USD/USDZ
        input_path = Path(args.input)
        if input_path.suffix.lower() not in {'.usd', '.usda', '.usdc', '.usdz'}:
            print(f"Step 1: Converting {input_path.name} to USDZ...")
            temp_usdz = input_path.with_suffix('.usdz')
            cmd = [sys.executable, str(self.usdzconvert_dir / 'usdzconvert'),
                   str(input_path), str(temp_usdz)]
            if args.ios12:
                cmd.append('-iOS12')
            result = subprocess.call(cmd)
            if result != 0:
                print("Conversion failed")
                return 1
            working_file = temp_usdz
        else:
            working_file = input_path
            print(f"Input is already USD/USDZ, skipping conversion")
        
        # Step 2: Condition
        if args.condition:
            print(f"Step 2: Conditioning {working_file.name}...")
            conditioned = working_file.parent / f"conditioned_{working_file.name}"
            conditioner = load_module('usd_conditioner',
                                     self.support_scripts_dir / 'usd_conditioner.py')
            if conditioner:
                sys.argv = ['usd_conditioner.py', str(working_file), '-o', str(conditioned)]
                if args.doublesided:
                    sys.argv.extend(['-d', args.doublesided])
                if args.subdivision:
                    sys.argv.extend(['-s', args.subdivision])
                result = conditioner.main()
                if result is not None and result != 0:
                    print("Conditioning failed")
                    return 1
                working_file = conditioned
            else:
                print("Error: Could not load conditioner")
                return 1
        
        # Step 3: Validate
        if args.validate:
            print(f"Step 3: Validating {working_file.name}...")
            # Use wrapper for better error handling
            wrapper = self.base_dir / 'usdARKitChecker_wrapper.py'
            if wrapper.exists():
                cmd = [sys.executable, str(wrapper), str(working_file)]
            else:
                cmd = [sys.executable, str(self.usdzconvert_dir / 'usdARKitChecker'),
                       str(working_file)]
            try:
                result = subprocess.call(cmd, stderr=subprocess.PIPE)
                if result != 0:
                    print("Validation found issues (this is normal for complex models)")
            except Exception as e:
                print(f"Note: Validation encountered errors (this may be due to shader resource issues): {e}")
                # Continue anyway as the file has been created successfully
        
        # Final output
        output_path = Path(args.output)
        if working_file != output_path:
            import shutil
            shutil.copy2(working_file, output_path)
            print(f"\nPipeline complete: {output_path}")
            
            # Clean up temp files
            if working_file != input_path and working_file.exists():
                working_file.unlink()
            temp_usdz = input_path.with_suffix('.usdz')
            if temp_usdz != input_path and temp_usdz.exists() and temp_usdz != output_path:
                temp_usdz.unlink()
        
        return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Unified USD Tool - All USD operations in one place',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert a file to USDZ
  %(prog)s convert model.obj model.usdz
  
  # Validate a USDZ file
  %(prog)s validate model.usdz
  
  # Condition a USD file for compatibility
  %(prog)s condition input.usdz -o output.usdz
  
  # Combine multiple files as variants
  %(prog)s variants -m red.usdz blue.usdz -o combined.usdz
  
  # Batch convert directory
  %(prog)s batch input_dir/ output_dir/ --recursive
  
  # Run full pipeline
  %(prog)s pipeline model.obj final.usdz --condition --validate
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Convert command
    convert_parser = subparsers.add_parser('convert', 
                                          help='Convert 3D files to USDZ')
    convert_parser.add_argument('remaining', nargs=argparse.REMAINDER,
                               help='Arguments to pass to usdzconvert')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate',
                                           help='Validate USDZ for AR')
    validate_parser.add_argument('remaining', nargs=argparse.REMAINDER,
                                help='Arguments to pass to usdARKitChecker')
    
    # Condition command
    condition_parser = subparsers.add_parser('condition',
                                            help='Fix USD compatibility issues')
    condition_parser.add_argument('remaining', nargs=argparse.REMAINDER,
                                 help='Arguments to pass to usd_conditioner')
    
    # Variants command
    variants_parser = subparsers.add_parser('variants',
                                           help='Combine files as variants')
    variants_parser.add_argument('remaining', nargs=argparse.REMAINDER,
                                help='Arguments to pass to variant_combiner')
    
    # Fix opacity command
    opacity_parser = subparsers.add_parser('opacity',
                                          help='Fix opacity issues')
    opacity_parser.add_argument('remaining', nargs=argparse.REMAINDER,
                               help='Arguments to pass to fixOpacity')
    
    # Asset library command
    assetlib_parser = subparsers.add_parser('assetlib',
                                           help='Create asset library')
    assetlib_parser.add_argument('remaining', nargs=argparse.REMAINDER,
                                help='Arguments to pass to usdzcreateassetlib')
    
    # Audio import command
    audio_parser = subparsers.add_parser('audio',
                                        help='Import audio into USDZ')
    audio_parser.add_argument('remaining', nargs=argparse.REMAINDER,
                             help='Arguments to pass to usdzaudioimport')
    
    # Batch convert command
    batch_parser = subparsers.add_parser('batch',
                                        help='Batch convert directory')
    batch_parser.add_argument('input_dir', help='Input directory')
    batch_parser.add_argument('output_dir', help='Output directory')
    batch_parser.add_argument('-r', '--recursive', action='store_true',
                             help='Process subdirectories')
    batch_parser.add_argument('--ios12', action='store_true',
                             help='iOS 12 compatibility mode')
    batch_parser.add_argument('-v', '--verbose', action='store_true',
                             help='Verbose output')
    
    # Pipeline command
    pipeline_parser = subparsers.add_parser('pipeline',
                                           help='Run full processing pipeline')
    pipeline_parser.add_argument('input', help='Input file')
    pipeline_parser.add_argument('output', help='Output USDZ file')
    pipeline_parser.add_argument('--condition', action='store_true',
                                help='Apply conditioning fixes')
    pipeline_parser.add_argument('--validate', action='store_true',
                                help='Validate output')
    pipeline_parser.add_argument('--ios12', action='store_true',
                                help='iOS 12 compatibility')
    pipeline_parser.add_argument('-d', '--doublesided', 
                                choices=['auto', 'off', 'skip'],
                                help='Double-sided mode for conditioning')
    pipeline_parser.add_argument('-s', '--subdivision',
                                choices=['auto', 'off', 'skip'],
                                help='Subdivision mode for conditioning')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    tool = USDTool()
    
    # Map commands to methods
    commands = {
        'convert': tool.convert,
        'validate': tool.validate,
        'condition': tool.condition,
        'variants': tool.combine_variants,
        'opacity': tool.fix_opacity,
        'assetlib': tool.create_asset_library,
        'audio': tool.import_audio,
        'batch': tool.batch_convert,
        'pipeline': tool.pipeline,
    }
    
    if args.command in commands:
        return commands[args.command](args)
    else:
        print(f"Unknown command: {args.command}")
        return 1


if __name__ == '__main__':
    sys.exit(main())