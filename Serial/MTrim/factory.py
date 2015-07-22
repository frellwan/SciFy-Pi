"""
MTrim Request/Response Decoder Factories
-------------------------------------------

The following factories make it easy to decode request/response messages.
To add a new request/response pair to be decodeable by the library, simply
add them to the respective function lookup table (order doesn't matter, but
it does help keep things organized).

Regardless of how many functions are added to the lookup, O(1) behavior is
kept as a result of a pre-computed lookup dictionary.
"""

from serialexceptions import SerialException
from MTrimCommands import MTrimResponse

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

    def __init__(self):
        ''' Initializes the client lookup tables
        '''
        
    def decode(self, message):
        ''' Wrapper to decode a response packet

        :param message: The raw packet to decode
        :return: The decoded message or None if error
        '''
        try:
            return self._helper(message)
        except SerialException, er:
            _logger.error("Unable to decode response %s" % er)
        return None

    def _helper(self, data):
        '''
        This factory is used to generate the correct response object
        from a valid response packet. This decodes from a list of the
        currently implemented request types.

        :param data: The response packet to decode
        :returns: The decoded request or an exception response object
        '''
        error_code = data[3]
        _logger.debug("Factory Response[%c]" % error_code)

        if (error_code != '@'):
            raise SerialException("Error in response: %c" % error_code)
            return None
        else:
            response = MTrimResponse()
            response.decode(data)
            
        return response

#---------------------------------------------------------------------------#
# Exported symbols
#---------------------------------------------------------------------------#
__all__ = ['ClientDecoder']

