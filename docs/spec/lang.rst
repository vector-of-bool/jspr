The Language: Expression Evaluation Semantics
#############################################

``jspr`` is an expression-oriented language, and the result of any expression
can be obtained by following the formal rules of evaluation. ``jspr`` is not
bound to any particular host programming language, on-disk file format, or
textual representation, and any conforming implementation should produce the
same result for the same given inputs.


Basic Definitions
=================

Throughout this document, and in those that follow, the following terms are
used:

*Value*
  Any JSON-compatible value: A string, a number, a boolean (or "bool"), a null,
  a sequence or a map (A map of key-value pairs with unspecified ordering).
  Additional runtime value types may be supported by the implementation, but do
  not have special execution semantics in a ``jspr`` interpreter.

*Sequence*
  A "sequence" is an ordered sequence of values. (Synonymous with a JSON
  "array" or Python "list".)

*Map*
  Because "object" is a very overloaded term, JSON-like objects will often be
  referred to as "maps," which is their name in YAML and the same name used
  within a plethora of other programming languages. A map is a collection of
  key-value pairs. The order of key-value pairs within an individual map is
  unspecified. At minimum, a ``jspr`` implementation is only required to support
  string keys, and duplicate keys are not required to be supported.

*Environment*
  An "Environment" is a mutable set of named values available as ambient state.
  The contents of the initial Environment must include the core ``jspr`` special
  forms. Additional content is implementation-defined. An Environment may or may
  not have a *parent* Environment.

.. _spec.lang.kwseq:

*KeywordSequence*
  A "keyword sequence" or ``KeywordSequence`` is a mutable ordered sequence of
  key-value pairs. All keys are strings, and the value is an arbitrary value.
  Unlike a map, a keyword sequence is an ordered sequence and may contain
  duplicate keys.

.. _spec.lang.applicable:

*Applicable*
  An "Applicable" entity is anything that accepts a set of arguments and
  evaluates to a new value. During evaluation, an applicable *may* manipulate
  the current Environment.

*Special form*
  A "special form" is an Applicable entity that receives unevaluated operands.

*Function*
  A "function" is an Applicable that receives already-evaluated operands.

Evaluation begins by passing the root value ``val`` and an initial environment
``env`` to *either* ``eval-do-seq(val, env)`` or ``eval-expr(val, env)``:

- It is up to the particular implementation to decide and document how the
  initial evaluation state is chosen.
- The initial environment ``env`` must (at minimum) contain definitions for all
  of the core ``jspr`` special forms. Refer: :doc:`sforms`. Additional contents
  are implementation-defined.

Throughout this documentation, Python's sequence-slicing syntax is used. As a
quick-reference, for a sequence ``s``:

- Indices are zero-based. ``s[0]`` is the first element.
- ``s[N]`` refers to the ``N``-th element of ``s``.
- ``s[N:]`` refers to the subsequence of ``s`` that begins at the ``N``-th
  element and continues until the end.
- ``s[:N]`` refers to the subsequence of ``s`` beginning at the start of ``s``
  and continuing until the ``N``-th element (not including the ``N``-th
  element).
- ``s[-N]`` (when ``N`` is negative) is equivalent to ``s[M]`` where ``M`` is
  ``length-of(s) - N``. That is: negative indices access from the end of the
  sequence. ``s[-1]`` refers to the last element of ``s``. ``s[-2]`` refers to
  the second-to-last element, etc.


Recursive Value Evaluation
==========================

This section expresses plain-English pseudocode that describes how a
JSON-compatible input value should be "evaluated" to new result value.


.. _spec.lang.eval-expr:

``eval-expr(val: Value, env: Environment)``
-------------------------------------------

1. If ``val`` is a string, return ``eval-expr-string(val, env)``.
2. Otherwise, if ``val`` is a sequence, return ``eval-expr-seq(val, env)``.
3. Otherwise, if ``val`` is a map, return ``eval-expr-map(val, env)``.
4. Otherwise, return ``val``


``eval-expr-string(string: String, env: Environment)``
------------------------------------------------------

#. If the string ``string`` begins with an ASCII period "``.``":

  #. Let ``varname`` be ``string[1:]``.
  #. Return ``env-lookup(env, varname)``

#. Otherwise, return ``string``


.. _spec.lang.env-lookup:

``env-lookup(env: Environment, key: String)``
---------------------------------------------

#. If a value named ``key`` is defined in ``env``, return that value.
#. Otherwise, if ``env`` has a parent environment ``par``, return
   ``env-lookup(par, key)``
#. Otherwise, do ``raise(["env-name-error", key])``. (This does not return a
   value.)


``eval-expr-seq(seq: Sequence, env: Environment)``
--------------------------------------------------

#. If ``seq`` is an empty sequence, return ``seq``
#. Let ``head`` be ``seq[0]``.
#. Let ``tail`` be ``seq[1:]``.
#. If ``head`` is a string:

   #. Let ``func`` be the result of ``env-lookup(env, head)``
   #. Return ``apply-seq(func, tail, env)``

#. If ``head`` is a map with a single key-value pair:

   #. If any element of ``tail`` is not a map, do
      ``raise(["invalid-kw-apply", seq])``
   #. Return ``apply-kwseq(seq, env)``

#. Let ``func`` be the result of ``eval-expr(head, env)``
#. Return ``apply-seq(func, tail, env)``


``eval-expr-map(m: Map, env: Environment)``
-------------------------------------------

#. If ``m`` is not a map containing a single element, do
   ``raise(['invalid-bare-map', m])``.
#. Let ``(key, expr)`` be the single key-value pair in ``m``
#. Let ``(nkey, nval)`` be pair result of ``normalize-pair(key, expr)``
#. If ``nkey`` starts with an ASCII hyphen "``-``":

   #. Create a new empty map ``m2``
   #. Set the value named by ``nkey[1:]`` in ``m2`` to ``nval``
   #. Create a sequence ``seq`` with a single element of value ``m2``
   #. Return ``eval-expr-seq(seq, env)``

#. Otherwise, if ``nkey`` does not end with an ASCII equal-sign "``=``",
   do ``raise(['invalid-bare-map', m])``
#. Otherwise, Let ``varname`` be `nkey[:-1]``.
#. Let ``varvalue`` be the result of ``eval-expr(nval, env)``
#. Define the value named by ``varname`` within ``env`` to be ``varvalue``.
#. Return ``varvalue``.


.. _spec.lang.eval-do-seq:

``eval-do-seq(seq: Sequence, outer_env: Environment)``
------------------------------------------------------

#. Let ``ret`` be ``null``
#. Let ``env`` be a new child environment of ``outer_env``.
#. For each ``expr`` in ``seq``, in order:

   #. Update the value of ``ret`` to be ``eval-expr(expr, env)``

#. Return the final value of ``ret``


.. _spec.lang.raise:

``raise(value: Value)``
-----------------------

Abort evaluation and signal a failure that contains the contents of `value`.
This expression does not return a value.


``apply-seq(func: Function, args: Sequence, env: Environment)``
---------------------------------------------------------------

1. Return ``do-apply(func, args, env)``


``apply-kwseq(args: Sequence, env: Environment)``
-------------------------------------------------

#. If ``args`` is empty, or if the first element of ``args`` is not a map with a
   single key-value pair, or any element of ``args`` is not a map, do
   ``raise(["invalid-kw-apply", args])``.
#. Otherwise, let ``norm-kws`` be a new ``KeywordSequence``.
#. Let ``pair-iter`` be an iterator that yields the key-value pairs of each map
   element in ``args`` in the order that those maps appear in ``args``. For
   each map element of ``args``, the order of the key-value pairs yielded by
   ``pair-iter`` from within that individual map is unspecified.
#. For each ``(key, expr)`` pair that is generated from ``pair-iter``, in order:

   #. Let ``pair-norm`` be the result of ``normalize-pair(key, expr)``
   #. Append ``pair-norm`` to ``norm-kws``

#. Let ``fn-key`` be the first element of the first pair in ``norm-kws``. This
   should be a string.
#. Let ``func`` be the result of ``env-lookup(env, fn-key)``.
#. If ``func`` is not a closure, special form, or implementation-defined
   applicable object, do ``raise(["invalid-apply", func, args])``
#. Return ``do-apply(func, norm-kws, env)``


``normalize-pair(key: String, value: Value)``
---------------------------------------------

#. If ``key`` contains an ASCII colon "``:``":

   #. Let ``N`` be the zero-based index of the first ``:`` in ``key``
   #. Let ``nkey`` be ``key[:N]``
   #. Let ``ntail`` be ``key[N+1:]``
   #. Let ``nvalue`` be ``normalize-pair(ntail, value)``
   #. If ``key`` ends with any non-alphanumeric character other than
      an ASCII equals ``=``, do ``raise(['invalid-key-suffix', nkey, nvalue])``
   #. Otherwise, return the pair ``(nkey, nvalue)``

#. If ``key`` ends with a single-quote ``'``:

   #. Let ``qval`` be ``["quote", value]``
   #. Return the pair ``(key[:-1], qval)``

#. If ``key`` ends with any non-alphanumeric character other than
   an ASCII equals ``=``, do ``raise(['invalid-key-suffix', key, value])``
#. Otherwise, return the pair ``(key, value)``


``do-apply(func: Applicable, args: Sequence | KeywordSequence, env: Environment)``
----------------------------------------------------------------------------------

#. If ``func`` is a special form ``sf``, return ``sf(args, env)``
#. Otherwise, if ``func`` is an implementation-defined function, return the
   implementation-defined evaluation of ``func`` with ``args`` and ``env``.
#. Otherwise, if ``func`` is **not** a closure object, do
   ``raise(["invalid-apply"], func, args)``
#. Let ``argspec`` be the sequence of string argument names associated with the
   Closure object ``func``.
#. If the length of ``argspec`` is not the same as the length of ``args``, do
   ``raise(["invalid-apply-args", func, argspec, args])``
#. Otherwise, let ``apl-args`` be the sequence result of ``eval-args(args, env)``
#. Let ``apl-env`` be a new empty Environment with a parent of the environment
   associated with the closure.
#. Do ``bind-args(apl-env, argspec, apl-args)``
#. Let ``body`` be the body of the ``func`` Closure.
#. Return ``eval-expr(body, apl-env)``


.. _spec.lang.eval-seq:

``eval-seq(seq: Sequence, outer_env: Environment)``
---------------------------------------------------

#. Create a new environment ``env`` that has a parent of ``outer_env``.
#. Let ``vals`` be an sequence of the same length as ``seq``, where the ``N``th
   element of ``vals`` is defined as if by
   ``vals[N] = eval-expr(args[N], env)``. Values are evaluated starting at the
   beginning of ``seq`` followed by evaluating each subsequent element in order.
#. Return ``vals``


.. _spec.lang.eval-map:

``eval-map(m: Map, env: env: Environment)``
-------------------------------------------

#. If ``m`` is not a map, do ``raise(["invalid-map", m])``
#. Let ``subenv`` be a new child environment of ``env``.
#. Let ``rmap`` be an empty map.
#. For each pair ``(key, expr)`` in ``m``:

   #. Let ``(nkey, nexpr)`` be the pair result of ``normalize-pair(key, expr)``
   #. Let ``value`` be the result of ``eval-expr(nexpr, subenv)``
   #. Set the value named by ``nkey`` in ``rmap`` to be ``value``

#. Return ``rmap``


``eval-args(args: Sequence | KeywordSequence, env: Environment)``
-----------------------------------------------------------------

#. If ``args`` is a KeywordSequence, return ``eval-kwseq(args, env)``
#. Otherwise, return ``eval-seq(args, env)``


``eval-kwseq(kwseq: KeywordSequence, env: Environment)``
--------------------------------------------------------

#. Let ``rkwseq`` be an empty KeywordSequence.
#. For each ``(key, expr)`` pair in ``kwseq``:

   #. Let ``value`` be the result of ``eval-expression(expr, env)``
   #. Append ``(key, expr)`` to ``rkwseq``

#. Return ``rkwseq``
