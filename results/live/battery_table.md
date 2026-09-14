| member | model | tier | prompt | trials | pass | ordinary | neg trial | neg 3of3 | done/halt/unp | macro F1 | med turns | tok in | tok out | US$ | US$/pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| zhao_yujia | `qwen/qwen3-235b-a22b-2507` | cheap | v1 | 60 | 51.7% | 90.0% | 13.3% | 1/10 (10%) | 55/2/3 | 0.87 | 3.0 | 367,581 | 25,019 | 0.0409 | 0.0013 |
| li_yunke | `qwen/qwen3-235b-a22b-2507` | cheap | v2 | 60 | 68.3% | 76.7% | 60.0% | 4/10 (40%) | 48/0/12 | 0.84 | 4.0 | 866,374 | 28,436 | 0.0858 | 0.0021 |
| shen_bowen | `deepseek/deepseek-v3.2` | cheap | v2 | 60 | 80.0% | 93.3% | 66.7% | 6/10 (60%) | 58/0/2 | 0.88 | 4.0 | 999,576 | 40,971 | 0.2853 | 0.0059 |
| xia_yanran | `google/gemini-2.5-flash` | mid | v2 | 60 | 73.3% | 76.7% | 70.0% | 7/10 (70%) | 51/0/9 | 0.91 | 2.5 | 889,356 | 32,305 | 0.3476 | 0.0079 |
| huang_yu | `openai/gpt-4.1-mini` | mid | v2 | 60 | 80.0% | 100.0% | 60.0% | 6/10 (60%) | 59/0/1 | 0.85 | 4.0 | 1,006,298 | 38,035 | 0.4634 | 0.0097 |
| rohit_panda | `anthropic/claude-haiku-4.5` | mid | v2 | 60 | 90.0% | 100.0% | 80.0% | 8/10 (80%) | 60/0/0 | 0.96 | 4.0 | 1,056,826 | 42,269 | 1.2682 | 0.0235 |

```
  v1 -> v2 on qwen/qwen3-235b-a22b-2507, model held fixed (zhao_yujia -> li_yunke)
    pass rate       51.7%  ->  68.3%   (+16.7 pp)
    negative 3of3   10.0%  ->  40.0%   (+30.0 pp)
    input tokens    367,581  ->  866,374   (+135.7%)
    cost per trial  US$0.00068  ->  US$0.00143
```
