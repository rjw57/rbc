"""
High-level interface to the B compiler.

"""
import os
import subprocess

import llvmlite.binding as llvm
import pkg_resources
import whichcraft

import rbc.codegen as codegen

from rbc.parser import BParser
from rbc.semantics import BSemantics
from rbc._backport import TemporaryDirectory

# pylint: disable=assignment-from-no-return
_LIBB_C_SOURCE_FILE = pkg_resources.resource_filename(__name__, 'libb.c')
_LIBB_B_SOURCE_FILE = pkg_resources.resource_filename(__name__, 'libb.b')

def _ensure_llvm():
    """Ensure that LLVM has been initialised."""
    if _ensure_llvm.was_initialized:
        return

    llvm.initialize()
    llvm.initialize_native_target()
    llvm.initialize_native_asmprinter()
    _ensure_llvm.was_initialized = True

_ensure_llvm.was_initialized = False


class CompilerOptions(object):
    """There are many options which affect the behaviour of the compiler. They
    are collected into this class for easy transport.

    The target and machine attributes are given default values based on the host
    machine running the compiler. The default optimisation level is 1.

    IMPORTANT: Make sure that LLVM and in particular the native target has been
    initialised via the llvmlite.binding.initialize...() functions before
    constructing an instance of this object.

    Attributes:
        target: The llvm.Target which is the target of compilation.
        machine: The llvm.TargetMachine which is the target of compilation.
        opt_level: The optimisation level from 0 (no optimisation) to 3 (full
                   optimisation.)

    """
    def __init__(self):
        _ensure_llvm()
        self.target = llvm.Target.from_default_triple()
        self.machine = self.target.create_target_machine(codemodel='default')
        self.opt_level = 1

def compile_b_source(source, options):
    """The B front end converts B source code into a LLVM module. No significant
    optimisation is performed.

    Args:
        source (str): B source code as a string
        options (CompilerOptions): compiler options

    Returns:
        A string with the LLVM assembly code for an unoptimised module
        corresponding to the input source.

    """
    # Set parser semantics and go forth and parse.
    program = BParser().parse(source, 'program',
                              semantics=BSemantics(codegen.make_node))

    # Emit LLVM assembly for the correct target.
    module_str = program.emit(options.target, options.machine)

    # Return the string representation of the module.
    return module_str

def optimize_module(module_assembly, options):
    """Verify and optimise the passed LLVM module assembly.

    Args:
        module_assembly (str): LLVM module assembly
        options (CompilerOptions): options for the compiler

    Returns:
        A llvmlite.binding.ModuleRef for the verified and optimised module.

    """
    _ensure_llvm()

    # Parse LLVM module assembly
    module = llvm.parse_assembly(module_assembly)
    module.verify()

    # Create optimiser pass manager
    pass_manager = llvm.ModulePassManager()

    # Populate with target passes
    options.machine.target_data.add_pass(pass_manager)

    # Populate with optimisation passes
    pass_manager_builder = llvm.PassManagerBuilder()
    pass_manager_builder.opt_level = options.opt_level
    pass_manager_builder.populate(pass_manager)

    # Run optimiser
    pass_manager.run(module)

    return module

class CompilationEnvironment(object):
    """
    Detect compiler tools available in the environment.

    Some parts of ``rbc`` call out to external compiler tools. This class
    centralises the automatic discovery of these tools. Custom environments may
    be created by creating an instance of this class and setting attributes
    manually.

    Attributes:
        gcc: path to the GCC compiler binary or None if no GCC present
        cppflags: list of C pre-processor flags
        cflags: list of C compiler flags
        ldflags: list of linker flags

    """
    def __init__(self):
        self.gcc = whichcraft.which('gcc')
        self.cflags = ['-std=gnu99']
        self.cppflags = []
        self.ldflags = []

    def compile_c_source(self, obj_filename, c_filename):
        subprocess.check_call(
            [self.gcc] + self.cppflags + self.cflags +
            ['-c', '-o', obj_filename, c_filename])

    def link_objects(self, output_filename, obj_filenames):
        subprocess.check_call(
            [self.gcc] + self.ldflags +
            ['-o', output_filename] + obj_filenames)

_DEFAULT_ENVIRONMENT = CompilationEnvironment()

def compile_b_to_native_object(obj_filename, b_filename, options):
    """Convenience function to compile an on-disk B file to a native object.

    Args:
        obj_filename (str): file to write object code to
        b_filename (str): file containing B source
        options (CompilerOptions): compiler options to use

    """
    with open(b_filename) as fobj:
        source = fobj.read()

    module_asm = compile_b_source(source, options)
    module = optimize_module(module_asm, options)
    module.name = os.path.basename(b_filename)

    with open(obj_filename, 'wb') as fobj:
        fobj.write(options.machine.emit_object(module))

def compile_and_link(output, source_files, options=None,
                     env=_DEFAULT_ENVIRONMENT):
    """Compile and link source files into an output file. Uses GCC for the heavy
    lifting. This will implicitly link in the B standard library.

    Input files may be anything GCC accepts along with B source files.

    If no compiler options are used, a new CompilerOptions object is
    constructed.

    Note: the passed compiler options *only* affect the B compiler. Use the
    'cflags', 'ldflags' and 'cppflags' attributes in the compilation
    environment.

    Args:
        output (str): path to output file
        source_files (sequence): paths of input files
        options (CompilerOptions): compiler options
        env (CompilationEnvironment): specify custom compiler environment

    """
    options = options if options is not None else CompilerOptions()

    with TemporaryDirectory() as tmp_dir:
        libb1_obj = os.path.join(tmp_dir, 'libb1.o')
        env.compile_c_source(libb1_obj, _LIBB_C_SOURCE_FILE)
        libb2_obj = os.path.join(tmp_dir, 'libb2.o')
        compile_b_to_native_object(libb2_obj, _LIBB_B_SOURCE_FILE, options)
        compiled_source_files = [libb1_obj, libb2_obj]
        for file_idx, source_file in enumerate(source_files):
            out_file = os.path.join(tmp_dir, 'tmp{}.o'.format(file_idx))
            _, ext = os.path.splitext(source_file)
            if ext == '.b':
                compile_b_to_native_object(out_file, source_file, options)
                compiled_source_files.append(out_file)
            elif ext == '.c':
                env.compile_c_source(out_file, source_file)
                compiled_source_files.append(out_file)
            else:
                compiled_source_files.append(source_file)
        env.link_objects(output, compiled_source_files)
