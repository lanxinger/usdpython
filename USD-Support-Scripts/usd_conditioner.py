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
import enum
import os
import shutil
import sys
import tempfile
import zipfile
from functools import partial
from typing import Optional

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


class Modes(enum.Enum):
    Auto = "auto"
    Off = "off"
    Skip = "skip"

    def __str__(self):
        return self.value


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


def fix_double_sided_task(prim: Usd.Prim, force_off=False):
    if not prim.IsA(UsdGeom.Gprim):
        return

    gprim = UsdGeom.Gprim(prim)
    doublesided = gprim.GetDoubleSidedAttr()

    is_authored = doublesided.IsAuthored()
    if force_off or not is_authored:
        doublesided.Set(False)


def fix_subdivision_task(prim: Usd.Prim, force_off=False):
    if not prim.IsA(UsdGeom.Mesh):
        return

    mesh = UsdGeom.Mesh(prim)
    subdiv = mesh.GetSubdivisionSchemeAttr()

    is_authored = subdiv.IsAuthored()

    if force_off or not is_authored:
        subdiv.Set("none")


def fix_material_bindings_task(prim: Usd.Prim):
    if prim.HasAPI(UsdShade.MaterialBindingAPI) or not prim.IsA(UsdGeom.Gprim):
        return

    rel = prim.GetRelationship("material:binding")
    if rel:
        UsdShade.MaterialBindingAPI.Apply(prim)


def fix_skel_bindings_task(prim: Usd.Prim, props=None):
    if prim.HasAPI(UsdSkel.BindingAPI):
        return

    for prop in props:
        if prim.HasProperty(prop):
            UsdSkel.BindingAPI.Apply(prim)
            break


def fix_nested_shaders_task(prim: Usd.Prim):
    if not prim.IsA(UsdShade.Shader):
        return

    for childPrim in prim.GetAllChildren():
        if not childPrim.IsA(UsdShade.Shader):
            continue

        # The new shader prim name is just the concatenation of the two existing shader prim names
        newShaderPrimName = f"{prim.GetName()}__{childPrim.GetName()}"

        # Record any inputs on the parent 'Shader' that are connected to the child 'Shader'
        # we do this inspection on the USD stage after composition.
        shader = UsdShade.Shader(prim)
        childShader = UsdShade.Shader(childPrim)
        connsToRemap = []
        for shaderInput in shader.GetInputs():
            if not shaderInput.HasConnectedSource():
                continue
            for conn in shaderInput.GetConnectedSources()[0]:
                srcPath = conn.source.GetPath()
                if srcPath == childPrim.GetPath():
                    connsToRemap.append(shaderInput.GetFullName())

        # Now find all prim specs for the child prim - and attempt to move them to the new name,
        # This should happen in all layers with opinions about the child shader prim
        childPrimSpecs = childPrim.GetPrimStack()
        for childPrimSpec in childPrimSpecs:
            newPath = Sdf.Path(f"{childPrimSpec.path.GetParentPath().GetParentPath()}/{newShaderPrimName}")

            # Copy the child 'Shader' to a new sibling location using the new name
            Sdf.CopySpec(childPrimSpec.layer, childPrimSpec.path, childPrimSpec.layer, newPath)

            # Delete the child 'Shader' prim
            sdfPrim = childPrimSpec.layer.GetPrimAtPath(childPrimSpec.path.GetParentPath())
            del sdfPrim.nameChildren[childPrimSpec.name]

        # Update the connection properties if they were pointing at the old child prim
        primSpecs = prim.GetPrimStack()
        for primSpec in primSpecs:
            for prop in primSpec.properties:
                if prop.name in connsToRemap:
                    newExplicitItems = []
                    for conn in prop.connectionPathList.explicitItems:
                        if conn.GetPrimPath() == childPrim.GetPath():
                            newPath = Sdf.Path(f"{conn.GetPrimPath().GetParentPath().GetParentPath()}/{newShaderPrimName}{conn.elementString}")
                            newExplicitItems.append(newPath)
                        else:
                            newExplicitItems.append(conn)
                    prop.connectionPathList.explicitItems = newExplicitItems


def fix(stage: Usd.Stage,
        doublesided: Modes = Modes.Auto, subdivision: Modes = Modes.Auto,
        fix_material_bindings: bool = True, fix_skeleton_bindings: bool = True,
        fix_nested_shaders: bool = True, ibl_version: Optional[int] = None
        ):
    tasks = []
    if doublesided != Modes.Skip:
        tasks.append(partial(fix_double_sided_task, force_off=doublesided == Modes.Off))
    if subdivision != Modes.Skip:
        tasks.append(partial(fix_subdivision_task, force_off=subdivision == Modes.Off))
    if fix_material_bindings:
        tasks.append(fix_material_bindings_task)
    if fix_skeleton_bindings:
        usdSchemaRegistry = Usd.SchemaRegistry()
        primDef = usdSchemaRegistry.BuildComposedPrimDefinition("",
                                                                ["SkelBindingAPI"])
        props = primDef.GetPropertyNames()
        tasks.append(partial(fix_skel_bindings_task, props=props))
    if fix_nested_shaders:
        tasks.append(fix_nested_shaders_task)

    for prim in stage.TraverseAll():
        for task in tasks:
            task(prim)

    if not ibl_version is None:
        root = stage.GetRootLayer()
        custom_data = root.customLayerData
        custom_data.setdefault("Apple", {})["preferredIblVersion"] = ibl_version
        root.customLayerData = custom_data

def main():
    parser = argparse.ArgumentParser(description="Condition USD files to fix common issues")
    parser.add_argument("file", help="The path to the USD file")
    parser.add_argument("-o", "--output", help="The path to the output file", required=True)
    parser.add_argument("-d", "--doublesided", choices=list(Modes), type=Modes, default=Modes.Auto,
                        help="Corrects double sided values on geometry. Auto will set double sided off if no "
                             "opinion is authored. Off will force it off, and skip will not make any change.")
    parser.add_argument("-s", "--subdivision", choices=list(Modes), type=Modes, default=Modes.Auto,
                        help="Corrects the subdivisionScheme values on geometry. Auto will set subdivisionSchema to none if no "
                             "opinion is authored. Off will force it to none, and skip will not make any change.")

    parser.add_argument("--dont-fix-material-binding", action="store_true",
                        help="Don't apply the MaterialBindingAPI for prims that are missing it but have bound materials.")
    parser.add_argument("--dont-fix-skel-binding", action="store_true",
                        help="Don't apply the SkelBindingAPI for prims that are missing it but have bound a bound Skeleton.")
    parser.add_argument("--dont-fix-nested-shaders", action="store_true",
                        help="Don't relocate Shader prims that are currently inside other Shader prims")
    parser.add_argument("--ibl-version", type=int, choices=[0,1,2,3], help="The IBL version to set. 0 means use the system default.")
    args = parser.parse_args()
    source_file = os.path.abspath(args.file)
    if not os.path.exists(source_file):
        raise IOError(f"{source_file} does not exist")

    source_name, ext = os.path.splitext(args.file)
    _, out_ext = os.path.splitext(args.output)

    output_is_usdz = out_ext == ".usdz"
    if ext in [".usd", ".usda", ".usdc"]:
        if out_ext not in [".usd", ".usda", ".usdc"]:
            raise ValueError("Output extension must be .usd, .usda or .usdc")

        stage = Usd.Stage.Open(source_file)
        fix(stage, doublesided=args.doublesided, subdivision=args.subdivision,
            fix_material_bindings=not args.dont_fix_material_binding,
            fix_skeleton_bindings=not args.dont_fix_skel_binding,
            fix_nested_shaders=not args.dont_fix_nested_shaders,
            ibl_version = args.ibl_version)

        stage.Export(args.output)

    elif ext == ".usdz":
        if not output_is_usdz:
            raise ValueError("Output must be a USDZ file when the input is a USDZ file")

        with ExpandedUSDZ(source_file, rezip=True, destination=args.output, cleanup=True) as expanded_usdz:
            stage = Usd.Stage.Open(expanded_usdz.default_layer_path)
            fix(stage, doublesided=args.doublesided, subdivision=args.subdivision,
                fix_material_bindings=not args.dont_fix_material_binding,
                fix_skeleton_bindings=not args.dont_fix_skel_binding, 
                fix_nested_shaders=not args.dont_fix_nested_shaders,
                ibl_version = args.ibl_version)
            stage.Save()


if __name__ == "__main__":
    main()
