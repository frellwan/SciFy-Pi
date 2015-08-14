from constants import Defaults
import struct

class PDU(object):
    '''
    Base class for all DF1 mesages

    .. attribute:: transaction_id

       This value is used to uniquely identify a request
       response pair.  It can be implemented as a simple counter

    .. attribute:: Source

       This is a constant set at 0 for serial communication.
       
    .. attribute:: Destination

       This is used to route the request to the correct device.
       The value 0x00 represents the broadcast address.

    .. attribute:: skip_encode

       This is used when the message payload has already been encoded.
       Generally this will occur when the PayloadBuilder is being used
       to create a complicated message. By setting this to True, the
       request will pass the currently encoded message through instead
       of encoding it again.
    '''

    def __init__(self, **kwargs):
        ''' Initializes the base data for a modbus request '''
        self.transaction_id = kwargs.get('transaction', Defaults.TransactionId)
        self.skip_encode = kwargs.get('skip_encode', False)

    def encode(self):
        ''' Encodes the message

        :raises: A not implemented exception
        '''
        pass

    def decode(self, data):
        ''' Decodes data part of the message.

        :param data: is a string object
        :raises: A not implemented exception
        '''
        pass

    @classmethod
    def calculateRtuFrameSize(cls, buffer):
        ''' Calculates the size of a PDU.

        :param buffer: A buffer containing the data that have been received.
        :returns: The number of bytes in the PDU.
        '''
        if hasattr(cls, '_rtu_frame_size'):
            return cls._frame_size
        elif hasattr(cls, '_byte_count_pos'):
            return rtuFrameSize(buffer, cls._byte_count_pos)
        else: raise NotImplementedException(
            "Cannot determine RTU frame size for %s" % cls.__name__)



class DataInquiryRequest(PDU):
    '''
    class for reading a MTrim register
    '''
    _frame_size = 12

    def __init__(self, address, parameter, **kwargs):
        ''' Initializes a new instance

        :param address: The address of device to read from
        :parameter: The parameter to read
        '''
        PDU.__init__(self, **kwargs)
        self.address = address
        self.parameter = parameter
        self.msgType = '2'
        self.Data = '0000'
        self.dataFormat = '0'
        self.packet = ''

    def encode(self):
        ''' Encodes the request packet

        :return: The encoded packet
        '''
        if (not self.skip_encode):
            self.packet = struct.pack('>B', 0x02)        #STX
            if (self.address <10):
                self.packet += '0' + str(self.address)
            else:
                self.packet += str(self.address)
            self.packet += self.msgType
            if (self.parameter < 10):
                self.packet += '0' + str(self.parameter)
            else:
                self.packet += str(self.parameter)
            self.packet += self.Data
            self.packet += self.dataFormat
            self.packet += struct.pack('>B', 0x03)       #ETX
                        
        return self.packet

    def decode(self, data):
        ''' Decode a register request packet

        :param data: The request to decode
        '''
        self.address = int(data[1])*10 + int(data[2])
        self.msgType = int(data[3])
        self.parameter = int(data[4])*10 + int(data[5])
        self.data = '0000'
        self.dataFormat = '0'
            
    def __str__(self):
        ''' Returns a string representation of the instance

        :returns: A string representation of the instance
        '''
        return "DataInquiryRequest (%d,%d)" % (self.address, self.parameter)


class ParameterSendRequest(PDU):
    '''
    Class for writing a MTrim register
    '''
    _frame_size = 12

    def __init__(self, address=1, parameter=1, value=0, **kwargs):
        ''' Initializes a new instance

        :param address: The address of the device to write to
        :paramater: The parameter to write to
        :value: The value to write to the parameter
        '''
        PDU.__init__(self, **kwargs)
        self.address = address
        self.parameter = parameter
        self.msgType = '3'
        self.value = value
        self.Data = ''
        self.dataFormat = '0'
        self.packet = ''

    def encode(self):
        ''' Encodes the request packet

        :return: The encoded packet
        '''
        if (not self.skip_encode):
            self.packet = struct.pack('>B', 0x02)        #STX
            if (self.address <10):
                self.packet += '0' + str(self.address)
            else:
                self.packet += str(self.address)

            self.packet += self.msgType

            if (self.parameter < 10):
                self.packet += '0' + str(self.parameter)
            else:
                self.packet += str(self.parameter)

            strValue = str(self.value)
            if(self.parameter in [20,21,22,23]):
                if (self.value >= 0):
                    if strValue.find('.') == -1:
                        self.dataFormat = '0'
                    else:
                        self.dataFormat = str((len(strValue)-1)-strValue.find('.'))
                if (self.value < 0):
                    if strValue.find('.') == -1:
                        self.dataFormat = '4'
                    else:
                        self.dataFormat = str((len(strValue)-1)-strValue.find('.')+4)
            else:
                self.dataFormat = '0'
                
            if strValue.find('.') == -1:
                for c in range(4-len(strValue)):
                    self.Data += '0'
                self.Data += strValue
            else:
                for c in range(5-len(strValue)):
                    self.Data += '0'
                self.Data += "".join(strValue.split('.'))
                    
            self.packet += self.Data
            self.packet += self.dataFormat
            self.packet += struct.pack('>B', 0x03)       #ETX
                        
        return self.packet

    def decode(self, data):
        ''' Decode a register request packet

        :param data: The request to decode
        '''
        self.address = int(data[1])*10 + int(data[2])
        self.msgType = data[3]
        self.parameter = int(data[4])*10 + int(data[5])
        self.dataFormat = int(data[10])

        self.value = int(data[6:10])
        if (self.dataFormat <= 3):
            self.Data = self.value/(10**self.dataFormat)
        else:
            self.Data = -1 * self.value/(10**(self.dataFormat-4))

        return self
        
    def __str__(self):
        ''' Returns a string representation of the instance

        :returns: A string representation of the instance
        '''
        return "ParameterSendRequest (%d,%d,%d)" % (self.address, self.parameter, self.Data)

class ControlCommandSendRequest(PDU):
    '''
    class for sending a control command to a MTrim
    '''
    _frame_size = 12

    def __init__(self, address, value, **kwargs):
        ''' Initializes a new instance

        :param address: The address of device to write to
        :param vale: The value to write
        '''
        PDU.__init__(self, **kwargs)
        self.address = address
        self.parameter = '00'
        self.msgType = '1'
        self.value = value
        self.Data = ''
        self.dataFormat = '0'
        self.packet = ''

    def encode(self):
        ''' Encodes the request packet

        :return: The encoded packet
        '''
        if (not self.skip_encode):
            self.packet = struct.pack('>B', 0x02)        #STX
            if (self.address <10):
                self.packet += '0' + str(self.address)
            else:
                self.packet += str(self.address)

            self.packet += self.msgType

            self.packet += self.parameter

            self.packet += '00'
            if (self.value<10):
                self.packet += '0' + str(self.value)
            else:
                self.packet += str(self.value)
                    
            self.packet += self.dataFormat
            self.packet += struct.pack('>B', 0x03)       #ETX
                        
        return self.packet

    def decode(self, data):
        ''' Decode a register request packet

        :param data: The request to decode
        '''
        self.address = int(data[1])*10 + int(data[2])
        self.msgType = int(data[3])
        self.parameter = int(data[4])*10 + int(data[5])
        self.dataFormat = int(data[10])

        self.value = int(data[6:10])
        if (self.dataFormat <= 3):
            self.Data = self.value/(10*self.dataFormat)
        else:
            self.Data = -1 * self.value/(10*self.dataFormat)
        
    def __str__(self):
        ''' Returns a string representation of the instance

        :returns: A string representation of the instance
        '''
        return "ControlCommandSendRequest (%d,%d,%d)" % (self.address, self.Data)



class MTrimResponse(PDU):
    '''
    This function code is used to read the response from a MTrim controller
    '''
    _frame_size = 12
    should_respond = True
    parameters = []

    def __init__(self, address=None, parameter=None, **kwargs):
        ''' Initializes a new instance of the request

        :param address: The address of the device 
        :param parameter: The paramter that was addressed in the read/write
        '''
        PDU.__init__(self, **kwargs)
        self.address = address
        self.parameter = parameter
        self.errorCode = '@'
        self.Data = 0
        self.dataFormat = 0

    def encode(self):
        ''' Encodes the response packet

        :returns: The encoded packet
        '''
        # Need to implement if you want to act as a MTrim Device
        # Can use parameter[] to keep data values
        # Use getParameter to get data
        pass

    def decode(self, data):
        ''' Decode a register response packet

        :param data: The request to decode
        '''
        if len(data) != 12:
            return None
        self.address = int(data[1])*10 + int(data[2])
        self.errorCode = data[3]
        self.parameter = int(data[4])*10 + int(data[5])
        self.dataFormat = int(data[10])

        if (self.dataFormat == 0):
            self.Data = int(data[6])*1000 + int(data[7])*100 + int(data[8])*10 + int(data[9])
        elif (self.dataFormat == 1):
            self.Data = int(data[6])*100 + int(data[7])*10 + int(data[8]) + int(data[9])*.1
        elif (self.dataFormat == 2):
            self.Data = int(data[6])*10 + int(data[7]) + int(data[8])*.1 + int(data[9])*.01
        elif (self.dataFormat == 3):
            self.Data = int(data[6]) + int(data[7])*.1 + int(data[8])*.01 + int(data[9])*.001
        elif (self.dataFormat == 4):
            self.Data = int(data[6])*-1000 + int(data[7])*-100 + int(data[8])*-10 + int(data[9])*-1
        elif (self.dataFormat == 5):
            self.Data = int(data[6])*-100 + int(data[7])*-10 + int(data[8])*-1 + int(data[9])*-.1
        elif (self.dataFormat == 6):
            self.Data = int(data[6])*-10 + int(data[7])*-1 + int(data[8])*-.1 + int(data[9])*-.01
        elif (self.dataFormat == 7):
            self.Data = int(data[6])*-1 + int(data[7])*-.1 + int(data[8])*-.01 + int(data[9])*-.001
        else:
            self.data = int(data[6])*10 + int(data[7]) + int(data[8])*.1 + int(data[9])*.01

    def getParameter(self, index):
        ''' Get the requested register

        :param index: The indexed register to retrieve
        :returns: The request register
        '''
        return self.parameters[index]

    def __str__(self):
        ''' Returns a string representation of the instance

        :returns: A string representation of the instance
        '''
        return "MTrimsponse (%d)" % self._frame_size
