# Validator Fixture

Each fenced block below exercises one validator case. The section labels
above each block are regular markdown headings; the validator only inspects
content inside `:::` fences, so a label can sit between blocks without
confusing it. When you add a new case, pin its expected line in
`tests/test_validate.py`.

## Unknown pressure-pool property

::: {.pressure-pool reload}
## 4D Some Pool
- item
:::

## Unknown div class

::: {.foo}
## 4D Never Closed
- item
:::

## Pressure-pool missing heading

::: {.pressure-pool}
- item
- item
:::

## Challenges div with no cards

::: {.challenges}
:::

## Image div with no markdown image

::: {.image}
just some text, no image syntax here
:::

## Heading without dice notation

::: {.challenges}
## A Title Without Dice
* trait
- move
:::

## Trigger link in challenges (not supported)

::: {.challenges}
## 4D | First
* trait
>>* Second

## 4D | Second
:::

## Plain link in pressure pool (not supported)

::: {.pressure-pool}
## 4D | Pool A
- item
> Pool B
:::

::: {.pressure-pool}
## 4D Pool B
- item
:::

## Link to non-existent pool title

::: {.pressure-pool}
## 4D Only Pool
- item
>> Ghost Pool
:::

## Duplicate challenge title

::: {.challenges}
## 4D | Same Name
* trait

## 4D | Same Name
* other trait
- move
x Bad Fail
:::

## Dice value outside 1..8 range

::: {.challenges}
## 0D | Too Low
* trait

## 9D | Too High
* trait
:::

## Closing fence with no opener

:::

## Unknown challenges property

::: {.challenges bogus='value'}
## 4D | Test
* trait
:::

## Prop value with single quotes (must be double)

::: {.challenges title='Wrong quotes'}
## 4D | Test
* trait
:::

## Prop with no value

::: {.challenges title}
## 4D | Test
* trait
:::

## Valid syntax (no issues expected)

The cases below exercise the positive path: well-formed input that must
validate with zero issues. Add a case here to lock in a feature that
should keep working. The matching test in `tests/test_validate.py`
extracts this section and runs it through `validate()` expecting `[]`.

### Pressure pool with lock link

::: {.pressure-pool}
## 4D Pool Alpha
- item
>> Pool Beta
:::

### Pressure pool with trigger link and repeat prop

::: {.pressure-pool repeat}
## 4D Pool Beta
- item
>>* Pool Gamma
:::

### Pressure pool with end prop

::: {.pressure-pool end}
## 4D Pool Gamma
- item
:::

### Challenges with all features (lock link, plain link, fail)

::: {.challenges}
## 4D | Challenge One
* trait
- move
x fail state
>> Challenge Two

## 4D | Challenge Two
* trait
- move
> Challenge Three

## 4D | Challenge Three
* trait
- move
:::

### Useful pieces with lead and items

::: {.useful-pieces}
**Lead**: description text
- item
- item
:::

### Set it up with lead and items

::: {.set-it-up}
**Lead**: description text
- item
- item
:::

### Image with markdown image

::: {.image}
![Alt text](path/to/image.png)
:::

### Challenges with title prop

::: {.challenges title="Panel header text"}
## 4D | First
* trait
- move

## 4D | Second
* trait
- move
:::

