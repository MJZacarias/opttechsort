# =============================
# imports
# =============================
from typing import Callable, BinaryIO, Tuple
import re
import sys

# =============================
# Classes
# =============================
class ByteTracker:
    def __init__(self, *args) -> None:
        self.bytes = [arg for arg in args]
        self._curr_byt_idx = 0

    # returns the current byte
    def current_byte(self) -> bytes:
        return self.bytes[self._curr_byt_idx]

    # Returns true if all bytes were given in sequence
    def got_all_bytes(self, byte) -> bool:
        if self.current_byte() == byte:
            if self._curr_byt_is_lst_byt():
                self._rst_curr_byt()
                return True
            else:
                self._inc_curr_byt_idx()
        else:
            self._rst_curr_byt()
        return False

    # Return true if curr_byt_indx is not 0
    def has_progress(self) -> bool:
        return self._curr_byt_idx != 0

    # Reset the current byte
    def reset(self):
        self._rst_curr_byt

    # increment current byte index 
    def _inc_curr_byt_idx(self) -> None:
        self._curr_byt_idx += 1
        if self._curr_byt_idx >= len(self.bytes):
            raise Exception("ERROR: ByteTracker self._curr_byt_idx exceeded byte size")

    # Resets current byte to first byte
    def _rst_curr_byt(self) -> None:
        self._curr_byt_idx = 0

    # Returns true if current byte index is the last byte
    def _curr_byt_is_lst_byt(self) -> bool:
        return self._curr_byt_idx + 1 == len(self.bytes)

    def __str__(self) -> str:
        string = ""
        string += f"bytes: {self.bytes}\n"
        string += f"current: {self._curr_byt_idx}"
        return string

class Record:
    def __init__(self, position: int, fields: tuple) -> None:
        self.position: int = position
        self.fields: tuple = fields
    
    def write_record(self, f_in: BinaryIO, f_out: BinaryIO, eor_tracker:ByteTracker) -> None:
        pending_bytes = list()
        # Jump to start of record
        f_in.seek(self.position)
        # Read and write until end of record
        eor_reached = False
        while (byte := f_in.read(1)):
            # If possibly end of record
            if eor_tracker.current_byte() == byte:
                pending_bytes.append(byte)
                eor_reached = eor_tracker.got_all_bytes(byte)
                # If confirmed end of record
                if eor_reached:
                    break
                # If confirmed not end of record
                if not (eor_reached or eor_tracker.has_progress()):
                    for b in pending_bytes:
                        f_out.write(b)
                    pending_bytes = list()
            # If not part of end record then just write byte
            else:
                f_out.write(byte)
    
class Records:
    def __init__(self, file_name_input: str, file_name_output: str, eor_tracker:ByteTracker, record_fields: list[dict]) -> None:
        self.file_name_input = file_name_input
        self.file_name_output = file_name_output
        self.eor_tracker = eor_tracker
        self.record_fields: list[dict] = record_fields
        self._records: list[Record] = list()

    # Creates record then adds it to the list
    def append(self, position: int, fields: tuple) -> None:
        self._records.append(Record(position, fields))

    # 3 Step Process
    # Read in file, sort, write out sorted file
    def run(self):
        self.populate()
        self.sort()
        self.write_records()

    # Step 1
    # Read file and populate record list
    def populate(self):
        self.eor_tracker.reset()
        with open(self.file_name_input, "rb") as f:
            first_record = f.tell() == 0
            while (byte := f.read(1)):
                if self.eor_tracker.got_all_bytes(byte) or first_record:
                    if first_record:
                        start_of_record_idx = 0
                        first_record = False
                    else:
                        start_of_record_idx = f.tell()
                    fields = list()
                    for rf in self.record_fields:
                        f.seek(start_of_record_idx + rf["position"])
                        bytes = f.read(rf["length"])
                        fields.append(rf["type_cast"](bytes))
                    fields = tuple(fields)
                    self.append(start_of_record_idx, fields)

    # Step 2
    # Sort records in list
    def sort(self) -> None:
        # Used to define a way to sort record object
        def _sort_records(record: Record) -> tuple:
            result = list([self.record_fields[i]["order"]*record.fields[i] for i in range(len(record.fields))])
            return result
        self._records = sorted(self._records, key=_sort_records)

    # Step 3
    # Write records to output file
    def write_records(self) -> None:
        i = 0
        with open(self.file_name_input, "rb") as f_in:
            with open(self.file_name_output, "wb") as f_out:
                for record in self._records:
                    record.write_record(f_in, f_out, self.eor_tracker)
                    i += 1
                    # If not last loop the write eor delimeter
                    if i != len(self._records):
                        for byte in self.eor_tracker.bytes:
                            f_out.write(byte)
    
    def __str__(self):
        string = ""
        for record in self._records:
            string+=" " + str(record.position) + " " + str(record.fields) + "\n"
        return string

# =============================
# Functions
# =============================
# Converts Bytes to type String
def bytes_to_string(bytes) -> str:
    return str(bytes, "utf-8")

# EXAMPLE: filetype(gp,(13,10),(255,255,0,254))
def filetype(typ:str="gp", end_of_record:tuple=(10), end_of_file:tuple=(-1)) -> None:
    if not (typ in ["gp"]):
        raise Exception(f"ERROR: invalid type '{typ}'")
    for item in end_of_record:
        if not str(item).isdecimal():
            raise Exception(f"ERROR: invalid end_of_record byte '{item}'")
    for item in end_of_file:
        if not str(item).isdecimal():
            raise Exception(f"ERROR: invalid end_of_file byte '{item}'")
    eor_bytes = tuple([decimal_to_byte(byte) for byte in end_of_record])
    eof_bytes = tuple([decimal_to_byte(byte) for byte in end_of_file])
    return ByteTracker(*eor_bytes), ByteTracker(*eof_bytes)

# Converts decimal int to type byte
def decimal_to_byte(decimal: int) -> bytes:
    return int(decimal).to_bytes(1,byteorder="little")

# Make sure arguments are in the following format
# EXAMPLE 1: /s(61,2,C,A)
# EXAMPLE 2: /s(61,2,C,A,1,23,C,A)
# OUTPUT: [{"position": ?, "length": ?, "type_cast": ?, "order": ?}, {???}, {???}]
def validate_sort_arguments(*args) -> list[dict]:
    if not(len(args)%4 == 0):
        raise Exception("ERROR: Number of arguments not validated. Should be divisible by 4.")
    var_type = {
        "C": bytes_to_string,
        "N": int
    }
    var_order = {
        "A": 1,
        "D": -1
    }
    fields = list()
    for i in range(0, len(args), 4):
        position = str(args[i])
        if not(position.isdecimal() and int(position) > 0):
            raise Exception("ERROR: Sort argument, Position not validated.")
        length = str(args[i+1])
        if not(length.isdecimal() and int(length) > 0):
            raise Exception("ERROR: Sort argument, Length not validated.")
        type = args[i+2]
        if not(type in ["C", "N"]):
            raise Exception("ERROR: Sort argument, Type not validated.")
        order = args[i+3]
        if not(order in ["A", "D"]):
            raise Exception("ERROR: Sort argument, Order not validated.")
        fields.append({
            "position": int(position)-1,
            "length": int(length),
            "type_cast": var_type[type],
            "order": var_order[order]
        })
    return fields

def test_sort():
    # Programmer set variables
    fn_in = "unsorted.txt"
    fn_out = "sorted_py2.txt"
    eor_tracker, eof_tracker = filetype("gp",[63,63],[255,255,0,254])
    record_fields: list[dict] = validate_sort_arguments(4,1,"N","D", 5,1,"N","A")
    # Sorting the file
    records = Records(fn_in, fn_out, eor_tracker, record_fields)
    records.run()
    print("eor", eor_tracker)
    print("eof", eof_tracker)
    print("Done...")

def regex_args(string: str = "/s(4,1,N,D,5,1,N,A) filetype(gp,(63,63),(255,255,0,254))"):
    #print("string:", string)
    sort_args = re.search(r"/s\(([^\)]*)\)", string).group(1).split(',')
    #print("sort_args:", sort_args)
    try:
        filetype_eor_args = re.search(r"filetype\(gp,\((.*)\),\(.*\)\)", string).group(1).split(',')
        #print("filetype_eor_args:", filetype_eor_args)
        filetype_eof_args = re.search(r"filetype\(gp,\(.*\),\((.*)\)\)", string).group(1).split(',')
        #print("filetype_eof_args:", filetype_eof_args)
    except:
        filetype_eor_args = [10]
        filetype_eof_args = [255,255,0,254]
    return sort_args, filetype_eor_args, filetype_eof_args

def command():
    if len(sys.argv) < 4:
        print('EXAMPLE: py opttechsort.py unsorted.txt output.txt "/s(4,1,N,D,5,1,N,D) filetype(gp,(63,63),(255,255,0,254))"')
        return
    fn_in = sys.argv[1]
    fn_out = sys.argv[2]
    string_input: str = sys.argv[3]
    sort_args, ft_eor_args, ft_eof_args = regex_args(string_input)
    # Programmer set variables
    eor_tracker, eof_tracker = filetype("gp",ft_eor_args,ft_eof_args)
    record_fields: list[dict] = validate_sort_arguments(*sort_args)
    # Sorting the file
    records = Records(fn_in, fn_out, eor_tracker, record_fields)
    records.run()
    print(f"Done sorting {fn_in} to {fn_out}")

# =============================
# Main
# =============================

if __name__ == "__main__":
    command()
