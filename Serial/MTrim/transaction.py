'''
Collection of transaction based abstractions
'''

import sys
import struct
import socket

from serialexceptions import *
from constants  import Defaults
MAXENQ = 3

#---------------------------------------------------------------------------#
# Logging
#---------------------------------------------------------------------------#
import logging
_logger = logging.getLogger(__name__)


#---------------------------------------------------------------------------#
# The Global Transaction Manager
#---------------------------------------------------------------------------#

class DictTransactionManager(object):
    ''' Impelements a transaction for a manager where the
    results are keyed based on the supplied transaction id.
    '''

    def __init__(self, client, **kwargs):
        ''' Initializes an instance of the TransactionManager
        :param client: The client socket wrapper
        '''
        self.transactions = {}
        self.tid = Defaults.TransactionId
        self.client = client

    def __iter__(self):
        ''' Iterater over the current managed transactions
        :returns: An iterator of the managed transactions
        '''
        return iter(self.transactions.keys())

    def addTransaction(self, request, tid=None):
        ''' Adds a transaction to the handler
        This holds the requets in case it needs to be resent.
        After being sent, the request is removed.
        :param request: The request to hold on to
        :param tid: The overloaded transaction id to use
        '''
        tid = tid if tid != None else request.transaction_id
        _logger.debug("adding transaction %d" % tid)
        self.transactions[tid] = request

    def getTransaction(self, tid):
        ''' Returns a transaction matching the referenced tid
        If the transaction does not exist, None is returned
        :param tid: The transaction to retrieve
        '''
        _logger.debug("getting transaction %d" % tid)
        return self.transactions.pop(tid, None)

    def delTransaction(self, tid):
        ''' Removes a transaction matching the referenced tid
        :param tid: The transaction to remove
        '''
        _logger.debug("deleting transaction %d" % tid)
        self.transactions.pop(tid, None)

    def getNextTID(self):
        ''' Retrieve the next unique transaction identifier
        This handles incrementing the identifier after
        retrieval
        :returns: The next unique transaction identifier
        '''
        self.tid = (self.tid + 1) & 0xffff
        return self.tid

    def reset(self):
        ''' Resets the transaction identifier '''
        self.tid = Defaults.TransactionId
        self.transactions = type(self.transactions)()


class FifoTransactionManager(object):
    ''' Impelements a transaction for a manager where the
    results are returned in a FIFO manner.
    '''

    def __init__(self, client, **kwargs):
        ''' Initializes an instance of the TransactionManager

        :param client: The client socket wrapper
        '''
        self.transactions = []
        self.tid = Defaults.TransactionId
        self.client = client

    def __iter__(self):
        ''' Iterater over the current managed transactions

        :returns: An iterator of the managed transactions
        '''
        return iter(self.transactions)

    def addTransaction(self, request, tid=None):
        ''' Adds a transaction to the handler

        This holds the requets in case it needs to be resent.
        After being sent, the request is removed.

        :param request: The request to hold on to
        :param tid: The overloaded transaction id to use
        '''
        tid = tid if tid != None else request.transaction_id
        _logger.debug("adding transaction %d" % tid)
        self.transactions.append(request)

    def getTransaction(self, tid):
        ''' Returns a transaction matching the referenced tid

        If the transaction does not exist, None is returned

        :param tid: The transaction to retrieve
        '''
        _logger.debug("getting transaction %s" % str(tid))
        return self.transactions.pop(0) if self.transactions else None

    def delTransaction(self, tid):
        ''' Removes a transaction matching the referenced tid

        :param tid: The transaction to remove
        '''
        _logger.debug("deleting transaction %d" % tid)
        if self.transactions: self.transactions.pop(0)

    def getNextTID(self):
        ''' Retrieve the next unique transaction identifier

        This handles incrementing the identifier after
        retrieval

        :returns: The next unique transaction identifier
        '''
        self.tid = (self.tid + 1) & 0xffff
        return self.tid

    def reset(self):
        ''' Resets the transaction identifier '''
        self.tid = Defaults.TransactionId
        self.transactions = type(self.transactions)()


#---------------------------------------------------------------------------#
# DF1  Message
#---------------------------------------------------------------------------#
class SocketFramer(object):
    ''' DF1 Socket Frame controller with timeout capability


        * length = uid + function code + data
        * The -1 is to account for the uid byte
    '''

    def __init__(self, decoder):
        ''' Initializes a new instance of the framer

        :param decoder: The decoder factory implementation to use
        '''
        self.__buffer = ''
        self.__header = {'sts':'\x00', 'len':0, 'tid':'\x00\x00'}
        self.__hsize  = '\x02'
        self.decoder  = decoder
        self.packetStarted = False
        self.packetEnded = False
        self.NAKCount = 0
        self.ENQCount = 0
        self.LastByte = 0
        self.currentByte = 0


    #-----------------------------------------------------------------------#
    # Private Helper Functions
    #-----------------------------------------------------------------------#
    def addClient(client):
        self.client = client
    
    def checkFrame(self):
        ''' Check and decode the next frame

        :returns: True if we have a complete packet,
                  False otherwise
        '''

        #############################################
        # If we have received an ETX string, has
        # CRC been received yet (2 additional bytes)
        #############################################
        if (self.packetEnded and len(self.__buffer) >= self.__header['len']+2):
            self.__header['len'] = self.__header['len']+2
            return True

        while ((self.currentByte < len(self.__buffer)) and not self.packetEnded):
            b = self.__buffer[self.currentByte]
            ############################
            # Unescape DLE DLE Sequence
            ############################
            if (self.packetStarted):
                if (self.LastByte == '\x10' and b == '\x10'):
                    self.__buffer = self.__buffer[:self.currentByte] + self.__buffer[self.currentByte+1:]
                    self.LastByte = 0
                    b = 0
                    self.currentByte -= 1

                # Is there another start sequence?
                if (self.LastByte == '\x10' and b == '\x02'):
                    self.advanceFrame(len(self.__buffer[:self.currentByte-1]))
                    self.currentByte = 1


            ##################
            # DLE Character
            ##################
            if (self.LastByte == '\x10'):
                ##################
                # STX Sequence
                ##################
                if (b == '\x02'): 
                    self.packetStarted = True
 
                    if (self.currentByte > 1):
                        self.advanceFrame(len(self.__buffer[:self.currentByte-1]))
                        self.currentByte = 1

                ##################
                # ETX Sequence
                ##################
                if ((self.packetStarted and b == '\x03')):
                    self.packetEnded = True
                    self.__header['len'] = len(self.__buffer[:self.currentByte+1])
                    self.__header['tid'], = struct.unpack('>H', self.__buffer[6:8])
                    self.__header['sts'], = struct.unpack('>B',self.__buffer[5])
                    if (len(self.__buffer) >= self.__header['len']+2):
                        self.__header['len'] = self.__header['len']+2
                        return True

                ##################
                # ACK Sequence
                ##################
                if (b == '\x06'):
                    self.advanceFrame(len(self.__buffer[:self.currentByte+1]))
                    b = 0
                    self.currentByte = -1

                ##################
                # NAK Sequence
                ##################
                if (b == '\x15'):
                    self.NAKCount += 1
                    if (self.NAKCount > MAXENQ):
                        raise IOError("NAK Limit Exceeded")
                    else:
                        self.client.transport.write(self.request.encode())
                        self.advanceFrame(len(self.__buffer[:self.currentByte+1]))
                                                   
                ##################
                # ENQ Sequence
                ##################
                if (b == '\x05'):
                    self.ENQCount += 1
                    if (self.ENQCount > MAXENQ):
                        _logger.debug("ENQ Limit Exceeded")
                    else:
                        self.client.transport.write(self.request.encode())

                    self.advanceFrame(len(self.__buffer[:self.currentByte+1]))                    


            self.LastByte = b
            self.currentByte += 1
        return False          

    def isFrameReady(self):
        ''' Check if we should continue decode logic
        This is meant to be used in a while loop in the decoding phase to let
        the decoder know that there is still data in the buffer.

        :returns: True if ready, False otherwise
        '''
        return len(self.__buffer) > 1

    def advanceFrame(self, length):
        ''' Skip over the current framed message
        This allows us to skip over the current message after we have processed
        it or determined that it contains an error. It also has to reset the
        current frame header handle
        '''
        self.__buffer = self.__buffer[length:]
        self.currentByte = 0


    def addToFrame(self, message):
        ''' Adds new packet data to the current frame buffer

        :param message: The most recent packet
        '''
        self.__buffer += message

    def getFrame(self):
        ''' Return the next frame from the buffered data

        :returns: The next full frame buffer
        '''
        start  = 0
        end    = self.__header['len']+3
        buffer = self.__buffer[start:end]
        return buffer

    #-----------------------------------------------------------------------#
    # Public Member Functions
    #-----------------------------------------------------------------------#
    def processIncomingPacket(self, data, request, callback):
        ''' The new packet processing pattern

        This takes in a new request packet, adds it to the current
        packet stream, and performs framing on it. That is, checks
        for complete messages, and once found, will process all that
        exist.  This handles the case when we read N + 1 or 1 / N
        messages at a time instead of 1.

        The processed and decoded messages are pushed to the callback
        function to process and send.

        :param data: The new packet data
        :param callback: The function to send results to
        '''
        self.request = request
        self.addToFrame(data)
        while self.isFrameReady():
            if self.checkFrame():
                result = self.decoder.decode(self.getFrame(), request)
                self.advanceFrame(self.__header['len'])
                self.packetStarted = False
                self.packetEnded = False
                callback(result)  # defer this
            else:
                break

    def buildPacket(self, message):
        ''' Creates a ready to send modbus packet

        :param message: The populated request/response to send
        '''
        data = message.encode()
        return data


#---------------------------------------------------------------------------#
# ASCII Message
#---------------------------------------------------------------------------#
class AsciiFramer(object):
    '''
    ASCII Frame Controller::

        [ Start ][ Address ][ Type ][ Parameter ][ Format ][ Data ][ End ]
          1c         2c        2c         2C        1C        5C      1C

        * data can be 5 chars
        * end is '\x03' 
        * start is '\x02'

    This framer is used for serial transmission.  Unlike the RTU protocol,
    the data in this framer is transferred in plain text ascii.
    '''

    def __init__(self, decoder):
        ''' Initializes a new instance of the framer

        :param decoder: The decoder implementation to use
        '''
        self.__buffer = ''
        self.__header = {'err':'@', 'len':0, 'uid':0x00}
        self.__hsize  = 0x00
        self.__start  = '\x02'
        self.__end    = '\x03'
        self.decoder  = decoder

    #-----------------------------------------------------------------------#
    # Private Helper Functions
    #-----------------------------------------------------------------------#
    def checkFrame(self):
        ''' Check and decode the next frame

        :returns: True if we successful, False otherwise
        '''
        start = self.__buffer.find(self.__start)
        if start == -1: return False
        if start > 0 :  # go ahead and skip old bad data
            self.__buffer = self.__buffer[start:]
            start = 0

        end = self.__buffer.find(self.__end)
        if (end != -1):
            self.__header['len'] = end
            self.__header['uid'] = int(self.__buffer[1:3], 16)
            self.__header['err'] = self.__buffer[3]
            if (self.__header['err'] == '@'):
                return True
        return False

    def advanceFrame(self):
        ''' Skip over the current framed message
        This allows us to skip over the current message after we have processed
        it or determined that it contains an error. It also has to reset the
        current frame header handle
        '''
        self.__buffer = self.__buffer[self.__header['len']+1:]
        self.__header = {'err':'@', 'len':0, 'uid':0x00}

    def isFrameReady(self):
        ''' Check if we should continue decode logic
        This is meant to be used in a while loop in the decoding phase to let
        the decoder know that there is still data in the buffer.

        :returns: True if ready, False otherwise
        '''
        return len(self.__buffer) > 1

    def addToFrame(self, message):
        ''' Add the next message to the frame buffer
        This should be used before the decoding while loop to add the received
        data to the buffer handle.

        :param message: The most recent packet
        '''
        self.__buffer += message

    def getFrame(self):
        ''' Get the next frame from the buffer

        :returns: The frame data or ''
        '''
        start  = 0
        end    = self.__header['len']+1
        buffer = self.__buffer[start:end]
        return buffer

    def populateResult(self, result):
        ''' Populates the modbus result header

        The serial packets do not have any header information
        that is copied.

        :param result: The response packet
        '''
        result.unit_id = self.__header['uid']

    #-----------------------------------------------------------------------#
    # Public Member Functions
    #-----------------------------------------------------------------------#
    def processIncomingPacket(self, data, request, callback):
        ''' The new packet processing pattern

        This takes in a new request packet, adds it to the current
        packet stream, and performs framing on it. That is, checks
        for complete messages, and once found, will process all that
        exist.  This handles the case when we read N + 1 or 1 / N
        messages at a time instead of 1.

        The processed and decoded messages are pushed to the callback
        function to process and send.

        :param data: The new packet data
        :param callback: The function to send results to
        '''
        self.addToFrame(data)
        while self.isFrameReady():
            if self.checkFrame():
                result = self.decoder.decode(self.getFrame())
                if result is None:
                    raise IOException("Unable to decode response")
                self.populateResult(result)
                self.advanceFrame()
                callback(result)  # defer this
            else: break

    def buildPacket(self, message):
        ''' Creates a ready to send DF1 packet
        Built off of a  DF1 request/response

        :param message: The request/response to send
        :return: The encoded packet
        '''
        data = message.encode()
        return data



#---------------------------------------------------------------------------#
# Exported symbols
#---------------------------------------------------------------------------#
__all__ = [
    "FifoTransactionManager", "DictTransactionManager"
    "SocketFramer", "AsciiFramer",
]
