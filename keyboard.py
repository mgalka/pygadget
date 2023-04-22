from curses.ascii import isupper
from enum import Enum
from keyboard_layout_us import ASCII_TO_KEYCODE


class ModifierKeys(Enum):
    LCTRL = 0b00000001
    LSHIFT = 0b00000010
    LALT = 0b00000100
    LGUI = 0b00001000
    RCTRL = 0b00010000
    RSHIFT = 0b00100000
    RALT = 0b01000000
    RGUI = 0b10000000


class ReportWriter:
    NULL_CHAR = chr(0)
    CHARMAP = ASCII_TO_KEYCODE

    def __init__(self, device: str) -> None:
        self.device = open(device, 'rb+')

    def send(self, report: str) -> None:
        self.device.write(report.encode())

    def write_text(self, text: str) -> None:
        '''Write text, convert capital letters to combinations
        '''
        for letter in text:
            if letter.isupper():
                modifier = chr(ModifierKeys.RSHIFT.value)
                letter = letter.lower()
            else:
                modifier = ReportWriter.NULL_CHAR
            letter = chr(ReportWriter.CHARMAP[ord(letter)])
            self.send(f'{modifier}{ReportWriter.NULL_CHAR}{letter}' +
                      ReportWriter.NULL_CHAR * 5)
            self.send(ReportWriter.NULL_CHAR * 8)


if __name__ == '__main__':
    writer = ReportWriter('/dev/hidg0')
    writer.write_text('PyCon US 2023')
