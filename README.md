# `jspr` - JSON Processor


## Why??

It's become somewhat clear that
[YAML is a poor programming language](https://earthly.dev/blog/intercal-yaml-and-other-horrible-programming-languages/),
and yet countless projects and systems continually reinvent half-baked
domain-specific programming languages on top of YAML. Even worse are templating
engines designed to emit YAML, but which are completely unaware of the YAML/JSON
object model.

One could attribute this to
[Greenspun's Tenth Rule](https://wiki.c2.com/?GreenspunsTenthRuleOfProgramming),
although the resulting YAML-embedded DLSs are often markedly uglier and less
featureful than Common Lisp.

So let's just cut to the chase and build a half-decent programming language
instead of "accidentally" doing it over and over again (poorly): `jspr` is a
Lisp-inspired programming language that is entirely representable within a
JSON/YAML document.


## What does it look like? "*Show me the code!*"

Here is a very simple `jspr` program written as a YAML document:

```yaml
- user-home:
  - if: .isWindows
  - then: [getenv: Profile]
  - else: [getenv: HOME]
- [print: 'User home directory is "{}"', with`: [.user-home]]
```

This will simply print the directory path of the user's home directory, which is
obtained from either the `Profile` or the `HOME` environment variable, depending
on the value of `isWindows`.

The above makes use of several syntactic-sugar elements of `jspr` that make the
program more concise and readable in YAML, especially with good syntax
highlighting. The equivalent document in raw JSON is somewhat uglier:

```json
[
  {"user-home=": [
    {"if": ".isWindows"},
    {"then": [{"getenv": "Profile"}]},
    {"else": [{"getenv": "HOME"}]}
  ]},
  [{"print": "User home directory is \"{}\""}, {"with`": [".user-home"]}]
]
```

Using `jspr`'s array-based syntax can result in a JSON document with less
punctuation noise:

```json
[
  ["let", "user-home",
    ["if", ".isWindows",
      ["getenv", "Profile"],
      ["getenv", "HOME"]
    ]
  ],
  ["print", "User home directory is \"{}\"", ["list", [".user-home"]]]
]
```

From the above, it may be easier to see how `jspr` is "Lisp-inspired."
