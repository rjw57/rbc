"""
Usage:
    rbc (-h | --help)
    rbc [-c | -s] [-o FILE] [-O LEVEL] [--emit-llvm] <file>...

Options:
    -h, --help      Show a brief usage summary.
    -o=FILE         Write output to FILE. The default is to use the basename of
                    <file> with an appropriate extension appended.
    -O=LEVEL        Set optimisation level from 0 to 3. [default: 1]
    -c              Generate object file output.
    -s              Generate assembly output.

Advanced options:
    --emit-llvm     Emit LLVM bytecode/assembly rather than native code when -c
                    or -s is specified.

"""
import enum
import os
import sys

import docopt

import rbc.compiler

class OptionError(RuntimeError):
    pass

OutputType = enum.Enum('OutputType', 'object asm executable')

class Options(object):
    def __init__(self, opts):
        self.input_files = opts['<file>']
        self.output_file = opts['-o']

        if opts['-c']:
            self.output_type = OutputType.object
        elif opts['-s']:
            self.output_type = OutputType.asm
        else:
            self.output_type = OutputType.executable

        if self.output_type != OutputType.executable and \
                len(self.input_files) > 1:
            raise OptionError('Only one file with -c or -s option')

        self.emit_llvm = opts['--emit-llvm']

        self.opt_level = int(opts['-O'])
        if self.opt_level < 0 or self.opt_level > 3:
            raise OptionError('Optimisation level must be between 0 and 3.')

def compile_object(output_file, source_file, compiler_options, emit_llvm):
    with open(source_file) as fobj:
        source = fobj.read()
    module_asm = rbc.compiler.compile_b_source(source, compiler_options)
    module = rbc.compiler.optimize_module(module_asm, compiler_options)
    module.name = os.path.basename(source_file)
    with open(output_file, 'wb') as fobj:
        if emit_llvm:
            fobj.write(module.as_bitcode())
        else:
            fobj.write(compiler_options.machine.emit_object(module))

def compile_asm(output_file, source_file, compiler_options, emit_llvm):
    with open(source_file) as fobj:
        source = fobj.read()
    module_asm = rbc.compiler.compile_b_source(source, compiler_options)
    module = rbc.compiler.optimize_module(module_asm, compiler_options)
    module.name = os.path.basename(source_file)
    with open(output_file, 'w') as fobj:
        if emit_llvm:
            fobj.write(str(module))
        else:
            fobj.write(compiler_options.machine.emit_assembly(module))

def main():
    """Main entry point for rbc tool."""
    # Parse CLI opts
    opts = Options(docopt.docopt(__doc__))

    compiler_options = rbc.compiler.CompilerOptions()
    compiler_options.opt_level = opts.opt_level

    if opts.output_type == OutputType.executable:
        if opts.output_file is None:
            output_file = 'a.out'
        else:
            output_file = opts.output_file
        rbc.compiler.compile_and_link(
            output_file, opts.input_files, options=compiler_options)
    elif opts.output_type == OutputType.object:
        output_file = opts.output_file
        if output_file is None:
            out_ext = '.bc' if opts.emit_llvm else '.o'
            output_file = os.path.splitext(opts.input_files[0])[0] + out_ext
        compile_object(output_file, opts.input_files[0], compiler_options,
                       emit_llvm=opts.emit_llvm)
    elif opts.output_type == OutputType.asm:
        output_file = opts.output_file
        if output_file is None:
            out_ext = '.ll' if opts.emit_llvm else '.s'
            output_file = os.path.splitext(opts.input_files[0])[0] + out_ext
        compile_asm(output_file, opts.input_files[0], compiler_options,
                    emit_llvm=opts.emit_llvm)
    else:
        raise RuntimeError('Unknown output type')
