"""
Automatic texture detection for OBJ files without MTL files.
Detects textures based on common naming conventions.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional

import usdUtils

class TextureAutoDetector:
    """Detects textures automatically based on filename patterns."""
    
    # Common texture type patterns (case-insensitive)
    TEXTURE_PATTERNS = {
        'diffuseColor': [
            r'.*diffuse.*',
            r'.*albedo.*',
            r'.*color.*',
            r'.*base.*',
            r'.*diff.*',
            r'.*d\..*',  # _d.jpg, _D.png, etc.
        ],
        'normal': [
            r'.*normal.*',
            r'.*norm.*',
            r'.*nrm.*',
            r'.*bump.*',
            r'.*n\..*',  # _n.jpg, _N.png, etc.
        ],
        'roughness': [
            r'.*roughness.*',
            r'.*rough.*',
            r'.*r\..*',  # _r.jpg, _R.png, etc.
        ],
        'metallic': [
            r'.*metallic.*',
            r'.*metal.*',
            r'.*met.*',
            r'.*m\..*',  # _m.jpg, _M.png, etc.
        ],
        'occlusion': [
            r'.*occlusion.*',
            r'.*ao.*',
            r'.*ambient.*',
            r'.*occ.*',
            r'.*o\..*',  # _o.jpg, _O.png, etc.
        ],
        'opacity': [
            r'.*opacity.*',
            r'.*alpha.*',
            r'.*transparent.*',
            r'.*a\..*',  # _a.jpg, _A.png, etc.
        ],
        'emissiveColor': [
            r'.*emissive.*',
            r'.*emission.*',
            r'.*emit.*',
            r'.*glow.*',
            r'.*e\..*',  # _e.jpg, _E.png, etc.
        ]
    }
    
    # Supported image formats
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.tga', '.bmp', '.tiff', '.exr', '.hdr', '.avif'}
    
    def __init__(self, obj_path: str, verbose: bool = False):
        """
        Initialize detector for an OBJ file.
        
        Args:
            obj_path: Path to the OBJ file
            verbose: Enable verbose logging
        """
        self.obj_path = Path(obj_path)
        self.obj_folder = self.obj_path.parent
        self.obj_basename = self.obj_path.stem  # filename without extension
        self.verbose = verbose
        
        # Find all image files in the same folder
        self.image_files = self._find_image_files()
        
    def _find_image_files(self) -> List[Path]:
        """Find all image files in the OBJ's directory."""
        image_files = []
        for ext in self.IMAGE_EXTENSIONS:
            image_files.extend(self.obj_folder.glob(f'*{ext}'))
            image_files.extend(self.obj_folder.glob(f'*{ext.upper()}'))
        return sorted(image_files)
    
    def _match_texture_type(self, filename: str, texture_type: str) -> bool:
        """Check if a filename matches patterns for a specific texture type."""
        patterns = self.TEXTURE_PATTERNS.get(texture_type, [])
        filename_lower = filename.lower()
        
        for pattern in patterns:
            if re.match(pattern, filename_lower):
                return True
        return False
    
    def detect_textures_for_material(self, material_name: str = None) -> Dict[str, str]:
        """
        Detect textures for a specific material or the OBJ file.
        
        Args:
            material_name: Name of the material (optional)
            
        Returns:
            Dictionary mapping texture types to file paths
        """
        detected_textures = {}
        
        # Create search patterns based on material name or OBJ name
        if material_name:
            search_base = material_name.lower()
        else:
            search_base = self.obj_basename.lower()
        
        if self.verbose:
            print(f"  Auto-detecting textures for: {search_base}")
            print(f"  Found {len(self.image_files)} image files in folder")
        
        # For each texture type, find the best matching file
        for texture_type in self.TEXTURE_PATTERNS.keys():
            best_match = self._find_best_match(search_base, texture_type)
            if best_match:
                detected_textures[texture_type] = str(best_match)
                if self.verbose:
                    print(f"    {texture_type}: {best_match.name}")
        
        return detected_textures
    
    def _find_best_match(self, search_base: str, texture_type: str) -> Optional[Path]:
        """Find the best matching texture file for a specific type."""
        candidates = []
        
        for image_file in self.image_files:
            filename = image_file.name.lower()
            
            # Check if this file matches the texture type patterns
            if self._match_texture_type(filename, texture_type):
                # Calculate match score based on how well it matches the search base
                score = self._calculate_match_score(filename, search_base, texture_type)
                candidates.append((score, image_file))
        
        # Return the highest scoring candidate
        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            return candidates[0][1]
        
        return None
    
    def _calculate_match_score(self, filename: str, search_base: str, texture_type: str) -> float:
        """Calculate how well a filename matches the search criteria."""
        score = 0.0
        
        # Higher score if filename contains the search base (material/obj name)
        if search_base in filename:
            score += 10.0
        
        # Higher score for exact pattern matches
        patterns = self.TEXTURE_PATTERNS[texture_type]
        for i, pattern in enumerate(patterns):
            if re.match(pattern, filename):
                # Earlier patterns in the list get higher scores
                score += 5.0 - (i * 0.1)
                break
        
        # Prefer common formats
        if filename.endswith(('.jpg', '.png', '.avif')):
            score += 1.0
        
        # Penalize very generic names without the search base
        if not search_base in filename and any(generic in filename for generic in ['texture', 'image', 'default']):
            score -= 2.0
        
        return score
    
    def create_material_with_textures(self, material_name: str = "autoMaterial") -> usdUtils.Material:
        """
        Create a usdUtils.Material with auto-detected textures.
        
        Args:
            material_name: Name for the material
            
        Returns:
            Material object with textures assigned
        """
        material = usdUtils.Material(material_name)
        detected_textures = self.detect_textures_for_material(material_name)
        
        # Map our texture types to usdUtils input names
        input_mapping = {
            'diffuseColor': usdUtils.InputName.diffuseColor,
            'normal': usdUtils.InputName.normal,
            'roughness': usdUtils.InputName.roughness,
            'metallic': usdUtils.InputName.metallic,
            'occlusion': usdUtils.InputName.occlusion,
            'opacity': usdUtils.InputName.opacity,
            'emissiveColor': usdUtils.InputName.emissiveColor,
        }
        
        # Assign detected textures to material inputs
        for texture_type, texture_path in detected_textures.items():
            if texture_type in input_mapping:
                input_name = input_mapping[texture_type]
                
                # Create relative path for USD
                rel_path = os.path.relpath(texture_path, self.obj_folder)
                
                # Create Map object for the texture
                material.inputs[input_name] = usdUtils.Map(
                    'rgb',  # channels
                    rel_path,  # filename
                    None,  # fallback
                    'st',  # primvar name
                    usdUtils.WrapMode.repeat,  # wrapS
                    usdUtils.WrapMode.repeat   # wrapT
                )
        
        return material


def auto_detect_textures_for_obj(obj_path: str, material_names: List[str] = None, verbose: bool = False) -> Dict[str, usdUtils.Material]:
    """
    Convenience function to auto-detect textures for an OBJ file.
    
    Args:
        obj_path: Path to the OBJ file
        material_names: List of material names found in the OBJ
        verbose: Enable verbose output
        
    Returns:
        Dictionary mapping material names to Material objects with textures
    """
    detector = TextureAutoDetector(obj_path, verbose)
    materials = {}
    
    if material_names:
        # Create materials for each named material
        for mat_name in material_names:
            materials[mat_name] = detector.create_material_with_textures(mat_name)
    else:
        # Create a single default material
        obj_name = Path(obj_path).stem
        materials[obj_name] = detector.create_material_with_textures(obj_name)
    
    return materials