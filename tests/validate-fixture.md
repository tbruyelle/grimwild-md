# Validator Fixture

Each fenced block below exercises one validator case. The section labels
above each block are regular markdown headings; the validator only inspects
content inside `:::` fences, so a label can sit between blocks without
confusing it. When you add a new case, pin its expected line in
`tests/test_validate.py`.

## Unknown pressure-pools property

::: {.pressure-pools reload}
## 4D Some Pool
- item
:::

## Unknown div class

::: {.foo}
## 4D Never Closed
- item
:::

## Pressure-pool missing heading

::: {.pressure-pools}
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

::: {.pressure-pools}
## 4D | Pool A
- item
> Pool B
:::

::: {.pressure-pools}
## 4D Pool B
- item
:::

## Link to non-existent pool title

::: {.pressure-pools}
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

::: {.challenges title=""}
## 4D | Test
* trait
:::

## Unknown column property

::: {.pressure-pools}
## 4D Pool Alpha [foo]
- item
:::

## Div-level repeat property (column suffix required)

::: {.pressure-pools repeat}
## 4D Pool Alpha
- item
:::

## Cross-div pressure-pools link (not allowed)

::: {.pressure-pools}
## 4D Pool X
- item
>> Pool Y
:::

::: {.pressure-pools}
## 4D Pool Y
- item
:::

## # Title not at top of challenges div

::: {.challenges}
## 4D | First
* trait
# Title After Card
:::

## Multiple # Title headings in challenges div

::: {.challenges}
# Title One
# Title Two

## 4D | Card
* trait
:::

## Valid syntax (no issues expected)

The cases below exercise the positive path: well-formed input that must
validate with zero issues. Add a case here to lock in a feature that
should keep working. The matching test in `tests/test_validate.py`
extracts this section and runs it through `validate()` expecting `[]`.

### Pressure pool with lock link

::: {.pressure-pools}
## 4D Pool Alpha
- item
>> Pool Beta

## 4D Pool Beta [repeat]
- item
>>* Pool Gamma

## 4D Pool Gamma [end]
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

### Challenges with inner # title heading

::: {.challenges}
# Negotiating Peace in a Civil War

## 4D | First
* trait
- move

## 4D | Second
* trait
- move
:::

### Page breaks

::: {.page-break}
:::

### List with a sublist

- top item one
  - sub item A
  - sub item B
- top item two
  - sub item C
- top item three

### Pressure pool with column [repeat] suffix

::: {.pressure-pools}
## 4D Pool One [repeat]
- item
>> Pool Two

## 4D Pool Two [end]
- item
:::

### Pressure pool with multi-heading columns and cross-column link

::: {.pressure-pools}
## 4D Pool One
- item
>> Pool Three

## 4D Pool Two
- item
>>* Pool Three

## 4D Pool Three [end]
- item
:::
