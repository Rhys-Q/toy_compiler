from toy_compiler.toy_ir.non_ssa_ir import Function, Assign, BinaryOp, Phi, Return


def eval_binary(op, a, b):
    if op == "add":
        return a + b
    if op == "sub":
        return a - b
    if op == "mul":
        return a * b
    if op == "div":
        return a // b  # toy
    raise NotImplementedError(op)


def constant_propagation(func: Function):
    const_env = {}

    for bb in func.blocks:
        for inst in bb.insts:
            # ---- Assign ----
            if isinstance(inst, Assign):
                rhs = inst.rhs
                if isinstance(rhs, int):
                    const_env[inst.lhs] = rhs
                elif rhs in const_env:
                    const_env[inst.lhs] = const_env[rhs]

            # ---- BinaryOp ----
            elif isinstance(inst, BinaryOp):
                v1 = inst.src1
                v2 = inst.src2

                if isinstance(v1, int):
                    c1 = v1
                elif v1 in const_env:
                    c1 = const_env[v1]
                else:
                    continue

                if isinstance(v2, int):
                    c2 = v2
                elif v2 in const_env:
                    c2 = const_env[v2]
                else:
                    continue

                res = eval_binary(inst.op, c1, c2)
                const_env[inst.dst] = res

            # ---- Phi ----
            elif isinstance(inst, Phi):
                incoming_vals = []
                for v in inst.incomings.values():
                    if v in const_env:
                        incoming_vals.append(const_env[v])
                    else:
                        break
                else:
                    if len(set(incoming_vals)) == 1:
                        const_env[inst.dst] = incoming_vals[0]

    return const_env


def rewrite_value(v, const_env):
    if isinstance(v, str) and v in const_env:
        return const_env[v]
    return v


def rewrite_constants(func, const_env):
    for bb in func.blocks:
        # rewrite instructions
        new_insts = []

        for inst in bb.insts:
            # ---- Assign ----
            if isinstance(inst, Assign):
                inst.rhs = rewrite_value(inst.rhs, const_env)
                new_insts.append(inst)

            # ---- BinaryOp ----
            elif isinstance(inst, BinaryOp):
                inst.src1 = rewrite_value(inst.src1, const_env)
                inst.src2 = rewrite_value(inst.src2, const_env)

                # constant folding
                if isinstance(inst.src1, int) and isinstance(inst.src2, int):
                    val = eval_binary(inst.op, inst.src1, inst.src2)
                    new_insts.append(Assign(inst.dst, val))
                else:
                    new_insts.append(inst)

            # ---- Phi ----
            elif isinstance(inst, Phi):
                inst.incomings = {pred: rewrite_value(v, const_env) for pred, v in inst.incomings.items()}
                new_insts.append(inst)

            else:
                new_insts.append(inst)

        bb.insts = new_insts

        # ---- rewrite terminator ----
        term = bb.terminator
        if isinstance(term, Return):
            term.ret = rewrite_value(term.ret, const_env)
