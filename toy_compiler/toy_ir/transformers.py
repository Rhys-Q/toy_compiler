from toy_compiler.toy_ir.non_ssa_ir import Function, Assign, BinaryOp, Phi, Return, Branch, Jump, BasicBlock


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


def rewrite_constants(func):
    const_env = constant_propagation(func)
    constant_propagation
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
        elif isinstance(term, Branch):
            term.cond = rewrite_value(term.cond, const_env)


def build_def_map(func):
    def_map = {}
    for bb in func.blocks:
        for inst in bb.insts:
            for v in inst.defs():
                def_map[v] = inst
    return def_map


def dce(func):
    def_map = build_def_map(func)

    from collections import deque

    worklist = deque()
    live_insts = set()

    # roots
    for bb in func.blocks:
        if bb.terminator:
            worklist.append(bb.terminator)
            live_insts.add(bb.terminator)

    # propagate
    # 思路就是先将所有terminator加入live_insts，然后从这些inst开始，将所有uses的def_inst加入live_insts
    while worklist:
        inst = worklist.popleft()
        for v in inst.uses():
            if v in def_map:
                def_inst = def_map[v]
                if def_inst not in live_insts:
                    live_insts.add(def_inst)
                    worklist.append(def_inst)

    # sweep
    for bb in func.blocks:
        bb.insts = [inst for inst in bb.insts if inst in live_insts]


def fold_constant_branches(func: Function) -> bool:
    changed = False

    for bb in func.blocks:
        term = bb.terminator
        if isinstance(term, Branch) and isinstance(term.cond, int):
            target = term.true_bb if term.cond else term.false_bb

            # 替换 terminator
            bb.terminator = Jump(target)

            # 修 CFG
            for succ in bb.succs:
                succ.preds.remove(bb)
            bb.succs = [target]
            target.preds.append(bb)

            changed = True

    return changed


def remove_unreachable_blocks(func: Function) -> bool:
    reachable = set()
    worklist = [func.entry]

    while worklist:
        bb = worklist.pop()
        if bb in reachable:
            continue
        reachable.add(bb)
        worklist.extend(bb.succs)

    removed = False
    new_blocks = []

    for bb in func.blocks:
        if bb in reachable:
            new_blocks.append(bb)
        else:
            # 从 preds / succs 里清掉
            for p in bb.preds:
                p.succs.remove(bb)
            for s in bb.succs:
                s.preds.remove(bb)
            removed = True

    func.blocks = new_blocks
    return removed


def has_phi(bb: BasicBlock) -> bool:
    return any(isinstance(inst, Phi) for inst in bb.insts)


def can_merge(A: BasicBlock, B: BasicBlock) -> bool:
    return (
        isinstance(A.terminator, Jump)
        and A.terminator.target is B
        and len(A.succs) == 1
        and len(B.preds) == 1
        and not has_phi(B)
    )


def merge_trivial_blocks(func: Function) -> bool:
    for A in list(func.blocks):
        if not isinstance(A.terminator, Jump):
            continue

        B = A.terminator.target
        if not can_merge(A, B):
            continue

        # 1. 删除 A 的 terminator
        A.terminator = None

        # 2. 拼接 B 的指令
        for inst in B.insts:
            A.insts.append(inst)
        A.terminator = B.terminator

        # 3. 修 CFG
        A.succs = B.succs
        for succ in B.succs:
            succ.preds.remove(B)
            succ.preds.append(A)

        # 4. 删除 B
        func.blocks.remove(B)

        return True  # 一次只合并一个，回到外层循环

    return False


def cleanup_phi_nodes(func: Function) -> bool:
    changed = False

    for bb in func.blocks:
        new_insts = []
        for inst in bb.insts:
            if not isinstance(inst, Phi):
                new_insts.append(inst)
                continue

            # 1. 删除来自不存在 predecessor 的 incoming
            inst.incomings = {p: v for p, v in inst.incomings.items() if p in bb.preds}

            # 2. 只有一个 incoming
            values = list(inst.incomings.values())
            if len(values) == 1:
                new_insts.append(Assign(inst.dst, values[0]))
                changed = True
                continue

            # 3. 所有 incoming 值相同
            if len(set(values)) == 1:
                new_insts.append(Assign(inst.dst, values[0]))
                changed = True
                continue

            new_insts.append(inst)

        bb.insts = new_insts

    return changed


def simplify_cfg(func: Function):

    changed = True

    while changed:

        changed = False

        changed |= fold_constant_branches(func)
        changed |= remove_unreachable_blocks(func)
        changed |= merge_trivial_blocks(func)
        changed |= cleanup_phi_nodes(func)
