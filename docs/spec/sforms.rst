``jspr`` Special Forms
######################

Special forms are applicable objects that look "function-like" in the input
``jspr`` document, but implement important core behaviors such as control flow
and Environment access and manipulation. These are described below. Note that
the special forms receive their operands as the direct input ``jspr`` program
expressions before they have been evaluated. Special forms also have access to
the environment of their caller. In the below, the variable ``env``, unless
otherwise specified, refers to the environment that is active where that the
special form was applied.


.. _spec.sforms.core:

Core Special Forms
******************

Beyond just implementing the :doc:`language evaluation rules <lang>`, a minimum
implementation must also define the core special forms.


.. function:: do(seq: Sequence[Value]) -> Value

  :param seq: An array of ``jspr`` expressions.

  Equivalent to ``eval-seq(seq, env)``. Refer: :ref:`eval-seq
  <spec.lang.eval-seq>`

  Evaluates an array of ``jspr`` expressions from ``seq`` in the order that they
  appear in ``seq``. Expressions are evaluated in a new child environment.

  :returns: The evaluation result of the final expression in ``seq``. If ``seq``
    is empty, evaluates to ``null``.

  :raise: ``['invalid-do', seq]`` if ``seq`` is not an array.


.. function:: if(condition: Value, then: Value, else: Value) -> Value:
              if(condition: Value, then: Value) -> Value:

  :param condition: An expression on which we will branch
  :param then: The branch taken if ``cond`` evaluates to ``true``.
  :param else: The branch taken if ``cond`` evaluates to ``false``. If omitted
      by the caller, ``else`` is ``null``.

  Implements basic control flow. First, evaluates ``condition`` to obtain a
  result ``c``. Depending on the result ``c``:

  - If ``c`` is ``true``, evaluates ``then`` and returns the result.
  - If ``c`` is ``false``, evaluates ``else`` and returns the result.
  - Otherwise, ``raise(["invalid-if-condition", c])``.

  :returns: The evaluation result of either ``then`` or ``else``, depending on
      which branch was taken.

  :raise: ``['invalid-condition', <value>]`` if the result of ``condition`` is
      not a boolean value. ``<value>`` should be the value that comes from
      ``condition``.

  .. note::

    We are strict: The result of ``condition`` must be a bool value: Anything
    else is an error.


.. function:: quote(expr: Value) -> Value

  :param expr: The input expression.

  :returns: ``expr`` exactly as given.

  This is used to embed arbitrary data in a ``jspr`` program and ensure it is
  not evaluated.


.. function:: let(name, be) -> Value

  :param name: The name to bind.
  :param be: The value which will be stored.

  :returns: The value that was bound.

  Evaluates ``name`` to a string ``varname``, and evaluates ``be`` into ``varval``. Updates the current environment ``env`` so that the name ``varname`` is defined to be ``varval``. ``let`` returns ``varval``.


.. function:: ref(name) -> Value:

  :param name: The name to look up.

  Evaluates ``name`` to a string ``varname``. Returns ``env-lookup(env, varname)``. Refer: :ref:`env-lookup <spec.lang.env-lookup>`.


.. function:: array(arr: Array) -> Array:

  :param arr: An array of expressions.

  Returns ``eval-array(arr, env)``. Refer:
  :ref:`eval-array <spec.lang.eval-array>`.


.. function:: map(m: Map) -> Map:

  :param m: A map value

  Returns ``eval-map(m, env)``. Refer: :ref:`eval-map <spec.lang.eval-map>`.


.. function:: or(or: Value, or: Value, ...) -> bool

  :param or: An arbitrary number of expressions.

  Takes any number of expressions to evaluate. Expressions are evaluated in
  sequence, and each must return a bool value. When any expression evaluates to
  ``true``, evaluation of the remaining expressions is skipped, and the result
  of the ``or`` becomes ``true``.

  If none of the given expressions evaluate to ``true``, ``or`` evaluates as
  ``false``.

  :raise: If any of the operand expressions evaluates to a non-bool value ``E``
      then: ``raise(['invalid-or-condition', E])``


.. function:: and(and: Value, and: Value, ...) -> bool:

  :param and: An arbitrary number of expression.

  Takes any number of expressions to evaluate. Expressions are evaluated in
  sequence, and each must return a bool value. When any expression evaluates to
  ``false``, evaluation of the remaining expressions is skipped, and the result
  of the ``and`` becomes ``false``.

  If none of the expressions evaluate to ``false``, ``and`` evaluates as
  ``true``.

  :raise: If any operand expression evaluates to a non-bool value ``E``, then:
      ``raise(['invalid-or-condition', e])``


.. function:: assert(expr: Value) -> null:

  :param expr: An expression to evaluate.

  Evaluates ``expr`` to a value ``A``:

  #. If ``A`` is ``true``, returns ``null``
  #. If ``A`` is ``false``, raises ``['assertion-failed', expr, <unspecified>]``
  #. Otherwise, raises ``['invalid-assert-cond', expr, A]``

  .. note::

    The value of ``<unspecified>`` above should be a value based on ``expr``,
    and give some assistance to the programmer in debugging why the assertion
    failed. For example, if ``expr`` is ``["eq", ".a", ".b"]``, it would be
    useful for the user to see the partially-evaluated inner expression with
    ``.a`` and ``.b`` evaluated.

  .. note::

    This is defined as a special form so that the assertion failure message can
    contain the original expression as written by the programmer.
