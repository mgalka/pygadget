from dataclasses import dataclass

hid_report_desc = bytes(
    (
        0x05, 0x01,
        0x09, 0x06,
        0xa1, 0x01,
        0x05, 0x07,
        0x19, 0xe0,
        0x29, 0xe7,
        0x15, 0x00,
        0x25, 0x01,
        0x75, 0x01,
        0x95, 0x08,
        0x81, 0x02,
        0x95, 0x01,
        0x75, 0x08,
        0x81, 0x03,
        0x95, 0x05,
        0x75, 0x01,
        0x05, 0x08,
        0x19, 0x01,
        0x29, 0x05,
        0x91, 0x02,
        0x95, 0x01,
        0x75, 0x03,
        0x91, 0x03,
        0x95, 0x06,
        0x75, 0x08,
        0x15, 0x00,
        0x25, 0x65,
        0x05, 0x07,
        0x19, 0x00,
        0x29, 0x65,
        0x81, 0x00,
        0xc0,
    )
)

desc = b'\\x05\\x01\\x09\\x06\\xa1\\x01\\x05\\x07\\x19\\xe0\\x29\\xe7\\x15\\x00\\x25\\x01\\x75\\x01\\x95\\x08\\x81\\x02\\x95\\x01\\x75\\x08\\x81\\x03\\x95\\x05\\x75\\x01\\x05\\x08\\x19\\x01\\x29\\x05\\x91\\x02\\x95\\x01\\x75\\x03\\x91\\x03\\x95\\x06\\x75\\x08\\x15\\x00\\x25\\x65\\x05\\x07\\x19\\x00\\x29\\x65\\x81\\x00\\xc0'

@dataclass
class HIDGadgetFunctionAttributes:
    protocol: int = 1
    report_desc: bytes = b''
    report_length: int = 8
    subclass: int = 0
