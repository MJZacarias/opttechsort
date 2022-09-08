# opttechsort
This is a python3 implementation of opttechsort program. The only functionalities implemented are /s and filetype.

## Usage Command
python3 [input] [output] [sort arguments]

## Example Command
python3 opttech.py unsorted.txt output.txt "/s(4,1,N,D,5,1,N,D) filetype(gp,(63,63),(255,255,0,254))"

## Documentation
### Format for sort:

/s(1, 2, 3, 4, 1, 2, 3, 4, ...)

Four attributes needed to sort one field, but can sort many fields by adding more attributes.

1. starting position of sortable field
1. length of sortable field
1. type of field (Character, Numberic)
1. sorting field (Ascending, Descending)

### Format for filetype:

filetype(gp,(1),(2))

1. end of record delimeter in decimal. (Example: 63=? and 10=\n and 13=\r)
2. end of file in decimal.