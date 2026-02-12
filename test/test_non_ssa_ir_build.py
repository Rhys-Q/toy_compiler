from toy_compiler.toy_ir.non_ssa_ir import IRBuilder, Function, Assign, Branch, Jump, Return, print_function, BinaryOp
from toy_compiler.toy_ir.ssa import (
    compute_dominator_sets,
    print_dominators,
    compute_idom,
    print_idom,
    build_dominator_tree,
    print_dom_tree,
    build_dominance_frontier,
    print_dominance_frontier,
    insert_phi,
    rename_ssa,
)
from toy_compiler.toy_ir.transformers import constant_propagation, rewrite_constants


def build_complex_function():
    func = Function("complex")

    entry = func.new_block("entry")
    A = func.new_block("A")
    split = func.new_block("split")
    B = func.new_block("B")
    C = func.new_block("C")
    D = func.new_block("D")
    end = func.new_block("end")

    builder = IRBuilder(func)

    # entry
    builder.set_block(entry)
    builder.emit(Assign("x", 0))
    builder.emit_terminator(Jump(A))

    # A
    builder.set_block(A)
    builder.emit(Assign("x", 1))
    builder.emit_terminator(Jump(split))

    # split
    builder.set_block(split)
    builder.emit(Assign("c", 1))
    builder.emit_terminator(Branch("c", B, C))

    # B
    builder.set_block(B)
    builder.emit(Assign("x", 2))
    builder.emit_terminator(Jump(D))

    # C
    builder.set_block(C)
    builder.emit(Assign("x", 3))
    builder.emit_terminator(Jump(D))

    # D
    builder.set_block(D)
    builder.emit(BinaryOp("add", "y", "x", 1))
    builder.emit(Assign("z", 1))
    builder.emit(BinaryOp("add", "k", "z", 1))
    builder.emit_terminator(Jump(end))

    # end
    builder.set_block(end)
    builder.emit_terminator(Return("y"))

    func.build_cfg()
    return func


def test_build_and_ssa():
    func = build_complex_function()

    print_function(func)

    # calcuate dom
    dom = compute_dominator_sets(func)
    print_dominators(dom)

    # calcuate idom
    idom = compute_idom(func, dom)
    print_idom(idom)

    # build dom tree
    dom_tree = build_dominator_tree(func, idom)
    print_dom_tree(dom_tree, func.entry)

    # build dominance frontier
    df = build_dominance_frontier(func, idom)
    print_dominance_frontier(df)

    # insert phi
    insert_phi(func, df)

    print_function(func)

    # rename ssa
    rename_ssa(func, dom_tree)
    print_function(func)

    # constant propagation
    const_env = constant_propagation(func)
    print(const_env)

    rewrite_constants(func, const_env)
    print_function(func)
