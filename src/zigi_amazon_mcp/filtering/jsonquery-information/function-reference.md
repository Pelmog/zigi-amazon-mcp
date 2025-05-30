<!-- @format -->

# Function reference • JSON Query

This reference lists all functions and operators.

## [pipe (`|`)](#pipe)

The pipe operator executes a series of query operations one by one, and the output of the first is the input for the next.

```
query1 | query2 | ...
pipe(query1, query2, ...)
```

Examples:

```
const data = [
  { "name": "Chris", "age": 23, "address": { "city": "New York" } },
  { "name": "Emily", "age": 19, "address": { "city": "Atlanta" } },
  { "name": "Michelle", "age": 27, "address": { "city": "Los Angeles" } }
]

jsonquery(data, 'sort(.age) | pick(.name, .age)')
// [
//   { "name": "Emily", "age": 19 },
//   { "name": "Chris", "age": 23 },
//   { "name": "Michelle", "age": 27 }
// ]
```

## [object](#object)

Create an object.

```
{ prop1: query1, prop2: query2, ...}
object({ prop1: query1, prop2: query2, ...})
```

Examples:

```
const data = [
  { "name": "Chris", "age": 23, "address": { "city": "New York" } },
  { "name": "Emily", "age": 19, "address": { "city": "Atlanta" } },
  { "name": "Michelle", "age": 27, "address": { "city": "Los Angeles" } }
]

jsonquery(data, '{ names: map(.name), total: size() }')
// {
//   "names": ["Chris", "Emily", "Michelle"],
//   "total" 3
// }


jsonquery(data, 'map({ firstName: .name, city: .address.city})')
// [
//   { "firstName": "Chris", "city": "New York" },
//   { "firstName": "Emily", "city": "Atlanta" },
//   { "firstName": "Michelle", "city": "Los Angeles" }
// ]
```

## [array](#array)

Create an array

```
[query1, query2, ...]
array(query2, query2, ...)
```

Examples:

```
const data = [
  { "name": "Chris", "age": 16 },
  { "name": "Emily", "age": 32 },
  { "name": "Joe", "age": 18 }
]

jsonquery(data, 'filter(.age in [16, 18])')
// [
//   { "name": "Chris", "age": 16 },
//   { "name": "Joe", "age": 18 }
// ]

const locations = [
  {"latitude": 52.33, "longitude": 4.01},
  {"latitude": 52.18, "longitude": 3.99},
  {"latitude": 51.97, "longitude": 4.05}
]

jsonquery(locations, 'map([.latitude, .longitude])')
// [
//   [52.33, 4.01],
//   [52.18, 3.99],
//   [51.97, 4.05]
// ]
```

## [get](#get)

Get a path from an object.

```
.prop1
.prop1.prop2
."prop1"
get(prop1, prop2, ...)
```

For example `.age` gets the property `age` from an object, and `.address.city` gets a nested property `city` inside an object `address`. To get the current value or object itself use function `get()` without properties.

The function returns `null` when a property does not exist.

Examples:

```
const data = {
  "name": "Joe",
  "age": 32,
  "address": {
    "city": "New York"
  }
}

jsonquery(data, '.name') // "Joe"
jsonquery(data, '.address.city') // "New York"
```

## [filter](#filter)

Filter a list with objects or values.

```
filter(condition)
```

Examples:

```
const data = [
  { "name": "Chris", "age": 23, "address": { "city": "New York" } },
  { "name": "Emily", "age": 19, "address": { "city": "Atlanta" } },
  { "name": "Joe", "age": 32, "address": { "city": "New York" } },
  { "name": "Kevin", "age": 19, "address": { "city": "Atlanta" } },
  { "name": "Michelle", "age": 27, "address": { "city": "Los Angeles" } },
  { "name": "Robert", "age": 45, "address": { "city": "Manhattan" } },
  { "name": "Sarah", "age": 31, "address": { "city": "New York" } }
]

jsonquery(data, 'filter(.age > 30)')
// [
//   { "name": "Joe", "age": 32, "address": { "city": "New York" } },
//   { "name": "Robert", "age": 45, "address": { "city": "Manhattan" } },
//   { "name": "Sarah", "age": 31, "address": { "city": "New York" } }
// ]

jsonquery(data, 'filter(.address.city == "new York")')
// [
//   { "name": "Chris", "age": 23, "address": { "city": "New York" } },
//   { "name": "Joe", "age": 32, "address": { "city": "New York" } },
//   { "name": "Sarah", "age": 31, "address": { "city": "New York" } }
// ]

jsonquery(data, 'filter((.age > 30) and (.address.city == "New York"))')
// [
//   { "name": "Joe", "age": 32, "address": { "city": "New York" } },
//   { "name": "Sarah", "age": 31, "address": { "city": "New York" } }
// ]
```

## [sort](#sort)

Sort a list with objects or values. The function first orders values by type: `boolean`, `number`, `string`, and other types. Strings are compared alphabetically and case-sensitive. Objects and arrays are not re-ordered.

```
sort()
sort(property)
sort(property, direction)
```

Examples:

```
const data = [
  { "name": "Chris", "age": 23, "address": { "city": "New York" } },
  { "name": "Emily", "age": 19, "address": { "city": "Atlanta" } },
  { "name": "Michelle", "age": 27, "address": { "city": "Los Angeles" } }
]

jsonquery(data, 'sort(.age)')
// [
//   { "name": "Emily", "age": 19, "address": { "city": "Atlanta" } },
//   { "name": "Chris", "age": 23, "address": { "city": "New York" } },
//   { "name": "Michelle", "age": 27, "address": { "city": "Los Angeles" } }
// ]

jsonquery(data, 'sort(.age, "desc")')
// [
//   { "name": "Michelle", "age": 27, "address": { "city": "Los Angeles" } },
//   { "name": "Chris", "age": 23, "address": { "city": "New York" } },
//   { "name": "Emily", "age": 19, "address": { "city": "Atlanta" } }
// ]

jsonquery(data, 'sort(.address.city)')
// [
//   { "name": "Emily", "age": 19, "address": { "city": "Atlanta" } },
//   { "name": "Michelle", "age": 27, "address": { "city": "Los Angeles" } },
//   { "name": "Chris", "age": 23, "address": { "city": "New York" } }
// ]

const values = [7, 2, 9]

jsonquery(values, 'sort()') // [2, 7, 9]
jsonquery(values, 'sort(get(), "desc")') // [9, 7, 2]
```

## [reverse](#reverse)

Create a new array with the items in reverse order.

```
reverse()
```

Examples:

```
const data = [1, 2, 3]
jsonquery(data, 'reverse()')
// [3, 2, 1]
```

## [pick](#pick)

Pick one or multiple properties or paths, and create a new, flat object for each of them. Can be used on both an object or an array.

```
pick(property1, property2, ...)
```

Examples:

```
const data = [
  { "name": "Chris", "age": 23, "address": { "city": "New York" } },
  { "name": "Emily", "age": 19, "address": { "city": "Atlanta" } },
  { "name": "Michelle", "age": 27, "address": { "city": "Los Angeles" } }
]

jsonquery(data, 'pick(.age)')
// [
//   { "age": 23 },
//   { "age": 19 },
//   { "age": 27 }
// ]

jsonquery(data, 'pick(.name, .address.city)')
// [
//   { "name": "Chris", "city": "New York" },
//   { "name": "Emily", "city": "Atlanta" },
//   { "name": "Michelle", "city": "Los Angeles" }
// ]

const item = { "price": 25 }

jsonquery(item, 'pick(.price)') // 25
```

## [map](#map)

Map over an array and apply the provided callback query to each of the items in the array.

```
map(callback)
```

Examples:

```
const data = [
  { "name": "Chris", "scores": [5, 7, 3] },
  { "name": "Emily", "scores": [8, 5, 2, 5] },
  { "name": "Joe", "scores": [1, 1, 5, 6] }
]

jsonquery(data, `map({
  firstName: .name,
  maxScore: .scores | max()
})`)
// [
//   {"firstName": "Chris", "maxScore": 7},
//   {"firstName": "Emily", "maxScore": 8},
//   {"firstName": "Joe"  , "maxScore": 6}
// ]

const cart = [
  {"name": "bread", "price": 2.5, "quantity": 2},
  {"name": "milk" , "price": 1.2, "quantity": 3}
]
jsonquery(data, 'map(.price * .quantity)')
// 8.6
```

## [mapObject](#mapobject)

Map over an object, and create a new object with the entry `{ key, value }` returned by the callback for every input entry.

```
mapObject(callback)
```

Examples:

```
const data = { "a": 2, "b": 3 }
jsonquery(data, `mapObject({
  key: (.key + " times two"),
  value: (.value * 2)
})`)
// {
//   "a times two": 4,
//   "b times two": 6
// }
```

## [mapKeys](#mapkeys)

Map over an object, and create a new object with the keys returned by the callback having the value of the original key.

```
mapKeys(callback)
```

Examples:

```
const data = { "a": 2, "b": 3 }
jsonquery(data, 'mapKeys("#" + get())')
// { "#a": 2, "#b": 3 }
```

## [mapValues](#mapvalues)

Map over an object, and create a new object with the values updated by the return value of callback.

```
mapValues(callback)
```

Examples:

```
const data = { "a": 2, "b": 3 }
jsonquery(data, 'mapValues(get() * 2)')
// { "a": 4, "b": 6 }
```

## [groupBy](#groupby)

Group a list with objects grouped by the value of given path. This creates an object with the different properties as key, and an array with all items having that property as value.

```
groupBy(property)
```

Examples:

```
const data = [
  { "name": "Chris", "city": "New York" },
  { "name": "Emily", "city": "Atlanta" },
  { "name": "Joe", "city": "New York" },
  { "name": "Kevin", "city": "Atlanta" },
  { "name": "Michelle", "city": "Los Angeles" },
  { "name": "Robert", "city": "Manhattan" },
  { "name": "Sarah", "city": "New York" }
]

jsonquery(data, 'groupBy(.city)')
// {
//   "New York": [
//     {"name": "Chris", "city": "New York"},
//     {"name": "Joe"  , "city": "New York"},
//     {"name": "Sarah", "city": "New York"}
//   ],
//   "Atlanta": [
//     {"name": "Emily", "city": "Atlanta"},
//     {"name": "Kevin", "city": "Atlanta"}
//   ],
//   "Los Angeles": [
//     {"name": "Michelle", "city": "Los Angeles"}
//   ],
//   "Manhattan": [
//     {"name": "Robert", "city": "Manhattan"}
//   ]
// }
```

## [keyBy](#keyby)

Turn an array with objects into an object by key. When there are multiple items with the same key, the first item will be kept.

```
keyBy(property)
```

Examples:

```
const data = [
  { id: 1, name: 'Joe' },
  { id: 2, name: 'Sarah' },
  { id: 3, name: 'Chris' }
]

jsonquery(data, 'keyBy(.id)')
// {
//   1: { id: 1, name: 'Joe' },
//   2: { id: 2, name: 'Sarah' },
//   3: { id: 3, name: 'Chris' }
// }
```

## [keys](#keys)

Return an array with the keys of an object.

```
keys()
```

Examples:

```
const data = {
  "name": "Joe",
  "age": 32,
  "address": {
    "city": "New York"
  }
}

jsonquery(data, 'keys()') // ["name", "age", "address"]
```

## [values](#values)

Return the values of an object.

```
values()
```

Examples:

```
const data = {
  "name": "Joe",
  "age": 32,
  "city": "New York"
}

jsonquery(data, 'values()') // ["Joe", 32, "New York"]
```

## [flatten](#flatten)

Flatten an array containing arrays.

```
flatten()
```

Examples:

```
const data = [[1, 2], [3, 4]]

jsonquery(data, 'flatten()') // [1, 2, 3, 4]

const data2 = [[1, 2, [3, 4]]]

jsonquery(data2, 'flatten()') // [1, 2, [3, 4]]
```

## [join](#join)

Concatenate array items into a string with an optional separator.

```
join()
join(separator)
```

Examples:

```
const data = [
  { "name": "Chris", "age": 16 },
  { "name": "Emily", "age": 32 },
  { "name": "Joe", "age": 18 }
]

jsonquery(data, 'map(.name) | join(", ")')
// "Chris, Emily, Joe"
```

## [split](#split)

Divide a string into an array substrings, separated by a separator. When no separator is provided, the string is split in words separated by one or multiple whitespaces, and the words are trimmed so they do not contain whitespace at the start or the end. When the separator is an empty string, the text will be split into a list with its individual characters.

```
split(text)
split(text, separator)
```

Examples:

```
const data = {
  "message": "hi there how are you doing?"
}
jsonquery(data, 'split(.message)')
// ["hi", "there", "how", "are", "you", "doing?"]


jsonquery(data, 'split("a,b,c", ",")')
// ["a", "b", "c"]
```

## [substring](#substring)

Extract a substring from a string. When `end` is not provided, the length of the string will be used as `end`.

```
substring(text, start)
substring(text, start, end)
```

Examples:

```
const events = [
  {"type": "start", "time": "2024-11-06 23:14:00" },
  {"type": "initialize", "time": "2025-11-08 09:00:00" },
  {"type": "end", "time": "2025-11-24 10:27:00" }
]

jsonquery(events, 'map(substring(.time, 0, 10))')
// [
//   "2024-11-06",
//   "2025-11-08",
//   "2025-11-24"
// ]
```

## [uniq](#uniq)

Create a copy of an array where all duplicates are removed. Values are compared using the `eq` operator, which does a deep strict equal comparison.

```
uniq()
```

Examples:

```
jsonquery([1, 5, 3, 3, 1], 'uniq()') // [1, 3, 5]
```

## [uniqBy](#uniqby)

Create a copy of an array where all objects with a duplicate value for the selected path are removed. In case of duplicates, the first object is kept.

```
uniqBy(property)
```

Examples:

```
const data = [
  { "name": "Chris", "age": 23, "address": { "city": "New York" } },
  { "name": "Emily", "age": 19, "address": { "city": "Atlanta" } },
  { "name": "Joe", "age": 32, "address": { "city": "New York" } },
  { "name": "Kevin", "age": 19, "address": { "city": "Atlanta" } },
  { "name": "Michelle", "age": 27, "address": { "city": "Los Angeles" } },
  { "name": "Robert", "age": 45, "address": { "city": "Manhattan" } },
  { "name": "Sarah", "age": 31, "address": { "city": "New York" } }
]

jsonquery(data, 'uniqBy(.address.city)')
// [
//   { "name": "Chris", "age": 23, "address": { "city": "New York" } },
//   { "name": "Emily", "age": 19, "address": { "city": "Atlanta" } },
//   { "name": "Michelle", "age": 27, "address": { "city": "Los Angeles" } },
//   { "name": "Robert", "age": 45, "address": { "city": "Manhattan" } }
// ]
```

## [limit](#limit)

Create a copy of an array cut off at the selected limit.

```
limit(size)
```

Examples:

```
const data = [1, 2, 3, 4, 5, 6]

jsonquery(data, 'limit(2)') // [1, 2]
jsonquery(data, 'limit(4)') // [1, 2, 3, 4]
```

## [size](#size)

Return the size of an array or the length of a string.

```
size()
```

Examples:

```
jsonquery([1, 2], 'size()') // 2
jsonquery([1, 2, 3, 4], 'size()') // 4
jsonquery("hello", 'size()') // 5
```

## [sum](#sum)

Calculate the sum of all values in an array. The function return `0` in case of an empty array.

```
sum()
```

Examples:

```
jsonquery([7, 4, 2], 'sum()') // 13
jsonquery([2.4, 5.7], 'sum()') // 8.1
```

## [min](#min)

Return the minimum of the values in an array. The function returns `null` in case of an empty array.

```
min()
```

Examples:

```
jsonquery([5, 1, 1, 6], 'min()') // 1
jsonquery([5, 7, 3], 'min()') // 3
```

## [max](#max)

Return the maximum of the values in an array. The function returns `null` in case of an empty array.

```
max()
```

Examples:

```
jsonquery([1, 1, 6, 5], 'max()') // 6
jsonquery([5, 7, 3], 'max()') // 7
```

## [prod](#prod)

Calculate the product of the values in an array. The function throws an error in case of an empty array.

```
prod()
```

Examples:

```
jsonquery([2, 3], 'prod()') // 6
jsonquery([2, 3, 2, 7, 1, 1], 'prod()') // 84
```

## [average](#average)

Calculate the average of the values in an array. The function throws an error in case of an empty array.

```
average()
```

Examples:

```
jsonquery([2, 4], 'average()') // 3
jsonquery([2, 3, 2, 7, 1], 'average()') // 3
```

## [eq (`==`)](#eq)

Test whether two values are deep strict equal. This will consider a string `"2"` and a number `2` to be _not_ equal for example, since their data type differs. Objects and arrays are compared recursively, so `{"id":1,"name":"Joe"}` and `{"name":"Joe","id":1}` are deep equal for example.

```
a == b
eq(a, b)
```

Examples:

```
const data = [
  { "name": "Chris", "age": 23 },
  { "name": "Emily", "age": 18 },
  { "name": "Kevin", "age": 18 }
]

jsonquery(data, 'filter(.age == 18)')
// [
//   { "name": "Emily", "age": 18 },
//   { "name": "Kevin", "age": 18 }
// ]

jsonquery({ a: 2 }, '.a == 2') // true
jsonquery({ a: 2 }, '.a == 3') // false
jsonquery({ a: 2 }, '.a == "2"') // false (since not strictly equal)
jsonquery({ a: 2 }, 'eq(.a, 2)') // true
```

## [gt (`>`)](#gt)

Test whether `a` is greater than `b`. The operator supports comparing two numbers, two strings, or two booleans. In case of unsupported data types or mixed data types, the function returns \`false.

```
a > b
gt(a, b)
```

Examples:

```
const data = [
  { "name": "Chris", "age": 16 },
  { "name": "Emily", "age": 32 },
  { "name": "Joe", "age": 18 }
]

jsonquery(data, 'filter(.age > 18)')
// [
//   { "name": "Emily", "age": 32 }
// ]
```

## [gte (`>=`)](#gte)

Test whether `a` is greater than or equal to `b`. The operator supports comparing two numbers, two strings, or two booleans. In case of unsupported data types or mixed data types, the function returns \`false.

```
a >= b
gte(a, b)
```

Examples:

```
const data = [
  { "name": "Chris", "age": 16 },
  { "name": "Emily", "age": 32 },
  { "name": "Joe", "age": 18 }
]

jsonquery(data, 'filter(.age >= 18)')
// [
//   { "name": "Emily", "age": 32 },
//   { "name": "Joe", "age": 18 }
// ]
```

## [lt (`<`)](#lt)

Test whether `a` is less than `b`. The operator supports comparing two numbers, two strings, or two booleans. In case of unsupported data types or mixed data types, the function returns \`false.

```
a < b
lt(a, b)
```

Examples:

```
const data = [
  { "name": "Chris", "age": 16 },
  { "name": "Emily", "age": 32 },
  { "name": "Joe", "age": 18 }
]

jsonquery(data, 'filter(.age < 18)')
// [
//   { "name": "Chris", "age": 16 }
// ]
```

## [lte (`<=`)](#lte)

Test whether `a` is less than or equal to `b`. The operator supports comparing two numbers, two strings, or two booleans. In case of unsupported data types or mixed data types, the function returns \`false.

```
a <= b
lte(a, b)
```

Examples:

```
const data = [
  { "name": "Chris", "age": 16 },
  { "name": "Emily", "age": 32 },
  { "name": "Joe", "age": 18 }
]

jsonquery(data, 'filter(.age <= 18)')
// [
//   { "name": "Chris", "age": 16 },
//   { "name": "Joe", "age": 18 }
// ]
```

## [ne (`!=`)](#ne)

Test whether two values are not deep strict equal. This is the opposite of the strict equal function `eq`. Two values are considered unequal when their data type differs (for example one is a string and another is a number), or when the value itself is different. For example a string `"2"` and a number `2` are considered unequal, even though their mathematical value is equal. Objects and arrays are compared recursively, so `{"id":1,"name":"Joe"}` and `{"name":"Joe","id":1}` are deep equal for example.

```
a != b
ne(a, b)
```

Examples:

```
const data = [
  { "name": "Chris", "age": 16 },
  { "name": "Emily", "age": 32 },
  { "name": "Joe", "age": 18 }
]

jsonquery(data, 'filter(.age != 16)')
// [
//   { "name": "Emily", "age": 32 },
//   { "name": "Joe", "age": 18 }
// ]

jsonquery({ a: 2 }, 'a != 2') // false
jsonquery({ a: 2 }, 'a != 3') // true
jsonquery({ a: 2 }, 'a != "2"') // true (since not strictly equal)
```

## [and](#and)

Test whether two or more values are truthy. A non-truthy value is any of `false`, `0`, `""`, `null`, or `undefined`. The function throws an error in case of zero arguments.

```
a and b
a and b and c and ...
and(a, b)
and(a, b, c, ...)
```

Examples:

```
const data = [
  { "name": "Chris", "age": 16 },
  { "name": "Emily", "age": 32 },
  { "name": "Chris", "age": 18 }
]

jsonquery(data, 'filter((.name == "Chris") and (.age == 16))')
// [
//   { "name": "Chris", "age": 16 }
// ]
```

## [or](#or)

Test whether at least one of the values is truthy. A non-truthy value is any of `false`, `0`, `""`, `null`, or `undefined`. The function throws an error in case of zero arguments.

```
a or b
a or b or c or ...
or(a, b)
or(a, b, c, ...)
```

Examples:

```
const data = [
  { "name": "Chris", "age": 16 },
  { "name": "Emily", "age": 32 },
  { "name": "Joe", "age": 18 }
]

jsonquery(data, 'filter((.age == 16) or (.age == 18))')
// [
//   { "name": "Chris", "age": 16 },
//   { "name": "Joe", "age": 18 }
// ]
```

## [not](#not)

Function `not` inverts the value. When the value is truthy it returns `false`, and otherwise it returns `true`.

```
not(value)
```

Examples:

```
const data = [
  { "name": "Chris", "age": 16 },
  { "name": "Emily", "age": 32 },
  { "name": "Joe", "age": 18 }
]

jsonquery(data, 'filter(not(.age == 18))')
// [
//   { "name": "Chris", "age": 16 },
//   { "name": "Emily", "age": 32 }
// ]
```

## [exists](#exists)

Returns `true` if the property at the provided path exists. Returns `true` too when the properties value contains a value `null`, `false` or `0`.

```
exists(path)
```

Examples:

```
const data = [
  { "name": "Joe", "details": { "age": 16 } },
  { "name": "Oliver" },
  { "name": "Sarah", "details": { "age": 18 } },
  { "name": "Dave", "details": null },
]

jsonquery(data, 'filter(exists(.details))')
// [
//   { "name": "Joe", "details": { "age": 16 } },
//   { "name": "Sarah", "details": { "age": 18 } },
//   { "name": "Dave", "details": null }
// ]

jsonquery({ }, ["exists", "value"]) // false
jsonquery({ "value": null }, ["exists", "value"]) // true
jsonquery({ "value": undefined }, ["exists", "value"]) // false
```

## [if](#if)

A conditional allowing to make a choice depending on a condition. Both `then` and `else` parts are required.

```
if(condition, valueIfTrue, valueIfFalse)
```

Examples:

```
const data = {
  "kid": {
    "name": "Emma",
    "age": 11
  },
  "minAge": 12,
  "messageOk": "Welcome!",
  "messageFail": "Sorry, you're too young."
}

jsonquery(data, 'if(.kid.age >= .minAge, .messageOk, .messageFail)')
// "Sorry, you're too young."
```

## [in](#in)

Test whether the search value is one of the values of the provided list. Values are compared using the `eq` operator, which does a deep strict equal comparison.

```
searchValue in values
in(searchValue, values)
```

Examples:

```
const data = [
  { "name": "Chris", "age": 16 },
  { "name": "Emily", "age": 32 },
  { "name": "Joe", "age": 18 }
]

jsonquery(data, 'filter(.age in [16, 18])')
// [
//   { "name": "Chris", "age": 16 },
//   { "name": "Joe", "age": 18 }
// ]
```

## [not in](#not-in)

Test whether the search value is _not_ one of the values of the provided list. Values are compared using the `eq` operator, which does a deep strict equal comparison.

```
searchValue not in values
```

Examples:

```
const data = [
  { "name": "Chris", "age": 16 },
  { "name": "Emily", "age": 32 },
  { "name": "Joe", "age": 18 }
]

jsonquery(data, 'filter(.age not in [16, 18])')
// [
//   { "name": "Emily", "age": 32 }
// ]
```

## [regex](#regex)

Test the `text` against the regular expression.

```
regex(text, expression)
regex(text, expression, options)
```

Here, `expression` is a string containing the regular expression like `^[a-z]+$`, and `options` are regular expression flags like `i`.

Examples:

```
const data = [
  { "id": 1, "message": "I LIKE it!" },
  { "id": 2, "message": "It is awesome!" },
  { "id": 3, "message": "Was a disaster" },
  { "id": 4, "message": "We like it a lot" }
]

jsonquery(data, 'filter(regex(.message, "like|awesome"))')
// [
//   { "id": 2, "message": "It is awesome!" },
//   { "id": 4, "message": "We like it a lot" }
// ]

jsonquery(data, 'filter(regex(.message, "like|awesome", "i"))')
// [
//   { "id": 1, "message": "I LIKE it!" },
//   { "id": 2, "message": "It is awesome!" },
//   { "id": 4, "message": "We like it a lot" }
// ]
```

## [add (`+`)](#add)

Add two values.

```
a + b
add(a, b)
```

Examples:

```
const data = { "a": 6, "b": 2 }

jsonquery(data, '.a + .b') // 8

const user = {
  "firstName": "José",
  "lastName": "Carioca"
}
jsonquery(user, '(.firstName + " ") + .lastName')
// "José Carioca"
```

## [subtract (`-`)](#subtract-)

Subtract two values.

```
a - b
subtract(a, b)
```

Examples:

```
const data = { "a": 6, "b": 2 }

jsonquery(data, '.a - .b') // 4
```

## [multiply (`*`)](#multiply)

Multiply two values.

```
a * b
multiply(a, b)
```

Examples:

```
const data = { "a": 6, "b": 2 }

jsonquery(data, '.a * .b') // 12
```

## [divide (`/`)](#divide)

Divide two values.

```
a / b
divide(a, b)
```

Examples:

```
const data = { "a": 6, "b": 2 }

jsonquery(data, '.a / .b') // 3
```

## [pow (`^`)](#pow)

Calculate the exponent. Returns the result of raising `a` to the power of `b`, like `a ^ b`. The `^` operator does not support more than two values, so if you need to calculate a chain of multiple exponents you’ll have to use parenthesis, like `(a ^ b) ^ c`.

```
a ^ b
pow(a, b)
```

Examples:

```
const data = { "a": 2, "b": 3 }

jsonquery(data, '.a ^ .b') // 8
```

## [mod (`%`)](#mod)

Calculate the remainder (the modulus) of `a` divided by `b`, like `a % b`.

```
a % b
mod(a, b)
```

Examples:

```
const data = { "a": 8, "b": 3 }

jsonquery(data, '.a % .b') // 2
```

## [abs](#abs)

Calculate the absolute value.

```
abs(value)
```

Examples:

```
jsonquery({"a": -7}, 'abs(.a)') // 7
```

## [round](#round)

Round a value. When `digits` is provided, the value will be rounded to the selected number of digits.

```
round(value)
round(value, digits)
```

Examples:

```
jsonquery({"a": 23.7612 }, 'round(.a)') // 24
jsonquery({"a": 23.1345 }, 'round(.a)') // 23
jsonquery({"a": 23.1345 }, 'round(.a, 2)') // 23.13
jsonquery({"a": 23.1345 }, 'round(.a, 3)') // 23.135
```

## [number](#number)

Parse the numeric value in a string into a number.

```
number(text)
```

Examples:

```
jsonquery({"value": "2.4" }, 'number(.value)') // 2.4
jsonquery("-4e3", 'number(get())') // -4000
jsonquery("2,7,1", 'split(",") | map(number(get()))') // [2, 7, 1]
```

## [string](#string)

Format a number as a string.

```
string(number)
```

Examples:

```
jsonquery({"value": 2.4 }, 'string(.value)') // "2.4"
jsonquery(42, 'string(get())') // "42"
```
