Formal Specification
####################

``jspr`` is not specifically tied to any specific language, and it is specified
as a DSL that is most importantly:

1. Easy to implement.
2. Easy to write.
3. Easy to read.

The specification is only a few pages seen below. Almost every ecosystem today
has tools for injesting and emitting JSON and YAML documents. Implementing
``jspr`` within a system is merely a matter of implementing the execution
semantics atop that groundwork.

The repository that contains this documentation also contains a reference
implementation and test cases.


.. toctree::

  lang
  sforms
  funcs
