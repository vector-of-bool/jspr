``jspr`` Functions
##################

In ``jspr``, a function is an object which receives some number of runtime
values as operands ("arguments") and evaluates to a new value. A function cannot
effect the caller's environment. A function may have other side effects besides
its return value. Unlike with :doc:`special forms <sforms>`, which receive the
input unevaluated program values, functions receive their operands as evaluated
values.


.. _spec.funcs.core:

Core Functions
***********************

Beyond just implementing the :doc:`language evaluation rules <lang>` and the
:ref:`core special forms <spec.sforms.core>`, a minimum implementation must also
define the core functions.


.. function:: apply(func: Applicable, with: Sequence | KeywordSequence) -> Value

  :param func: An applicable object.
  :param with: A set of arguments to give to other applicable object.

  Applies the arguments given as ``with`` to ``func``.

  :raise: ``['invalid-apply-func', func, with]`` if ``func`` is not
      :ref:`Applicable <spec.lang.applicable>`.
  :raise: ``['invalid-apply-args', func, with]`` if ``with`` is not a sequence
      nor a :ref:`KeywordSequence <spec.lang.kwseq>`

  ::

    - func=: .add
    - args=:seq: [1, [add: 4, and: 9]]
    - - assert:
        - eq: [apply: .func, with: .args]
        - and: 14

  ::

    - func=: 6
    - args=:seq: [3, [add: 1, and: 3]]
    # Raises [invalid-apply-func, 88, [1, 2]]
    - [apply: .func, with: .args]


.. function:: eval(expression: Value, with: Environment) -> Value:
              eval(expression: Value) -> Value:

  :param expression: An arbitrary value to treat as a ``jspr`` program.
  :param with: An environment to use when evaluating. If omitted, creates a new
      empty environment with only the default values.

  :raise: ``['invalid-eval-env', with]`` if ``with`` is not an environment.

  Equivalent to language-level ``eval-expr(expression, with)``. Refer:
  :ref:`spec.lang.eval-expr`.


.. function:: raise(error: Value) -> Never

  :param error: A value to raise

  Generates an error condition and aborts program evaluation at the point of
  invocation, as if by language-level ``raise(error)``. Refer:
  :ref:`raise <spec.lang.raise>`.

  :raise: `error`

  .. note:: This function does not evaluate to a value.


.. function:: eq(arg: Value, and: Value) -> Value:
              neq(arg: Value, and: Value) -> Value:

  :param arg: The left-hand operand.
  :param and: The right-hand operand.

  ``eq`` performs an equality check, and ``neq`` performs an inequality check.

  The following aliases must be defined:

  - ``eq`` - ``=`` and ``==``
  - ``neq`` - ``!=``, ``=!`` [#neq-yaml-note]_, and ``<>``

  ::

    - [assert: [eq, 5, [add, 3, 2]]]

.. function:: add(arg: Value, and: Value) -> Value:
              sub(arg: Value, minus: Value) -> Value:
              mul(arg: Value, by: Value) -> Value:
              floordiv(arg: Value, by: Value) -> Value:
              div(arg: Value, by: Value) -> Value:

  :param a: The left-hand of the ``+`` operation
  :param and: The right-hand of the ``+`` operation

  Implements arithmetic operations. The naming of the right-hand argument is purposeful, to facilitate easier reading when using with KeywordSequence syntax::

    - a=: [mul: 6, by: 7]
    - b=: [add: .a, and: 88]

  In addition, the following aliases must be defined:

  - ``add`` - ``+``
  - ``sub`` - ``-``
  - ``mul`` - ``*``
  - ``floordiv`` - ``//``
  - ``div`` - ``/``

  .. note::

    The names ``div`` and ``floordiv`` come from Python. The result of ``div``
    should not perform integral rounding, whereas ``floordiv`` will *always*
    round-down the result to the nearest integer. e.g.::

      - - assert:
          - eq: [div: 3, by: 2]
          - and: 1.5
      - - assert:
          - eq: [floordiv: 3, by: 2]
          - and: 1


.. function:: join(arg: Sequence, , ...with: Sequence) -> Sequence:
              join(arg: String, , ...with: String) -> String:

  :param arg: The left-hand of the join.
  :param with: The right-hand of the join. Any number of operands may be
      supplied.

  Concatenates strings and sequences. Either all parameters must be sequences,
  or all parameters must be strings.

  :raise: ``["invalid-join", left, right]`` if any operands are not of the same
      type.


.. function:: len(arg: String|Sequence|Map|KeywordSequence) -> Integer:

  :param arg: The string, sequence, map, or keyword sequence to inspect.

  Obtain the number of elements in the given object.

  :raise: ``['invalid-seq', arg]`` if ``arg`` is not one of the noted types

  ::

    - [assert: [eq: 5, and: [len: 'Hello']]]
    - [assert: [eq: 2, and: [len': [1, 2]]]]
    - [assert: [eq: 3, and: [len: {a: b, c: d, e: f}]]]


.. function:: elem(arg: String, at: Integer) -> String
              elem(arg: Sequence, at: Integer) -> Value

  :param arg: The string or sequence to access
  :param at: The zero-based index to obtain

  Obtain the value at the zero-based index ``at`` from the given sequence or
  string. If ``at`` is a negative integral value, ``at`` should be treated as
  ``[add: .at, and: [len: arg]]`` (That is: ``len(arg) - abs(at)``)

  :raise: ``["invalid-elem-index", arg, at]`` if ``at`` is greater than or
      equal to ``[len: arg]`` or ``at`` is less than
      ``[sub: 0, minus: [len: arg]]``

  ::

    - arr=': [foo, bar, baz]
    - [assert: [eq: bar, and: [elem: .arr, at: 1]]]
    - [assert: [eq: baz, and: [elem: .arr, at: 2]]]
    - [assert: [eq: baz, and: [elem: .arr, at: -1]]]
    - [assert: [eq: foo, and: [elem: .arr, at: 0]]]


.. function:: slice(arg: String, ...) -> String
              slice(arg: Sequence, ...) -> Sequence
              slice(arg, from: Integer)
              slice(arg, to: Integer)
              slice(arg, from, to)

  :param arg: A string or sequence.
  :param from: The zero-based start index. If omitted, ``from`` is ``0``.
  :param to: The zero-based end index. If omitted, ``to`` is ``[len: arg]``.

  Obtain a subsequence of the given sequence as the half-open range beginning at
  ``from`` and ending at ``to``. If ``from`` or ``two`` are a negative integer
  ``n``, they should be treated as ``[add, .n, [len: arg]]`` (That is:
  ``len(arg) - abs(n)``

  :raise: ``['invalid-slice-seq', arg]`` if ``arg`` is not a string or sequence.
  :raise: ``['invalid-slice-from', from]`` if ``from`` is not an integer.
  :raise: ``['invalid-slice-to', to]`` if ``to`` is not an integer.
  :raise: ``['invalid-slice-range', seq, from, to]`` if ``[from, to)`` is not a
      valid half-open range of indices into ``seq``

  ::

    - arr=': [1, 2, 3, 4, 5, 6]
    - - assert:
        - eq': [1, 2, 3]
        - and: [slice: .arr, to: 3]
    - - assert:
        - eq': [3, 4, 5, 6]
        - and: [slice: .arr, from: 2]
    - - assert:
        - eq': []
        - and: [slice: .arr, from: -1, to: 5]


.. [#neq-yaml-note]

  The alias ``=!`` for ``neq`` is to work around a YAML limitation that ``!``
  may not be the first character in a bare string scalar.
