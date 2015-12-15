from __future__ import print_function
import contextlib
from future.moves import collections

from llvmlite import ir

# Emitting code from the AST
# ==========================
#
# The LLVM code for the program is emitted after the program has been fully
# parsed. This is required because B functions may refer to functions and
# external variables which have not yet been defined in the program.
#
# LLVM code is emitted within an "emit context". This is some mutable state
# which is used to keep important information on the program and the current
# state of the LLVM code emission.

class EmitContext(object):
    """A context is initialised with an llvm Target and TargetMachine instance.

    """
    def __init__(self, target, machine):
        # Record target and machine
        self.target = target
        self.machine = machine

        # We choose the word type to be an integer with the same size as a
        # pointer to i8. The word size is expressed in bytes
        word_size = ir.IntType(8).as_pointer().get_abi_size(
            self.machine.target_data)

        # Define the word type and bytes-per-word appropriately
        self.word_type = ir.IntType(word_size * 8)
        self.bytes_per_word = word_size

        # Define the type used for constructor function records
        priority_type = ir.IntType(32)
        ctor_func_type = ir.FunctionType(ir.VoidType(), [])
        data_ptr_type = ir.PointerType(ir.IntType(8))
        self.ctor_record_type = ir.LiteralStructType([
            priority_type, ctor_func_type.as_pointer(), data_ptr_type])

        # Initialise context attributes
        self.module = None
        self.global_scope = {}
        self.externals = {}
        self.scope = collections.ChainMap(self.global_scope)
        self.builder = None
        self.string_constants = {}
        self.ctor_records = []

        # Block at end of current switch/which statement
        self.break_block = None

        # LLVM Value of condition in current switch statement
        self.switch_val = None

        # Block which new switch tests should be appended to
        self.switch_block = None

        # Labels are mappings from names to.basic blocks A goto branches to the
        # block. The labels dict is only created within functions.
        self.labels = None

        # Callables which should be called after all code has been emitted
        self.post_emit_hooks = []

        # Flag to indicate when one is within the emitting_code() context.
        self._is_emitting = False

    # There are tasks which must be done to finalise the LLVM module after all
    # code is emitted. Users of the context need not worry about what this
    # finalisation entails but it's important that the finalisation is
    # performed. The emitting_code() method returns a context manager which
    # ensures that the finalisation is performed.

    @contextlib.contextmanager
    def emitting_code(self):
        """A context manager which takes care of any pre- and post-emit tasks.
        (Such as emitting constructor functions.) Only emit code within this
        context.

        """
        assert not self._is_emitting
        assert self.module is None

        if self.module is not None:
            raise RuntimeError('Cannot emit twice using the same EmitContext')

        # Create module for program
        self.module = ir.Module()

        # Set module's triple and data layout from target
        self.module.triple = self.target.triple
        self.module.data_layout = str(self.machine.target_data)

        self._is_emitting = True
        yield
        self._is_emitting = False

        # Create the global variable constructors if necessary
        if len(self.ctor_records) > 0:
            ctor_array_type = ir.ArrayType(
                self.ctor_record_type, len(self.ctor_records))

            var = ir.GlobalVariable(self.module, ctor_array_type,
                                    'llvm.global_ctors')
            var.linkage = 'appending'
            var.initializer = ir.Constant(ctor_array_type, self.ctor_records)

        # Call any post-commit hooks
        for hook in self.post_emit_hooks:
            hook(self)
        self.post_emit_hooks = []

    # Scopes
    # ======
    #
    # Scopes associate names with lvalues. The addresses associated with lvalues
    # never change. "Assigning" to a variable involves writing a new value at
    # the associated address. Variables are simply the lvalues in scopes
    # retrieved by name but the name is only looked up at emit()-time. This is
    # to allow forward-references to in-scope but yet-to-be-declared variables
    # such as global definitions.
    #
    # Scopes are implemented as dict-like objects with string keys and LValue
    # values.

    @contextlib.contextmanager
    def in_child_scope(self):
        """A context manager which switches to a new local scope which is a
        child of the current scope.

        """
        old_scope, self.scope = self.scope, self.scope.new_child()
        yield
        self.scope = old_scope

    # Instruction building
    # ====================
    #
    # LLVM instructions are emitted via a "Instruction Builder". There is only a
    # builder set when there is a block to insert code in. The "builder"
    # attribute should be set to the instruction builder while emitting
    # top-level definitions containing code. If should be None if there is no
    # currently defined point to insert code.

    @contextlib.contextmanager
    def new_function_body(self, entry_block):
        """A context manager which sets values in the context ready for emitting
        a function body. It takes the basic block corresponding to the entry
        point.

        """
        # Create a new scope
        builder = ir.IRBuilder(entry_block)
        old_builder, self.builder = self.builder, builder
        old_labels, self.labels = self.labels, {}
        with self.in_child_scope():
            yield
        self.labels = old_labels
        self.builder = old_builder

    @contextlib.contextmanager
    def setting_break_block(self, block):
        old_block, self.break_block = self.break_block, block
        yield
        self.break_block = old_block

    @contextlib.contextmanager
    def setting_switch_context(self, val, block):
        old_val, self.switch_val = self.switch_val, val
        old_block, self.switch_block = self.switch_block, block
        yield
        self.switch_block = old_block
        self.switch_val = old_val

# Symbol naming
# =============
#
# B allows for global externally visible symbols such as functions. To avoid
# clashes with the C world, we mangle the symbol names. By default the B world
# can't see C and vice versa. This is done by prefixing all B symbols with "b."
# which renders them invalid as C identifiers.

def mangle_symbol_name(name):
    """Mangle an external symbol name for use with B."""
    return 'b.' + name

# Addresses and pointers and words, oh my!
# ========================================
#
# Although B lacks what would today be called a type system (every object is
# of type "word") there is an implicit one in that addresses are assumed to
# be word oriented and thus "address" + "word" should really be "address" +
# (word size * "word") in a byte-oriented architecture. We need to tackle
# this since "a[b]" is syntactic sugar for "*(a + b)" and we don't know at
# emit time which of a and/or b are pointers.  This is further complicated
# by the fact that *neither* of a or b *need* be pointers, "1[2]" is a valid
# vector expression in B, albeit one likely to lead to an invalid memory
# access.
#
# The most straight-forward approach is to have address values be stored
# word-oriented which requires that the alignment of the target be suitable.
# This also necessitates the use of constructor functions and wrappers to
# shuffle between "addresses" and pointers used by LLVM.

def address_to_llvm_ptr(context, address_val, ptr_type):
    """Cast a llvm Value representing a word into a pointer. Performs the
    appropriate conversion from word-oriented addresses to llvm's
    byte-oriented addresses. Requires builder to be not None.

    This method will arrange that

        address_to_llvm_ptr(llvm_ptr_to_address(ptr_val), ptr_type)

    is elided into a simple bitcast. This implies that ptr_val must be word
    aligned. It's the responsibility of the code generator to make sure
    that's the case.

    """
    # If this address came from a pointer, just return the punned pointer.
    if hasattr(address_val, 'b_ptr'):
        return context.builder.bitcast(address_val.b_ptr, ptr_type)

    bpw_const = ir.Constant(context.word_type, context.bytes_per_word)
    byte_address = context.builder.mul(address_val, bpw_const,
                                       flags=['nuw', 'nsw'])
    ptr_val = context.builder.inttoptr(byte_address, ptr_type)

    # HACK: we tag the value with a 'b_address' attribute so that
    # llvm_ptr_to_address() can elide address to pointer followed by pointer
    # to address conversion.
    ptr_val.b_address = address_val

    return ptr_val

def llvm_ptr_to_address(context, ptr_val):
    """Cast a llvm Value representing a byte-oriented pointer to a word
    representing a word-oriented address. Requires builder to be not None.

    This method will arrange that

        llvm_ptr_to_address(address_to_llvm_ptr(address_val, ptr_type))

    is elided to address_val irrespective of ptr_type.

    """
    # If this pointer came from an address, just return the original address
    # value.
    if hasattr(ptr_val, 'b_address'):
        return ptr_val.b_address

    bpw_const = ir.Constant(context.word_type, context.bytes_per_word)
    byte_address = context.builder.ptrtoint(ptr_val, context.word_type)
    address_val = context.builder.udiv(byte_address, bpw_const,
                                       flags=['exact'])

    # HACK: we tag the value with a 'b_ptr' attribute so that
    # address_to_llvm_ptr() can elide pointer to address followed by address
    # to pointer conversion.
    address_val.b_ptr = ptr_val

    return address_val

# Convenience functions
# =====================
#
# Code generation can be quite repetitive. Define some functions which express
# common functionality.

def if_else(context, cond):
    """Convenience wrapper around llvm.ir.Builder.if_else. Takes a single AST
    node representing an expression which should be treated as a condition and
    evaluates that node.

    """
    cond_val = cond.emit(context)
    zero = ir.Constant(context.word_type, 0)
    bool_val = context.builder.icmp_signed('!=', cond_val, zero)
    return context.builder.if_else(bool_val)

def create_constructor(context, priority=0, name_hint=None):
    """Create a function which is called on module load. Functions are called in
    increasing order or priority. (The order of functions with equal priority is
    undefined.)

    """
    ctor_record_type = context.ctor_record_type
    priority_type, ctor_func_ptr_type, data_ptr_type = ctor_record_type.elements

    # Create the constructor function
    if name_hint is None:
        func_name = context.module.get_unique_name('__ctor')
    else:
        func_name = context.module.get_unique_name(
            '__ctor.{}'.format(name_hint))
    func = ir.Function(context.module, ctor_func_ptr_type.pointee, func_name)
    func.linkage = 'private'

    context.ctor_records.append(ir.Constant(ctor_record_type, [
        ir.Constant(priority_type, priority), func,
        ir.Constant(data_ptr_type, None)]))

    return func

def create_aligned_global(module, type_, name):
    """Construct and return an ir.GlobalVariable instance which is guaranteed to
    have a word-aligned pointer. The symbol name is automatically mangled to
    avoid collision with C symbols.

    """
    return _ModifiedGlobalVariable(module, type_, mangle_symbol_name(name))

class _ModifiedGlobalVariable(ir.GlobalVariable):
    """A derived class based on llvm.ir.GlobalVariable with an added attribute,
    "modifiers" which is a sequence of string constants appended to the variable
    declaration separated by commas. If modifiers is of non-zero length, it also
    has a leading comma. This is useful for specifying alignment, etc.

    Note that this class makes use of knowledge of the llvm.ir internals and is
    not a good long-term solution.

    """
    def __init__(self, *args, **kwargs):
        ir.GlobalVariable.__init__(self, *args, **kwargs)
        self.modifiers = []

    def descr(self, buf):
        ir.GlobalVariable.descr(self, buf)
        if len(self.modifiers) > 0:
            print(',', file=buf)
            print(','.join(self.modifiers), file=buf)

