# Editorial decisions for the second printing

The owner has authorized small, high-confidence repairs of obvious typewriter,
spelling, and grammatical errors. The aim is to preserve John's meaning and
voice in a readable second printing. This edition need not reproduce every
mechanical error of the 1957 typescript.

The following readings are already present in both `source/manuscript.md` and
`book.pdf`. This review accepts and documents them; it introduces no new changes
to the manuscript or PDF. Physical scan page numbers are used below. The
[review ledger](review.json) retains source crops, coordinates, and hashes.

| Scan page | Typescript | Accepted edition reading | Judgment |
| --- | --- | --- | --- |
| 5 | prophesy | prophecy | High confidence. The sentence requires the noun, a Messianic prediction. *Prophesy* is the verb. |
| 7 | analyse | analyze | Accepted American spelling normalization. *Analyse* is correct British spelling, not a typo. This accepts the existing instance without imposing a new global spelling policy. |
| 11 | basis reality | basic reality | High confidence. *Basic* is the adjective required by this construction, expressing matter as fundamental reality in the account of materialism. *Basis of reality* would also be grammatical, but would require inserting a word; *basic reality* is the minimal repair. |
| 35 | appreciate full | appreciate fully | High confidence. The adverb modifies *appreciate*: to understand or recognize the distinction completely. |
| 37 | Bolsheviki or member of the majority | Bolsheviki or members of the majority | High confidence. The plural *adherents* requires *members*, and the following parallel clause already says *Mensheviki or members of the minority*. |
| 38 | the portend of events | the portent of events | High confidence. *Portend* is a verb; this noun phrase calls for *portent*, the sign or foreshadowing of what is to come. It preserves the wording with a one-letter repair. |
| 52 | reconcilation | reconciliation | High confidence. Missing *i* in the ordinary word for reconciling opposites. |
| 57 | classess | classes | High confidence. An extra final *s*. The intended plural of social class is unambiguous. |
| 61 | key to the riddle of history in his hypothesis | key to the riddle of history is his hypothesis | High confidence. *Is* supplies the missing finite verb and identifies the hypothesis as the key. No change to the account of Toynbee's ideas is needed. |
| 82 | do not compliment each other | do not complement each other | High confidence. The argument concerns compatibility between communism and human nature. *Complement* means fit together or complete one another; *compliment* would mean praise. |
| 92 | seperate | separate | High confidence. Straightforward spelling repair. |
| 119 | charge' d'affaires | chargé d'affaires | Accept as typographic restoration of the French term for the diplomatic representative. The manuscript and book already have the correct accented *é*. There is no dropped letter. |

The initial report mistakenly described the last entry as `charge` becoming
`charg`. Its ASCII-only alignment tokenizer omitted `é` from the actual
manuscript word `chargé`. That diagnosis is withdrawn. The tokenizer now retains
accented letters, and regression tests guard against this truncation. The exact
text comparator continues to distinguish accented and unaccented letters;
acceptance of this specific typographic restoration is recorded here.

For further review, small mechanical repairs must be supported by an exact
passage and recorded individually. Historical facts, dated terminology,
philosophical claims, and stylistic preferences are not grounds for silently
rewriting the text. A valid variant spelling is not automatically an error.
An ambiguous scan reading remains unresolved. Direct quotations receive
separate source review before any proposed correction.

These decisions close the twelve reviewed readings. They do not sign off the
remaining scan pages, the four ambiguous inspections, the uppercase-to-italics
design transform, or the other outstanding audit work.
