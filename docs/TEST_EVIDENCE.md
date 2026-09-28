# AwazSetu — Test Evidence

**7/7 passed**

| Suite | Case | Lang | Result | Time | Detail |
|---|---|---|---|---|---|
| langid | hand-pairs | - | PASS |  | 6/6 identified |
| langid | corpus-accuracy | - | PASS |  | 842/920 correct, 69 unsure, 9 wrong (91.5%) |
| langid | keeps-correct-answers | - | PASS |  | 911/920 correct answers accepted (99.0%) -- a false rejection costs the user their answer |
| langid | catches-wrong-language | - | PASS |  | 842/920 wrong-language answers caught (91.5%) -- this is the reported bug |
| langid | guard | - | PASS |  | 5/5 correct -- Marathi must NOT pass as Hindi |
| script | detect | - | PASS |  | 7 cases |
| script | guard | - | PASS |  | 6/6 correct |
