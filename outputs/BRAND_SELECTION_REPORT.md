# Phase 1: Dataset Audit and Brand Selection

## Dataset used

- Path: `C:\Users\DELL\Desktop\hiver side project\data\twcs.csv`
- Size: 516,508,641 bytes
- Rows: 2,811,774
- Schema: tweet_id, author_id, inbound, created_at, text, response_tweet_id, in_response_to_tweet_id
- Inbound/customer tweets: 1,537,843
- Outbound/brand tweets: 1,273,931
- Unique outbound brands: 108
- Date range (UTC): 2008-05-08T20:13:59+00:00 to 2017-12-03T23:14:01+00:00

## Method

The script makes three streaming passes. It ranks the 40 largest outbound authors, follows raw tweet-id links to measure answered customer issues and local thread components, and scores candidates with the weights recorded in `brand_config.json`. It does not label intents; lexical diversity is only a Phase 1 proxy.

## Top 10 candidates

| Rank | Brand | Score | Answered issues | Usable responses | Link coverage | Components | Avg. component size | Lexical signals | Golden-set eligible |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | AppleSupport | 98.30 | 106,623 | 106,623 | 99.8% | 83,449 | 2.72 | 9975 | Yes |
| 2 | AmazonHelp | 98.25 | 154,976 | 154,976 | 91.2% | 89,642 | 4.01 | 21043 | Yes |
| 3 | Uber_Support | 94.35 | 55,182 | 55,182 | 98.1% | 43,841 | 2.79 | 7621 | Yes |
| 4 | SpotifyCares | 92.29 | 41,585 | 41,585 | 96.1% | 30,143 | 2.94 | 6399 | Yes |
| 5 | AmericanAir | 92.22 | 36,457 | 36,457 | 99.2% | 27,502 | 2.99 | 7491 | Yes |
| 6 | TMobileHelp | 91.79 | 33,837 | 33,837 | 98.6% | 27,208 | 2.69 | 5725 | Yes |
| 7 | SouthwestAir | 90.57 | 28,285 | 28,285 | 97.6% | 22,133 | 2.81 | 5988 | Yes |
| 8 | comcastcares | 89.91 | 30,369 | 30,369 | 91.9% | 25,325 | 2.65 | 5606 | Yes |
| 9 | Ask_Spectrum | 89.67 | 24,976 | 24,976 | 96.6% | 19,469 | 2.81 | 4699 | Yes |
| 10 | Delta | 89.44 | 36,134 | 36,134 | 85.5% | 27,165 | 3.09 | 6876 | Yes |

## Selected brand

**AppleSupport** (score 98.30/100).

It is the highest-ranked candidate under the recorded method. Its raw-link evidence includes 106,623 answered customer issues, 106,623 usable linked brand responses, 83,449 reconstructed local conversation components, and 99.8% outbound-to-inbound link coverage.

## Limitations

- Tweet link fields can be missing or contain multiple ids, so components are reconstructed from observed links rather than assumed complete conversations.
- Inbound messages without an outbound tweet-id link are not attributed to a brand.
- This analysis is Phase 1 only: no RAG, embeddings, agent, intent taxonomy, golden set, or evaluation harness was created.
