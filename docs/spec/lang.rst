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
  an array or an object (A map of key-value pairs with unspecified ordering).

*Map*
  Because "object" is a very overloaded term, JSON-like objects will often be
  referred to as "maps," which is their name in YAML and the same name used
  within a plethora of other programming languages. A map is a collection of
  key-value pairs. The order of key-value pairs within an individual map is
  unspecified. Maps in ``jspr`` only use string keys, and a single key may not
  appear twice in a single map.

*List*
  A "list" is an ordered sequence of values. (Synonymous with a JSON "array".)

*Environment*
  An "Environment" is a mutable set of named values available as ambient state.
  The contents of the initial Environment must include the core ``jspr`` special
  forms. Additional content is implementation-defined. An Environment may or may
  not have a *parent* Environment.

.. _spec.lang.kwlist:

*KeywordList*
  A "keyword list" or ``KeywordList`` is a mutable ordered sequence of key-value
  pairs. All keys are strings, and the value is an arbitrary value. Unlike a
  map, a keyword list is an ordered sequence and may contain duplicate keys

.. _spec.lang.applicable:

*Applicable*
  An "Applicable" entity is anything that accepts a list of arguments and evaluates to a new value. During evaluation, the applicable may manipulate
  the current Environment.

*Special form*
  A "special form" is an Applicable entity that receives unevaluated operands.

*Function*
  A "function" is an applicable that receives already-evaluated operands.

Evaluation begins by passing the root value ``val`` and an initial environment
``env`` to *either* ``eval-seq(val, env)`` or ``eval-expr(val, env)``:

- It is up to the particular implementation to decide and document how the
  initial evaluation state is chosen.
- The initial environment ``env`` must (at minimum) contain definitions for all
  of the core ``jspr`` special forms. Refer: :doc:`sforms`.

Throughout this documentation, Python's range-slicing syntax is used. As a
quick-reference, for a string ``s``:

- String indexes are zero-based. ``s[0]`` is the first character.
- ``s[N]`` refers to the ``N``-th character of ``s``.
- ``s[N:]`` refers to the substring of ``s`` that begins at the ``N``-th
  character and continues until the end.
- ``s[:N]`` refers to the substring of ``s`` beginning at the start of ``s`` and
  continuing until the ``N``-th character (not including the ``N``-th
  character).
- ``s[-N]`` (when ``N`` is negative) is equivalent to ``N = len(s) - 1``. That
  is, negative indices access from the end of the string. ``s[-1]`` refers to
  the last character of ``s``. ``s[-2]`` refers to the second-to-last character,
  etc.


Recursive Value Evaluation
==========================

This section expresses plain-English pseudocode that describes how a
JSON-compatible input value should be "evaluated" to new result value.


.. _spec.lang.eval-expr:

``eval-expr(val: Value, env: Environment)``
-------------------------------------------

1. If ``val`` is a string, return ``eval-expr-string(val, env)``.
2. Otherwise, if ``val`` is an array, return ``eval-expr-array(val, env)``.
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


``eval-expr-array(arr: Array, env: Environment)``
-------------------------------------------------

#. If ``arr`` is an empty array, return ``arr``
#. Let ``head`` be the first element of ``arr``.
#. Let ``tail`` be an array from ``arr`` with the first element removed.
#. If ``head`` is a string:

   #. Let ``func`` be the result of ``env-lookup(env, head)``
   #. Return ``apply-array(func, tail, env)``

#. If ``head`` is a map with a single key-value pair:

   #. If any element of ``tail`` is not a map, do
      ``raise(["invalid-kw-apply", arr])``
   #. Return ``apply-kwlist(arr, env)``

#. Let ``func`` be the result of ``eval-expr(head, env)``
#. Return ``apply-array(func, tail, env)``


``eval-expr-map(m: Map, env: Environment)``
-------------------------------------------

#. If ``m`` is not a map containing a single element, do
   ``raise(['invalid-bare-map', m])``.
#. Let ``(key, expr)`` be the single key-value pair in ``m``
#. Let ``(nkey, nval)`` be pair result of ``normalize-pair(key, expr)``
#. If ``nkey`` starts with an ASCII hyphen:
   #. Create a new map ``m2``
   #. Set the value named by ``nkey[1:]`` in ``m2`` to ``nval``
   #. Create an array ``a`` with a single value of ``m2``
   #. Return ``eval-expr-array(a, env)``
#. Otherwise, if ``nkey`` does not end with an ASCII equal-sign "``=``",
   do ``raise(['invalid-bare-map', m])``
#. Otherwise, Let ``varname`` be the string ``nkey`` with the final
   character removed
#. Let ``varvalue`` be the result of ``eval-expr(nval, env)``
#. Define the value named by ``varname`` within ``env`` to be ``varvalue``.
#. Return ``varvalue``.


.. _spec.lang.eval-seq:

``eval-seq(seq: Array, outer_env: Environment)``
------------------------------------------------

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


``apply-array(func: Function, args: Array, env: Environment)``
--------------------------------------------------------------

1. Return ``do-apply(func, args, env)``


``apply-kwlist(args: Array, env: Environment)``
-----------------------------------------------

#. If ``args`` is empty, or if the first element of ``args`` is not a map with a
   single key-value pair, or any element of ``args`` is not a map, do
   ``raise(["invalid-kw-apply", args])``.
#. Otherwise, let ``norm-kws`` be a new ``KeywordList``.
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

#. If ``key`` ends with a single-quote ``'``:

   #. Let ``qval`` be ``["quote", value]``
   #. Return the pair ``(key[:-1], qval)``

#. Otherwise, if ``key`` ends with a backtick/grave character ``\```:

   #. If ``value`` is not an array, do
      ``raise(['invalid-array-quote', key, value])``
   #. Let ``lval`` be ``["list", value]``
   #. Return the pair ``(key[:-1], lval)``

#. Otherwise, if ``key`` ends with an ASCII hyphen ``-``:

   #. If ``value`` is not an array, do
      ``raise(['invalid-do-quote', key, value])``
   #. Let ``dval`` be ``["do", value]``
   #. Return the pair ``(key[:-1], dval)``.

#. Otherwise, if ``key`` ends with an ASCII colon ``:``:

   #. If ``value`` is not a map, do ``raise(['invalid-map-quote', key, value])``
   #. Let ``mval`` be ``["map", value]``
   #. Return the pair ``(key[:-1], mval)``

#. Otherwise, if ``key`` ends with an ASCII equals ``=``, return
   ``(key, value)``.
#. Otherwise, if ``key`` ends with any non-alphanumeric character, do
   ``raise(['invalid-key-suffix', key, value])``
#. Otherwise, return the pair ``(key, value)``


``do-apply(func: Applicable, args: Array | KeywordList, env: Environment)``
---------------------------------------------------------------------------

#. If ``func`` is a special form ``sf``, return ``sf(args, env)``
#. Otherwise, if ``func`` is an implementation-defined function, return the
   implementation-defined evaluation of ``func`` with ``args`` and ``env``.
#. Otherwise, if ``func`` is **not** a closure object, do
   ``raise(["invalid-apply"], func, args)``
#. Let ``argspec`` be the list of string argument names associated with the
   Closure object ``func``.
#. If the length of ``argspec`` is not the same as the length of ``args``, do
   ``raise(["invalid-apply-args", func, argspec, args])``
#. Otherwise, let ``apl-args`` be the array result of ``eval-args(args, env)``
#. Let ``apl-env`` be a new empty Environment with a parent of the environment
   associated with the closure.
#. Do ``bind-args(apl-env, argspec, apl-args)``
#. Let ``body`` be the body of the ``func`` Closure.
#. Return ``eval-expr(body, apl-env)``


.. _spec.lang.eval-array:

``eval-array(arr: Array, outer_env: Environment)``
--------------------------------------------------

#. Create a new environment ``env`` that has a parent of ``outer_env``.
#. Let ``vals`` be an array of the same length as ``arr``, where the ``N``th
   element of ``vals`` is defined as if by
   ``vals[N] = eval-root-expr(args[N], env)``. Values are evaluated starting
   at the beginning of ``arr`` followed by evaluating each subsequent element in
   order.
#. Return ``vals``


.. _spec.lang.eval-map:

``eval-map(m: Map, env: env: Environment)``
-------------------------------------------

#. Let ``rmap`` be an empty map.
#. For each pair ``(key, expr)`` in ``m``:

   #. Let ``(nkey, nexpr)`` be the pair result of ``normalize-pair(key, expr)``
   #. Let ``value`` be the result of ``eval-expr(nexpr, env)``
   #. Set the value named by ``nkey`` in ``rmap`` to be ``value``

#. Return ``rmap``


``eval-args(args: Array | KeywordList, env: Environment)``
----------------------------------------------------------

#. If ``args`` is a KeywordList, return ``eval-kwlist(args, env)``
#. Otherwise, return ``eval-array(args, env)``


``eval-kwlist(kwlist: KeywordList, env: Environment)``
------------------------------------------------------

#. Let ``rkwlist`` be an empty KeywordList.
#. For each ``(key, expr)`` pair in ``kwlist``:

   #. Let ``value`` be the result of ``eval-expression(expr, env)``
   #. Append ``(key, expr)`` to ``rkwlist``

#. Return ``rkwlist``
