#!/usr/bin/env python
"""
Byte array conversion utility.

This script converts raw byte arrays into Python values such as integers,
unsigned integers, floats, strings, and bit strings. It is useful when reading
binary payloads received from hardware, sensors, protocols, or network devices.

Common use cases:
    - decoding Modbus payloads
    - converting binary sensor data to Python types
    - interpreting raw serial or TCP packet values

Notes:
    - byteorder controls the ordering of bytes inside a value
    - wordorder is used for 32-bit and 64-bit values when splitting words
    - supported types include signed/unsigned integers, floats, strings, and bits

Example:
    converter = ByteArrConverter()
    raw = bytearray([0x12, 0x34])
    value = ByteArrConverter.convert(raw, "UINT_16BIT", log=None, byteorder=Endian.Big)
    print(value)  # 0x1234 -> 4660

Reference:
    https://msoe.us/taylor/tutorial/ce2810/csimilar
    https://pymodbus.readthedocs.io/en/latest/source/example/modbus_payload.html
    https://github.com/riptideio/pymodbus/blob/master/pymodbus/payload.py

--------------------------------------------------------------------------
# E.g. Random bytearray format:
#
# - a 8 byte string 'abcdefgh'
# - a 32 bit float 22.34
# - a 16 bit unsigned int 0x1234
# - an 8 bit int 0x12
# - an 8 bit bitstring [0,1,0,1,1,0,1,0]
# - an 32 bit uint 0x12345678
# - an 32 bit signed int -0x1234
# - an 64 bit signed int 0x12345678
# -----------------------------------------------------------------------
# Decoding can be done as per word (wordorder) and bytes in each word (byteorder)
# The wordorder is applicable only for 32 and 64 bit values
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ #
# Possible combinations for word and byte order:

# Word Order - Big                      Byte Order - Big
# word1 =0x1234 word2 = 0x5678

# Word Order - Big                      Byte Order - Little
# word1 =0x3412 word2 = 0x7856

# Word Order - Little                   Byte Order - Big
# word1 = 0x5678 word2 = 0x1234

# Word Order - Little                   Byte Order - Little
# word1 =0x7856 word2 = 0x3412
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ #

# ----------------------------------------------------------------------- #
"""

from logging import Logger
from struct import pack, unpack
from threading import Thread

WC = {
    "b": 1,
    "h": 2,
    "e": 2,
    "i": 4,
    "l": 4,
    "q": 8,
    "f": 4,
    "d": 8
}


class Endian():
    '''
    .. attribute:: Big
       This indicates that the bytes are in big endian format
    .. attribute:: Little
       This indicates that the bytes are in little endian format
    '''
    Big = '>'
    Little = '<'


# ---------------------------------------------------------------------------
# Byte conversion class
# This class converts raw byte arrays into common C/Python-compatible values.
# ---------------------------------------------------------------------------
class ByteArrConverter(Thread):
    '''This class is used to convert bytearray data to c structures like 
        int, float, string of size 8,16,32 bit signed or unsigned data.'''

    def unpackWords(fstring, handle, byteorder, wordorder):
        try:
            ret = None
            wc = WC.get(fstring.lower()) // 2
            up = "!{}H".format(wc)
            handle = unpack(up, handle)
            if wordorder == Endian.Little:
                handle = list(reversed(handle))

            # Repack as unsigned Integer
            pk = byteorder + 'H'
            handle = [pack(pk, p) for p in handle]
            handle = b''.join(handle)
            ret = handle
        except Exception as e:
            raise Exception(f'Error in unpacking words : {handle} : {str(e)}')
        return ret

    def to_bits(val: bytearray):
        try:
            ret = None
            hexStr = ''.join(format(x, '02x') for x in val)
            n = int(str(hexStr), 16)
            bits = ''
            while n > 0:
                bits = str(n % 2) + bits
                n = n >> 1
            ret = bits
        except Exception as e:
            raise Exception(f'Error in bytearray to bits : {val} : {str(e)}')
        return ret

    def to_string(val: bytearray):
        try:
            ret = None
            ret = val.decode('utf-8')
        except Exception as e:
            raise Exception('Error in bytearray to string : {val} : {str(e)}')
        return ret

    def to_8bit_int(val: bytearray, byteorder):
        try:
            ret = None
            pointer = 0x00
            pointer += 1
            fstring = byteorder + 'b'
            handle = val[pointer - 1:pointer]
            ret = unpack(fstring, handle)[0]
        except Exception as e:
            raise Exception(
                f'Error in bytearray to 8bit int : {val} : {str(e)}')
        return ret

    def to_8bit_uint(val: bytearray, byteorder):
        try:
            ret = None
            pointer = 0x00
            pointer += 1
            fstring = byteorder + 'B'
            handle = val[pointer - 1:pointer]
            ret = unpack(fstring, handle)[0]
        except Exception as e:
            raise Exception(
                f'Error in bytearray to 8 bit uint : {val} : {str(e)}')
        return ret

    def to_16bit_int(val: bytearray, byteorder):
        try:
            ret = None
            pointer = 0x00
            pointer += 2
            fstring = byteorder + 'h'
            handle = val[pointer - 2:pointer]
            ret = unpack(fstring, handle)[0]
        except Exception as e:
            raise Exception(
                f'Error in bytearray to 16 bit int : {val} : {str(e)}')
        return ret

    def to_16bit_uint(val: bytearray, byteorder):
        try:
            ret = None
            pointer = 0x00
            pointer += 2
            fstring = byteorder + 'H'
            handle = val[pointer - 2:pointer]
            ret = unpack(fstring, handle)[0]
        except Exception as e:
            raise Exception(
                f'Error in bytearray to 16 bit uint : {val} : {str(e)}')
        return ret

    def to_16bit_float(val: bytearray, byteorder, wordorder):
        try:
            ret = None
            pointer = 0x00
            pointer += 2
            fstring = 'e'
            handle = val[pointer - 2:pointer]
            handle = ByteArrConverter.unpackWords(fstring, handle,
                                                  byteorder, wordorder)
            ret = unpack("!"+fstring, handle)[0]
        except Exception as e:
            raise Exception(
                f'Error in bytearray to 16 bit float : {val} : {str(e)}')
        return ret

    def to_32bit_int(val: bytearray, byteorder, wordorder):
        try:
            ret = None
            pointer = 0x00
            pointer += 4
            fstring = 'i'
            handle = val[pointer - 4:pointer]
            handle = ByteArrConverter.unpackWords(fstring, handle,
                                                  byteorder, wordorder)
            ret = unpack("!"+fstring, handle)[0]
        except Exception as e:
            raise Exception(
                f'Error in bytearray to 32 bit int : {val} : {str(e)}')
        return ret

    def to_32bit_uint(val: bytearray, byteorder, wordorder):
        try:
            ret = None
            pointer = 0x00
            pointer += 4
            fstring = 'I'
            handle = val[pointer - 4:pointer]
            handle = ByteArrConverter.unpackWords(fstring, handle,
                                                  byteorder, wordorder)
            ret = unpack("!"+fstring, handle)[0]
        except Exception as e:
            raise Exception(
                f'Error in bytearray to 32 bit uint : {val} : {str(e)}')
        return ret

    def to_32bit_float(val: bytearray, byteorder, wordorder):
        try:
            ret = None
            pointer = 0x00
            pointer += 4
            fstring = 'f'
            handle = val[pointer - 4:pointer]
            handle = ByteArrConverter.unpackWords(fstring, handle,
                                                  byteorder, wordorder)
            ret = unpack("!"+fstring, handle)[0]
        except Exception as e:
            raise Exception(
                f'Error in bytearray to 32 bit signed float : {val} : {str(e)}')
        return ret

    def to_64bit_int(val: bytearray, byteorder, wordorder):
        try:
            ret = None
            pointer = 0x00
            pointer += 8
            fstring = 'q'
            handle = val[pointer - 8:pointer]
            handle = ByteArrConverter.unpackWords(fstring, handle,
                                                  byteorder, wordorder)
            ret = unpack("!"+fstring, handle)[0]

        except Exception as e:
            raise Exception(
                f'Error in bytearray to 64 bit int : {val} : {str(e)}')
        return ret

    def to_64bit_uint(val: bytearray, byteorder, wordorder):
        try:
            ret = None
            pointer = 0x00
            pointer += 8
            fstring = 'Q'
            handle = val[pointer - 8:pointer]
            handle = ByteArrConverter.unpackWords(fstring, handle,
                                                  byteorder, wordorder)
            ret = unpack("!"+fstring, handle)[0]
        except Exception as e:
            raise Exception(
                'Error in bytearray to 64 bit uint : {val} : {str(e)}')
        return ret

    def to_64bit_float(val: bytearray, byteorder, wordorder):
        try:
            ret = None
            pointer = 0x00
            pointer += 8
            fstring = 'd'
            handle = val[pointer - 8:pointer]
            handle = ByteArrConverter.unpackWords(fstring, handle,
                                                  byteorder, wordorder)
            ret = unpack("!"+fstring, handle)[0]
        except Exception as e:
            raise Exception(
                f'Error in bytearray to 64 bit signed double : {val} : {str(e)}')
        return ret

    # -----------------------------------------------------------------------
    # Convert a raw byte array into a target data type.
    # Example:
    #   ByteArrConverter.convert(raw_bytes, "INT_16BIT", log, Endian.Big)
    # -----------------------------------------------------------------------
    @staticmethod
    def convert(byteArrayData: bytearray, data_type: str, log: Logger, byteorder=Endian.Big, wordorder=Endian.Big):
        convertedVal = None
        try:
            if data_type.upper() == "BITS":
                convertedVal = ByteArrConverter.to_bits(byteArrayData)
            elif data_type.upper() == "STRING":
                convertedVal = ByteArrConverter.to_string(byteArrayData)
            elif data_type.upper() == "INT_8BIT":
                convertedVal = ByteArrConverter.to_8bit_int(byteArrayData,
                                                            byteorder=byteorder)
            elif data_type.upper() == "UINT_8BIT":
                convertedVal = ByteArrConverter.to_8bit_uint(byteArrayData,
                                                             byteorder=byteorder)
            elif data_type.upper() == "INT_16BIT":
                convertedVal = ByteArrConverter.to_16bit_int(byteArrayData,
                                                             byteorder=byteorder)
            elif data_type.upper() == "UINT_16BIT":
                convertedVal = ByteArrConverter.to_16bit_uint(byteArrayData,
                                                              byteorder=byteorder)
            elif data_type.upper() == "FLOAT_16BIT":
                convertedVal = ByteArrConverter.to_16bit_float(byteArrayData,
                                                               byteorder=byteorder,
                                                               wordorder=wordorder)
            elif data_type.upper() == "INT_32BIT":
                convertedVal = ByteArrConverter.to_32bit_int(byteArrayData,
                                                             byteorder=byteorder,
                                                             wordorder=wordorder)
            elif data_type.upper() == "UINT_32BIT":
                convertedVal = ByteArrConverter.to_32bit_uint(byteArrayData,
                                                              byteorder=byteorder,
                                                              wordorder=wordorder)
            elif data_type.upper() == "FLOAT_32BIT":
                convertedVal = ByteArrConverter.to_32bit_float(byteArrayData,
                                                               byteorder=byteorder,
                                                               wordorder=wordorder)
            elif data_type.upper() == "INT_64BIT":
                convertedVal = ByteArrConverter.to_64bit_int(byteArrayData,
                                                             byteorder=byteorder,
                                                             wordorder=wordorder)
            elif data_type.upper() == "UINT_64BIT":
                convertedVal = ByteArrConverter.to_64bit_uint(byteArrayData,
                                                              byteorder=byteorder,
                                                              wordorder=wordorder)
            elif data_type.upper() == "FLOAT_64BIT":
                convertedVal = ByteArrConverter.to_64bit_float(byteArrayData,
                                                               byteorder=byteorder,
                                                               wordorder=wordorder)
            else:
                raise Exception(
                    f'Bytearray convertion not implemented : {data_type} : {byteArrayData}')
        except Exception as e:
            log.error(str(e))
        return convertedVal

raw = bytearray([0x12, 0x34])
value = ByteArrConverter.convert(raw, "UINT_16BIT", log=None, byteorder=Endian.Big)
print(value)  # 0x1234 -> 4660