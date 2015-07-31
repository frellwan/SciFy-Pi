"""
DF1 Request/Response Decoder Factories
-------------------------------------------

The following factories make it easy to decode request/response messages.
To add a new request/response pair to be decodeable by the library, simply
add them to the respective function lookup table (order doesn't matter, but
it does help keep things organized).

Regardless of how many functions are added to the lookup, O(1) behavior is
kept as a result of a pre-computed lookup dictionary.
"""

from serialexceptions import SerialException
from DF1commands import *

import struct
import sys
#sys.path.insert(0, '/home/pi/projects/MTrin-New')
from MTrimCommands import ParameterSendRequest
#---------------------------------------------------------------------------#
# Logging
#---------------------------------------------------------------------------#
import logging
_logger = logging.getLogger(__name__)


#---------------------------------------------------------------------------#
# Client Decoder
#---------------------------------------------------------------------------#
class ClientDecoder(object):
    ''' Response Message Factory (Client)

    To add more implemented functions, simply add them to the list
    '''
    __function_table = [
                        protectedReadRequest,
                        protectedWriteRequest,
                        Command_0F_Response
                        ]
    def __init__(self):
        ''' Initializes the client lookup tables
        '''
        #self.client = client
        functions = set(f.cmd for f in self.__function_table)
        self.__lookup = dict([(f.cmd, f) for f in self.__function_table])
        self.__sub_lookup = dict((f, {}) for f in functions)
        for f in self.__function_table:
            self.__sub_lookup[f.cmd][f.function] = f

    def lookupPduClass(self, function_code):
        ''' Use `function_code` to determine the class of the PDU.
        :param function_code: The function code specified in a frame.
        :returns: The class of the PDU that has a matching `function_code`.
        '''
        return self.__lookup.get(function_code, ExceptionResponse)
    
    def decode(self, message, request):
        ''' Wrapper to decode a response packet

        :param message: The raw packet to decode
        :return: The decoded message or None if error
        '''
        self.request = request
        if (message[0] == '\x10'):
            # This is a response from a DF1 command
            try:
                return self._helper(message)
            except SerialException, er:
                _logger.error("Unable to decode response %s" % er)
            return None
        else:
            # This is an ASCII write (AWT) instruction from the SLC
            result = ParameterSendRequest(skip_encode = True)
            return result.decode(message)

    def _helper(self, data):
        '''
        This factory is used to generate the correct response object
        from a valid response packet. This decodes from a list of the
        currently implemented request types.

        :param data: The response packet to decode
        :returns: The decoded request or an exception response object
        '''
        command = ord(data[4])          # The command byte
        _logger.debug("Factory Response[%d]" % command)
        if (command & 64):
            ''' If bit 6 of the command byte is 1 this means it is a response
                to a sent command
            '''
            error_code, = struct.unpack('>B', data[5])
            _logger.debug("Factory Response[%c]" % error_code)

            if (error_code != 0):
                raise SerialException("Error in response: %d" % int(error_code))
                return None
            else:
                response = self.__lookup.get(command, lambda: None)(self.request)
                response.decode(data)

        else:
            ''' If bit 6 of the command byte is 0 then this is a command
                sent from the PLC. We need to decode and respond.
            '''
            function = ord(data[6])     # The function byte
            print "cmd: ", command, "fnc: ", function
            response = self.__sub_lookup[command][function]()
            response.decode(data)
            
        if not response:
            raise SerialException("Unknown response %d" % function_code)

        return response

#---------------------------------------------------------------------------#
# Exported symbols
#---------------------------------------------------------------------------#
__all__ = ['ClientDecoder']
