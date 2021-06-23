Introduction
############

``jspr`` (or JSPR) (pronounced "jasper"), is a programming language whose AST
can be directly represented as a JSON document. ``jspr`` code can be written as
a JSON document, but can also be represented in other data formats such as YAML
and JSON5. Many aspects of ``jspr`` are designed specifically to appear
especially clean when written in YAML documents.

Why??
=====

It's become somewhat clear that YAML is a poor programming language
[#earthly-yaml-fn]_ and yet countless projects and systems continually reinvent
half-baked domain-specific programming languages on top of YAML. Even worse are
templating engines designed to emit YAML, but which are completely unaware of
the YAML/JSON object model.

One could attribute this to Greenspun's Tenth Rule [#greenspun]_, although the
resulting YAML-embedded DLSs are often markedly uglier and less featureful than
Common Lisp.

So let's just cut to the chase and build a half-decent programming language
instead of "accidentally" doing it over and over again (poorly): ``jspr`` is a
Lisp-inspired programming language whose programs are entirely representable
within a JSON/YAML document.


What does it look like? "*Show me the code!*"
=============================================

Here is a very simple ``jspr`` program written as a YAML document::

  - user-home=: [if: .isWindows, then: [getenv: Profile], else: [getenv: HOME]]
  - [print: 'User home directory is "{}"', with`: [.user-home]]

This will simply print the directory path of the user's home directory, which is
obtained from either the ``Profile`` or the ``HOME`` environment variable,
depending on the value of the ``is-windows`` JSPR variable.

The above makes use of several syntactic-sugar elements of ``jspr`` that make
the program more concise and readable, especially in YAML, and especially with
good syntax highlighting. The equivalent document in raw JSON is somewhat
uglier::

  [
    {"user-home=": [
      {"if": ".isWindows"},
      {"then": [{"getenv": "Profile"}]},
      {"else": [{"getenv": "HOME"}]}
    ]},
    [{"print": "User home directory is \"{}\""}, {"with`": [".user-home"]}]
  ]

Using ``jspr``'s Lisp-like array-based syntax can result in a JSON document with
less punctuation noise::

  [
    ["let", "user-home",
      ["if", ".isWindows",
        ["getenv", "Profile"],
        ["getenv", "HOME"]
      ]
    ],
    ["print", "User home directory is \"{}\"",
        ["list", [".user-home"]]]
  ]

From the above, it may be easier to see how ``jspr`` is "Lisp-inspired."
Unfortunately, because everything is just JSON strings, most syntax highlighting
benefits disappear.


Is This a Joke?
===============

No, but it's not too serious either.

There have been efforts to address the "code-as-config" and "config-as-code"
overlap before, (Such as Dhall_ and Pulumi_) and they are likely much more
thorough and specialized than ``jspr``, but ``jspr`` is the first serious
attempt (of which this author is aware) to define a formal, generalized,
fully-featured programming language embeddable within arbitrary JSON documents.

.. _Dhall: https://dhall-lang.org/#

.. _Pulumi: https://www.pulumi.com/

This project is also somewhat useful for the author in exploring the design
space of embeddable programming languages and exploring the limits and
capabilities of the host language (JSON and YAML).

.. Footnotes

.. [#earthly-yaml-fn]

  The developers of *Earthly* have a good write-up exploring the downsides and
  oddities associated with "accidental" programming languages embedded in YAML
  documents. `Refer to their write-up here`__.

.. __: https://earthly.dev/blog/intercal-yaml-and-other-horrible-programming-languages/

.. [#greenspun]

  A humorous aphorism stating that "Any sufficiently complicated [...] program contains an ad-hoc, informally-specified, bug-ridden, slow implementation of half of Common Lisp. (Refer__)

.. __: https://wiki.c2.com/?GreenspunsTenthRuleOfProgramming