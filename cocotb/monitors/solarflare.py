''' Copyright (c) 2013 Potential Ventures Ltd
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Potential Ventures Ltd nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. '''
"""
Monitors for Altera Avalon interfaces.

See http://www.altera.co.uk/literature/manual/mnl_avalon_spec.pdf

NB Currently we only support a very small subset of functionality
"""

from cocotb.decorators import coroutine
from cocotb.triggers import RisingEdge, ReadOnly
from cocotb.monitors import BusMonitor
from cocotb.utils import hexdump

# Solarflare specific
from modules.sf_streaming.model.sf_streaming import SFStreamingData

class SFStreaming(BusMonitor):
    """This is the Solarflare Streaming bus as defined by the FDK.

    Expect to see a 72-bit bus (bottom 64 bits data, top 8 bits are ECC)

    TODO:
        Metaword / channel bits
        ECC checking
    """
    _signals = ["startofpacket", "endofpacket", "ready", "empty", "channel", "error", "valid", "data"]


    @coroutine
    def _monitor_recv(self):
        """Watch the pins and reconstruct transactions"""

        # Avoid spurious object creation by recycling
        clkedge = RisingEdge(self.clock)
        rdonly  = ReadOnly()
        word = SFStreamingData()

        pkt = ""

        while True:
            yield clkedge
            yield rdonly

            if self.bus.valid.value and self.bus.startofpacket.value:
                vec = self.bus.data.value
                pkt += vec.buff[1:][::-1]
                while True:
                    yield clkedge
                    yield rdonly
                    if self.bus.valid.value:
                        vec = self.bus.data.value
                        pkt += vec.buff[1:][::-1]
                        if self.bus.endofpacket.value:
                            # Truncate the empty bits
                            if self.bus.empty.value.value:
                                pkt = pkt[:-self.bus.empty.value.value]
                            self.log.info("Recieved a packet of %d bytes", len(pkt))
                            self.log.debug(hexdump(pkt))
                            self._recv(pkt)
                            pkt = ""
                            break