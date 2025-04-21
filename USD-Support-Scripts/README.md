# USD Support Scripts

This package contains a collection of USD utilities as Python scripts.
They are used to provide USD files and offer functionality that is described below.

These scripts are provided as is, according to the terms of the included license.

## Overview of Scripts

To use these scripts, you must use Python 3.7 or higher, and OpenUSD built with the Python bindings.
You may get the official USD package for Python from https://pypi.org/project/usd-core/ .

### USD Conditioner

The USD Conditioner helps process USD files that were authored for older versions of USD or RealityKit.
These older files may have had missing metadata or had incorrect assumptions about how they would be represented. 
In those cases, this script will help update and correct the file.

Usage: `python3 usd_conditioner.py input.usdz -o output.usdz`

Options include:

* `-d / --doublesided` : This option changes the double sided attribute on meshes. Options include:
  * `auto` : auto is the default and will set the attribute to off if no value is explicitly authored.
  * `off` : Turns the attribute off, even if it is explicitly authored.
  * `skip` : Does not modify the value.
* `-s / --subdivision` : This option changes the subdivision schema attribute on meshes. Options include:
  * `auto` : auto is the default and will set the attribute to none if no value is explicitly authored.
  * `off` : Turns the attribute to none, even if it is explicitly authored.
  * `skip` : Does not modify the value.
* `--dont-fix-material-binding` : This option turns off the default behaviour where the script will fix prims with missing binding APIs.
* `--dont-fix-skel-binding` : This option turns off the default behaviour where the script will fix prims with missing binding APIs.
* `--dont-fix-nested-shaders`: This option turns off the default behaviour where the script will fix
shader prims that are under other shader prims.

The default options are recommended for most USD files that will be processed.

### Variant Combiner

USD allows multiple representations of an asset to exist within a single USD file as Variants, encapsulated under a Variant Set.
The Variant Combiner allows you to combine multiple USD files into a single file. This simplifies workflows from
content creation tools that do not natively support creating variants.

The script supports adding material and skeleton animation variants.
It is required that the input USD files have matching hierarchies, except materials themselves.

Usage: `python3 -m red.usdz blue.usdz -o output.usdz`

Options include:

* `-m / --material-variants` : A list of input files to use for varying the material binding on prims.
   The name of the file will be used as the
   name of the variant. Optionally, you may alternate name and file to give custom names.
   In the usage example above, this would be `-m Red red.usdz Blue blue.usdz`
* `-a / --animation-variants` : A list of input files to use for varying the skeleton animation binding on prims.
   The name of the file will be used as the
   name of the variant. Optionally, you may alternate name and file to give custom names.
* `--material-variantset-name` : The name of the Material Variant Set. By default, it is called Material.
* `--animation-variantset-name` : The name of the Skeleton Animation Variant Set. By default, it is called Animation.
* `--timecode-mode`: Different input files may have longer or shorter timelines. 
   This allows you to choose between the minimum (`min`) or maximum (`max`) of the input files. The default is `min`.


