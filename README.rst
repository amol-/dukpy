dukpy
=====

Simple JavaScript interpreter for Python::

    import _dukpy
    
    res = _dukpy.eval_string('var x = {"ciao": 5}; x["ciao"] + 3;')
    print(res)
    b'8'

