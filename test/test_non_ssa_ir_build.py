from toy_compiler.toy_ir.non_ssa_ir import IRBuilder, Function, Assign, Branch, Jump, Return, print_function, BinaryOp
from toy_compiler.toy_ir.ssa import compute_dominator_sets, print_dominators


def test_build_and_ssa():
    func = Function("add")
    entry = func.new_block("entry")
    then = func.new_block("then")
    end = func.new_block("end")

    builder = IRBuilder(func)

    # entry block
    builder.set_block(entry)
    builder.emit(Assign("x", 0))
    builder.emit(Assign("c", 1))  # <- 定义条件
    builder.emit_terminator(Branch("c", then, end))

    # then block
    builder.set_block(then)
    builder.emit(Assign("x", 1))
    builder.emit_terminator(Jump(end))

    # end block
    builder.set_block(end)
    builder.emit(BinaryOp("add", "z", "x", "1"))
    builder.emit_terminator(Return("x"))

    # build cfg
    func.build_cfg()

    print_function(func)

    # calcuate dom
    dom = compute_dominator_sets(func)
    print_dominators(dom)
