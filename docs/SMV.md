# Design changes and SMV

SMV here means Standard Minute Value: standard minutes for a defined operation
under stated conditions. Crumble accepts already-established standard operation
times. It does not apply a hidden performance rating or allowance formula.

## What the calculation means

For each changed part, map the old value and new value to operation quantities.
For operation i, calculate:

~~~text
quantity_delta[i] = quantity_after[i] - quantity_before[i]
time_delta[i] = quantity_delta[i] * standard_minutes[i]
~~~

A range uses the lower and upper standard-minute inputs. Negative quantities
reverse the interval bounds. Unchanged operations cancel. Ranges are input
bounds, not statistical confidence intervals. Correlations between separate
operations are not modelled.

Each operation may belong to only one part field. The library validator rejects
cross-field reuse, duplicate rules, invalid ranges and non-finite values. This
prevents an obvious form of double counting; it cannot verify the engineering
content of the library.

## Library format

See the complete, runnable [illustrative library](../crumble/data/demo_operations.json).
Its times are invented workflow examples. Do not use them as production standards.

~~~json
{
  "version": "your-factory-study-2026-01",
  "scope": "Describe factory, fabric, machine, method and allowance basis here",
  "illustrative": false,
  "operations": [
    {
      "id": "operation-code",
      "label": "Operation description",
      "low": 0.0,
      "high": 0.0,
      "source": "Replace with a valid time-study reference",
      "machine": "Replace with the machine and method"
    }
  ],
  "rules": [
    {
      "field": "pockets",
      "values": ["none"],
      "operations": []
    },
    {
      "field": "pockets",
      "values": ["patch"],
      "operations": [{"id": "operation-code", "quantity": 2}]
    }
  ]
}
~~~

Zero values above are placeholders illustrating JSON syntax, not real standards.
Use your measured standard-minute ranges before installing the library:

~~~sh
crumble --workspace retailer operations factory-times.json
~~~

Only complete, normalised sets of field values match a rule. A missing pocket
description is **unknown**, not "none". Counts and construction details cannot be
reliably inferred from a broad label; define your own more specific values and
rules, such as "two lined patch pockets", when needed.

## Review and limitations

A suggestion records the time library hash, version, scope, changed part values,
operation quantities, source references and missing rules. Reviews freeze both
garment snapshots, the complete library and the computed suggestion.

Reviewers can mark suggestions as needing a time study, rejected, or accepted
for a trial. Acceptance does not turn an estimate into a validated factory SMV.
The application intentionally does not output a new total garment SMV because
the visible and mapped operations are generally incomplete.

Review material handling, fabric behaviour, machine setup, seam lengths,
measurement changes, work aids and unseen construction. A colour-only change
might affect handling or process requirements; missing rules are not a claim of
zero impact. Scope is visible text in this alpha, not automatically enforced
factory/material matching.

