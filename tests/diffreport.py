# -*- coding: utf-8 -*-
import difflib


def report_diff(expected, ans):
    sqm = difflib.SequenceMatcher()
    sqm.set_seq1(ans)
    sqm.set_seq2(expected)

    out = ['DIFFERENCE : RESULT -> EXPECTED']
    for action, sq1s, sq1e, sq2s, sq2e in sqm.get_opcodes():
        out.append(action + ' : ' + repr(ans[sq1s:sq1e]) + ' -> ' + repr(expected[sq2s:sq2e]))
    return '\n'.join(out)