import os
import re
from extract_functions import *
from common import *

rejects = ""
integer_types = ["u8", "u16", "u32", "u64", "s8", "s16", "s32", "s64", "int"]
number_types = ["f32", "float"]
param_override_build = {}
out_filename = 'src/pc/lua/smlua_functions_autogen.c'
docs_lua_functions = 'docs/lua/functions.md'

in_files = [
    "src/audio/external.h",
    "src/engine/surface_collision.h",
    "src/game/camera.h",
    "src/game/characters.h",
    "src/game/mario_actions_airborne.c",
    "src/game/mario_actions_automatic.c",
    "src/game/mario_actions_cutscene.c",
    "src/game/mario_actions_moving.c",
    "src/game/mario_actions_object.c",
    "src/game/mario_actions_stationary.c",
    "src/game/mario_actions_submerged.c",
    "src/game/mario_step.h",
    "src/game/mario.h",
    "src/game/thread6.c",
    "src/pc/djui/djui_popup.h",
    "src/pc/network/network_utils.h",
    "src/pc/djui/djui_chat_message.h",
    "src/game/interaction.h",
    "src/game/level_info.h",
    "src/game/save_file.h",
    "src/game/sound_init.h",
    "src/pc/djui/djui_gfx_utils.h",
]

override_allowed_functions = {
    "src/audio/external.h":           [ " play_", "fade" ],
    "src/game/camera.h":              [ "set_.*camera_.*shake" ],
    "src/game/thread6.c":             [ "queue_rumble_"],
    "src/pc/djui/djui_popup.h" :      [ "create" ],
    "src/game/save_file.h":           [ "save_file_get_" ],
}

override_disallowed_functions = {
    "src/audio/external.h":                [ " func_" ],
    "src/engine/surface_collision.h":      [ " debug_", "f32_find_wall_collision" ],
    "src/game/mario_actions_airborne.c":   [ "^[us]32 act_.*" ],
    "src/game/mario_actions_automatic.c":  [ "^[us]32 act_.*" ],
    "src/game/mario_actions_cutscene.c":   [ "^[us]32 act_.*", " geo_" ],
    "src/game/mario_actions_moving.c":     [ "^[us]32 act_.*" ],
    "src/game/mario_actions_object.c":     [ "^[us]32 act_.*" ],
    "src/game/mario_actions_stationary.c": [ "^[us]32 act_.*" ],
    "src/game/mario_actions_submerged.c":  [ "^[us]32 act_.*" ],
    "src/game/mario_step.h":               [ " stub_mario_step", "transfer_bully_speed"],
    "src/game/mario.h":                    [ " init_mario" ],
    "src/pc/djui/djui_chat_message.h":     [ "create_from" ],
    "src/game/interaction.h":              [ "process_interactions", "_handle_" ],
    "src/game/sound_init.h":               [ "_loop_", "thread4_", "set_sound_mode" ],
    "src/pc/network/network_utils.h":      [ "network_get_player_text_color[^_]" ],
}

###########################################################

template = """/* THIS FILE IS AUTOGENERATED */
/* SHOULD NOT BE MANUALLY CHANGED */

#include "smlua.h"

$[INCLUDES]

$[FUNCTIONS]

void smlua_bind_functions_autogen(void) {
    lua_State* L = gLuaState;
$[BINDS]
}
"""

###########################################################

param_vec3f_before_call = """
    f32* $[IDENTIFIER] = smlua_get_vec3f_from_buffer();
    $[IDENTIFIER][0] = smlua_get_number_field($[INDEX], "x");
    if (!gSmLuaConvertSuccess) { return 0; }
    $[IDENTIFIER][1] = smlua_get_number_field($[INDEX], "y");
    if (!gSmLuaConvertSuccess) { return 0; }
    $[IDENTIFIER][2] = smlua_get_number_field($[INDEX], "z");
"""

param_vec3f_after_call = """
    smlua_push_number_field($[INDEX], "x", $[IDENTIFIER][0]);
    smlua_push_number_field($[INDEX], "y", $[IDENTIFIER][1]);
    smlua_push_number_field($[INDEX], "z", $[IDENTIFIER][2]);
"""

param_override_build['Vec3f'] = {
    'before': param_vec3f_before_call,
    'after': param_vec3f_after_call
}

param_vec3s_before_call = """
    s16* $[IDENTIFIER] = smlua_get_vec3s_from_buffer();
    $[IDENTIFIER][0] = smlua_get_integer_field($[INDEX], "x");
    if (!gSmLuaConvertSuccess) { return 0; }
    $[IDENTIFIER][1] = smlua_get_integer_field($[INDEX], "y");
    if (!gSmLuaConvertSuccess) { return 0; }
    $[IDENTIFIER][2] = smlua_get_integer_field($[INDEX], "z");
"""

param_vec3s_after_call = """
    smlua_push_integer_field($[INDEX], "x", $[IDENTIFIER][0]);
    smlua_push_integer_field($[INDEX], "y", $[IDENTIFIER][1]);
    smlua_push_integer_field($[INDEX], "z", $[IDENTIFIER][2]);
"""

param_override_build['Vec3s'] = {
    'before': param_vec3s_before_call,
    'after': param_vec3s_after_call
}

############################################################################

total_functions = 0
header_h = ""

def reject_line(line):
    if len(line) == 0:
        return True
    if '(' not in line:
        return True
    if ')' not in line:
        return True
    if ';' not in line:
        return True

def normalize_type(t):
    t = t.strip()
    if ' ' in t:
        parts = t.split(' ', 1)
        t = parts[0] + ' ' + parts[1].replace(' ', '')
    return t

def alter_type(t):
    if t.startswith('enum '):
        return 'int'
    return t


############################################################################

def build_param(param, i):
    ptype = alter_type(param['type'])
    pid = param['identifier']

    if ptype in param_override_build:
        return param_override_build[ptype]['before'].replace('$[IDENTIFIER]', str(pid)).replace('$[INDEX]', str(i))
    elif ptype == 'bool':
        return '    %s %s = smlua_to_boolean(L, %d);\n' % (ptype, pid, i)
    elif ptype in integer_types:
        return '    %s %s = smlua_to_integer(L, %d);\n' % (ptype, pid, i)
    elif ptype in number_types:
        return '    %s %s = smlua_to_number(L, %d);\n' % (ptype, pid, i)
    elif ptype == 'const char*':
        return '    %s %s = smlua_to_string(L, %d);\n' % (ptype, pid, i)
    else:
        lot = translate_type_to_lot(ptype)
        s = '  %s %s = (%s)smlua_to_cobject(L, %d, %s);' % (ptype, pid, ptype, i, lot)

        if '???' in lot:
            s = '//' + s + ' <--- UNIMPLEMENTED'
        else:
            s = '  ' + s

        return s + '\n'

def build_param_after(param, i):
    ptype = param['type']
    pid = param['identifier']

    if ptype in param_override_build:
        return param_override_build[ptype]['after'].replace('$[IDENTIFIER]', str(pid)).replace('$[INDEX]', str(i))
    else:
        return ''

def build_call(function):
    ftype = alter_type(function['type'])
    fid = function['identifier']

    ccall = '%s(%s)' % (fid, ', '.join([x['identifier'] for x in function['params']]))

    if ftype == 'void':
        return '    %s;\n' % ccall

    flot = translate_type_to_lot(ftype)

    lfunc = 'UNIMPLEMENTED -->'
    if ftype in integer_types:
        lfunc = 'lua_pushinteger'
    elif ftype in number_types:
        lfunc = 'lua_pushnumber'
    elif ftype == 'bool':
        lfunc = 'lua_pushboolean'
    elif ftype == 'char*':
        lfunc = 'lua_pushstring'
    elif ftype == 'const char*':
        lfunc = 'lua_pushstring'
    elif '???' not in flot and flot != 'LOT_NONE':
        return '    smlua_push_object(L, %s, %s);\n' % (flot, ccall)

    return '    %s(L, %s);\n' % (lfunc, ccall)

def build_function(function, do_extern):
    s = ''

    if len(function['params']) <= 0:
        s = 'int smlua_func_%s(UNUSED lua_State* L) {\n' % function['identifier']
    else:
        s = 'int smlua_func_%s(lua_State* L) {\n' % function['identifier']

    s += '    if(!smlua_functions_valid_param_count(L, %d)) { return 0; }\n\n' % len(function['params'])

    i = 1
    for param in function['params']:
        s += build_param(param, i)
        s += '    if (!gSmLuaConvertSuccess) { return 0; }\n'
        i += 1
    s += '\n'

    if do_extern:
        s += '    extern %s\n' % function['line']

    s += build_call(function)

    i = 1
    for param in function['params']:
        s += build_param_after(param, i)
        i += 1
    s += '\n'

    s += '    return 1;\n}\n'

    function['implemented'] = 'UNIMPLEMENTED' not in s
    if 'UNIMPLEMENTED' in s:
        s = "/*\n" + s + "*/\n"
    else:
        global total_functions
        total_functions += 1

    return s + "\n"

def build_functions(processed_files):
    s = ''
    for processed_file in processed_files:
        s += gen_comment_header(processed_file['filename'])

        for function in processed_file['functions']:
            s += build_function(function, processed_file['extern'])
    return s

def build_bind(function):
    s = 'smlua_bind_function(L, "%s", smlua_func_%s);' % (function['identifier'], function['identifier'])
    if function['implemented']:
        s = '    ' + s
    else:
        s = '    //' + s + ' <--- UNIMPLEMENTED'
    return s + "\n"

def build_binds(processed_files):
    s = ''
    for processed_file in processed_files:
        s += "\n    // " + processed_file['filename'] + "\n"

        for function in processed_file['functions']:
            s += build_bind(function)
    return s

def build_includes():
    s = ''
    for f in in_files:
        if not f.endswith('.h'):
            continue
        s += '#include "%s"\n' % f
    return s

############################################################################

def process_function(fname, line):
    if fname in override_allowed_functions:
        found_match = False
        for pattern in override_allowed_functions[fname]:
            if re.search(pattern, line) != None:
                found_match = True
                break
        if not found_match:
            return None

    if fname in override_disallowed_functions:
        for pattern in override_disallowed_functions[fname]:
            if re.search(pattern, line) != None:
                return None

    function = {}

    line = line.strip()
    function['line'] = line

    line = line.replace('UNUSED', '')

    match = re.search('[a-zA-Z0-9_]+\(', line)
    function['type'] = normalize_type(line[0:match.span()[0]])
    function['identifier'] = match.group()[0:-1]

    function['params'] = []
    params_str = line.split('(', 1)[1].rsplit(')', 1)[0].strip()
    if len(params_str) == 0 or params_str == 'void':
        pass
    else:
        param_index = 0
        for param_str in params_str.split(','):
            param = {}
            param_str = param_str.strip()
            if param_str.endswith('*') or ' ' not in param_str:
                param['type'] = normalize_type(param_str)
                param['identifier'] = 'arg%d' % param_index
            else:
                match = re.search('[a-zA-Z0-9_\[\]]+$', param_str)
                if match == None:
                    return None
                param['type'] = normalize_type(param_str[0:match.span()[0]])
                param['identifier'] = match.group()

            # override Vec3s/f
            if param['identifier'] == 'pos':
                if param['type'].replace(' ', '') == 'f32*':
                    param['type'] = 'Vec3f'
                if param['type'].replace(' ', '') == 's16*':
                    param['type'] = 'Vec3s'

            function['params'].append(param)
            param_index += 1

    return function

def process_functions(fname, file_str):
    functions = []
    for line in file_str.splitlines():
        if reject_line(line):
            global rejects
            rejects += line + '\n'
            continue
        fn = process_function(fname, line)
        if fn == None:
            continue
        functions.append(fn)

    functions = sorted(functions, key=lambda d: d['identifier'])
    return functions

def process_file(fname):
    processed_file = {}
    processed_file['filename'] = fname.replace('\\', '/').split('/')[-1]
    processed_file['extern'] = fname.endswith('.c')

    extracted_str = extract_functions(fname)
    processed_file['functions'] = process_functions(fname, extracted_str)

    return processed_file

def process_files():
    processed_files = []
    files = sorted(in_files, key=lambda d: d.split('/')[-1])
    for f in files:
        processed_files.append(process_file(f))
    return processed_files

############################################################################

def doc_function_index(processed_files):
    s = '# Supported Functions\n'
    for processed_file in processed_files:
        s += '- %s\n' % processed_file['filename']
        for function in processed_file['functions']:
            if not function['implemented']:
                continue
            s += '   - [%s](#%s)\n' % (function['identifier'], function['identifier'])
        s += '\n<br />\n\n'

    return s

def doc_function(function):
    if not function['implemented']:
        return ''

    fid = function['identifier']
    s = '\n## [%s](#%s)\n' % (fid, fid)

    rtype, rlink = translate_type_to_lua(function['type'])
    param_str = ', '.join([x['identifier'] for x in function['params']])

    s += "\n### Lua Example\n"
    if rtype != None:
        s += "`local %sValue = %s(%s)`\n" % (rtype, fid, param_str)
    else:
        s += "`%s(%s)`\n" % (fid, param_str)

    s += '\n### Parameters\n'
    if len(function['params']) > 0:
        s += '| Field | Type |\n'
        s += '| ----- | ---- |\n'
        for param in function['params']:
            pid = param['identifier']
            ptype = param['type']
            ptype, plink = translate_type_to_lua(ptype)

            if plink:
                s += '| %s | [%s](structs.md#%s) |\n'  % (pid, ptype, ptype)
                continue

            s += '| %s | %s |\n'  % (pid, ptype)

    else:
        s += '- None\n'

    s += '\n### Returns\n'
    if rtype != None:
        if rlink:
            s += '[%s](structs.md#%s)\n' % (rtype, rtype)
        else:
            s += '- %s\n' % rtype
    else:
        s += '- None\n'


    s += '\n### C Prototype\n'
    s += '`%s`\n' % function['line'].strip()

    s += '\n[:arrow_up_small:](#)\n\n<br />\n'

    return s

def doc_functions(functions):
    s = ''
    for function in functions:
        s += doc_function(function)
    return s

def doc_files(processed_files):
    s = '## [:rewind: Lua Reference](lua.md)\n\n'
    s += doc_function_index(processed_files)
    for processed_file in processed_files:
        s += '\n---'
        s += '\n# functions from %s\n\n<br />\n\n' % processed_file['filename']
        s += doc_functions(processed_file['functions'])

    with open(get_path(docs_lua_functions), 'w') as out:
        out.write(s)

############################################################################

def main():
    processed_files = process_files()

    built_functions = build_functions(processed_files)
    built_binds = build_binds(processed_files)
    built_includes = build_includes()

    filename = get_path(out_filename)

    gen = template                                \
        .replace("$[FUNCTIONS]", built_functions) \
        .replace("$[BINDS]", built_binds)         \
        .replace("$[INCLUDES]", built_includes)

    with open(filename, 'w') as out:
        out.write(gen)

    print('REJECTS:\n%s' % rejects)

    doc_files(processed_files)

    global total_functions
    print('Total functions: ' + str(total_functions))

if __name__ == '__main__':
   main()