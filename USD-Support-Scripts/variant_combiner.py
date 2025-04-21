#! /usr/bin/env python3
"""
Copyright © 2024 Apple Inc. All Rights Reserved.

Disclaimer: IMPORTANT: This Apple software is supplied to you by Apple Inc. ("Apple")
in consideration of your agreement to the following terms, and your use, installation,
modification or redistribution of this Apple software constitutes acceptance of these
terms. If you do not agree with these terms, please do not use, install, modify or
redistribute this Apple software.

In consideration of your agreement to abide by the following terms, and subject to these
terms, Apple grants you a personal, non-exclusive license, under Apple's copyrights in
this original Apple software (the "Apple Software"), to use, reproduce, modify and
redistribute the Apple Software, with or without modifications, in source and/or binary
forms; provided that if you redistribute the Apple Software in its entirety and without
modifications, you must retain this notice and the following text and disclaimers in all
such redistributions of the Apple Software. Neither the name, trademarks, service
marks or logos of Apple Inc. may be used to endorse or promote products derived from
the Apple Software without specific prior written permission from Apple. Except as
expressly stated in this notice, no other rights or licenses, express or implied, are
granted by Apple herein, including but not limited to any patent rights that may be
infringed by your derivative works or by other works in which the Apple Software may be
incorporated.

The Apple Software is provided by Apple on an "AS IS" basis. APPLE MAKES NO
WARRANTIES, EXPRESS OR IMPLIED, INCLUDING WITHOUT LIMITATION THE
IMPLIED WARRANTIES OF NON-INFRINGEMENT, MERCHANTABILITY AND
FITNESS FOR A PARTICULAR PURPOSE, REGARDING THE APPLE SOFTWARE
OR ITS USE AND OPERATION ALONE OR IN COMBINATION WITH YOUR
PRODUCTS.

IN NO EVENT SHALL APPLE BE LIABLE FOR ANY SPECIAL, INDIRECT,
INCIDENTAL OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
OR PROFITS; OR BUSINESS INTERRUPTION) ARISING IN ANY WAY OUT OF THE
USE, REPRODUCTION, MODIFICATION AND/OR DISTRIBUTION OF THE APPLE
SOFTWARE, HOWEVER CAUSED AND WHETHER UNDER THEORY OF
CONTRACT, TORT (INCLUDING NEGLIGENCE), STRICT LIABILITY OR
OTHERWISE, EVEN IF APPLE HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH
DAMAGE.
"""
import argparse
import os
import random
import shutil
import sys
import tempfile
import zipfile
import hashlib
import mmap
from typing import Optional, List, Dict

allowed_exts = (".usd", ".usda", ".usdc", ".usdz")

RED = '\033[31m'
NC = '\033[0m'

if sys.version_info[0] < 3 or sys.version_info[1] < 7:
    print(f"{RED}This script requires Python version 3.7 or above.{NC}")
    sys.exit(1)

try:
    from pxr import Usd, UsdGeom, UsdShade, UsdSkel, Sdf
except ImportError:
    print(
        f"""{RED}USD Conditioner requires USD to be available.
Please make sure your environment is configured properly.

You can get USD from PyPi ( https://pypi.org/project/usd-core/ ) by running this comamnd in your terminal:

        pip3 install usd-core{NC}""", file=sys.stderr)

    if "Xcode" in sys.executable:
        print(f"{RED}It is not recommended to use the Xcode Python Interpreter to install USD. "
              f"Please install Python separately from Xcode.{NC}")

    sys.exit(1)


class ExpandedUSDZ(object):
    """
    A context library for expanding a given usdz file in to separate
    files on disk so that they can be operated on.

    Args:
       source (str): A path to the usdz file
       rezip (bool): Whether you want to rezip the file on closing this context
       destination (str): An optional location to recompress the usdz to. Overwrites the source usd if not given.
       cleanup (bool): Whether you want this context to clean up temporary files after itself
    """

    def __init__(self, source: str, rezip: bool = False, destination: Optional[str] = None, cleanup: bool = True):
        self.source: str = source
        self.path: Optional[str] = None
        self.rezip: bool = rezip
        self.default_layer: Optional[str] = None
        self.default_layer_path: Optional[str] = None
        self.cleanup: bool = cleanup
        self.destination: str = destination or source

    def __enter__(self):
        self.path = tempfile.mkdtemp()

        with zipfile.ZipFile(self.source, "r") as zh:
            zh.extractall(self.path)

            # This is the only way I could find to programmatically find the default layer.
            # The usdz spec says the first file must be a usd and is treated as a default layer.
            # Some apps care about this however usd itself just uses the first found usd
            # So I iterate through the files in order till we find one
            for name in zh.namelist():
                base, ext = os.path.splitext(name)
                if ext.startswith(".usd"):
                    self.default_layer = os.path.basename(name)
                    self.default_layer_path = os.path.join(
                        self.path, self.default_layer
                    )
                    break

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.rezip:
            self._rezip()

        if self.cleanup:
            self._cleanup()

    def _rezip(self):
        with tempfile.NamedTemporaryFile(suffix=".usdz", delete=self.cleanup) as tmp:
            directory_to_usdz(
                self.path,
                tmp.name,
                default_layer=self.default_layer,
            )

            shutil.copy(tmp.name, self.destination)

    def _cleanup(self):
        shutil.rmtree(self.path)


def directory_to_usdz(
        directory: str,
        usdz_path: str,
        default_layer: Optional[str] = None,
):
    """
    Converts a directory path to a usdz file
    Args:
        directory : A path to the directory to convert
        usdz_path : The path to write the usdz file out to
        default_layer : An optional name of the default layer file to use
    """
    paths = []
    for root, dirs, files in os.walk(directory):
        for name in files:
            file_path = os.path.join(root, name)
            paths.append(file_path)

    if not paths:
        return

    default_layer_str = default_layer or ".usd"
    paths.sort(key=lambda x: default_layer_str in x, reverse=True)

    with Usd.ZipFileWriter.CreateNew(usdz_path) as usdz:
        for file_path in paths:
            usdz.AddFile(file_path, os.path.relpath(file_path, directory))


class VariantCombiner:
    def __init__(self, material_variantset_name, animation_variantset_name):
        self.temp_dir = tempfile.mkdtemp()
        self.cleanup_dirs = [self.temp_dir]
        self.resources = {}
        self.base_path = None
        self.stage = None
        self.material_variantset_name = material_variantset_name
        self.animation_variantset_name = animation_variantset_name
        self.default_prim = None

    def load_base(self, file_path: str):
        self.base_path = file_path
        self.stage = self.load(file_path)

        default_prim = self.stage.GetDefaultPrim()
        if not default_prim:
            raise RuntimeError("Could not find a default prim. File is invalid")

        self.default_prim = default_prim

    def load(self, file_path: str):
        base, ext = os.path.splitext(file_path)
        if ext not in allowed_exts:
            raise ValueError(f"Unsupported file: {file_path}")
        if file_path.endswith(".usdz"):
            with ExpandedUSDZ(file_path, cleanup=False) as usdz:
                self.cleanup_dirs.append(usdz.path)
                stage = Usd.Stage.Open(usdz.default_layer_path)

        else:
            stage = Usd.Stage.Open(file_path)

        if not stage:
            raise RuntimeError(f"Could not create stage from {file_path}")

        self.bake_resources(stage)

        layer = stage.Flatten()
        stage = Usd.Stage.Open(layer)
        return stage

    def bake_resources(self, stage):
        # Currently, only handle Shaders for resources.
        for prim in stage.TraverseAll():
            if prim.IsA(UsdShade.Shader):
                shader = UsdShade.Shader(prim)
                for shader_input in shader.GetInputs():
                    if shader_input.GetTypeName() != "asset":
                        continue

                    value = shader_input.Get()
                    if not value:
                        continue

                    resolved_path = value.resolvedPath
                    if not resolved_path:
                        print(f"{RED}Could not find '{resolved_path}' resolved from '{value}' for {stage}.{NC}")
                        continue
                    path = self.copy_resource(resolved_path)
                    shader_input.Set(os.path.basename(path))

    def cleanup(self):
        for path in self.cleanup_dirs:
            path = os.path.abspath(path)
            try:
                shutil.rmtree(path)
            except OSError as e:
                pass

    def __del__(self):
        self.cleanup()

    def copy_resource(self, file_path):

        file_hash = self.get_file_hash(file_path)
        resource = self.resources.get(file_hash)
        if resource:
            return resource

        file_name = os.path.basename(file_path)
        base, ext = os.path.splitext(file_name)
        count = 0
        while os.path.exists(os.path.join(self.temp_dir, file_name)):
            count += 1
            file_name = f"{base}_{count}{ext}"

        target = os.path.join(self.temp_dir, file_name)
        shutil.copy(file_path, target)

        self.resources[file_hash] = target

        return target

    def get_file_hash(self, file_path):
        if not os.path.exists(file_path):
            print(f"{RED}Could not read  {file_path}.{NC}")
            return None
        with open(file_path) as fh, mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ) as file:
            return hashlib.sha256(file).hexdigest()

    def setup_material_variants(self, material_variants):
        if not material_variants:
            return

        vset = self.default_prim.GetVariantSets().AddVariantSet(self.material_variantset_name)

        for file_path, variant_name in material_variants.items():
            vset.AddVariant(variant_name)

            # Handle the active stage differently
            if file_path == self.base_path:
                for prim in self.stage.TraverseAll():
                    rel = prim.GetRelationship("material:binding")
                    if not rel:
                        continue

                    val = rel.GetTargets()
                    bindMaterialAs = rel.GetMetadata("bindMaterialAs")
                    rel.ClearTargets(True)

                    vset.SetVariantSelection(variant_name)
                    with vset.GetVariantEditContext():
                        rel.SetTargets(val)
                        if bindMaterialAs:
                            rel.SetMetadata("bindMaterialAs", bindMaterialAs)
                continue

            material_map = {}
            var_stage = self.load(file_path)

            for prim in var_stage.TraverseAll():
                rel = prim.GetRelationship("material:binding")
                if not rel:
                    continue

                destination_prim = self.stage.GetPrimAtPath(prim.GetPath())
                if not destination_prim:
                    print(f"{RED}Could not find {prim.GetPath()} in {self.base_path}. There is a hierarchy mismatch.{NC}")
                    continue

                bindMaterialAs = rel.GetMetadata("bindMaterialAs")
                targets = rel.GetTargets()
                for i, target in enumerate(targets):
                    if target in material_map:
                        targets[i] = material_map[target]
                        continue

                    target_prim = var_stage.GetPrimAtPath(target)
                    if not target_prim:
                        print(f"{RED}Could not find {target} in {file_path}. A material appears to be missing.{NC}")
                        continue

                    new_path = self.copy_prim(target_prim)
                    targets[i] = new_path

                vset.SetVariantSelection(variant_name)
                with vset.GetVariantEditContext():
                    rel = destination_prim.CreateRelationship("material:binding")
                    rel.SetTargets(targets)
                    if bindMaterialAs:
                        rel.SetMetadata("bindMaterialAs", bindMaterialAs)

        # I assume the first variant provided by the user is their desired default
        vset.SetVariantSelection(list(material_variants.values())[0])

    def setup_animation_variants(self, animation_variants, maximize_timecode=False):
        if not animation_variants:
            return

        vset = self.default_prim.GetVariantSets().AddVariantSet(self.animation_variantset_name)

        start = self.stage.GetStartTimeCode()
        end = self.stage.GetEndTimeCode()

        for file_path, variant_name in animation_variants.items():
            vset.AddVariant(variant_name)

            # Handle the active stage differently
            if file_path == self.base_path:
                for prim in self.stage.TraverseAll():
                    rel = prim.GetRelationship("skel:animationSource")
                    if not rel:
                        continue

                    val = rel.GetTargets()
                    if not val:
                        continue
                    rel.ClearTargets(True)

                    vset.SetVariantSelection(variant_name)
                    with vset.GetVariantEditContext():
                        rel.SetTargets(val)
                continue

            anim_map = {}
            var_stage = self.load(file_path)

            if maximize_timecode:
                start = min(start, var_stage.GetStartTimeCode())
                end = max(end, var_stage.GetEndTimeCode())
            else:
                start = max(start, var_stage.GetStartTimeCode())
                end = min(end, var_stage.GetEndTimeCode())

            for prim in var_stage.TraverseAll():
                rel = prim.GetRelationship("skel:animationSource")
                if not rel:
                    continue

                destination_prim = self.stage.GetPrimAtPath(prim.GetPath())
                if not destination_prim:
                    print(f"{RED}Could not find {prim.GetPath()} in {self.base_path}. There is a hierarchy mismatch.{NC}")
                    continue

                targets = rel.GetTargets()
                for i, target in enumerate(targets):
                    if target in anim_map:
                        targets[i] = anim_map[target]
                        continue

                    target_prim = var_stage.GetPrimAtPath(target)
                    if not target_prim:
                        print(f"{RED}Could not find {target} in {file_path}. An animation appears to be missing.{NC}")
                        continue

                    new_path = self.copy_prim(target_prim)
                    targets[i] = new_path

                vset.SetVariantSelection(variant_name)
                with vset.GetVariantEditContext():
                    rel = destination_prim.CreateRelationship("skel:animationSource")
                    rel.SetTargets(targets)

        vset.SetVariantSelection(list(animation_variants.values())[0])
        self.stage.SetStartTimeCode(start)
        self.stage.SetEndTimeCode(end)

    def export(self, output):
        base, ext = os.path.splitext(os.path.basename(output))
        temp_file_name = f"{base}.usdc"
        temp_file = os.path.join(self.temp_dir, temp_file_name)

        self.stage.GetRootLayer().Export(temp_file)
        directory_to_usdz(self.temp_dir, output, temp_file_name)

    def copy_prim(self, prim):
        path = prim.GetPath()
        name = prim.GetName()

        parent = self.stage.GetPrimAtPath(prim.GetParent().GetPath())
        if not parent:
            parent = self.default_prim

        names = parent.GetChildrenNames()

        count = 0
        new_name = name
        while new_name in names:
            count += 1
            new_name = f"{new_name}_{count}"

        new_path = parent.GetPath().AppendPath(new_name)

        Sdf.CopySpec(
            prim.GetStage().GetRootLayer(),
            path,
            self.stage.GetRootLayer(),
            new_path
        )

        return new_path


def get_variant_to_file_map(source: List[str]) -> Dict[str, str]:
    results = {}
    if not source:
        return results

    count = len(source)
    file_only_mode = None
    for i, item in enumerate(source):
        base, ext = os.path.splitext(item)
        if file_only_mode is None:

            if ext in allowed_exts:
                file_only_mode = True
            elif not ext:
                file_only_mode = False
            else:
                raise ValueError(f"Unsupported file extension: {ext}")

        if file_only_mode:
            filepath = os.path.abspath(item)
            if not os.path.exists(filepath):
                raise IOError(f"Could not find {filepath}")
            results[filepath] = os.path.basename(base)
            continue

        if i % 2:  # Skip any alternate item
            continue

        if i + 1 == count:
            raise RuntimeError(f"{item} has no corresponding file to associate with")

        filepath = os.path.abspath(source[i + 1])
        if not os.path.exists(filepath):
            raise IOError(f"Could not find {filepath}")
        results[filepath] = item

    return results


def main():
    parser = argparse.ArgumentParser(description="Combine multiple USD files into a single USDZ file with variants")
    parser.add_argument("-o", "--output", required=True, help="Output file")
    parser.add_argument("-m", "--material-variants", nargs="*",
                        help="Files to be used for the material variants. If you provide a list of files, the file "
                             "name will be chosen as the variant name. "
                             "You may also provide an alternating list of Name and File.usdz to provide custom names."
                             "This option only supports varying Material bindings.")
    parser.add_argument("-a", "--animation-variants", nargs="*",
                        help="Files to be used for the animation variants. If you provide a list of files, the file "
                             "name will be chosen as the variant name. "
                             "You may also provide an alternating list of Name and File.usdz to provide custom names."
                             "This option only supports varying SkelAnimation bindings.")
    parser.add_argument("--material-variantset-name", default="Material")
    parser.add_argument("--animation-variantset-name", default="Animation")
    parser.add_argument("--timecode-mode", choices=["max", "min"], default="min",
                        help="Sets the resulting stage's timecode to a Maximum (max) of all input variants"
                             "or to a Minimum (min) of all input variants.")

    args = parser.parse_args()
    if not args.output.endswith(".usdz"):
        print(f"{RED}The output file must have a usdz extension{NC}")
        return sys.exit(1)

    material_variants = get_variant_to_file_map(args.material_variants)
    animation_variants = get_variant_to_file_map(args.animation_variants)

    if not (material_variants or animation_variants):
        parser.print_help()
        print(f"{RED}You must provide at least one of --material-variants or --animation-variants{NC}")
        return sys.exit(1)

    combiner = VariantCombiner(args.material_variantset_name, args.animation_variantset_name)

    # Use a random file as the basis to discourage users providing mismatched hierarchies
    base_file = random.choice(list(material_variants.keys()) + list(animation_variants.keys()))
    combiner.load_base(base_file)
    combiner.setup_material_variants(material_variants)
    combiner.setup_animation_variants(animation_variants, maximize_timecode=args.timecode_mode.lower() == "max")

    combiner.export(args.output)


if __name__ == "__main__":
    main()
