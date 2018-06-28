#!/usr/bin/env python2
# Copyright 2018 The ANGLE Project Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# gen_vk_internal_shaders.py:
#  Code generation for internal Vulkan shaders. Should be run when an intenal
#  shader program is changed, added or removed.

from datetime import date
import os
import subprocess
import sys

out_file_cpp = 'vk_internal_shaders_autogen.cpp'
out_file_h = 'vk_internal_shaders_autogen.h'
out_file_gni = 'vk_internal_shaders_autogen.gni'

# Templates for the generated files:
template_shader_library_cpp = """// GENERATED FILE - DO NOT EDIT.
// Generated by {script_name} using data from {input_file_name}
//
// Copyright {copyright_year} The ANGLE Project Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.
//
// {out_file_name}:
//   Pre-generated shader library for the ANGLE Vulkan back-end.

#include "libANGLE/renderer/vulkan/vk_internal_shaders_autogen.h"

#include "common/debug.h"

namespace rx
{{
namespace vk
{{
namespace priv
{{
namespace
{{
{internal_shader_includes}

constexpr ShaderBlob kShaderBlobs[] = {{
{internal_shader_array_entries}
}};
}}  // anonymous namespace

const ShaderBlob &GetInternalShaderBlob(InternalShaderID shaderID)
{{
    ASSERT(static_cast<size_t>(shaderID) < static_cast<size_t>(InternalShaderID::EnumCount));
    return kShaderBlobs[static_cast<size_t>(shaderID)];
}}
}}  // namespace priv
}}  // namespace vk
}}  // namespace rx
"""

template_shader_library_h = """// GENERATED FILE - DO NOT EDIT.
// Generated by {script_name} using data from {input_file_name}
//
// Copyright {copyright_year} The ANGLE Project Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.
//
// {out_file_name}:
//   Pre-generated shader library for the ANGLE Vulkan back-end.

#ifndef LIBANGLE_RENDERER_VULKAN_VK_INTERNAL_SHADERS_AUTOGEN_H_
#define LIBANGLE_RENDERER_VULKAN_VK_INTERNAL_SHADERS_AUTOGEN_H_

#include <stddef.h>
#include <stdint.h>

#include <utility>

namespace rx
{{
namespace vk
{{
enum class InternalShaderID
{{
{internal_shader_ids}
}};

namespace priv
{{
// This is SPIR-V binary blob and the size.
struct ShaderBlob
{{
    const uint32_t *code;
    size_t codeSize;
}};
const ShaderBlob &GetInternalShaderBlob(InternalShaderID shaderID);
}}  // priv
}}  // namespace vk
}}  // namespace rx

#endif  // LIBANGLE_RENDERER_VULKAN_VK_INTERNAL_SHADERS_AUTOGEN_H_
"""

template_shader_includes_gni = """# GENERATED FILE - DO NOT EDIT.
# Generated by {script_name} using data from {input_file_name}
#
# Copyright {copyright_year} The ANGLE Project Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# {out_file_name}:
#   List of generated shaders for inclusion in ANGLE's build process.

angle_vulkan_internal_shaders = [
{shaders_list}
]
"""

# Gets the constant variable name for a generated shader.
def get_var_name(shader):
    return "k" + os.path.basename(shader).replace(".", "_")

# Gets the internal ID string for a particular shader.
def get_shader_id(shader):
    file = os.path.splitext(os.path.basename(shader))[0]
    return file.replace(".", "_")

# Returns the name of the generated SPIR-V file for a shader.
def get_output_name(shader):
    return os.path.join('shaders', 'gen', os.path.basename(shader) + ".inc")

# Finds a path to GN's out directory
def find_build_path(path):
    out = os.path.join(path, "out")
    if (os.path.isdir(out)):
        for o in os.listdir(out):
            subdir = os.path.join(out, o)
            if os.path.isdir(subdir):
                argsgn = os.path.join(subdir, "args.gn")
                if os.path.isfile(argsgn):
                    return subdir
    else:
        parent = os.path.join(path, "..")
        if (os.path.isdir(parent)):
            return find_build_path(parent)
        else:
            raise Exception("Could not find GN out directory")

# Generates the code for a shader blob array entry.
def gen_shader_blob_entry(shader):
    var_name = get_var_name(os.path.basename(shader))[0:-4]
    return "{%s, %s}" % (var_name, "sizeof(%s)" % var_name)

def slash(s):
    return s.replace('\\', '/')

def gen_shader_include(shader):
    return '#include "libANGLE/renderer/vulkan/%s"' % slash(shader)

# STEP 0: Handle inputs/outputs for run_code_generation.py's auto_script
shaders_dir = os.path.join('shaders', 'src')
if not os.path.isdir(shaders_dir):
    raise Exception("Could not find shaders directory")

input_shaders = sorted([os.path.join(shaders_dir, shader) for shader in os.listdir(shaders_dir)])
output_shaders = sorted([get_output_name(shader) for shader in input_shaders])

outputs = output_shaders + [out_file_cpp, out_file_h]

if len(sys.argv) == 2 and sys.argv[1] == 'inputs':
    print(",".join(input_shaders))
    sys.exit(0)
elif len(sys.argv) == 2 and sys.argv[1] == 'outputs':
    print(",".join(outputs))
    sys.exit(0)

# STEP 1: Call glslang to generate the internal shaders into small .inc files.

# a) Get the path to the glslang binary from the script directory.
build_path = find_build_path(".")
print("Using glslang_validator from '" + build_path + "'")
result = subprocess.call(['ninja', '-C', build_path, 'glslang_validator'])
if result != 0:
    raise Exception("Error building glslang_validator")

glslang_binary = 'glslang_validator'
if os.name == 'nt':
    glslang_binary += '.exe'
glslang_path = os.path.join(build_path, glslang_binary)
if not os.path.isfile(glslang_path):
    raise Exception("Could not find " + glslang_binary)

# b) Iterate over the shaders and call glslang with the right arguments.
for shader_file in input_shaders:
    glslang_args = [
        glslang_path,
        '-V',                                            # Output mode is Vulkan
        '--variable-name', get_var_name(shader_file),    # C-style variable name
        '-o', get_output_name(shader_file),              # Output file
        shader_file,                                     # Input GLSL shader
    ]
    result = subprocess.call(glslang_args)
    if result != 0:
        raise Exception("Error compiling " + shader_file)

# STEP 2: Consolidate the .inc files into an auto-generated cpp/h library.
with open(out_file_cpp, 'w') as outfile:
    includes = "\n".join([gen_shader_include(shader) for shader in output_shaders])
    array_entries = ",\n".join([gen_shader_blob_entry(shader) for shader in output_shaders])
    outcode = template_shader_library_cpp.format(
        script_name = __file__,
        copyright_year = date.today().year,
        out_file_name = out_file_cpp,
        input_file_name = 'shaders/src/*',
        internal_shader_includes = includes,
        internal_shader_array_entries = array_entries)
    outfile.write(outcode)
    outfile.close()

with open(out_file_h, 'w') as outfile:
    ids = ",\n".join([get_shader_id(shader) for shader in output_shaders] + ["EnumCount"])
    outcode = template_shader_library_h.format(
        script_name = __file__,
        copyright_year = date.today().year,
        out_file_name = out_file_h,
        input_file_name = 'shaders/src/*',
        internal_shader_ids = ids)
    outfile.write(outcode)
    outfile.close()

# STEP 3: Create a gni file with the generated files.
with open(out_file_gni, 'w') as outfile:
    outcode = template_shader_includes_gni.format(
        script_name = __file__,
        copyright_year = date.today().year,
        out_file_name = out_file_gni,
        input_file_name = 'shaders/src/*',
        shaders_list = ',\n'.join(['  "' + slash(shader) + '"' for shader in output_shaders]))
    outfile.write(outcode)
    outfile.close()
