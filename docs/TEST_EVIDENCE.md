# AwazSetu — Test Evidence

Run: 2026-09-15 15:49:31 · **6/8 passed**

| Suite | Case | Lang | Result | Time | Detail |
|---|---|---|---|---|---|
| chat | on-topic | hi | PASS | 56.6 | यह वीडियो बकरियों को प्रभावित करने वाली बीमारियों के उपचार और प्रबंधन के बारे में है, जिसमें विभिन्न बीमारियों जैसे कि रक्तस्राव सेप्टिकमिया और अन्य ज |
| chat | on-topic | mr | PASS | 42.0 | या व्हिडिओमध्ये शेळींच्या रोगांच्या उपचाराबद्दल आणि प्रतिबंधाबद्दल माहिती आहे, ज्यात लक्षणे, निदान आणि उपचार पद्धती जसे की अलगाव आणि शेड साफ करणे यांच |
| chat | on-topic | en | PASS | 26.6 | This video is about the treatment and management of diseases affecting goats, including the classification of diseases, remedies, and preventive measu |
| chat | on-topic | or | FAIL |  | Traceback (most recent call last):   File "C:\users\hansu\awazsetu\scripts\test_e2e.py", line 102, in suite_chat     r = answer(m, GOOD_Q[L], L) KeyError: 'or'  |
| refusal | offtopic-refused | hi | PASS | 28.9 | इस वीडियो में इसकी जानकारी नहीं है। सबसे नज़दीकी पंक्तियाँ नीचे दी गई हैं। |
| refusal | offtopic-refused | mr | PASS | 27.7 | या व्हिडिओमध्ये याची माहिती नाही. सर्वात जवळच्या ओळी खाली दिल्या आहेत. |
| refusal | offtopic-refused | en | PASS | 22.7 | This video does not cover that. The closest lines I found are below. |
| refusal | offtopic-refused | or | FAIL |  | 'or' |

## Open defects (2)
- **chat/on-topic** (or): Traceback (most recent call last):
  File "C:\users\hansu\awazsetu\scripts\test_e2e.py", line 102, in suite_chat
    r = answer(m, GOOD_Q[L], L)
KeyError: 'or'

- **refusal/offtopic-refused** (or): 'or'
