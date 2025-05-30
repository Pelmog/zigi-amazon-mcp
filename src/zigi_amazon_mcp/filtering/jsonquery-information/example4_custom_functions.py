from jsonquerylang import JsonQueryOptions, jsonquery


def times(value):
    return lambda array: [item * value for item in array]


data = [2, 3, 8]
query = ["times", 2]
options: JsonQueryOptions = {"functions": {"times": times}}

print(jsonquery(data, query, options))
# [4, 6, 16]
