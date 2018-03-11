serial data structure:

   For synchronization purposes, the following scheme was chosen:
   A0 data:   A09 (MSB) A08 A07 A06 A05 A04 A03 A02 A01 A00 (LSB)
   sent as byte 1:   1 1 1 A09 A08 A07 A06 A05
       and byte 2:   0 1 1 A04 A03 A02 A01 A00

           byte 1  A0 5 most significant bits + 224 (128+64+32), legitimate values are between 224 and 255
           byte 2  A0 5 least significant bits + 96 (64+32)    , legitimate values are between 96 and 127
