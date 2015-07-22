"""
Implementation of a Serial Client Using Twisted
--------------------------------------------------

Example run::

    from twisted.internet import reactor, protocol
    from async import SerialClientProtocol

    def printResult(result):
        print "Result: %d" % result.Data

    def process(client):
        result = client.sendRequest(protectedReadRequest(1, 'N7:0')
        result.addCallback(printResult)
        reactor.callLater(1, reactor.stop)

    serial = serialport.SerialPort(SerialClientProtocol, '/dev/ttyUSB0', reactor)
    reactor.callWhenRunning(process)

    if __name__ == "__main__":
       reactor.callLater(1, process)
       reactor.run()
"""

from twisted.internet import defer, protocol
from twisted.protocols.basic import LineReceiver
from twisted.python.failure import Failure
from serialexceptions import ConnectionException
from transaction import SocketFramer, FifoTransactionManager, DictTransactionManager
from twisted.python import usage
from twisted.protocols.policies import TimeoutMixin
from factory import ClientDecoder


class Options(usage.Options):
    optParameters = [['config', 'c', './config.ini']]

TIMEOUT = 1
MAXENQ = 3
#---------------------------------------------------------------------------#
# Logging
#---------------------------------------------------------------------------#
import logging
_logger = logging.getLogger(__name__)

#---------------------------------------------------------------------------#
# Connected Client Protocols
#---------------------------------------------------------------------------#
class SerialClientProtocol(protocol.Protocol, TimeoutMixin):
    '''
    This represents the base asynchronous client protocol.  All the application
    layer code is deferred to a higher level wrapper.
    '''    
    
    def __init__(self, framer=None, **kwargs):
        ''' Initializes the framer module

        :param framer: The framer to use for the protocol
        '''
        self._connected = False
        self.framer = framer or SocketFramer(ClientDecoder())
        if isinstance(self.framer, SocketFramer):
            self.transaction = DictTransactionManager(self, **kwargs)
        else:
            self.transaction = FifoTransactionManager(self, **kwargs)
        self.lock = defer.DeferredLock()
        self.currentRequest = None
        self._reconnecting = False
        self.deferred = None
        self.lastNAK = '\x10\x15'
        self.ENQCount = 0
        self.NAKCount = 0

    def connectionMade(self):
        ''' Called upon a successful client connection.
        '''
        _logger.debug("Client connected to Serial Device")
        self._connected = True       

    def connectionLost(self, reason):
        ''' Called upon a client disconnect

        :param reason: The reason for the disconnect
        '''
        _logger.debug("Client disconnected from Serial Device: %s" % reason)
        print "Client disconnected from Serial Device: ", reason
        self._connected = False

        self.reconnect()
     
    def sendRequest(self, request):
        '''The main entry into the serial link. Any information sent across
           the serial link should be sent throgh this method.

        :param request: the class that holds the data to be sent 
        :return: a deferred that promises a class that holds the response
        '''
        d = self.lock.run(self.execute, request)
        d.addCallback(self.ackPacket)
        d.addErrback(self.errorHandler, 'sendRequest failed')
        return d

    def ackPacket(self, packet):
        '''ACK Message, reset counters/timers and release lock to prepare for next message
           Overide if you need additional code such as sending an ACK message
           for example self.transport.write('\x10\x06')

        :param packet: the class returned from the deferred that called this
        :return: Pass along the class that was returned from the deferred
        '''
        self.resetTimeout()
        self.ENQCount = 0
        self.NAKCount = 0
        self.setTimeout(None)
        self.deffered = None
        
        return packet

    def dataReceived(self, data):
        ''' Get response, check for valid message, decode result

        :param data: The data returned from the server
        '''
        self.framer.processIncomingPacket(data, self.currentRequest, self._handleResponse)


    def execute(self, request):
        ''' Write the encoded request across the serial link

        :param request: the class that holds the data to be sent
        :returns: A deferred linked to the current request
        '''
        self.currentRequest = request
        request.transaction_id = self.transaction.getNextTID()
        packet = self.framer.buildPacket(request)
        self.transport.write(packet)
        self.setTimeout(TIMEOUT)

        self.deferred = self._buildResponse(request.transaction_id)
        return self.deferred
           
    def _handleResponse(self, reply):
        ''' Handle the response recieved on the serial link
            and link to correct deferred

        :param reply: The received data to process
        '''
        if reply is not None:
            if (reply == '\x10\x15'):
                self.NAKCount += 1
                if (self.NAKCount > MAXENQ):
                    #self.result.errBack(defer.fail(IOError("NAK Limit Exceeded")))
                    pass
                else:
                    self.transport.write(self.lastNAK)

            elif (reply == '\x10\x05'):
                self.ENQCount += 1
                if (self.ENQCount > MAXENQ):
                    print("ENQ Limit Exceeded")
                else:
                    self.transport.write(self.framer.buildPacket(self.currentRequest))

            else:
                tid = reply.transaction_id
                handler = self.transaction.getTransaction(tid)
                if handler:
                    handler.callback(reply)
                else: _logger.debug("Unrequested message: " + str(reply))

    def _buildResponse(self, tid):
        ''' Helper method to return a deferred response
        for the current request.

        :param tid: The transaction identifier for this response
        :returns: A defer linked to the latest request
        '''            
        d = defer.Deferred()
        self.transaction.addTransaction(d, tid)
        return d

    def timeoutConnection(self):
        print "Timed Out - send ENQ"
        ##############
        # Send ENQ
        ##############
        self.ENQCount += 1
        if (self.ENQCount <= MAXENQ):
            self.resetTimeout()
            self.setTimeout(TIMEOUT)
            self.transport.write('\x10\x05')

        ################################
        # Release Lock for next message
        ################################
        else:
            _logger.debug("ENQ Limit reached")
            self.setTimeout(None)
            self.NAKCount = 0
            self.ENQCount = 0
            if (self._connected and self.deferred):
                #self.deferred = None
                #self.lock.release()
                self.deferred.errback(ConnectionException("Timed Out"))
            
        
    def errorHandler(self, error, msg=''):
        stringMsg = msg + ': Failed.  Error was: ', error.value
        _logger.debug(stringMsg)


#---------------------------------------------------------------------------#
# Client Factories
#---------------------------------------------------------------------------#
class SerialClientFactory(protocol.ReconnectingClientFactory):
    ''' Simple client protocol factory '''

    protocol = SerialClientProtocol

#---------------------------------------------------------------------------#
# Exported symbols
#---------------------------------------------------------------------------#
__all__ = [
    "SerialClientProtocol", "SerialClientFactory",
]

