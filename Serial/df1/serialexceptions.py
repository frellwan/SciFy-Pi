'''
Pymodbus Exceptions
--------------------

Custom exceptions to be used in the Modbus code.
'''

#---------------------------------------------------------------------------#
# Generic
#---------------------------------------------------------------------------#
class Singleton(object):
    '''
    Singleton base class
    http://mail.python.org/pipermail/python-list/2007-July/450681.html
    '''
    def __new__(cls, *args, **kwargs):
        ''' Create a new instance
        '''
        if '_inst' not in vars(cls):
            cls._inst = object.__new__(cls)
        return cls._inst

#---------------------------------------------------------------------------#
# Exception PDU's
#---------------------------------------------------------------------------#
class Exceptions(Singleton):
    '''
    An enumeration of the valid STS error codes
    '''
    Success_no_error        = 0x00
    DSTNodeOutofBuffer      = 0x01
    DESTNoAck               = 0x02
    DupTokenHolder          = 0x03
    LocalPortComm           = 0x04
    AppLayerTimeOut         = 0x05
    DuplicateNode           = 0x06
    StationOffLine          = 0x07 
    HardwareFault           = 0x08
    IllegalCommand          = 0x10
    HostNoComm              = 0x20
    RemoteNodeMissing       = 0x30
    HostHardwareFault       = 0x40
    AddrProblem             = 0x50
    FunctionNotAllowed      = 0x60
    ProcessorProgramMode    = 0x70
    CompModeFileMissing     = 0x80
    RemoteNodeBuffer        = 0x90
    WaitACK                 = 0xA0
    DownloadProblem         = 0xB0
    WaitACK                 = 0xC0
    ErrorCodeinEXTSTS       = 0xF0
    

    @classmethod
    def decode(cls, code):
        ''' Given an error code, translate it to a
        string error name. 
        
        :param code: The code number to translate
        '''
        values = dict((v, k) for k, v in cls.__dict__.iteritems()
            if not k.startswith('__') and not callable(v))
        return values.get(code, None)

class SerialException(Exception):
    ''' Base modbus exception '''

    def __init__(self, string):
        ''' Initialize the exception

        :param string: The message to append to the error
        '''
        self.string = string

    def __str__(self):
        return 'DF1 Serial Error: %s' % self.string


class IOException(SerialException):
    ''' Error resulting from data i/o '''

    def __init__(self, string=""):
        ''' Initialize the exception

        :param string: The message to append to the error
        '''
        message = "[Input/Output] %s" % string
        SerialException.__init__(self, message)


class ParameterException(SerialException):
    ''' Error resulting from invalid parameter '''

    def __init__(self, string=""):
        ''' Initialize the exception

        :param string: The message to append to the error
        '''
        message = "[Invalid Parameter] %s" % string
        SerialException.__init__(self, message)


class NoSuchSlaveException(SerialException):
    ''' Error resulting from making a request to a slave
    that does not exist '''

    def __init__(self, string=""):
        ''' Initialize the exception

        :param string: The message to append to the error
        '''
        message = "[No Such Slave] %s" % string
        SerialException.__init__(self, message)


class NotImplementedException(SerialException):
    ''' Error resulting from not implemented function '''

    def __init__(self, string=""):
        ''' Initialize the exception

        :param string: The message to append to the error
        '''
        message = "[Not Implemented] ", string
        SerialException.__init__(self, message)


class ConnectionException(SerialException):
    ''' Error resulting from a bad connection '''

    def __init__(self, string=""):
        ''' Initialize the exception

        :param string: The message to append to the error
        '''
        message = "[Connection] %s" % string
        SerialException.__init__(self, message)

class CRCException(SerialException):
    ''' Error resulting from a bad connection '''

    def __init__(self, string=""):
        ''' Initialize the exception

        :param string: The message to append to the error
        '''
        message = "[Connection] %s" % string
        SerialException.__init__(self, message)

#---------------------------------------------------------------------------#
# Exported symbols
#---------------------------------------------------------------------------#
__all__ = [
    "Singleton", "SerialException", "IOException",
    "ParameterException", "NotImplementedException",
    "ConnectionException", "NoSuchSlaveException",
]

